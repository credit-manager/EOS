from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..db import get_db
from ..metadata.models import MetadataEntity
from ..tenant import require_tenant
from .models import Record
from .schemas import RecordCreate, RecordResponse, RecordUpdate

router = APIRouter(prefix="/api/v1/entities/{entity_code}/records", tags=["records"])


def _get_published(db: Session, tenant_id: UUID, entity_code: str) -> MetadataEntity:
    row = db.scalar(
        select(MetadataEntity)
        .where(MetadataEntity.tenant_id == tenant_id, MetadataEntity.code == entity_code, MetadataEntity.published_at.is_not(None))
        .order_by(MetadataEntity.version.desc())
    )
    if row is None:
        raise HTTPException(status_code=404, detail="published metadata entity not found")
    return row


def _validate(payload: dict, metadata: MetadataEntity) -> None:
    fields = {field["code"]: field for field in metadata.definition["fields"]}
    unknown = set(payload) - set(fields)
    missing = {code for code, field in fields.items() if field.get("required") and code not in payload}
    if unknown or missing:
        detail: dict[str, list[str]] = {}
        if unknown:
            detail["unknown_fields"] = sorted(unknown)
        if missing:
            detail["missing_fields"] = sorted(missing)
        raise HTTPException(status_code=422, detail=detail)


def _response(row: Record) -> RecordResponse:
    return RecordResponse(id=row.id, tenant_id=row.tenant_id, entity_code=row.entity_code, data=row.data, version=row.version)


@router.post("", response_model=RecordResponse, status_code=201)
def create_record(entity_code: str, payload: RecordCreate, request: Request, tenant_id: UUID = Depends(require_tenant), db: Session = Depends(get_db)) -> RecordResponse:
    metadata = _get_published(db, tenant_id, entity_code)
    _validate(payload.data, metadata)
    row = Record(tenant_id=tenant_id, entity_code=entity_code, data=payload.data)
    db.add(row)
    audit_record(db, tenant_id=tenant_id, action="record.created", resource_type=entity_code, resource_id=row.id, metadata={}, request_id=request.headers.get("X-Request-ID"))
    db.commit(); db.refresh(row)
    return _response(row)


@router.get("", response_model=list[RecordResponse])
def list_records(entity_code: str, tenant_id: UUID = Depends(require_tenant), db: Session = Depends(get_db)) -> list[RecordResponse]:
    _get_published(db, tenant_id, entity_code)
    rows = db.scalars(select(Record).where(Record.tenant_id == tenant_id, Record.entity_code == entity_code).order_by(Record.created_at.desc())).all()
    return [_response(row) for row in rows]


@router.get("/{record_id}", response_model=RecordResponse)
def get_record(entity_code: str, record_id: UUID, tenant_id: UUID = Depends(require_tenant), db: Session = Depends(get_db)) -> RecordResponse:
    _get_published(db, tenant_id, entity_code)
    row = db.scalar(select(Record).where(Record.id == record_id, Record.tenant_id == tenant_id, Record.entity_code == entity_code))
    if row is None:
        raise HTTPException(status_code=404, detail="record not found")
    return _response(row)


@router.patch("/{record_id}", response_model=RecordResponse)
def update_record(entity_code: str, record_id: UUID, payload: RecordUpdate, request: Request, tenant_id: UUID = Depends(require_tenant), db: Session = Depends(get_db)) -> RecordResponse:
    metadata = _get_published(db, tenant_id, entity_code)
    _validate(payload.data, metadata)
    row = db.scalar(select(Record).where(Record.id == record_id, Record.tenant_id == tenant_id, Record.entity_code == entity_code))
    if row is None:
        raise HTTPException(status_code=404, detail="record not found")
    if row.version != payload.version:
        raise HTTPException(status_code=409, detail="record version conflict")
    row.data = payload.data
    row.version += 1
    audit_record(db, tenant_id=tenant_id, action="record.updated", resource_type=entity_code, resource_id=row.id, metadata={"version": row.version}, request_id=request.headers.get("X-Request-ID"))
    db.commit(); db.refresh(row)
    return _response(row)


@router.delete("/{record_id}", status_code=204)
def delete_record(entity_code: str, record_id: UUID, request: Request, tenant_id: UUID = Depends(require_tenant), db: Session = Depends(get_db)) -> None:
    _get_published(db, tenant_id, entity_code)
    row = db.scalar(select(Record).where(Record.id == record_id, Record.tenant_id == tenant_id, Record.entity_code == entity_code))
    if row is None:
        raise HTTPException(status_code=404, detail="record not found")
    audit_record(db, tenant_id=tenant_id, action="record.deleted", resource_type=entity_code, resource_id=row.id, metadata={}, request_id=request.headers.get("X-Request-ID"))
    db.delete(row)
    db.commit()
