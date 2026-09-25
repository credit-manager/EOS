"""Document -> Ledger bridge (STEP 2 Slice 5 -- the wedge's missing link).

Chain enforced (governed execution, LLM never source of truth):
    validated Document (category=invoice, extracted_data present)
      -> accounting classification (domain-controlled code path; NOT metadata-configurable)
      -> LedgerEntry DRAFT via financial.posting_service.create_journal_entry
        (which enforces Debit == Credit and validates accounts/periods)
      -> governed posting via post_entry (draft-only guard => idempotency at ledger level)
      -> audit event on every step.

Idempotency: one document produces at most one journal entry, keyed by
(reference_type="document", reference_id=document_id). Re-processing returns
the existing entry instead of creating a duplicate.

NOTE: uses the LEDGER models (financial/ledger.py: LedgerAccount with
`account_code`, LedgerEntry/LedgerLine) — that is the real System of Record
used by posting_service. The financial_accounts table (models.py) is the
legacy AR/AP surface and is intentionally NOT written here.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import service as audit
from ..financial.ledger import LedgerAccount, LedgerEntry
from ..financial.posting_service import create_journal_entry, post_entry
from .models import Document

logger = logging.getLogger("2to-eos.documents.ledger_bridge")

# Domain-controlled chart-of-accounts codes (Construction P2P supplier invoice).
# These are explicit code constants ON PURPOSE: ledger/tax invariants must never
# be freely metadata-configurable (Production Completion Standard).
AP_ACCOUNT_CODE = "2100"          # Accounts Payable (liability)
EXPENSE_ACCOUNT_CODE = "5100"     # Subcontract / materials expense
TAX_INPUT_ACCOUNT_CODE = "1300"   # VAT/sales tax recoverable (asset)


class InvoiceClassificationError(HTTPException):
    def __init__(self, reason: str):
        super().__init__(status_code=422, detail=f"invoice cannot be classified for ledger: {reason}")


def _extract_decimal(data: dict[str, Any], *keys: str) -> Decimal | None:
    for k in keys:
        v = data.get(k)
        if v is None or v == "":
            continue
        try:
            return Decimal(str(v)).quantize(Decimal("0.0001"))
        except (InvalidOperation, ValueError):
            continue
    return None


def classify_invoice_for_ledger(document: Document) -> dict[str, Any]:
    """Turn untrusted extracted_data into a trusted, validated posting plan.

    Returns {"total","tax","net","currency","invoice_date"} or raises 422.
    This validation gate is what makes OCR output safe to touch the ledger.
    """
    data = document.extracted_data or {}
    total = _extract_decimal(data, "total", "invoice_total", "amount_due")
    if total is None or total <= 0:
        raise InvoiceClassificationError("missing or non-positive total")
    tax = _extract_decimal(data, "tax", "tax_amount", "vat") or Decimal("0")
    subtotal = _extract_decimal(data, "subtotal", "net", "base_amount")
    if subtotal is None:
        subtotal = total - tax
    if tax < 0 or subtotal <= 0:
        raise InvoiceClassificationError("negative tax or non-positive net amount")
    if (subtotal + tax) != total:
        raise InvoiceClassificationError(
            f"line math mismatch: subtotal {subtotal} + tax {tax} != total {total}"
        )
    currency = str(data.get("currency") or "EGP").upper()[:3]
    raw_date = data.get("invoice_date") or data.get("date")
    invoice_date = None
    if raw_date:
        try:
            from datetime import datetime as dt
            invoice_date = dt.strptime(str(raw_date)[:10], "%Y-%m-%d").date()
        except ValueError:
            invoice_date = None
    return {
        "total": total, "tax": tax, "net": subtotal,
        "currency": currency, "invoice_date": invoice_date or date.today(),
    }


def _account(db: Session, tenant_id: UUID, code: str) -> LedgerAccount:
    acct = db.scalar(select(LedgerAccount).where(
        LedgerAccount.tenant_id == tenant_id,
        LedgerAccount.account_code == code,
        LedgerAccount.is_active.is_(True),
    ))
    if acct is None:
        raise HTTPException(
            status_code=409,
            detail=f"chart of accounts missing active account {code}",
        )
    return acct


def create_journal_draft_from_document(
    db: Session, *, tenant_id: UUID, user_id: UUID, document_id: str,
    request_id: str | None = None,
) -> LedgerEntry:
    """Validated invoice document -> balanced draft journal entry (idempotent)."""
    doc = db.get(Document, document_id)
    if doc is None or doc.tenant_id != str(tenant_id):
        raise HTTPException(status_code=404, detail="document not found")
    if doc.category != "invoice":
        raise HTTPException(status_code=422, detail="only invoice documents can be bridged to ledger")

    # Idempotency: same document => same entry, never a second one.
    existing = db.scalar(select(LedgerEntry).where(
        LedgerEntry.tenant_id == tenant_id,
        LedgerEntry.reference_type == "document",
        LedgerEntry.reference_id == uuid.UUID(document_id),
    ))
    if existing is not None:
        return existing

    plan = classify_invoice_for_ledger(doc)
    ap = _account(db, tenant_id, AP_ACCOUNT_CODE)
    expense = _account(db, tenant_id, EXPENSE_ACCOUNT_CODE)
    lines: list[dict] = [
        {"account_id": expense.id, "debit": str(plan["net"]), "credit": "0",
         "description": f"Subcontract expense ({doc.original_filename})"},
    ]
    if plan["tax"] > 0:
        tax_acct = _account(db, tenant_id, TAX_INPUT_ACCOUNT_CODE)
        lines.append({"account_id": tax_acct.id, "debit": str(plan["tax"]), "credit": "0",
                      "description": "Input VAT recoverable"})
    lines.append({"account_id": ap.id, "debit": "0", "credit": str(plan["total"]),
                  "description": f"Payable for invoice {doc.original_filename}"})

    entry = create_journal_entry(
        db, tenant_id=tenant_id, user_id=user_id,
        entry_date=plan["invoice_date"],
        description=f"Supplier invoice from document {doc.original_filename}",
        lines=lines, reference_type="document",
        reference_id=uuid.UUID(document_id), currency=plan["currency"],
    )
    audit.record(db, tenant_id=tenant_id, actor_id=user_id,
                 action="documents.ledger.draft_created", resource_type="document",
                 resource_id=uuid.UUID(document_id),
                 metadata={"journal_entry_id": str(entry.id), "total": str(plan["total"]),
                           "currency": plan["currency"]},
                 request_id=request_id)
    return entry


def post_document_journal(
    db: Session, *, tenant_id: UUID, user_id: UUID, document_id: str,
    request_id: str | None = None,
) -> LedgerEntry:
    """Governed posting: draft -> posted via posting_service (which re-checks
    balance, periods, account validity, and refuses already-posted entries)."""
    entry = create_journal_draft_from_document(
        db, tenant_id=tenant_id, user_id=user_id, document_id=document_id,
        request_id=request_id,
    )
    if entry.status == "posted":
        return entry  # idempotent replay
    posted = post_entry(db, tenant_id=tenant_id, user_id=user_id,
                        entry_id=entry.id, request_id=request_id)
    audit.record(db, tenant_id=tenant_id, actor_id=user_id,
                 action="documents.ledger.entry_posted", resource_type="document",
                 resource_id=uuid.UUID(document_id),
                 metadata={"journal_entry_id": str(posted.id)},
                 request_id=request_id)
    db.commit()
    return posted
