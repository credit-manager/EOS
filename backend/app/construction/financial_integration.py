"""
Financial Core Integration for Construction Module.

All financial impacts from construction operations must go through Financial Core
by creating journal entries via the financial service. Direct GL/Journal modifications
are prohibited.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from ..financial.schemas import JournalEntryCreate, JournalLineCreate
from ..financial.service import commit_financial, create_draft, post_entry
from .models import (
    GoodsReceipt,
    Payment,
    ProgressClaim,
    SupplierInvoice,
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
    """Create and post a journal entry through Financial Core."""
    payload = JournalEntryCreate(
        accounting_date=accounting_date,
        currency=currency,
        description=description,
        reference=reference,
        lines=lines,
    )
    entry = create_draft(db, tenant_id=tenant_id, user_id=user_id, payload=payload, request_id=request_id)
    posted = post_entry(db, tenant_id=tenant_id, user_id=user_id, entry_id=entry.id, request_id=request_id)
    commit_financial(db)
    return posted.id


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
    - Debit: Accounts Receivable (or Cash/Bank)
    - Credit: Construction Revenue
    """
    if claim.total_amount <= 0:
        raise ValueError("claim amount must be greater than zero")
    
    lines = [
        JournalLineCreate(
            account_id=claim.contract.project.client_receivable_account_id,  # To be configured
            debit=claim.total_amount,
            credit=Decimal("0"),
            description=f"Progress claim {claim.claim_number} payment received",
        ),
        JournalLineCreate(
            account_id=claim.contract.project.construction_revenue_account_id,  # To be configured
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
    - Debit: Construction Materials/Expenses (based on invoice lines)
    - Credit: Accounts Payable
    """
    if invoice.total_amount <= 0:
        raise ValueError("invoice amount must be greater than zero")
    
    # For simplicity, using a single expense account - in reality would split by line
    lines = [
        JournalLineCreate(
            account_id=invoice.purchase_order.procurement.project.materials_account_id,  # To be configured
            debit=invoice.total_amount,
            credit=Decimal("0"),
            description=f"Supplier invoice {invoice.invoice_number} for PO {invoice.purchase_order.po_number}",
        ),
        JournalLineCreate(
            account_id=invoice.purchase_order.procurement.project.accounts_payable_account_id,  # To be configured
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
    if payment.amount <= 0:
        raise ValueError("payment amount must be greater than zero")
    
    lines = [
        JournalLineCreate(
            account_id=payment.supplier_invoice.purchase_order.procurement.project.accounts_payable_account_id,  # To be configured
            debit=payment.amount,
            credit=Decimal("0"),
            description=f"Payment {payment.payment_number} for invoice {payment.supplier_invoice.invoice_number}",
        ),
        JournalLineCreate(
            account_id=payment.supplier_invoice.purchase_order.procurement.project.cash_account_id,  # To be configured
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
    - Debit: Inventory/WIP (Construction Materials)
    - Credit: Goods Received Not Invoiced (GRNI) / Accrued Payables
    """
    # Calculate total from lines
    total = sum((line.quantity_accepted * line.po_line.unit_price for line in grn.lines), Decimal("0"))
    
    if total <= 0:
        raise ValueError("GRN total amount must be greater than zero")
    
    lines = [
        JournalLineCreate(
            account_id=grn.purchase_order.procurement.project.inventory_account_id,  # To be configured
            debit=total,
            credit=Decimal("0"),
            description=f"GRN {grn.grn_number} for PO {grn.purchase_order.po_number}",
        ),
        JournalLineCreate(
            account_id=grn.purchase_order.procurement.project.grni_account_id,  # To be configured
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


# ---------------------------------------------------------------------------
# Project Account Configuration (to be set up per project)
# ---------------------------------------------------------------------------

class ProjectFinancialAccounts:
    """Account IDs for a construction project's financial accounts.
    
    These should be configured per project/tenant during project setup.
    """
    def __init__(
        self,
        tenant_id: UUID,
        project_id: UUID,
        cash_account_id: UUID,
        accounts_receivable_account_id: UUID,
        accounts_payable_account_id: UUID,
        inventory_account_id: UUID,
        grni_account_id: UUID,
        materials_account_id: UUID,
        construction_revenue_account_id: UUID,
        labor_account_id: UUID,
        equipment_account_id: UUID,
        subcontractor_account_id: UUID,
        overhead_account_id: UUID,
        wip_account_id: UUID,
    ):
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.cash_account_id = cash_account_id
        self.accounts_receivable_account_id = accounts_receivable_account_id
        self.accounts_payable_account_id = accounts_payable_account_id
        self.inventory_account_id = inventory_account_id
        self.grni_account_id = grni_account_id
        self.materials_account_id = materials_account_id
        self.construction_revenue_account_id = construction_revenue_account_id
        self.labor_account_id = labor_account_id
        self.equipment_account_id = equipment_account_id
        self.subcontractor_account_id = subcontractor_account_id
        self.overhead_account_id = overhead_account_id
        self.wip_account_id = wip_account_id


def get_project_accounts(db: Session, tenant_id: UUID, project_id: UUID) -> ProjectFinancialAccounts | None:
    """
    Retrieve project-specific financial account configuration.
    Returns None if not configured - caller should handle appropriately.
    """
    from .models import ProjectFinancialAccounts as PFAModel
    
    accounts = db.query(PFAModel).filter(
        PFAModel.tenant_id == tenant_id,
        PFAModel.project_id == project_id
    ).first()
    
    if accounts is None:
        return None
    
    return ProjectFinancialAccounts(
        tenant_id=accounts.tenant_id,
        project_id=accounts.project_id,
        cash_account_id=accounts.cash_account_id,
        accounts_receivable_account_id=accounts.accounts_receivable_account_id,
        accounts_payable_account_id=accounts.accounts_payable_account_id,
        inventory_account_id=accounts.inventory_account_id,
        grni_account_id=accounts.grni_account_id,
        materials_account_id=accounts.materials_account_id,
        construction_revenue_account_id=accounts.construction_revenue_account_id,
        labor_account_id=accounts.labor_account_id,
        equipment_account_id=accounts.equipment_account_id,
        subcontractor_account_id=accounts.subcontractor_account_id,
        overhead_account_id=accounts.overhead_account_id,
        wip_account_id=accounts.wip_account_id,
    )


def ensure_project_accounts_configured(db: Session, tenant_id: UUID, project_id: UUID) -> ProjectFinancialAccounts:
    """
    Ensure project has financial accounts configured, raise if not.
    """
    accounts = get_project_accounts(db, tenant_id, project_id)
    if accounts is None:
        raise ValueError(
            f"Project {project_id} does not have financial accounts configured. "
            "Please configure project financial accounts before processing financial transactions."
        )
    return accounts