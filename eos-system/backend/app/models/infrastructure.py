"""
EOS System — Infrastructure Models (Fiscal Years, Currencies, Exchange Rates, Company, Notifications, Files, Custom Fields, Number Sequences)
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class FiscalYear(Base):
    """Fiscal Year — defines accounting year boundaries."""

    __tablename__ = "fiscal_years"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False)
    is_closed = Column(Boolean, default=False)
    closed_by = Column(String(36), ForeignKey("users.id"))
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
            "is_closed": self.is_closed,
        }


class Currency(Base):
    """Currency master data."""

    __tablename__ = "currencies"

    id = Column(String(36), primary_key=True)
    code = Column(String(3), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100))
    symbol = Column(String(10))
    decimal_places = Column(Integer, default=2)
    is_base = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "symbol": self.symbol,
            "is_base": self.is_base,
        }


class ExchangeRate(Base):
    """Daily exchange rates against base currency."""

    __tablename__ = "exchange_rates"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    currency_id = Column(String(36), ForeignKey("currencies.id"), nullable=False, index=True)
    rate = Column(Numeric(18, 6), nullable=False)
    effective_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    currency = relationship("Currency")

    def to_dict(self):
        return {
            "id": self.id,
            "currency_id": self.currency_id,
            "rate": float(self.rate),
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
        }


class CompanyProfile(Base):
    """Company profile — legal entity information."""

    __tablename__ = "company_profiles"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    legal_name = Column(String(255), nullable=False)
    legal_name_ar = Column(String(255))
    trade_name = Column(String(255))
    trade_name_ar = Column(String(255))
    tax_number = Column(String(50))
    commercial_register = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(100), default="Egypt")
    phone = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))
    logo_url = Column(String(500))
    default_currency = Column(String(3), default="EGP")
    fiscal_year_start = Column(Integer, default=1)  # month (1=Jan)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "legal_name": self.legal_name,
            "tax_number": self.tax_number,
            "address": self.address,
            "country": self.country,
            "default_currency": self.default_currency,
        }


class Notification(Base):
    """User notification."""

    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    title_ar = Column(String(255))
    message = Column(Text)
    message_ar = Column(Text)
    type = Column(String(50), index=True)  # info, warning, error, success
    module = Column(String(50))  # accounting, inventory, hr, sales
    reference_type = Column(String(50))
    reference_id = Column(String(36))
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "module": self.module,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class File(Base):
    """File attachment."""

    __tablename__ = "files"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    original_name = Column(String(500))
    mime_type = Column(String(100))
    file_size = Column(Integer)
    storage_path = Column(String(1000), nullable=False)
    reference_type = Column(String(50))
    reference_id = Column(String(36))
    uploaded_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "original_name": self.original_name,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
        }


class CustomField(Base):
    """Custom field definition."""

    __tablename__ = "custom_fields"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # customer, product, employee
    field_name = Column(String(100), nullable=False)
    field_type = Column(String(50), nullable=False)  # text, number, date, select, boolean
    label = Column(String(255))
    label_ar = Column(String(255))
    options = Column(JSON)  # for select type
    is_required = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "field_name": self.field_name,
            "field_type": self.field_type,
            "label": self.label,
            "is_required": self.is_required,
        }


class NumberSequence(Base):
    """Auto-increment number sequences for documents."""

    __tablename__ = "number_sequences"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    prefix = Column(String(20))
    suffix = Column(String(20))
    current_number = Column(Integer, default=0)
    increment_by = Column(Integer, default=1)
    padding = Column(Integer, default=4)
    module = Column(String(50), index=True)  # accounting, inventory, hr, sales
    entity_type = Column(String(50), index=True)  # invoice, order, employee
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "prefix": self.prefix,
            "current_number": self.current_number,
            "module": self.module,
            "entity_type": self.entity_type,
        }
