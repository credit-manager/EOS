"""
AI Governance Router - API endpoints for managing policies, limits, escalations, and audit.

Endpoints:
- POST /ai/governance/policies        - Create a policy
- GET  /ai/governance/policies        - List policies
- GET  /ai/governance/policies/{id}   - Get policy
- PUT  /ai/governance/policies/{id}   - Update policy
- DEL  /ai/governance/policies/{id}   - Delete policy
- POST /ai/governance/policies/builtin-apply  - Apply built-in policy templates
- POST /ai/governance/limits          - Create an execution limit
- GET  /ai/governance/limits          - List limits
- GET  /ai/governance/limits/{id}     - Get limit
- PUT  /ai/governance/limits/{id}     - Update limit
- DEL  /ai/governance/limits/{id}     - Delete limit
- GET  /ai/governance/escalations     - List pending escalations
- POST /ai/governance/escalations/{id}/approve   - Approve escalation
- POST /ai/governance/escalations/{id}/reject    - Reject escalation
- GET  /ai/governance/audit           - List audit trail
- GET  /ai/governance/audit/{id}      - Get audit entry
"""

from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import get_db
from ...tenant import require_admin, require_tenant
from .models import (
    AIPolicy,
    AIAgentLimit,
    AIEscalation,
    AIExecutionAudit,
)
from .policies import (
    BUILTIN_POLICIES,
    evaluate_policies,
    policy_matches_action,
)


