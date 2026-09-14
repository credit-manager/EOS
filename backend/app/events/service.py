import json
import logging
from collections.abc import Callable
from typing import TypeAlias
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import SystemEvent

logger = logging.getLogger("2to-eos.events")

EventHandler: TypeAlias = Callable[[SystemEvent], None]

_handlers: dict[str, list[EventHandler]] = {}


def subscribe(event_type: str, handler: EventHandler) -> None:
    """Register an in-process handler for a dotted event type
    (e.g. 'auth.user.registered'). Use '*' to receive every event."""
    _handlers.setdefault(event_type, [])
    if handler not in _handlers[event_type]:
        _handlers[event_type].append(handler)


def unsubscribe(event_type: str, handler: EventHandler) -> None:
    handlers = _handlers.get(event_type)
    if handlers is not None and handler in handlers:
        handlers.remove(handler)


def clear_subscribers() -> None:
    _handlers.clear()


def _dispatch(event: SystemEvent) -> None:
    handlers = _handlers.get(event.event_type, []) + _handlers.get("*", [])
    for handler in handlers:
        try:
            handler(event)
        except Exception:
            logger.exception("Event handler failed for %s", event.event_type)


def publish(
    db: Session,
    *,
    tenant_id: UUID,
    event_type: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: str | None = None,
    payload: dict | None = None,
    request_id: str | None = None,
) -> SystemEvent:
    event = SystemEvent(
        tenant_id=tenant_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        payload_json=json.dumps(payload) if payload is not None else None,
        request_id=request_id,
    )
    db.add(event)
    db.flush()
    event.session = db
    _dispatch(event)
    logger.info("Event published: %s (tenant %s)", event_type, tenant_id)
    return event


def list_events(
    db: Session,
    *,
    tenant_id: UUID,
    event_type: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[SystemEvent], int]:
    query = select(SystemEvent).where(SystemEvent.tenant_id == tenant_id)

    if event_type:
        query = query.where(SystemEvent.event_type == event_type)
    if entity_type:
        query = query.where(SystemEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(SystemEvent.entity_id == entity_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    query = query.order_by(SystemEvent.occurred_at.desc(), SystemEvent.id)
    items = list(db.scalars(query.offset(offset).limit(limit)).all())

    return items, total