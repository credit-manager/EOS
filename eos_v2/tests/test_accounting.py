from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.accounting.service import AccountingService
from eos_v2.domain.accounting.entities import Account, AccountType, JournalEntry, JournalLine


def test_journal_entry_requires_balanced_double_entry() -> None:
    tenant = uuid4()
    cash = uuid4()
    revenue = uuid4()
    entry = JournalEntry(
        tenant_id=tenant,
        entry_date=date(2026, 9, 6),
        currency="usd",
        description="Sale",
        lines=(JournalLine(cash, debit=Decimal("100")), JournalLine(revenue, credit=Decimal("100"))),
    )
    assert entry.currency == "usd"
    with pytest.raises(ValueError, match="Unbalanced"):
        JournalEntry(
            tenant_id=tenant,
            entry_date=date(2026, 9, 6),
            currency="USD",
            description="Broken",
            lines=(JournalLine(cash, debit=Decimal("100")), JournalLine(revenue, credit=Decimal("90"))),
        )


def test_accounting_posting_is_tenant_safe() -> None:
    tenant = uuid4()
    other_tenant = uuid4()
    cash = Account(tenant, "1000", "Cash", AccountType.ASSET)
    revenue = Account(tenant, "4000", "Revenue", AccountType.REVENUE)
    posted = []

    class Repo:
        def get_account(self, account_id):
            return {cash.id: cash, revenue.id: revenue}[account_id]
        def save_entry(self, entry):
            posted.append(entry)

    entry = JournalEntry(tenant, date(2026, 9, 6), "USD", "Sale", (JournalLine(cash.id, debit=Decimal("100")), JournalLine(revenue.id, credit=Decimal("100"))))
    token = set_tenant_context(TenantContext(tenant))
    try:
        result = AccountingService(Repo()).post(entry)
        assert result.posted is True
        assert posted == [result]
    finally:
        reset_tenant_context(token)

    foreign_entry = JournalEntry(other_tenant, date(2026, 9, 6), "USD", "Sale", (JournalLine(cash.id, debit=Decimal("100")), JournalLine(revenue.id, credit=Decimal("100"))))
    token = set_tenant_context(TenantContext(tenant))
    try:
        with pytest.raises(PermissionError, match="tenant"):
            AccountingService(Repo()).post(foreign_entry)
    finally:
        reset_tenant_context(token)
