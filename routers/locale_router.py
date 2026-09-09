"""
EOS i18n Router — P64
Locale management endpoints.

Endpoints:
    GET  /api/v1/locale/current     — Current locale info
    POST /api/v1/locale/switch      — Switch locale
    GET  /api/v1/locale/translations — Get translations for locale
    GET  /api/v1/locale/terms       — Business terminology
"""

from fastapi import APIRouter, Query, Body, Depends
from pydantic import BaseModel
from typing import Optional
from core.auth import get_current_user
from core.i18n import (
    t, get_locale, set_locale, is_rtl, get_direction,
    get_locale_info, SUPPORTED_LOCALES, BUSINESS_TERMS,
    format_date, format_number, format_currency, detect_locale
)
from datetime import datetime

router = APIRouter(prefix="/api/v1/locale", tags=["Locale"])


class SwitchLocaleRequest(BaseModel):
    locale: str


class LocaleInfoResponse(BaseModel):
    locale: str
    direction: str
    is_rtl: bool
    language_name: str
    supported: list


class FormatDateRequest(BaseModel):
    date: str  # ISO format
    locale: Optional[str] = None
    fmt: Optional[str] = None


class FormatNumberRequest(BaseModel):
    value: float
    locale: Optional[str] = None
    decimals: Optional[int] = 0


class FormatCurrencyRequest(BaseModel):
    value: float
    currency: str = "SAR"
    locale: Optional[str] = None
    decimals: Optional[int] = 2


# ═══════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════

@router.get("/current", response_model=LocaleInfoResponse)
async def current_locale():
    """Get current locale information."""
    return get_locale_info()


@router.post("/switch", response_model=LocaleInfoResponse)
async def switch_locale(req: SwitchLocaleRequest, user: dict = Depends(get_current_user)):
    """Switch to a different locale."""
    set_locale(req.locale)
    return get_locale_info(req.locale)


@router.get("/translations")
async def get_translations(
    locale: str = Query(None, description="Locale code (ar/en)"),
    section: str = Query(None, description="Translation section (ui, auth, errors, erp, etc.)")
):
    """Get translations for a locale, optionally filtered by section."""
    if locale is None:
        locale = get_locale()

    from core.i18n import _translations
    translations = _translations.get(locale, _translations.get("en", {}))

    if section:
        translations = translations.get(section, {})

    return {
        "locale": locale,
        "section": section or "all",
        "translations": translations,
    }


@router.get("/terms")
async def get_business_terms(
    locale: str = Query(None, description="Locale code (ar/en)")
):
    """Get all business terminology translations."""
    if locale is None:
        locale = get_locale()

    result = {}
    for key, values in BUSINESS_TERMS.items():
        result[key] = values.get(locale, key)

    return {
        "locale": locale,
        "terms": result,
    }


@router.get("/term/{term_key}")
async def get_term(
    term_key: str,
    locale: str = Query(None)
):
    """Get a single business term translation."""
    if locale is None:
        locale = get_locale()
    terms = BUSINESS_TERMS.get(term_key, {})
    return {
        "key": term_key,
        "locale": locale,
        "translation": terms.get(locale, term_key),
        "all": terms,
    }


# ═══════════════════════════════════════════════
# Formatting Endpoints
# ═══════════════════════════════════════════════

@router.post("/format/date")
async def api_format_date(req: FormatDateRequest):
    """Format a date for the given locale."""
    dt = datetime.fromisoformat(req.date)
    result = format_date(dt, locale=req.locale, fmt=req.fmt)
    return {"formatted": result, "locale": req.locale or get_locale()}


@router.post("/format/number")
async def api_format_number(req: FormatNumberRequest):
    """Format a number for the given locale."""
    result = format_number(req.value, locale=req.locale, decimals=req.decimals)
    return {"formatted": result, "locale": req.locale or get_locale()}


@router.post("/format/currency")
async def api_format_currency(req: FormatCurrencyRequest):
    """Format a currency amount for the given locale."""
    result = format_currency(req.value, req.currency, locale=req.locale, decimals=req.decimals)
    return {"formatted": result, "locale": req.locale or get_locale(), "currency": req.currency}