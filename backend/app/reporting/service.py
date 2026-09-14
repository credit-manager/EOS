import json
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..events.models import SystemEvent
from ..events.service import publish as publish_event
from ..graph.service import can_read
from ..metadata.models import MetadataEntity
from ..policy import evaluate_conditions
from ..records.models import Record
from ..rules.models import Rule, RuleExecution
from ..workflow.models import ApprovalTask, WorkflowDefinition, WorkflowInstance
from .models import AnalyticsReport, ReportRun

NUMERIC_TYPES = {"integer", "decimal"}
_MAX_ORDERED = 5
_MAX_REFS = 100


def _published(db: Session, tenant_id: UUID, entity_code: str) -> MetadataEntity | None:
    return db.scalar(
        select(MetadataEntity)
        .where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        )
        .order_by(MetadataEntity.version.desc())
    )


def _all_records(db: Session, tenant_id: UUID, entity_code: str) -> list[Record]:
    return list(
        db.scalars(
            select(Record).where(Record.tenant_id == tenant_id, Record.entity_code == entity_code)
        ).all()
    )


def _coerce_decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _metrics_for(decimals: list[Decimal], metric: str) -> Decimal | None:
    if not decimals:
        return None
    if metric == "sum":
        return sum(decimals, Decimal("0"))
    if metric == "avg":
        return sum(decimals, Decimal("0")) / len(decimals)
    if metric == "min":
        return min(decimals)
    return max(decimals)


def execute_report(
    db: Session,
    *,
    tenant_id: UUID,
    role: str,
    report: AnalyticsReport,
) -> dict:
    metadata = _published(db, tenant_id, report.entity_code)
    if metadata is None or not can_read(metadata, role):
        raise HTTPException(status_code=404, detail="entity not found")
    fields = {field["code"]: field for field in metadata.definition.get("fields", [])}

    if report.metric != "count":
        field = fields.get(report.field or "")
        if field is None or field["type"] not in NUMERIC_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"report field {report.field!r} must be a numeric field of {report.entity_code}",
            )
    if report.group_by and report.group_by not in fields:
        raise HTTPException(status_code=400, detail=f"group_by field {report.group_by!r} not found in metadata")

    conditions = json.loads(report.conditions_json) if report.conditions_json else []
    matched: list[Record] = []
    for row in _all_records(db, tenant_id, report.entity_code):
        ctx = {
            "record": row.data or {},
            "record_id": str(row.id),
            "entity_code": row.entity_code,
            "tenant_id": str(tenant_id),
        }
        if evaluate_conditions(ctx, conditions):
            matched.append(row)

    metric = report.metric
    field_code = report.field
    if metric == "count":
        value = Decimal(len(matched))
    else:
        decimals = [
            dec
            for row in matched
            if (dec := _coerce_decimal((row.data or {}).get(field_code or ""))) is not None
        ]
        value = _metrics_for(decimals, metric)

    series: list[dict] = []
    if report.group_by:
        grouped: dict[str, list[Record]] = {}
        for row in matched:
            key = str((row.data or {}).get(report.group_by) or "unknown")
            grouped.setdefault(key, []).append(row)
        for key in sorted(grouped):
            if metric == "count":
                series.append({"key": key, "value": Decimal(len(grouped[key]))})
                continue
            decimals = [
                dec
                for row in grouped[key]
                if (dec := _coerce_decimal((row.data or {}).get(field_code or ""))) is not None
            ]
            series.append({"key": key, "value": _metrics_for(decimals, metric)})

    refs = [f"{report.entity_code}:{row.id}" for row in matched[:_MAX_REFS]]
    return {
        "report_code": report.code,
        "report_name": report.name,
        "entity_code": report.entity_code,
        "metric": metric,
        "field": report.field,
        "value": _jsonable(value),
        "count": len(matched),
        "series": [{"key": item["key"], "value": _jsonable(item["value"])} for item in series],
        "refs": refs,
    }


def _jsonable(value) -> str | None:
    if value is None:
        return None
    return str(value)


def run_and_record(
    db: Session,
    *,
    tenant_id: UUID,
    role: str,
    user_id: UUID,
    report: AnalyticsReport,
    request_id: str | None = None,
) -> dict:
    result = execute_report(db, tenant_id=tenant_id, role=role, report=report)
    run_row = ReportRun(
        tenant_id=tenant_id,
        report_id=report.id,
        result_json=result,
        created_by=user_id,
    )
    db.add(run_row)
    db.flush()
    publish_event(
        db,
        tenant_id=tenant_id,
        event_type="report.run.completed",
        entity_type=report.entity_code,
        entity_id=str(run_row.id),
        actor_id=str(user_id),
        payload={
            "report_code": report.code,
            "entity_code": report.entity_code,
            "metric": report.metric,
            "value": result["value"] if result["value"] is not None else None,
            "count": result["count"],
        },
        request_id=request_id,
    )
    db.commit()
    db.refresh(run_row)
    return {
        "run_id": run_row.id,
        "report_code": report.code,
        "result": result,
        "created_at": run_row.created_at,
    }


