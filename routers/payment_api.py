"""Payment Gateway API Router.

All gateway and transaction operations are tenant-bound through the
authenticated principal and protected by explicit RBAC dependencies.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user, require_permission
from core.payment_engine import PaymentGatewayEngine
from core.rate_limit import read_limiter, write_limiter
from database import SessionLocal

router = APIRouter(prefix="/payments", tags=["Payments"])


class GatewayCreate(BaseModel):
    gateway_name: str = Field(min_length=1, max_length=120)
    gateway_type: str = Field(min_length=1, max_length=50)
    config: dict | None = None


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    currency: str | None = Field(default="SAR", min_length=3, max_length=3)
    transaction_type: str | None = Field(default="payment", max_length=40)
    reference_type: str | None = Field(default=None, max_length=80)
    reference_id: str | None = Field(default=None, max_length=120)
    customer_id: str | None = Field(default=None, max_length=120)
    payment_method: str | None = Field(default=None, max_length=50)


class RefundRequest(BaseModel):
    amount: float | None = Field(default=None, gt=0)


class PaymentLinkCreate(BaseModel):
    amount: float = Field(gt=0)
    description: str | None = Field(default=None, max_length=500)
    customer_email: str | None = None
    expires_hours: int | None = Field(default=24, ge=1, le=168)


class BankTransferRequest(BaseModel):
    amount: float = Field(gt=0)
    bank_name: str = Field(min_length=1, max_length=120)
    account_number: str = Field(min_length=1, max_length=120)
    reference: str = Field(min_length=1, max_length=120)


def _tenant(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(401, detail={"status":"error","error":{"code":"TENANT_REQUIRED","message":"Authenticated tenant is required"}})
    return tenant_id


def _session():
    return SessionLocal()


@router.get("/gateways", dependencies=[Depends(require_permission("payments", "read")), Depends(read_limiter.check)])
async def list_gateways(user: dict = Depends(get_current_user)):
    db = _session()
    try:
        return {"status":"success","data":PaymentGatewayEngine(db).list_gateways(_tenant(user))}
    finally:
        db.close()


@router.post("/gateways", dependencies=[Depends(require_permission("payments", "create")), Depends(write_limiter.check)])
async def create_gateway(body: GatewayCreate, user: dict = Depends(get_current_user)):
    db = _session()
    try:
        return {"status":"success","data":PaymentGatewayEngine(db).create_gateway(_tenant(user),body.gateway_name,body.gateway_type,body.config)}
    finally:
        db.close()


@router.post("/transactions", dependencies=[Depends(require_permission("payments", "create")), Depends(write_limiter.check)])
async def create_transaction(body: TransactionCreate, user: dict = Depends(get_current_user)):
    db = _session()
    try:
        try:
            result=PaymentGatewayEngine(db).create_transaction(_tenant(user),body.amount,body.currency,body.transaction_type,body.reference_type,body.reference_id,body.customer_id,body.payment_method)
        except ValueError as exc:
            raise HTTPException(400,detail={"status":"error","error":{"code":"INVALID","message":str(exc)}}) from exc
        return {"status":"success","data":result}
    finally: db.close()


@router.get("/transactions", dependencies=[Depends(require_permission("payments", "read")), Depends(read_limiter.check)])
async def list_transactions(status: str | None = None, limit: int = Query(50, ge=1, le=500), user: dict = Depends(get_current_user)):
    db=_session()
    try: return {"status":"success","data":PaymentGatewayEngine(db).list_transactions(_tenant(user),status,limit)}
    finally: db.close()


@router.get("/transactions/{transaction_id}", dependencies=[Depends(require_permission("payments", "read")), Depends(read_limiter.check)])
async def get_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    db=_session()
    try:
        data=PaymentGatewayEngine(db).get_transaction(transaction_id,_tenant(user))
        if not data: raise HTTPException(404,detail="Transaction not found")
        return {"status":"success","data":data}
    finally: db.close()


@router.post("/transactions/{transaction_id}/complete", dependencies=[Depends(require_permission("payments", "update")), Depends(write_limiter.check)])
async def complete_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    db=_session()
    try:
        result=PaymentGatewayEngine(db).complete_transaction(transaction_id,_tenant(user))
        if result.get("error"): raise HTTPException(404,detail={"status":"error","error":{"code":"NOT_FOUND","message":result["error"]}})
        return {"status":"success","data":result}
    finally: db.close()


@router.post("/transactions/{transaction_id}/fail", dependencies=[Depends(require_permission("payments", "update")), Depends(write_limiter.check)])
async def fail_transaction(transaction_id: str, reason: str = Query("", max_length=500), user: dict = Depends(get_current_user)):
    db=_session()
    try:
        result=PaymentGatewayEngine(db).fail_transaction(transaction_id,_tenant(user),reason)
        if result.get("error"): raise HTTPException(404,detail={"status":"error","error":{"code":"NOT_FOUND","message":result["error"]}})
        return {"status":"success","data":result}
    finally: db.close()


@router.post("/transactions/{transaction_id}/refund", dependencies=[Depends(require_permission("payments", "update")), Depends(write_limiter.check)])
async def refund_transaction(transaction_id: str, body: RefundRequest, user: dict = Depends(get_current_user)):
    db=_session()
    try:
        result=PaymentGatewayEngine(db).refund_transaction(transaction_id,_tenant(user),body.amount)
        if result.get("error"):
            err=result["error"]; code="NOT_FOUND" if err=="Transaction not found" else "REFUND_FAILED"
            raise HTTPException(404 if code=="NOT_FOUND" else 400,detail={"status":"error","error":{"code":code,"message":err}})
        return {"status":"success","data":result}
    finally: db.close()


@router.post("/bank-transfer", dependencies=[Depends(require_permission("payments", "create")), Depends(write_limiter.check)])
async def bank_transfer(body: BankTransferRequest, user: dict = Depends(get_current_user)):
    db=_session()
    try:
        try: result=PaymentGatewayEngine(db).process_bank_transfer(_tenant(user),body.amount,body.bank_name,body.account_number,body.reference)
        except ValueError as exc: raise HTTPException(400,detail={"status":"error","error":{"code":"INVALID","message":str(exc)}}) from exc
        return {"status":"success","data":result}
    finally: db.close()


@router.post("/cash", dependencies=[Depends(require_permission("payments", "create")), Depends(write_limiter.check)])
async def cash_payment(amount: float = Query(..., gt=0), user: dict = Depends(get_current_user)):
    db=_session()
    try:
        try: result=PaymentGatewayEngine(db).process_cash(_tenant(user),amount)
        except ValueError as exc: raise HTTPException(400,detail={"status":"error","error":{"code":"INVALID","message":str(exc)}}) from exc
        return {"status":"success","data":result}
    finally: db.close()


@router.post("/links", dependencies=[Depends(require_permission("payments", "create")), Depends(write_limiter.check)])
async def create_payment_link(body: PaymentLinkCreate, user: dict = Depends(get_current_user)):
    db=_session()
    try:
        try: result=PaymentGatewayEngine(db).create_payment_link(_tenant(user),body.amount,body.description,body.customer_email,body.expires_hours)
        except ValueError as exc: raise HTTPException(400,detail={"status":"error","error":{"code":"INVALID","message":str(exc)}}) from exc
        return {"status":"success","data":result}
    finally: db.close()


@router.get("/summary", dependencies=[Depends(require_permission("payments", "read")), Depends(read_limiter.check)])
async def payment_summary(user: dict = Depends(get_current_user)):
    db=_session()
    try: return {"status":"success","data":PaymentGatewayEngine(db).get_summary(_tenant(user))}
    finally: db.close()
