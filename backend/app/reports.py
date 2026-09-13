import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .financial.models import Account, JournalEntry, JournalLine

logger = logging.getLogger("2to-eos.reports")


def get_financial_summary(
    db: Session,
    *,
    tenant_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    query = select(JournalEntry).where(JournalEntry.tenant_id == tenant_id)
    
    if start_date:
        query = query.where(JournalEntry.entry_date >= start_date)
    if end_date:
        query = query.where(JournalEntry.entry_date <= end_date)
    
    entries = list(db.scalars(query).all())
    
    total_debits = Decimal("0")
    total_credits = Decimal("0")
    
    for entry in entries:
        for line in entry.lines:
            if line.debit:
                total_debits += line.debit
            if line.credit:
                total_credits += line.credit
    
    return {
        "total_entries": len(entries),
        "total_debits": float(total_debits),
        "total_credits": float(total_credits),
        "net_balance": float(total_debits - total_credits),
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
    }


def get_account_balances(
    db: Session,
    *,
    tenant_id: UUID,
) -> list[dict]:
    accounts = db.scalars(
        select(Account).where(Account.tenant_id == tenant_id)
    ).all()
    
    result = []
    for account in accounts:
        lines = db.scalars(
            select(JournalLine).join(JournalEntry).where(
                JournalEntry.tenant_id == tenant_id,
                JournalLine.account_id == account.id,
            )
        ).all()
        
        total_debits = sum(float(line.debit or 0) for line in lines)
        total_credits = sum(float(line.credit or 0) for line in lines)
        balance = total_debits - total_credits
        
        result.append({
            "account_id": str(account.id),
            "account_code": account.code,
            "account_name": account.name,
            "account_type": account.account_type,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "balance": balance,
        })
    
    return result


def get_profit_loss_report(
    db: Session,
    *,
    tenant_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    accounts = db.scalars(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.account_type.in_(["revenue", "expense"]),
        )
    ).all()
    
    revenue_total = Decimal("0")
    expense_total = Decimal("0")
    revenue_details = []
    expense_details = []
    
    for account in accounts:
        query = (
            select(JournalLine)
            .join(JournalEntry)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalLine.account_id == account.id,
            )
        )
        
        if start_date:
            query = query.where(JournalEntry.entry_date >= start_date)
        if end_date:
            query = query.where(JournalEntry.entry_date <= end_date)
        
        lines = list(db.scalars(query).all())
        
        account_debits = sum(float(line.debit or 0) for line in lines)
        account_credits = sum(float(line.credit or 0) for line in lines)
        
        detail = {
            "account_code": account.code,
            "account_name": account.name,
            "debits": account_debits,
            "credits": account_credits,
            "net": account_credits - account_debits if account.account_type == "revenue" else account_debits - account_credits,
        }
        
        if account.account_type == "revenue":
            revenue_total += Decimal(str(detail["net"]))
            revenue_details.append(detail)
        else:
            expense_total += Decimal(str(detail["net"]))
            expense_details.append(detail)
    
    net_income = revenue_total - expense_total
    
    return {
        "revenue": {
            "total": float(revenue_total),
            "details": revenue_details,
        },
        "expenses": {
            "total": float(expense_total),
            "details": expense_details,
        },
        "net_income": float(net_income),
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
    }


def get_trial_balance(
    db: Session,
    *,
    tenant_id: UUID,
    as_of_date: datetime | None = None,
) -> dict:
    accounts = db.scalars(
        select(Account).where(Account.tenant_id == tenant_id)
    ).all()
    
    balances = []
    total_debits = Decimal("0")
    total_credits = Decimal("0")
    
    for account in accounts:
        query = (
            select(JournalLine)
            .join(JournalEntry)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalLine.account_id == account.id,
            )
        )
        
        if as_of_date:
            query = query.where(JournalEntry.entry_date <= as_of_date)
        
        lines = list(db.scalars(query).all())
        
        account_debits = Decimal(str(sum(float(line.debit or 0) for line in lines)))
        account_credits = Decimal(str(sum(float(line.credit or 0) for line in lines)))
        
        if account_debits != 0 or account_credits != 0:
            balances.append({
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.account_type,
                "debit": float(account_debits),
                "credit": float(account_credits),
            })
            total_debits += account_debits
            total_credits += account_credits
    
    return {
        "balances": balances,
        "total_debits": float(total_debits),
        "total_credits": float(total_credits),
        "is_balanced": total_debits == total_credits,
        "as_of_date": as_of_date.isoformat() if as_of_date else None,
    }


def get_dashboard_stats(
    db: Session,
    *,
    tenant_id: UUID,
) -> dict:
    from .construction.models import Project
    
    project_count = db.scalar(
        select(func.count()).where(Project.tenant_id == tenant_id)
    ) or 0
    
    active_projects = db.scalar(
        select(func.count()).where(
            Project.tenant_id == tenant_id,
            Project.status.in_(["active", "in_progress"]),
        )
    ) or 0
    
    account_count = db.scalar(
        select(func.count()).where(Account.tenant_id == tenant_id)
    ) or 0
    
    entry_count = db.scalar(
        select(func.count()).where(JournalEntry.tenant_id == tenant_id)
    ) or 0
    
    total_budget = db.scalar(
        select(func.coalesce(func.sum(Project.budget), 0)).where(
            Project.tenant_id == tenant_id
        )
    ) or 0
    
    return {
        "total_projects": project_count,
        "active_projects": active_projects,
        "total_accounts": account_count,
        "total_entries": entry_count,
        "total_budget": float(total_budget),
    }
