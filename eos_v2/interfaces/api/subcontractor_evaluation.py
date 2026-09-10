from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from eos_v2.application.audit.service import record_event
from eos_v2.application.workflow.subcontractor_evaluation import SubcontractorEvaluationWorkflow
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType
from eos_v2.domain.permissions.policy import Permission
from eos_v2.interfaces.api.auth import get_current_identity, require_permission
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.infrastructure.db.record_repository import SqlAlchemyRecordRepository
from eos_v2.application.records.service import DynamicRecordService

router = APIRouter(prefix="/api/v1/subcontractor-evaluation", tags=["vertical-slice"])


class EvaluationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subcontractor: str
    project: str
    evaluation_date: str
    quality_score: int = Field(ge=0, le=100)
    safety_score: int = Field(ge=0, le=100)
    delivery_score: int = Field(ge=0, le=100)
    notes: str = ""


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_status: str
    expected_row_version: int = Field(ge=1)


def _definition() -> EntityDefinition:
    return EntityDefinition(
        name="subcontractor_evaluation",
        label="Subcontractor Evaluation",
        fields=(
            FieldDefinition("subcontractor", FieldType.TEXT, required=True),
            FieldDefinition("project", FieldType.TEXT, required=True),
            FieldDefinition("evaluation_date", FieldType.DATE, required=True),
            FieldDefinition("quality_score", FieldType.INTEGER, required=True),
            FieldDefinition("safety_score", FieldType.INTEGER, required=True),
            FieldDefinition("delivery_score", FieldType.INTEGER, required=True),
            FieldDefinition("total_score", FieldType.INTEGER, required=True),
            FieldDefinition("status", FieldType.TEXT, required=True),
            FieldDefinition("notes", FieldType.TEXT),
        ),
        tenant_id=None,
        published=False,
    )


@router.post("/bootstrap")
def bootstrap(request: Request, identity=Depends(get_current_identity)) -> dict[str, Any]:
    require_permission(identity, Permission.ADMIN)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    from dataclasses import replace
    definition = replace(_definition(), tenant_id=identity.tenant.id)
    with database.session() as session:
        repository = SqlAlchemyMetadataRepository(session)
        try:
            existing = repository.get_published(definition.name)
            return {"id": str(existing.id), "name": existing.name, "version": existing.version, "created": False}
        except KeyError:
            repository.add(replace(definition, published=True))
            entity = repository.get(definition.id)
            record_event(session, action="vertical_slice.metadata_bootstrapped", resource_type="metadata_entity", resource_id=entity.id, actor_id=identity.actor.id, request_id=request.headers.get("X-Request-ID"), metadata={"name": entity.name})
            session.commit()
            return {"id": str(entity.id), "name": entity.name, "version": entity.version, "created": True}


@router.post("/records")
def create_evaluation(payload: EvaluationCreateRequest, request: Request, identity=Depends(get_current_identity)) -> dict[str, Any]:
    require_permission(identity, Permission.WRITE)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        metadata = SqlAlchemyMetadataRepository(session)
        try:
            definition = metadata.get_published("subcontractor_evaluation")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Bootstrap subcontractor evaluation metadata first") from exc
        service = DynamicRecordService(SqlAlchemyRecordRepository(session))
        data = payload.model_dump()
        data["total_score"] = round((payload.quality_score + payload.safety_score + payload.delivery_score) / 3)
        data["status"] = "draft"
        try:
            record = service.create(definition, data)
            record_event(session, action="vertical_slice.evaluation_created", resource_type="dynamic_record", resource_id=record.id, actor_id=identity.actor.id, request_id=request.headers.get("X-Request-ID"), metadata={"status": "draft"})
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": str(record.id), "data": record.data, "row_version": record.row_version}


@router.post("/records/{record_id}/transition")
def transition_evaluation(record_id: UUID, payload: TransitionRequest, request: Request, identity=Depends(get_current_identity)) -> dict[str, Any]:
    require_permission(identity, Permission.WRITE)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        metadata = SqlAlchemyMetadataRepository(session)
        records = SqlAlchemyRecordRepository(session)
        try:
            definition = metadata.get_published("subcontractor_evaluation")
            workflow = SubcontractorEvaluationWorkflow(records)
            updated = workflow.transition(definition, record_id, payload.target_status, payload.expected_row_version)
            record_event(session, action="vertical_slice.workflow_transition", resource_type="dynamic_record", resource_id=record_id, actor_id=identity.actor.id, request_id=request.headers.get("X-Request-ID"), metadata={"target_status": payload.target_status, "row_version": updated.row_version})
            session.commit()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Evaluation or metadata not found") from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"id": str(updated.id), "data": updated.data, "row_version": updated.row_version}


@router.get("/records")
def list_evaluations(request: Request, identity=Depends(get_current_identity), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> dict[str, Any]:
    require_permission(identity, Permission.READ)
    database = request.app.state.database
    if database is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    with database.session() as session:
        metadata = SqlAlchemyMetadataRepository(session)
        try:
            definition = metadata.get_published("subcontractor_evaluation")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Bootstrap subcontractor evaluation metadata first") from exc
        from sqlalchemy import func, select
        from eos_v2.infrastructure.db.record_models import DynamicRecordModel
        stmt = select(DynamicRecordModel).where(DynamicRecordModel.entity_id == definition.id, DynamicRecordModel.tenant_id == identity.tenant.id).order_by(DynamicRecordModel.created_at.desc()).limit(limit).offset(offset)
        rows = session.scalars(stmt).all()
        records = [DynamicRecordService(SqlAlchemyRecordRepository(session)).get(row.id) for row in rows]
        total = session.scalar(select(func.count()).select_from(DynamicRecordModel).where(DynamicRecordModel.entity_id == definition.id, DynamicRecordModel.tenant_id == identity.tenant.id)) or 0
    return {"data": [{"id": str(item.id), "data": item.data, "row_version": item.row_version} for item in records], "total": total, "limit": limit, "offset": offset, "has_next": offset + len(records) < total}
