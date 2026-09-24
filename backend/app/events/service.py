import json
import logging
import re
from collections.abc import Callable
from typing import Any, TypeAlias
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import SystemEvent

logger = logging.getLogger("2to-eos.events")

EventHandler: TypeAlias = Callable[[SystemEvent], None]
EventFilter: TypeAlias = Callable[[SystemEvent], bool]
EventTransformer: TypeAlias = Callable[[dict[str, Any]], dict[str, Any]]

_handlers: dict[str, list[EventHandler]] = {}
_routes: list[dict[str, Any]] = []
_subscriptions: list[dict[str, Any]] = []


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


# ---------------------------------------------------------------------------
# Event Bus V2 - Routing
# ---------------------------------------------------------------------------

def add_route(
    name: str,
    source_pattern: str,
    target_handler: str,
    filters: list[dict[str, Any]] | None = None,
    transformers: list[dict[str, Any]] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    """Add an event route for routing events to different handlers"""
    route = {
        "name": name,
        "source_pattern": source_pattern,
        "target_handler": target_handler,
        "filters": filters or [],
        "transformers": transformers or [],
        "enabled": enabled,
        "compiled_pattern": re.compile(source_pattern),
    }
    _routes.append(route)
    return route


def remove_route(name: str) -> bool:
    """Remove an event route by name"""
    global _routes
    initial_count = len(_routes)
    _routes = [r for r in _routes if r["name"] != name]
    return len(_routes) < initial_count


def get_routes() -> list[dict[str, Any]]:
    """Get all registered routes"""
    return [
        {k: v for k, v in route.items() if k != "compiled_pattern"}
        for route in _routes
    ]


# ---------------------------------------------------------------------------
# Event Bus V2 - Filtering
# ---------------------------------------------------------------------------

def add_subscription(
    name: str,
    event_pattern: str,
    handler: EventHandler,
    filters: list[EventFilter] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    """Add a subscription with filters"""
    subscription = {
        "name": name,
        "event_pattern": event_pattern,
        "handler": handler,
        "filters": filters or [],
        "enabled": enabled,
        "compiled_pattern": re.compile(event_pattern),
    }
    _subscriptions.append(subscription)
    return subscription


def remove_subscription(name: str) -> bool:
    """Remove a subscription by name"""
    global _subscriptions
    initial_count = len(_subscriptions)
    _subscriptions = [s for s in _subscriptions if s["name"] != name]
    return len(_subscriptions) < initial_count


def get_subscriptions() -> list[dict[str, Any]]:
    """Get all registered subscriptions"""
    return [
        {
            "name": s["name"],
            "event_pattern": s["event_pattern"],
            "enabled": s["enabled"],
            "filters_count": len(s["filters"]),
        }
        for s in _subscriptions
    ]


# ---------------------------------------------------------------------------
# Event Bus V2 - Transformation
# ---------------------------------------------------------------------------

def transform_payload(
    payload: dict[str, Any],
    transformers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply transformers to event payload"""
    result = dict(payload)

    for transformer in transformers:
        t_type = transformer.get("type", "")

        if t_type == "rename_field":
            old_name = transformer.get("old_name")
            new_name = transformer.get("new_name")
            if old_name and new_name and old_name in result:
                result[new_name] = result.pop(old_name)

        elif t_type == "add_field":
            field_name = transformer.get("field_name")
            field_value = transformer.get("field_value")
            if field_name:
                result[field_name] = field_value

        elif t_type == "remove_field":
            field_name = transformer.get("field_name")
            if field_name and field_name in result:
                result.pop(field_name)

        elif t_type == "convert_type":
            field_name = transformer.get("field_name")
            target_type = transformer.get("target_type")
            if field_name and target_type and field_name in result:
                try:
                    if target_type == "int":
                        result[field_name] = int(result[field_name])
                    elif target_type == "float":
                        result[field_name] = float(result[field_name])
                    elif target_type == "str":
                        result[field_name] = str(result[field_name])
                    elif target_type == "bool":
                        result[field_name] = bool(result[field_name])
                except (ValueError, TypeError):
                    pass

        elif t_type == "filter_keys":
            include_keys = transformer.get("include_keys", [])
            exclude_keys = transformer.get("exclude_keys", [])
            if include_keys:
                result = {k: v for k, v in result.items() if k in include_keys}
            elif exclude_keys:
                result = {k: v for k, v in result.items() if k not in exclude_keys}

    return result


# ---------------------------------------------------------------------------
# Event Bus V2 - Chaining
# ---------------------------------------------------------------------------

def chain_events(
    db: Session,
    tenant_id: UUID,
    event_type: str,
    payload: dict[str, Any],
    chain: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> list[SystemEvent]:
    """Execute a chain of events"""
    events = []
    current_payload = dict(payload)
    current_context = dict(context or {})

    for step in chain:
        step_event_type = step.get("event_type", event_type)
        step_transformers = step.get("transformers", [])

        # Apply transformers
        transformed_payload = transform_payload(current_payload, step_transformers)

        # Publish event
        event = publish(
            db,
            tenant_id=tenant_id,
            event_type=step_event_type,
            entity_type=step.get("entity_type"),
            entity_id=step.get("entity_id"),
            payload=transformed_payload,
            request_id=current_context.get("request_id"),
        )
        events.append(event)

        # Update context for next step
        current_context["previous_event_id"] = str(event.id)
        current_payload = transformed_payload

    return events


# ---------------------------------------------------------------------------
# Event Bus V2 - Dispatch with routing
# ---------------------------------------------------------------------------

def _dispatch(event: SystemEvent) -> None:
    """Dispatch event to handlers with routing support"""
    # Direct handlers
    handlers = _handlers.get(event.event_type, []) + _handlers.get("*", [])
    for handler in handlers:
        try:
            handler(event)
        except Exception:
            logger.exception("Event handler failed for %s", event.event_type)

    # Subscription-based handlers
    for subscription in _subscriptions:
        if not subscription["enabled"]:
            continue

        pattern = subscription["compiled_pattern"]
        if not pattern.match(event.event_type):
            continue

        # Apply filters
        filters_match = True
        for event_filter in subscription["filters"]:
            if not event_filter(event):
                filters_match = False
                break

        if filters_match:
            try:
                subscription["handler"](event)
            except Exception:
                logger.exception(
                    "Subscription handler failed for %s",
                    subscription["name"],
                )

    # Route-based handlers
    for route in _routes:
        if not route["enabled"]:
            continue

        pattern = route["compiled_pattern"]
        if not pattern.match(event.event_type):
            continue

        # Apply route filters
        filters_match = True
        for route_filter in route["filters"]:
            if not route_filter(event):
                filters_match = False
                break

        if filters_match:
            # Transform payload
            transformed_payload = transform_payload(
                event.payload or {},
                route["transformers"],
            )

            # Log route execution with transformed payload
            logger.info(
                "Event routed: %s -> %s (transformed payload keys: %s)",
                event.event_type,
                route["target_handler"],
                list(transformed_payload.keys()),
            )


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


# ---------------------------------------------------------------------------
# Persistent Subscriptions (database-backed)
# ---------------------------------------------------------------------------

def create_persistent_subscription(
    db: Session, *, tenant_id: UUID, data: dict
) -> "PersistentSubscription":
    from .models import PersistentSubscription
    sub = PersistentSubscription(tenant_id=tenant_id, **data)
    db.add(sub)
    db.flush()
    return sub


def get_persistent_subscription(db: Session, tenant_id: UUID, sub_id: UUID) -> "PersistentSubscription":
    from .models import PersistentSubscription
    sub = db.scalar(
        select(PersistentSubscription).where(
            PersistentSubscription.id == sub_id,
            PersistentSubscription.tenant_id == tenant_id,
        )
    )
    if sub is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="subscription not found")
    return sub


def list_persistent_subscriptions(db: Session, tenant_id: UUID) -> list:
    from .models import PersistentSubscription
    return list(
        db.scalars(
            select(PersistentSubscription)
            .where(PersistentSubscription.tenant_id == tenant_id)
            .order_by(PersistentSubscription.created_at.desc())
        ).all()
    )


def delete_persistent_subscription(db: Session, tenant_id: UUID, sub_id: UUID) -> bool:
    from .models import PersistentSubscription
    sub = get_persistent_subscription(db, tenant_id, sub_id)
    db.delete(sub)
    db.flush()
    return True


def deliver_event_to_subscription(
    db: Session, subscription_id: UUID, event_id: UUID
) -> "EventDeliveryAttempt":
    """Attempt to deliver an event to a webhook subscription."""
    from datetime import UTC, datetime
    from .models import EventDeliveryAttempt, PersistentSubscription

    sub = db.get(PersistentSubscription, subscription_id)
    if sub is None:
        raise ValueError("subscription not found")

    attempt = EventDeliveryAttempt(
        subscription_id=subscription_id,
        event_id=event_id,
        attempt_number=sub.delivery_count + 1,
        status="pending",
    )
    db.add(attempt)
    db.flush()

    # If webhook_url is set, attempt HTTP delivery
    if sub.webhook_url:
        try:
            import hashlib
            import hmac
            import json

            event = db.get(SystemEvent, event_id)
            if event:
                payload_bytes = json.dumps({
                    "event_type": event.event_type,
                    "entity_type": event.entity_type,
                    "entity_id": event.entity_id,
                    "payload": event.payload,
                    "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
                }).encode()

                # Sign if secret is set
                headers = {"Content-Type": "application/json"}
                if sub.webhook_secret:
                    sig = hmac.new(
                        sub.webhook_secret.encode(), payload_bytes, hashlib.sha256
                    ).hexdigest()
                    headers["X-EOS-Signature"] = sig

                import httpx
                resp = httpx.post(
                    sub.webhook_url,
                    content=payload_bytes,
                    headers=headers,
                    timeout=10,
                )
                attempt.status_code = resp.status_code
                attempt.response_body = resp.text[:1000]
                attempt.status = "success" if 200 <= resp.status_code < 300 else "failed"
        except Exception as e:
            attempt.status = "failed"
            attempt.error_message = str(e)[:1000]
    else:
        # No webhook - mark as success (in-process handler already ran)
        attempt.status = "success"

    sub.delivery_count += 1
    sub.last_delivered_at = datetime.now(UTC)
    sub.last_delivery_status = attempt.status
    db.flush()
    return attempt


def get_delivery_attempts(
    db: Session, subscription_id: UUID, event_id: UUID | None = None
) -> list:
    from .models import EventDeliveryAttempt
    q = select(EventDeliveryAttempt).where(
        EventDeliveryAttempt.subscription_id == subscription_id
    )
    if event_id:
        q = q.where(EventDeliveryAttempt.event_id == event_id)
    return list(db.scalars(q.order_by(EventDeliveryAttempt.attempted_at.desc()).limit(50)).all())


# ---------------------------------------------------------------------------
# Dead-Letter Queue
# ---------------------------------------------------------------------------

def move_to_dead_letter(
    db: Session, *, tenant_id: UUID, event_id: UUID, subscription_id: UUID,
    reason: str, attempt_count: int, last_error: str | None = None
) -> "DeadLetterEvent":
    from .models import DeadLetterEvent
    dl = DeadLetterEvent(
        tenant_id=tenant_id,
        event_id=event_id,
        subscription_id=subscription_id,
        reason=reason,
        attempt_count=attempt_count,
        last_error=last_error,
        status="pending",
    )
    db.add(dl)
    db.flush()
    return dl


def list_dead_letters(
    db: Session, tenant_id: UUID, status: str | None = None
) -> list:
    from .models import DeadLetterEvent
    q = select(DeadLetterEvent).where(DeadLetterEvent.tenant_id == tenant_id)
    if status:
        q = q.where(DeadLetterEvent.status == status)
    return list(db.scalars(q.order_by(DeadLetterEvent.created_at.desc()).limit(100)).all())


def retry_dead_letter(db: Session, tenant_id: UUID, dead_letter_id: UUID) -> bool:
    from .models import DeadLetterEvent
    dl = db.scalar(
        select(DeadLetterEvent).where(
            DeadLetterEvent.id == dead_letter_id,
            DeadLetterEvent.tenant_id == tenant_id,
        )
    )
    if dl is None:
        return False
    dl.status = "retried"
    db.flush()
    # Re-attempt delivery
    try:
        deliver_event_to_subscription(db, dl.subscription_id, dl.event_id)
    except Exception:
        pass
    return True


def resolve_dead_letter(db: Session, tenant_id: UUID, dead_letter_id: UUID, resolved_by: str) -> bool:
    from datetime import UTC, datetime
    from .models import DeadLetterEvent
    dl = db.scalar(
        select(DeadLetterEvent).where(
            DeadLetterEvent.id == dead_letter_id,
            DeadLetterEvent.tenant_id == tenant_id,
        )
    )
    if dl is None:
        return False
    dl.status = "resolved"
    dl.resolved_by = resolved_by
    dl.resolved_at = datetime.now(UTC)
    db.flush()
    return True


def get_dead_letter_stats(db: Session, tenant_id: UUID) -> dict:
    from .models import DeadLetterEvent
    total = db.scalar(
        select(func.count()).select_from(
            select(DeadLetterEvent).where(DeadLetterEvent.tenant_id == tenant_id).subquery()
        )
    ) or 0
    pending = db.scalar(
        select(func.count()).select_from(
            select(DeadLetterEvent).where(
                DeadLetterEvent.tenant_id == tenant_id,
                DeadLetterEvent.status == "pending",
            ).subquery()
        )
    ) or 0
    return {"total": total, "pending": pending, "resolved": total - pending}
