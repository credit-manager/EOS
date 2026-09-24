"""Integration Hub models."""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text

from ..db import Base


class WebhookStatus(str, Enum):
    pending = "pending"
    delivered = "delivered"
    failed = "failed"
    dead_letter = "dead_letter"


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    integration_type = Column(String(50), nullable=False)
    provider = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    config = Column(JSON, nullable=True)
    credentials = Column(JSON, nullable=True)
    rate_limit = Column(Integer, nullable=True)
    timeout_seconds = Column(Integer, nullable=False, default=30)
    retry_count = Column(Integer, nullable=False, default=3)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntegrationEndpoint(Base):
    __tablename__ = "integration_endpoints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False, default="GET")
    path = Column(String(500), nullable=False)
    headers = Column(JSON, nullable=True)
    body_template = Column(JSON, nullable=True)
    response_mapping = Column(JSON, nullable=True)
    error_mapping = Column(JSON, nullable=True)
    timeout_seconds = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntegrationMapping(Base):
    __tablename__ = "integration_mappings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    source_entity = Column(String(100), nullable=False)
    target_entity = Column(String(100), nullable=False)
    field_mappings = Column(JSON, nullable=True)
    transform_rules = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    endpoint_name = Column(String(200), nullable=True)
    direction = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False)
    request_method = Column(String(10), nullable=True)
    request_url = Column(String(1000), nullable=True)
    request_headers = Column(JSON, nullable=True)
    request_body = Column(JSON, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntegrationSecret(Base):
    __tablename__ = "integration_secrets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    secret_key = Column(String(200), nullable=False)
    secret_value_encrypted = Column(Text, nullable=False)
    secret_type = Column(String(50), nullable=False, default="api_key")
    description = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookDelivery(Base):
    """Webhook delivery tracking with retry logic."""
    __tablename__ = "webhook_deliveries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    integration_id = Column(String(36), nullable=False, index=True)
    endpoint_id = Column(String(36), nullable=False, index=True)

    # Target
    url = Column(String(1000), nullable=False)
    method = Column(String(10), nullable=False, default="POST")
    headers = Column(JSON, nullable=True)
    payload = Column(JSON, nullable=False)

    # Status tracking
    status = Column(String(20), nullable=False, default=WebhookStatus.pending.value)
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)

    # Response
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timing
    scheduled_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookDeliveryAttempt(Base):
    """Individual delivery attempt log."""
    __tablename__ = "webhook_delivery_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    delivery_id = Column(String(36), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    status_code = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
