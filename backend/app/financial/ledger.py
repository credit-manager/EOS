"""Double-entry Financial Ledger — the financial truth of the Business Operating System."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
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


# ============================================================
# Fiscal Period
# ============================================================

class FiscalPeriod(Base):
    """Fiscal period for closing books."""
    __tablename__ = "financial_fiscal_periods"
    __table_args__ = (
        UniqueConstraint("tenant_id", "period_name", name="uq_fiscal_period_tenant_name"),
        CheckConstraint(
            "status IN ('open', 'closed', 'locked')",
            name="ck_fiscal_period_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_name: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    closed_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ============================================================
# Chart of Accounts (extended)
# ============================================================

class LedgerAccount(Base):
    """Extended chart of accounts with parent hierarchy and normal balance."""
    __tablename__ = "financial_ledger_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_code", name="uq_ledger_account_tenant_code"),
        CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')",
            name="ck_ledger_account_type",
        ),
        CheckConstraint(
            "normal_balance IN ('debit', 'credit')",
            name="ck_ledger_account_normal_balance",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    normal_balance: Mapped[str] = mapped_column(String(10), nullable=False)
    parent_account_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("financial_ledger_accounts.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ============================================================
# Ledger Journal Entry
# ============================================================

class LedgerEntry(Base):
    """Double-entry journal entry with reference tracking and period."""
    __tablename__ = "financial_ledger_entries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entry_number", name="uq_ledger_entry_tenant_number"),
        CheckConstraint(
            "status IN ('draft', 'posted', 'reversed')",
            name="ck_ledger_entry_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    posted_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_by_entry_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    period_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("financial_fiscal_periods.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LedgerLine(Base):
    """Journal line for a ledger entry."""
    __tablename__ = "financial_ledger_lines"
    __table_args__ = (
        CheckConstraint("debit >= 0 AND credit >= 0", name="ck_ledger_line_nonnegative"),
        CheckConstraint("NOT (debit > 0 AND credit > 0)", name="ck_ledger_line_single_side"),
        CheckConstraint("debit + credit > 0", name="ck_ledger_line_nonzero"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    ledger_entry_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("financial_ledger_entries.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("financial_ledger_accounts.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ============================================================
# Account Balance (per period)
# ============================================================

class AccountBalance(Base):
    """Running balances per account per fiscal period."""
    __tablename__ = "financial_account_balances"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "account_id", "period_id",
            name="uq_account_balance_tenant_account_period",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("financial_ledger_accounts.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    period_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("financial_fiscal_periods.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, default=Decimal("0")
    )
    debit_total: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, default=Decimal("0")
    )
    credit_total: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, default=Decimal("0")
    )
    closing_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ============================================================
# Posting Rule
# ============================================================

class PostingRule(Base):
    """Maps business events to journal entry lines."""
    __tablename__ = "financial_posting_rules"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "event_type", "rule_name",
            name="uq_posting_rule_tenant_event_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    debit_account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    credit_account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_field: Mapped[str] = mapped_column(String(100), nullable=False)
    conditions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
