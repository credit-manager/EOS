"""
P12 Events & Webhooks Router

Webhook CRUD + Event log read endpoints.
"""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission
from core.event_bus import EventBus
from core.rate_limit import read_limiter, write_limiter
from database import get_db
from models import DBPWebhook

router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Events & Webhooks"],
)


def _tenant_id(current_user: dict):
    return current_user.get("tenant_id")


@router.post(
    "/webhooks",
    dependencies=[
        Depends(require_permission("dynamic", "create")),
        Depends(write_limiter.check),
    ],
)
async def create_webhook(
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    required = ["code", "target_url", "entity_code", "event_types"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    code = body["code"]
    if not re.match(r"^[a-z][a-z0-9_]{0,99}$", code):
        raise HTTPException(status_code=400, detail="Webhook code must be lowercase alphanumeric + underscore")

    tenant_id = _tenant_id(current_user)
    existing = db.execute(
        text("SELECT id FROM dbp_webhooks WHERE code = :code AND tenant_id = :tenant_id"),
        {"code": code, "tenant_id": tenant_id},
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"Webhook '{code}' already exists")

    event_types = body["event_types"]
    valid_types = EventBus.VALID_EVENT_TYPES | {"*"}
    for event_type in event_types:
        if event_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid event_type: {event_type}")

    webhook_id = str(uuid.uuid4())
    webhook = DBPWebhook(
        id=webhook_id,
        tenant_id=tenant_id,
        code=code,
        target_url=body["target_url"],
        entity_code=body["entity_code"],
        event_types=event_types,
        secret=body.get("secret"),
        is_active=body.get("is_active", True),
        custom_headers=body.get("custom_headers", {}),
    )
    db.add(webhook)
    db.commit()
    return {"status": "success", "webhook_id": webhook_id, "code": code}


@router.get(
    "/webhooks",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def list_webhooks(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rows = db.execute(
        text(
            "SELECT id, code, target_url, entity_code, event_types, "
            "is_active, created_at FROM dbp_webhooks "
            "WHERE tenant_id = :tenant_id ORDER BY created_at DESC LIMIT 100"
        ),
        {"tenant_id": _tenant_id(current_user)},
    ).fetchall()
    data = [
        {
            "id": row[0],
            "code": row[1],
            "target_url": row[2],
            "entity_code": row[3],
            "event_types": row[4] if isinstance(row[4], list) else [],
            "is_active": row[5],
            "created_at": str(row[6]) if row[6] else None,
        }
        for row in rows
    ]
    return {"data": data, "count": len(data)}


@router.get(
    "/webhooks/{webhook_code}",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def get_webhook(
    webhook_code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = db.execute(
        text(
            "SELECT id, code, target_url, entity_code, event_types, "
            "is_active, custom_headers, created_at FROM dbp_webhooks "
            "WHERE code = :code AND tenant_id = :tenant_id"
        ),
        {"code": webhook_code, "tenant_id": _tenant_id(current_user)},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {
        "data": {
            "id": row[0],
            "code": row[1],
            "target_url": row[2],
            "entity_code": row[3],
            "event_types": row[4] if isinstance(row[4], list) else [],
            "is_active": row[5],
            "custom_headers": row[6] if isinstance(row[6], dict) else {},
            "created_at": str(row[7]) if row[7] else None,
        }
    }


@router.put(
    "/webhooks/{webhook_code}",
    dependencies=[
        Depends(require_permission("dynamic", "update")),
        Depends(write_limiter.check),
    ],
)
async def update_webhook(
    webhook_code: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    webhook = (
        db.query(DBPWebhook)
        .filter(DBPWebhook.code == webhook_code, DBPWebhook.tenant_id == _tenant_id(current_user))
        .first()
    )
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    changed = []
    if "target_url" in body and body["target_url"] != webhook.target_url:
        webhook.target_url = body["target_url"]
        changed.append("target_url")
    if "event_types" in body and body["event_types"] != webhook.event_types:
        valid_types = EventBus.VALID_EVENT_TYPES | {"*"}
        if any(event_type not in valid_types for event_type in body["event_types"]):
            raise HTTPException(status_code=400, detail="Invalid event_type")
        webhook.event_types = body["event_types"]
        changed.append("event_types")
    if "is_active" in body and body["is_active"] != webhook.is_active:
        webhook.is_active = body["is_active"]
        changed.append("is_active")
    if "secret" in body:
        webhook.secret = body["secret"]
        changed.append("secret")
    if "custom_headers" in body and body["custom_headers"] != (webhook.custom_headers or {}):
        webhook.custom_headers = body["custom_headers"]
        changed.append("custom_headers")

    if not changed:
        return {"status": "success", "message": "No changes"}
    db.commit()
    return {"status": "success", "changed": changed}


@router.delete(
    "/webhooks/{webhook_code}",
    dependencies=[
        Depends(require_permission("dynamic", "delete")),
        Depends(write_limiter.check),
    ],
)
async def delete_webhook(
    webhook_code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    webhook = (
        db.query(DBPWebhook)
        .filter(DBPWebhook.code == webhook_code, DBPWebhook.tenant_id == _tenant_id(current_user))
        .first()
    )
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(webhook)
    db.commit()
    return {"status": "success", "deleted": webhook_code}


@router.get(
    "/events",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def list_events(
    entity_code: str | None = None,
    event_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    bus = EventBus(db)
    events = bus.get_events(
        entity_code=entity_code,
        event_type=event_type,
        tenant_id=_tenant_id(current_user),
        limit=limit,
        offset=offset,
    )
    return {"data": events, "count": len(events)}


@router.get(
    "/events/{event_id}",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    bus = EventBus(db)
    event = bus.get_event(event_id, tenant_id=_tenant_id(current_user))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"data": event}


@router.get(
    "/webhooks/{webhook_code}/deliveries",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def list_webhook_deliveries(
    webhook_code: str,
    limit: int | None = Query(None, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    webhook = (
        db.query(DBPWebhook)
        .filter(DBPWebhook.code == webhook_code, DBPWebhook.tenant_id == _tenant_id(current_user))
        .first()
    )
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    effective_limit = limit or 50
    rows = db.execute(
        text(
            "SELECT d.id, d.event_id, d.status, d.attempts, "
            "d.last_response_code, d.last_error, d.created_at "
            "FROM dbp_webhook_deliveries d "
            "WHERE d.webhook_id = :wid "
            "ORDER BY d.created_at DESC LIMIT :limit"
        ),
        {"wid": webhook.id, "limit": effective_limit},
    ).fetchall()
    data = [
        {
            "id": row[0],
            "event_id": row[1],
            "status": row[2],
            "attempts": row[3],
            "last_response_code": row[4],
            "last_error": row[5],
            "created_at": str(row[6]) if row[6] else None,
        }
        for row in rows
    ]
    return {"data": data, "count": len(data)}
