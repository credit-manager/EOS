"""Marketplace foundation models."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text

from ..db import Base


class MarketplaceApp(Base):
    __tablename__ = "marketplace_apps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    app_type = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100), nullable=True)
    author = Column(String(200), nullable=False)
    author_id = Column(String(36), nullable=True, index=True)
    version = Column(String(20), nullable=False, default="1.0.0")
    min_eos_version = Column(String(20), nullable=True)
    max_eos_version = Column(String(20), nullable=True)
    icon_url = Column(String(500), nullable=True)
    screenshot_urls = Column(JSON, nullable=True)
    demo_url = Column(String(500), nullable=True)
    documentation_url = Column(String(500), nullable=True)
    source_code_url = Column(String(500), nullable=True)
    license_type = Column(String(50), nullable=False, default="proprietary")
    license_url = Column(String(500), nullable=True)
    pricing_model = Column(String(50), nullable=False, default="free")
    price = Column(Float, nullable=True)
    currency = Column(String(3), nullable=True)
    trial_days = Column(Integer, nullable=True)
    is_published = Column(Boolean, nullable=False, default=False)
    is_featured = Column(Boolean, nullable=False, default=False)
    is_verified = Column(Boolean, nullable=False, default=False)
    rating = Column(Float, nullable=True)
    rating_count = Column(Integer, nullable=False, default=0)
    install_count = Column(Integer, nullable=False, default=0)
    download_count = Column(Integer, nullable=False, default=0)
    tags = Column(JSON, nullable=True)
    compatibility = Column(JSON, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)


class MarketplaceCategory(Base):
    __tablename__ = "marketplace_categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    parent_id = Column(String(36), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class MarketplaceReview(Base):
    __tablename__ = "marketplace_reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    review_text = Column(Text, nullable=True)
    is_verified_purchase = Column(Boolean, nullable=False, default=False)
    is_helpful_count = Column(Integer, nullable=False, default=0)
    developer_response = Column(Text, nullable=True)
    developer_response_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketplaceInstallation(Base):
    __tablename__ = "marketplace_installations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    version = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    config = Column(JSON, nullable=True)
    license_key = Column(String(200), nullable=True)
    installed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    uninstalled_at = Column(DateTime, nullable=True)


class MarketplaceOrder(Base):
    __tablename__ = "marketplace_orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    app_id = Column(String(36), nullable=False, index=True)
    order_type = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    payment_method = Column(String(50), nullable=True)
    payment_id = Column(String(200), nullable=True)
    license_key = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class MarketplaceAuthor(Base):
    __tablename__ = "marketplace_authors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    is_organization = Column(Boolean, nullable=False, default=False)
    total_apps = Column(Integer, nullable=False, default=0)
    total_installs = Column(Integer, nullable=False, default=0)
    average_rating = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
