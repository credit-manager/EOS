from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import get_db
from ..tenant import require_tenant
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