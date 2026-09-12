"""
Financial Core Integration for Construction Module.

All financial impacts from construction operations must go through Financial Core
by creating journal entries via the financial service. Direct GL/Journal mutations
are prohibited.

Posting is idempotent per business reference: calling a record_* function twice
with the same source document returns the existing journal entry instead of
creating a duplicate posting.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import commit_db
from ..financial.models import JournalEntry
from ..financial.schemas import JournalEntryCreate, JournalLineCreate
from ..financial.service import create_draft, post_entry
from . import service as construction_service
from .models import (
    GoodsReceipt,
    Payment,
    ProgressClaim,
    ProjectFinancialAccounts,
    SupplierInvoice,
)


def get_project_accounts(
    db: Session, tenant_id: UUID, project_id: UUID
) -> ProjectFinancialAccounts | None:
    """
    Retrieve project-specific financial account configuration.
    Returns None if not configured - caller should handle appropriately.
    """
    return db.scalar(
        select(ProjectFinancialAccounts).where(
            ProjectFinancialAccounts.tenant_id == tenant_id,
            ProjectFinancialAccounts.project_id == project_id,
        )
    )


def ensure_project_accounts_configured(
    db: Session, tenant_id: UUID, project_id: UUID
) -> ProjectFinancialAccounts:
    """
    Ensure project has financial accounts configured, raise if not.
    """
    accounts = get_project_accounts(db, tenant_id, project_id)
    if accounts is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Project {project_id} does not have financial accounts configured. "
                "Configure project financial accounts before processing financial transactions."
            ),
        )
    return accounts


def _find_existing_entry(db: Session, *, tenant_id: UUID, reference: str) -> JournalEntry | None:
    """Return an already-posted entry for a business reference, if any."""
    return db.scalar(
        select(JournalEntry).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.reference == reference,
        )
    )


def _create_journal_entry(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    accounting_date: date,
    currency: str,
    description: str,
    reference: str,
    lines: list[JournalLineCreate],
    request_id: str | None = None,
) -> UUID:
    """Create and post a journal entry through Financial Core.

    Idempotent: a journal entry already recorded for (tenant_id, reference)
    is returned as-is; no duplicate posting is created. Atomicity is enforced
    by UNIQUE (tenant_id, reference): a concurrent duplicate insert raises
    IntegrityError, in which case the transaction rolls back and the winning
    entry is returned deterministically.
    """
    existing = _find_existing_entry(db, tenant_id=tenant_id, reference=reference)
    if existing is not None:
        return existing.id
    payload = JournalEntryCreate(
        accounting_date=accounting_date,
        currency=currency,
        description=description,
        reference=reference,
        lines=lines,
    )
    try:
        entry = create_draft(
            db, tenant_id=tenant_id, user_id=user_id, payload=payload, request_id=request_id
        )
        posted = post_entry(
            db, tenant_id=tenant_id, user_id=user_id, entry_id=entry.id, request_id=request_id
        )
        commit_db(db)
    except IntegrityError:
        # Lost a concurrent race on (tenant_id, reference) or entry_number.
        # The transaction is rolled back; return the winner if our reference
        # won elsewhere, otherwise surface a genuine write conflict.
        db.rollback()
        winner = _find_existing_entry(db, tenant_id=tenant_id, reference=reference)
        if winner is not None:
            return winner.id
        raise HTTPException(
            status_code=409, detail="financial write conflicted with another transaction"
        )
    except HTTPException as exc:
        # commit_financial maps an IntegrityError to HTTP 409 after rolling
        # back; resolve it to the winning entry the same way.
        if exc.status_code != 409 or "conflicted" not in exc.detail:
            raise
        winner = _find_existing_entry(db, tenant_id=tenant_id, reference=reference)
        if winner is not None:
            return winner.id
        raise
    return posted.id


def _resolve_project_id_for_claim(db: Session, *, tenant_id: UUID, claim: ProgressClaim) -> UUID:
    contract = construction_service.get_contract(db, tenant_id=tenant_id, contract_id=claim.contract_id)
    return contract.project_id


def _resolve_project_id_for_procurement(
    db: Session, *, tenant_id: UUID, procurement_id: UUID
) -> UUID:
    procurement = construction_service.get_procurement(
        db, tenant_id=tenant_id, procurement_id=procurement_id
    )
    return procurement.project_id


def record_progress_claim_payment(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    claim: ProgressClaim,
    accounting_date: date,
    currency: str,
    request_id: str | None = None,
) -> UUID:
    """
    Record payment for a progress claim.

    Creates a journal entry:
    - Debit: Accounts Receivable
    - Credit: Construction Revenue
    """
    if claim.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="progress claim not found")
    if claim.total_amount <= 0:
        raise ValueError("claim amount must be greater than zero")
    project_id = _resolve_project_id_for_claim(db, tenant_id=tenant_id, claim=claim)
    accounts = ensure_project_accounts_configured(db, tenant_id, project_id)

    lines = [
        JournalLineCreate(
            account_id=accounts.accounts_receivable_account_id,
            debit=claim.total_amount,
            credit=Decimal("0"),
            description=f"Progress claim {claim.claim_number} payment received",
        ),
        JournalLineCreate(
            account_id=accounts.construction_revenue_account_id,
            debit=Decimal("0"),
            credit=claim.total_amount,
            description=f"Revenue recognized for progress claim {claim.claim_number}",
        ),
    ]

    return _create_journal_entry(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        accounting_date=accounting_date,
        currency=currency,
        description=f"Progress claim {claim.claim_number} payment",
        reference=f"CLAIM-{claim.claim_number}",
        lines=lines,
        request_id=request_id,
    )


def record_supplier_invoice(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    invoice: SupplierInvoice,
    accounting_date: date,
    currency: str,
    request_id: str | None = None,
) -> UUID:
    """
    Record a supplier invoice (AP entry).

    Creates a journal entry:
    - Debit: Construction Materials
    - Credit: Accounts Payable
    """
    if invoice.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="supplier invoice not found")
    if invoice.total_amount <= 0:
        raise ValueError("invoice amount must be greater than zero")
    purchase_order = construction_service.get_purchase_order(
        db, tenant_id=tenant_id, po_id=invoice.purchase_order_id
    )
    project_id = _resolve_project_id_for_procurement(
        db, tenant_id=tenant_id, procurement_id=purchase_order.procurement_id
    )
    accounts = ensure_project_accounts_configured(db, tenant_id, project_id)

    lines = [
        JournalLineCreate(
            account_id=accounts.materials_account_id,
            debit=invoice.total_amount,
            credit=Decimal("0"),
            description=f"Supplier invoice {invoice.invoice_number} for PO {purchase_order.po_number}",
        ),
        JournalLineCreate(
            account_id=accounts.accounts_payable_account_id,
            debit=Decimal("0"),
            credit=invoice.total_amount,
            description=f"AP for supplier invoice {invoice.invoice_number}",
        ),
    ]

    return _create_journal_entry(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        accounting_date=accounting_date,
        currency=currency,
        description=f"Supplier invoice {invoice.invoice_number}",
        reference=f"INV-{invoice.invoice_number}",
        lines=lines,
        request_id=request_id,
    )


def record_payment(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    payment: Payment,
    accounting_date: date,
    currency: str,
    request_id: str | None = None,
) -> UUID:
    """
    Record a payment to supplier.

    Creates a journal entry:
    - Debit: Accounts Payable
    - Credit: Cash/Bank
    """
    if payment.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="payment not found")
    if payment.amount <= 0:
        raise ValueError("payment amount must be greater than zero")
    invoice = construction_service.get_supplier_invoice(
        db, tenant_id=tenant_id, invoice_id=payment.supplier_invoice_id
    )
    purchase_order = construction_service.get_purchase_order(
        db, tenant_id=tenant_id, po_id=invoice.purchase_order_id
    )
    project_id = _resolve_project_id_for_procurement(
        db, tenant_id=tenant_id, procurement_id=purchase_order.procurement_id
    )
    accounts = ensure_project_accounts_configured(db, tenant_id, project_id)

    lines = [
        JournalLineCreate(
            account_id=accounts.accounts_payable_account_id,
            debit=payment.amount,
            credit=Decimal("0"),
            description=f"Payment {payment.payment_number} for invoice {invoice.invoice_number}",
        ),
        JournalLineCreate(
            account_id=accounts.cash_account_id,
            debit=Decimal("0"),
            credit=payment.amount,
            description=f"Cash outflow for payment {payment.payment_number}",
        ),
    ]

    return _create_journal_entry(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        accounting_date=accounting_date,
        currency=currency,
        description=f"Supplier payment {payment.payment_number}",
        reference=f"PAY-{payment.payment_number}",
        lines=lines,
        request_id=request_id,
    )


def record_goods_receipt(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    grn: GoodsReceipt,
    accounting_date: date,
    currency: str,
    request_id: str | None = None,
) -> UUID:
    """
    Record goods receipt (inventory/accrual entry).

    Creates a journal entry:
    - Debit: Inventory (Construction Materials)
    - Credit: Goods Received Not Invoiced (GRNI) / Accrued Payables
    """
    if grn.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="goods receipt not found")
    purchase_order = construction_service.get_purchase_order(
        db, tenant_id=tenant_id, po_id=grn.purchase_order_id
    )
    project_id = _resolve_project_id_for_procurement(
        db, tenant_id=tenant_id, procurement_id=purchase_order.procurement_id
    )
    accounts = ensure_project_accounts_configured(db, tenant_id, project_id)

    po_lines = construction_service.list_purchase_order_lines(
        db, tenant_id=tenant_id, po_id=purchase_order.id
    )
    unit_price_by_line = {line.id: line.unit_price for line in po_lines}
    grn_lines = construction_service.list_goods_receipt_lines(
        db, tenant_id=tenant_id, grn_id=grn.id
    )
    total = sum(
        (line.quantity_accepted * unit_price_by_line.get(line.po_line_id, Decimal("0"))
         for line in grn_lines),
        Decimal("0"),
    )

    if total <= 0:
        raise ValueError("GRN total amount must be greater than zero")

    lines = [
        JournalLineCreate(
            account_id=accounts.inventory_account_id,
            debit=total,
            credit=Decimal("0"),
            description=f"GRN {grn.grn_number} for PO {purchase_order.po_number}",
        ),
        JournalLineCreate(
            account_id=accounts.grni_account_id,
            debit=Decimal("0"),
            credit=total,
            description=f"GRNI accrual for GRN {grn.grn_number}",
        ),
    ]

    return _create_journal_entry(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        accounting_date=accounting_date,
        currency=currency,
        description=f"Goods receipt {grn.grn_number}",
        reference=f"GRN-{grn.grn_number}",
        lines=lines,
        request_id=request_id,
    )
