"""Globalization Engine router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from .schemas import (
    CountryCreate,
    CountryPackCreate,
    CountryPackResponse,
    CountryResponse,
    CurrencyCreate,
    CurrencyResponse,
    ExchangeRateCreate,
    ExchangeRateResponse,
    FiscalPeriodCreate,
    FiscalPeriodResponse,
    NumberingSequenceCreate,
    NumberingSequenceResponse,
    TaxConfigCreate,
    TaxConfigResponse,
)
from .service import GlobalizationService
from ..tenant import require_tenant

router = APIRouter(prefix="/api/v1/globalization", tags=["globalization"])


# Countries

@router.post("/countries", response_model=CountryResponse, status_code=201)
def create_country(
    payload: CountryCreate,
    db: Session = Depends(get_db),
) -> CountryResponse:
    svc = GlobalizationService(db)
    country = svc.create_country(payload.model_dump())
    return CountryResponse.model_validate(country)


@router.get("/countries", response_model=list[CountryResponse])
def list_countries(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[CountryResponse]:
    svc = GlobalizationService(db)
    countries = svc.list_countries(limit=limit)
    return [CountryResponse.model_validate(c) for c in countries]


@router.get("/countries/{country_code}", response_model=CountryResponse)
def get_country(
    country_code: str,
    db: Session = Depends(get_db),
) -> CountryResponse:
    svc = GlobalizationService(db)
    country = svc.get_country(country_code)
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    return CountryResponse.model_validate(country)


# Country Packs

@router.post("/packs", response_model=CountryPackResponse, status_code=201)
def create_country_pack(
    payload: CountryPackCreate,
    db: Session = Depends(get_db),
) -> CountryPackResponse:
    svc = GlobalizationService(db)
    pack = svc.create_country_pack(payload.model_dump())
    return CountryPackResponse.model_validate(pack)


@router.get("/packs", response_model=list[CountryPackResponse])
def list_country_packs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[CountryPackResponse]:
    svc = GlobalizationService(db)
    packs = svc.list_country_packs(limit=limit)
    return [CountryPackResponse.model_validate(p) for p in packs]


@router.get("/packs/{country_code}", response_model=CountryPackResponse)
def get_country_pack(
    country_code: str,
    db: Session = Depends(get_db),
) -> CountryPackResponse:
    svc = GlobalizationService(db)
    pack = svc.get_country_pack(country_code)
    if not pack:
        raise HTTPException(status_code=404, detail="Country pack not found")
    return CountryPackResponse.model_validate(pack)


# Currencies

@router.post("/currencies", response_model=CurrencyResponse, status_code=201)
def create_currency(
    payload: CurrencyCreate,
    db: Session = Depends(get_db),
) -> CurrencyResponse:
    svc = GlobalizationService(db)
    currency = svc.create_currency(payload.model_dump())
    return CurrencyResponse.model_validate(currency)


@router.get("/currencies", response_model=list[CurrencyResponse])
def list_currencies(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[CurrencyResponse]:
    svc = GlobalizationService(db)
    currencies = svc.list_currencies(limit=limit)
    return [CurrencyResponse.model_validate(c) for c in currencies]


@router.get("/currencies/{currency_code}", response_model=CurrencyResponse)
def get_currency(
    currency_code: str,
    db: Session = Depends(get_db),
) -> CurrencyResponse:
    svc = GlobalizationService(db)
    currency = svc.get_currency(currency_code)
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    return CurrencyResponse.model_validate(currency)


# Exchange Rates

@router.post("/exchange-rates", response_model=ExchangeRateResponse, status_code=201)
def create_exchange_rate(
    payload: ExchangeRateCreate,
    db: Session = Depends(get_db),
) -> ExchangeRateResponse:
    svc = GlobalizationService(db)
    rate = svc.create_exchange_rate(payload.model_dump())
    return ExchangeRateResponse.model_validate(rate)


@router.get("/exchange-rates", response_model=list[ExchangeRateResponse])
def list_exchange_rates(
    from_currency: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[ExchangeRateResponse]:
    svc = GlobalizationService(db)
    rates = svc.list_exchange_rates(from_currency=from_currency, limit=limit)
    return [ExchangeRateResponse.model_validate(r) for r in rates]


@router.post("/convert")
def convert_amount(
    amount: int = Query(..., ge=0),
    from_currency: str = Query(..., min_length=3, max_length=3),
    to_currency: str = Query(..., min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> dict:
    svc = GlobalizationService(db)
    result = svc.convert_amount(amount, from_currency, to_currency)
    if not result:
        raise HTTPException(status_code=404, detail="Exchange rate not found")
    return result


# Tax Configs

@router.post("/tax-configs", response_model=TaxConfigResponse, status_code=201)
def create_tax_config(
    payload: TaxConfigCreate,
    db: Session = Depends(get_db),
) -> TaxConfigResponse:
    svc = GlobalizationService(db)
    tax = svc.create_tax_config(payload.model_dump())
    return TaxConfigResponse.model_validate(tax)


@router.get("/tax-configs/{country_code}", response_model=list[TaxConfigResponse])
def get_tax_configs(
    country_code: str,
    db: Session = Depends(get_db),
) -> list[TaxConfigResponse]:
    svc = GlobalizationService(db)
    configs = svc.get_tax_configs(country_code)
    return [TaxConfigResponse.model_validate(c) for c in configs]


# Numbering Sequences

@router.post("/sequences", response_model=NumberingSequenceResponse, status_code=201)
def create_numbering_sequence(
    payload: NumberingSequenceCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> NumberingSequenceResponse:
    svc = GlobalizationService(db)
    seq = svc.create_numbering_sequence(str(tenant_id), payload.model_dump())
    return NumberingSequenceResponse.model_validate(seq)


@router.get("/sequences", response_model=list[NumberingSequenceResponse])
def list_numbering_sequences(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[NumberingSequenceResponse]:
    svc = GlobalizationService(db)
    seqs = svc.list_numbering_sequences(str(tenant_id))
    return [NumberingSequenceResponse.model_validate(s) for s in seqs]


@router.post("/sequences/next")
def get_next_number(
    entity_type: str = Query(..., min_length=1, max_length=100),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    svc = GlobalizationService(db)
    number = svc.get_next_number(str(tenant_id), entity_type)
    if not number:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return {"entity_type": entity_type, "next_number": number}


# Fiscal Periods

@router.post("/fiscal-periods", response_model=FiscalPeriodResponse, status_code=201)
def create_fiscal_period(
    payload: FiscalPeriodCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> FiscalPeriodResponse:
    svc = GlobalizationService(db)
    period = svc.create_fiscal_period(str(tenant_id), payload.model_dump())
    return FiscalPeriodResponse.model_validate(period)


@router.get("/fiscal-periods", response_model=list[FiscalPeriodResponse])
def list_fiscal_periods(
    fiscal_year: int | None = Query(default=None),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[FiscalPeriodResponse]:
    svc = GlobalizationService(db)
    periods = svc.list_fiscal_periods(str(tenant_id), fiscal_year=fiscal_year)
    return [FiscalPeriodResponse.model_validate(p) for p in periods]


@router.post("/fiscal-periods/{period_id}/close", response_model=FiscalPeriodResponse)
def close_fiscal_period(
    period_id: str,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> FiscalPeriodResponse:
    svc = GlobalizationService(db)
    period = svc.close_fiscal_period(period_id, str(tenant_id), str(request.state.user_id))
    if not period:
        raise HTTPException(status_code=404, detail="Period not found or already closed")
    return FiscalPeriodResponse.model_validate(period)


# ---------------------------------------------------------------------------
# Egypt Pack endpoints
# ---------------------------------------------------------------------------

@router.get("/egypt/pack/initialize")
def initialize_egypt_pack(
    db: Session = Depends(get_db),
) -> dict:
    """Initialize the Egypt Pack (idempotent - safe to call multiple times)"""
    from .egypt_pack import EgyptPackService
    svc = EgyptPackService(db)
    result = svc.initialize_egypt_pack()
    return {
        "status": result["status"],
        "country": result["country"].code if result["country"] else None,
        "currency": result["currency"].code if result["currency"] else None,
        "pack_version": result["pack"].pack_version if result["pack"] else None,
        "tax_configs_count": len(result["tax_configs"]),
    }


@router.get("/egypt/vat/calculate")
def calculate_egypt_vat(
    taxable_amount: int = Query(..., ge=0),
    tax_category: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    """Calculate Egyptian VAT for a taxable amount"""
    from .egypt_pack import EgyptPackService
    svc = EgyptPackService(db)
    return svc.calculate_egypt_vat(taxable_amount, tax_category)


@router.post("/egypt/e-invoice/generate")
def generate_egypt_e_invoice(
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    """Generate Egyptian e-invoice in ETA format"""
    from .egypt_pack import EgyptPackService
    svc = EgyptPackService(db)
    return svc.generate_egypt_e_invoice(payload)


@router.get("/egypt/reports/vat-quarterly")
def get_vat_return_quarterly(
    quarter: int = Query(..., ge=1, le=4),
    fiscal_year: int = Query(..., ge=2020, le=2100),
    tenant_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    """Generate Egyptian quarterly VAT return"""
    from .egypt_pack import EgyptPackService
    svc = EgyptPackService(db)
    return svc.generate_vat_return_quarterly(tenant_id, quarter, fiscal_year)


@router.get("/egypt/reports/income-tax-annual")
def get_income_tax_return_annual(
    fiscal_year: int = Query(..., ge=2020, le=2100),
    tenant_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    """Generate Egyptian annual income tax return"""
    from .egypt_pack import EgyptPackService
    svc = EgyptPackService(db)
    return svc.generate_income_tax_return_annual(tenant_id, fiscal_year)


@router.get("/egypt/reports/withholding-tax-monthly")
def get_withholding_tax_monthly(
    month: int = Query(..., ge=1, le=12),
    fiscal_year: int = Query(..., ge=2020, le=2100),
    tenant_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    """Generate Egyptian monthly employee withholding tax report"""
    from .egypt_pack import EgyptPackService
    svc = EgyptPackService(db)
    return svc.generate_employee_withholding_tax_monthly(tenant_id, month, fiscal_year)


@router.get("/egypt/fiscal/quarters")
def get_egypt_fiscal_quarters(
    fiscal_year: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get Egypt fiscal quarters for a year"""
    from .egypt_pack import EgyptPackService
    svc = EgyptPackService(db)
    return svc.get_quarters_in_year(fiscal_year)


