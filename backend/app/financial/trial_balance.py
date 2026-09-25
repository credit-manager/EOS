"""Trial Balance and Financial Reports."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .ledger import AccountBalance, FiscalPeriod, LedgerAccount, LedgerEntry, LedgerLine

_ZERO = Decimal("0.000001")


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


def get_trial_balance(
    db: Session,
    tenant_id: UUID,
    period_id: UUID | None = None,
    as_of_date: date | None = None,
    currency: str = "USD",
) -> dict:
    """Generate trial balance for a period or as of a date."""
    if period_id:
        period = db.get(FiscalPeriod, period_id)
        if period is None or period.tenant_id != tenant_id:
            raise ValueError("fiscal period not found")
        entry_filter = (
            LedgerEntry.period_id == period_id,
            LedgerEntry.status == "posted",
        )
    elif as_of_date:
        entry_filter = (
            LedgerEntry.entry_date <= as_of_date,
            LedgerEntry.status == "posted",
        )
    else:
        entry_filter = (LedgerEntry.status == "posted",)

    rows = db.execute(
        select(
            LedgerAccount.id,
            LedgerAccount.account_code,
            LedgerAccount.account_name,
            LedgerAccount.account_type,
            LedgerAccount.normal_balance,
            func.coalesce(func.sum(LedgerLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(LedgerLine.credit), 0).label("total_credit"),
        )
        .join(LedgerLine, LedgerLine.account_id == LedgerAccount.id)
        .join(LedgerEntry, LedgerEntry.id == LedgerLine.ledger_entry_id)
        .where(
            LedgerAccount.tenant_id == tenant_id,
            LedgerAccount.is_active.is_(True),
            LedgerEntry.tenant_id == tenant_id,
            *entry_filter,
        )
        .group_by(
            LedgerAccount.id,
            LedgerAccount.account_code,
            LedgerAccount.account_name,
            LedgerAccount.account_type,
            LedgerAccount.normal_balance,
        )
        .order_by(LedgerAccount.account_code)
    ).all()

    lines = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for account_id, code, name, account_type, normal_balance, debit, credit in rows:
        debit = _money(Decimal(str(debit or 0)))
        credit = _money(Decimal(str(credit or 0)))
        total_debit += debit
        total_credit += credit

        if normal_balance == "debit":
            balance = debit - credit
        else:
            balance = credit - debit

        lines.append({
            "account_id": account_id,
            "code": code,
            "name": name,
            "account_type": account_type,
            "normal_balance": normal_balance,
            "debit": debit,
            "credit": credit,
            "balance": _money(balance),
        })

    return {
        "currency": currency,
        "lines": lines,
        "total_debit": _money(total_debit),
        "total_credit": _money(total_credit),
        "is_balanced": _money(total_debit) == _money(total_credit),
    }


def get_balance_sheet(
    db: Session,
    tenant_id: UUID,
    as_of_date: date | None = None,
    currency: str = "USD",
) -> dict:
    """Generate balance sheet from ledger entries."""
    entry_filter = (LedgerEntry.status == "posted",)
    if as_of_date:
        entry_filter = (LedgerEntry.entry_date <= as_of_date, LedgerEntry.status == "posted")

    rows = db.execute(
        select(
            LedgerAccount.account_type,
            LedgerAccount.account_code,
            LedgerAccount.account_name,
            LedgerAccount.normal_balance,
            func.coalesce(func.sum(LedgerLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(LedgerLine.credit), 0).label("total_credit"),
        )
        .join(LedgerLine, LedgerLine.account_id == LedgerAccount.id)
        .join(LedgerEntry, LedgerEntry.id == LedgerLine.ledger_entry_id)
        .where(
            LedgerAccount.tenant_id == tenant_id,
            LedgerAccount.is_active.is_(True),
            LedgerEntry.tenant_id == tenant_id,
            LedgerAccount.account_type.in_(["asset", "liability", "equity"]),
            *entry_filter,
        )
        .group_by(
            LedgerAccount.account_type,
            LedgerAccount.account_code,
            LedgerAccount.account_name,
            LedgerAccount.normal_balance,
        )
        .order_by(LedgerAccount.account_code)
    ).all()

    assets = []
    liabilities = []
    equity = []
    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    total_equity = Decimal("0")

    for account_type, code, name, normal_balance, debit, credit in rows:
        debit = _money(Decimal(str(debit or 0)))
        credit = _money(Decimal(str(credit or 0)))

        if normal_balance == "debit":
            balance = debit - credit
        else:
            balance = credit - debit

        line = {"code": code, "name": name, "balance": _money(balance)}

        if account_type == "asset":
            total_assets += balance
            assets.append(line)
        elif account_type == "liability":
            total_liabilities += balance
            liabilities.append(line)
        elif account_type == "equity":
            total_equity += balance
            equity.append(line)

    return {
        "currency": currency,
        "assets": {"lines": assets, "total": _money(total_assets)},
        "liabilities": {"lines": liabilities, "total": _money(total_liabilities)},
        "equity": {"lines": equity, "total": _money(total_equity)},
        "total_liabilities_and_equity": _money(total_liabilities + total_equity),
        "is_balanced": _money(total_assets) == _money(total_liabilities + total_equity),
    }


def get_income_statement(
    db: Session,
    tenant_id: UUID,
    period_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    currency: str = "USD",
) -> dict:
    """Generate income statement (P&L) from ledger entries."""
    entry_filter = [LedgerEntry.status == "posted"]

    if period_id:
        period = db.get(FiscalPeriod, period_id)
        if period and period.tenant_id == tenant_id:
            entry_filter.append(LedgerEntry.period_id == period_id)
    if start_date:
        entry_filter.append(LedgerEntry.entry_date >= start_date)
    if end_date:
        entry_filter.append(LedgerEntry.entry_date <= end_date)

    rows = db.execute(
        select(
            LedgerAccount.account_type,
            LedgerAccount.account_code,
            LedgerAccount.account_name,
            LedgerAccount.normal_balance,
            func.coalesce(func.sum(LedgerLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(LedgerLine.credit), 0).label("total_credit"),
        )
        .join(LedgerLine, LedgerLine.account_id == LedgerAccount.id)
        .join(LedgerEntry, LedgerEntry.id == LedgerLine.ledger_entry_id)
        .where(
            LedgerAccount.tenant_id == tenant_id,
            LedgerAccount.is_active.is_(True),
            LedgerEntry.tenant_id == tenant_id,
            LedgerAccount.account_type.in_(["revenue", "expense"]),
            *entry_filter,
        )
        .group_by(
            LedgerAccount.account_type,
            LedgerAccount.account_code,
            LedgerAccount.account_name,
            LedgerAccount.normal_balance,
        )
        .order_by(LedgerAccount.account_code)
    ).all()

    revenue_lines = []
    expense_lines = []
    total_revenue = Decimal("0")
    total_expense = Decimal("0")

    for account_type, code, name, normal_balance, debit, credit in rows:
        debit = _money(Decimal(str(debit or 0)))
        credit = _money(Decimal(str(credit or 0)))

        if normal_balance == "credit":
            balance = credit - debit
        else:
            balance = debit - credit

        line = {"code": code, "name": name, "balance": _money(balance)}

        if account_type == "revenue":
            total_revenue += balance
            revenue_lines.append(line)
        else:
            total_expense += balance
            expense_lines.append(line)

    net_income = total_revenue - total_expense
    return {
        "currency": currency,
        "revenue": {"lines": revenue_lines, "total": _money(total_revenue)},
        "expense": {"lines": expense_lines, "total": _money(total_expense)},
        "gross_profit": _money(total_revenue),
        "net_income": _money(net_income),
    }


def get_account_balances(
    db: Session,
    tenant_id: UUID,
    period_id: UUID | None = None,
) -> list[dict]:
    """Get account balances, optionally filtered by period."""
    q = (
        select(AccountBalance, LedgerAccount)
        .join(LedgerAccount, LedgerAccount.id == AccountBalance.account_id)
        .where(
            AccountBalance.tenant_id == tenant_id,
            LedgerAccount.tenant_id == tenant_id,
        )
        .order_by(LedgerAccount.account_code)
    )
    if period_id:
        q = q.where(AccountBalance.period_id == period_id)

    results = db.execute(q).all()
    return [
        {
            "account_id": str(balance.account_id),
            "account_code": account.account_code,
            "account_name": account.account_name,
            "account_type": account.account_type,
            "period_id": str(balance.period_id),
            "opening_balance": _money(balance.opening_balance),
            "debit_total": _money(balance.debit_total),
            "credit_total": _money(balance.credit_total),
            "closing_balance": _money(balance.closing_balance),
        }
        for balance, account in results
    ]
