"""
EOS System — Infrastructure Router (Fiscal Years, Currencies, Exchange Rates, Company Profile)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.infrastructure import (
    FiscalYear, Currency, ExchangeRate, CompanyProfile,
)

router = APIRouter()


# ─── Fiscal Year Schemas ──────────────────────────────────

class FiscalYearCreate(BaseModel):
    name: str
    start_date: date
    end_date: date
    is_current: bool = False


class FiscalYearResponse(BaseModel):
    id: str
    name: str
    start_date: date
    end_date: date
    is_current: bool
    is_closed: bool
    created_at: datetime


# ─── Currency Schemas ─────────────────────────────────────

class CurrencyCreate(BaseModel):
    code: str
    name: str
    name_ar: Optional[str] = None
    symbol: Optional[str] = None
    decimal_places: int = 2
    is_base: bool = False


class CurrencyResponse(BaseModel):
    id: str
    code: str
    name: str
    name_ar: Optional[str]
    symbol: Optional[str]
    decimal_places: int
    is_base: bool
    is_active: bool


# ─── Exchange Rate Schemas ────────────────────────────────

class ExchangeRateCreate(BaseModel):
    currency_id: str
    rate: Decimal
    effective_date: date


class ExchangeRateResponse(BaseModel):
    id: str
    currency_id: str
    rate: float
    effective_date: date
    created_at: datetime


# ─── Company Profile Schemas ──────────────────────────────

class CompanyProfileCreate(BaseModel):
    legal_name: str
    legal_name_ar: Optional[str] = None
    trade_name: Optional[str] = None
    trade_name_ar: Optional[str] = None
    tax_number: Optional[str] = None
    commercial_register: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Egypt"
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    default_currency: str = "EGP"
    fiscal_year_start: int = 1


class CompanyProfileResponse(BaseModel):
    id: str
    legal_name: str
    legal_name_ar: Optional[str]
    trade_name: Optional[str]
    tax_number: Optional[str]
    commercial_register: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: str
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    default_currency: str
    fiscal_year_start: int
    created_at: datetime


# ─── FISCAL YEARS ─────────────────────────────────────────

@router.get("/fiscal-years", response_model=list[FiscalYearResponse])
async def list_fiscal_years(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    result = await db.execute(
        select(FiscalYear).filter(FiscalYear.tenant_id == current_user["tenant_id"])
        .order_by(FiscalYear.start_date.desc())
    )
    years = result.scalars().all()
    return [FiscalYearResponse(
        id=y.id, name=y.name, start_date=y.start_date, end_date=y.end_date,
        is_current=y.is_current, is_closed=y.is_closed, created_at=y.created_at,
    ) for y in years]


@router.post("/fiscal-years", response_model=FiscalYearResponse)
async def create_fiscal_year(
    fy: FiscalYearCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    if fy.is_current:
        await db.execute(
            FiscalYear.__table__.update()
            .where(FiscalYear.is_current == True)
            .values(is_current=False)
        )

    new_fy = FiscalYear(
        id=str(uuid.uuid4()), tenant_id=current_user["tenant_id"],
        name=fy.name, start_date=fy.start_date, end_date=fy.end_date,
        is_current=fy.is_current,
    )
    db.add(new_fy)
    await db.flush()

    return FiscalYearResponse(
        id=new_fy.id, name=new_fy.name, start_date=new_fy.start_date,
        end_date=new_fy.end_date, is_current=new_fy.is_current,
        is_closed=new_fy.is_closed, created_at=new_fy.created_at,
    )


# ─── CURRENCIES ───────────────────────────────────────────

@router.get("/currencies", response_model=list[CurrencyResponse])
async def list_currencies(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    result = await db.execute(select(Currency).order_by(Currency.code))
    currencies = result.scalars().all()
    return [CurrencyResponse(
        id=c.id, code=c.code, name=c.name, name_ar=c.name_ar,
        symbol=c.symbol, decimal_places=c.decimal_places,
        is_base=c.is_base, is_active=c.is_active,
    ) for c in currencies]


@router.post("/currencies", response_model=CurrencyResponse)
async def create_currency(
    currency: CurrencyCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    new_cur = Currency(
        id=str(uuid.uuid4()), code=currency.code.upper(),
        name=currency.name, name_ar=currency.name_ar,
        symbol=currency.symbol, decimal_places=currency.decimal_places,
        is_base=currency.is_base, is_active=True,
    )
    db.add(new_cur)
    await db.flush()

    return CurrencyResponse(
        id=new_cur.id, code=new_cur.code, name=new_cur.name,
        name_ar=new_cur.name_ar, symbol=new_cur.symbol,
        decimal_places=new_cur.decimal_places, is_base=new_cur.is_base,
        is_active=new_cur.is_active,
    )


# ─── EXCHANGE RATES ──────────────────────────────────────

@router.get("/exchange-rates", response_model=list[ExchangeRateResponse])
async def list_exchange_rates(
    currency_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    query = select(ExchangeRate)
    query = query.filter(ExchangeRate.tenant_id == current_user["tenant_id"])
    if currency_id:
        query = query.filter(ExchangeRate.currency_id == currency_id)
    query = query.order_by(ExchangeRate.effective_date.desc())

    result = await db.execute(query)
    rates = result.scalars().all()
    return [ExchangeRateResponse(
        id=r.id, currency_id=r.currency_id, rate=float(r.rate),
        effective_date=r.effective_date, created_at=r.created_at,
    ) for r in rates]


@router.post("/exchange-rates", response_model=ExchangeRateResponse)
async def create_exchange_rate(
    rate: ExchangeRateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    new_rate = ExchangeRate(
        id=str(uuid.uuid4()), tenant_id=current_user["tenant_id"],
        currency_id=rate.currency_id,
        rate=rate.rate, effective_date=rate.effective_date,
    )
    db.add(new_rate)
    await db.flush()

    return ExchangeRateResponse(
        id=new_rate.id, currency_id=new_rate.currency_id,
        rate=float(new_rate.rate), effective_date=new_rate.effective_date,
        created_at=new_rate.created_at,
    )


# ─── COMPANY PROFILE ─────────────────────────────────────

@router.get("/company-profile", response_model=CompanyProfileResponse)
async def get_company_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:read")

    result = await db.execute(
        select(CompanyProfile).filter(CompanyProfile.tenant_id == current_user["tenant_id"]).limit(1)
    )
    profile = result.scalar()
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")

    return CompanyProfileResponse(
        id=profile.id, legal_name=profile.legal_name,
        legal_name_ar=profile.legal_name_ar,
        trade_name=profile.trade_name, tax_number=profile.tax_number,
        commercial_register=profile.commercial_register,
        address=profile.address, city=profile.city, country=profile.country,
        phone=profile.phone, email=profile.email, website=profile.website,
        default_currency=profile.default_currency,
        fiscal_year_start=profile.fiscal_year_start,
        created_at=profile.created_at,
    )


@router.post("/company-profile", response_model=CompanyProfileResponse)
async def create_company_profile(
    profile: CompanyProfileCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "accounting:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires accounting:create")

    existing = await db.execute(
        select(CompanyProfile).filter(CompanyProfile.tenant_id == current_user["tenant_id"]).limit(1)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Company profile already exists")

    new_profile = CompanyProfile(
        id=str(uuid.uuid4()), tenant_id=current_user["tenant_id"],
        legal_name=profile.legal_name,
        legal_name_ar=profile.legal_name_ar,
        trade_name=profile.trade_name, trade_name_ar=profile.trade_name_ar,
        tax_number=profile.tax_number, commercial_register=profile.commercial_register,
        address=profile.address, city=profile.city, country=profile.country,
        phone=profile.phone, email=profile.email, website=profile.website,
        default_currency=profile.default_currency,
        fiscal_year_start=profile.fiscal_year_start,
    )
    db.add(new_profile)
    await db.flush()

    return CompanyProfileResponse(
        id=new_profile.id, legal_name=new_profile.legal_name,
        legal_name_ar=new_profile.legal_name_ar,
        trade_name=new_profile.trade_name, tax_number=new_profile.tax_number,
        commercial_register=new_profile.commercial_register,
        address=new_profile.address, city=new_profile.city, country=new_profile.country,
        phone=new_profile.phone, email=new_profile.email, website=new_profile.website,
        default_currency=new_profile.default_currency,
        fiscal_year_start=new_profile.fiscal_year_start,
        created_at=new_profile.created_at,
    )