router = APIRouter(prefix="/api/v1/ai/governance", tags=["ai-governance"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class PolicyCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    agent_types: list[str] = Field(default=["*"], min_length=1)
    action_patterns: list[str] = Field(default=["*"], min_length=1)
    effect: str = Field(default="permit", pattern=r"^(permit|deny|escalate)$")
    conditions: dict | None = None
    priority: int = Field(default=100, ge=0, le=1000)


class PolicyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    agent_types: list[str] | None = None
    action_patterns: list[str] | None = None
    effect: str | None = None
    conditions: dict | None = None
    priority: int | None = None
    is_active: bool | None = None


class PolicyResponse(BaseModel):
    id: str
    tenant_id: str
    code: str
    name: str
    description: str | None
    agent_types: list[str]
    action_patterns: list[str]
    effect: str
    conditions: dict | None
    priority: int
    is_active: bool
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


class LimitCreate(BaseModel):
    agent_code: str = Field(..., min_length=1, max_length=100)
    limit_type: str = Field(
        ...,
        pattern=r"^(hourly_actions|daily_actions|token_budget|time_budget|financial_limit)$",
    )
    max_value: int = Field(..., ge=1, le=10_000_000)
    window_seconds: int | None = Field(default=None, ge=60, le=86400)


class LimitUpdate(BaseModel):
    max_value: int | None = None
    window_seconds: int | None = None
    is_active: bool | None = None


class LimitResponse(BaseModel):
    id: str
    tenant_id: str
    agent_code: str
    limit_type: str
    max_value: int
    window_seconds: int | None
    is_active: bool
    created_at: str | None

    class Config:
        from_attributes = True


class EscalationResponse(BaseModel):
    id: str
    tenant_id: str
    agent_code: str
    action_type: str
    action_data: str | None
    reason: str
    status: str
    requested_by: str | None
    requested_at: str | None
    resolved_by: str | None
    resolved_at: str | None
    approved_by: str | None
    approved_at: str | None
    rejection_reason: str | None

    class Config:
        from_attributes = True


class AuditResponse(BaseModel):
    id: str
    tenant_id: str
    actor_type: str
    actor_id: str
    action: str
    resource_type: str | None
    resource_id: str | None
    effect: str
    policy_applied: str | None
    result: str | None
    metadata: str | None
    execution_id: str | None
    trace_id: str | None
    created_at: str | None

    class Config:
        from_attributes = True


# ============================================================================
# Policy Endpoints
# ============================================================================

@router.post("/policies", response_model=PolicyResponse, status_code=201)
def create_policy(
    payload: PolicyCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Create a new AI governance policy."""
    existing = db.scalar(
        select(AIPolicy).where(
            AIPolicy.tenant_id == tenant_id,
            AIPolicy.code == payload.code,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Policy with this code already exists")

    policy = AIPolicy(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        agent_types=str(payload.agent_types),
        action_patterns=str(payload.action_patterns),
        effect=payload.effect,
        conditions=str(payload.conditions) if payload.conditions else None,
        priority=payload.priority,
        is_active=True,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return _policy_to_response(policy)


@router.get("/policies", response_model=list[PolicyResponse])
def list_policies(
    active_only: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """List AI governance policies for the tenant."""
    query = select(AIPolicy).where(AIPolicy.tenant_id == tenant_id)
    if active_only:
        query = query.where(AIPolicy.is_active.is_(True))
    query = query.order_by(AIPolicy.priority, AIPolicy.code).offset(offset).limit(limit)
    rows = db.scalars(query).all()
    return [_policy_to_response(r) for r in rows]


@router.get("/policies/builtin-apply", response_model=list[PolicyResponse])
def apply_builtin_policies(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Apply built-in policy templates for the tenant (idempotent)."""
    applied = []
    for template in BUILTIN_POLICIES:
        existing = db.scalar(
            select(AIPolicy).where(
                AIPolicy.tenant_id == tenant_id,
                AIPolicy.code == template["code"],
            )
        )
        if existing:
            applied.append(_policy_to_response(existing))
            continue
        policy = AIPolicy(
            tenant_id=tenant_id,
            code=template["code"],
            name=template["name"],
            description=template["description"],
            agent_types=str(template["agent_types"]),
            action_patterns=str(template["action_patterns"]),
            effect=template["effect"],
            conditions=str(template.get("conditions")) if template.get("conditions") else None,
            priority=template["priority"],
            is_active=True,
        )
        db.add(policy)
        applied.append(_policy_to_response(policy))
    db.commit()
    return applied


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Get a specific policy by ID."""
    policy = db.scalar(
        select(AIPolicy).where(
            AIPolicy.id == policy_id,
            AIPolicy.tenant_id == tenant_id,
        )
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_to_response(policy)


@router.put("/policies/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: int,
    payload: PolicyUpdate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Update a policy."""
    policy = db.scalar(
        select(AIPolicy).where(
            AIPolicy.id == policy_id,
            AIPolicy.tenant_id == tenant_id,
        )
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "agent_types" and value is not None:
            setattr(policy, key, str(value))
        elif key == "action_patterns" and value is not None:
            setattr(policy, key, str(value))
        elif key == "conditions" and value is not None:
            setattr(policy, key, str(value))
        else:
            setattr(policy, key, value)
    db.commit()
    db.refresh(policy)
    return _policy_to_response(policy)


@router.delete("/policies/{policy_id}", status_code=204, response_model=None)
def delete_policy(
    policy_id: int,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Soft-delete a policy (sets is_active=False)."""
    policy = db.scalar(
        select(AIPolicy).where(
            AIPolicy.id == policy_id,
            AIPolicy.tenant_id == tenant_id,
        )
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy.is_active = False
    db.commit()


# ============================================================================
# Limit Endpoints
# ============================================================================

@router.post("/limits", response_model=LimitResponse, status_code=201)
def create_limit(
    payload: LimitCreate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Create an execution limit for an agent."""
    existing = db.scalar(
        select(AIAgentLimit).where(
            AIAgentLimit.tenant_id == tenant_id,
            AIAgentLimit.agent_code == payload.agent_code,
            AIAgentLimit.limit_type == payload.limit_type,
            AIAgentLimit.is_active.is_(True),
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Active limit already exists for agent '{payload.agent_code}' and type '{payload.limit_type}'",
        )

    limit = AIAgentLimit(
        tenant_id=tenant_id,
        agent_code=payload.agent_code,
        limit_type=payload.limit_type,
        max_value=payload.max_value,
        window_seconds=payload.window_seconds,
        is_active=True,
    )
    db.add(limit)
    db.commit()
    db.refresh(limit)
    return _limit_to_response(limit)


@router.get("/limits", response_model=list[LimitResponse])
def list_limits(
    agent_code: str | None = Query(default=None),
    limit_type: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """List execution limits for the tenant."""
    query = select(AIAgentLimit).where(AIAgentLimit.tenant_id == tenant_id)
    if agent_code:
        query = query.where(AIAgentLimit.agent_code == agent_code)
    if limit_type:
        query = query.where(AIAgentLimit.limit_type == limit_type)
    if active_only:
        query = query.where(AIAgentLimit.is_active.is_(True))
    query = query.order_by(AIAgentLimit.agent_code, AIAgentLimit.limit_type).offset(offset).limit(limit)
    rows = db.scalars(query).all()
    return [_limit_to_response(r) for r in rows]


@router.get("/limits/{limit_id}", response_model=LimitResponse)
def get_limit(
    limit_id: int,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Get a specific limit by ID."""
    limit = db.scalar(
        select(AIAgentLimit).where(
            AIAgentLimit.id == limit_id,
            AIAgentLimit.tenant_id == tenant_id,
        )
    )
    if not limit:
        raise HTTPException(status_code=404, detail="Limit not found")
    return _limit_to_response(limit)


@router.put("/limits/{limit_id}", response_model=LimitResponse)
def update_limit(
    limit_id: int,
    payload: LimitUpdate,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Update a limit."""
    limit = db.scalar(
        select(AIAgentLimit).where(
            AIAgentLimit.id == limit_id,
            AIAgentLimit.tenant_id == tenant_id,
        )
    )
    if not limit:
        raise HTTPException(status_code=404, detail="Limit not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(limit, key, value)
    db.commit()
    db.refresh(limit)
    return _limit_to_response(limit)


@router.delete("/limits/{limit_id}", status_code=204, response_model=None)
def delete_limit(
    limit_id: int,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Soft-delete a limit (sets is_active=False)."""
    limit = db.scalar(
        select(AIAgentLimit).where(
            AIAgentLimit.id == limit_id,
            AIAgentLimit.tenant_id == tenant_id,
        )
    )
    if not limit:
        raise HTTPException(status_code=404, detail="Limit not found")
    limit.is_active = False
    db.commit()


# ============================================================================
# Escalation Endpoints
# ============================================================================

@router.get("/escalations", response_model=list[EscalationResponse])
def list_escalations(
    status_filter: str | None = Query(default="pending", pattern=r"^(pending|approved|rejected|expired)$"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """List escalations for the tenant."""
    query = select(AIEscalation).where(AIEscalation.tenant_id == tenant_id)
    if status_filter:
        query = query.where(AIEscalation.status == status_filter)
    query = query.order_by(AIEscalation.requested_at.desc()).offset(offset).limit(limit)
    rows = db.scalars(query).all()
    return [_escalation_to_response(r) for r in rows]


@router.post("/escalations/{escalation_id}/approve", response_model=EscalationResponse)
def approve_escalation(
    escalation_id: int,
    resolved_by: str = Query(default=None, description="User ID who approved"),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Approve a pending escalation."""
    esc = db.scalar(
        select(AIEscalation).where(
            AIEscalation.id == escalation_id,
            AIEscalation.tenant_id == tenant_id,
        )
    )
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if esc.status != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot approve escalation in status '{esc.status}'")

    esc.status = "approved"
    esc.resolved_by = resolved_by
    esc.resolved_at = datetime.now(UTC)
    esc.approved_by = resolved_by
    esc.approved_at = datetime.now(UTC)
    db.commit()
    db.refresh(esc)
    return _escalation_to_response(esc)


@router.post("/escalations/{escalation_id}/reject", response_model=EscalationResponse)
def reject_escalation(
    escalation_id: int,
    rejection_reason: str = Query(default="Rejected by human review"),
    resolved_by: str = Query(default=None, description="User ID who rejected"),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Reject a pending escalation."""
    esc = db.scalar(
        select(AIEscalation).where(
            AIEscalation.id == escalation_id,
            AIEscalation.tenant_id == tenant_id,
        )
    )
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if esc.status != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot reject escalation in status '{esc.status}'")

    esc.status = "rejected"
    esc.resolved_by = resolved_by
    esc.resolved_at = datetime.now(UTC)
    esc.rejection_reason = rejection_reason
    db.commit()
    db.refresh(esc)
    return _escalation_to_response(esc)


# ============================================================================
# Audit Endpoints
# ============================================================================

@router.get("/audit", response_model=list[AuditResponse])
def list_audit(
    actor_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    effect: str | None = Query(default=None),
    policy_applied: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """List AI execution audit entries for the tenant."""
    query = select(AIExecutionAudit).where(AIExecutionAudit.tenant_id == tenant_id)
    if actor_type:
        query = query.where(AIExecutionAudit.actor_type == actor_type)
    if action:
        query = query.where(AIExecutionAudit.action == action)
    if effect:
        query = query.where(AIExecutionAudit.effect == effect)
    if policy_applied:
        query = query.where(AIExecutionAudit.policy_applied == policy_applied)
    query = query.order_by(AIExecutionAudit.created_at.desc()).offset(offset).limit(limit)
    rows = db.scalars(query).all()
    return [_audit_to_response(r) for r in rows]


@router.get("/audit/{audit_id}", response_model=AuditResponse)
def get_audit_entry(
    audit_id: int,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Get a specific audit entry by ID."""
    entry = db.scalar(
        select(AIExecutionAudit).where(
            AIExecutionAudit.id == audit_id,
            AIExecutionAudit.tenant_id == tenant_id,
        )
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return _audit_to_response(entry)


# ============================================================================
# Helper functions
# ============================================================================

def _parse_json_list(val: str | None) -> list[str]:
    import json as _json
    if not val:
        return []
    try:
        result = _json.loads(val)
        return result if isinstance(result, list) else [str(result)]
    except (_json.JSONDecodeError, TypeError):
        return [val]


def _parse_json_dict(val: str | None) -> dict | None:
    import json as _json
    if not val:
        return None
    try:
        return _json.loads(val)
    except (_json.JSONDecodeError, TypeError):
        return None


def _policy_to_response(policy: AIPolicy) -> PolicyResponse:
    return PolicyResponse(
        id=str(policy.id),
        tenant_id=str(policy.tenant_id),
        code=policy.code,
        name=policy.name,
        description=policy.description,
        agent_types=_parse_json_list(policy.agent_types),
        action_patterns=_parse_json_list(policy.action_patterns),
        effect=policy.effect,
        conditions=_parse_json_dict(policy.conditions) if policy.conditions else None,
        priority=policy.priority,
        is_active=policy.is_active,
        created_at=policy.created_at.isoformat() if policy.created_at else None,
        updated_at=policy.updated_at.isoformat() if policy.updated_at else None,
    )


def _limit_to_response(limit: AIAgentLimit) -> LimitResponse:
    return LimitResponse(
        id=str(limit.id),
        tenant_id=limit.tenant_id,
        agent_code=limit.agent_code,
        limit_type=limit.limit_type,
        max_value=limit.max_value,
        window_seconds=limit.window_seconds,
        is_active=limit.is_active,
        created_at=limit.created_at.isoformat() if limit.created_at else None,
    )


def _escalation_to_response(esc: AIEscalation) -> EscalationResponse:
    return EscalationResponse(
        id=str(esc.id),
        tenant_id=esc.tenant_id,
        agent_code=esc.agent_code,
        action_type=esc.action_type,
        action_data=esc.action_data,
        reason=esc.reason,
        status=esc.status,
        requested_by=esc.requested_by,
        requested_at=esc.requested_at.isoformat() if esc.requested_at else None,
        resolved_by=esc.resolved_by,
        resolved_at=esc.resolved_at.isoformat() if esc.resolved_at else None,
        approved_by=esc.approved_by,
        approved_at=esc.approved_at.isoformat() if esc.approved_at else None,
        rejection_reason=esc.rejection_reason,
    )


def _audit_to_response(audit: AIExecutionAudit) -> AuditResponse:
    return AuditResponse(
        id=str(audit.id),
        tenant_id=audit.tenant_id,
        actor_type=audit.actor_type,
        actor_id=audit.actor_id,
        action=audit.action,
        resource_type=audit.resource_type,
        resource_id=audit.resource_id,
        effect=audit.effect,
        policy_applied=audit.policy_applied,
        result=audit.result,
        metadata=audit.metadata,
        execution_id=audit.execution_id,
        trace_id=audit.trace_id,
        created_at=audit.created_at.isoformat() if audit.created_at else None,
    )
