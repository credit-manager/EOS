from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..tenant import require_tenant
from .models import MetadataEntity
from .schemas import MetadataDefinition, MetadataResponse

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


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
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> MetadataResponse:
    latest = db.scalar(
        select(MetadataEntity)
        .where(MetadataEntity.tenant_id == tenant_id, MetadataEntity.code == payload.code)
        .order_by(MetadataEntity.version.desc())
    )
    version = (latest.version + 1) if latest else 1
    row = MetadataEntity(
        tenant_id=tenant_id,
        code=payload.code,
        name=payload.name,
        version=version,
        definition=payload.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _response(row)


@router.post("/entities/{code}/publish", response_model=MetadataResponse)
def publish_entity(
    code: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> MetadataResponse:
    row = db.scalar(
        select(MetadataEntity)
        .where(MetadataEntity.tenant_id == tenant_id, MetadataEntity.code == code)
        .order_by(MetadataEntity.version.desc())
    )
    if row is None:
        raise HTTPException(status_code=404, detail="metadata entity not found")
    if row.published_at is None:
        row.published_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return _response(row)


@router.get("/entities/{code}", response_model=MetadataResponse)
def get_entity(
    code: str,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> MetadataResponse:
    row = db.scalar(
        select(MetadataEntity)
        .where(MetadataEntity.tenant_id == tenant_id, MetadataEntity.code == code, MetadataEntity.published_at.is_not(None))
        .order_by(MetadataEntity.version.desc())
    )
    if row is None:
        raise HTTPException(status_code=404, detail="published metadata entity not found")
    return _response(row)
