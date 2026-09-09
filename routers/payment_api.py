"""
Payment Gateway API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import SessionLocal
from core.auth import get_current_user
from core.payment_engine import PaymentGatewayEngine
from core.rate_limit import read_limiter, write_limiter

router = APIRouter(prefix="/payments", tags=["Payments"])


class GatewayCreate(BaseModel):
    gateway_name: str
    gateway_type: str
    config: Optional[dict] = None


class TransactionCreate(BaseModel):
    amount: float
    currency: Optional[str] = "SAR"
    transaction_type: Optional[str] = "payment"
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    customer_id: Optional[str] = None
    payment_method: Optional[str] = None


class RefundRequest(BaseModel):
    amount: Optional[float] = None


class PaymentLinkCreate(BaseModel):
    amount: float
    description: Optional[str] = None
    customer_email: Optional[str] = None
    expires_hours: Optional[int] = 24


class BankTransferRequest(BaseModel):
    amount: float
    bank_name: str
    account_number: str
    reference: str


@router.get("/gateways")
async def list_gateways(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = PaymentGatewayEngine(db).list_gateways(user["tenant_id"])
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.post("/gateways")
async def create_gateway(body: GatewayCreate, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).create_gateway(
            user["tenant_id"], body.gateway_name, body.gateway_type, body.config
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/transactions")
async def create_transaction(body: TransactionCreate, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).create_transaction(
            user["tenant_id"], body.amount, body.currency, body.transaction_type,
            body.reference_type, body.reference_id, body.customer_id, body.payment_method
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/transactions")
async def list_transactions(status: Optional[str] = None, limit: int = 50,
                            user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = PaymentGatewayEngine(db).list_transactions(user["tenant_id"], status, limit)
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = PaymentGatewayEngine(db).get_transaction(transaction_id)
        if not data:
            raise HTTPException(404, detail="Transaction not found")
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.post("/transactions/{transaction_id}/complete")
async def complete_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).complete_transaction(transaction_id)
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/transactions/{transaction_id}/fail")
async def fail_transaction(transaction_id: str, reason: str = "", user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).fail_transaction(transaction_id, reason)
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/transactions/{transaction_id}/refund")
async def refund_transaction(transaction_id: str, body: RefundRequest, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).refund_transaction(transaction_id, body.amount)
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/bank-transfer")
async def bank_transfer(body: BankTransferRequest, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).process_bank_transfer(
            user["tenant_id"], body.amount, body.bank_name, body.account_number, body.reference
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/cash")
async def cash_payment(amount: float, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).process_cash(user["tenant_id"], amount)
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/links")
async def create_payment_link(body: PaymentLinkCreate, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).create_payment_link(
            user["tenant_id"], body.amount, body.description,
            body.customer_email, body.expires_hours
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/summary")
async def payment_summary(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = PaymentGatewayEngine(db).get_summary(user["tenant_id"])
        return {"status": "success", "data": data}
    finally:
        db.close()
