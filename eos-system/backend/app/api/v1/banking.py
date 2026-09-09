"""
EOS System — Bank Reconciliation & Account Statements Router
"""
from fastapi import APIRouter, Depends, HTTPException, Request
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
from app.models.accounting_ext import (
    BankReconciliation, BankReconciliationLine, AccountStatement,
)

router = APIRouter()


# ─── Bank Reconciliation Schemas ──────────────────────────

class ReconciliationLineCreate(BaseModel):
    journal_entry_id: Optional[str] = None
    statement_date: date
    description: Optional[str] = None
    amount: Decimal


class ReconciliationCreate(BaseModel):
    bank_account_id: str
    statement_date: date
    statement_balance: Decimal
    book_balance: Decimal
    notes: Optional[str] = None
    lines: List[ReconciliationLineCreate] = []


class ReconciliationLineResponse(BaseModel):
    id: str
    journal_entry_id: Optional[str]
    statement_date: date
    description: Optional[str]
    amount: float
    is_matched: bool


class ReconciliationResponse(BaseModel):
    id: str
    bank_account_id: str
    statement_date: date
    statement_balance: float
    book_balance: float
    difference: float
    status: str
    notes: Optional[str]
    created_at: datetime


class ReconciliationListResponse(BaseModel):
    reconciliations: List[ReconciliationResponse]
    total: int


# ─── Account Statement Schemas ────────────────────────────

class StatementCreate(BaseModel):
    account_id: str
    period_id: str
    opening_balance: Decimal = Decimal("0")
    closing_balance: Decimal = Decimal("0")
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")
    notes: Optional[str] = None


class StatementResponse(BaseModel):
    id: str
    account_id: str
    period_id: str
    opening_balance: float
    closing_balance: float
    total_debit: float
    total_credit: float
    status: str
    notes: Optional[str]
    created_at: datetime


class StatementListResponse(BaseModel):
    statements: List[StatementResponse]
    total: int


# ─── BANK RECONCILIATIONS ────────────────────────────────

@router.get("/bank-reconciliations", response_model=ReconciliationListResponse)
async def list_reconciliations(
    bank_account_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    query = select(BankReconciliation)
    query = query.filter(BankReconciliation.tenant_id == current_user["tenant_id"])
    if bank_account_id:
        query = query.filter(BankReconciliation.bank_account_id == bank_account_id)
    if status:
        query = query.filter(BankReconciliation.status == status)
    query = query.order_by(BankReconciliation.created_at.desc())

    count_q = select(func.count(BankReconciliation.id)).filter(
        BankReconciliation.tenant_id == current_user["tenant_id"]
    )
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    recs = result.scalars().all()

    return ReconciliationListResponse(
        reconciliations=[
            ReconciliationResponse(
                id=r.id, bank_account_id=r.bank_account_id,
                statement_date=r.statement_date,
                statement_balance=float(r.statement_balance),
                book_balance=float(r.book_balance),
                difference=float(r.statement_balance) - float(r.book_balance),
                status=r.status, notes=r.notes, created_at=r.created_at,
            )
            for r in recs
        ],
        total=total,
    )


@router.post("/bank-reconciliations", response_model=ReconciliationResponse)
async def create_reconciliation(
    recon: ReconciliationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    new_recon = BankReconciliation(
        id=str(uuid.uuid4()), tenant_id=current_user["tenant_id"],
        bank_account_id=recon.bank_account_id,
        statement_date=recon.statement_date,
        statement_balance=recon.statement_balance,
        book_balance=recon.book_balance,
        status="draft", notes=recon.notes,
    )
    db.add(new_recon)
    await db.flush()

    for line in recon.lines:
        db.add(BankReconciliationLine(
            id=str(uuid.uuid4()), reconciliation_id=new_recon.id,
            journal_entry_id=line.journal_entry_id,
            statement_date=line.statement_date,
            description=line.description, amount=line.amount,
        ))
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="accounting",
        entity_type="BankReconciliation", entity_id=new_recon.id,
        entity_name=f"Recon {recon.statement_date}", request=request,
    )

    diff = float(recon.statement_balance) - float(recon.book_balance)
    return ReconciliationResponse(
        id=new_recon.id, bank_account_id=new_recon.bank_account_id,
        statement_date=new_recon.statement_date,
        statement_balance=float(new_recon.statement_balance),
        book_balance=float(new_recon.book_balance),
        difference=diff, status=new_recon.status,
        notes=new_recon.notes, created_at=new_recon.created_at,
    )


@router.post("/bank-reconciliations/{recon_id}/reconcile")
async def reconcile_bank(
    recon_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:update" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:update")

    result = await db.execute(
        select(BankReconciliation).filter(
            BankReconciliation.id == recon_id,
            BankReconciliation.tenant_id == current_user["tenant_id"],
        )
    )
    recon = result.scalar()
    if not recon:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    if recon.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft reconciliations can be reconciled")

    diff = float(recon.statement_balance) - float(recon.book_balance)
    if abs(diff) > 0.01:
        raise HTTPException(status_code=400, detail=f"Balance mismatch: {diff:.2f}")

    recon.status = "reconciled"
    recon.reconciled_by = current_user["id"]
    recon.reconciled_at = datetime.utcnow()
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="update", module="accounting",
        entity_type="BankReconciliation", entity_id=recon_id,
        entity_name=f"Reconciled", request=request,
    )

    return {"message": "Bank reconciled", "status": "reconciled"}


