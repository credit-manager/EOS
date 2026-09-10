from decimal import Decimal

from core.schemas import JournalLineCreate


def test_journal_line_rejects_both_sides():
    try:
        JournalLineCreate(account_id="a", debit=Decimal("1"), credit=Decimal("1"))
    except ValueError:
        return
    raise AssertionError("journal line must not contain both debit and credit")
