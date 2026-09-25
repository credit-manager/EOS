"""
Pluggable Country Pack Registry for the Globalization Engine.

Provides a single source of truth for which country packs exist,
how to instantiate them, and how to initialize them idempotently.

Add a new country pack:
    1. Create backend/app/globalization/<country>_pack.py with a <Country>PackService class
    2. Register it here in PACK_HANDLERS
    3. Call initialize_pack("XX") or use the dispatch endpoints

Pack contract (what every pack service must implement):
    - CODE: str                         -- ISO 3166-1 alpha-2 country code
    - CURRENCY: str                     -- ISO 4217 currency code
    - ensure_country() -> Country
    - ensure_currency() -> Currency
    - ensure_pack() -> CountryPack
    - ensure_tax_configs() -> list[TaxConfig]
    - initialize_pack() -> dict         -- idempotent full initialization
    - calculate_vat(taxable_amount, tax_category) -> dict
    - generate_e_invoice(payload) -> dict
    - generate_vat_return(period, fiscal_year, tenant_id) -> dict
    - generate_statutory_report(report_type, fiscal_year, tenant_id) -> dict
    - get_numbering_pattern(entity_type) -> dict
    - get_fiscal_calendar() -> dict
    - get_currency_formatting() -> dict
"""

from typing import Any

from sqlalchemy.orm import Session

from .egypt_pack import EgyptPackService
from .models import Country, CountryPack, Currency, TaxConfig
from .saudi_pack import KSAPackService

# ---------------------------------------------------------------------------
# Pack catalog
# ---------------------------------------------------------------------------

PACK_HANDLERS: dict[str, type] = {
    "EG": EgyptPackService,
    "SA": KSAPackService,
}

PACK_METADATA: dict[str, dict[str, Any]] = {
    "EG": {
        "country_code": "EG",
        "name": "Egypt Pack",
        "native_name": "حزمة مصر",
        "currency": "EGP",
        "currency_name": "Egyptian Pound",
        "currency_symbol": "ج.م",
        "language": "ar",
        "language_name": "Arabic",
        "timezone": "Africa/Cairo",
        "phone_code": "+20",
        "date_format": "DD/MM/YYYY",
        "number_format": "#,##0.00",
        "vat_rate": 14.0,
        "fiscal_year_start": 1,
        "fiscal_year_end": 12,
        "e_invoice_standard": "ETA",
        "e_invoice_authority": "Egyptian Tax Authority (ETA)",
        "documentation_url": "",
    },
    "SA": {
        "country_code": "SA",
        "name": "Saudi Arabia Pack",
        "native_name": "حزمة المملكة العربية السعودية",
        "currency": "SAR",
        "currency_name": "Saudi Riyal",
        "currency_symbol": "﷼",
        "language": "ar",
        "language_name": "Arabic",
        "timezone": "Asia/Riyadh",
        "phone_code": "+966",
        "date_format": "DD/MM/YYYY",
        "number_format": "#,##0.00",
        "vat_rate": 15.0,
        "fiscal_year_start": 1,
        "fiscal_year_end": 12,
        "e_invoice_standard": "ZATCA Fatoora",
        "e_invoice_authority": "ZATCA (Zakat, Tax and Customs Authority)",
        "documentation_url": "",
    },
}

SUPPORTED_COUNTRIES = list(PACK_HANDLERS.keys())


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------

def get_supported_countries() -> list[str]:
    """Return list of supported country codes."""
    return list(PACK_HANDLERS.keys())


def get_pack_metadata(country_code: str) -> dict[str, Any] | None:
    """Return metadata dict for a country pack, or None if not registered."""
    return PACK_METADATA.get(country_code)


def get_all_pack_metadata() -> list[dict[str, Any]]:
    """Return metadata for all registered packs."""
    return [ PACK_METADATA[code] for code in sorted(PACK_METADATA.keys()) ]


def register_pack(
    country_code: str,
    handler: type,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Register a new country pack at runtime (extension hook)."""
    PACK_HANDLERS[country_code] = handler
    if metadata:
        PACK_METADATA[country_code] = metadata


def has_pack(country_code: str) -> bool:
    """Check whether a country code has a registered pack."""
    return country_code in PACK_HANDLERS


# ---------------------------------------------------------------------------
# Public dispatch helpers used by the router
# ---------------------------------------------------------------------------

def list_packs() -> list[dict[str, Any]]:
    """Return metadata for all registered country packs."""
    return get_all_pack_metadata()


def get_pack_info(country_code: str) -> dict[str, Any] | None:
    """Return full metadata dict for a single country pack, or None."""
    return get_pack_metadata(country_code)


def list_registrations() -> list[dict[str, Any]]:
    """Return registration status for each pack (code, handler class name, metadata)."""
    return [
        {
            "country_code": code,
            "handler": handler.__name__,
            "metadata": get_pack_metadata(code),
        }
        for code, handler in sorted(PACK_HANDLERS.items())
    ]


# ---------------------------------------------------------------------------
# Initialization helpers
# ---------------------------------------------------------------------------

def _ensure_base_records(
    db: Session,
    svc: Any,
) -> dict[str, Any]:
    """Call the standard ensure_* methods on any pack service instance.

    Assumes the service exposes:
        ensure_country() -> Country
        ensure_currency() -> Currency
        ensure_pack() -> CountryPack
        ensure_tax_configs() -> list[TaxConfig]
    """
    country = svc.ensure_country()
    currency = svc.ensure_currency()
    pack = svc.ensure_pack()
    tax_configs = svc.ensure_tax_configs()
    return {
        "country": country,
        "currency": currency,
        "pack": pack,
        "tax_configs": tax_configs,
    }


def initialize_pack(country_code: str, db: Session) -> dict[str, Any]:
    """Initialize a registered country pack idempotently.

    Args:
        country_code: ISO 3166-1 alpha-2 code (e.g. "EG", "SA").
        db: SQLAlchemy session.

    Returns:
        Dict with keys: status, country, currency, pack, tax_configs.

    Raises:
        ValueError: if country_code is not registered.
    """
    handler = PACK_HANDLERS.get(country_code)
    if handler is None:
        raise ValueError(f"No pack registered for country code: {country_code}")

    svc = handler(db)
    result = _ensure_base_records(db, svc)
    result["status"] = "initialized"
    return result


def get_pack_instance(country_code: str, db: Session) -> Any:
    """Return an instantiated pack service for the given country code.

    Useful for direct service-layer access (tax calculation, e-invoice generation, etc.).

    Raises:
        ValueError: if country_code is not registered.
    """
    handler = PACK_HANDLERS.get(country_code)
    if handler is None:
        raise ValueError(f"No pack registered for country code: {country_code}")
    return handler(db)
