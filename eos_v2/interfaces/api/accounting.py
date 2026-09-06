from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from eos_v2.application.accounting.service import AccountingService
from eos_v2.domain.accounting.entities import Account, AccountType, JournalEntry, JournalLine
from eos_v2.domain.permissions.policy import Permission
from eos_v2.infrastructure.db.accounting_repository import SqlAlchemyAccountingRepository
from eos_v2.interfaces.api.auth import get_current_identity, require_permission

router = APIRouter(prefix="/api/v1/accounting", tags=["accounting"])


class AccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    account_type: AccountType


class AccountResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    account_type: AccountType
    active: bool


class JournalLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: UUID
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


class JournalEntryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry_date: date
    currency: str = Field(min_length=3, max_length=3)
    description: str = Field(min_length=1, max_length=500)
    lines: list[JournalLineRequest] = Field(min_length=2)


class JournalEntryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    entry_date: date
    currency: str
    description: str
    posted: bool


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountRequest, request: Request, identity=Depends(get_current_identity)) -> AccountResponse:
    require_permission(identity, Permission.ADMIN)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    account = Account(
        tenant_id=identity.tenant.id,
        code=payload.code,
        name=payload.name,
        account_type=payload.account_type,
    )
    with database.session() as session:
        repository = SqlAlchemyAccountingRepository(session)
        try:
            repository.add_account(account)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="Account code already exists") from exc
    return AccountResponse(
        id=account.id, tenant_id=account.tenant_id, code=account.code,
        name=account.name, account_type=account.account_type, active=account.active,
    )


@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
def post_journal_entry(payload: JournalEntryRequest, request: Request, identity=Depends(get_current_identity)) -> JournalEntryResponse:
    require_permission(identity, Permission.WRITE)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        entry = JournalEntry(
            tenant_id=identity.tenant.id,
            entry_date=payload.entry_date,
            currency=payload.currency,
            description=payload.description,
            lines=tuple(JournalLine(line.account_id, line.debit, line.credit) for line in payload.lines),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with database.session() as session:
        try:
            posted = AccountingService(SqlAlchemyAccountingRepository(session)).post(entry)
            session.commit()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Accounting account not found") from exc
        except (PermissionError, ValueError) as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JournalEntryResponse(
        id=posted.id, tenant_id=posted.tenant_id, entry_date=posted.entry_date,
        currency=posted.currency, description=posted.description, posted=posted.posted,
    )
