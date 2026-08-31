"""
P11 Entity Management + Schema Versioning Router

Provides CRUD for entity definitions and field management,
with automatic immutable versioning on every mutation.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from core.auth import require_permission, get_current_user
from core.metadata_engine import MetadataEngine
from core.versioning_engine import VersioningEngine
from core.rate_limit import read_limiter, write_limiter
from core.event_bus import EventBus
from models import DBPEntity, DBPField
import uuid
import re


router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Entity Management"],
)


def _validate_code(code: str):
    if not re.match(r'^[a-z][a-z0-9_]{0,99}$', code):
        raise HTTPException(
            status_code=400,
            detail="Entity code must be lowercase alphanumeric + underscore, start with letter"
        )


def _validate_field_code(code: str):
    if not re.match(r'^[a-z][a-z0-9_]{0,99}$', code):
        raise HTTPException(
            status_code=400,
            detail="Field code must be lowercase alphanumeric + underscore, start with letter"
        )


ALLOWED_FIELD_TYPES = {
    "string", "text", "integer", "float", "number",
    "boolean", "date", "datetime", "enum", "json",
}


# ──────────────────────────────────────────────────────────────
# ENTITY CRUD
# ──────────────────────────────────────────────────────────────

@router.post(
    "/entities",
    dependencies=[
        Depends(require_permission("dynamic", "create")),
        Depends(write_limiter.check),
    ],
)
async def create_entity(
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    required = ["code", "name_en", "faculty", "table_mapping"]
    for field in required:
        if field not in body:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    code = body["code"]
    _validate_code(code)

    existing = db.execute(
        text("SELECT id FROM dbp_entities WHERE code = :code"),
        {"code": code},
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"Entity '{code}' already exists")

    table_mapping = body["table_mapping"]
    if not re.match(r'^[a-z][a-z0-9_]{0,99}$', table_mapping):
        raise HTTPException(status_code=400, detail="table_mapping must be safe")

    table_check = db.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :tname AND table_schema = 'public'"
        ),
        {"tname": table_mapping},
    ).fetchone()
    if not table_check:
        raise HTTPException(
            status_code=400,
            detail=f"Physical table '{table_mapping}' does not exist"
        )

    entity_id = str(uuid.uuid4())
    entity = DBPEntity(
        id=entity_id,
        code=code,
        name_en=body["name_en"],
        name_ar=body.get("name_ar"),
        faculty=body["faculty"],
        table_mapping=table_mapping,
        is_system=body.get("is_system", False),
        metadata_schema=body.get("metadata_schema", {}),
    )
    db.add(entity)
    db.flush()

    fields_data = body.get("fields", [])
    for fd in fields_data:
        fcode = fd.get("code")
        if not fcode:
            raise HTTPException(status_code=400, detail="Field missing 'code'")
        _validate_field_code(fcode)
        ftype = fd.get("field_type", "string")
        if ftype not in ALLOWED_FIELD_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid field_type: {ftype}")

        field = DBPField(
            id=str(uuid.uuid4()),
            entity_id=entity_id,
            code=fcode,
            label_en=fd.get("label_en"),
            label_ar=fd.get("label_ar"),
            field_type=ftype,
            is_required=fd.get("is_required", False),
            ui_config=fd.get("ui_config", {}),
            enum_values=fd.get("enum_values", []),
        )
        db.add(field)

    db.flush()

    ve = VersioningEngine(db)
    ver = ve.create_version(
        entity_id=entity_id,
        change_type="create_entity",
        changed_by=current_user.get("id", current_user.get("user_id", "unknown")),
        change_summary=f"Entity '{code}' created",
    )

    EventBus(db).emit("entity.created", code, tenant_id=current_user.get("tenant_id"), user_id=current_user.get("id", current_user.get("user_id")), payload={"entity_id": entity_id})

    db.commit()

    return {"status": "success", "entity_id": entity_id, "version": ver["version_number"]}


@router.put(
    "/entities/{entity_code}",
    dependencies=[
        Depends(require_permission("dynamic", "update")),
        Depends(write_limiter.check),
    ],
)
async def update_entity(
    entity_code: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if entity.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system entity")

    changed_fields = []
    if "name_en" in body and body["name_en"] != entity.name_en:
        entity.name_en = body["name_en"]
        changed_fields.append("name_en")
    if "name_ar" in body and body["name_ar"] != entity.name_ar:
        entity.name_ar = body["name_ar"]
        changed_fields.append("name_ar")
    if "faculty" in body and body["faculty"] != entity.faculty:
        entity.faculty = body["faculty"]
        changed_fields.append("faculty")
    if "metadata_schema" in body and body["metadata_schema"] != (entity.metadata_schema or {}):
        entity.metadata_schema = body["metadata_schema"]
        changed_fields.append("metadata_schema")

    if not changed_fields:
        return {"status": "success", "message": "No changes"}

    db.flush()

    ve = VersioningEngine(db)
    ver = ve.create_version(
        entity_id=entity.id,
        change_type="update_entity",
        changed_by=current_user.get("id", current_user.get("user_id", "unknown")),
        change_summary=f"Updated: {', '.join(changed_fields)}",
    )

    EventBus(db).emit("entity.updated", entity_code, tenant_id=current_user.get("tenant_id"), user_id=current_user.get("id", current_user.get("user_id")), payload={"changed_fields": changed_fields})

    db.commit()

    return {"status": "success", "version": ver["version_number"], "changed": changed_fields}


@router.delete(
    "/entities/{entity_code}",
    dependencies=[
        Depends(require_permission("dynamic", "delete")),
        Depends(write_limiter.check),
    ],
)
async def delete_entity(
    entity_code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if entity.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system entity")

    rec_count = db.execute(
        text(f"SELECT COUNT(*) FROM {entity.table_mapping}")
    ).scalar()
    if rec_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Entity has {rec_count} records. Delete records first."
        )

    db.delete(entity)

    EventBus(db).emit("entity.deleted", entity_code, tenant_id=current_user.get("tenant_id"), user_id=current_user.get("id", current_user.get("user_id")))

    db.commit()

    return {"status": "success", "deleted": entity_code}


# ──────────────────────────────────────────────────────────────
# FIELD MANAGEMENT
# ──────────────────────────────────────────────────────────────

@router.post(
    "/entities/{entity_code}/fields",
    dependencies=[
        Depends(require_permission("dynamic", "create")),
        Depends(write_limiter.check),
    ],
)
async def add_field(
    entity_code: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if entity.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system entity")

    fcode = body.get("code")
    if not fcode:
        raise HTTPException(status_code=400, detail="Missing 'code'")
    _validate_field_code(fcode)

    existing = db.query(DBPField).filter(
        DBPField.entity_id == entity.id,
        DBPField.code == fcode,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Field '{fcode}' already exists")

    ftype = body.get("field_type", "string")
    if ftype not in ALLOWED_FIELD_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid field_type: {ftype}")

    field = DBPField(
        id=str(uuid.uuid4()),
        entity_id=entity.id,
        code=fcode,
        label_en=body.get("label_en"),
        label_ar=body.get("label_ar"),
        field_type=ftype,
        is_required=body.get("is_required", False),
        ui_config=body.get("ui_config", {}),
        enum_values=body.get("enum_values", []),
    )
    db.add(field)
    db.flush()

    ve = VersioningEngine(db)
    ver = ve.create_version(
        entity_id=entity.id,
        change_type="add_field",
        changed_by=current_user.get("id", current_user.get("user_id", "unknown")),
        change_summary=f"Added field '{fcode}' ({ftype})",
    )

    EventBus(db).emit("field.added", entity_code, tenant_id=current_user.get("tenant_id"), user_id=current_user.get("id", current_user.get("user_id")), payload={"field_code": fcode, "field_type": ftype})

    db.commit()

    return {"status": "success", "field_code": fcode, "version": ver["version_number"]}


@router.put(
    "/entities/{entity_code}/fields/{field_code}",
    dependencies=[
        Depends(require_permission("dynamic", "update")),
        Depends(write_limiter.check),
    ],
)
async def update_field(
    entity_code: str,
    field_code: str,
    body: dict,
    db: Session = Depends(get_db),
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
    if "label_en" in body and body["label_en"] != field.label_en:
        field.label_en = body["label_en"]
        changed.append("label_en")
    if "label_ar" in body and body["label_ar"] != field.label_ar:
        field.label_ar = body["label_ar"]
        changed.append("label_ar")
    if "field_type" in body:
        if body["field_type"] not in ALLOWED_FIELD_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid field_type: {body['field_type']}")
        if body["field_type"] != field.field_type:
            field.field_type = body["field_type"]
            changed.append("field_type")
    if "is_required" in body and body["is_required"] != field.is_required:
        field.is_required = body["is_required"]
        changed.append("is_required")
    if "ui_config" in body and body["ui_config"] != (field.ui_config or {}):
        field.ui_config = body["ui_config"]
        changed.append("ui_config")
    if "enum_values" in body and body["enum_values"] != (field.enum_values or []):
        field.enum_values = body["enum_values"]
        changed.append("enum_values")

    if not changed:
        return {"status": "success", "message": "No changes"}

    db.flush()

    ve = VersioningEngine(db)
    ver = ve.create_version(
        entity_id=entity.id,
        change_type="update_field",
        changed_by=current_user.get("id", current_user.get("user_id", "unknown")),
        change_summary=f"Updated field '{field_code}': {', '.join(changed)}",
    )

    EventBus(db).emit("field.updated", entity_code, tenant_id=current_user.get("tenant_id"), user_id=current_user.get("id", current_user.get("user_id")), payload={"field_code": field_code, "changed": changed})

    db.commit()

    return {"status": "success", "version": ver["version_number"], "changed": changed}


@router.delete(
    "/entities/{entity_code}/fields/{field_code}",
    dependencies=[
        Depends(require_permission("dynamic", "delete")),
        Depends(write_limiter.check),
    ],
)
async def remove_field(
    entity_code: str,
    field_code: str,
    db: Session = Depends(get_db),
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

    db.delete(field)
    db.flush()

    ve = VersioningEngine(db)
    ver = ve.create_version(
        entity_id=entity.id,
        change_type="remove_field",
        changed_by=current_user.get("id", current_user.get("user_id", "unknown")),
        change_summary=f"Removed field '{field_code}'",
    )

    EventBus(db).emit("field.removed", entity_code, tenant_id=current_user.get("tenant_id"), user_id=current_user.get("id", current_user.get("user_id")), payload={"field_code": field_code})

    db.commit()

    return {"status": "success", "version": ver["version_number"]}


# ──────────────────────────────────────────────────────────────
# VERSION ENDPOINTS
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/versions",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def list_versions(
    entity_code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    ve = VersioningEngine(db)
    versions = ve.get_versions(entity.id)
    return {"data": versions, "count": len(versions)}


@router.get(
    "/entities/{entity_code}/versions/{version_number}",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def get_version(
    entity_code: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    entity = db.query(DBPEntity).filter(DBPEntity.code == entity_code).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    ve = VersioningEngine(db)
    version = ve.get_version(entity.id, version_number)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return {"data": version}
