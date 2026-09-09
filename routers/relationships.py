"""
P9 Relationship Router
API endpoints for managing entity relationships and nested reads.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from core.auth import (
    require_permission, optional_get_current_user, get_current_user
)
from core.dynamic_verification import DynamicVerificationEngine
from core.relationship_engine import RelationshipEngine
from core.versioning_engine import VersioningEngine
from core.rate_limit import read_limiter, write_limiter
from core.event_bus import EventBus
from models import DBPEntity
import uuid

router = APIRouter(
    prefix="/api/v1/dynamic",
)


# ──────────────────────────────────────────────────────────────
# RELATIONSHIP MANAGEMENT ENDPOINTS
# ──────────────────────────────────────────────────────────────

@router.post(
    "/entities/{entity_code}/relationships",
    dependencies=[
        Depends(require_permission("dynamic", "create")),
        Depends(write_limiter.check)
    ]
)
async def create_relationship(
    entity_code: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new relationship definition for an entity."""
    # Validate entity exists
    entity = db.query(DBPEntity).filter(
        DBPEntity.code == entity_code
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Extract and validate required fields
    required = ["code", "target_entity_code", "relationship_type",
                "source_column"]
    for field in required:
        if field not in body:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    try:
        engine = RelationshipEngine(db)
        rel = engine.create_relationship(
            entity_id=entity.id,
            code=body["code"],
            target_entity_code=body["target_entity_code"],
            relationship_type=body["relationship_type"],
            source_column=body["source_column"],
            target_column=body.get("target_column", "id"),
            lookup_field=body.get("lookup_field", "name_en"),
            is_required=body.get("is_required", False),
            tenant_scope=body.get("tenant_scope", True),
            on_delete=body.get("on_delete", "restrict"),
            junction_table=body.get("junction_table", ""),
            junction_source_col=body.get("junction_source_col", ""),
            junction_target_col=body.get("junction_target_col", ""),
        )

        ve = VersioningEngine(db)
        ver = ve.create_version(
            entity_id=entity.id,
            change_type="add_relationship",
            changed_by=current_user.get("id", current_user.get("user_id", "unknown")),
            change_summary=f"Added relationship '{body['code']}' → {body['target_entity_code']}",
        )

        EventBus(db).emit("relationship.created", entity_code, tenant_id=current_user.get("tenant_id"), user_id=current_user.get("id", current_user.get("user_id")), payload={"relationship_code": body["code"], "target": body["target_entity_code"]})

        db.commit()

        return {"status": "success", "relationship": rel, "version": ver["version_number"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/entities/{entity_code}/relationships",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check)
    ]
)
async def list_relationships(
    entity_code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("dynamic", "read"))
):
    """List all relationships for an entity."""
    entity = db.query(DBPEntity).filter(
        DBPEntity.code == entity_code
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    engine = RelationshipEngine(db)
    rels = engine.get_relationships(entity.id)
    return {"data": rels, "count": len(rels)}


@router.get(
    "/entities/{entity_code}/relationships/{relationship_code}",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check)
    ]
)
async def get_relationship(
    entity_code: str,
    relationship_code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("dynamic", "read"))
):
    """Get a single relationship by code."""
    entity = db.query(DBPEntity).filter(
        DBPEntity.code == entity_code
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    engine = RelationshipEngine(db)
    rel = engine.get_relationship(entity.id, relationship_code)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return {"data": rel}


@router.delete(
    "/entities/{entity_code}/relationships/{relationship_code}",
    dependencies=[
        Depends(require_permission("dynamic", "delete")),
        Depends(write_limiter.check)
    ]
)
async def delete_relationship(
    entity_code: str,
    relationship_code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a relationship definition."""
    entity = db.query(DBPEntity).filter(
        DBPEntity.code == entity_code
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    engine = RelationshipEngine(db)
    deleted = engine.delete_relationship(entity.id, relationship_code)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship not found")

    ve = VersioningEngine(db)
    ver = ve.create_version(
        entity_id=entity.id,
        change_type="remove_relationship",
        changed_by=current_user.get("id", current_user.get("user_id", "unknown")),
        change_summary=f"Removed relationship '{relationship_code}'",
    )

    EventBus(db).emit("relationship.deleted", entity_code, tenant_id=current_user.get("tenant_id"), user_id=current_user.get("id", current_user.get("user_id")), payload={"relationship_code": relationship_code})

    db.commit()

    return {"status": "success", "deleted": relationship_code, "version": ver["version_number"]}


# ──────────────────────────────────────────────────────────────
# NESTED READ ENDPOINT
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/records/{record_id}/nested",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check)
    ]
)
async def get_record_nested(
    entity_code: str,
    record_id: str,
    depth: int = Query(1, ge=0, le=3),
    db: Session = Depends(get_db),
    current_user: dict = Depends(optional_get_current_user)
):
    """
    Fetch a record with nested related records.

    depth=0: flat record only
    depth=1: record + direct relationships (default)
    depth=2: record + relationships of relationships
    depth=3: maximum nesting
    """
    entity = db.query(DBPEntity).filter(
        DBPEntity.code == entity_code
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    if not entity.table_mapping:
        raise HTTPException(status_code=400, detail="Entity has no table mapping")

    # Get tenant_id for SCOPED entities
    tenant_id = None
    if current_user:
        tenant_id = current_user["tenant_id"]

    engine = RelationshipEngine(db)
    record = engine.fetch_nested(
        entity_code, record_id, depth=depth, tenant_id=tenant_id
    )

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return {"data": record}


# ──────────────────────────────────────────────────────────────
# LOOKUP ENDPOINT (for dropdowns)
# ──────────────────────────────────────────────────────────────

@router.get(
    "/entities/{entity_code}/relationships/{relationship_code}/lookup",
    dependencies=[
        Depends(require_permission("dynamic", "read")),
        Depends(read_limiter.check)
    ]
)
async def get_relationship_lookup(
    entity_code: str,
    relationship_code: str,
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(optional_get_current_user)
):
    """
    Get lookup data for a relationship (for dropdowns/selects).

    Returns [{id, label}, ...] format.
    """
    # Entity lookup via raw SQL
    ent_row = db.execute(
        text("SELECT id, table_mapping FROM dbp_entities WHERE code = :code"),
        {"code": entity_code}
    ).fetchone()
    if not ent_row:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity_id = ent_row[0]
    table_mapping = ent_row[1]

    # Check tenant via raw SQL
    has_tenant = False
    if table_mapping:
        has_tenant = db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :tname AND column_name = 'tenant_id'"
            ),
            {"tname": table_mapping}
        ).fetchone() is not None

    tenant_id = None
    if has_tenant:
        if not current_user:
            raise HTTPException(status_code=401, detail="Auth required")
        tenant_id = current_user["tenant_id"]

    # Get relationship via raw SQL
    rel_row = db.execute(
        text(
            "SELECT target_entity_code, relationship_type, source_column, "
            "target_column, lookup_field, tenant_scope "
            "FROM dbp_relationships "
            "WHERE entity_id = :eid AND code = :code"
        ),
        {"eid": entity_id, "code": relationship_code}
    ).fetchone()
    if not rel_row:
        raise HTTPException(status_code=404, detail="Relationship not found")

    target_entity_code = rel_row[0]
    lookup_col = rel_row[4]
    rel_tenant_scope = rel_row[5]

    # Get target entity table via raw SQL
    tgt_row = db.execute(
        text("SELECT table_mapping FROM dbp_entities WHERE code = :code"),
        {"code": target_entity_code}
    ).fetchone()
    if not tgt_row or not tgt_row[0]:
        raise HTTPException(status_code=400, detail="Target entity invalid")

    target_table = tgt_row[0]

    # Build query
    where_parts = []
    params = {}

    if q:
        where_parts.append(f"{lookup_col} ILIKE :search")
        params["search"] = f"%{q}%"

    if rel_tenant_scope and tenant_id:
        where_parts.append("tenant_id = :tenant_id")
        params["tenant_id"] = tenant_id

    where_sql = " AND ".join(where_parts) if where_parts else "1=1"

    query = text(
        f"SELECT id, {lookup_col} FROM {target_table} "
        f"WHERE {where_sql} "
        f"ORDER BY {lookup_col} ASC "
        f"LIMIT 50"
    )
    rows = db.execute(query, params).fetchall()

    return {
        "data": [
            {"id": str(row[0]), "label": str(row[1])}
            for row in rows
        ]
    }
