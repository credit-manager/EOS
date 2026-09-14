import json
import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..events.service import publish as publish_event
from ..events.service import subscribe, unsubscribe
from ..notification.service import create_notification
from .models import Rule, RuleExecution

logger = logging.getLogger("2to-eos.rules")

_MAX_RULE_DEPTH = 4
_TEMPLATE_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")

_depth = 0
_handler_registered = False


def install_listener() -> None:
    """Subscribe the rules engine to every published event (idempotent)."""
    global _handler_registered
    if not _handler_registered:
        subscribe("*", _on_event)
        _handler_registered = True


def uninstall_listener() -> None:
    global _handler_registered
    if _handler_registered:
        unsubscribe("*", _on_event)
        _handler_registered = False


def _on_event(event) -> None:
    global _depth
    if _depth >= _MAX_RULE_DEPTH:
        return
    db: Session | None = getattr(event, "session", None)
    if db is None:
        return
    try:
        rules = db.scalars(
            select(Rule)
            .where(
                Rule.tenant_id == event.tenant_id,
                Rule.event_type == event.event_type,
                Rule.enabled.is_(True),
            )
            .order_by(Rule.priority, Rule.created_at)
        ).all()
    except Exception:
        return
    if not rules:
        return
    _depth += 1
    try:
        for rule in rules:
            matched = False
            detail: str | None = None
            try:
                matches, detail = _evaluate(db, rule, event)
                matched = matches
            except Exception as exc:
                detail = f"evaluation failed: {exc}"
            db.add(
                RuleExecution(
                    tenant_id=event.tenant_id,
                    rule_id=rule.id,
                    triggered_event_id=event.id,
                    matched=matched,
                    detail=detail,
                )
            )
        db.flush()
    finally:
        _depth -= 1


def _build_context(event) -> dict[str, Any]:
    return {
        "payload": event.payload or {},
        "event": {
            "id": str(event.id),
            "event_type": event.event_type,
            "tenant_id": str(event.tenant_id),
            "actor_id": event.actor_id,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "request_id": event.request_id,
        },
    }


def _resolve(ctx: dict[str, Any], path: str) -> tuple[bool, Any]:
    node: Any = ctx
    for segment in path.split("."):
        if isinstance(node, dict) and segment in node:
            node = node[segment]
        else:
            return False, None
    return True, node


def _coerce_num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _num_or_none(a: Any, b: Any) -> tuple[float, float] | None:
    na, nb = _coerce_num(a), _coerce_num(b)
    if na is not None and nb is not None:
        return na, nb
    return None


def _evaluate_condition(ctx: dict[str, Any], cond: dict) -> bool:
    field = cond.get("field", "")
    op = cond.get("op", "eq")
    value = cond.get("value")
    found, actual = _resolve(ctx, field)

    if op == "exists":
        return found is bool(value)

    if not found:
        return False

    pair = _num_or_none(actual, value)
    if pair is not None and op in ("eq", "neq", "gt", "gte", "lt", "lte"):
        a, b = pair
        if op == "eq":
            return a == b
        if op == "neq":
            return a != b
        if op == "gt":
            return a > b
        if op == "gte":
            return a >= b
        if op == "lt":
            return a < b
        return a <= b

    if op == "eq":
        return actual == value
    if op == "neq":
        return actual != value
    if op == "contains":
        return value in actual if isinstance(actual, (str, list, tuple)) else False
    if op == "not_contains":
        return value not in actual if isinstance(actual, (str, list, tuple)) else True
    if op == "in":
        return actual in value if isinstance(value, list) else False
    if op == "starts_with":
        return actual.startswith(value) if isinstance(actual, str) else False
    return False


def _render_template(template: str, ctx: dict[str, Any]) -> str:
    def replace(match: re.Match) -> str:
        _, resolved = _resolve(ctx, match.group(1))
        return "" if resolved is None else str(resolved)

    return _TEMPLATE_RE.sub(replace, template)


def _render_value(value: Any, ctx: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return _render_template(value, ctx)
    if isinstance(value, dict):
        return {k: _render_value(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_render_value(v, ctx) for v in value]
    return value


def _notify_recipients(db: Session, tenant_id: UUID, action: dict) -> list[UUID]:
    user_id = action.get("user_id")
    if user_id:
        return [UUID(str(user_id))]
    role = action.get("role")
    if role:
        from ..auth.models import TenantMembership

        rows = db.scalars(
            select(TenantMembership.user_id).where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.role == role,
            )
        ).all()
        return [UUID(str(uid)) for uid in rows]
    return []


def _execute_action(
    db: Session, rule: Rule, event, ctx: dict[str, Any], action: dict
) -> None:
    action_type = action.get("type")
    if action_type == "notify":
        title = _render_template(str(action.get("title", "Alert")), ctx)
        message = _render_template(str(action.get("message", "")), ctx)
        for user_id in _notify_recipients(db, event.tenant_id, action):
            create_notification(
                db,
                tenant_id=event.tenant_id,
                user_id=user_id,
                title=title,
                message=message,
                notification_type="info",
                category="system",
            )
    elif action_type == "publish_event":
        entity_type = _render_template(str(action["entity_type"]), ctx) if action.get("entity_type") else event.entity_type
        entity_id = _render_template(str(action["entity_id"]), ctx) if action.get("entity_id") else event.entity_id
        payload = _render_value(action.get("payload") or {}, ctx)
        publish_event(
            db,
            tenant_id=event.tenant_id,
            event_type=action["event_type"],
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=event.actor_id,
            payload=payload,
            request_id=getattr(event, "request_id", None),
        )
    elif action_type == "audit":
        audit_record(
            db,
            tenant_id=event.tenant_id,
            actor_id=UUID(event.actor_id) if event.actor_id else None,
            action="rules.rule_fired",
            resource_type="rule",
            resource_id=rule.id,
            metadata={
                "rule": rule.name,
                "event": event.event_type,
                "message": _render_template(str(action.get("message", "")), ctx),
            },
            request_id=getattr(event, "request_id", None),
        )


def _evaluate(db: Session, rule: Rule, event) -> tuple[bool, str | None]:
    ctx = _build_context(event)
    conditions = json.loads(rule.conditions_json) if rule.conditions_json else []
    if not all(_evaluate_condition(ctx, cond) for cond in conditions):
        return False, None
    actions = json.loads(rule.actions_json) if rule.actions_json else []
    for action in actions:
        try:
            _execute_action(db, rule, event, ctx, action)
        except Exception as exc:
            return False, f"action '{action.get('type')}' failed: {exc}"
    return True, None