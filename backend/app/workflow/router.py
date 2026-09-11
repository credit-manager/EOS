from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import get_db
from .models import ApprovalTask, WorkflowDefinition, WorkflowInstance
from .schemas import (
    ApprovalDecisionRequest,
    ApprovalTaskResponse,
    WorkflowDefinitionCreate,
    WorkflowDefinitionResponse,
    WorkflowInstanceCreate,
    WorkflowInstanceResponse,
    WorkflowTransitionRequest,
)
from .service import (
    commit_workflow,
    create_definition,
    decide_approval,
    request_transition,
    start_instance,
)

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
        workflow_code=definition.code,
        workflow_version=definition.version,
        reference_type=row.reference_type,
        reference_id=row.reference_id,
        current_state=row.current_state,
        status=row.status,
    )


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
    instance, task = request_transition(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        role=principal.role,
        instance_id=instance_id,
        action=payload.action,
        request_id=request.state.request_id,
    )
    commit_workflow(db)
    if task is not None:
        return {"status": "pending_approval", "approval_task_id": str(task.id)}
    return {"status": "applied", "current_state": instance.current_state}


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
