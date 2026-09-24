"""Metadata Engine service — single source of truth for versioning and publishing.

Contract (B01):
- Entity identity = tenant_id + code; version is a revision number.
- Draft   (published_at IS NULL): editable, invisible to runtime.
- Publish (published_at NOT NULL): immutable, visible to runtime.

Deploy rules:
- No entity            -> create v1 Draft
- Latest is Draft      -> update the same Draft version in place
- Latest is Published  -> create vN+1 Draft (never mutate published)
- Published + Draft    -> update Draft only

Publish rules:
- Latest Draft         -> mark same version Published
- Latest Published     -> idempotent no-op (returns current published row)

Runtime visibility:
- get_published_definition returns the latest *Published* version only.
"""
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from .models import MetadataEntity


def _latest(db: Session, tenant_id: UUID, code: str) -> MetadataEntity | None:
    return db.scalar(
        select(MetadataEntity)
        .where(MetadataEntity.tenant_id == tenant_id, MetadataEntity.code == code)
        .order_by(MetadataEntity.version.desc())
    )


def get_published_definition(db: Session, tenant_id: UUID, code: str) -> MetadataEntity | None:
    """Return the latest PUBLISHED version of an entity, or None.

    Drafts are never visible to the runtime through this function.
    """
    return db.scalar(
        select(MetadataEntity)
        .where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == code,
            MetadataEntity.published_at.is_not(None),
        )
        .order_by(MetadataEntity.version.desc())
    )


def deploy_definition(
    db: Session,
    *,
    tenant_id: UUID,
    actor_id: UUID | None,
    code: str,
    name: str,
    definition: dict[str, Any],
    request_id: str | None = None,
) -> MetadataEntity:
    """Apply the unified Deploy contract and persist a Draft MetadataEntity.

    Never mutates a published version. Returns the resulting Draft row.
    """
    latest = _latest(db, tenant_id, code)

    if latest is None:
        row = MetadataEntity(
            tenant_id=tenant_id,
            code=code,
            name=name,
            version=1,
            definition=definition,
        )
        db.add(row)
        action = "metadata.created"
    elif latest.published_at is None:
        # Latest is a Draft -> update the same version in place.
        row = latest
        row.name = name
        row.definition = definition
        action = "metadata.deployed"
    else:
        # Latest is Published -> create vN+1 Draft.
        row = MetadataEntity(
            tenant_id=tenant_id,
            code=code,
            name=name,
            version=latest.version + 1,
            definition=definition,
        )
        db.add(row)
        action = "metadata.deployed"

    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        resource_type="metadata_entity",
        resource_id=row.id,
        metadata={"code": code, "version": row.version},
        request_id=request_id,
    )
    db.commit()
    db.refresh(row)
    return row


def publish_latest(db: Session, tenant_id: UUID, code: str, *, actor_id: UUID | None, request_id: str | None = None) -> MetadataEntity:
    """Publish the latest Draft. Idempotent when latest is already Published."""
    latest = _latest(db, tenant_id, code)
    if latest is None:
        raise HTTPException(status_code=404, detail="metadata entity not found")
    if latest.published_at is not None:
        # Already published -> no-op, do not create a version, do not mutate.
        return latest
    latest.published_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="metadata.published",
        resource_type="metadata_entity",
        resource_id=latest.id,
        metadata={"code": code, "version": latest.version},
        request_id=request_id,
    )
    db.commit()
    db.refresh(latest)
    return latest


def assert_editable(row: MetadataEntity) -> None:
    """Service-layer immutability guard for published versions."""
    if row.published_at is not None:
        raise HTTPException(status_code=409, detail="cannot modify a published metadata version")


def delete_draft(db: Session, row: MetadataEntity) -> None:
    """Delete is allowed only for Draft rows; published versions are immutable."""
    assert_editable(row)
    db.delete(row)
    db.commit()
