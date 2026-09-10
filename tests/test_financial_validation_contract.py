from decimal import Decimal

import pytest

from core.schemas import AccountCreate, JournalLineCreate


def test_journal_line_rejects_both_sides():
    with pytest.raises(ValueError, match="both debit and credit"):
        JournalLineCreate(account_id="a", debit=Decimal("1"), credit=Decimal("1"))


def test_journal_line_rejects_zero_sides():
    with pytest.raises(ValueError, match="non-zero"):
        JournalLineCreate(account_id="a", debit=Decimal("0"), credit=Decimal("0"))


def test_journal_line_accepts_exactly_one_side():
    debit = JournalLineCreate(account_id="a", debit=Decimal("10.25"), credit=Decimal("0"))
    credit = JournalLineCreate(account_id="a", debit=Decimal("0"), credit=Decimal("10.25"))
    assert debit.debit == Decimal("10.25")
    assert credit.credit == Decimal("10.25")


def test_account_opening_balance_uses_decimal():
    account = AccountCreate(code="1000", name_en="Cash", account_type="asset", opening_balance="10.25")
    assert account.opening_balance == Decimal("10.25")
