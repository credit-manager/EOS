from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.application.metadata.versioning import MetadataVersioningService
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition
from eos_v2.domain.permissions.policy import Permission
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.interfaces.api.auth import get_current_identity, require_permission

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


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


def to_entity(request: MetadataCreateRequest) -> EntityDefinition:
    return EntityDefinition(
        tenant_id=get_tenant_context().tenant_id,
        name=request.name,
        label=request.label,
        fields=tuple(FieldDefinition(**item.model_dump()) for item in request.fields),
        relationships=tuple(RelationshipDefinition(**item.model_dump()) for item in request.relationships),
    )


@router.get("/{entity_id}", response_model=MetadataResponse)
def get_metadata(entity_id: UUID, request: Request, identity=Depends(get_current_identity)) -> MetadataResponse:
    require_permission(identity, Permission.READ)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        repository = SqlAlchemyMetadataRepository(session)
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


@router.post("", response_model=MetadataResponse, status_code=status.HTTP_201_CREATED)
def publish_metadata(request: Request, payload: MetadataCreateRequest, identity=Depends(get_current_identity)) -> MetadataResponse:
    require_permission(identity, Permission.ADMIN)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        repository = SqlAlchemyMetadataRepository(session)
        try:
            entity = MetadataVersioningService(repository).publish_new_version(to_entity(payload))
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return MetadataResponse(
        id=entity.id,
        tenant_id=entity.tenant_id,
        name=entity.name,
        label=entity.label,
        version=entity.version,
        published=entity.published,
    )
