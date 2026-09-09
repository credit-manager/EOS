"""
EOS System — Accounting Module Router (with RBAC + Audit)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.accounting import Account, JournalEntry, JournalEntryLine

router = APIRouter()


# Schemas
class AccountCreate(BaseModel):
    code: str
    name: str
    name_ar: str
    account_type: str
    parent_id: Optional[str] = None
    currency: str = "EGP"
    is_active: bool = True


class AccountResponse(BaseModel):
    id: str
    code: str
    name: str
    name_ar: str
    account_type: str
    parent_id: Optional[str]
    balance: float
    currency: str
    is_active: bool
    created_at: datetime


class AccountListResponse(BaseModel):
    accounts: List[AccountResponse]
    total: int


class JournalEntryCreate(BaseModel):
    entry_date: date
    description: str
    description_ar: Optional[str] = None
    lines: List["JournalEntryLineCreate"]
    reference: Optional[str] = None
    source_module: Optional[str] = None


class JournalEntryLineCreate(BaseModel):
    account_id: str
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    description: Optional[str] = None


class JournalEntryResponse(BaseModel):
    id: str
    entry_number: str
    entry_date: date
    description: str
    description_ar: Optional[str]
    total_debit: float
    total_credit: float
    status: str
    reference: Optional[str]
    source_module: Optional[str]
    created_at: datetime


class JournalEntryListResponse(BaseModel):
    entries: List[JournalEntryResponse]
    total: int


class TrialBalanceResponse(BaseModel):
    accounts: List[AccountResponse]
    total_debit: float
    total_credit: float
    as_of_date: date


async def generate_entry_number(db: AsyncSession) -> str:
    year = datetime.now().year
    result = await db.execute(
        select(func.count(JournalEntry.id))
        .filter(JournalEntry.entry_number.like(f"JE-{year}-%"))
    )
    count = result.scalar() or 0
    return f"JE-{year}-{count + 1:04d}"


# ─── ACCOUNTS ─────────────────────────────────────────────

@router.get("/accounts", response_model=AccountListResponse)
async def list_accounts(
    account_type: Optional[str] = None,
    parent_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    query = select(Account)
    if account_type:
        query = query.filter(Account.account_type == account_type)
    if parent_id:
        query = query.filter(Account.parent_id == parent_id)
    elif parent_id is None:
        query = query.filter(Account.parent_id.is_(None))
    if search:
        query = query.filter(
            (Account.name.ilike(f"%{search}%"))
            | (Account.name_ar.ilike(f"%{search}%"))
            | (Account.code.ilike(f"%{search}%"))
        )

    count_query = select(func.count(Account.id))
    if account_type:
        count_query = count_query.filter(Account.account_type == account_type)
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    accounts = result.scalars().all()

    return AccountListResponse(
        accounts=[
            AccountResponse(
                id=a.id, code=a.code, name=a.name, name_ar=a.name_ar,
                account_type=a.account_type, parent_id=a.parent_id,
                balance=float(a.balance) if a.balance else 0,
                currency=a.currency, is_active=a.is_active, created_at=a.created_at,
            )
            for a in accounts
        ],
        total=total,
    )


@router.post("/accounts", response_model=AccountResponse)
async def create_account(
    account: AccountCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    existing = await db.execute(select(Account).filter(Account.code == account.code))
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Account code already exists")

    new_account = Account(
        id=str(uuid.uuid4()), code=account.code, name=account.name,
        name_ar=account.name_ar, account_type=account.account_type,
        parent_id=account.parent_id, balance=Decimal("0.00"),
        currency=account.currency, is_active=account.is_active,
    )
    db.add(new_account)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="accounting",
        entity_type="Account", entity_id=new_account.id,
        entity_name=f"{new_account.code} - {new_account.name}",
        new_values=new_account.to_dict(), request=request,
    )

    return AccountResponse(
        id=new_account.id, code=new_account.code, name=new_account.name,
        name_ar=new_account.name_ar, account_type=new_account.account_type,
        parent_id=new_account.parent_id, balance=float(new_account.balance),
        currency=new_account.currency, is_active=new_account.is_active,
        created_at=new_account.created_at,
    )


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    result = await db.execute(select(Account).filter(Account.id == account_id))
    account = result.scalar()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return AccountResponse(
        id=account.id, code=account.code, name=account.name,
        name_ar=account.name_ar, account_type=account.account_type,
        parent_id=account.parent_id, balance=float(account.balance) if account.balance else 0,
        currency=account.currency, is_active=account.is_active,
        created_at=account.created_at,
    )


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    account: AccountCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:update" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:update")

    result = await db.execute(select(Account).filter(Account.id == account_id))
    existing = result.scalar()
    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")

    old_values = existing.to_dict()

    existing.name = account.name
    existing.name_ar = account.name_ar
    existing.account_type = account.account_type
    existing.parent_id = account.parent_id
    existing.is_active = account.is_active
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="update", module="accounting",
        entity_type="Account", entity_id=account_id,
        entity_name=f"{existing.code} - {existing.name}",
        old_values=old_values, new_values=existing.to_dict(), request=request,
    )

    return AccountResponse(
        id=existing.id, code=existing.code, name=existing.name,
        name_ar=existing.name_ar, account_type=existing.account_type,
        parent_id=existing.parent_id, balance=float(existing.balance) if existing.balance else 0,
        currency=existing.currency, is_active=existing.is_active,
        created_at=existing.created_at,
    )


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:delete" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:delete")

    result = await db.execute(select(Account).filter(Account.id == account_id))
    account = result.scalar()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    old_values = account.to_dict()

    await db.delete(account)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="delete", module="accounting",
        entity_type="Account", entity_id=account_id,
        old_values=old_values, request=request,
    )

    return {"message": "Account deleted"}


# ─── JOURNAL ENTRIES ──────────────────────────────────────

@router.get("/journal", response_model=JournalEntryListResponse)
async def list_journal_entries(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    query = select(JournalEntry)
    if start_date:
        query = query.filter(JournalEntry.entry_date >= start_date)
    if end_date:
        query = query.filter(JournalEntry.entry_date <= end_date)
    if status:
        query = query.filter(JournalEntry.status == status)
    query = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc())

    count_query = select(func.count(JournalEntry.id))
    if status:
        count_query = count_query.filter(JournalEntry.status == status)
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    entries = result.scalars().all()

    return JournalEntryListResponse(
        entries=[
            JournalEntryResponse(
                id=e.id, entry_number=e.entry_number, entry_date=e.entry_date,
                description=e.description, description_ar=e.description_ar,
                total_debit=float(e.total_debit), total_credit=float(e.total_credit),
                status=e.status, reference=e.reference, source_module=e.source_module,
                created_at=e.created_at,
            )
            for e in entries
        ],
        total=total,
    )


@router.post("/journal", response_model=JournalEntryResponse)
async def create_journal_entry(
    entry: JournalEntryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    total_debit = sum(line.debit for line in entry.lines)
    total_credit = sum(line.credit for line in entry.lines)

    if total_debit != total_credit:
        raise HTTPException(status_code=400, detail=f"Debit ({total_debit}) != Credit ({total_credit})")
    if total_debit == 0:
        raise HTTPException(status_code=400, detail="Debit and credit cannot be zero")

    entry_number = await generate_entry_number(db)

    new_entry = JournalEntry(
        id=str(uuid.uuid4()), entry_number=entry_number, entry_date=entry.entry_date,
        description=entry.description, description_ar=entry.description_ar,
        total_debit=total_debit, total_credit=total_credit, status="draft",
        reference=entry.reference, source_module=entry.source_module,
        created_by=current_user["id"],
    )
    db.add(new_entry)
    await db.flush()

    for line in entry.lines:
        new_line = JournalEntryLine(
            id=str(uuid.uuid4()), journal_entry_id=new_entry.id,
            account_id=line.account_id, debit=line.debit, credit=line.credit,
            description=line.description,
        )
        db.add(new_line)

    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="accounting",
        entity_type="JournalEntry", entity_id=new_entry.id,
        entity_name=entry_number, new_values=new_entry.to_dict(), request=request,
    )

    return JournalEntryResponse(
        id=new_entry.id, entry_number=new_entry.entry_number, entry_date=new_entry.entry_date,
        description=new_entry.description, description_ar=new_entry.description_ar,
        total_debit=float(new_entry.total_debit), total_credit=float(new_entry.total_credit),
        status=new_entry.status, reference=new_entry.reference,
        source_module=new_entry.source_module, created_at=new_entry.created_at,
    )


@router.post("/journal/{entry_id}/post")
async def post_journal_entry(
    entry_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:update" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:update")

    result = await db.execute(select(JournalEntry).filter(JournalEntry.id == entry_id))
    entry = result.scalar()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    if entry.status != "draft":
        raise HTTPException(status_code=400, detail=f"Cannot post entry with status: {entry.status}")

    old_status = entry.status

    lines_result = await db.execute(
        select(JournalEntryLine).filter(JournalEntryLine.journal_entry_id == entry_id)
    )
    lines = lines_result.scalars().all()

    for line in lines:
        account_result = await db.execute(select(Account).filter(Account.id == line.account_id))
        account = account_result.scalar()
        if account:
            if account.account_type in ["asset", "expense"]:
                account.balance = (account.balance or Decimal("0")) + line.debit - line.credit
            else:
                account.balance = (account.balance or Decimal("0")) + line.credit - line.debit

    entry.status = "posted"
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="update", module="accounting",
        entity_type="JournalEntry", entity_id=entry_id,
        entity_name=entry.entry_number,
        old_values={"status": old_status}, new_values={"status": "posted"},
        request=request,
    )

    return {"message": "Journal entry posted successfully", "entry_number": entry.entry_number}


# ─── REPORTS ──────────────────────────────────────────────

@router.get("/reports/trial-balance", response_model=TrialBalanceResponse)
async def get_trial_balance(
    as_of_date: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    result = await db.execute(select(Account).filter(Account.is_active == True).order_by(Account.code))
    accounts = result.scalars().all()

    total_debit = Decimal("0")
    total_credit = Decimal("0")
    account_responses = []

    for account in accounts:
        balance = account.balance or Decimal("0")
        if account.account_type in ["asset", "expense"]:
            debit = balance if balance >= 0 else Decimal("0")
            credit = abs(balance) if balance < 0 else Decimal("0")
        else:
            debit = abs(balance) if balance < 0 else Decimal("0")
            credit = balance if balance >= 0 else Decimal("0")

        total_debit += debit
        total_credit += credit

        account_responses.append(AccountResponse(
            id=account.id, code=account.code, name=account.name,
            name_ar=account.name_ar, account_type=account.account_type,
            parent_id=account.parent_id, balance=float(balance),
            currency=account.currency, is_active=account.is_active,
            created_at=account.created_at,
        ))

    return TrialBalanceResponse(
        accounts=account_responses, total_debit=float(total_debit),
        total_credit=float(total_credit), as_of_date=as_of_date,
    )


@router.get("/reports/income-statement")
async def get_income_statement(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    revenue_result = await db.execute(select(Account).filter(Account.account_type == "revenue"))
    revenue_accounts = revenue_result.scalars().all()

    expense_result = await db.execute(select(Account).filter(Account.account_type == "expense"))
    expense_accounts = expense_result.scalars().all()

    total_revenue = sum(acc.balance or Decimal("0") for acc in revenue_accounts)
    total_expenses = sum(acc.balance or Decimal("0") for acc in expense_accounts)

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_revenue": float(total_revenue),
        "total_expenses": float(total_expenses),
        "net_income": float(total_revenue - total_expenses),
    }


@router.get("/reports/balance-sheet")
async def get_balance_sheet(
    as_of_date: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    asset_result = await db.execute(select(Account).filter(Account.account_type == "asset"))
    asset_accounts = asset_result.scalars().all()

    liability_result = await db.execute(select(Account).filter(Account.account_type == "liability"))
    liability_accounts = liability_result.scalars().all()

    equity_result = await db.execute(select(Account).filter(Account.account_type == "equity"))
    equity_accounts = equity_result.scalars().all()

    total_assets = sum(acc.balance or Decimal("0") for acc in asset_accounts)
    total_liabilities = sum(acc.balance or Decimal("0") for acc in liability_accounts)
    total_equity = sum(acc.balance or Decimal("0") for acc in equity_accounts)

    return {
        "as_of_date": as_of_date.isoformat(),
        "total_assets": float(total_assets),
        "total_liabilities": float(total_liabilities),
        "total_equity": float(total_equity),
        "total_liabilities_and_equity": float(total_liabilities + total_equity),
    }
