"""P11 Entity Management + Schema Versioning Router.

All tenant-owned metadata is scoped to the authenticated tenant. Platform
owners may operate across tenants explicitly; ordinary users may never select
a tenant by crafting a request body or path.
"""
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_permission
from core.event_bus import EventBus
from core.rate_limit import read_limiter, write_limiter
from core.versioning_engine import VersioningEngine
from models import DBPEntity, DBPField
from security.tenant_scope import get_user_tenant_id, is_platform_owner

router = APIRouter(prefix="/api/v1/dynamic", tags=["Entity Management"])


def _validate_code(code: str):
    if not re.match(r'^[a-z][a-z0-9_]{0,99}$', code):
        raise HTTPException(400, "Entity code must be lowercase alphanumeric + underscore, start with letter")


def _validate_field_code(code: str):
    if not re.match(r'^[a-z][a-z0-9_]{0,99}$', code):
        raise HTTPException(400, "Field code must be lowercase alphanumeric + underscore, start with letter")


ALLOWED_FIELD_TYPES = {"string", "text", "integer", "float", "number", "boolean", "date", "datetime", "enum", "json"}


def _tenant_for_write(current_user: dict, requested=None):
    own = get_user_tenant_id(current_user)
    if is_platform_owner(current_user):
        return requested or own
    if requested and str(requested) != str(own):
        raise HTTPException(403, "Tenant access denied")
    if not own:
        raise HTTPException(403, "Authenticated user has no tenant")
    return own


def _entity_query(db, entity_code: str, current_user: dict):
    q = db.query(DBPEntity).filter(DBPEntity.code == entity_code)
    if not is_platform_owner(current_user):
        tenant_id = get_user_tenant_id(current_user)
        if not tenant_id:
            raise HTTPException(403, "Authenticated user has no tenant")
        q = q.filter(DBPEntity.tenant_id == tenant_id)
    return q


