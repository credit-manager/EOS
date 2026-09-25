from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..db import get_db
from ..tenant import require_admin, require_tenant
from .business_object import BusinessObjectConfig
from .business_object_registry import PREBUILT_OBJECTS, BusinessObjectRegistry
from .models import MetadataEntity, MetadataTemplate
from .service import deploy_definition, publish_latest
from .schemas import (
    MetadataDefinition,
    MetadataPermissions,
    MetadataResponse,
    MetadataSummary,
    SchemaTemplate,
    SchemaTemplateResponse,
    SchemaTemplateSummary,
)

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])
_DEFAULT_PERMISSIONS = MetadataPermissions().model_dump()


def _permissions(row: MetadataEntity) -> dict[str, list[str]]:
    raw = row.definition.get("permissions")
    if not isinstance(raw, dict):
        return _DEFAULT_PERMISSIONS
    return {
        "admin": list(raw.get("admin", _DEFAULT_PERMISSIONS["admin"])),
        "member": list(raw.get("member", _DEFAULT_PERMISSIONS["member"])),
    }


def _require_read(request: Request, row: MetadataEntity) -> None:
    role = getattr(request.state, "role", "member")
    if role != "admin" and "read" not in _permissions(row)["member"]:
        raise HTTPException(status_code=403, detail="read permission denied")


def _response(row: MetadataEntity) -> MetadataResponse:
    return MetadataResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        code=row.code,
        name=row.name,
        version=row.version,
        definition=row.definition,
        published=row.published_at is not None,
    )


