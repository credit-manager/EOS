from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.accounting.entities import Account, AccountType, JournalEntry
from eos_v2.infrastructure.db.accounting_models import AccountModel, JournalEntryModel, JournalLineModel


class SqlAlchemyAccountingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_account(self, account_id: UUID) -> Account:
        tenant_id = get_tenant_context().tenant_id
        model = self.session.scalar(select(AccountModel).where(
            AccountModel.id == account_id,
            AccountModel.tenant_id == tenant_id,
        ))
        if model is None:
            raise KeyError("Account not found")
        return Account(
            tenant_id=model.tenant_id,
            code=model.code,
            name=model.name,
            account_type=AccountType(model.account_type),
            id=model.id,
            active=model.active,
        )

    def add_account(self, account: Account) -> None:
        tenant_id = get_tenant_context().tenant_id
        if account.tenant_id != tenant_id:
            raise PermissionError("Account tenant does not match current tenant")
        self.session.add(AccountModel(
            id=account.id, tenant_id=tenant_id, code=account.code,
            name=account.name, account_type=account.account_type.value,
            active=account.active,
        ))

    def save_entry(self, entry: JournalEntry) -> None:
        tenant_id = get_tenant_context().tenant_id
        if entry.tenant_id != tenant_id:
            raise PermissionError("Entry tenant does not match current tenant")
        self.session.add(JournalEntryModel(
            id=entry.id, tenant_id=tenant_id, entry_date=entry.entry_date,
            currency=entry.currency, description=entry.description, posted=entry.posted,
        ))
        for line in entry.lines:
            self.session.add(JournalLineModel(
                tenant_id=tenant_id, journal_entry_id=entry.id,
                account_id=line.account_id, debit=line.debit, credit=line.credit,
            ))
