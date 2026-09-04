"""
P23 Finance & Treasury Router
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.finance_engine import FinanceEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic", tags=["Finance & Treasury"])


@router.get("/companies/{cid}/bank-accounts", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_bank_accounts(cid: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": FinanceEngine(db).get_bank_accounts(cid, user.get("tenant_id"))}


@router.post("/companies/{cid}/bank-accounts", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_bank_account(cid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("account_name"):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "account_name required"}})
    bid = FinanceEngine(db).create_bank_account(user.get("tenant_id"), cid, body["account_name"],
                                                 bank_name=body.get("bank_name"), account_number=body.get("account_number"),
                                                 iban=body.get("iban"), currency_code=body.get("currency_code", "SAR"),
                                                 opening_balance=body.get("opening_balance", 0))
    db.commit()
    return {"status": "success", "data": {"id": bid}}


@router.get("/companies/{cid}/payments", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_payments(cid: str, payment_type: str | None = None, status: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": FinanceEngine(db).list_payments(cid, user.get("tenant_id"), payment_type=payment_type, status=status)}


@router.post("/companies/{cid}/payments", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_payment(cid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ("payment_type", "payment_date", "amount"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    pid = FinanceEngine(db).create_payment(user.get("tenant_id"), cid, body["payment_type"],
                                            body["payment_date"], body["amount"],
                                            bank_account_id=body.get("bank_account_id"),
                                            payee_name=body.get("payee_name"), payee_type=body.get("payee_type"),
                                            reference=body.get("reference"), description=body.get("description"),
                                            currency_code=body.get("currency_code"),
                                            cost_center_id=body.get("cost_center_id"))
    if not pid:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": "Invalid payment type or amount"}})
    db.commit()
    return {"status": "success", "data": {"id": pid}}


@router.post("/payments/{pid}/approve", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def approve_payment(pid: str, user: dict | None=None, db: Session = Depends(get_db)):
    result = FinanceEngine(db).approve_payment(pid, user.get("id") or user.get("user_id"), user.get("tenant_id"))
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "APPROVE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/exchange-rates", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_exchange_rate(from_currency: str | None=None, to_currency: str = Query(...), db: Session = Depends(get_db)):
    rate = FinanceEngine(db).get_exchange_rate(from_currency, to_currency)
    if not rate:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Exchange rate not found"}})
    return {"status": "success", "data": rate}


@router.post("/exchange-rates", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def set_exchange_rate(body: dict, db: Session = Depends(get_db)):
    for f in ("from_currency", "to_currency", "rate", "rate_date"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    rid = FinanceEngine(db).set_exchange_rate(body["from_currency"], body["to_currency"],
                                               body["rate"], body["rate_date"], source=body.get("source"))
    db.commit()
    return {"status": "success", "data": {"id": rid}}


@router.post("/convert", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def convert_amount(body: dict, db: Session = Depends(get_db)):
    result = FinanceEngine(db).convert_amount(body.get("amount", 0), body.get("from_currency", ""), body.get("to_currency", ""))
    if not result:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NO_RATE", "message": "Exchange rate not available"}})
    return {"status": "success", "data": result}


@router.get("/companies/{cid}/budgets", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_budgets(cid: str, fiscal_year_id: str | None = None, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": FinanceEngine(db).get_budgets(cid, user.get("tenant_id"), fiscal_year_id=fiscal_year_id)}


@router.get("/companies/{cid}/budgets/utilization", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def budget_utilization(cid: str, user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": FinanceEngine(db).get_budget_utilization(cid, user.get("tenant_id"))}


@router.post("/companies/{cid}/budgets", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_budget(cid: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    for f in ("account_id", "fiscal_year_id", "budget_amount"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    bid = FinanceEngine(db).create_budget(user.get("tenant_id"), cid, body["account_id"],
                                           body["fiscal_year_id"], body["budget_amount"],
                                           cost_center_id=body.get("cost_center_id"), period=body.get("period"))
    db.commit()
    return {"status": "success", "data": {"id": bid}}