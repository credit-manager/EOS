from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.accounting.entities import JournalLine


@dataclass(frozen=True, slots=True)
class PostingInstruction:
    """Deterministic bridge from operational modules to double-entry accounting."""

    debit_account_id: UUID
    credit_account_id: UUID
    amount: Decimal
    source_module: str
    source_id: UUID

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Posting amount must be positive")
        if not self.source_module.strip():
            raise ValueError("Posting source module is required")

    def lines(self) -> tuple[JournalLine, JournalLine]:
        return (
            JournalLine(account_id=self.debit_account_id, debit=self.amount),
            JournalLine(account_id=self.credit_account_id, credit=self.amount),
        )

    def validate_tenant_context(self, tenant_id: UUID) -> None:
        if get_tenant_context().tenant_id != tenant_id:
            raise PermissionError("Accounting posting tenant mismatch")
