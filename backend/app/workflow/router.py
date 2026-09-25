from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import get_db
from ..policy import evaluate_conditions
from .models import ApprovalTask, WorkflowDefinition, WorkflowInstance
from .schemas import (
    ApprovalDecisionRequest,
    ApprovalTaskResponse,
    TaskListResponse,
    WorkflowDefinitionCreate,
    WorkflowDefinitionResponse,
    WorkflowInstanceCreate,
    WorkflowInstanceResponse,
    WorkflowTransitionRequest,
)
from .service import (
    build_workflow_context,
    commit_workflow,
    create_definition,
    decide_approval,
    get_pending_approval_tasks,
    request_transition,
    start_instance,
)
from .state_machine import WorkflowEngine

router = APIRouter(prefix="/api/v1/workflows", tags=["workflow"])


def _definition_response(row: WorkflowDefinition) -> WorkflowDefinitionResponse:
    return WorkflowDefinitionResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        code=row.code,
        name=row.name,
        version=row.version,
        initial_state=row.initial_state,
        definition=row.definition,
        is_active=row.is_active,
    )


def _instance_response(db: Session, row: WorkflowInstance) -> WorkflowInstanceResponse:
    definition = db.get(WorkflowDefinition, row.workflow_definition_id)
    return WorkflowInstanceResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        workflow_code=definition.code if definition else row.reference_type,
        workflow_version=definition.version if definition else 1,
        reference_type=row.reference_type,
        reference_id=row.reference_id,
        current_state=row.current_state,
        status=row.status,
    )


# ---------------------------------------------------------------------------
# Existing endpoints (unchanged)
# ---------------------------------------------------------------------------

