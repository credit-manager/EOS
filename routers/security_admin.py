"""
P13 Security Admin Router
Endpoints for managing field-level security and row-level rules.
"""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission
from core.rate_limit import read_limiter, write_limiter
from models import DBPEntity, DBPField, DBPRowRule

router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Security Admin"],
)


# ──────────────────────────────────────────────────────────────
# FIELD-LEVEL SECURITY
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/security/fields",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def get_field_security(
    entity_code: str,
    db: Session=None,
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    fields = db.query(DBPField).filter(DBPField.entity_id == entity.id).all()
    data = []
    for f in fields:
        data.append({
            "code": f.code,
            "field_type": f.field_type,
            "is_sensitive": f.is_sensitive or False,
            "writable_roles": f.writable_roles or [],
            "visible_roles": f.visible_roles or [],
            "validation_rules": f.validation_rules or {},
        })

    return {"data": data, "count": len(data)}


@router.put(
    "/entities/{entity_code}/security/fields/{field_code}",
    dependencies=[
        Depends(require_permission("dynamic", "update")),
        Depends(write_limiter.check),
    ],
)
async def update_field_security(
    entity_code: str,
    field_code: str,
    body: dict,
    db: Session=None,
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    field = db.query(DBPField).filter(
        DBPField.entity_id == entity.id,
        DBPField.code == field_code,
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    changed = []
    if "is_sensitive" in body:
        field.is_sensitive = bool(body["is_sensitive"])
        changed.append("is_sensitive")
    if "writable_roles" in body:
        field.writable_roles = body["writable_roles"]
        changed.append("writable_roles")
    if "visible_roles" in body:
        field.visible_roles = body["visible_roles"]
        changed.append("visible_roles")
    if "validation_rules" in body:
        field.validation_rules = body["validation_rules"]
        changed.append("validation_rules")

    if not changed:
        return {"status": "success", "message": "No changes"}

    db.commit()
    return {"status": "success", "changed": changed}


# ──────────────────────────────────────────────────────────────
# ROW-LEVEL SECURITY RULES
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/security/rows",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def list_row_rules(
    entity_code: str,
    db: Session=None,
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    rules = db.query(DBPRowRule).filter(
        DBPRowRule.entity_id == entity.id
    ).order_by(DBPRowRule.priority.asc()).all()

    data = []
    for r in rules:
        data.append({
            "id": r.id,
            "filter_column": r.filter_column,
            "filter_type": r.filter_type,
            "filter_value": r.filter_value,
            "allowed_roles": r.allowed_roles or [],
            "priority": r.priority,
            "is_active": r.is_active,
        })

    return {"data": data, "count": len(data)}


@router.post(
    "/entities/{entity_code}/security/rows",
    dependencies=[
        Depends(require_permission("dynamic", "create")),
        Depends(write_limiter.check),
    ],
)
async def create_row_rule(
    entity_code: str,
    body: dict,
    db: Session=None,
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    required = ["filter_column", "filter_type"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"Missing: {field}")

    filter_type = body["filter_type"]
    if filter_type not in ("equals", "in"):
        raise HTTPException(status_code=400, detail="filter_type must be 'equals' or 'in'")

    filter_col = body["filter_column"]
    if not re.match(r'^[a-z][a-z0-9_]{0,99}$', filter_col):
        raise HTTPException(status_code=400, detail="Invalid filter_column format")

    rule_id = str(uuid.uuid4())
    rule = DBPRowRule(
        id=rule_id,
        entity_id=entity.id,
        filter_column=filter_col,
        filter_type=filter_type,
        filter_value=body.get("filter_value"),
        allowed_roles=body.get("allowed_roles", []),
        priority=body.get("priority", 0),
        is_active=body.get("is_active", True),
    )
    db.add(rule)
    db.commit()

    return {"status": "success", "rule_id": rule_id}


@router.delete(
    "/entities/{entity_code}/security/rows/{rule_id}",
    dependencies=[
        Depends(require_permission("dynamic", "delete")),
        Depends(write_limiter.check),
    ],
)
async def delete_row_rule(
    entity_code: str,
    rule_id: str,
    db: Session=None,
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    rule = db.query(DBPRowRule).filter(
        DBPRowRule.id == rule_id,
        DBPRowRule.entity_id == entity.id,
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Row rule not found")

    db.delete(rule)
    db.commit()

    return {"status": "success", "deleted": rule_id}
