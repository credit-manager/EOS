"""
Payment Gateway API Router
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.payment_engine import PaymentGatewayEngine
from database import SessionLocal

router = APIRouter(prefix="/payments", tags=["Payments"])


class GatewayCreate(BaseModel):
    gateway_name: str
    gateway_type: str
    config: dict | None = None


class TransactionCreate(BaseModel):
    amount: float
    currency: str | None = "SAR"
    transaction_type: str | None = "payment"
    reference_type: str | None = None
    reference_id: str | None = None
    customer_id: str | None = None
    payment_method: str | None = None


class RefundRequest(BaseModel):
    amount: float | None = None


class PaymentLinkCreate(BaseModel):
    amount: float
    description: str | None = None
    customer_email: str | None = None
    expires_hours: int | None = 24


class BankTransferRequest(BaseModel):
    amount: float
    bank_name: str
    account_number: str
    reference: str


@router.get("/gateways")
async def list_gateways(user: dict | None=None):
    db = SessionLocal()
    try:
        data = PaymentGatewayEngine(db).list_gateways(user["tenant_id"])
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.post("/gateways")
async def create_gateway(body: GatewayCreate, user: dict | None=None):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).create_gateway(
            user["tenant_id"], body.gateway_name, body.gateway_type, body.config
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/transactions")
async def create_transaction(body: TransactionCreate, user: dict | None=None):
    db = SessionLocal()
    try:
        try:
            result = PaymentGatewayEngine(db).create_transaction(
                user["tenant_id"], body.amount, body.currency, body.transaction_type,
                body.reference_type, body.reference_id, body.customer_id, body.payment_method
            )
        except ValueError as e:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": str(e)}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/transactions")
async def list_transactions(status: str | None = None, limit: int = 50,
                            user: dict | None=None):
    db = SessionLocal()
    try:
        data = PaymentGatewayEngine(db).list_transactions(user["tenant_id"], status, limit)
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str, user: dict | None=None):
    db = SessionLocal()
    try:
        data = PaymentGatewayEngine(db).get_transaction(transaction_id, user["tenant_id"])
        if not data:
            raise HTTPException(404, detail="Transaction not found")
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.post("/transactions/{transaction_id}/complete")
async def complete_transaction(transaction_id: str, user: dict | None=None):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).complete_transaction(transaction_id, user["tenant_id"])
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": result["error"]}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/transactions/{transaction_id}/fail")
async def fail_transaction(transaction_id: str, reason: str = "", user: dict | None=None):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).fail_transaction(transaction_id, user["tenant_id"], reason)
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": result["error"]}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/transactions/{transaction_id}/refund")
async def refund_transaction(transaction_id: str, body: RefundRequest, user: dict | None=None):
    db = SessionLocal()
    try:
        result = PaymentGatewayEngine(db).refund_transaction(transaction_id, user["tenant_id"], body.amount)
        if isinstance(result, dict) and result.get("error"):
            err = result["error"]
            if err == "Transaction not found":
                raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": err}})
            raise HTTPException(400, detail={"status": "error", "error": {"code": "REFUND_FAILED", "message": err}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/bank-transfer")
async def bank_transfer(body: BankTransferRequest, user: dict | None=None):
    db = SessionLocal()
    try:
        try:
            result = PaymentGatewayEngine(db).process_bank_transfer(
                user["tenant_id"], body.amount, body.bank_name, body.account_number, body.reference
            )
        except ValueError as e:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": str(e)}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/cash")
async def cash_payment(amount: float, user: dict | None=None):
    db = SessionLocal()
    try:
        try:
            result = PaymentGatewayEngine(db).process_cash(user["tenant_id"], amount)
        except ValueError as e:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": str(e)}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/links")
async def create_payment_link(body: PaymentLinkCreate, user: dict | None=None):
    db = SessionLocal()
    try:
        try:
            result = PaymentGatewayEngine(db).create_payment_link(
                user["tenant_id"], body.amount, body.description,
                body.customer_email, body.expires_hours
            )
        except ValueError as e:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": str(e)}})
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/summary")
async def payment_summary(user: dict | None=None):
    db = SessionLocal()
    try:
        data = PaymentGatewayEngine(db).get_summary(user["tenant_id"])
        return {"status": "success", "data": data}
    finally:
        db.close()
