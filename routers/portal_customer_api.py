"""
Customer Portal API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import SessionLocal
from core.auth import get_current_user
from core.portal_engine import CustomerPortalEngine

router = APIRouter(prefix="/portal", tags=["Customer Portal"])


class PortalRegister(BaseModel):
    customer_id: str
    email: str
    password: str
    full_name: Optional[str] = None


class PortalLogin(BaseModel):
    email: str
    password: str


@router.post("/register")
async def register_portal_user(body: PortalRegister, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = CustomerPortalEngine(db).register_portal_user(
            user["tenant_id"], body.customer_id, body.email, body.password, body.full_name
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.post("/login")
async def portal_login(body: PortalLogin, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = CustomerPortalEngine(db).portal_login(user["tenant_id"], body.email, body.password)
        if "error" in result:
            raise HTTPException(401, detail=result["error"])
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/invoices")
async def customer_invoices(customer_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = CustomerPortalEngine(db).get_customer_invoices(user["tenant_id"], customer_id)
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.get("/orders")
async def customer_orders(customer_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = CustomerPortalEngine(db).get_customer_orders(user["tenant_id"], customer_id)
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.get("/payments")
async def customer_payments(customer_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = CustomerPortalEngine(db).get_customer_payments(user["tenant_id"], customer_id)
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.get("/summary/{customer_id}")
async def portal_summary(customer_id: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = CustomerPortalEngine(db).get_portal_summary(user["tenant_id"], customer_id)
        return {"status": "success", "data": data}
    finally:
        db.close()
