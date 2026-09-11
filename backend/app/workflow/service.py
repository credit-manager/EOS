from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit.models import AuditEvent
from ..metadata.models import MetadataEntity
from ..records.models import Record
from .models import ApprovalTask, WorkflowDefinition, WorkflowInstance
from .schemas import WorkflowDefinitionCreate


def _definition_graph(definition: WorkflowDefinition) -> list[dict]:
    return definition.definition["transitions"]


def _is_terminal(definition: WorkflowDefinition, state: str) -> bool:
    return not any(item["from_state"] == state for item in _definition_graph(definition))


def get_definition(db: Session, tenant_id: UUID, code: str) -> WorkflowDefinition:
    definition = db.scalar(
        select(WorkflowDefinition)
        .where(
            WorkflowDefinition.tenant_id == tenant_id,
            WorkflowDefinition.code == code,
            WorkflowDefinition.is_active.is_(True),
        )
        .order_by(WorkflowDefinition.version.desc())
    )
    if definition is None:
        raise HTTPException(status_code=404, detail="workflow definition not found")
    return definition


def create_definition(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    payload: WorkflowDefinitionCreate,
    request_id: str | None,
) -> WorkflowDefinition:
    current = db.scalar(
        select(func.max(WorkflowDefinition.version)).where(
            WorkflowDefinition.tenant_id == tenant_id,
            WorkflowDefinition.code == payload.code,
        )
    )
    definition = WorkflowDefinition(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        version=(current or 0) + 1,
        initial_state=payload.initial_state,
        definition={
            "states": payload.states,
            "transitions": [item.model_dump(mode="json") for item in payload.transitions],
        },
        is_active=payload.is_active,
        created_by=user_id,
    )
    db.add(definition)
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            action="workflow.definition.created",
            resource_type="workflow_definition",
            resource_id=definition.id,
            request_id=request_id,
            details={"code": definition.code, "version": definition.version},
        )
    )
    return definition


def start_instance(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    workflow_code: str,
    reference_type: str,
    reference_id: UUID,
    request_id: str | None,
) -> WorkflowInstance:
    definition = get_definition(db, tenant_id, workflow_code)
    instance = WorkflowInstance(
        tenant_id=tenant_id,
        workflow_definition_id=definition.id,
        reference_type=reference_type,
        reference_id=reference_id,
        current_state=definition.initial_state,
        status="completed" if _is_terminal(definition, definition.initial_state) else "active",
        created_by=user_id,
    )
    db.add(instance)
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            action="workflow.instance.started",
            resource_type="workflow_instance",
            resource_id=instance.id,
            request_id=request_id,
            details={"workflow_code": workflow_code, "state": instance.current_state},
        )
    )
    return instance


def _apply_transition_actions(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    instance: WorkflowInstance,
    actions: list[dict],
    request_id: str | None,
) -> None:
    for action in actions:
        action_type = action.get("type")
        if action_type != "set_record_field":
            raise HTTPException(status_code=422, detail=f"unsupported workflow action: {action_type}")

        if not instance.reference_type:
            raise HTTPException(status_code=409, detail="workflow action requires a record reference")

        record = db.scalar(
            select(Record)
            .where(
                Record.id == instance.reference_id,
                Record.tenant_id == tenant_id,
                Record.entity_code == instance.reference_type,
                Record.workflow_instance_id == instance.id,
            )
            .with_for_update()
        )
        if record is None:
            raise HTTPException(status_code=409, detail="workflow action record is not bound to this instance")

        metadata = db.scalar(
            select(MetadataEntity)
            .where(
                MetadataEntity.tenant_id == tenant_id,
                MetadataEntity.code == record.entity_code,
                MetadataEntity.published_at.is_not(None),
            )
            .order_by(MetadataEntity.version.desc())
        )
        if metadata is None:
            raise HTTPException(status_code=409, detail="workflow action metadata is not published")

        field_code = action.get("field")
        field_codes = {field["code"] for field in metadata.definition.get("fields", [])}
        if field_code not in field_codes:
            raise HTTPException(status_code=422, detail=f"workflow action field is not defined: {field_code}")

        data = deepcopy(record.data)
        data[field_code] = action.get("value")
        record.data = data
        record.version += 1
        db.add(
            AuditEvent(
                tenant_id=tenant_id,
                actor_id=user_id,
                action="workflow.action.record_field_set",
                resource_type=record.entity_code,
                resource_id=record.id,
                request_id=request_id,
                details={"field": field_code, "workflow_instance_id": str(instance.id)},
            )
        )


