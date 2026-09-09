from __future__ import annotations

from typing import Protocol
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.accounting.entities import Account, JournalEntry


class AccountingRepository(Protocol):
    def get_account(self, account_id: UUID) -> Account: ...
    def save_entry(self, entry: JournalEntry) -> None: ...


class AccountingService:
    def __init__(self, repository: AccountingRepository) -> None:
        self.repository = repository

    def post(self, entry: JournalEntry) -> JournalEntry:
        tenant_id = get_tenant_context().tenant_id
        if entry.tenant_id != tenant_id:
            raise PermissionError("Accounting tenant does not match current tenant")
        if entry.posted:
            raise ValueError("Journal entry is already posted")
        for line in entry.lines:
            account = self.repository.get_account(line.account_id)
            if account.tenant_id != tenant_id:
                raise PermissionError("Cross-tenant accounting account access denied")
            if not account.active:
                raise ValueError(f"Account is inactive: {account.code}")
        posted = JournalEntry(
            tenant_id=entry.tenant_id,
            entry_date=entry.entry_date,
            currency=entry.currency.upper(),
            description=entry.description,
            lines=entry.lines,
            id=entry.id,
            posted=True,
        )
        self.repository.save_entry(posted)
        return posted
