"""Developer SDK router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from .schemas import (
    SDKAPIKeyCreate,
    SDKAPIKeyCreatedResponse,
    SDKAPIKeyResponse,
    SDKAppCreate,
    SDKAppResponse,
    SDKEndpointCreate,
    SDKEndpointResponse,
    SDKEventResponse,
    SDKPluginCreate,
    SDKPluginResponse,
    SDKWebhookCreate,
    SDKWebhookResponse,
)
from .service import SDKService
from ..tenant import require_tenant

router = APIRouter(prefix="/api/v1/sdk", tags=["sdk"])


# Apps

@router.post("/apps", response_model=SDKAppResponse, status_code=201)
def create_app(
    payload: SDKAppCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SDKAppResponse:
    svc = SDKService(db)
    app = svc.create_app(str(tenant_id), payload.model_dump())
    return SDKAppResponse.model_validate(app)


@router.get("/apps", response_model=list[SDKAppResponse])
def list_apps(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[SDKAppResponse]:
    svc = SDKService(db)
    return [SDKAppResponse.model_validate(a) for a in svc.list_apps(str(tenant_id))]


@router.get("/apps/{app_id}", response_model=SDKAppResponse)
def get_app(
    app_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SDKAppResponse:
    svc = SDKService(db)
    app = svc.get_app(app_id, str(tenant_id))
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return SDKAppResponse.model_validate(app)


@router.post("/apps/{app_id}/install", response_model=SDKAppResponse)
def install_app(
    app_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SDKAppResponse:
    svc = SDKService(db)
    app = svc.install_app(app_id, str(tenant_id))
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return SDKAppResponse.model_validate(app)


# Webhooks

@router.post("/webhooks", response_model=SDKWebhookResponse, status_code=201)
def create_webhook(
    payload: SDKWebhookCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SDKWebhookResponse:
    svc = SDKService(db)
    webhook = svc.create_webhook(str(tenant_id), payload.model_dump())
    return SDKWebhookResponse.model_validate(webhook)


@router.get("/webhooks", response_model=list[SDKWebhookResponse])
def list_webhooks(
    app_id: str | None = Query(default=None),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[SDKWebhookResponse]:
    svc = SDKService(db)
    return [SDKWebhookResponse.model_validate(w) for w in svc.list_webhooks(str(tenant_id), app_id=app_id)]


# API Keys

@router.post("/api-keys", response_model=SDKAPIKeyCreatedResponse, status_code=201)
def create_api_key(
    payload: SDKAPIKeyCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SDKAPIKeyCreatedResponse:
    svc = SDKService(db)
    api_key, raw_key = svc.create_api_key(str(tenant_id), payload.model_dump())
    result = SDKAPIKeyCreatedResponse.model_validate(api_key)
    result.key = raw_key
    return result


@router.get("/api-keys", response_model=list[SDKAPIKeyResponse])
def list_api_keys(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[SDKAPIKeyResponse]:
    svc = SDKService(db)
    return [SDKAPIKeyResponse.model_validate(k) for k in svc.list_api_keys(str(tenant_id))]


# Plugins

@router.post("/plugins", response_model=SDKPluginResponse, status_code=201)
def create_plugin(
    payload: SDKPluginCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SDKPluginResponse:
    svc = SDKService(db)
    plugin = svc.create_plugin(str(tenant_id), payload.model_dump())
    return SDKPluginResponse.model_validate(plugin)


@router.get("/plugins", response_model=list[SDKPluginResponse])
def list_plugins(
    app_id: str | None = Query(default=None),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[SDKPluginResponse]:
    svc = SDKService(db)
    return [SDKPluginResponse.model_validate(p) for p in svc.list_plugins(str(tenant_id), app_id=app_id)]


# Endpoints

@router.post("/endpoints", response_model=SDKEndpointResponse, status_code=201)
def create_endpoint(
    payload: SDKEndpointCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SDKEndpointResponse:
    svc = SDKService(db)
    endpoint = svc.create_endpoint(str(tenant_id), payload.model_dump())
    return SDKEndpointResponse.model_validate(endpoint)


@router.get("/endpoints", response_model=list[SDKEndpointResponse])
def list_endpoints(
    app_id: str | None = Query(default=None),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[SDKEndpointResponse]:
    svc = SDKService(db)
    return [SDKEndpointResponse.model_validate(e) for e in svc.list_endpoints(str(tenant_id), app_id=app_id)]


# Events

@router.get("/events", response_model=list[SDKEventResponse])
def list_events(
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[SDKEventResponse]:
    svc = SDKService(db)
    return [SDKEventResponse.model_validate(e) for e in svc.list_events(str(tenant_id), event_type=event_type, status=status, limit=limit)]


@router.get("/events/stats")
def get_event_stats(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    svc = SDKService(db)
    return svc.get_event_stats(str(tenant_id))
