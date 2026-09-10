from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select

from eos_v2.application.audit.service import record_event
from eos_v2.application.records.service import DynamicRecordService
from eos_v2.domain.permissions.policy import Permission
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.infrastructure.db.record_models import DynamicRecordModel
from eos_v2.infrastructure.db.record_repository import SqlAlchemyRecordRepository, UniqueValueConflict
from eos_v2.interfaces.api.auth import get_current_identity, require_permission

router = APIRouter(prefix="/api/v1", tags=["records"])


class RecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: dict[str, Any]


class RecordResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    entity_id: UUID
    entity_version: int
    data: dict[str, Any]
    row_version: int


class RecordListResponse(BaseModel):
    data: list[RecordResponse]
    count: int
    total: int
    limit: int
    offset: int
    has_next: bool


def to_response(record) -> RecordResponse:
    return RecordResponse(
        id=record.id,
        tenant_id=record.tenant_id,
        entity_id=record.entity_id,
        entity_version=record.entity_version,
        data=record.data,
        row_version=record.row_version,
    )


@router.get("/entities/{entity_id}/records", response_model=RecordListResponse)
def list_records(
    entity_id: UUID,
    request: Request,
    identity=Depends(get_current_identity),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> RecordListResponse:
    require_permission(identity, Permission.READ)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        metadata = SqlAlchemyMetadataRepository(session)
        try:
            metadata.get(entity_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Metadata entity not found") from exc
        tenant_id = identity.tenant.id
        stmt = (
            select(DynamicRecordModel)
            .where(DynamicRecordModel.entity_id == entity_id, DynamicRecordModel.tenant_id == tenant_id)
            .order_by(DynamicRecordModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        models = session.scalars(stmt).all()
        total = session.scalar(
            select(func.count()).select_from(DynamicRecordModel).where(
                DynamicRecordModel.entity_id == entity_id,
                DynamicRecordModel.tenant_id == tenant_id,
            )
        ) or 0
        records = [DynamicRecordService(SqlAlchemyRecordRepository(session)).get(model.id) for model in models]
    return RecordListResponse(
        data=[to_response(record) for record in records],
        count=len(records), total=total, limit=limit, offset=offset,
        has_next=offset + len(records) < total,
    )


@router.post("/entities/{entity_id}/records", response_model=RecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(entity_id: UUID, payload: RecordRequest, request: Request, identity=Depends(get_current_identity)) -> RecordResponse:
    require_permission(identity, Permission.WRITE)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        metadata = SqlAlchemyMetadataRepository(session)
        records = SqlAlchemyRecordRepository(session)
        try:
            definition = metadata.get(entity_id)
            record = DynamicRecordService(records).create(definition, payload.data)
            record_event(session, action="record.created", resource_type="dynamic_record", resource_id=record.id, actor_id=identity.actor.id, request_id=request.headers.get("X-Request-ID"), metadata={"entity_id": str(record.entity_id), "entity_version": record.entity_version})
            session.commit()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Metadata entity not found") from exc
        except (ValueError, UniqueValueConflict) as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return to_response(record)


@router.get("/records/{record_id}", response_model=RecordResponse)
def get_record(record_id: UUID, request: Request, identity=Depends(get_current_identity)) -> RecordResponse:
    require_permission(identity, Permission.READ)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        try:
            record = DynamicRecordService(SqlAlchemyRecordRepository(session)).get(record_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Record not found") from exc
    return to_response(record)


@router.put("/records/{record_id}", response_model=RecordResponse)
def update_record(record_id: UUID, payload: RecordRequest, request: Request, identity=Depends(get_current_identity), expected_row_version: int = Query(default=1, ge=1)) -> RecordResponse:
    require_permission(identity, Permission.WRITE)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        metadata = SqlAlchemyMetadataRepository(session)
        records = SqlAlchemyRecordRepository(session)
        service = DynamicRecordService(records)
        try:
            current = service.get(record_id)
            definition = metadata.get(current.entity_id)
            updated = service.update(definition, record_id, payload.data, expected_row_version)
            record_event(session, action="record.updated", resource_type="dynamic_record", resource_id=updated.id, actor_id=identity.actor.id, request_id=request.headers.get("X-Request-ID"), metadata={"entity_id": str(updated.entity_id), "row_version": updated.row_version})
            session.commit()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Record or metadata not found") from exc
        except UniqueValueConflict as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except RuntimeError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return to_response(updated)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: UUID, request: Request, identity=Depends(get_current_identity), expected_row_version: int = Query(default=1, ge=1)) -> None:
    require_permission(identity, Permission.WRITE)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        try:
            DynamicRecordService(SqlAlchemyRecordRepository(session)).delete(record_id, expected_row_version)
            record_event(session, action="record.deleted", resource_type="dynamic_record", resource_id=record_id, actor_id=identity.actor.id, request_id=request.headers.get("X-Request-ID"))
            session.commit()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Record not found") from exc
        except RuntimeError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