# ─── ACCOUNT STATEMENTS ───────────────────────────────────

@router.get("/account-statements", response_model=StatementListResponse)
async def list_statements(
    account_id: Optional[str] = None,
    period_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    query = select(AccountStatement)
    query = query.filter(AccountStatement.tenant_id == current_user["tenant_id"])
    if account_id:
        query = query.filter(AccountStatement.account_id == account_id)
    if period_id:
        query = query.filter(AccountStatement.period_id == period_id)

    count_q = select(func.count(AccountStatement.id)).filter(
        AccountStatement.tenant_id == current_user["tenant_id"]
    )
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    stmts = result.scalars().all()

    return StatementListResponse(
        statements=[
            StatementResponse(
                id=s.id, account_id=s.account_id, period_id=s.period_id,
                opening_balance=float(s.opening_balance),
                closing_balance=float(s.closing_balance),
                total_debit=float(s.total_debit),
                total_credit=float(s.total_credit),
                status=s.status, notes=s.notes, created_at=s.created_at,
            )
            for s in stmts
        ],
        total=total,
    )


@router.post("/account-statements", response_model=StatementResponse)
async def create_statement(
    stmt: StatementCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    new_stmt = AccountStatement(
        id=str(uuid.uuid4()), tenant_id=current_user["tenant_id"],
        account_id=stmt.account_id,
        period_id=stmt.period_id, opening_balance=stmt.opening_balance,
        closing_balance=stmt.closing_balance, total_debit=stmt.total_debit,
        total_credit=stmt.total_credit, status="draft", notes=stmt.notes,
    )
    db.add(new_stmt)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="accounting",
        entity_type="AccountStatement", entity_id=new_stmt.id,
        entity_name=f"Statement {stmt.period_id}", request=request,
    )

    return StatementResponse(
        id=new_stmt.id, account_id=new_stmt.account_id,
        period_id=new_stmt.period_id,
        opening_balance=float(new_stmt.opening_balance),
        closing_balance=float(new_stmt.closing_balance),
        total_debit=float(new_stmt.total_debit),
        total_credit=float(new_stmt.total_credit),
        status=new_stmt.status, notes=new_stmt.notes,
        created_at=new_stmt.created_at,
    )


@router.post("/account-statements/{stmt_id}/post")
async def post_statement(
    stmt_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:update" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:update")

    result = await db.execute(
        select(AccountStatement).filter(
            AccountStatement.id == stmt_id,
            AccountStatement.tenant_id == current_user["tenant_id"],
        )
    )
    stmt = result.scalar()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")
    if stmt.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft statements can be posted")

    stmt.status = "posted"
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="update", module="accounting",
        entity_type="AccountStatement", entity_id=stmt_id,
        entity_name="Posted", request=request,
    )

    return {"message": "Statement posted", "status": "posted"}