@router.get("/egypt/fiscal/current-quarter")
def get_current_egypt_fiscal_quarter(
    db: Session = Depends(get_db),
) -> dict:
    """Get current Egypt fiscal quarter"""
    from .egypt_pack import EgyptPackService
    svc = EgyptPackService(db)
    return svc.get_current_fiscal_quarter()


@router.get("/egypt/numberings-patterns")
def get_egypt_numbering_patterns(
    db: Session = Depends(get_db),
) -> dict:
    """Get Egypt-standard numbering patterns for all entity types"""
    from .egypt_pack import EgyptPackService
    svc = EgyptPackService(db)
    patterns = {}
    for entity_type in ["invoice", "contract", "purchase_order", "quotation", "payment", "employee", "asset"]:
        patterns[entity_type] = svc.get_egypt_numbering_pattern(entity_type)
    return {"country_code": "EG", "patterns": patterns}


@router.get("/ksa/pack/initialize")
def initialize_ksa_pack(
    db: Session = Depends(get_db),
) -> dict:
    """Initialize the Saudi Arabia Pack (idempotent - safe to call multiple times)"""
    from .saudi_pack import KSAPackService
    svc = KSAPackService(db)
    result = svc.initialize_ksa_pack()
    return {
        "status": result["status"],
        "country": result["country"].code if result["country"] else None,
        "currency": result["currency"].code if result["currency"] else None,
        "pack_version": result["pack"].pack_version if result["pack"] else None,
        "tax_configs_count": len(result["tax_configs"]),
    }


