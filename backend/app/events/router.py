from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import get_db
from ..tenant import require_admin, require_tenant
from . import service

router = APIRouter(prefix="/api/v1/events", tags=["events"])

LimitParam = Annotated[int, Query(ge=1, le=200)]
OffsetParam = Annotated[int, Query(ge=0)]


class EventPublishRequest(BaseModel):
    event_type: str = Field(
        min_length=1,
        max_length=120,
        pattern=r"^[a-z0-9]+(\.[a-z0-9_]+)+$",
        description="Dotted event type, e.g. 'workflow.task.approved'",
    )
    entity_type: str | None = Field(default=None, max_length=120)
    entity_id: str | None = Field(default=None, max_length=64)
    payload: dict | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    event_type: str
    entity_type: str | None = None
    entity_id: str | None = None
    actor_id: str | None = None
    payload: dict | None = None
    request_id: str | None = None
    occurred_at: datetime


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Event Bus V2 - Route schemas
# ---------------------------------------------------------------------------

class EventRouteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    source_pattern: str = Field(min_length=1, max_length=200)
    target_handler: str = Field(min_length=1, max_length=200)
    filters: list[dict[str, Any]] | None = None
    transformers: list[dict[str, Any]] | None = None
    enabled: bool = True


class EventRouteResponse(BaseModel):
    name: str
    source_pattern: str
    target_handler: str
    filters: list[dict[str, Any]]
    transformers: list[dict[str, Any]]
    enabled: bool


class EventSubscriptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    event_pattern: str = Field(min_length=1, max_length=200)
    enabled: bool = True


class EventSubscriptionResponse(BaseModel):
    name: str
    event_pattern: str
    enabled: bool
    filters_count: int


class EventChainStep(BaseModel):
    event_type: str = Field(min_length=1, max_length=120)
    entity_type: str | None = None
    entity_id: str | None = None
    transformers: list[dict[str, Any]] | None = None


class EventChainRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    chain: list[EventChainStep] = Field(min_length=1, max_length=10)


