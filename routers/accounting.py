"""P22 Accounting Engine Router — tenant-scoped financial operations."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.accounting_engine import AccountingEngine
from core.auth import get_current_user, require_permission
from core.financial_reporting import FinancialReportingEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Accounting Engine"])


def _tenant(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(401, detail={"status":"error","error":{"code":"TENANT_REQUIRED","message":"Authenticated tenant is required"}})
    return tenant_id


def _assert_period_open(db: Session, tenant_id: str, company_id: str, entry_date: str) -> None:
    try:
        parsed = date.fromisoformat(entry_date)
    except ValueError as exc:
        raise HTTPException(400, detail={"status":"error","error":{"code":"INVALID_DATE","message":"entry_date must be YYYY-MM-DD"}}) from exc
    row = db.execute(text("SELECT status FROM dbp_fiscal_periods WHERE tenant_id=:tid AND company_id=:cid AND :ed BETWEEN start_date AND end_date ORDER BY start_date DESC LIMIT 1"), {"tid":tenant_id,"cid":company_id,"ed":parsed}).fetchone()
    if row and row[0] != "open":
        raise HTTPException(409, detail={"status":"error","error":{"code":"FISCAL_PERIOD_CLOSED","message":"The journal date falls in a closed fiscal period"}})


def _report_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError): return HTTPException(404, detail={"status":"error","error":{"code":"NOT_FOUND","message":str(exc)}})
    return HTTPException(400, detail={"status":"error","error":{"code":"INVALID","message":str(exc)}})


@router.get("/companies/{company_id}/accounts", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_accounts(company_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status":"success","data":AccountingEngine(db).get_accounts(company_id,_tenant(user))}


@router.get("/companies/{company_id}/accounts/tree", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_account_tree(company_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status":"success","data":AccountingEngine(db).get_account_tree(company_id,_tenant(user))}


@router.post("/companies/{company_id}/accounts", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_account(company_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("code") or not body.get("name_en") or not body.get("account_type"): raise HTTPException(400, detail={"status":"error","error":{"code":"MISSING","message":"code, name_en, account_type required"}})
    aid=AccountingEngine(db).create_account(_tenant(user),company_id,body["code"],body["name_en"],body["account_type"],parent_id=body.get("parent_id"),name_ar=body.get("name_ar"),opening_balance=body.get("opening_balance",0),currency_code=body.get("currency_code","SAR"),description=body.get("description"))
    if not aid: raise HTTPException(409, detail={"status":"error","error":{"code":"DUPLICATE","message":"Account code already exists or invalid input"}})
    db.commit(); return {"status":"success","data":{"id":aid}}


@router.get("/companies/{company_id}/journal-entries", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_journal_entries(company_id: str, status: str | None = None, limit: int = Query(50,ge=1,le=500), offset: int = Query(0,ge=0), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status":"success","data":AccountingEngine(db).list_journal_entries(company_id,_tenant(user),status=status,limit=limit,offset=offset)}


@router.post("/companies/{company_id}/journal-entries", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_journal_entry(company_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("entry_date") or not body.get("entry_type"): raise HTTPException(400, detail={"status":"error","error":{"code":"MISSING","message":"entry_date and entry_type required"}})
    tid=_tenant(user); _assert_period_open(db,tid,company_id,body["entry_date"])
    jeid=AccountingEngine(db).create_journal_entry(tid,company_id,body["entry_date"],body["entry_type"],description=body.get("description"),reference=body.get("reference"),fiscal_year_id=body.get("fiscal_year_id"),created_by=user.get("id") or user.get("user_id"))
    if not jeid: raise HTTPException(400, detail={"status":"error","error":{"code":"INVALID","message":"Invalid entry type"}})
    db.commit(); return {"status":"success","data":{"id":jeid}}


@router.get("/journal-entries/{je_id}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_journal_entry(je_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    entry=AccountingEngine(db).get_journal_entry(je_id,_tenant(user))
    if not entry: raise HTTPException(404, detail={"status":"error","error":{"code":"NOT_FOUND","message":"Journal entry not found"}})
    return {"status":"success","data":entry}


@router.post("/journal-entries/{je_id}/lines", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_journal_line(je_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("account_id"): raise HTTPException(400, detail={"status":"error","error":{"code":"MISSING","message":"account_id required"}})
    lid=AccountingEngine(db).add_journal_line(je_id,body["account_id"],_tenant(user),debit=body.get("debit",0),credit=body.get("credit",0),description=body.get("description"),cost_center_id=body.get("cost_center_id"))
    if not lid: raise HTTPException(400, detail={"status":"error","error":{"code":"INVALID","message":"Exactly one of debit or credit must be positive"}})
    db.commit(); return {"status":"success","data":{"id":lid}}


@router.post("/journal-entries/{je_id}/post", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def post_journal_entry(je_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid=_tenant(user); result=AccountingEngine(db).post_journal_entry(je_id,tid)
    if not result["success"]: raise HTTPException(400, detail={"status":"error","error":{"code":"POST_FAILED","message":result["error"]}})
    db.commit(); return {"status":"success","data":result}


@router.get("/companies/{company_id}/trial-balance", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_trial_balance(company_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status":"success","data":AccountingEngine(db).get_trial_balance(company_id,_tenant(user))}


@router.get("/companies/{company_id}/financials/income-statement", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def income_statement(company_id: str,start_date: str,end_date: str,user: dict=Depends(get_current_user),db: Session=Depends(get_db)):
    try: return {"status":"success","data":FinancialReportingEngine(db).income_statement(_tenant(user),company_id,start_date,end_date)}
    except (ValueError,LookupError) as exc: raise _report_error(exc) from exc


@router.get("/companies/{company_id}/financials/balance-sheet", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def balance_sheet(company_id: str,as_of: str,user: dict=Depends(get_current_user),db: Session=Depends(get_db)):
    try: return {"status":"success","data":FinancialReportingEngine(db).balance_sheet(_tenant(user),company_id,as_of)}
    except (ValueError,LookupError) as exc: raise _report_error(exc) from exc


@router.post("/companies/{company_id}/fiscal-periods", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_fiscal_period(company_id: str,body: dict,user: dict=Depends(get_current_user),db: Session=Depends(get_db)):
    try: period_id=FinancialReportingEngine(db).create_period(_tenant(user),company_id,body["period_code"],body["start_date"],body["end_date"]); return {"status":"success","data":{"id":period_id}}
    except (KeyError,ValueError,LookupError) as exc: raise _report_error(exc) from exc


@router.post("/companies/{company_id}/fiscal-periods/{period_id}/close", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def close_fiscal_period(company_id: str,period_id: str,user: dict=Depends(get_current_user),db: Session=Depends(get_db)):
    try: return {"status":"success","data":FinancialReportingEngine(db).close_period(_tenant(user),company_id,period_id,user.get("id") or user.get("user_id"))}
    except (ValueError,LookupError) as exc: raise _report_error(exc) from exc