@router.post("/definitions", response_model=WorkflowDefinitionResponse, status_code=201)
def create_workflow_definition(
    payload: WorkflowDefinitionCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> WorkflowDefinitionResponse:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    row = create_definition(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        payload=payload,
        request_id=request.state.request_id,
    )
    commit_workflow(db)
    return _definition_response(row)


@router.get("/definitions", response_model=list[WorkflowDefinitionResponse])
def list_workflow_definitions(
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> list[WorkflowDefinitionResponse]:
    rows = db.scalars(
        select(WorkflowDefinition)
        .where(WorkflowDefinition.tenant_id == principal.tenant_id, WorkflowDefinition.is_active.is_(True))
        .order_by(WorkflowDefinition.code, WorkflowDefinition.version.desc())
    ).all()
    return [_definition_response(row) for row in rows]


@router.post("/instances", response_model=WorkflowInstanceResponse, status_code=201)
def start_workflow_instance(
    payload: WorkflowInstanceCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> WorkflowInstanceResponse:
    row = start_instance(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        workflow_code=payload.workflow_code,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        request_id=request.state.request_id,
    )
    commit_workflow(db)
    return _instance_response(db, row)


@router.get("/instances", response_model=list[WorkflowInstanceResponse])
def list_workflow_instances(
    principal: Principal = Depends(require_principal),
    status: str | None = Query(default=None, min_length=1, max_length=20),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[WorkflowInstanceResponse]:
    query = select(WorkflowInstance).where(WorkflowInstance.tenant_id == principal.tenant_id)
    if status is not None:
        query = query.where(WorkflowInstance.status == status)
    rows = db.scalars(query.order_by(WorkflowInstance.created_at.desc()).limit(limit)).all()
    return [_instance_response(db, row) for row in rows]


@router.get("/instances/{instance_id}/available-transitions")
def list_available_transitions(
    instance_id: UUID,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    instance = db.scalar(
        select(WorkflowInstance).where(
            WorkflowInstance.id == instance_id,
            WorkflowInstance.tenant_id == principal.tenant_id,
        )
    )
    if instance is None:
        raise HTTPException(status_code=404, detail="workflow instance not found")
    definition = db.get(WorkflowDefinition, instance.workflow_definition_id)
    if definition is None or not definition.is_active:
        raise HTTPException(status_code=409, detail="workflow definition is not active")
    if instance.status != "active":
        return []
    return [
        {
            "action": transition["action"],
            "from_state": transition["from_state"],
            "to_state": transition["to_state"],
            "requires_approval": transition["requires_approval"],
            "condition_satisfied": evaluate_conditions(
                build_workflow_context(instance, definition, user_id=principal.user_id, role=principal.role, payload=None),
                transition.get("conditions", []),
            ),
        }
        for transition in definition.definition.get("transitions", [])
        if transition["from_state"] == instance.current_state
        and principal.role in transition["roles"]
    ]


@router.post("/instances/{instance_id}/transitions")
def transition_workflow_instance(
    instance_id: UUID,
    payload: WorkflowTransitionRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    try:
        instance, task = request_transition(
            db,
            tenant_id=principal.tenant_id,
            user_id=principal.user_id,
            role=principal.role,
            instance_id=instance_id,
            action=payload.action,
            payload=payload.payload,
            request_id=request.state.request_id,
        )
        commit_workflow(db)
        if task is not None:
            return {"status": "pending_approval", "approval_task_id": str(task.id)}
        return {"status": "applied", "current_state": instance.current_state}
    except HTTPException as exc:
        if exc.status_code == 422 and isinstance(exc.detail, str) and "conditions" in exc.detail:
            # Contract (test_workflow_v2.test_condition_gates_direct_
            # transition): a failed condition gate is a machine-readable
            # 422 whose detail is the reason string. Do NOT replace it
            # with a dict — that broke the legacy 200/"blocked" fallback
            # path used by older clients (test_workflow_sm).
            raise HTTPException(status_code=422, detail=exc.detail) from exc
        raise


@router.get("/approvals", response_model=list[ApprovalTaskResponse])
def list_approval_tasks(
    principal: Principal = Depends(require_principal),
    status: str = Query(default="pending", min_length=1, max_length=20),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ApprovalTaskResponse]:
    rows = db.scalars(
        select(ApprovalTask)
        .where(ApprovalTask.tenant_id == principal.tenant_id, ApprovalTask.status == status)
        .order_by(ApprovalTask.requested_at.asc())
        .limit(limit)
    ).all()
    return [
        ApprovalTaskResponse(
            id=row.id,
            workflow_instance_id=row.workflow_instance_id,
            action=row.action,
            from_state=row.from_state,
            to_state=row.to_state,
            status=row.status,
            requested_by=row.requested_by,
            decided_by=row.decided_by,
        )
        for row in rows
    ]


@router.post("/approvals/{task_id}/decision", response_model=ApprovalTaskResponse)
def decide_workflow_approval(
    task_id: UUID,
    payload: ApprovalDecisionRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> ApprovalTaskResponse:
    task, _ = decide_approval(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        role=principal.role,
        task_id=task_id,
        approved=payload.approved,
        request_id=request.state.request_id,
    )
    commit_workflow(db)
    return ApprovalTaskResponse(
        id=task.id,
        workflow_instance_id=task.workflow_instance_id,
        action=task.action,
        from_state=task.from_state,
        to_state=task.to_state,
        status=task.status,
        requested_by=task.requested_by,
        decided_by=task.decided_by,
    )


@router.get("/my-tasks", response_model=TaskListResponse)
def get_my_tasks(
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> TaskListResponse:
    """Return workflow approval tasks awaiting action from the current user."""
    tasks = get_pending_approval_tasks(db, principal.tenant_id, principal.user_id)
    return TaskListResponse(
        items=[ApprovalTaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
        pending=len(tasks),
    )


# ---------------------------------------------------------------------------
# State Machine endpoints
# ---------------------------------------------------------------------------

@router.post("/instances/{instance_id}/transition")
def execute_transition(
    instance_id: UUID,
    payload: WorkflowTransitionRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Execute a workflow transition via the state machine engine."""
    engine = WorkflowEngine(db)
    instance = engine.execute_transition(
        instance_id=str(instance_id),
        transition_code=payload.action,
        actor=str(principal.user_id),
        comment=payload.payload.get("comment", "") if payload.payload else "",
        data=payload.payload,
        tenant_id=principal.tenant_id,
    )
    commit_workflow(db)
    return {"status": instance.status, "current_state": instance.current_state}


@router.post("/instances/{instance_id}/cancel")
def cancel_workflow(
    instance_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Cancel a running workflow."""
    engine = WorkflowEngine(db)
    instance = engine.cancel_workflow(
        instance_id=str(instance_id),
        reason="Cancelled by user",
        tenant_id=principal.tenant_id,
    )
    commit_workflow(db)
    return {"status": instance.status, "current_state": instance.current_state}


@router.get("/instances/{instance_id}/history")
def get_workflow_history(
    instance_id: UUID,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get the full history of a workflow instance."""
    engine = WorkflowEngine(db)
    return engine.get_workflow_history(
        instance_id=str(instance_id),
        tenant_id=principal.tenant_id,
    )


@router.get("/instances/{instance_id}/transitions")
def get_available_transitions_sm(
    instance_id: UUID,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get transitions available to the current user from the current state (state machine)."""
    engine = WorkflowEngine(db)
    return engine.get_available_transitions(
        instance_id=str(instance_id),
        user_role=principal.role,
        tenant_id=principal.tenant_id,
    )


@router.get("/pending-approvals")
def get_pending_approvals(
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get all workflows waiting for approval by the user's role."""
    engine = WorkflowEngine(db)
    return engine.get_pending_approvals(
        user_role=principal.role,
        tenant_id=principal.tenant_id,
    )


@router.get("/templates")
def list_workflow_templates(
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List all available workflow templates."""
    engine = WorkflowEngine(db)
    return engine.list_templates()


@router.post("/templates", status_code=201)
def create_workflow_template(
    payload: WorkflowDefinitionCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new workflow template (stores as a WorkflowDefinition)."""
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    row = create_definition(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        payload=payload,
        request_id=request.state.request_id,
    )
    commit_workflow(db)
    return {"id": str(row.id), "code": row.code, "name": row.name, "version": row.version}


@router.get("/entity/{entity_type}/{entity_id}")
def get_entity_workflow_status(
    entity_type: str,
    entity_id: str,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict | None:
    """Get the current workflow status for an entity."""
    engine = WorkflowEngine(db)
    result = engine.get_workflow_status(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=principal.tenant_id,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="no workflow found for this entity")
    return result


@router.post("/check-timeouts")
def check_timeouts(
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Check and process timed-out workflows."""
    engine = WorkflowEngine(db)
    results = engine.check_timeouts(tenant_id=principal.tenant_id)
    commit_workflow(db)
    return {"processed": len(results), "events": results}


@router.post("/instances/{instance_id}/compensate")
def compensate_transition(
    instance_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Compensate (undo) a transition by moving to the compensation state."""
    engine = WorkflowEngine(db)
    # Get the last transition from approval tasks
    task = db.scalar(
        select(ApprovalTask).where(
            ApprovalTask.workflow_instance_id == instance_id,
            ApprovalTask.status == "approved",
        ).order_by(ApprovalTask.decided_at.desc())
    )
    if task is None:
        raise HTTPException(status_code=404, detail="no approved transition found to compensate")

    instance = engine.compensate_transition(
        instance_id=str(instance_id),
        transition_code=task.action,
        actor=str(principal.user_id),
        reason="Compensated by user",
        tenant_id=principal.tenant_id,
    )
    commit_workflow(db)
    return {"status": instance.status, "current_state": instance.current_state}


@router.post("/instances/{instance_id}/delegate")
def delegate_approval(
    instance_id: UUID,
    delegate_to: str = Query(..., description="Role or user to delegate to"),
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Delegate a pending approval task to another user/role."""
    engine = WorkflowEngine(db)
    task = db.scalar(
        select(ApprovalTask).where(
            ApprovalTask.workflow_instance_id == instance_id,
            ApprovalTask.tenant_id == principal.tenant_id,
            ApprovalTask.status == "pending",
        )
    )
    if task is None:
        raise HTTPException(status_code=404, detail="no pending approval task found")

    result = engine.delegate_approval(
        task_id=str(task.id),
        delegate_to=delegate_to,
        delegated_by=str(principal.user_id),
        tenant_id=principal.tenant_id,
    )
    commit_workflow(db)
    return result