def _transition_for(task: ApprovalTask, definition: WorkflowDefinition) -> dict | None:
    for transition in definition.definition.get("transitions", []):
        if transition.get("action") == task.action and transition.get("from_state") == task.from_state:
            return transition
    return None


def home_feed(
    db: Session,
    *,
    tenant_id: UUID,
    role: str,
    user_id: UUID,
) -> dict:
    entities = db.scalars(
        select(MetadataEntity)
        .where(MetadataEntity.tenant_id == tenant_id, MetadataEntity.published_at.is_not(None))
        .order_by(MetadataEntity.code, MetadataEntity.version.desc())
    ).all()
    latest: dict[str, MetadataEntity] = {}
    for entity in entities:
        latest.setdefault(entity.code, entity)

    entity_counts: list[dict] = []
    for code in sorted(latest):
        if not can_read(latest[code], role):
            continue
        count = db.scalar(
            select(func.count())
            .select_from(Record)
            .where(Record.tenant_id == tenant_id, Record.entity_code == code)
        )
        if count:
            entity_counts.append({"entity_code": code, "count": count})

    tasks = db.scalars(
        select(ApprovalTask)
        .where(ApprovalTask.tenant_id == tenant_id, ApprovalTask.status == "pending")
        .order_by(ApprovalTask.requested_at)
    ).all()
    instance_cache: dict[UUID, WorkflowInstance | None] = {}
    approvals: list[dict] = []
    needing_action: dict[UUID, dict] = {}
    for task in tasks:
        instance = instance_cache.get(task.workflow_instance_id)
        if instance is None and task.workflow_instance_id not in instance_cache:
            instance = db.get(WorkflowInstance, task.workflow_instance_id)
            instance_cache[task.workflow_instance_id] = instance
        if instance is None or instance.status != "active":
            continue
        definition = db.get(WorkflowDefinition, instance.workflow_definition_id)
        if definition is None:
            continue
        transition = _transition_for(task, definition)
        roles = transition.get("roles", []) if transition else []
        if role not in roles:
            continue
        if task.requested_by != user_id:
            approvals.append(
                {
                    "task_id": str(task.id),
                    "instance_id": str(instance.id),
                    "workflow_code": definition.code,
                    "action": task.action,
                    "from_state": task.from_state,
                    "to_state": task.to_state,
                    "requested_at": task.requested_at,
                    "roles": roles,
                }
            )
        needing_action.setdefault(
            instance.id,
            {
                "instance_id": str(instance.id),
                "workflow_code": definition.code,
                "current_state": instance.current_state,
                "status": instance.status,
            },
        )

    recent_events = db.scalars(
        select(SystemEvent)
        .where(SystemEvent.tenant_id == tenant_id)
        .order_by(SystemEvent.occurred_at.desc())
        .limit(8)
    ).all()
    recent_events_data = [
        {
            "event_type": event.event_type,
            "entity_type": event.entity_type,
            "entity_id": str(event.entity_id) if event.entity_id else None,
            "occurred_at": event.occurred_at,
        }
        for event in recent_events
    ]

    rule_execs = db.execute(
        select(RuleExecution, Rule.name)
        .join(Rule, RuleExecution.rule_id == Rule.id)
        .where(RuleExecution.tenant_id == tenant_id, RuleExecution.matched.is_(True))
        .order_by(RuleExecution.executed_at.desc())
        .limit(_MAX_ORDERED)
    ).all()
    recent_rule_firings = [
        {
            "rule_id": str(execution.rule_id),
            "rule_name": name,
            "executed_at": execution.executed_at,
            "triggered_event_id": str(execution.triggered_event_id)
            if execution.triggered_event_id
            else None,
        }
        for execution, name in rule_execs
    ]

    report_count = db.scalar(
        select(func.count()).select_from(AnalyticsReport).where(AnalyticsReport.tenant_id == tenant_id)
    )

    return {
        "entity_counts": entity_counts,
        "approvals_pending": approvals,
        "workflows_needing_action": list(needing_action.values()),
        "recent_events": recent_events_data,
        "recent_rule_firings": recent_rule_firings,
        "report_count": report_count or 0,
    }