def request_transition(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    role: str,
    instance_id: UUID,
    action: str,
    request_id: str | None,
) -> tuple[WorkflowInstance, ApprovalTask | None]:
    instance = db.scalar(
        select(WorkflowInstance)
        .where(WorkflowInstance.id == instance_id, WorkflowInstance.tenant_id == tenant_id)
        .with_for_update()
    )
    if instance is None:
        raise HTTPException(status_code=404, detail="workflow instance not found")
    if instance.status != "active":
        raise HTTPException(status_code=409, detail="workflow instance is not active")

    definition = db.get(WorkflowDefinition, instance.workflow_definition_id)
    if definition is None or not definition.is_active:
        raise HTTPException(status_code=409, detail="workflow definition is not active")

    transition = next(
        (
            item
            for item in _definition_graph(definition)
            if item["from_state"] == instance.current_state and item["action"] == action
        ),
        None,
    )
    if transition is None:
        raise HTTPException(status_code=422, detail="transition is not allowed from the current state")
    if role not in transition["roles"]:
        raise HTTPException(status_code=403, detail="role cannot request this transition")

    if transition["requires_approval"]:
        pending = db.scalar(
            select(ApprovalTask).where(
                ApprovalTask.workflow_instance_id == instance.id,
                ApprovalTask.status == "pending",
            )
        )
        if pending is not None:
            raise HTTPException(status_code=409, detail="workflow instance already has a pending approval")
        task = ApprovalTask(
            tenant_id=tenant_id,
            workflow_instance_id=instance.id,
            action=action,
            from_state=instance.current_state,
            to_state=transition["to_state"],
            requested_by=user_id,
        )
        db.add(task)
        db.flush()
        db.add(
            AuditEvent(
                tenant_id=tenant_id,
                actor_id=user_id,
                action="workflow.approval.requested",
                resource_type="approval_task",
                resource_id=task.id,
                request_id=request_id,
                details={"action": action, "from_state": task.from_state, "to_state": task.to_state},
            )
        )
        return instance, task

    instance.current_state = transition["to_state"]
    _apply_transition_actions(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        instance=instance,
        actions=transition.get("actions", []),
        request_id=request_id,
    )
    if _is_terminal(definition, instance.current_state):
        instance.status = "completed"
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            action="workflow.transition.applied",
            resource_type="workflow_instance",
            resource_id=instance.id,
            request_id=request_id,
            details={"action": action, "state": instance.current_state},
        )
    )
    db.flush()
    return instance, None


def decide_approval(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    role: str,
    task_id: UUID,
    approved: bool,
    request_id: str | None,
) -> tuple[ApprovalTask, WorkflowInstance]:
    task = db.scalar(
        select(ApprovalTask)
        .where(ApprovalTask.id == task_id, ApprovalTask.tenant_id == tenant_id)
        .with_for_update()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="approval task not found")
    if task.status != "pending":
        raise HTTPException(status_code=409, detail="approval task is already decided")
    if task.requested_by == user_id:
        raise HTTPException(status_code=403, detail="requester cannot approve the same transition")

    instance = db.scalar(
        select(WorkflowInstance)
        .where(WorkflowInstance.id == task.workflow_instance_id, WorkflowInstance.tenant_id == tenant_id)
        .with_for_update()
    )
    if instance is None or instance.status != "active":
        raise HTTPException(status_code=409, detail="workflow instance is not active")

    definition = db.get(WorkflowDefinition, instance.workflow_definition_id)
    transition = next(
        (
            item
            for item in _definition_graph(definition)
            if item["from_state"] == task.from_state and item["action"] == task.action
        ),
        None,
    )
    if transition is None or role not in transition["roles"]:
        raise HTTPException(status_code=403, detail="role cannot decide this approval")

    task.status = "approved" if approved else "rejected"
    task.decided_by = user_id
    task.decided_at = datetime.now(UTC)
    if approved:
        instance.current_state = task.to_state
        _apply_transition_actions(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            instance=instance,
            actions=transition.get("actions", []),
            request_id=request_id,
        )
        if _is_terminal(definition, instance.current_state):
            instance.status = "completed"
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_id=user_id,
            action="workflow.approval.approved" if approved else "workflow.approval.rejected",
            resource_type="approval_task",
            resource_id=task.id,
            request_id=request_id,
            details={"action": task.action, "state": instance.current_state},
        )
    )
    db.flush()
    return task, instance


def commit_workflow(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="workflow write conflicted with another transaction") from exc
