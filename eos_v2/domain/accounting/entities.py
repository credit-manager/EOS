from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


@dataclass(frozen=True, slots=True)
class Account:
    tenant_id: UUID
    code: str
    name: str
    account_type: AccountType
    id: UUID = field(default_factory=uuid4)
    active: bool = True

    def __post_init__(self) -> None:
        if not self.code or not self.code.strip():
            raise ValueError("Account code is required")
        if not self.name or not self.name.strip():
            raise ValueError("Account name is required")


@dataclass(frozen=True, slots=True)
class JournalLine:
    account_id: UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.debit < 0 or self.credit < 0:
            raise ValueError("Debit and credit must be non-negative")
        if self.debit > 0 and self.credit > 0:
            raise ValueError("A journal line cannot contain both debit and credit")
        if self.debit == 0 and self.credit == 0:
            raise ValueError("A journal line must contain a debit or credit")


@dataclass(frozen=True, slots=True)
class JournalEntry:
    tenant_id: UUID
    entry_date: date
    currency: str
    description: str
    lines: tuple[JournalLine, ...]
    id: UUID = field(default_factory=uuid4)
    posted: bool = False

    def __post_init__(self) -> None:
        currency = self.currency.upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("Currency must be a 3-letter ISO-style code")
        if not self.description.strip():
            raise ValueError("Journal description is required")
        if len(self.lines) < 2:
            raise ValueError("A journal entry requires at least two lines")
        debit = sum((line.debit for line in self.lines), Decimal("0"))
        credit = sum((line.credit for line in self.lines), Decimal("0"))
        if debit != credit:
            raise ValueError(f"Unbalanced journal entry: debit={debit} credit={credit}")
