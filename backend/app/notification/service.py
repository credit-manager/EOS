import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .models import Notification

logger = logging.getLogger("2to-eos.notification")


def create_notification(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    title: str,
    message: str,
    notification_type: str = "info",
    category: str = "system",
    action_url: str | None = None,
    metadata: dict | None = None,
) -> Notification:
    notification = Notification(
        tenant_id=tenant_id,
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        category=category,
        action_url=action_url,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(notification)
    db.flush()
    logger.info("Notification created for user %s: %s", user_id, title)
    return notification


def create_bulk_notifications(
    db: Session,
    *,
    tenant_id: UUID,
    user_ids: list[UUID],
    title: str,
    message: str,
    notification_type: str = "info",
    category: str = "system",
    action_url: str | None = None,
) -> list[Notification]:
    notifications = []
    for user_id in user_ids:
        n = create_notification(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            action_url=action_url,
        )
        notifications.append(n)
    return notifications


def list_notifications(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
    is_read: bool | None = None,
    category: str | None = None,
    notification_type: str | None = None,
) -> tuple[list[Notification], int, int]:
    query = select(Notification).where(
        Notification.tenant_id == tenant_id,
        Notification.user_id == user_id,
    )
    
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    if category:
        query = query.where(Notification.category == category)
    if notification_type:
        query = query.where(Notification.notification_type == notification_type)
    
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    
    query = query.order_by(Notification.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    items = list(db.scalars(query).all())
    
    unread_count = db.scalar(
        select(func.count()).where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
            not Notification.is_read,
        )
    ) or 0
    
    return items, total, unread_count


def mark_as_read(db: Session, *, tenant_id: UUID, user_id: UUID, notification_ids: list[UUID]) -> int:
    now = datetime.now(UTC)
    result = db.execute(
        update(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
            Notification.id.in_(notification_ids),
            not Notification.is_read,
        )
        .values(is_read=True, read_at=now)
    )
    db.flush()
    return result.rowcount


def mark_all_as_read(db: Session, *, tenant_id: UUID, user_id: UUID) -> int:
    now = datetime.now(UTC)
    result = db.execute(
        update(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
            not Notification.is_read,
        )
        .values(is_read=True, read_at=now)
    )
    db.flush()
    return result.rowcount


def get_notification_stats(db: Session, *, tenant_id: UUID, user_id: UUID) -> dict:
    total = db.scalar(
        select(func.count()).where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
        )
    ) or 0
    
    unread = db.scalar(
        select(func.count()).where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
            not Notification.is_read,
        )
    ) or 0
    
    type_rows = db.execute(
        select(Notification.notification_type, func.count())
        .where(Notification.tenant_id == tenant_id, Notification.user_id == user_id)
        .group_by(Notification.notification_type)
    ).all()
    by_type = {row[0]: row[1] for row in type_rows}
    
    cat_rows = db.execute(
        select(Notification.category, func.count())
        .where(Notification.tenant_id == tenant_id, Notification.user_id == user_id)
        .group_by(Notification.category)
    ).all()
    by_category = {row[0]: row[1] for row in cat_rows}
    
    return {
        "total": total,
        "unread": unread,
        "by_type": by_type,
        "by_category": by_category,
    }


def delete_notification(db: Session, *, tenant_id: UUID, user_id: UUID, notification_id: UUID) -> bool:
    from .models import Notification as N
    
    n = db.get(N, notification_id)
    if n and n.tenant_id == tenant_id and n.user_id == user_id:
        db.delete(n)
        db.flush()
        return True
    return False
