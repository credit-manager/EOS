"""Integration Hub router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from .schemas import (
    EndpointCreate,
    EndpointResponse,
    IntegrationCreate,
    IntegrationLogResponse,
    IntegrationResponse,
    IntegrationTestRequest,
    IntegrationTestResult,
    IntegrationUpdate,
    MappingCreate,
    MappingResponse,
    SecretCreate,
    SecretResponse,
    WebhookDeliveryCreate,
    WebhookDeliveryResponse,
    WebhookDeliveryAttemptResponse,
    WebhookProcessResult,
)
from .service import IntegrationService
from ..tenant import require_tenant

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


# --- Static routes first ---

@router.post("", response_model=IntegrationResponse, status_code=201)
def create_integration(
    payload: IntegrationCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> IntegrationResponse:
    svc = IntegrationService(db)
    integration = svc.create_integration(str(tenant_id), payload.model_dump())
    return IntegrationResponse.model_validate(integration)


@router.get("", response_model=list[IntegrationResponse])
def list_integrations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[IntegrationResponse]:
    svc = IntegrationService(db)
    items, _ = svc.list_integrations(str(tenant_id), limit=limit, offset=offset)
    return [IntegrationResponse.model_validate(i) for i in items]


@router.get("/logs", response_model=list[IntegrationLogResponse])
def list_logs(
    integration_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[IntegrationLogResponse]:
    svc = IntegrationService(db)
    logs = svc.list_logs(str(tenant_id), integration_id=integration_id, status=status, limit=limit)
    return [IntegrationLogResponse.model_validate(log) for log in logs]


# --- Dynamic routes after static ---

@router.get("/{integration_id}", response_model=IntegrationResponse)
def get_integration(
    integration_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> IntegrationResponse:
    svc = IntegrationService(db)
    integration = svc.get_integration(integration_id, str(tenant_id))
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return IntegrationResponse.model_validate(integration)


@router.patch("/{integration_id}", response_model=IntegrationResponse)
def update_integration(
    integration_id: str,
    payload: IntegrationUpdate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> IntegrationResponse:
    svc = IntegrationService(db)
    integration = svc.update_integration(integration_id, str(tenant_id), payload.model_dump(exclude_unset=True))
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return IntegrationResponse.model_validate(integration)


@router.delete("/{integration_id}", status_code=204)
def delete_integration(
    integration_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> None:
    svc = IntegrationService(db)
    if not svc.delete_integration(integration_id, str(tenant_id)):
        raise HTTPException(status_code=404, detail="Integration not found")


@router.post("/{integration_id}/endpoints", response_model=EndpointResponse, status_code=201)
def create_endpoint(
    integration_id: str,
    payload: EndpointCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> EndpointResponse:
    svc = IntegrationService(db)
    endpoint = svc.create_endpoint(integration_id, str(tenant_id), payload.model_dump())
    if not endpoint:
        raise HTTPException(status_code=404, detail="Integration not found")
    return EndpointResponse.model_validate(endpoint)


@router.get("/{integration_id}/endpoints", response_model=list[EndpointResponse])
def list_endpoints(
    integration_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[EndpointResponse]:
    svc = IntegrationService(db)
    endpoints = svc.list_endpoints(integration_id, str(tenant_id))
    return [EndpointResponse.model_validate(e) for e in endpoints]


@router.post("/{integration_id}/test", response_model=IntegrationTestResult)
def test_integration(
    integration_id: str,
    payload: IntegrationTestRequest,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> IntegrationTestResult:
    svc = IntegrationService(db)
    result = svc.test_endpoint(integration_id, str(tenant_id), payload.endpoint_name, payload.test_data)
    return IntegrationTestResult(**result)


@router.post("/{integration_id}/mappings", response_model=MappingResponse, status_code=201)
def create_mapping(
    integration_id: str,
    payload: MappingCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> MappingResponse:
    svc = IntegrationService(db)
    mapping = svc.create_mapping(integration_id, str(tenant_id), payload.model_dump())
    if not mapping:
        raise HTTPException(status_code=404, detail="Integration not found")
    return MappingResponse.model_validate(mapping)


@router.get("/{integration_id}/mappings", response_model=list[MappingResponse])
def list_mappings(
    integration_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[MappingResponse]:
    svc = IntegrationService(db)
    mappings = svc.list_mappings(integration_id, str(tenant_id))
    return [MappingResponse.model_validate(m) for m in mappings]


@router.post("/{integration_id}/secrets", response_model=SecretResponse, status_code=201)
def create_secret(
    integration_id: str,
    payload: SecretCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SecretResponse:
    svc = IntegrationService(db)
    secret = svc.create_secret(integration_id, str(tenant_id), payload.model_dump())
    if not secret:
        raise HTTPException(status_code=404, detail="Integration not found")
    return SecretResponse.model_validate(secret)


@router.get("/{integration_id}/secrets", response_model=list[SecretResponse])
def list_secrets(
    integration_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[SecretResponse]:
    svc = IntegrationService(db)
    secrets = svc.list_secrets(integration_id, str(tenant_id))
    return [SecretResponse.model_validate(s) for s in secrets]


# ---------------------------------------------------------------------------
# Webhook Delivery endpoints
# ---------------------------------------------------------------------------

@router.post("/{integration_id}/webhooks", response_model=WebhookDeliveryResponse, status_code=201)
def queue_webhook(
    integration_id: str,
    endpoint_id: str,
    payload: WebhookDeliveryCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> WebhookDeliveryResponse:
    """Queue a webhook for delivery with retry logic."""
    svc = IntegrationService(db)
    delivery = svc.queue_webhook(
        integration_id=integration_id,
        endpoint_id=endpoint_id,
        tenant_id=str(tenant_id),
        url=payload.url,
        payload=payload.payload,
        headers=payload.headers,
        method=payload.method,
        max_attempts=payload.max_attempts,
        scheduled_at=payload.scheduled_at,
    )
    return WebhookDeliveryResponse.model_validate(delivery)


@router.post("/{integration_id}/webhooks/process", response_model=WebhookProcessResult)
def process_webhooks(
    integration_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> WebhookProcessResult:
    """Process pending webhook deliveries."""
    svc = IntegrationService(db)
    result = svc.process_pending_webhooks(str(tenant_id), limit=limit)
    return WebhookProcessResult(**result)


@router.get("/{integration_id}/webhooks", response_model=list[WebhookDeliveryResponse])
def list_webhook_deliveries(
    integration_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[WebhookDeliveryResponse]:
    """List webhook deliveries."""
    svc = IntegrationService(db)
    deliveries, _ = svc.list_webhook_deliveries(str(tenant_id), status=status, integration_id=integration_id, limit=limit, offset=offset)
    return [WebhookDeliveryResponse.model_validate(d) for d in deliveries]


@router.get("/{integration_id}/webhooks/{delivery_id}", response_model=WebhookDeliveryResponse)
def get_webhook_delivery(
    integration_id: str,
    delivery_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> WebhookDeliveryResponse:
    """Get a webhook delivery by ID."""
    svc = IntegrationService(db)
    delivery = svc.get_webhook_delivery(delivery_id, str(tenant_id))
    if not delivery:
        raise HTTPException(status_code=404, detail="Webhook delivery not found")
    return WebhookDeliveryResponse.model_validate(delivery)


@router.get("/{integration_id}/webhooks/{delivery_id}/attempts", response_model=list[WebhookDeliveryAttemptResponse])
def get_webhook_attempts(
    integration_id: str,
    delivery_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[WebhookDeliveryAttemptResponse]:
    """Get delivery attempts for a webhook."""
    svc = IntegrationService(db)
    attempts = svc.get_webhook_attempts(delivery_id, str(tenant_id))
    return [WebhookDeliveryAttemptResponse.model_validate(a) for a in attempts]


@router.post("/{integration_id}/webhooks/{delivery_id}/retry", response_model=WebhookDeliveryResponse)
def retry_webhook(
    integration_id: str,
    delivery_id: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> WebhookDeliveryResponse:
    """Manually retry a failed webhook delivery."""
    svc = IntegrationService(db)
    delivery = svc.retry_webhook(delivery_id, str(tenant_id))
    if not delivery:
        raise HTTPException(status_code=404, detail="Webhook delivery not found or not retryable")
    return WebhookDeliveryResponse.model_validate(delivery)
