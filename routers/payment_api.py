"""Payment Gateway API Router.

Payment creation is separate from settlement. Completion/failure/refund paths
require explicit financial settlement privileges; regular tenant users cannot
self-approve monetary state transitions.
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user, require_financial_settlement, require_permission
from core.payment_engine import PaymentGatewayEngine
from core.rate_limit import read_limiter, write_limiter
from database import SessionLocal

router = APIRouter(prefix="/payments", tags=["Payments"])


class GatewayCreate(BaseModel):
    gateway_name: str = Field(min_length=1, max_length=120)
    gateway_type: str = Field(min_length=1, max_length=32)
    config: Optional[dict] = None


class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="SAR", min_length=3, max_length=3)
    transaction_type: str = Field(default="payment", min_length=1, max_length=32)
    reference_type: Optional[str] = Field(default=None, max_length=64)
    reference_id: Optional[str] = Field(default=None, max_length=128)
    customer_id: Optional[str] = Field(default=None, max_length=128)
    payment_method: Optional[str] = Field(default=None, max_length=64)


class RefundRequest(BaseModel):
    amount: Optional[Decimal] = Field(default=None, gt=0)


class PaymentLinkCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    description: Optional[str] = Field(default=None, max_length=500)
    customer_email: Optional[str] = Field(default=None, max_length=320)
    expires_hours: int = Field(default=24, ge=1, le=720)


class BankTransferRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    bank_name: str = Field(min_length=1, max_length=120)
    account_number: str = Field(min_length=4, max_length=64)
    reference: str = Field(min_length=1, max_length=120)


def _run_permission(module: str, action: str):
    return Depends(require_permission(module, action))


def _db():
    return SessionLocal()


@router.get("/gateways", dependencies=[_run_permission("payments", "read"), Depends(read_limiter.check)])
async def list_gateways(user: dict = Depends(get_current_user)):
    db = _db()
    try:
        return {"status": "success", "data": PaymentGatewayEngine(db).list_gateways(user["tenant_id"])}
    finally:
        db.close()


@router.post("/gateways", dependencies=[_run_permission("payments", "admin"), Depends(write_limiter.check)])
async def create_gateway(body: GatewayCreate, user: dict = Depends(get_current_user)):
    db = _db()
    try:
        try:
            result = PaymentGatewayEngine(db).create_gateway(user["tenant_id"], body.gateway_name, body.gateway_type, body.config)
        except ValueError as exc:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": str(exc)}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/transactions", dependencies=[_run_permission("payments", "create"), Depends(write_limiter.check)])
async def create_transaction(body: TransactionCreate, user: dict = Depends(get_current_user)):
    db = _db()
    try:
        try:
            result = PaymentGatewayEngine(db).create_transaction(
                user["tenant_id"], body.amount, body.currency, body.transaction_type,
                body.reference_type, body.reference_id, body.customer_id, body.payment_method,
            )
        except ValueError as exc:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": str(exc)}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/transactions")
async def list_transactions(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    _permission=Depends(require_permission("payments", "read")),
    _rate=Depends(read_limiter.check),
):
    db = _db()
    try:
        data = PaymentGatewayEngine(db).list_transactions(user["tenant_id"], status, limit)
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.get("/transactions/{transaction_id}", dependencies=[_run_permission("payments", "read"), Depends(read_limiter.check)])
async def get_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    db = _db()
    try:
        data = PaymentGatewayEngine(db).get_transaction(transaction_id, user["tenant_id"])
        if not data:
            raise HTTPException(404, detail="Transaction not found")
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.post("/transactions/{transaction_id}/complete", dependencies=[Depends(require_financial_settlement), Depends(write_limiter.check)])
async def complete_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    db = _db()
    try:
        result = PaymentGatewayEngine(db).complete_transaction(transaction_id, user["tenant_id"])
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(409 if "status" in result.get("error", "") else 404, detail={"status": "error", "error": {"code": "SETTLEMENT_FAILED", "message": result["error"]}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/transactions/{transaction_id}/fail", dependencies=[Depends(require_financial_settlement), Depends(write_limiter.check)])
async def fail_transaction(transaction_id: str, reason: str = Query("", max_length=500), user: dict = Depends(get_current_user)):
    db = _db()
    try:
        result = PaymentGatewayEngine(db).fail_transaction(transaction_id, user["tenant_id"], reason)
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": result["error"]}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/transactions/{transaction_id}/refund", dependencies=[Depends(require_financial_settlement), Depends(write_limiter.check)])
async def refund_transaction(transaction_id: str, body: RefundRequest, user: dict = Depends(get_current_user)):
    db = _db()
    try:
        result = PaymentGatewayEngine(db).refund_transaction(transaction_id, user["tenant_id"], body.amount)
        if isinstance(result, dict) and result.get("error"):
            err = result["error"]
            raise HTTPException(404 if err == "Transaction not found" else 400, detail={"status": "error", "error": {"code": "REFUND_FAILED", "message": err}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/bank-transfer", dependencies=[_run_permission("payments", "create"), Depends(write_limiter.check)])
async def bank_transfer(body: BankTransferRequest, user: dict = Depends(get_current_user)):
    db = _db()
    try:
        try:
            result = PaymentGatewayEngine(db).process_bank_transfer(user["tenant_id"], body.amount, body.bank_name, body.account_number, body.reference)
        except ValueError as exc:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": str(exc)}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/cash", dependencies=[_run_permission("payments", "create"), Depends(write_limiter.check)])
async def cash_payment(amount: Decimal = Query(..., gt=0), user: dict = Depends(get_current_user)):
    db = _db()
    try:
        try:
            result = PaymentGatewayEngine(db).process_cash(user["tenant_id"], amount)
        except ValueError as exc:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": str(exc)}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/links", dependencies=[_run_permission("payments", "create"), Depends(write_limiter.check)])
async def create_payment_link(body: PaymentLinkCreate, user: dict = Depends(get_current_user)):
    db = _db()
    try:
        try:
            result = PaymentGatewayEngine(db).create_payment_link(user["tenant_id"], body.amount, body.description, body.customer_email, body.expires_hours)
        except ValueError as exc:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": str(exc)}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/summary", dependencies=[_run_permission("payments", "read"), Depends(read_limiter.check)])
async def payment_summary(user: dict = Depends(get_current_user)):
    db = _db()
    try:
        return {"status": "success", "data": PaymentGatewayEngine(db).get_summary(user["tenant_id"])}
    finally:
        db.close()