@router.post("/entities", response_model=MetadataResponse, status_code=201)
def create_entity(
    payload: MetadataDefinition,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MetadataResponse:
    row = deploy_definition(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        code=payload.code,
        name=payload.name,
        definition=payload.model_dump(mode="json"),
        request_id=request.state.request_id,
    )
    return _response(row)


@router.post("/entities/{code}/publish", response_model=MetadataResponse)
def publish_entity(
    code: str,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MetadataResponse:
    row = publish_latest(
        db,
        tenant_id,
        code,
        actor_id=request.state.user_id,
        request_id=request.state.request_id,
    )
    return _response(row)


@router.get("/entities", response_model=list[MetadataSummary])
def list_entities(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[MetadataSummary]:
    rows = db.scalars(
        select(MetadataEntity)
        .where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.published_at.is_not(None),
        )
        .order_by(MetadataEntity.code, MetadataEntity.version.desc())
    ).all()
    latest_by_code: dict[str, MetadataEntity] = {}
    for row in rows:
        latest_by_code.setdefault(row.code, row)
    role = getattr(request.state, "role", "member")
    result: list[MetadataSummary] = []
    for row in latest_by_code.values():
        if role != "admin" and "read" not in _permissions(row)["member"]:
            continue
        result.append(
            MetadataSummary(
                id=row.id,
                code=row.code,
                name=row.name,
                version=row.version,
                field_count=len(row.definition.get("fields", [])),
                permissions=_permissions(row),
            )
        )
    return result


@router.get("/entities/{code}", response_model=MetadataResponse)
def get_entity(
    code: str,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> MetadataResponse:
    row = db.scalar(
        select(MetadataEntity)
        .where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == code,
            MetadataEntity.published_at.is_not(None),
        )
        .order_by(MetadataEntity.version.desc())
    )
    if row is None:
        raise HTTPException(status_code=404, detail="published metadata entity not found")
    _require_read(request, row)
    return _response(row)


# ---------------------------------------------------------------------------
# Schema Templates (Metadata Engine V2)
# ---------------------------------------------------------------------------

@router.get("/templates", response_model=list[SchemaTemplateSummary])
def list_templates(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[SchemaTemplateSummary]:
    """List available schema templates"""
    rows = db.scalars(
        select(MetadataTemplate)
        .where(MetadataTemplate.tenant_id == tenant_id)
        .order_by(MetadataTemplate.category, MetadataTemplate.name)
    ).all()

    return [
        SchemaTemplateSummary(
            id=row.id,
            code=row.code,
            name=row.name,
            description=row.description,
            entity_code=row.entity_code,
            is_builtin=row.is_builtin,
            category=row.category,
            field_count=len(_parse_json_field(row.fields_json, [])),
        )
        for row in rows
    ]


@router.get("/templates/{code}", response_model=SchemaTemplate)
def get_template(
    code: str,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> SchemaTemplate:
    """Get a schema template by code"""
    row = db.scalar(
        select(MetadataTemplate)
        .where(
            MetadataTemplate.tenant_id == tenant_id,
            MetadataTemplate.code == code,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="template not found")

    return SchemaTemplate(
        code=row.code,
        name=row.name,
        description=row.description,
        entity_code=row.entity_code,
        fields=_parse_json_field(row.fields_json, []),
        permissions=_parse_json_field(row.permissions_json, _DEFAULT_PERMISSIONS),
        groups=_parse_json_field(row.groups_json, []),
        is_builtin=row.is_builtin,
        category=row.category,
        tags=_parse_json_field(row.tags_json, []),
    )


@router.post("/templates", response_model=SchemaTemplateResponse, status_code=201)
def create_template(
    payload: SchemaTemplate,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SchemaTemplateResponse:
    """Create a new schema template"""
    # Check if code already exists
    existing = db.scalar(
        select(MetadataTemplate).where(
            MetadataTemplate.tenant_id == tenant_id,
            MetadataTemplate.code == payload.code,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="template code already exists")

    row = MetadataTemplate(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        entity_code=payload.entity_code,
        fields_json=payload.model_dump_json(mode="json", include={"fields"}),
        permissions_json=payload.permissions.model_dump_json(mode="json"),
        groups_json=payload.model_dump_json(mode="json", include={"groups"}) if payload.groups else None,
        is_builtin=payload.is_builtin,
        category=payload.category,
        tags_json=payload.model_dump_json(mode="json", include={"tags"}) if payload.tags else None,
    )
    db.add(row)

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="metadata.template.created",
        resource_type="metadata_template",
        resource_id=row.id,
        metadata={"code": payload.code, "name": payload.name},
        request_id=request.state.request_id,
    )

    db.commit()
    db.refresh(row)

    return SchemaTemplateResponse(
        id=row.id,
        code=row.code,
        name=row.name,
        description=row.description,
        entity_code=row.entity_code,
        is_builtin=row.is_builtin,
        category=row.category,
    )


@router.delete("/templates/{code}", status_code=204, response_model=None)
def delete_template(
    code: str,
    request: Request,
    tenant_id: UUID = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Delete a schema template (non-builtin only)"""
    row = db.scalar(
        select(MetadataTemplate).where(
            MetadataTemplate.tenant_id == tenant_id,
            MetadataTemplate.code == code,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="template not found")
    if row.is_builtin:
        raise HTTPException(status_code=403, detail="cannot delete builtin template")

    db.delete(row)

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=request.state.user_id,
        action="metadata.template.deleted",
        resource_type="metadata_template",
        resource_id=row.id,
        metadata={"code": code},
        request_id=request.state.request_id,
    )

    db.commit()


def _parse_json_field(json_str: str | None, default: Any) -> Any:
    """Parse a JSON field safely"""
    if not json_str:
        return default
    try:
        import json
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Business Object V2 Endpoints
# ---------------------------------------------------------------------------


class BusinessObjectSummary(BaseModel):
    entity_code: str
    entity_name: str
    description: str
    field_count: int
    relationship_count: int
    has_workflow: bool
    has_financial: bool
    is_custom: bool = False


class BusinessObjectFull(BaseModel):
    entity_code: str
    entity_name: str
    description: str
    config: dict[str, Any]
    is_custom: bool = False


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str]


class EntityGraph(BaseModel):
    entity_code: str
    relationships: list[dict[str, Any]]
    inbound: list[dict[str, Any]]


class GraphPath(BaseModel):
    from_entity: str
    to_entity: str
    path: list[dict[str, Any]]
    found: bool


@router.get("/business-objects", response_model=list[BusinessObjectSummary])
def list_business_objects(
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[BusinessObjectSummary]:
    """List all business objects (prebuilt + custom for this tenant)."""
    registry = BusinessObjectRegistry(db)
    configs = registry.list_all(str(tenant_id))

    result: list[BusinessObjectSummary] = []
    for config in configs:
        is_custom = config.entity_code not in PREBUILT_OBJECTS
        result.append(
            BusinessObjectSummary(
                entity_code=config.entity_code,
                entity_name=config.entity_name,
                description=config.description,
                field_count=len(config.fields),
                relationship_count=len(config.relationships),
                has_workflow=config.workflow is not None,
                has_financial=config.financial is not None and config.financial.has_financial_impact,
                is_custom=is_custom,
            )
        )
    return result


@router.get("/business-objects/{code}", response_model=BusinessObjectFull)
def get_business_object(
    code: str,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> BusinessObjectFull:
    """Get full business object configuration."""
    registry = BusinessObjectRegistry(db)
    config = registry.get(code, str(tenant_id))
    if config is None:
        raise HTTPException(status_code=404, detail=f"business object '{code}' not found")
    is_custom = code not in PREBUILT_OBJECTS
    return BusinessObjectFull(
        entity_code=config.entity_code,
        entity_name=config.entity_name,
        description=config.description,
        config=config.to_dict(),
        is_custom=is_custom,
    )


@router.post("/business-objects/{code}/validate", response_model=ValidationResult)
def validate_business_object(
    code: str,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> ValidationResult:
    """Validate a business object configuration."""
    registry = BusinessObjectRegistry(db)
    config = registry.get(code, str(tenant_id))
    if config is None:
        raise HTTPException(status_code=404, detail=f"business object '{code}' not found")
    errors = config.validate()
    return ValidationResult(valid=len(errors) == 0, errors=errors)


@router.get("/business-objects/{code}/graph", response_model=EntityGraph)
def get_entity_graph(
    code: str,
    request: Request,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> EntityGraph:
    """Get the entity relationship graph for a business object."""
    registry = BusinessObjectRegistry(db)
    config = registry.get(code, str(tenant_id))
    if config is None:
        raise HTTPException(status_code=404, detail=f"business object '{code}' not found")

    outbound = [r.to_dict() for r in config.relationships]

    inbound: list[dict[str, Any]] = []
    all_configs = registry.list_all(str(tenant_id))
    for other in all_configs:
        for rel in other.relationships:
            if rel.target_entity == code:
                inbound.append({
                    "source_entity": other.entity_code,
                    "relation_type": rel.relation_type,
                    "foreign_key": rel.foreign_key,
                    "label": rel.label,
                })

    return EntityGraph(
        entity_code=code,
        relationships=outbound,
        inbound=inbound,
    )


@router.get("/business-objects/graph/paths", response_model=GraphPath)
def find_entity_path(
    request: Request,
    from_entity: str = Query(..., description="Source entity code"),
    to_entity: str = Query(..., description="Target entity code"),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> GraphPath:
    """Find the shortest path between two entities in the business graph."""
    registry = BusinessObjectRegistry(db)
    path = registry.get_graph_path(from_entity, to_entity, str(tenant_id))
    return GraphPath(
        from_entity=from_entity,
        to_entity=to_entity,
        path=path,
        found=len(path) > 0,
    )
