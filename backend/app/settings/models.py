import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text

from ..db import Base


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True, unique=True)
    company_name = Column(String(200), nullable=False, default="")
    timezone = Column(String(50), nullable=False, default="UTC")
    date_format = Column(String(20), nullable=False, default="YYYY-MM-DD")
    currency = Column(String(10), nullable=False, default="USD")
    fiscal_year_start = Column(String(5), nullable=False, default="01")
    tax_id = Column(String(100), nullable=True, default="")
    address = Column(Text, nullable=True, default="")
    phone = Column(String(50), nullable=True, default="")
    email = Column(String(200), nullable=True, default="")
    website = Column(String(200), nullable=True, default="")
    logo_url = Column(String(500), nullable=True, default="")
    notifications = Column(JSON, nullable=True, default=dict)
    appearance = Column(JSON, nullable=True, default=dict)
    security = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
