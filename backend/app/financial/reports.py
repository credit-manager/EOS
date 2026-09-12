"""Financial reporting: Balance Sheet, Income Statement, Cash Flow.

All reports operate on posted journal entries only and are tenant-scoped.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Account, JournalEntry, JournalLine

_ZERO = Decimal("0.000000")


def _account_balances(
    db: Session, tenant_id, *, currency: str = "USD", as_of: date | None = None
) -> list[dict]:
    """Get net balance per account (debit - credit) for posted entries."""
    stmt = (
        select(
            Account.id,
            Account.code,
            Account.name,
            Account.account_type,
            func.coalesce(func.sum(JournalLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            Account.tenant_id == tenant_id,
            Account.currency == currency,
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.currency == currency,
            JournalEntry.status == "posted",
        )
    )
    if as_of is not None:
        stmt = stmt.where(JournalEntry.accounting_date <= as_of)
    stmt = stmt.group_by(
        Account.id, Account.code, Account.name, Account.account_type
    ).order_by(Account.code)
    rows = db.execute(stmt).all()
    results = []
    for account_id, code, name, account_type, total_debit, total_credit in rows:
        total_debit = Decimal(str(total_debit or 0))
        total_credit = Decimal(str(total_credit or 0))
        balance = total_debit - total_credit
        results.append(
            {
                "account_id": account_id,
                "code": code,
                "name": name,
                "account_type": account_type,
                "debit": total_debit,
                "credit": total_credit,
                "balance": balance,
            }
        )
    return results


def balance_sheet(
    db: Session, tenant_id, *, currency: str = "USD", as_of: date | None = None
) -> dict:
    """Generate Balance Sheet: Assets = Liabilities + Equity.

    Balance sheet is a point-in-time snapshot. Assets carry debit balance,
    liabilities and equity carry credit balance.
    """
    balances = _account_balances(db, tenant_id, currency=currency, as_of=as_of)

    assets = []
    liabilities = []
    equity = []

    for b in balances:
        line = {
            "account_id": b["account_id"],
            "code": b["code"],
            "name": b["name"],
            "amount": b["balance"],
        }
        if b["account_type"] == "asset":
            assets.append(line)
        elif b["account_type"] == "liability":
            liabilities.append(line)
        elif b["account_type"] == "equity":
            equity.append(line)

    total_assets = sum((a["amount"] for a in assets), _ZERO)
    total_liabilities = sum((liab["amount"] for liab in liabilities), _ZERO)
    total_equity = sum((eq["amount"] for eq in equity), _ZERO)

    return {
        "currency": currency,
        "as_of": as_of.isoformat() if as_of else None,
        "assets": {"lines": assets, "total": total_assets},
        "liabilities": {"lines": liabilities, "total": total_liabilities},
        "equity": {"lines": equity, "total": total_equity},
        "total_liabilities_and_equity": total_liabilities + total_equity,
    }


def income_statement(
    db: Session, tenant_id, *, currency: str = "USD",
    period_start: date | None = None, period_end: date | None = None,
) -> dict:
    """Generate Income Statement (P&L): Revenue - Expenses = Net Income.

    Revenue is credit balance, expense is debit balance.
    """
    balances = _account_balances(db, tenant_id, currency=currency, as_of=period_end)

    revenue_lines = []
    expense_lines = []

    for b in balances:
        if b["account_type"] == "revenue":
            # Revenue: credit balance is positive income
            amount = -b["balance"] if b["balance"] < 0 else b["balance"]
            revenue_lines.append({
                "account_id": b["account_id"],
                "code": b["code"],
                "name": b["name"],
                "amount": amount,
            })
        elif b["account_type"] == "expense":
            expense_lines.append({
                "account_id": b["account_id"],
                "code": b["code"],
                "name": b["name"],
                "amount": b["balance"],
            })

    total_revenue = sum((r["amount"] for r in revenue_lines), _ZERO)
    total_expenses = sum((e["amount"] for e in expense_lines), _ZERO)
    net_income = total_revenue - total_expenses

    return {
        "currency": currency,
        "period_start": period_start.isoformat() if period_start else None,
        "period_end": period_end.isoformat() if period_end else None,
        "revenue": {"lines": revenue_lines, "total": total_revenue},
        "expenses": {"lines": expense_lines, "total": total_expenses},
        "net_income": net_income,
    }


def cash_flow(
    db: Session, tenant_id, *, currency: str = "USD",
    period_start: date | None = None, period_end: date | None = None,
) -> dict:
    """Generate Cash Flow Statement grouped by activity type.

    Classification heuristic based on account code prefixes:
    - 1xxx/asset = Operating (cash, receivables)
    - 2xxx/liability = Financing (payables, loans)
    - 3xxx/equity = Financing
    - 4xxx/revenue = Operating
    - 5xxx/expense = Operating
    """
    balances = _account_balances(db, tenant_id, currency=currency, as_of=period_end)

    operating = []
    investing = []
    financing = []

    for b in balances:
        line = {
            "account_id": b["account_id"],
            "code": b["code"],
            "name": b["name"],
            "amount": b["balance"],
        }
        if b["account_type"] in {"revenue", "expense"}:
            operating.append(line)
        elif b["account_type"] == "asset":
            if b["code"].startswith("1"):
                operating.append(line)
            else:
                investing.append(line)
        elif b["account_type"] == "liability":
            financing.append(line)
        elif b["account_type"] == "equity":
            financing.append(line)

    total_operating = sum((o["amount"] for o in operating), _ZERO)
    total_investing = sum((i["amount"] for i in investing), _ZERO)
    total_financing = sum((f["amount"] for f in financing), _ZERO)

    return {
        "currency": currency,
        "period_start": period_start.isoformat() if period_start else None,
        "period_end": period_end.isoformat() if period_end else None,
        "operating": {"lines": operating, "total": total_operating},
        "investing": {"lines": investing, "total": total_investing},
        "financing": {"lines": financing, "total": total_financing},
        "net_change_in_cash": total_operating + total_investing + total_financing,
    }
