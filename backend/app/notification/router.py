from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import get_db
from ..tenant import require_tenant
from . import schemas, service

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=schemas.NotificationListResponse)
def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_read: bool | None = Query(None),
    category: str | None = Query(None),
    notification_type: str | None = Query(None),
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> schemas.NotificationListResponse:
    items, total, unread_count = service.list_notifications(
        db,
        tenant_id=tenant_id,
        user_id=principal.user_id,
        limit=limit,
        offset=offset,
        is_read=is_read,
        category=category,
        notification_type=notification_type,
    )
    return schemas.NotificationListResponse(
        items=[schemas.NotificationResponse.model_validate(i) for i in items],
        total=total,
        unread_count=unread_count,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=schemas.NotificationStats)
def get_stats(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> schemas.NotificationStats:
    stats = service.get_notification_stats(
        db, tenant_id=tenant_id, user_id=principal.user_id
    )
    return schemas.NotificationStats(**stats)


@router.post("/read")
def mark_read(
    payload: schemas.MarkReadRequest,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    count = service.mark_as_read(
        db, tenant_id=tenant_id, user_id=principal.user_id, notification_ids=payload.notification_ids
    )
    return {"marked": count}


@router.post("/read-all")
def mark_all_read(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    count = service.mark_all_as_read(
        db, tenant_id=tenant_id, user_id=principal.user_id
    )
    return {"marked": count}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: UUID,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    deleted = service.delete_notification(
        db, tenant_id=tenant_id, user_id=principal.user_id, notification_id=notification_id
    )
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="notification not found")
    return {"deleted": True}
