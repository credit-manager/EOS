from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..auth.security import Principal, require_principal
from ..db import get_db
from ..tenant import require_tenant
from . import schemas, service

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


def _record_forbidden(db: Session, request: Request, principal: Principal, path: str) -> None:
    audit_record(
        db,
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        action="rules.forbidden",
        resource_type="rule",
        resource_id=None,
        metadata={"path": path, "role": principal.role},
        request_id=request.state.request_id,
    )
    db.commit()


def require_admin(
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> Principal:
    if principal.role != "admin":
        _record_forbidden(db, request, principal, request.url.path)
        raise HTTPException(status_code=403, detail="admin role required")
    return principal


@router.get("", response_model=schemas.RuleListResponse)
def list_rules(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> schemas.RuleListResponse:
    items, total = service.list_rules(db, tenant_id=tenant_id, limit=limit, offset=offset)
    return schemas.RuleListResponse(
        items=[schemas.RuleResponse.model_validate(service._rule_to_dict(item)) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=schemas.RuleResponse, status_code=201)
def create_rule(
    payload: schemas.RuleCreate,
    request: Request,
    principal: Principal = Depends(require_admin),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> schemas.RuleResponse:
    rule = service.create_rule(
        db, tenant_id=tenant_id, created_by=principal.user_id, payload=payload
    )
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=principal.user_id,
        action="rules.rule_created",
        resource_type="rule",
        resource_id=rule.id,
        metadata={"rule": rule.name, "event_type": rule.event_type},
        request_id=request.state.request_id,
    )
    db.commit()
    return schemas.RuleResponse.model_validate(service._rule_to_dict(rule))


@router.get("/executions", response_model=schemas.ExecutionListResponse)
def list_executions(
    rule_id: UUID | None = Query(None),
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> schemas.ExecutionListResponse:
    items, total = service.list_executions(
        db, tenant_id=tenant_id, rule_id=rule_id, limit=limit, offset=offset
    )
    return schemas.ExecutionListResponse(
        items=[schemas.RuleExecutionResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{rule_id}", response_model=schemas.RuleResponse)
def get_rule(
    rule_id: UUID,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> schemas.RuleResponse:
    rule = service.get_rule(db, tenant_id=tenant_id, rule_id=rule_id)
    return schemas.RuleResponse.model_validate(service._rule_to_dict(rule))


@router.patch("/{rule_id}", response_model=schemas.RuleResponse)
def update_rule(
    rule_id: UUID,
    payload: schemas.RuleUpdate,
    request: Request,
    principal: Principal = Depends(require_admin),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> schemas.RuleResponse:
    rule = service.update_rule(db, tenant_id=tenant_id, rule_id=rule_id, payload=payload)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=principal.user_id,
        action="rules.rule_updated",
        resource_type="rule",
        resource_id=rule.id,
        metadata={"rule": rule.name},
        request_id=request.state.request_id,
    )
    db.commit()
    return schemas.RuleResponse.model_validate(service._rule_to_dict(rule))


@router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: UUID,
    request: Request,
    principal: Principal = Depends(require_admin),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> None:
    service.delete_rule(db, tenant_id=tenant_id, rule_id=rule_id)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=principal.user_id,
        action="rules.rule_deleted",
        resource_type="rule",
        resource_id=rule_id,
        metadata={"rule_id": str(rule_id)},
        request_id=request.state.request_id,
    )
    db.commit()


@router.post("/test", response_model=schemas.RuleTestResponse)
def test_rules(
    payload: schemas.RuleTestRequest,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> schemas.RuleTestResponse:
    """Test rules against a simulated event without executing actions."""
    from .models import Rule
    from ..policy import evaluate_conditions, resolve_path

    rules = db.scalars(
        select(Rule).where(
            Rule.tenant_id == tenant_id,
            Rule.event_type == payload.event_type,
            Rule.enabled.is_(True),
        ).order_by(Rule.priority, Rule.created_at)
    ).all()

    results = []
    matched_count = 0

    for rule in rules:
        ctx = {
            "payload": payload.payload,
            "event": {
                "event_type": payload.event_type,
                "entity_type": payload.entity_type or "",
                "entity_id": payload.entity_id or "",
            },
        }
        conditions = json.loads(rule.conditions_json) if rule.conditions_json else []
        matched = evaluate_conditions(ctx, conditions) if conditions else True
        if matched:
            matched_count += 1
        actions = json.loads(rule.actions_json) if rule.actions_json else []
        results.append({
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "matched": matched,
            "conditions_count": len(conditions),
            "actions_count": len(actions),
        })

    return schemas.RuleTestResponse(
        matched_rules=matched_count,
        total_rules=len(rules),
        results=results,
    )


# ---------------------------------------------------------------------------
# Async / Delayed Actions endpoints
# ---------------------------------------------------------------------------

class DelayedActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    rule_id: UUID
    actions_json: str
    context_json: str | None
    delay_seconds: int
    scheduled_for: datetime
    status: str
    error_message: str | None
    created_at: datetime
    executed_at: datetime | None


@router.get("/delayed-actions", response_model=list[DelayedActionResponse])
def list_delayed(
    status: str | None = Query(None),
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_delayed_actions(db, tenant_id=tenant_id, status=status)


@router.post("/delayed-actions/{da_id}/cancel")
def cancel_delayed(
    da_id: UUID,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    ok = service.cancel_delayed_action(db, tenant_id, da_id)
    if not ok:
        raise HTTPException(status_code=404, detail="delayed action not found or not cancellable")
    db.commit()
    return {"status": "cancelled"}
