from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class InvoiceStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"


class BillStatus(str, Enum):
    draft = "draft"
    received = "received"
    approved = "approved"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class BankAccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    credit = "credit"
    cash = "cash"


class ReconciliationStatus(str, Enum):
    pending = "pending"
    matched = "matched"
    unmatched = "unmatched"


class Account(Base):
    __tablename__ = "financial_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_financial_account_tenant_code"),
        CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')",
            name="ck_financial_account_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Running balances (cached for performance)
    current_balance_debit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    current_balance_credit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))


class JournalEntry(Base):
    __tablename__ = "financial_journal_entries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entry_number", name="uq_financial_journal_tenant_number"),
        UniqueConstraint(
            "tenant_id", "reference", name="uq_financial_journal_tenant_reference"
        ),
        CheckConstraint("status IN ('draft', 'posted')", name="ck_financial_journal_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    accounting_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JournalLine(Base):
    __tablename__ = "financial_journal_lines"
    __table_args__ = (
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_financial_line_nonnegative"),
        CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_financial_line_single_side"),
        CheckConstraint("debit + credit > 0", name="ck_financial_line_nonzero"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    journal_entry_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("financial_journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("financial_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# AR/AP Models
# ============================================================

class Customer(Base):
    """Customer for AR."""
    __tablename__ = "financial_customers"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(20), nullable=False, default="NET30")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    ar_account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_accounts.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Supplier(Base):
    """Supplier for AP."""
    __tablename__ = "financial_suppliers"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(20), nullable=False, default="NET30")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    ap_account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_accounts.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Invoice(Base):
    """Customer Invoice (AR)."""
    __tablename__ = "financial_invoices"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_customers.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=InvoiceStatus.draft.value, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    balance_due: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    journal_entry_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_journal_entries.id"), nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InvoiceLine(Base):
    __tablename__ = "financial_invoice_lines"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0"))
    account_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_accounts.id"), nullable=True)
    line_total: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Bill(Base):
    """Supplier Bill (AP)."""
    __tablename__ = "financial_bills"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    bill_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    supplier_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_suppliers.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=BillStatus.draft.value, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    balance_due: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    journal_entry_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_journal_entries.id"), nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BillLine(Base):
    __tablename__ = "financial_bill_lines"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    bill_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_bills.id", ondelete="CASCADE"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0"))
    account_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_accounts.id"), nullable=True)
    line_total: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    """Payment (can be for AR or AP)."""
    __tablename__ = "financial_payments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    payment_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "customer" or "supplier"
    customer_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_customers.id"), nullable=True, index=True)
    supplier_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_suppliers.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PaymentStatus.pending.value, index=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False, default="bank_transfer")
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bank_account_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_bank_accounts.id"), nullable=True)
    journal_entry_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_journal_entries.id"), nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PaymentAllocation(Base):
    """Payment allocation to invoices/bills."""
    __tablename__ = "financial_payment_allocations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_payments.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_invoices.id"), nullable=True, index=True)
    bill_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_bills.id"), nullable=True, index=True)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# Bank Reconciliation Models
# ============================================================

class BankAccount(Base):
    __tablename__ = "financial_bank_accounts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=True)
    bank_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default=BankAccountType.checking.value)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    gl_account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_accounts.id"), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    last_reconciled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_reconciled_balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BankTransaction(Base):
    __tablename__ = "financial_bank_transactions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    bank_account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ReconciliationStatus.pending.value)
    matched_journal_entry_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("financial_journal_entries.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BankReconciliation(Base):
    __tablename__ = "financial_bank_reconciliations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    bank_account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("financial_bank_accounts.id"), nullable=False, index=True)
    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    statement_balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    book_balance: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    difference: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    reconciled_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CurrencyExchangeRate(Base):
    """Exchange rates for multi-currency support."""
    __tablename__ = "financial_currency_exchange_rates"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
