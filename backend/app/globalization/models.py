"""Globalization Engine models."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, Numeric, String

from ..db import Base


class Country(Base):
    __tablename__ = "countries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(3), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    native_name = Column(String(200), nullable=True)
    currency_code = Column(String(3), nullable=False)
    currency_name = Column(String(100), nullable=False)
    currency_symbol = Column(String(10), nullable=True)
    language_code = Column(String(10), nullable=False)
    language_name = Column(String(100), nullable=False)
    timezone = Column(String(50), nullable=False)
    phone_code = Column(String(10), nullable=True)
    date_format = Column(String(20), nullable=False, default="DD/MM/YYYY")
    number_format = Column(String(20), nullable=False, default="#,##0.00")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class CountryPack(Base):
    __tablename__ = "country_packs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    country_code = Column(String(3), nullable=False, index=True)
    pack_name = Column(String(200), nullable=False)
    pack_version = Column(String(20), nullable=False, default="1.0.0")
    pack_config = Column(JSON, nullable=True)
    tax_config = Column(JSON, nullable=True)
    accounting_config = Column(JSON, nullable=True)
    e_invoice_config = Column(JSON, nullable=True)
    compliance_config = Column(JSON, nullable=True)
    fiscal_calendar = Column(JSON, nullable=True)
    statutory_reports = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Currency(Base):
    __tablename__ = "currencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(3), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=True)
    decimal_places = Column(Integer, nullable=False, default=2)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)
    rate = Column(Numeric(12, 6), nullable=False)
    rate_date = Column(DateTime, nullable=False)
    source = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TaxConfig(Base):
    __tablename__ = "tax_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    country_code = Column(String(3), nullable=False, index=True)
    tax_type = Column(String(50), nullable=False)
    tax_name = Column(String(200), nullable=False)
    tax_rate = Column(Integer, nullable=False)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class NumberingSequence(Base):
    __tablename__ = "numbering_sequences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False)
    prefix = Column(String(50), nullable=True)
    suffix = Column(String(50), nullable=True)
    next_value = Column(Integer, nullable=False, default=1)
    padding = Column(Integer, nullable=False, default=6)
    format_pattern = Column(String(200), nullable=True)
    fiscal_year_based = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class FiscalPeriod(Base):
    __tablename__ = "fiscal_periods"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    period_number = Column(Integer, nullable=False)
    is_closed = Column(Boolean, nullable=False, default=False)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
