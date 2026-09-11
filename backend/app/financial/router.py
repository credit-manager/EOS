from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_admin
from .models import Account, JournalEntry, JournalLine
from .schemas import (
    AccountCreate,
    AccountResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    JournalLineResponse,
    TrialBalanceLine,
    TrialBalanceResponse,
)
from .service import commit_financial, create_draft, post_entry

router = APIRouter(prefix="/api/v1/financial", tags=["financial"])


@router.post("/accounts", response_model=AccountResponse, status_code=201)
def create_account(
    payload: AccountCreate,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Account:
    existing = db.scalar(select(Account).where(Account.tenant_id == tenant_id, Account.code == payload.code))
    if existing is not None:
        raise HTTPException(status_code=409, detail="account code already exists")
    account = Account(tenant_id=tenant_id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts(
    tenant_id: UUID = Depends(require_admin),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[Account]:
    query = select(Account).where(Account.tenant_id == tenant_id).order_by(Account.code)
    if active_only:
        query = query.where(Account.is_active.is_(True))
    return db.scalars(query).all()


@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=201)
def create_journal_entry(
    payload: JournalEntryCreate,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    entry = create_draft(
        db,
        tenant_id=tenant_id,
        user_id=request.state.user_id,
        payload=payload,
        request_id=request.state.request_id,
    )
    commit_financial(db)
    return _serialize_entry(db, entry)


@router.post("/journal-entries/{entry_id}/post", response_model=JournalEntryResponse)
def post_journal_entry(
    entry_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    entry = post_entry(
        db,
        tenant_id=tenant_id,
        user_id=request.state.user_id,
        entry_id=entry_id,
        request_id=request.state.request_id,
    )
    commit_financial(db)
    return _serialize_entry(db, entry)


@router.get("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
def get_journal_entry(
    entry_id: UUID,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    entry = db.scalar(select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.tenant_id == tenant_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="journal entry not found")
    return _serialize_entry(db, entry)


@router.get("/trial-balance", response_model=TrialBalanceResponse)
def trial_balance(
    tenant_id: UUID = Depends(require_admin),
    currency: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> TrialBalanceResponse:
    currency = currency.upper()
    rows = db.execute(
        select(
            Account.id,
            Account.code,
            Account.name,
            Account.account_type,
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
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
        .group_by(Account.id, Account.code, Account.name, Account.account_type)
        .order_by(Account.code)
    ).all()
    lines: list[TrialBalanceLine] = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for account_id, code, name, account_type, debit, credit in rows:
        debit = Decimal(debit or 0)
        credit = Decimal(credit or 0)
        total_debit += debit
        total_credit += credit
        lines.append(
            TrialBalanceLine(
                account_id=account_id,
                code=code,
                name=name,
                account_type=account_type,
                debit=debit,
                credit=credit,
                balance=debit - credit,
            )
        )
    return TrialBalanceResponse(
        currency=currency,
        lines=lines,
        total_debit=total_debit,
        total_credit=total_credit,
    )


def _serialize_entry(db: Session, entry: JournalEntry) -> JournalEntryResponse:
    lines = db.scalars(
        select(JournalLine).where(JournalLine.journal_entry_id == entry.id).order_by(JournalLine.line_number)
    ).all()
    return JournalEntryResponse(
        id=entry.id,
        tenant_id=entry.tenant_id,
        entry_number=entry.entry_number,
        accounting_date=entry.accounting_date,
        currency=entry.currency,
        description=entry.description,
        reference=entry.reference,
        status=entry.status,
        posted_at=entry.posted_at.isoformat() if entry.posted_at else None,
        lines=[
            JournalLineResponse(
                id=line.id,
                account_id=line.account_id,
                line_number=line.line_number,
                description=line.description,
                debit=line.debit,
                credit=line.credit,
            )
            for line in lines
        ],
    )
