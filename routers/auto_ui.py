"""
P14 Auto UI + Dynamic OpenAPI Router
Provides UI schema endpoints and dynamic OpenAPI generation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from core.auth import get_current_user, require_permission
from core.rate_limit import read_limiter
from core.ui_schema import UISchemaEngine

router = APIRouter(prefix="/api/v1/dynamic", tags=["Auto UI / Dynamic OpenAPI"])


def _get_ui_engine(db: Session = Depends(get_db)):
    return UISchemaEngine(db)


def _extract_user_context(user: dict):
    roles = user.get("roles", [])
    return roles, "admin" in roles or "*:*" in user.get("permissions", [])


def _tenant_id(user: dict) -> Optional[str]:
    value = user.get("tenant_id")
    return str(value).strip().lower() if value is not None and str(value).strip() else None


def _is_platform_owner(user: dict) -> bool:
    if "platform_owner" in user.get("roles", []):
        return True
    import os
    email = (user.get("email") or "").strip().lower()
    owners = {x.strip().lower() for x in os.getenv("EOS_PLATFORM_OWNER_EMAILS", "admin@demo.com").split(",") if x.strip()}
    return bool(email and email in owners)


def _has_column(db: Session, table_name: str, column_name: str) -> bool:
    from sqlalchemy import text
    return db.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = :table_name
          AND column_name = :column_name
        LIMIT 1
    """), {"table_name": table_name, "column_name": column_name}).fetchone() is not None


def _identifier(value: str, label: str) -> str:
    import re
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", value):
        raise HTTPException(status_code=500, detail=f"Invalid {label} mapping")
    return value


@router.get("/entities/{entity_code}/ui/form", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_form_schema(entity_code: str, mode: str = "create", user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: UISchemaEngine = Depends(_get_ui_engine)):
    if mode not in ("create", "edit"):
        raise HTTPException(status_code=400, detail={"status": "error", "error": {"code": "INVALID_MODE", "message": "mode must be 'create' or 'edit'"}})
    roles, is_admin = _extract_user_context(user)
    schema = engine.get_form_schema(entity_code, mode, roles, is_admin)
    if not schema:
        raise HTTPException(status_code=404, detail={"status": "error", "error": {"code": "ENTITY_NOT_FOUND", "message": f"Entity '{entity_code}' not found"}})
    return {"status": "success", "data": schema}


@router.get("/entities/{entity_code}/ui/list", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_list_schema(entity_code: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: UISchemaEngine = Depends(_get_ui_engine)):
    roles, is_admin = _extract_user_context(user)
    schema = engine.get_list_schema(entity_code, roles, is_admin)
    if not schema:
        raise HTTPException(status_code=404, detail={"status": "error", "error": {"code": "ENTITY_NOT_FOUND", "message": f"Entity '{entity_code}' not found"}})
    return {"status": "success", "data": schema}


@router.get("/entities/{entity_code}/ui/detail", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_detail_schema(entity_code: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: UISchemaEngine = Depends(_get_ui_engine)):
    roles, is_admin = _extract_user_context(user)
    schema = engine.get_detail_schema(entity_code, roles, is_admin)
    if not schema:
        raise HTTPException(status_code=404, detail={"status": "error", "error": {"code": "ENTITY_NOT_FOUND", "message": f"Entity '{entity_code}' not found"}})
    return {"status": "success", "data": schema}


@router.get("/entities/{entity_code}/ui/openapi", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_openapi_schema(entity_code: str, db: Session = Depends(get_db), engine: UISchemaEngine = Depends(_get_ui_engine)):
    schema = engine.get_openapi_schema(entity_code)
    if not schema:
        raise HTTPException(status_code=404, detail={"status": "error", "error": {"code": "ENTITY_NOT_FOUND", "message": f"Entity '{entity_code}' not found"}})
    return {"status": "success", "data": schema}


@router.get("/ui/entities", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_entity_ui_schemas(user: dict = Depends(get_current_user), db: Session = Depends(get_db), engine: UISchemaEngine = Depends(_get_ui_engine)):
    """List entities visible to the authenticated tenant."""
    from sqlalchemy import text
    tenant_id = _tenant_id(user)
    platform_owner = _is_platform_owner(user)
    if not tenant_id and not platform_owner:
        raise HTTPException(status_code=403, detail="Authenticated tenant context required")

    scoped = _has_column(db, "dbp_entities", "tenant_id")
    query = "SELECT code, name_en, name_ar, faculty FROM dbp_entities"
    params = {}
    if scoped and not platform_owner:
        query += " WHERE tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id
    query += " ORDER BY code ASC"
    rows = db.execute(text(query), params).fetchall()
    entities = [{"code": r[0], "name_en": r[1], "name_ar": r[2], "faculty": r[3]} for r in rows]
    return {"status": "success", "data": {"entities": entities, "count": len(entities)}}


@router.get("/entities/{entity_code}/ui/lookup/{field_code}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def ui_field_lookup(entity_code: str, field_code: str, q: str = "", limit: int = 20, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tenant-safe autocomplete for relationship fields."""
    from sqlalchemy import text
    tenant_id = _tenant_id(user)
    platform_owner = _is_platform_owner(user)
    if not tenant_id and not platform_owner:
        raise HTTPException(status_code=403, detail="Authenticated tenant context required")
    if limit < 1 or limit > 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50")

    metadata_scoped = _has_column(db, "dbp_entities", "tenant_id")
    rel_query = ("SELECT r.target_entity_code, r.lookup_field, r.source_column, r.target_column "
                 "FROM dbp_relationships r JOIN dbp_entities e ON r.entity_id = e.id "
                 "WHERE e.code = :ecode AND r.source_column = :fcode")
    rel_params = {"ecode": entity_code, "fcode": field_code}
    if metadata_scoped and not platform_owner:
        rel_query += " AND e.tenant_id = :tenant_id"
        rel_params["tenant_id"] = tenant_id
    rel = db.execute(text(rel_query), rel_params).fetchone()
    if not rel:
        raise HTTPException(status_code=404, detail={"status": "error", "error": {"code": "FIELD_NOT_FOUND", "message": f"No relationship for field '{field_code}'"}})

    target_code, lookup_field, _, _ = rel
    target_query = "SELECT table_mapping FROM dbp_entities WHERE code = :code"
    target_params = {"code": target_code}
    if metadata_scoped and not platform_owner:
        target_query += " AND tenant_id = :tenant_id"
        target_params["tenant_id"] = tenant_id
    target = db.execute(text(target_query), target_params).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail={"status": "error", "error": {"code": "TARGET_ENTITY_NOT_FOUND", "message": f"Target entity '{target_code}' not found"}})

    table = _identifier(target[0], "target table")
    lookup = _identifier(lookup_field, "lookup field")
    has_tenant = _has_column(db, table, "tenant_id")
    query = f'SELECT id, "{lookup}" FROM "{table}" WHERE "{lookup}" ILIKE :search'
    params = {"search": f"%{q}%", "lim": limit}
    if has_tenant and not platform_owner:
        query += ' AND tenant_id = :tenant_id'
        params["tenant_id"] = tenant_id
    query += f' ORDER BY "{lookup}" ASC LIMIT :lim'
    rows = db.execute(text(query), params).fetchall()
    return {"status": "success", "data": {"results": [{"id": r[0], "label": r[1]} for r in rows], "count": len(rows)}}
