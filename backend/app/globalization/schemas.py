"""Globalization Engine schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class CountryCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=3)
    name: str = Field(..., min_length=1, max_length=200)
    native_name: str | None = Field(default=None, max_length=200)
    currency_code: str = Field(..., min_length=3, max_length=3)
    currency_name: str = Field(..., min_length=1, max_length=100)
    currency_symbol: str | None = Field(default=None, max_length=10)
    language_code: str = Field(..., min_length=2, max_length=10)
    language_name: str = Field(..., min_length=1, max_length=100)
    timezone: str = Field(..., min_length=1, max_length=50)
    phone_code: str | None = Field(default=None, max_length=10)
    date_format: str = Field(default="DD/MM/YYYY", max_length=20)
    number_format: str = Field(default="#,##0.00", max_length=20)


class CountryResponse(BaseModel):
    id: str
    code: str
    name: str
    native_name: str | None = None
    currency_code: str
    currency_name: str
    currency_symbol: str | None = None
    language_code: str
    language_name: str
    timezone: str
    phone_code: str | None = None
    date_format: str
    number_format: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CountryPackCreate(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=3)
    pack_name: str = Field(..., min_length=1, max_length=200)
    pack_version: str = Field(default="1.0.0", max_length=20)
    pack_config: dict | None = None
    tax_config: dict | None = None
    accounting_config: dict | None = None
    e_invoice_config: dict | None = None
    compliance_config: dict | None = None
    fiscal_calendar: dict | None = None
    statutory_reports: dict | None = None


class CountryPackResponse(BaseModel):
    id: str
    country_code: str
    pack_name: str
    pack_version: str
    pack_config: dict | None = None
    tax_config: dict | None = None
    accounting_config: dict | None = None
    e_invoice_config: dict | None = None
    compliance_config: dict | None = None
    fiscal_calendar: dict | None = None
    statutory_reports: dict | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CurrencyCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=3)
    name: str = Field(..., min_length=1, max_length=100)
    symbol: str | None = Field(default=None, max_length=10)
    decimal_places: int = Field(default=2, ge=0, le=10)


class CurrencyResponse(BaseModel):
    id: str
    code: str
    name: str
    symbol: str | None = None
    decimal_places: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ExchangeRateCreate(BaseModel):
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)
    rate: int = Field(..., gt=0)
    rate_date: datetime
    source: str | None = Field(default=None, max_length=100)


class ExchangeRateResponse(BaseModel):
    id: str
    from_currency: str
    to_currency: str
    rate: int
    rate_date: datetime
    source: str | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TaxConfigCreate(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=3)
    tax_type: str = Field(..., min_length=1, max_length=50)
    tax_name: str = Field(..., min_length=1, max_length=200)
    tax_rate: int = Field(..., ge=0, le=10000)
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class TaxConfigResponse(BaseModel):
    id: str
    country_code: str
    tax_type: str
    tax_name: str
    tax_rate: int
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NumberingSequenceCreate(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=100)
    prefix: str | None = Field(default=None, max_length=50)
    suffix: str | None = Field(default=None, max_length=50)
    next_value: int = Field(default=1, ge=0)
    padding: int = Field(default=6, ge=1, le=20)
    format_pattern: str | None = Field(default=None, max_length=200)
    fiscal_year_based: bool = False


class NumberingSequenceResponse(BaseModel):
    id: str
    tenant_id: str
    entity_type: str
    prefix: str | None = None
    suffix: str | None = None
    next_value: int
    padding: int
    format_pattern: str | None = None
    fiscal_year_based: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FiscalPeriodCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    start_date: datetime
    end_date: datetime
    fiscal_year: int = Field(..., ge=2000, le=2100)
    period_number: int = Field(..., ge=1, le=12)


class FiscalPeriodResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    start_date: datetime
    end_date: datetime
    fiscal_year: int
    period_number: int
    is_closed: bool
    closed_at: datetime | None = None
    closed_by: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
