from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..metadata.models import MetadataEntity
from ..records.models import Record

MAX_DEPTH = 3
_TITLE_CANDIDATES = ("name", "title", "label", "code", "number")


def _published(db: Session, tenant_id: UUID, entity_code: str) -> MetadataEntity | None:
    return db.scalar(
        select(MetadataEntity)
        .where(
            MetadataEntity.tenant_id == tenant_id,
            MetadataEntity.code == entity_code,
            MetadataEntity.published_at.is_not(None),
        )
        .order_by(MetadataEntity.version.desc())
    )


def can_read(metadata: MetadataEntity, role: str) -> bool:
    if role == "admin":
        return True
    permissions = metadata.definition.get("permissions")
    if not isinstance(permissions, dict):
        return "read" in {"create", "read", "update", "delete"}
    return "read" in permissions.get("member", {"create", "read", "update", "delete"})


def _ref(entity_code: str, record_id: UUID) -> str:
    return f"{entity_code}:{record_id}"


def _title(record: Record, metadata: MetadataEntity) -> str:
    data = record.data or {}
    for code in _TITLE_CANDIDATES:
        value = data.get(code)
        if isinstance(value, str) and value:
            return value
    return f"{record.entity_code} / {str(record.id)[-8:]}"


def _summary(record: Record, metadata: MetadataEntity) -> dict:
    return {
        "ref": _ref(record.entity_code, record.id),
        "entity_code": record.entity_code,
        "record_id": record.id,
        "title": _title(record, metadata),
        "data": record.data or {},
    }


def relation_edges(metadata: MetadataEntity, data: dict) -> list[dict]:
    """Extract resolved relation references from a record's data dict."""
    edges: list[dict] = []
    for field in metadata.definition.get("fields", []):
        if field.get("type") != "relation":
            continue
        raw = data.get(field["code"])
        if not raw:
            continue
        try:
            target_id = UUID(str(raw))
        except (ValueError, TypeError):
            continue
        edges.append(
            {
                "field": field["code"],
                "target_entity": field["target_entity"],
                "target_id": str(target_id),
            }
        )
    return edges


def build_story(
    db: Session,
    *,
    tenant_id: UUID,
    role: str,
    entity_code: str,
    record_id: UUID,
    depth: int = 2,
) -> dict:
    depth = max(1, min(int(depth), MAX_DEPTH))

    root_metadata = _published(db, tenant_id, entity_code)
    if root_metadata is None or not can_read(root_metadata, role):
        raise HTTPException(status_code=404, detail="entity not found")
    root = db.scalar(
        select(Record).where(
            Record.tenant_id == tenant_id,
            Record.entity_code == entity_code,
            Record.id == record_id,
        )
    )
    if root is None:
        raise HTTPException(status_code=404, detail="record not found")

    nodes: list[dict] = []
    edges: list[dict] = []
    visited: set[tuple[str, UUID]] = set()
    queue: list[tuple[Record, str, int]] = [(root, entity_code, 0)]
    metadata_cache: dict[str, MetadataEntity] = {entity_code: root_metadata}
    record_cache: dict[tuple[str, UUID], Record] = {(entity_code, root.id): root}

    while queue:
        record, current_code, current_depth = queue.pop(0)
        key = (current_code, record.id)
        if key in visited:
            continue
        visited.add(key)
        metadata = metadata_cache.get(current_code)
        if metadata is None:
            metadata = _published(db, tenant_id, current_code)
            if metadata is None:
                continue
            metadata_cache[current_code] = metadata
        nodes.append(_summary(record, metadata))
        if current_depth >= depth:
            continue
        for field in metadata.definition.get("fields", []):
            if field.get("type") != "relation":
                continue
            raw = (record.data or {}).get(field["code"])
            if not raw:
                continue
            try:
                target_id = UUID(str(raw))
            except (ValueError, TypeError):
                continue
            target_code = field["target_entity"]
            target_metadata = _published(db, tenant_id, target_code)
            if target_metadata is None or not can_read(target_metadata, role):
                continue
            target_key = (target_code, target_id)
            target = record_cache.get(target_key)
            if target is None:
                target = db.scalar(
                    select(Record).where(
                        Record.tenant_id == tenant_id,
                        Record.entity_code == target_code,
                        Record.id == target_id,
                    )
                )
                if target is None:
                    continue
                record_cache[target_key] = target
            edges.append(
                {
                    "source": _ref(current_code, record.id),
                    "target": _ref(target_code, target_id),
                    "field": field["code"],
                    "target_entity": target_code,
                }
            )
            if target_key not in visited:
                queue.append((target, target_code, current_depth + 1))

    return {"root": _summary(root, root_metadata), "nodes": nodes, "edges": edges, "depth": depth}
