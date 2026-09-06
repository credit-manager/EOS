from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository

router = APIRouter(prefix="/metadata", tags=["metadata"])


class MetadataFieldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    field_type: FieldType
    required: bool = False
    unique: bool = False


class MetadataRelationshipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    target_entity_id: UUID
    required: bool = False


class MetadataCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    label: str = Field(default="", max_length=200)
    fields: list[MetadataFieldRequest] = Field(default_factory=list)
    relationships: list[MetadataRelationshipRequest] = Field(default_factory=list)


class MetadataResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    label: str
    version: int
    published: bool


def metadata_repository() -> SqlAlchemyMetadataRepository:
    raise RuntimeError("Database dependency is intentionally not wired until the v2 API composition slice")


@router.get("/{entity_id}", response_model=MetadataResponse)
def get_metadata(entity_id: UUID, repository: SqlAlchemyMetadataRepository = Depends(metadata_repository)) -> MetadataResponse:
    try:
        entity = repository.get(entity_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Metadata entity not found") from exc
    return MetadataResponse(
        id=entity.id,
        tenant_id=get_tenant_context().tenant_id,
        name=entity.name,
        label=entity.label,
        version=entity.version,
        published=entity.published,
    )


def to_entity(request: MetadataCreateRequest) -> EntityDefinition:
    return EntityDefinition(
        tenant_id=get_tenant_context().tenant_id,
        name=request.name,
        label=request.label,
        fields=tuple(FieldDefinition(**item.model_dump()) for item in request.fields),
        relationships=tuple(RelationshipDefinition(**item.model_dump()) for item in request.relationships),
    )