@router.get("", response_model=EventListResponse)
def list_events(
    event_type: str | None = Query(None, max_length=120),
    entity_type: str | None = Query(None, max_length=120),
    entity_id: str | None = Query(None, max_length=64),
    limit: LimitParam = 20,
    offset: OffsetParam = 0,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> EventListResponse:
    items, total = service.list_events(
        db,
        tenant_id=tenant_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )
    return EventListResponse(
        items=[EventResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=EventResponse, status_code=201)
def publish_event(
    payload: EventPublishRequest,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> EventResponse:
    event = service.publish(
        db,
        tenant_id=tenant_id,
        event_type=payload.event_type,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        actor_id=str(principal.user_id),
        payload=payload.payload,
    )
    db.commit()
    return EventResponse.model_validate(event)


# ---------------------------------------------------------------------------
# Event Bus V2 - Routes endpoints
# ---------------------------------------------------------------------------

@router.get("/routes", response_model=list[EventRouteResponse])
def list_routes(
    principal: Principal = Depends(require_principal),
) -> list[EventRouteResponse]:
    """List all event routes"""
    routes = service.get_routes()
    return [
        EventRouteResponse(
            name=r["name"],
            source_pattern=r["source_pattern"],
            target_handler=r["target_handler"],
            filters=r["filters"],
            transformers=r["transformers"],
            enabled=r["enabled"],
        )
        for r in routes
    ]


@router.post("/routes", response_model=EventRouteResponse, status_code=201)
def create_route(
    payload: EventRouteCreate,
    principal: Principal = Depends(require_admin),
) -> EventRouteResponse:
    """Create a new event route"""
    route = service.add_route(
        name=payload.name,
        source_pattern=payload.source_pattern,
        target_handler=payload.target_handler,
        filters=payload.filters,
        transformers=payload.transformers,
        enabled=payload.enabled,
    )
    return EventRouteResponse(
        name=route["name"],
        source_pattern=route["source_pattern"],
        target_handler=route["target_handler"],
        filters=route["filters"],
        transformers=route["transformers"],
        enabled=route["enabled"],
    )


@router.delete("/routes/{route_name}", status_code=204, response_model=None)
def delete_route(
    route_name: str,
    principal: Principal = Depends(require_admin),
) -> None:
    """Delete an event route"""
    if not service.remove_route(route_name):
        raise HTTPException(status_code=404, detail="route not found")


# ---------------------------------------------------------------------------
# Event Bus V2 - Subscriptions endpoints
# ---------------------------------------------------------------------------

@router.get("/subscriptions", response_model=list[EventSubscriptionResponse])
def list_subscriptions(
    principal: Principal = Depends(require_principal),
) -> list[EventSubscriptionResponse]:
    """List all event subscriptions"""
    subs = service.get_subscriptions()
    return [
        EventSubscriptionResponse(
            name=s["name"],
            event_pattern=s["event_pattern"],
            enabled=s["enabled"],
            filters_count=s["filters_count"],
        )
        for s in subs
    ]


# ---------------------------------------------------------------------------
# Event Bus V2 - Chain endpoint
# ---------------------------------------------------------------------------

@router.post("/chain", response_model=list[EventResponse], status_code=201)
def chain_events(
    payload: EventChainRequest,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[EventResponse]:
    """Execute a chain of events"""
    chain_dicts = [
        {
            "event_type": step.event_type,
            "entity_type": step.entity_type,
            "entity_id": step.entity_id,
            "transformers": step.transformers,
        }
        for step in payload.chain
    ]

    events = service.chain_events(
        db,
        tenant_id=tenant_id,
        event_type=payload.event_type,
        payload=payload.payload,
        chain=chain_dicts,
        context={"request_id": str(principal.user_id)},
    )

    db.commit()
    return [EventResponse.model_validate(event) for event in events]


# ---------------------------------------------------------------------------
# Event Bus V2 - Statistics endpoint
# ---------------------------------------------------------------------------

class EventStatsResponse(BaseModel):
    total_events: int
    event_types: dict[str, int]
    entity_types: dict[str, int]
    recent_events: list[EventResponse]


@router.get("/stats", response_model=EventStatsResponse)
def get_event_stats(
    limit: LimitParam = 20,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> EventStatsResponse:
    """Get event statistics for the tenant"""
    from sqlalchemy import func, select
    from .models import SystemEvent

    total = db.scalar(
        select(func.count()).select_from(
            select(SystemEvent).where(SystemEvent.tenant_id == tenant_id).subquery()
        )
    ) or 0

    event_type_rows = db.scalars(
        select(SystemEvent.event_type, func.count())
        .where(SystemEvent.tenant_id == tenant_id)
        .group_by(SystemEvent.event_type)
        .order_by(func.count().desc())
    ).all()
    event_types = {row[0]: row[1] for row in event_type_rows}

    entity_type_rows = db.scalars(
        select(SystemEvent.entity_type, func.count())
        .where(SystemEvent.tenant_id == tenant_id, SystemEvent.entity_type.is_not(None))
        .group_by(SystemEvent.entity_type)
        .order_by(func.count().desc())
    ).all()
    entity_types = {row[0]: row[1] for row in entity_type_rows}

    recent = list(db.scalars(
        select(SystemEvent)
        .where(SystemEvent.tenant_id == tenant_id)
        .order_by(SystemEvent.occurred_at.desc())
        .limit(limit)
    ).all())

    return EventStatsResponse(
        total_events=total,
        event_types=event_types,
        entity_types=entity_types,
        recent_events=[EventResponse.model_validate(e) for e in recent],
    )


# ---------------------------------------------------------------------------
# Persistent Subscriptions endpoints
# ---------------------------------------------------------------------------

class PersistentSubscriptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    event_pattern: str = Field(min_length=1, max_length=200)
    webhook_url: str | None = None
    webhook_secret: str | None = None
    enabled: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=10, le=3600)


class PersistentSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    name: str
    event_pattern: str
    webhook_url: str | None
    enabled: bool
    max_retries: int
    retry_delay_seconds: int
    last_delivered_at: datetime | None
    last_delivery_status: str | None
    delivery_count: int
    created_at: datetime


class DeadLetterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    event_id: UUID
    subscription_id: UUID
    reason: str
    attempt_count: int
    last_error: str | None
    status: str
    created_at: datetime


@router.get("/persistent-subscriptions", response_model=list[PersistentSubscriptionResponse])
def list_persistent_subs(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list:
    return service.list_persistent_subscriptions(db, tenant_id)


@router.post("/persistent-subscriptions", response_model=PersistentSubscriptionResponse, status_code=201)
def create_persistent_sub(
    payload: PersistentSubscriptionCreate,
    principal: Principal = Depends(require_admin),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    sub = service.create_persistent_subscription(db, tenant_id=tenant_id, data=payload.model_dump())
    db.commit()
    return sub


@router.delete("/persistent-subscriptions/{sub_id}", status_code=204, response_model=None)
def delete_persistent_sub(
    sub_id: UUID,
    principal: Principal = Depends(require_admin),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    service.delete_persistent_subscription(db, tenant_id, sub_id)
    db.commit()


@router.get("/persistent-subscriptions/{sub_id}/deliveries", response_model=list)
def list_deliveries(
    sub_id: UUID,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_delivery_attempts(db, sub_id)


# ---------------------------------------------------------------------------
# Dead-Letter Queue endpoints
# ---------------------------------------------------------------------------

@router.get("/dead-letters", response_model=list[DeadLetterResponse])
def list_dlq(
    status: str | None = Query(None),
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_dead_letters(db, tenant_id, status=status)


@router.post("/dead-letters/{dl_id}/retry")
def retry_dl(
    dl_id: UUID,
    principal: Principal = Depends(require_admin),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    ok = service.retry_dead_letter(db, tenant_id, dl_id)
    if not ok:
        raise HTTPException(status_code=404, detail="dead letter not found")
    db.commit()
    return {"status": "retried"}


@router.post("/dead-letters/{dl_id}/resolve")
def resolve_dl(
    dl_id: UUID,
    principal: Principal = Depends(require_admin),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    ok = service.resolve_dead_letter(db, tenant_id, dl_id, resolved_by=str(principal.user_id))
    if not ok:
        raise HTTPException(status_code=404, detail="dead letter not found")
    db.commit()
    return {"status": "resolved"}


@router.get("/dead-letters/stats")
def dlq_stats(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_dead_letter_stats(db, tenant_id)
