"""Developer SDK schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class SDKAppCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    app_type: str = Field(default="plugin", max_length=50)
    version: str = Field(default="1.0.0", max_length=20)
    author: str | None = Field(default=None, max_length=200)
    homepage: str | None = Field(default=None, max_length=500)
    config: dict | None = None
    permissions: list[str] | None = None
    dependencies: list[str] | None = None


class SDKAppResponse(BaseModel):
    id: str
    tenant_id: str
    code: str
    name: str
    description: str | None = None
    app_type: str
    version: str
    author: str | None = None
    homepage: str | None = None
    config: dict | None = None
    permissions: list[str] | None = None
    dependencies: list[str] | None = None
    is_active: bool
    is_installed: bool
    installed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SDKWebhookCreate(BaseModel):
    app_id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    event_type: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=1000)
    secret: str | None = Field(default=None, max_length=200)
    headers: dict | None = None
    retry_count: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class SDKWebhookResponse(BaseModel):
    id: str
    tenant_id: str
    app_id: str
    code: str
    name: str
    event_type: str
    url: str
    secret: str | None = None
    headers: dict | None = None
    is_active: bool
    retry_count: int
    timeout_seconds: int
    last_triggered_at: datetime | None = None
    trigger_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class SDKAPIKeyCreate(BaseModel):
    app_id: str | None = None
    name: str = Field(..., min_length=1, max_length=200)
    scopes: list[str] | None = None
    rate_limit: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None


class SDKAPIKeyResponse(BaseModel):
    id: str
    tenant_id: str
    app_id: str | None = None
    name: str
    key_prefix: str
    scopes: list[str] | None = None
    rate_limit: int | None = None
    expires_at: datetime | None = None
    is_active: bool
    last_used_at: datetime | None = None
    use_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class SDKAPIKeyCreatedResponse(SDKAPIKeyResponse):
    key: str


class SDKPluginCreate(BaseModel):
    app_id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    plugin_type: str = Field(..., max_length=50)
    entry_point: str | None = Field(default=None, max_length=500)
    config_schema: dict | None = None
    default_config: dict | None = None


class SDKPluginResponse(BaseModel):
    id: str
    tenant_id: str
    app_id: str
    code: str
    name: str
    description: str | None = None
    plugin_type: str
    entry_point: str | None = None
    config_schema: dict | None = None
    default_config: dict | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SDKEndpointCreate(BaseModel):
    app_id: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1, max_length=500)
    method: str = Field(..., max_length=10)
    description: str | None = None
    request_schema: dict | None = None
    response_schema: dict | None = None
    middleware: list[str] | None = None


class SDKEndpointResponse(BaseModel):
    id: str
    tenant_id: str
    app_id: str
    path: str
    method: str
    description: str | None = None
    request_schema: dict | None = None
    response_schema: dict | None = None
    middleware: list[str] | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SDKEventResponse(BaseModel):
    id: str
    tenant_id: str
    event_type: str
    source: str | None = None
    payload: dict | None = None
    status: str
    error_message: str | None = None
    retry_count: int
    max_retries: int
    processed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True
