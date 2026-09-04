from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from core.subscription_engine import SubscriptionEngine
from database import get_db

router = APIRouter(prefix="/api/v1/dynamic/billing", tags=["Subscription & Billing"])


@router.get("/subscription",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_subscription(user: dict | None=None, db: Session = Depends(get_db)):
    data = SubscriptionEngine(db).get_subscription(user["tenant_id"])
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "No subscription found"}})
    return {"status": "success", "data": data}


@router.post("/subscription",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_subscription(body: dict,
                            user: dict | None=None, db: Session = Depends(get_db)):
    if "plan_id" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "plan_id required"}})
    sid = SubscriptionEngine(db).create_subscription(
        user["tenant_id"], body["plan_id"],
        billing_cycle=body.get("billing_cycle", "monthly"),
        trial_end=body.get("trial_end"))
    db.commit()
    return {"status": "success", "data": {"id": sid, "message": "Subscription created"}}


@router.delete("/subscription",
               dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def cancel_subscription(user: dict | None=None, db: Session = Depends(get_db)):
    result = SubscriptionEngine(db).cancel_subscription(user["tenant_id"])
    db.commit()
    return {"status": "success", "data": result}


@router.get("/subscriptions",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_subscriptions(status: str | None = None,
                            user: dict | None=None, db: Session = Depends(get_db)):
    data = SubscriptionEngine(db).list_subscriptions(status=status)
    return {"status": "success", "data": data}


# -------------------------------------------------------- invoices
@router.get("/invoices",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_invoices(status: str | None = None,
                       user: dict | None=None, db: Session = Depends(get_db)):
    data = SubscriptionEngine(db).list_invoices(user["tenant_id"], status=status)
    return {"status": "success", "data": data}


@router.post("/invoices",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_invoice(body: dict,
                       user: dict | None=None, db: Session = Depends(get_db)):
    required = ["subscription_id", "invoice_number", "amount"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    inv_id = SubscriptionEngine(db).create_invoice(
        user["tenant_id"], body["subscription_id"], body["invoice_number"],
        body["amount"], currency=body.get("currency", "USD"),
        due_date=body.get("due_date"), line_items=body.get("line_items"))
    db.commit()
    return {"status": "success", "data": {"id": inv_id, "message": "Invoice created"}}


@router.get("/invoices/{invoice_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_invoice(invoice_id: str,
                     user: dict | None=None, db: Session = Depends(get_db)):
    data = SubscriptionEngine(db).get_invoice(user["tenant_id"], invoice_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "Invoice not found"}})
    return {"status": "success", "data": data}


@router.put("/invoices/{invoice_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_invoice(invoice_id: str, body: dict,
                        user: dict | None=None, db: Session = Depends(get_db)):
    if "status" not in body:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "MISSING", "message": "status required"}})
    result = SubscriptionEngine(db).update_invoice_status(
        user["tenant_id"], invoice_id, body["status"])
    db.commit()
    return {"status": "success", "data": result}


# -------------------------------------------------------- payments
@router.get("/payments",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_payments(user: dict | None=None, db: Session = Depends(get_db)):
    data = SubscriptionEngine(db).list_payments(user["tenant_id"])
    return {"status": "success", "data": data}


@router.post("/payments",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_payment(body: dict,
                       user: dict | None=None, db: Session = Depends(get_db)):
    required = ["amount"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    pid = SubscriptionEngine(db).create_payment(
        user["tenant_id"], body.get("invoice_id"), body["amount"],
        currency=body.get("currency", "USD"),
        payment_method=body.get("payment_method"),
        transaction_id=body.get("transaction_id"))
    db.commit()
    return {"status": "success", "data": {"id": pid, "message": "Payment recorded"}}


# -------------------------------------------------------- licenses
@router.get("/licenses",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_licenses(status: str | None = None,
                       user: dict | None=None, db: Session = Depends(get_db)):
    data = SubscriptionEngine(db).list_licenses(user["tenant_id"], status=status)
    return {"status": "success", "data": data}


@router.post("/licenses",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_license(body: dict,
                       user: dict | None=None, db: Session = Depends(get_db)):
    required = ["license_key", "license_type"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    lid = SubscriptionEngine(db).create_license(
        user["tenant_id"], body["license_key"], body["license_type"],
        max_seats=body.get("max_seats", 5),
        valid_from=body.get("valid_from"),
        valid_until=body.get("valid_until"),
        features=body.get("features"))
    db.commit()
    return {"status": "success", "data": {"id": lid, "message": "License created"}}


@router.get("/licenses/{license_id}",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_license(license_id: str,
                     user: dict | None=None, db: Session = Depends(get_db)):
    data = SubscriptionEngine(db).get_license(user["tenant_id"], license_id)
    if not data:
        raise HTTPException(404, detail={"status": "error",
            "error": {"code": "NOT_FOUND", "message": "License not found"}})
    return {"status": "success", "data": data}


@router.put("/licenses/{license_id}",
            dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_license(license_id: str, body: dict,
                        user: dict | None=None, db: Session = Depends(get_db)):
    result = SubscriptionEngine(db).update_license(user["tenant_id"], license_id, **body)
    if not result:
        raise HTTPException(400, detail={"status": "error",
            "error": {"code": "INVALID", "message": "No fields to update"}})
    db.commit()
    return {"status": "success", "data": result}


# --------------------------------------------------- usage meters
@router.get("/usage",
            dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_usage(meter_name: str | None = None, limit: int = 50,
                    user: dict | None=None, db: Session = Depends(get_db)):
    data = SubscriptionEngine(db).get_usage(user["tenant_id"], meter_name=meter_name, limit=limit)
    return {"status": "success", "data": data}


@router.post("/usage",
             dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def record_usage(body: dict,
                     user: dict | None=None, db: Session = Depends(get_db)):
    required = ["meter_name", "meter_value"]
    for f in required:
        if f not in body:
            raise HTTPException(400, detail={"status": "error",
                "error": {"code": "MISSING", "message": f"{f} required"}})
    uid = SubscriptionEngine(db).record_usage(
        user["tenant_id"], body["meter_name"], body["meter_value"],
        unit=body.get("unit"),
        period_start=body.get("period_start"),
        period_end=body.get("period_end"),
        overage_rate=body.get("overage_rate", 0))
    db.commit()
    return {"status": "success", "data": {"id": uid, "message": "Usage recorded"}}
