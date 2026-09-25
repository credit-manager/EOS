"""Integration Hub schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class IntegrationCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    integration_type: str = Field(..., max_length=50)
    provider: str | None = Field(default=None, max_length=100)
    config: dict | None = None
    credentials: dict | None = None
    rate_limit: int | None = Field(default=None, ge=1)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_count: int = Field(default=3, ge=0, le=10)
    is_active: bool = True


class IntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    status: str | None = Field(default=None, max_length=20)
    config: dict | None = None
    credentials: dict | None = None
    rate_limit: int | None = Field(default=None, ge=1)
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    retry_count: int | None = Field(default=None, ge=0, le=10)
    is_active: bool | None = None


class IntegrationResponse(BaseModel):
    id: str
    tenant_id: str
    code: str
    name: str
    description: str | None = None
    integration_type: str
    provider: str | None = None
    status: str
    config: dict | None = None
    rate_limit: int | None = None
    timeout_seconds: int
    retry_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EndpointCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    method: str = Field(default="GET", max_length=10)
    path: str = Field(..., min_length=1, max_length=500)
    headers: dict | None = None
    body_template: dict | None = None
    response_mapping: dict | None = None
    error_mapping: dict | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    is_active: bool = True


class EndpointUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    method: str | None = Field(default=None, max_length=10)
    path: str | None = Field(default=None, max_length=500)
    headers: dict | None = None
    body_template: dict | None = None
    response_mapping: dict | None = None
    error_mapping: dict | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    is_active: bool | None = None


class EndpointResponse(BaseModel):
    id: str
    integration_id: str
    name: str
    method: str
    path: str
    headers: dict | None = None
    body_template: dict | None = None
    response_mapping: dict | None = None
    error_mapping: dict | None = None
    timeout_seconds: int | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MappingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    source_entity: str = Field(..., min_length=1, max_length=100)
    target_entity: str = Field(..., min_length=1, max_length=100)
    field_mappings: dict | None = None
    transform_rules: dict | None = None
    is_active: bool = True


class MappingUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    source_entity: str | None = Field(default=None, max_length=100)
    target_entity: str | None = Field(default=None, max_length=100)
    field_mappings: dict | None = None
    transform_rules: dict | None = None
    is_active: bool | None = None


class MappingResponse(BaseModel):
    id: str
    integration_id: str
    name: str
    source_entity: str
    target_entity: str
    field_mappings: dict | None = None
    transform_rules: dict | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationLogResponse(BaseModel):
    id: str
    integration_id: str
    endpoint_name: str | None = None
    direction: str
    status: str
    request_method: str | None = None
    request_url: str | None = None
    request_headers: dict | None = None
    request_body: dict | None = None
    response_status: int | None = None
    response_body: dict | None = None
    error_message: str | None = None
    duration_ms: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class IntegrationTestRequest(BaseModel):
    endpoint_name: str = Field(..., min_length=1, max_length=200)
    test_data: dict | None = None


class IntegrationTestResult(BaseModel):
    success: bool
    status_code: int | None = None
    response_body: dict | None = None
    error_message: str | None = None
    duration_ms: float | None = None


class SecretCreate(BaseModel):
    secret_key: str = Field(..., min_length=1, max_length=200)
    secret_value: str = Field(..., min_length=1)
    secret_type: str = Field(default="api_key", max_length=50)
    description: str | None = None
    expires_at: datetime | None = None


class SecretResponse(BaseModel):
    id: str
    integration_id: str
    secret_key: str
    secret_type: str
    description: str | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Webhook Delivery schemas

class WebhookDeliveryCreate(BaseModel):
    url: str = Field(..., min_length=1, max_length=1000)
    method: str = Field(default="POST", max_length=10)
    headers: dict | None = None
    payload: dict = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=10)
    scheduled_at: datetime | None = None


class WebhookDeliveryResponse(BaseModel):
    id: str
    tenant_id: str
    integration_id: str
    endpoint_id: str
    url: str
    method: str
    headers: dict | None = None
    payload: dict
    status: str
    attempt_count: int
    max_attempts: int
    response_status: int | None = None
    response_body: dict | None = None
    error_message: str | None = None
    scheduled_at: datetime | None = None
    delivered_at: datetime | None = None
    next_retry_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryAttemptResponse(BaseModel):
    id: str
    delivery_id: str
    attempt_number: int
    status_code: int | None = None
    response_body: dict | None = None
    error_message: str | None = None
    duration_ms: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookProcessResult(BaseModel):
    processed: int
    delivered: int
    failed: int
    dead_letter: int
