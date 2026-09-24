"""Developer SDK models."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from ..db import Base


class SDKApp(Base):
    __tablename__ = "sdk_apps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    app_type = Column(String(50), nullable=False, default="plugin")
    version = Column(String(20), nullable=False, default="1.0.0")
    author = Column(String(200), nullable=True)
    homepage = Column(String(500), nullable=True)
    config = Column(JSON, nullable=True)
    permissions = Column(JSON, nullable=True)
    dependencies = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_installed = Column(Boolean, nullable=False, default=False)
    installed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SDKWebhook(Base):
    __tablename__ = "sdk_webhooks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    app_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    event_type = Column(String(100), nullable=False)
    url = Column(String(1000), nullable=False)
    secret = Column(String(200), nullable=True)
    headers = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    retry_count = Column(Integer, nullable=False, default=3)
    timeout_seconds = Column(Integer, nullable=False, default=30)
    last_triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SDKAPIKey(Base):
    __tablename__ = "sdk_api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    app_id = Column(String(36), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    key_hash = Column(String(200), nullable=False)
    key_prefix = Column(String(20), nullable=False)
    scopes = Column(JSON, nullable=True)
    rate_limit = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime, nullable=True)
    use_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SDKPlugin(Base):
    __tablename__ = "sdk_plugins"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    app_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    plugin_type = Column(String(50), nullable=False)
    entry_point = Column(String(500), nullable=True)
    config_schema = Column(JSON, nullable=True)
    default_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SDKEndpoint(Base):
    __tablename__ = "sdk_endpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    app_id = Column(String(36), nullable=False, index=True)
    path = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    description = Column(Text, nullable=True)
    request_schema = Column(JSON, nullable=True)
    response_schema = Column(JSON, nullable=True)
    middleware = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SDKEvent(Base):
    __tablename__ = "sdk_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    source = Column(String(100), nullable=True)
    payload = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SDKRateLimit(Base):
    __tablename__ = "sdk_rate_limits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    api_key_id = Column(String(36), nullable=False, index=True)
    endpoint = Column(String(500), nullable=False)
    window_seconds = Column(Integer, nullable=False, default=60)
    max_requests = Column(Integer, nullable=False, default=100)
    current_count = Column(Integer, nullable=False, default=0)
    window_start = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
