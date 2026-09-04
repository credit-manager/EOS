"""
P14 Auto UI + Dynamic OpenAPI Router
======================================
Provides UI schema endpoints and dynamic OpenAPI generation
for dynamic entities. All security enforced at metadata level.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.rate_limit import read_limiter
from core.ui_schema import UISchemaEngine
from database import get_db

router = APIRouter(
    prefix="/api/v1/dynamic",
    tags=["Auto UI / Dynamic OpenAPI"]
)


def _get_ui_engine(db: Session = Depends(get_db)):
    return UISchemaEngine(db)


def _extract_user_context(user: dict):
    """Extract roles and admin flag from current_user dict."""
    roles = user.get("roles", [])
    is_admin = "admin" in roles or "*:*" in roles
    return roles, is_admin


# ──────────────────────────────────────────────────────────────
# FORM SCHEMAS
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/ui/form",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def get_form_schema(
    entity_code: str,
    mode: str = "create",
    user: dict | None=None,
    db: Session = Depends(get_db),
    engine: UISchemaEngine = Depends(_get_ui_engine),
):
    """Get UI form schema for an entity (create or edit mode)."""
    if mode not in ("create", "edit"):
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "error": {
                    "code": "INVALID_MODE",
                    "message": "mode must be 'create' or 'edit'",
                    "message_en": "mode must be 'create' or 'edit'",
                },
            },
        )

    user_roles, is_admin = _extract_user_context(user)
    schema = engine.get_form_schema(entity_code, mode, user_roles, is_admin)

    if not schema:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {
                "code": "ENTITY_NOT_FOUND",
                "message": f"Entity '{entity_code}' not found",
                "message_en": f"Entity '{entity_code}' not found",
            },
        })

    return {
        "status": "success",
        "data": schema,
    }


# ──────────────────────────────────────────────────────────────
# LIST SCHEMA
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/ui/list",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def get_list_schema(
    entity_code: str,
    user: dict | None=None,
    db: Session = Depends(get_db),
    engine: UISchemaEngine = Depends(_get_ui_engine),
):
    """Get UI list/table schema for an entity."""
    user_roles, is_admin = _extract_user_context(user)
    schema = engine.get_list_schema(entity_code, user_roles, is_admin)

    if not schema:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {
                "code": "ENTITY_NOT_FOUND",
                "message": f"Entity '{entity_code}' not found",
                "message_en": f"Entity '{entity_code}' not found",
            },
        })

    return {
        "status": "success",
        "data": schema,
    }


# ──────────────────────────────────────────────────────────────
# DETAIL SCHEMA
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/ui/detail",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def get_detail_schema(
    entity_code: str,
    user: dict | None=None,
    db: Session = Depends(get_db),
    engine: UISchemaEngine = Depends(_get_ui_engine),
):
    """Get UI detail/view schema for an entity."""
    user_roles, is_admin = _extract_user_context(user)
    schema = engine.get_detail_schema(entity_code, user_roles, is_admin)

    if not schema:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {
                "code": "ENTITY_NOT_FOUND",
                "message": f"Entity '{entity_code}' not found",
                "message_en": f"Entity '{entity_code}' not found",
            },
        })

    return {
        "status": "success",
        "data": schema,
    }


# ──────────────────────────────────────────────────────────────
# OPENAPI SCHEMA
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/ui/openapi",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def get_openapi_schema(
    entity_code: str,
    db: Session = Depends(get_db),
    engine: UISchemaEngine = Depends(_get_ui_engine),
):
    """Get OpenAPI-compatible schema for a dynamic entity."""
    schema = engine.get_openapi_schema(entity_code)

    if not schema:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {
                "code": "ENTITY_NOT_FOUND",
                "message": f"Entity '{entity_code}' not found",
                "message_en": f"Entity '{entity_code}' not found",
            },
        })

    return {
        "status": "success",
        "data": schema,
    }


# ──────────────────────────────────────────────────────────────
# UI SCHEMAS FOR ALL ENTITIES (index)
# ──────────────────────────────────────────────────────────────

@router.get(
    "/ui/entities",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def list_entity_ui_schemas(
    db: Session = Depends(get_db),
    engine: UISchemaEngine = Depends(_get_ui_engine),
):
    """List all entities with basic UI metadata (for sidebar/navigation)."""
    from sqlalchemy import text as sql_text

    rows = db.execute(
        sql_text("SELECT code, name_en, name_ar, faculty "
                 "FROM dbp_entities ORDER BY code ASC")
    ).fetchall()

    entities = [
        {
            "code": r[0],
            "name_en": r[1],
            "name_ar": r[2],
            "faculty": r[3],
        }
        for r in rows
    ]

    return {
        "status": "success",
        "data": {
            "entities": entities,
            "count": len(entities),
        },
    }


# ──────────────────────────────────────────────────────────────
# RELATIONSHIP LOOKUP (UI dropdown/autocomplete)
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/ui/lookup/{field_code}",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check),
    ],
)
async def ui_field_lookup(
    entity_code: str,
    field_code: str,
    q: str = "",
    limit: int = 20,
    user: dict | None=None,
    db: Session = Depends(get_db),
):
    """
    Autocomplete/lookup endpoint for relationship fields.
    Returns matching records from the related entity.
    """
    from sqlalchemy import text as sql_text

    # Find relationship for this field
    rel = db.execute(
        sql_text(
            "SELECT r.target_entity_code, r.lookup_field, r.source_column, "
            "r.target_column "
            "FROM dbp_relationships r "
            "JOIN dbp_entities e ON r.entity_id = e.id "
            "WHERE e.code = :ecode AND r.source_column = :fcode"
        ),
        {"ecode": entity_code, "fcode": field_code},
    ).fetchone()

    if not rel:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {
                "code": "FIELD_NOT_FOUND",
                "message": f"No relationship for field '{field_code}'",
                "message_en": f"No relationship for field '{field_code}'",
            },
        })

    target_code, lookup_field, _, _target_col = rel

    # Get table_mapping for target entity
    target = db.execute(
        sql_text("SELECT table_mapping FROM dbp_entities WHERE code = :code"),
        {"code": target_code},
    ).fetchone()

    if not target:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "error": {
                "code": "TARGET_ENTITY_NOT_FOUND",
                "message": f"Target entity '{target_code}' not found",
                "message_en": f"Target entity '{target_code}' not found",
            },
        })

    table = target[0]

    # Fetch records filtered by search term
    safe_q = str(q).replace("'", "''").replace("%", "")
    query = (
        f'SELECT id, "{lookup_field}" FROM "{table}" '
        f'WHERE "{lookup_field}" ILIKE :search '
        f'ORDER BY "{lookup_field}" ASC LIMIT :lim'
    )
    rows = db.execute(
        sql_text(query),
        {"search": f"%{safe_q}%", "lim": min(limit, 50)},
    ).fetchall()

    return {
        "status": "success",
        "data": {
            "results": [
                {"id": r[0], "label": r[1]}
                for r in rows
            ],
            "count": len(rows),
        },
    }
