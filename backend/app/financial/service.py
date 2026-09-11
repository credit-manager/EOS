from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit.models import AuditEvent
from .models import Account, JournalEntry, JournalLine
from .schemas import JournalEntryCreate

_ZERO = Decimal("0.000000")


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"))


def _next_entry_number(db: Session, tenant_id: UUID) -> int:
    current = db.scalar(
        select(func.max(JournalEntry.entry_number)).where(JournalEntry.tenant_id == tenant_id)
    )
    return (current or 0) + 1


def _validate_lines(db: Session, payload: JournalEntryCreate, tenant_id: UUID) -> tuple[list[Account], Decimal]:
    debit_total = _money(sum((line.debit for line in payload.lines), _ZERO))
    credit_total = _money(sum((line.credit for line in payload.lines), _ZERO))
    if debit_total != credit_total or debit_total <= 0:
        raise HTTPException(status_code=422, detail="journal entry must be balanced and greater than zero")

    account_ids = [line.account_id for line in payload.lines]
    accounts = db.scalars(
        select(Account).where(Account.tenant_id == tenant_id, Account.id.in_(account_ids))
    ).all()
    account_map = {account.id: account for account in accounts}
    missing = [str(account_id) for account_id in account_ids if account_id not in account_map]
    if missing:
        raise HTTPException(status_code=404, detail=f"account(s) not found: {', '.join(missing)}")
    inactive = [str(account.id) for account in accounts if not account.is_active]
    if inactive:
        raise HTTPException(status_code=409, detail=f"inactive account(s): {', '.join(inactive)}")
    wrong_currency = [str(account.id) for account in accounts if account.currency != payload.currency]
    if wrong_currency:
        raise HTTPException(status_code=422, detail="all accounts must use the journal currency")
    return [account_map[account_id] for account_id in account_ids], debit_total


def _validate_persisted_lines(
    db: Session, entry: JournalEntry, lines: list[JournalLine], tenant_id: UUID
) -> None:
    account_ids = [line.account_id for line in lines]
    accounts = db.scalars(
        select(Account).where(Account.tenant_id == tenant_id, Account.id.in_(account_ids)).with_for_update()
    ).all()
    account_map = {account.id: account for account in accounts}
    if len(account_map) != len(set(account_ids)):
        raise HTTPException(status_code=409, detail="journal line references an invalid tenant account")
    inactive = [str(account.id) for account in accounts if not account.is_active]
    if inactive:
        raise HTTPException(status_code=409, detail=f"inactive account(s): {', '.join(inactive)}")
    wrong_currency = [str(account.id) for account in accounts if account.currency != entry.currency]
    if wrong_currency:
        raise HTTPException(status_code=422, detail="all journal accounts must use the journal currency")


def create_draft(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    payload: JournalEntryCreate,
    request_id: str | None,
) -> JournalEntry:
    accounts, _ = _validate_lines(db, payload, tenant_id)
    entry = JournalEntry(
        tenant_id=tenant_id,
        entry_number=_next_entry_number(db, tenant_id),
        accounting_date=payload.accounting_date,
        currency=payload.currency,
        description=payload.description,
        reference=payload.reference,
        status="draft",
        created_by=user_id,
    )
    db.add(entry)
    db.flush()
    account_by_id = {account.id: account for account in accounts}
    for index, line in enumerate(payload.lines, start=1):
        account = account_by_id[line.account_id]
        db.add(
            JournalLine(
                journal_entry_id=entry.id,
                account_id=account.id,
                line_number=index,
                description=line.description,
                debit=_money(line.debit),
                credit=_money(line.credit),
            )
        )
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            action="financial.journal.created",
            resource_type="journal_entry",
            resource_id=entry.id,
            request_id=request_id,
            details={"entry_number": entry.entry_number, "status": "draft"},
        )
    )
    return entry


def post_entry(
    db: Session, *, tenant_id: UUID, user_id: UUID, entry_id: UUID, request_id: str | None
) -> JournalEntry:
    entry = db.scalar(
        select(JournalEntry)
        .where(JournalEntry.id == entry_id, JournalEntry.tenant_id == tenant_id)
        .with_for_update()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="journal entry not found")
    if entry.status != "draft":
        raise HTTPException(status_code=409, detail="only draft journal entries can be posted")

    lines = db.scalars(
        select(JournalLine).where(JournalLine.journal_entry_id == entry.id).order_by(JournalLine.line_number)
    ).all()
    debit_total = _money(sum((line.debit for line in lines), _ZERO))
    credit_total = _money(sum((line.credit for line in lines), _ZERO))
    if len(lines) < 2 or debit_total != credit_total or debit_total <= 0:
        raise HTTPException(status_code=422, detail="journal entry is not balanced")
    _validate_persisted_lines(db, entry, lines, tenant_id)

    entry.status = "posted"
    entry.posted_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            action="financial.journal.posted",
            resource_type="journal_entry",
            resource_id=entry.id,
            request_id=request_id,
            details={
                "entry_number": entry.entry_number,
                "debit_total": str(debit_total),
                "currency": entry.currency,
            },
        )
    )
    db.flush()
    return entry


def commit_financial(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="financial write conflicted with another transaction") from exc
