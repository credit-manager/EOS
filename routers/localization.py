"""
EOS Localization Router — API endpoints for language, translations, formatting.
P64.3: API endpoints for language switching and translation retrieval.
"""

from fastapi import APIRouter, Query, Request, Response
from typing import Optional
from core.localization import (
    t, get_direction, get_language_name, get_supported_languages,
    format_number, format_currency, format_percentage, format_date,
    TRANSLATIONS, SUPPORTED_LANGUAGES, detect_language,
    current_lang, current_direction,
)

router = APIRouter(prefix="/api/v1/localization", tags=["Localization"], include_in_schema=False)


@router.get("/languages")
def list_languages():
    """List supported languages."""
    return {
        "languages": get_supported_languages(),
        "default": "en",
    }


@router.get("/translations/{lang}")
def get_translations(lang: str, prefix: Optional[str] = Query(None)):
    """
    Get all translations for a language, optionally filtered by prefix.
    Example: /api/v1/localization/translations/ar?prefix=auth
    """
    if lang not in SUPPORTED_LANGUAGES:
        return Response(
            content=f'{{"error": "Unsupported language: {lang}"}}',
            status_code=400,
            media_type="application/json",
        )

    if prefix:
        filtered = {k: v.get(lang, v.get("en", k))
                    for k, v in TRANSLATIONS.items()
                    if k.startswith(prefix)}
    else:
        filtered = {k: v.get(lang, v.get("en", k))
                    for k, v in TRANSLATIONS.items()}

    return {
        "language": lang,
        "direction": get_direction(lang),
        "translations": filtered,
        "count": len(filtered),
    }


@router.get("/translate")
def translate_key(
    key: str = Query(..., description="Translation key"),
    lang: Optional[str] = Query(None, description="Language code (ar/en)"),
):
    """Translate a single key."""
    result = t(key, lang=lang)
    return {
        "key": key,
        "language": lang or "en",
        "translation": result,
        "direction": get_direction(lang),
    }


@router.get("/direction/{lang}")
def text_direction(lang: str):
    """Get text direction for a language."""
    return {
        "language": lang,
        "direction": get_direction(lang),
        "is_rtl": get_direction(lang) == "rtl",
    }


@router.post("/detect")
def detect_lang(request: Request):
    """Detect language from request headers."""
    accept_lang = request.headers.get("accept-language", "")
    detected = detect_language(accept_lang)
    return {
        "detected": detected,
        "direction": get_direction(detected),
        "accept_language_header": accept_lang,
    }


@router.get("/format/number")
def fmt_number(
    value: float = Query(..., description="Number to format"),
    lang: Optional[str] = Query(None),
    decimals: int = Query(2, ge=0, le=10),
):
    """Format a number with locale-appropriate separators."""
    return {
        "value": value,
        "formatted": format_number(value, lang=lang, decimals=decimals),
        "language": lang or "en",
    }


@router.get("/format/currency")
def fmt_currency(
    value: float = Query(..., description="Amount to format"),
    currency: str = Query("SAR", description="Currency code"),
    lang: Optional[str] = Query(None),
):
    """Format a currency value with locale-appropriate symbol and separators."""
    return {
        "value": value,
        "currency": currency,
        "formatted": format_currency(value, currency=currency, lang=lang),
        "language": lang or "en",
    }


@router.get("/format/percentage")
def fmt_percentage(
    value: float = Query(..., description="Percentage to format"),
    lang: Optional[str] = Query(None),
    decimals: int = Query(1, ge=0, le=5),
):
    """Format a percentage."""
    return {
        "value": value,
        "formatted": format_percentage(value, lang=lang, decimals=decimals),
        "language": lang or "en",
    }