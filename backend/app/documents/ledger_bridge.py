"""Document -> Ledger bridge (STEP 2 Slice 5).

Chain:
    validated invoice document
      -> domain-controlled accounting classification
      -> balanced LedgerEntry draft
      -> governed posting through posting_service
      -> audit trail

The LLM/OCR output is treated as untrusted input. Ledger writes are performed
only through the existing financial posting service.
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

# Domain-controlled chart-of-accounts codes. These are deliberately not
# metadata-configurable because accounting/tax invariants must remain governed.
AP_ACCOUNT_CODE = "2100"
EXPENSE_ACCOUNT_CODE = "5100"
TAX_INPUT_ACCOUNT_CODE = "1300"


class InvoiceClassificationError(HTTPException):
    def __init__(self, reason: str):
        super().__init__(
            status_code=422,
            detail=f"invoice cannot be classified for ledger: {reason}",
        )


def _extract_decimal(data: dict[str, Any], *keys: str) -> Decimal | None:
    for key in keys:
        value = data.get(key)
        if value is None or value == "":
            continue
        try:
            return Decimal(str(value)).quantize(Decimal("0.0001"))
        except (InvalidOperation, ValueError):
            continue
    return None


def classify_invoice_for_ledger(document: Document) -> dict[str, Any]:
    """Validate extracted invoice data before it can reach the ledger."""
    data = document.extracted_data or {}
    total = _extract_decimal(data, "total", "invoice_total", "amount_due")
    if total is None or total <= 0:
        raise InvoiceClassificationError("missing or non-positive total")

    tax = _extract_decimal(data, "tax", "tax_amount", "vat") or Decimal("0")
    subtotal = _extract_decimal(data, "subtotal", "net", "base_amount")
    if subtotal is None:
        subtotal = total - tax

    if tax < 0 or subtotal <= 0:
        raise InvoiceClassificationError(
            "negative tax or non-positive net amount"
        )

    if subtotal + tax != total:
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
        "total": total,
        "tax": tax,
        "net": subtotal,
        "currency": currency,
        "invoice_date": invoice_date or date.today(),
    }


def _account(db: Session, tenant_id: UUID, code: str) -> LedgerAccount:
    account = db.scalar(
        select(LedgerAccount).where(
            LedgerAccount.tenant_id == tenant_id,
            LedgerAccount.account_code == code,
            LedgerAccount.is_active.is_(True),
        )
    )
    if account is None:
        raise HTTPException(
            status_code=409,
            detail=f"chart of accounts missing active account {code}",
        )
    return account


def create_journal_draft_from_document(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    document_id: str,
    request_id: str | None = None,
) -> LedgerEntry:
    """Create a balanced, idempotent draft journal entry from an invoice."""
    document = db.get(Document, document_id)
    if document is None or document.tenant_id != str(tenant_id):
        raise HTTPException(status_code=404, detail="document not found")
    if document.category != "invoice":
        raise HTTPException(
            status_code=422,
            detail="only invoice documents can be bridged to ledger",
        )

    # Idempotency: one document maps to one ledger entry.
    existing = db.scalar(
        select(LedgerEntry).where(
            LedgerEntry.tenant_id == tenant_id,
            LedgerEntry.reference_type == "document",
            LedgerEntry.reference_id == uuid.UUID(document_id),
        )
    )
    if existing is not None:
        return existing

    plan = classify_invoice_for_ledger(document)
    ap = _account(db, tenant_id, AP_ACCOUNT_CODE)
    expense = _account(db, tenant_id, EXPENSE_ACCOUNT_CODE)

    lines: list[dict] = [
        {
            "account_id": expense.id,
            "debit": str(plan["net"]),
            "credit": "0",
            "description": f"Subcontract expense ({document.original_filename})",
        }
    ]

    if plan["tax"] > 0:
        tax_account = _account(db, tenant_id, TAX_INPUT_ACCOUNT_CODE)
        lines.append(
            {
                "account_id": tax_account.id,
                "debit": str(plan["tax"]),
                "credit": "0",
                "description": "Input VAT recoverable",
            }
        )

    lines.append(
        {
            "account_id": ap.id,
            "debit": "0",
            "credit": str(plan["total"]),
            "description": f"Payable for invoice {document.original_filename}",
        }
    )

    entry = create_journal_entry(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        entry_date=plan["invoice_date"],
        description=f"Supplier invoice from document {document.original_filename}",
        lines=lines,
        reference_type="document",
        reference_id=uuid.UUID(document_id),
        currency=plan["currency"],
    )

    audit.record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="documents.ledger.draft_created",
        resource_type="document",
        resource_id=uuid.UUID(document_id),
        metadata={
            "journal_entry_id": str(entry.id),
            "total": str(plan["total"]),
            "currency": plan["currency"],
        },
        request_id=request_id,
    )
    return entry


def post_document_journal(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    document_id: str,
    request_id: str | None = None,
) -> LedgerEntry:
    """Governed document -> ledger posting with replay-safe behavior."""
    entry = create_journal_draft_from_document(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        document_id=document_id,
        request_id=request_id,
    )

    if entry.status == "posted":
        return entry

    posted = post_entry(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        entry_id=entry.id,
        request_id=request_id,
    )
    audit.record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="documents.ledger.entry_posted",
        resource_type="document",
        resource_id=uuid.UUID(document_id),
        metadata={"journal_entry_id": str(posted.id)},
        request_id=request_id,
    )
    db.commit()
    return posted
