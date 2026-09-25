from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..db import get_db
from ..tenant import require_admin, require_tenant
from .models import Policy, PolicyExecution
from .schemas import (
    PolicyDefinition,
    PolicyExecutionResponse,
    PolicyResponse,
    PolicySummary,
)

router = APIRouter(prefix="/api/v1/policy", tags=["policy"])


def _parse_json_field(json_str: str | None, default: Any) -> Any:
    """Parse a JSON field safely"""
    if not json_str:
        return default
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def _response(row: Policy) -> PolicyResponse:
    """Convert policy model to response"""
    return PolicyResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        code=row.code,
        name=row.name,
        description=row.description,
        enabled=row.enabled,
        priority=row.priority,
        when=row.when_clause,
        if_=row.if_clause,
        then=row.then_actions,
        else_=row.else_actions,
        category=row.category,
        tags=_parse_json_field(row.tags_json, []),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("", response_model=PolicyResponse, status_code=201)
def create_policy(
    payload: PolicyDefinition,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PolicyResponse:
    """Create a new policy"""
    # Check if code already exists
    existing = db.scalar(
        select(Policy).where(
            Policy.tenant_id == tenant_id,
            Policy.code == payload.code,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="policy code already exists")

    row = Policy(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        enabled=payload.enabled,
        priority=payload.priority,
        when_clause=payload.when.model_dump(mode="json"),
        if_clause=payload.if_.model_dump(mode="json"),
        then_actions=payload.then.model_dump(mode="json"),
        else_actions=payload.else_.model_dump(mode="json") if payload.else_ else None,
        category=payload.category,
        tags_json=payload.model_dump_json(mode="json", include={"tags"}) if payload.tags else None,
    )
    db.add(row)

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="policy.created",
        resource_type="policy",
        resource_id=row.id,
        metadata={"code": payload.code, "name": payload.name},
        request_id=request.state.request_id,
    )

    db.commit()
    db.refresh(row)
    return _response(row)


@router.get("", response_model=list[PolicySummary])
def list_policies(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[PolicySummary]:
    """List all policies"""
    rows = db.scalars(
        select(Policy)
        .where(Policy.tenant_id == tenant_id)
        .order_by(Policy.priority.desc(), Policy.code)
    ).all()

    return [
        PolicySummary(
            id=row.id,
            code=row.code,
            name=row.name,
            enabled=row.enabled,
            priority=row.priority,
            trigger=row.when_clause.get("trigger", "manual"),
            category=row.category,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> PolicyResponse:
    """Get a policy by ID"""
    row = db.scalar(
        select(Policy).where(
            Policy.tenant_id == tenant_id,
            Policy.id == policy_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="policy not found")
    return _response(row)


@router.patch("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: UUID,
    payload: PolicyDefinition,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PolicyResponse:
    """Update a policy"""
    row = db.scalar(
        select(Policy).where(
            Policy.tenant_id == tenant_id,
            Policy.id == policy_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="policy not found")

    # Check code uniqueness if changed
    if payload.code != row.code:
        existing = db.scalar(
            select(Policy).where(
                Policy.tenant_id == tenant_id,
                Policy.code == payload.code,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="policy code already exists")

    row.code = payload.code
    row.name = payload.name
    row.description = payload.description
    row.enabled = payload.enabled
    row.priority = payload.priority
    row.when_clause = payload.when.model_dump(mode="json")
    row.if_clause = payload.if_.model_dump(mode="json")
    row.then_actions = payload.then.model_dump(mode="json")
    row.else_actions = payload.else_.model_dump(mode="json") if payload.else_ else None
    row.category = payload.category
    row.tags_json = payload.model_dump_json(mode="json", include={"tags"}) if payload.tags else None

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="policy.updated",
        resource_type="policy",
        resource_id=row.id,
        metadata={"code": payload.code},
        request_id=request.state.request_id,
    )

    db.commit()
    db.refresh(row)
    return _response(row)


@router.delete("/{policy_id}", status_code=204, response_model=None)
def delete_policy(
    policy_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Delete a policy"""
    row = db.scalar(
        select(Policy).where(
            Policy.tenant_id == tenant_id,
            Policy.id == policy_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="policy not found")

    db.delete(row)

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="policy.deleted",
        resource_type="policy",
        resource_id=policy_id,
        metadata={"code": row.code},
        request_id=request.state.request_id,
    )

    db.commit()


@router.post("/{policy_id}/toggle", response_model=PolicyResponse)
def toggle_policy(
    policy_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PolicyResponse:
    """Toggle policy enabled/disabled"""
    row = db.scalar(
        select(Policy).where(
            Policy.tenant_id == tenant_id,
            Policy.id == policy_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="policy not found")

    row.enabled = not row.enabled

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="policy.toggled",
        resource_type="policy",
        resource_id=row.id,
        metadata={"code": row.code, "enabled": row.enabled},
        request_id=request.state.request_id,
    )

    db.commit()
    db.refresh(row)
    return _response(row)


@router.get("/{policy_id}/executions", response_model=list[PolicyExecutionResponse])
def list_policy_executions(
    policy_id: UUID,
    request: Request,
    limit: int = 50,
    offset: int = 0,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[PolicyExecutionResponse]:
    """List policy execution history"""
    # Verify policy exists
    policy = db.scalar(
        select(Policy).where(
            Policy.tenant_id == tenant_id,
            Policy.id == policy_id,
        )
    )
    if policy is None:
        raise HTTPException(status_code=404, detail="policy not found")

    rows = db.scalars(
        select(PolicyExecution)
        .where(
            PolicyExecution.tenant_id == tenant_id,
            PolicyExecution.policy_id == policy_id,
        )
        .order_by(PolicyExecution.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return [
        PolicyExecutionResponse(
            id=row.id,
            policy_id=row.policy_id,
            policy_code=row.policy_code,
            trigger_event=row.trigger_event,
            trigger_resource_type=row.trigger_resource_type,
            trigger_resource_id=row.trigger_resource_id,
            matched=row.matched,
            actions_executed=row.actions_executed,
            execution_time_ms=row.execution_time_ms,
            error_message=row.error_message,
            created_at=row.created_at,
        )
        for row in rows
    ]
