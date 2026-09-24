import json
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Rule, RuleExecution
from .schemas import (
    AuditAction,
    NotifyAction,
    PublishEventAction,
    RuleAction,
    RuleCreate,
    RuleUpdate,
)


def _dump_action(action: RuleAction) -> dict:
    if isinstance(action, NotifyAction):
        return action.model_dump()
    if isinstance(action, PublishEventAction):
        return action.model_dump()
    if isinstance(action, AuditAction):
        return action.model_dump()
    return action.model_dump()


def _rule_to_dict(rule: Rule) -> dict:
    conditions = json.loads(rule.conditions_json) if rule.conditions_json else []
    actions = json.loads(rule.actions_json) if rule.actions_json else []
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "event_type": rule.event_type,
        "conditions": conditions,
        "actions": actions,
        "priority": rule.priority,
        "enabled": rule.enabled,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }


def get_rule(db: Session, *, tenant_id: UUID, rule_id: UUID) -> Rule:
    rule = db.get(Rule, rule_id)
    if rule is None or rule.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="rule not found")
    return rule


def create_rule(
    db: Session,
    *,
    tenant_id: UUID,
    created_by: UUID,
    payload: RuleCreate,
) -> Rule:
    rule = Rule(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        event_type=payload.event_type,
        conditions_json=json.dumps([c.model_dump() for c in payload.conditions]) if payload.conditions else None,
        actions_json=json.dumps([_dump_action(a) for a in payload.actions]),
        priority=payload.priority,
        enabled=payload.enabled,
        created_by=created_by,
    )
    db.add(rule)
    db.flush()
    return rule


def update_rule(db: Session, *, tenant_id: UUID, rule_id: UUID, payload: RuleUpdate) -> Rule:
    rule = get_rule(db, tenant_id=tenant_id, rule_id=rule_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        rule.name = data["name"]
    if "description" in data:
        rule.description = data["description"]
    if "event_type" in data:
        rule.event_type = data["event_type"]
    if "priority" in data:
        rule.priority = data["priority"]
    if "enabled" in data:
        rule.enabled = data["enabled"]
    if "conditions" in data:
        rule.conditions_json = (
            json.dumps([c.model_dump() for c in data["conditions"]]) if data["conditions"] else None
        )
    if "actions" in data:
        rule.actions_json = json.dumps([_dump_action(a) for a in data["actions"]])
    db.flush()
    return rule


def list_rules(db: Session, *, tenant_id: UUID, limit: int, offset: int) -> tuple[list[Rule], int]:
    query = select(Rule).where(Rule.tenant_id == tenant_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(query.order_by(Rule.priority, Rule.created_at).offset(offset).limit(limit)).all()
    )
    return items, total


def delete_rule(db: Session, *, tenant_id: UUID, rule_id: UUID) -> None:
    rule = get_rule(db, tenant_id=tenant_id, rule_id=rule_id)
    db.delete(rule)
    db.flush()


def list_executions(
    db: Session, *, tenant_id: UUID, rule_id: UUID | None, limit: int, offset: int
) -> tuple[list[dict], int]:
    query = (
        select(RuleExecution, Rule.name)
        .join(Rule, Rule.id == RuleExecution.rule_id)
        .where(RuleExecution.tenant_id == tenant_id)
    )
    if rule_id is not None:
        query = query.where(RuleExecution.rule_id == rule_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(RuleExecution.executed_at.desc()).offset(offset).limit(limit)
    ).all()
    items = [
        {
            "id": execution.id,
            "rule_id": execution.rule_id,
            "rule_name": rule_name,
            "triggered_event_id": execution.triggered_event_id,
            "matched": execution.matched,
            "detail": execution.detail,
            "executed_at": execution.executed_at,
        }
        for execution, rule_name in rows
    ]
    return items, total


# ---------------------------------------------------------------------------
# Async / Delayed Actions
# ---------------------------------------------------------------------------

from datetime import UTC, datetime, timedelta

from .models import DelayedAction


def schedule_delayed_actions(
    db: Session, *, tenant_id: UUID, rule_id: UUID, actions: list[dict],
    context: dict | None, delay_seconds: int
) -> DelayedAction:
    da = DelayedAction(
        tenant_id=tenant_id,
        rule_id=rule_id,
        actions_json=json.dumps(actions),
        context_json=json.dumps(context) if context else None,
        delay_seconds=delay_seconds,
        scheduled_for=datetime.now(UTC) + timedelta(seconds=delay_seconds),
        status="pending",
    )
    db.add(da)
    db.flush()
    return da


def list_pending_delayed_actions(db: Session) -> list:
    now = datetime.now(UTC)
    return list(
        db.scalars(
            select(DelayedAction).where(
                DelayedAction.status == "pending",
                DelayedAction.scheduled_for <= now,
            ).order_by(DelayedAction.scheduled_for)
        ).all()
    )


def execute_delayed_action(db: Session, delayed_action_id: UUID) -> bool:
    da = db.get(DelayedAction, delayed_action_id)
    if da is None or da.status != "pending":
        return False

    da.status = "executing"
    db.flush()

    try:
        from .engine import execute_actions

        actions = json.loads(da.actions_json)
        context = json.loads(da.context_json) if da.context_json else {}
        execute_actions(db, tenant_id=da.tenant_id, rule_id=da.rule_id, actions=actions, context=context)

        da.status = "completed"
        da.executed_at = datetime.now(UTC)
        db.flush()
        return True
    except Exception as e:
        da.status = "failed"
        da.error_message = str(e)[:2000]
        da.executed_at = datetime.now(UTC)
        db.flush()
        return False


def list_delayed_actions(
    db: Session, *, tenant_id: UUID, status: str | None = None, limit: int = 50
) -> list:
    q = select(DelayedAction).where(DelayedAction.tenant_id == tenant_id)
    if status:
        q = q.where(DelayedAction.status == status)
    return list(db.scalars(q.order_by(DelayedAction.scheduled_for.desc()).limit(limit)).all())


def cancel_delayed_action(db: Session, tenant_id: UUID, delayed_action_id: UUID) -> bool:
    da = db.scalar(
        select(DelayedAction).where(
            DelayedAction.id == delayed_action_id,
            DelayedAction.tenant_id == tenant_id,
        )
    )
    if da is None or da.status != "pending":
        return False
    da.status = "failed"
    da.error_message = "Cancelled by user"
    db.flush()
    return True
