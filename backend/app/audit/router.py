from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_admin
from .models import AuditEvent
from .schemas import AuditEventResponse

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/events", response_model=list[AuditEventResponse])
def list_events(
    action: str | None = Query(default=None, min_length=1, max_length=80),
    resource_type: str | None = Query(default=None, min_length=1, max_length=100),
    resource_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tenant_id=Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AuditEventResponse]:
    query = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if action:
        query = query.where(AuditEvent.action == action)
    if resource_type:
        query = query.where(AuditEvent.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditEvent.resource_id == resource_id)
    rows = db.scalars(
        query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit).offset(offset)
    ).all()
    return rows
