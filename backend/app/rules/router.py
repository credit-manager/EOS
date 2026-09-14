from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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