"""
P22 Accounting Engine Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.accounting_engine import AccountingEngine
from core.auth import get_current_user, require_permission
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Accounting Engine"])


# ── CHART OF ACCOUNTS ──

@router.get("/companies/{company_id}/accounts", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_accounts(company_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": AccountingEngine(db).get_accounts(company_id, user.get("tenant_id"))}


@router.get("/companies/{company_id}/accounts/tree", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_account_tree(company_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": AccountingEngine(db).get_account_tree(company_id, user.get("tenant_id"))}


@router.post("/companies/{company_id}/accounts", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_account(company_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("code") or not body.get("name_en") or not body.get("account_type"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "code, name_en, account_type required"}})
    aid = AccountingEngine(db).create_account(user.get("tenant_id"), company_id, body["code"], body["name_en"],
                                              body["account_type"], parent_id=body.get("parent_id"),
                                              name_ar=body.get("name_ar"), opening_balance=body.get("opening_balance", 0))
    if not aid:
        raise HTTPException(409, detail={"status": "error", "error": {"code": "DUPLICATE", "message": "Account code already exists or invalid type"}})
    db.commit()
    return {"status": "success", "data": {"id": aid}}


# ── JOURNAL ENTRIES ──

@router.get("/companies/{company_id}/journal-entries", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_journal_entries(company_id: str, status: str | None = None,
                               limit: int | None=None, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": AccountingEngine(db).list_journal_entries(company_id, user.get("tenant_id"), status=status, limit=limit)}


@router.post("/companies/{company_id}/journal-entries", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_journal_entry(company_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("entry_date") or not body.get("entry_type"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "entry_date and entry_type required"}})
    jeid = AccountingEngine(db).create_journal_entry(
        user.get("tenant_id"), company_id, body["entry_date"], body["entry_type"],
        description=body.get("description"), reference=body.get("reference"),
        fiscal_year_id=body.get("fiscal_year_id"),
        created_by=user.get("id") or user.get("user_id"))
    if not jeid:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": "Invalid entry type"}})
    db.commit()
    return {"status": "success", "data": {"id": jeid}}


@router.get("/journal-entries/{je_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_journal_entry(je_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    entry = AccountingEngine(db).get_journal_entry(je_id, user.get("tenant_id"))
    if not entry:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Journal entry not found"}})
    return {"status": "success", "data": entry}


@router.post("/journal-entries/{je_id}/lines", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_journal_line(je_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("account_id"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "account_id required"}})
    lid = AccountingEngine(db).add_journal_line(
        je_id, body["account_id"], user.get("tenant_id"),
        debit=body.get("debit", 0), credit=body.get("credit", 0),
        description=body.get("description"), cost_center_id=body.get("cost_center_id"))
    if not lid:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": "Must specify debit or credit (non-zero)"}})
    db.commit()
    return {"status": "success", "data": {"id": lid}}


@router.post("/journal-entries/{je_id}/post", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def post_journal_entry(je_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    result = AccountingEngine(db).post_journal_entry(je_id, user.get("tenant_id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "POST_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


# ── TRIAL BALANCE ──

@router.get("/companies/{company_id}/trial-balance", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_trial_balance(company_id: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": AccountingEngine(db).get_trial_balance(company_id, user.get("tenant_id"))}
