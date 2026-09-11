from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.models import AuditEvent
from ..db import get_db
from ..tenant import require_admin

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/events")
def list_audit_events(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, min_length=1, max_length=80),
    resource_type: str | None = Query(default=None, min_length=1, max_length=100),
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    query = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
    if action is not None:
        query = query.where(AuditEvent.action == action)
    if resource_type is not None:
        query = query.where(AuditEvent.resource_type == resource_type)
    rows = db.scalars(query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)).all()
    return [
        {
            "id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": str(row.resource_id) if row.resource_id else None,
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "request_id": row.request_id,
            "details": row.details,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
