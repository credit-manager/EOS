from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import String, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..metadata.models import MetadataEntity
from ..records.models import Record
from ..tenant import require_tenant
from .schemas import LookupItem

router = APIRouter(prefix="/api/v1/entities/{entity_code}/lookup", tags=["lookup"])


def _published_entity(db: Session, tenant_id: UUID, entity_code: str) -> MetadataEntity:
    row = db.scalar(
        select(MetadataEntity)
        .where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        )
        .order_by(MetadataEntity.version.desc())
    )
    if row is None:
        raise HTTPException(status_code=404, detail="published metadata entity not found")
    return row


def _require_read(request: Request, metadata: MetadataEntity) -> None:
    if getattr(request.state, "role", "member") == "admin":
        return
    permissions = metadata.definition.get("permissions")
    member_actions = permissions.get("member") if isinstance(permissions, dict) else None
    if member_actions is not None and "read" not in set(member_actions):
        raise HTTPException(status_code=403, detail="read permission denied")


def _label(row: Record, metadata: MetadataEntity) -> str:
    for field in metadata.definition.get("fields", []):
        if field.get("type") == "text":
            value = row.data.get(field["code"])
            if value not in (None, ""):
                return str(value)
    return str(row.id)


@router.get("", response_model=list[LookupItem])
def lookup_records(
    entity_code: str,
    request: Request,
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=25, ge=1, le=100),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> list[LookupItem]:
    metadata = _published_entity(db, tenant_id, entity_code)
    _require_read(request, metadata)

    query = select(Record).where(Record.tenant_id == tenant_id, Record.entity_code == entity_code)
    if q:
        needle = q.strip()
        if needle:
            text_fields = [
                field["code"]
                for field in metadata.definition.get("fields", [])
                if field.get("type") == "text"
            ]
            expressions: list[Any] = [Record.id.cast(String).ilike(f"%{needle}%")]
            expressions.extend(Record.data[field_code].as_string().ilike(f"%{needle}%") for field_code in text_fields)
            query = query.where(or_(*expressions))

    rows = db.scalars(query.order_by(Record.created_at.desc()).limit(limit)).all()
    return [LookupItem(id=row.id, label=_label(row, metadata), data=row.data) for row in rows]
