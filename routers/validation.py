"""
P20 Validation Rules Router — CRUD + validate endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.rate_limit import read_limiter, write_limiter
from core.validation_engine import ValidationEngine
from database import get_db

router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Validation Engine"],
)


@router.get(
    "/validation-rules",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def list_rules(
    entity_id: str | None=None,
    field_code: str | None = None,
    db: Session = Depends(get_db),
):
    """List validation rules for an entity."""
    engine = ValidationEngine(db)
    rules = engine.get_rules(entity_id, field_code=field_code)
    return {"status": "success", "data": rules}


@router.post(
    "/validation-rules",
    dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)],
)
async def create_rule(
    body: dict,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """Create a validation rule."""
    engine = ValidationEngine(db)

    entity_id = body.get("entity_id")
    rule_type = body.get("rule_type")
    field_code = body.get("field_code")

    if not entity_id or not rule_type:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING", "message": "entity_id and rule_type required"},
        })

    if rule_type not in ValidationEngine.BUILTIN_VALIDATORS and rule_type != "conditional":
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "INVALID_TYPE",
                      "message": f"rule_type must be one of: {ValidationEngine.BUILTIN_VALIDATORS}"},
        })

    rule_id = engine.create_rule(
        entity_id=entity_id, field_code=field_code, rule_type=rule_type,
        rule_config=body.get("rule_config", {}),
        name_en=body.get("name_en"), name_ar=body.get("name_ar"),
        severity=body.get("severity", "error"),
        tenant_id=user.get("tenant_id"),
        condition=body.get("condition"),
    )

    if not rule_id:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "CREATE_FAILED", "message": "Could not create rule"},
        })

    db.commit()
    return {"status": "success", "data": {"id": rule_id}}


@router.delete(
    "/validation-rules/{rule_id}",
    dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)],
)
async def delete_rule(
    rule_id: str,
    db: Session=None,
):
    """Delete (soft) a validation rule."""
    engine = ValidationEngine(db)
    ok = engine.delete_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Rule not found"},
        })
    db.commit()
    return {"status": "success", "message": "Rule deleted"}


@router.post(
    "/validate/{entity_code}",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def validate_record(
    entity_code: str,
    body: dict,
    db: Session=None,
):
    """Validate a record against entity rules."""
    entity = db.execute(
        __import__("sqlalchemy").text(
            "SELECT id FROM dbp_entities WHERE code = :ec"
        ),
        {"ec": entity_code},
    ).fetchone()

    if not entity:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Entity not found"},
        })

    engine = ValidationEngine(db)
    result = engine.validate_record(
        entity_id=entity[0],
        data=body.get("data", {}),
        existing_data=body.get("existing_data"),
        tenant_id=body.get("tenant_id"),
    )

    return {"status": "success", "data": result}


@router.post(
    "/validate/{entity_code}/batch",
    dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)],
)
async def validate_batch(
    entity_code: str,
    body: dict,
    db: Session=None,
):
    """Validate a batch of records against entity rules."""
    entity = db.execute(
        __import__("sqlalchemy").text(
            "SELECT id FROM dbp_entities WHERE code = :ec"
        ),
        {"ec": entity_code},
    ).fetchone()

    if not entity:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": "Entity not found"},
        })

    records = body.get("records", [])
    if not records:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "error": {"code": "MISSING", "message": "records array required"},
        })

    engine = ValidationEngine(db)
    result = engine.validate_batch(
        entity_id=entity[0],
        records=records,
        tenant_id=body.get("tenant_id"),
    )

    return {"status": "success", "data": result}