@router.post("/entities", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_entity(body: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    required = ["code", "name_en", "faculty", "table_mapping"]
    for field in required:
        if field not in body:
            raise HTTPException(400, detail=f"Missing required field: {field}")
    code = body["code"]
    _validate_code(code)
    tenant_id = _tenant_for_write(current_user, body.get("tenant_id"))
    existing_q = db.query(DBPEntity).filter(DBPEntity.code == code)
    if tenant_id is None:
        existing_q = existing_q.filter(DBPEntity.tenant_id.is_(None))
    else:
        existing_q = existing_q.filter(DBPEntity.tenant_id == tenant_id)
    if existing_q.first():
        raise HTTPException(409, detail=f"Entity '{code}' already exists for this tenant")
    table_mapping = body["table_mapping"]
    if not re.match(r'^[a-z][a-z0-9_]{0,99}$', table_mapping):
        raise HTTPException(400, "table_mapping must be safe")
    table_check = db.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name = :tname AND table_schema = 'public'"), {"tname": table_mapping}).fetchone()
    if not table_check:
        raise HTTPException(400, detail=f"Physical table '{table_mapping}' does not exist")
    entity_id = str(uuid.uuid4())
    entity = DBPEntity(id=entity_id, tenant_id=tenant_id, code=code, name_en=body["name_en"], name_ar=body.get("name_ar"), faculty=body["faculty"], table_mapping=table_mapping, is_system=body.get("is_system", False) if is_platform_owner(current_user) else False, metadata_schema=body.get("metadata_schema", {}))
    db.add(entity); db.flush()
    for fd in body.get("fields", []):
        fcode = fd.get("code")
        if not fcode: raise HTTPException(400, "Field missing 'code'")
        _validate_field_code(fcode)
        ftype = fd.get("field_type", "string")
        if ftype not in ALLOWED_FIELD_TYPES: raise HTTPException(400, detail=f"Invalid field_type: {ftype}")
        db.add(DBPField(id=str(uuid.uuid4()), entity_id=entity_id, code=fcode, label_en=fd.get("label_en"), label_ar=fd.get("label_ar"), field_type=ftype, is_required=fd.get("is_required", False), ui_config=fd.get("ui_config", {}), enum_values=fd.get("enum_values", [])))
    db.flush()
    ver = VersioningEngine(db).create_version(entity_id=entity_id, change_type="create_entity", changed_by=current_user.get("id", current_user.get("user_id", "unknown")), change_summary=f"Entity '{code}' created")
    EventBus(db).emit("entity.created", code, tenant_id=tenant_id, user_id=current_user.get("id", current_user.get("user_id")), payload={"entity_id": entity_id})
    db.commit()
    return {"status": "success", "entity_id": entity_id, "version": ver["version_number"]}


@router.put("/entities/{entity_code}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_entity(entity_code: str, body: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    entity = _entity_query(db, entity_code, current_user).first()
    if not entity: raise HTTPException(404, "Entity not found")
    if entity.is_system: raise HTTPException(403, "Cannot modify system entity")
    changed_fields = []
    for name in ("name_en", "name_ar", "faculty", "metadata_schema"):
        if name in body and body[name] != getattr(entity, name): setattr(entity, name, body[name]); changed_fields.append(name)
    if not changed_fields: return {"status": "success", "message": "No changes"}
    db.flush()
    ver = VersioningEngine(db).create_version(entity_id=entity.id, change_type="update_entity", changed_by=current_user.get("id", current_user.get("user_id", "unknown")), change_summary=f"Updated: {', '.join(changed_fields)}")
    EventBus(db).emit("entity.updated", entity_code, tenant_id=entity.tenant_id, user_id=current_user.get("id", current_user.get("user_id")), payload={"changed_fields": changed_fields})
    db.commit()
    return {"status": "success", "version": ver["version_number"], "changed": changed_fields}


@router.delete("/entities/{entity_code}", dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def delete_entity(entity_code: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    entity = _entity_query(db, entity_code, current_user).first()
    if not entity: raise HTTPException(404, "Entity not found")
    if entity.is_system: raise HTTPException(403, "Cannot delete system entity")
    rec_count = db.execute(text(f"SELECT COUNT(*) FROM {entity.table_mapping}")).scalar()
    if rec_count > 0: raise HTTPException(409, detail=f"Entity has {rec_count} records. Delete records first.")
    tenant_id = entity.tenant_id
    db.delete(entity)
    EventBus(db).emit("entity.deleted", entity_code, tenant_id=tenant_id, user_id=current_user.get("id", current_user.get("user_id")))
    db.commit()
    return {"status": "success", "deleted": entity_code}


def _field_entity(db, entity_code, current_user):
    entity = _entity_query(db, entity_code, current_user).first()
    if not entity: raise HTTPException(404, "Entity not found")
    return entity


@router.post("/entities/{entity_code}/fields", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_field(entity_code: str, body: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    entity = _field_entity(db, entity_code, current_user)
    if entity.is_system: raise HTTPException(403, "Cannot modify system entity")
    fcode = body.get("code")
    if not fcode: raise HTTPException(400, "Missing 'code'")
    _validate_field_code(fcode)
    if db.query(DBPField).filter(DBPField.entity_id == entity.id, DBPField.code == fcode).first(): raise HTTPException(409, detail=f"Field '{fcode}' already exists")
    ftype = body.get("field_type", "string")
    if ftype not in ALLOWED_FIELD_TYPES: raise HTTPException(400, detail=f"Invalid field_type: {ftype}")
    db.add(DBPField(id=str(uuid.uuid4()), entity_id=entity.id, code=fcode, label_en=body.get("label_en"), label_ar=body.get("label_ar"), field_type=ftype, is_required=body.get("is_required", False), ui_config=body.get("ui_config", {}), enum_values=body.get("enum_values", [])))
    db.flush()
    ver = VersioningEngine(db).create_version(entity_id=entity.id, change_type="add_field", changed_by=current_user.get("id", current_user.get("user_id", "unknown")), change_summary=f"Added field '{fcode}' ({ftype})")
    EventBus(db).emit("field.added", entity_code, tenant_id=entity.tenant_id, user_id=current_user.get("id", current_user.get("user_id")), payload={"field_code": fcode, "field_type": ftype})
    db.commit()
    return {"status": "success", "field_code": fcode, "version": ver["version_number"]}


@router.put("/entities/{entity_code}/fields/{field_code}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_field(entity_code: str, field_code: str, body: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    entity = _field_entity(db, entity_code, current_user)
    field = db.query(DBPField).filter(DBPField.entity_id == entity.id, DBPField.code == field_code).first()
    if not field: raise HTTPException(404, "Field not found")
    changed = []
    for name in ("label_en", "label_ar", "is_required", "ui_config", "enum_values"):
        if name in body and body[name] != getattr(field, name): setattr(field, name, body[name]); changed.append(name)
    if "field_type" in body:
        if body["field_type"] not in ALLOWED_FIELD_TYPES: raise HTTPException(400, detail=f"Invalid field_type: {body['field_type']}")
        if body["field_type"] != field.field_type: field.field_type = body["field_type"]; changed.append("field_type")
    if not changed: return {"status": "success", "message": "No changes"}
    db.flush()
    ver = VersioningEngine(db).create_version(entity_id=entity.id, change_type="update_field", changed_by=current_user.get("id", current_user.get("user_id", "unknown")), change_summary=f"Updated field '{field_code}': {', '.join(changed)}")
    EventBus(db).emit("field.updated", entity_code, tenant_id=entity.tenant_id, user_id=current_user.get("id", current_user.get("user_id")), payload={"field_code": field_code, "changed": changed})
    db.commit()
    return {"status": "success", "version": ver["version_number"], "changed": changed}


@router.delete("/entities/{entity_code}/fields/{field_code}", dependencies=[Depends(require_permission("dynamic", "delete")), Depends(write_limiter.check)])
async def remove_field(entity_code: str, field_code: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    entity = _field_entity(db, entity_code, current_user)
    if entity.is_system: raise HTTPException(403, "Cannot modify system entity")
    field = db.query(DBPField).filter(DBPField.entity_id == entity.id, DBPField.code == field_code).first()
    if not field: raise HTTPException(404, "Field not found")
    db.delete(field); db.flush()
    ver = VersioningEngine(db).create_version(entity_id=entity.id, change_type="remove_field", changed_by=current_user.get("id", current_user.get("user_id", "unknown")), change_summary=f"Removed field '{field_code}'")
    EventBus(db).emit("field.removed", entity_code, tenant_id=entity.tenant_id, user_id=current_user.get("id", current_user.get("user_id")), payload={"field_code": field_code})
    db.commit()
    return {"status": "success", "version": ver["version_number"]}


@router.get("/entities/{entity_code}/versions", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_versions(entity_code: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    entity = _field_entity(db, entity_code, current_user)
    versions = VersioningEngine(db).get_versions(entity.id)
    return {"data": versions, "count": len(versions)}


@router.get("/entities/{entity_code}/versions/{version_number}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_version(entity_code: str, version_number: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    entity = _field_entity(db, entity_code, current_user)
    version = VersioningEngine(db).get_version(entity.id, version_number)
    if not version: raise HTTPException(404, "Version not found")
    return {"data": version}
