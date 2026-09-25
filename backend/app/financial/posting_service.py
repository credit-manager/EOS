"""Service for posting business events to the ledger."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.models import AuditEvent
from .ledger import (
    AccountBalance,
    FiscalPeriod,
    LedgerAccount,
    LedgerEntry,
    LedgerLine,
    PostingRule,
)

_ZERO = Decimal("0.000000")


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


def _next_entry_number(db: Session, tenant_id: UUID) -> int:
    from sqlalchemy import func

    current = db.scalar(
        select(func.max(LedgerEntry.entry_number)).where(LedgerEntry.tenant_id == tenant_id)
    )
    return (current or 0) + 1


def _get_open_period(db: Session, tenant_id: UUID, entry_date: date) -> FiscalPeriod | None:
    return db.scalar(
        select(FiscalPeriod).where(
            FiscalPeriod.tenant_id == tenant_id,
            FiscalPeriod.status == "open",
            FiscalPeriod.start_date <= entry_date,
            FiscalPeriod.end_date >= entry_date,
        )
    )


def _resolve_account(db: Session, tenant_id: UUID, account_code: str) -> LedgerAccount:
    account = db.scalar(
        select(LedgerAccount).where(
            LedgerAccount.tenant_id == tenant_id,
            LedgerAccount.account_code == account_code,
            LedgerAccount.is_active.is_(True),
        )
    )
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=f"account not found or inactive: {account_code}",
        )
    return account


def create_journal_entry(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    entry_date: date,
    description: str,
    lines: list[dict],
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    currency: str = "USD",
) -> LedgerEntry:
    """Create a draft journal entry with balanced debit/credit lines."""
    if len(lines) < 2:
        raise HTTPException(status_code=422, detail="journal entry requires at least 2 lines")

    debit_total = _money(sum(Decimal(str(l.get("debit", 0))) for l in lines))
    credit_total = _money(sum(Decimal(str(l.get("credit", 0))) for l in lines))
    if debit_total != credit_total or debit_total <= 0:
        raise HTTPException(
            status_code=422,
            detail="journal entry must be balanced (debits == credits) and greater than zero",
        )

    period = _get_open_period(db, tenant_id, entry_date)

    entry = LedgerEntry(
        tenant_id=tenant_id,
        entry_number=_next_entry_number(db, tenant_id),
        entry_date=entry_date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        currency=currency.upper(),
        status="draft",
        period_id=period.id if period else None,
        created_by=user_id,
    )
    db.add(entry)
    db.flush()

    for idx, line in enumerate(lines, start=1):
        db.add(LedgerLine(
            ledger_entry_id=entry.id,
            account_id=line["account_id"],
            line_number=idx,
            description=line.get("description"),
            debit=_money(Decimal(str(line.get("debit", 0)))),
            credit=_money(Decimal(str(line.get("credit", 0)))),
        ))

    db.flush()
    return entry


def post_entry(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    entry_id: UUID,
    request_id: str | None = None,
) -> LedgerEntry:
    """Post a draft journal entry, update account balances."""
    entry = db.scalar(
        select(LedgerEntry)
        .where(LedgerEntry.id == entry_id, LedgerEntry.tenant_id == tenant_id)
        .with_for_update()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="ledger entry not found")
    if entry.status != "draft":
        raise HTTPException(status_code=409, detail="only draft entries can be posted")

    lines = db.scalars(
        select(LedgerLine)
        .where(LedgerLine.ledger_entry_id == entry.id)
        .order_by(LedgerLine.line_number)
    ).all()

    debit_total = _money(sum(line.debit for line in lines))
    credit_total = _money(sum(line.credit for line in lines))
    if len(lines) < 2 or debit_total != credit_total or debit_total <= 0:
        raise HTTPException(status_code=422, detail="journal entry is not balanced")

    account_ids = {line.account_id for line in lines}
    accounts = db.scalars(
        select(LedgerAccount).where(
            LedgerAccount.tenant_id == tenant_id,
            LedgerAccount.id.in_(account_ids),
        )
    ).all()
    account_map = {a.id: a for a in accounts}

    for aid in account_ids:
        if aid not in account_map:
            raise HTTPException(status_code=409, detail="line references invalid account")
        if not account_map[aid].is_active:
            raise HTTPException(status_code=409, detail="line references inactive account")

    entry.status = "posted"
    entry.posted_by = user_id
    entry.posted_at = datetime.now(UTC)

    for line in lines:
        _update_account_balance(db, tenant_id, line.account_id, entry, line)

    db.add(AuditEvent(
        tenant_id=tenant_id,
        actor_id=user_id,
        action="financial.ledger.entry.posted",
        resource_type="ledger_entry",
        resource_id=entry.id,
        request_id=request_id,
        details={
            "entry_number": entry.entry_number,
            "debit_total": str(debit_total),
            "currency": entry.currency,
        },
    ))
    db.flush()
    return entry


def reverse_entry(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    entry_id: UUID,
    reason: str | None = None,
    request_id: str | None = None,
) -> LedgerEntry:
    """Reverse a posted journal entry by creating an opposite entry."""
    original = db.scalar(
        select(LedgerEntry)
        .where(LedgerEntry.id == entry_id, LedgerEntry.tenant_id == tenant_id)
        .with_for_update()
    )
    if original is None:
        raise HTTPException(status_code=404, detail="ledger entry not found")
    if original.status != "posted":
        raise HTTPException(status_code=409, detail="only posted entries can be reversed")

    original_lines = db.scalars(
        select(LedgerLine)
        .where(LedgerLine.ledger_entry_id == original.id)
        .order_by(LedgerLine.line_number)
    ).all()

    reversal_lines = []
    for line in original_lines:
        reversal_lines.append({
            "account_id": line.account_id,
            "description": f"Reversal: {line.description or ''}",
            "debit": float(line.credit),
            "credit": float(line.debit),
        })

    reversal_entry = create_journal_entry(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        entry_date=date.today(),
        description=reason or f"Reversal of entry #{original.entry_number}",
        lines=reversal_lines,
        reference_type="reversal",
        reference_id=original.id,
        currency=original.currency,
    )

    original.status = "reversed"
    original.reversed_by_entry_id = reversal_entry.id
    original.updated_at = datetime.now(UTC)

    reversal_entry.reference_type = "reversal"
    reversal_entry.reference_id = original.id

    db.add(AuditEvent(
        tenant_id=tenant_id,
        actor_id=user_id,
        action="financial.ledger.entry.reversed",
        resource_type="ledger_entry",
        resource_id=original.id,
        request_id=request_id,
        details={
            "original_entry_number": original.entry_number,
            "reversal_entry_number": reversal_entry.entry_number,
            "reason": reason,
        },
    ))
    db.flush()
    return reversal_entry


def _update_account_balance(
    db: Session,
    tenant_id: UUID,
    account_id: UUID,
    entry: LedgerEntry,
    line: LedgerLine,
) -> None:
    """Update the account balance for the posting period."""
    period = None
    if entry.period_id:
        period = db.get(FiscalPeriod, entry.period_id)
    if period is None:
        period = _get_open_period(db, tenant_id, entry.entry_date)

    if period is None:
        return

    balance = db.scalar(
        select(AccountBalance).where(
            AccountBalance.tenant_id == tenant_id,
            AccountBalance.account_id == account_id,
            AccountBalance.period_id == period.id,
        )
    )
    if balance is None:
        balance = AccountBalance(
            tenant_id=tenant_id,
            account_id=account_id,
            period_id=period.id,
            opening_balance=Decimal("0"),
            debit_total=Decimal("0"),
            credit_total=Decimal("0"),
            closing_balance=Decimal("0"),
        )
        db.add(balance)

    balance.debit_total = _money(balance.debit_total + line.debit)
    balance.credit_total = _money(balance.credit_total + line.credit)
    balance.closing_balance = _money(
        balance.opening_balance + balance.debit_total - balance.credit_total
    )


def process_event(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    event_type: str,
    event_data: dict,
    request_id: str | None = None,
) -> LedgerEntry:
    """Process a business event using posting rules to generate journal entries."""
    rules = db.scalars(
        select(PostingRule).where(
            PostingRule.tenant_id == tenant_id,
            PostingRule.event_type == event_type,
            PostingRule.is_active.is_(True),
        )
    ).all()

    if not rules:
        raise HTTPException(
            status_code=422,
            detail=f"no active posting rule for event: {event_type}",
        )

    entries = []
    for rule in rules:
        amount = Decimal(str(event_data.get(rule.amount_field, 0)))
        if amount <= 0:
            continue

        debit_account = _resolve_account(db, tenant_id, rule.debit_account_code)
        credit_account = _resolve_account(db, tenant_id, rule.credit_account_code)

        conditions = rule.conditions or {}
        for field, expected in conditions.items():
            if event_data.get(field) != expected:
                break
        else:
            entry = create_journal_entry(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                entry_date=date.today(),
                description=f"{event_type} - {rule.rule_name}",
                lines=[
                    {
                        "account_id": debit_account.id,
                        "description": f"Debit: {rule.rule_name}",
                        "debit": float(amount),
                        "credit": 0,
                    },
                    {
                        "account_id": credit_account.id,
                        "description": f"Credit: {rule.rule_name}",
                        "debit": 0,
                        "credit": float(amount),
                    },
                ],
                reference_type=event_type.split(".")[0],
                reference_id=event_data.get("id"),
                currency=debit_account.currency,
            )
            entry = post_entry(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                entry_id=entry.id,
                request_id=request_id,
            )
            entries.append(entry)

    if not entries:
        raise HTTPException(
            status_code=422,
            detail=f"no entries generated for event: {event_type}",
        )

    return entries[0] if len(entries) == 1 else entries