@router.get("/ksa/vat/calculate")
def calculate_ksa_vat(
    taxable_amount: float = Query(..., ge=0),
    tax_category: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    """Calculate Saudi VAT for a taxable amount"""
    from .saudi_pack import KSAPackService
    svc = KSAPackService(db)
    return svc.calculate_ksa_vat(taxable_amount, tax_category)


@router.post("/ksa/e-invoice/generate")
def generate_ksa_e_invoice(
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    """Generate Saudi e-invoice in ZATCA Fatoora format"""
    from .saudi_pack import KSAPackService
    svc = KSAPackService(db)
    return svc.generate_ksa_e_invoice(payload)


@router.get("/ksa/reports/vat-quarterly")
def get_ksa_vat_return_quarterly(
    quarter: int = Query(..., ge=1, le=4),
    fiscal_year: int = Query(..., ge=2020, le=2100),
    tenant_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    """Generate Saudi quarterly VAT return (ZATCA format)"""
    from .saudi_pack import KSAPackService
    svc = KSAPackService(db)
    return svc.generate_ksa_vat_return_quarterly(tenant_id, quarter, fiscal_year)


@router.get("/ksa/reports/zakat-annual")
def get_ksa_zakat_return_annual(
    fiscal_year: int = Query(..., ge=2020, le=2100),
    tenant_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    """Generate Saudi annual Zakat return"""
    from .saudi_pack import KSAPackService
    svc = KSAPackService(db)
    return svc.generate_ksa_zakat_return_annual(tenant_id, fiscal_year)


@router.get("/ksa/reports/withholding-tax-monthly")
def get_ksa_withholding_tax_monthly(
    month: int = Query(..., ge=1, le=12),
    fiscal_year: int = Query(..., ge=2020, le=2100),
    tenant_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> dict:
    """Generate Saudi monthly withholding tax report"""
    from .saudi_pack import KSAPackService
    svc = KSAPackService(db)
    return svc.generate_ksa_withholding_tax(tenant_id, fiscal_year, month)


@router.get("/ksa/fiscal/quarters")
def get_ksa_fiscal_quarters(
    fiscal_year: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get KSA fiscal quarters for a year"""
    from .saudi_pack import KSAPackService
    svc = KSAPackService(db)
    return svc.get_quarters_in_year(fiscal_year)


@router.get("/ksa/fiscal/current-quarter")
def get_current_ksa_fiscal_quarter(
    db: Session = Depends(get_db),
) -> dict:
    """Get current KSA fiscal quarter"""
    from .saudi_pack import KSAPackService
    svc = KSAPackService(db)
    return svc.get_current_fiscal_quarter()


@router.get("/ksa/numbering-patterns")
def get_saudi_numbering_patterns(
    db: Session = Depends(get_db),
) -> dict:
    """Get Saudi-standard numbering patterns for all entity types"""
    from .saudi_pack import KSAPackService
    svc = KSAPackService(db)
    patterns = {}
    for entity_type in [
        "invoice", "contract", "purchase_order", "quotation",
        "payment", "employee", "asset", "proposal",
    ]:
        patterns[entity_type] = svc.get_saudi_numbering_pattern(entity_type)
    return {"country_code": "SA", "patterns": patterns}


class EgyptVATCalculateRequest(BaseModel):
    taxable_amount: int = Field(ge=0)
    tax_category: str | None = Field(default=None, max_length=50)


class EgyptEInvoiceRequest(BaseModel):
    invoice_number: str = Field(min_length=1)
    invoice_date: str = Field(min_length=1)
    seller_name: str = Field(min_length=1)
    seller_tax_id: str = Field(min_length=1)
    buyer_name: str = Field(min_length=1)
    buyer_tax_id: str = Field(min_length=1)
    items: list[dict] = Field(min_length=1)
    seller_address: str | None = None
    seller_phone: str | None = None
    seller_email: str | None = None
    buyer_address: str | None = None
    buyer_phone: str | None = None
    buyer_email: str | None = None

class TaxCalculationRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    tax_type: str = Field(min_length=1, max_length=50)
    subtotal: int = Field(ge=0)
    tax_region: str | None = None


class TaxCalculationBatchRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    tax_region: str | None = None
    items: list[TaxCalculationItem] = Field(min_length=1)


class TaxCalculationItem(BaseModel):
    tax_type: str = Field(min_length=1, max_length=50)
    amount: int = Field(ge=0)


@router.post("/tax-configs/calculate")
def calculate_tax(
    payload: TaxCalculationRequest,
    db: Session = Depends(get_db),
):
    svc = GlobalizationService(db)
    result = svc.calculate_tax(
        country_code=payload.country_code,
        tax_type=payload.tax_type,
        subtotal=payload.subtotal,
        tax_region=payload.tax_region,
    )
    if not result:
        raise HTTPException(status_code=404, detail="No tax config found")
    return result


def get_quarters_in_year(self, fiscal_year: int) -> list[dict]:
    """Get Saudi Arabia fiscal quarters for a year"""
    return [
        {"quarter": 1, "name": "Q1", "start": f"{fiscal_year}-01-01", "end": f"{fiscal_year}-03-31"},
        {"quarter": 2, "name": "Q2", "start": f"{fiscal_year}-04-01", "end": f"{fiscal_year}-06-30"},
        {"quarter": 3, "name": "Q3", "start": f"{fiscal_year}-07-01", "end": f"{fiscal_year}-09-30"},
        {"quarter": 4, "name": "Q4", "start": f"{fiscal_year}-10-01", "end": f"{fiscal_year}-12-31"},
    ]


def get_current_fiscal_quarter(self, date: datetime | None = None) -> dict:
    """Get current Saudi Arabia fiscal quarter"""
    now = date or datetime.now()
    month = now.month

    if month <= 3:
        return {"quarter": 1, "name": "Q1", "start": f"{now.year}-01-01", "end": f"{now.year}-03-31"}
    elif month <= 6:
        return {"quarter": 2, "name": "Q2", "start": f"{now.year}-04-01", "end": f"{now.year}-06-30"}
    elif month <= 9:
        return {"quarter": 3, "name": "Q3", "start": f"{now.year}-07-01", "end": f"{now.year}-09-30"}
    else:
        return {"quarter": 4, "name": "Q4", "start": f"{now.year}-10-01", "end": f"{now.year}-12-31"}


def get_saudi_numbering_pattern(self, entity_type: str) -> dict:
    """Get Saudi-standard numbering pattern for entity type"""
    patterns = {
        "invoice": {"prefix": "FATOORA", "padding": 8, "suffix": ""},
        "contract": {"prefix": "MUAWA", "padding": 6, "suffix": ""},
        "purchase_order": {"prefix": "PO", "padding": 6, "suffix": ""},
        "quotation": {"prefix": "Q", "padding": 6, "suffix": ""},
        "payment": {"prefix": "PAY", "padding": 6, "suffix": ""},
        "employee": {"prefix": "EMP", "padding": 4, "suffix": ""},
        "asset": {"prefix": "AST", "padding": 6, "suffix": ""},
        "proposal": {"prefix": "PROP", "padding": 6, "suffix": ""},
    }
    return patterns.get(
        entity_type,
        {"prefix": entity_type[:4].upper(), "padding": 6, "suffix": ""}
    )


@router.post("/tax-configs/calculate-batch")
def calculate_taxes_batch(
    payload: TaxCalculationBatchRequest,
    db: Session = Depends(get_db),
):
    svc = GlobalizationService(db)
    return svc.calculate_taxes(
        country_code=payload.country_code,
        items=[item.model_dump() for item in payload.items],
        tax_region=payload.tax_region,
    )


# ---------------------------------------------------------------------------
# Live Exchange Rates endpoint
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Pluggable Pack Registry endpoints
# ---------------------------------------------------------------------------

@router.get("/packs/registry")
def list_pack_registry() -> list[dict]:
    """List all registered country packs with full metadata."""
    from .pack_registry import list_registrations
    return list_registrations()


@router.get("/packs/registry/{country_code}")
def get_pack_registry_info(country_code: str) -> dict:
    """Get pack info for a country code."""
    from .pack_registry import get_pack_info
    info = get_pack_info(country_code)
    if not info:
        raise HTTPException(status_code=404, detail=f"No pack for {country_code}")
    return {"country_code": info["country_code"], "name": info["name"]}


@router.get("/packs/registry/{country_code}/initialize")
def initialize_pack_via_registry(country_code: str, db: Session = Depends(get_db)) -> dict:
    """Initialize a registered pack for the given country (idempotent)."""
    from .pack_registry import initialize_pack
    try:
        result = initialize_pack(country_code, db)
        return {
            "status": result.get("status", "initialized"),
            "country": result["country"].code if result.get("country") else country_code,
            "currency": result["currency"].code if result.get("currency") else None,
            "pack_version": result["pack"].pack_version if result.get("pack") else None,
            "tax_configs_count": len(result.get("tax_configs", [])),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Live Exchange Rates endpoint
# ---------------------------------------------------------------------------

@router.get("/exchange-rates/live")
def get_live_exchange_rates(
    base: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
):
    """Fetch live exchange rates from a free public API."""
    import httpx

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"https://open.er-api.com/v6/latest/{base.upper()}"
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "base": data.get("base_code", base.upper()),
                    "rates": data.get("rates", {}),
                    "time_last_update_utc": data.get("time_last_update_utc"),
                    "result": data.get("result"),
                }
    except Exception:
        pass

    # Fallback: use stored rates from database
    svc = GlobalizationService(db)
    stored = svc.list_exchange_rates(from_currency=base, limit=50)
    return {
        "base": base.upper(),
        "rates": {r.to_currency: r.rate for r in stored},
        "source": "database",
        "result": "success",
    }
