"""
EOS System — Accounting Models
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Account(Base):
    """Chart of Accounts model."""
    
    __tablename__ = "accounts"
    
    id = Column(String(36), primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False, index=True)  # asset, liability, equity, revenue, expense
    parent_id = Column(String(36), ForeignKey("accounts.id"))
    balance = Column(Numeric(18, 2), default=0)
    currency = Column(String(3), default="EGP")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("Account", remote_side=[id], backref="children")
    journal_lines = relationship("JournalEntryLine", back_populates="account")
    
    def __repr__(self):
        return f"<Account {self.code} - {self.name}>"
    
    def to_dict(self, include_children=False):
        data = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "name_ar": self.name_ar,
            "account_type": self.account_type,
            "parent_id": self.parent_id,
            "balance": float(self.balance) if self.balance else 0,
            "currency": self.currency,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_children:
            data["children"] = [child.to_dict() for child in self.children]
        
        return data


class JournalEntry(Base):
    """Journal Entry model."""
    
    __tablename__ = "journal_entries"
    
    id = Column(String(36), primary_key=True)
    entry_number = Column(String(50), unique=True, nullable=False, index=True)
    entry_date = Column(Date, nullable=False, index=True)
    description = Column(String(500), nullable=False)
    description_ar = Column(String(500))
    total_debit = Column(Numeric(18, 2), nullable=False)
    total_credit = Column(Numeric(18, 2), nullable=False)
    status = Column(String(20), default="draft", index=True)  # draft, posted, reversed
    reference = Column(String(100))
    source_module = Column(String(50))
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lines = relationship("JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<JournalEntry {self.entry_number}>"
    
    def to_dict(self, include_lines=False):
        data = {
            "id": self.id,
            "entry_number": self.entry_number,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "description": self.description,
            "description_ar": self.description_ar,
            "total_debit": float(self.total_debit) if self.total_debit else 0,
            "total_credit": float(self.total_credit) if self.total_credit else 0,
            "status": self.status,
            "reference": self.reference,
            "source_module": self.source_module,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_lines:
            data["lines"] = [line.to_dict() for line in self.lines]
        
        return data
    
    def validate(self):
        """Validate that debit equals credit."""
        if self.total_debit != self.total_credit:
            raise ValueError("Total debit must equal total credit")
        return True


class JournalEntryLine(Base):
    """Journal Entry Line model."""
    
    __tablename__ = "journal_entry_lines"
    
    id = Column(String(36), primary_key=True)
    journal_entry_id = Column(String(36), ForeignKey("journal_entries.id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    debit = Column(Numeric(18, 2), default=0)
    credit = Column(Numeric(18, 2), default=0)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")
    
    def __repr__(self):
        return f"<JournalEntryLine {self.id}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "journal_entry_id": self.journal_entry_id,
            "account_id": self.account_id,
            "account_code": self.account.code if self.account else None,
            "account_name": self.account.name if self.account else None,
            "debit": float(self.debit) if self.debit else 0,
            "credit": float(self.credit) if self.credit else 0,
            "description": self.description,
        }
