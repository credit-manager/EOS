from uuid import UUID

from sqlalchemy.orm import Session

from .models import AuditEvent


def record(
    db: Session,
    *,
    tenant_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    metadata: dict | None = None,
    request_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        tenant_id=tenant_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        details=metadata or {},
    )
    db.add(event)
    db.flush()
    return event
