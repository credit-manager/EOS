"""
Multi-Currency API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import SessionLocal
from core.auth import get_current_user
from core.currency_engine import MultiCurrencyEngine

router = APIRouter(prefix="/currencies", tags=["Multi-Currency"])


class CurrencyCreate(BaseModel):
    code: str
    name: str
    symbol: Optional[str] = None
    decimal_places: Optional[int] = 2
    is_base: Optional[bool] = False


class ExchangeRateCreate(BaseModel):
    from_currency: str
    to_currency: str
    rate: float
    source: Optional[str] = "manual"
    effective_date: Optional[str] = None


class ConvertRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str


@router.get("")
async def list_currencies(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = MultiCurrencyEngine(db).list_currencies(user["tenant_id"])
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.post("")
async def create_currency(body: CurrencyCreate, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = MultiCurrencyEngine(db).create_currency(
            user["tenant_id"], body.code, body.name, body.symbol,
            body.decimal_places, body.is_base
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/base")
async def get_base_currency(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = MultiCurrencyEngine(db).get_base_currency(user["tenant_id"])
        if not data:
            raise HTTPException(404, detail="No base currency set")
        return {"status": "success", "data": data}
    finally:
        db.close()


@router.get("/rates")
async def list_rates(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = MultiCurrencyEngine(db).list_exchange_rates(user["tenant_id"])
        return {"status": "success", "data": data, "total": len(data)}
    finally:
        db.close()


@router.post("/rates")
async def set_rate(body: ExchangeRateCreate, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = MultiCurrencyEngine(db).set_exchange_rate(
            user["tenant_id"], body.from_currency, body.to_currency,
            body.rate, body.source, body.effective_date
        )
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/rates/{from_currency}/{to_currency}")
async def get_rate(from_currency: str, to_currency: str, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rate = MultiCurrencyEngine(db).get_exchange_rate(user["tenant_id"], from_currency, to_currency)
        if rate is None:
            raise HTTPException(404, detail="Exchange rate not found")
        return {"status": "success", "data": {"from": from_currency, "to": to_currency, "rate": rate}}
    finally:
        db.close()


@router.post("/convert")
async def convert_currency(body: ConvertRequest, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = MultiCurrencyEngine(db).convert(
            user["tenant_id"], body.amount, body.from_currency, body.to_currency
        )
        if "error" in result:
            raise HTTPException(400, detail=result["error"])
        return {"status": "success", "data": result}
    finally:
        db.close()


@router.get("/summary")
async def currency_summary(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        data = MultiCurrencyEngine(db).get_currency_summary(user["tenant_id"])
        return {"status": "success", "data": data}
    finally:
        db.close()
