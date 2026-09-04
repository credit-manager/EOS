"""
P56 Billing Flow Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.billing_flow import BillingFlowEngine
from core.rate_limit import read_limiter, write_limiter
from database import get_db


def _err(sc, code, msg):
    return HTTPException(sc, detail={"status": "error", "error": {"code": code, "message": msg}})


router = APIRouter(prefix="/api/v1/dynamic/billing-flow", tags=["Billing Flow"])


@router.get("/plans", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def plans(db: Session = Depends(get_db)):
    return {"status": "success", "data": BillingFlowEngine(db).get_plan_catalog()}


@router.post("/checkout", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def checkout(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    plan_code = body.get("plan_code")
    if not plan_code:
        raise _err(400, "MISSING", "plan_code required")
    result = BillingFlowEngine(db).checkout(
        user.get("tenant_id"), plan_code,
        billing_cycle=body.get("billing_cycle", "monthly"))
    if not result.get("success"):
        raise _err(400, "CHECKOUT_FAILED", result["error"])
    return {"status": "success", "data": result}


@router.post("/invoices/{invoice_id}/pay", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def pay(invoice_id: str, body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    result = BillingFlowEngine(db).pay_invoice(
        user.get("tenant_id"), invoice_id,
        payment_method=body.get("payment_method", "card"))
    if not result.get("success"):
        raise _err(400, "PAY_FAILED", result["error"])
    return {"status": "success", "data": result}


@router.get("/my-subscription", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def my_subscription(user: dict | None=None, db: Session = Depends(get_db)):
    data = BillingFlowEngine(db).my_subscription(user.get("tenant_id"))
    if not data:
        raise _err(404, "NOT_FOUND", "No subscription for this tenant")
    return {"status": "success", "data": data}


@router.post("/change-plan", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def change_plan(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("plan_code"):
        raise _err(400, "MISSING", "plan_code required")
    result = BillingFlowEngine(db).change_plan(
        user.get("tenant_id"), body["plan_code"],
        billing_cycle=body.get("billing_cycle", "monthly"))
    if not result.get("success"):
        raise _err(400, "CHANGE_FAILED", result["error"])
    return {"status": "success", "data": result}


@router.post("/usage", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_usage(body: dict, user: dict | None=None, db: Session = Depends(get_db)):
    if not body.get("meter_name") or "meter_value" not in body:
        raise _err(400, "MISSING", "meter_name and meter_value required")
    BillingFlowEngine(db).record_usage(user.get("tenant_id"),
                                        body["meter_name"], float(body["meter_value"]))
    return {"status": "success"}


@router.get("/usage-summary", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def usage_summary(user: dict | None=None, db: Session = Depends(get_db)):
    return {"status": "success", "data": BillingFlowEngine(db).usage_summary(user.get("tenant_id"))}
