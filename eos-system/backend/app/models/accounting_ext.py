"""
EOS System — Extended Accounting Models (Periods, Cost Centers, Bank Accounts, Taxes, Reconciliation, Statements)
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base
from app.models.accounting import Account, JournalEntry


class AccountingPeriod(Base):
    """Fiscal/Accounting Period."""
    
    __tablename__ = "periods"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), default="open", index=True)  # open, closed
    is_adjustment = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
        }


class CostCenter(Base):
    """Cost Center for departmental accounting."""
    
    __tablename__ = "cost_centers"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    parent_id = Column(String(36), ForeignKey("cost_centers.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {"id": self.id, "code": self.code, "name": self.name}


class BankAccount(Base):
    """Bank Account for treasury management."""
    
    __tablename__ = "bank_accounts"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    bank_name = Column(String(255), nullable=False)
    bank_name_ar = Column(String(255))
    account_number = Column(String(100), nullable=False)
    iban = Column(String(50))
    swift_code = Column(String(20))
    currency = Column(String(3), default="EGP")
    current_balance = Column(Numeric(18, 2), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    account = relationship("Account")
    
    def to_dict(self):
        return {
            "id": self.id,
            "bank_name": self.bank_name,
            "account_number": self.account_number,
            "currency": self.currency,
            "current_balance": float(self.current_balance) if self.current_balance else 0,
        }


class Tax(Base):
    """Tax configuration (VAT, WHT, etc.)."""
    
    __tablename__ = "taxes"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100))
    rate = Column(Numeric(5, 2), nullable=False)  # e.g. 14.00 for 14%
    tax_type = Column(String(50), nullable=False)  # vat, wht_sales, wht_purchase
    is_active = Column(Boolean, default=True)
    account_id = Column(String(36), ForeignKey("accounts.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    account = relationship("Account")
    
    def to_dict(self):
        return {"id": self.id, "name": self.name, "rate": float(self.rate), "tax_type": self.tax_type}


class BankReconciliation(Base):
    """Bank Reconciliation — matches bank statement lines with journal entries."""

    __tablename__ = "bank_reconciliations"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    bank_account_id = Column(String(36), ForeignKey("bank_accounts.id"), nullable=False, index=True)
    statement_date = Column(Date, nullable=False)
    statement_balance = Column(Numeric(18, 2), nullable=False)
    book_balance = Column(Numeric(18, 2), nullable=False)
    status = Column(String(20), default="draft", index=True)  # draft, reconciled, void
    notes = Column(Text)
    reconciled_by = Column(String(36), ForeignKey("users.id"))
    reconciled_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    bank_account = relationship("BankAccount")

    def to_dict(self):
        return {
            "id": self.id,
            "bank_account_id": self.bank_account_id,
            "statement_date": self.statement_date.isoformat() if self.statement_date else None,
            "statement_balance": float(self.statement_balance) if self.statement_balance else 0,
            "book_balance": float(self.book_balance) if self.book_balance else 0,
            "status": self.status,
        }


class BankReconciliationLine(Base):
    """Individual line in a bank reconciliation — links a statement line to a journal entry."""

    __tablename__ = "bank_reconciliation_lines"

    id = Column(String(36), primary_key=True)
    reconciliation_id = Column(String(36), ForeignKey("bank_reconciliations.id"), nullable=False, index=True)
    journal_entry_id = Column(String(36), ForeignKey("journal_entries.id"), index=True)
    statement_date = Column(Date, nullable=False)
    description = Column(String(500))
    amount = Column(Numeric(18, 2), nullable=False)
    is_matched = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    reconciliation = relationship("BankReconciliation")
    journal_entry = relationship("JournalEntry")


class AccountStatement(Base):
    """Account Statement — periodic closing/balance carry-forward."""

    __tablename__ = "account_statements"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    period_id = Column(String(36), ForeignKey("fiscal_years.id"), nullable=False, index=True)
    opening_balance = Column(Numeric(18, 2), default=0)
    closing_balance = Column(Numeric(18, 2), default=0)
    total_debit = Column(Numeric(18, 2), default=0)
    total_credit = Column(Numeric(18, 2), default=0)
    status = Column(String(20), default="draft", index=True)  # draft, posted, void
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account")
    period = relationship("FiscalYear")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "period_id": self.period_id,
            "opening_balance": float(self.opening_balance) if self.opening_balance else 0,
            "closing_balance": float(self.closing_balance) if self.closing_balance else 0,
            "total_debit": float(self.total_debit) if self.total_debit else 0,
            "total_credit": float(self.total_credit) if self.total_credit else 0,
            "status": self.status,
        }
