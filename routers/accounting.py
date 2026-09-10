"""
P22 Accounting Engine Router
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.accounting_engine import AccountingEngine
from core.schemas import AccountCreate, JournalEntryCreate, JournalLineCreate

router = APIRouter(prefix="/api/v1/dynamic", tags=["Accounting Engine"])


@router.get("/companies/{company_id}/accounts", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_accounts(company_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": AccountingEngine(db).get_accounts(company_id, user.get("tenant_id"))}


@router.get("/companies/{company_id}/accounts/tree", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_account_tree(company_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": AccountingEngine(db).get_account_tree(company_id, user.get("tenant_id"))}


@router.post("/companies/{company_id}/accounts", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_account(company_id: str, body: AccountCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    name_en = body.name_en or body.name
    if not name_en:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "name_en or name is required"}})
    aid = AccountingEngine(db).create_account(
        user.get("tenant_id"), company_id, body.code, name_en, body.account_type,
        parent_id=body.parent_id, name_ar=body.name_ar, currency_code=body.currency_code,
        opening_balance=body.opening_balance, description=body.description,
    )
    if not aid:
        raise HTTPException(409, detail={"status": "error", "error": {"code": "DUPLICATE", "message": "Account code already exists or invalid type"}})
    db.commit()
    return {"status": "success", "data": {"id": aid}}


@router.get("/companies/{company_id}/journal-entries", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_journal_entries(company_id: str, status: Optional[str] = None,
                               limit: int = Query(50, ge=1, le=200), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": AccountingEngine(db).list_journal_entries(company_id, user.get("tenant_id"), status=status, limit=limit)}


@router.post("/companies/{company_id}/journal-entries", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_journal_entry(company_id: str, body: JournalEntryCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    jeid = AccountingEngine(db).create_journal_entry(
        user.get("tenant_id"), company_id, body.entry_date.isoformat(), body.entry_type,
        description=body.description, reference=body.reference,
        fiscal_year_id=body.fiscal_year_id,
        created_by=user.get("id") or user.get("user_id"),
    )
    if not jeid:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": "Invalid entry type"}})
    db.commit()
    return {"status": "success", "data": {"id": jeid}}


@router.get("/journal-entries/{je_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_journal_entry(je_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = AccountingEngine(db).get_journal_entry(je_id, user.get("tenant_id"))
    if not entry:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Journal entry not found"}})
    return {"status": "success", "data": entry}


@router.post("/journal-entries/{je_id}/lines", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_journal_line(je_id: str, body: JournalLineCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lid = AccountingEngine(db).add_journal_line(
        je_id, body.account_id, user.get("tenant_id"),
        debit=body.debit, credit=body.credit,
        description=body.description, cost_center_id=body.cost_center_id,
    )
    if not lid:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": "Must specify exactly one non-zero debit or credit"}})
    db.commit()
    return {"status": "success", "data": {"id": lid}}


@router.post("/journal-entries/{je_id}/post", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def post_journal_entry(je_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = AccountingEngine(db).post_journal_entry(je_id, user.get("tenant_id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "POST_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/companies/{company_id}/trial-balance", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_trial_balance(company_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": AccountingEngine(db).get_trial_balance(company_id, user.get("tenant_id"))}
