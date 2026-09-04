"""P11 Versioning Engine — immutable schema snapshots for dynamic entities."""
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import DBPEntity, DBPEntityVersion, DBPField, DBPRelationship


class VersioningEngine:
    """
    Manages immutable schema versioning for dynamic entities.

    Every mutation (entity create/update, field add/update/remove,
    relationship create/delete) produces a new version.
    History is immutable — no UPDATE or DELETE on versions.
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_next_version_number(self, entity_id: str) -> int:
        result = self.db.execute(
            text(
                "SELECT COALESCE(MAX(version_number), 0) "
                "FROM dbp_entity_versions WHERE entity_id = :eid"
            ),
            {"eid": entity_id},
        ).scalar()
        return result + 1

    def _build_snapshot(self, entity_id: str) -> dict[str, Any]:
        entity = self.db.query(DBPEntity).filter(
            DBPEntity.id == entity_id
        ).first()
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")

        fields = self.db.query(DBPField).filter(
            DBPField.entity_id == entity_id
        ).order_by(
            text("CAST(ui_config->>'order' AS INTEGER) ASC")
        ).all()

        relationships = self.db.query(DBPRelationship).filter(
            DBPRelationship.entity_id == entity_id
        ).all()

        return {
            "entity": {
                "code": entity.code,
                "name_en": entity.name_en,
                "name_ar": entity.name_ar,
                "faculty": entity.faculty,
                "table_mapping": entity.table_mapping,
                "is_system": entity.is_system,
                "metadata_schema": entity.metadata_schema or {},
            },
            "fields": [
                {
                    "code": f.code,
                    "label_en": f.label_en,
                    "label_ar": f.label_ar,
                    "field_type": f.field_type,
                    "is_required": f.is_required,
                    "ui_config": f.ui_config or {},
                    "enum_values": f.enum_values or [],
                }
                for f in fields
            ],
            "relationships": [
                {
                    "code": r.code,
                    "target_entity_code": r.target_entity_code,
                    "relationship_type": r.relationship_type,
                    "source_column": r.source_column,
                    "target_column": r.target_column,
                    "lookup_field": r.lookup_field,
                    "is_required": r.is_required,
                    "tenant_scope": r.tenant_scope,
                    "on_delete": r.on_delete,
                }
                for r in relationships
            ],
        }

    def create_version(
        self,
        entity_id: str,
        change_type: str,
        changed_by: str,
        change_summary: str | None = None,
    ) -> dict[str, Any]:
        version_number = self._get_next_version_number(entity_id)
        snapshot = self._build_snapshot(entity_id)

        version = DBPEntityVersion(
            id=str(uuid.uuid4()),
            entity_id=entity_id,
            version_number=version_number,
            schema_snapshot=snapshot,
            change_type=change_type,
            changed_by=changed_by,
            change_summary=change_summary,
        )
        self.db.add(version)
        self.db.flush()

        return {
            "id": version.id,
            "entity_id": version.entity_id,
            "version_number": version.version_number,
            "change_type": version.change_type,
            "changed_by": version.changed_by,
            "changed_at": str(version.changed_at) if version.changed_at else None,
            "change_summary": version.change_summary,
        }

    def get_versions(self, entity_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(DBPEntityVersion)
            .filter(DBPEntityVersion.entity_id == entity_id)
            .order_by(DBPEntityVersion.version_number.asc())
            .all()
        )
        return [
            {
                "id": r.id,
                "version_number": r.version_number,
                "change_type": r.change_type,
                "changed_by": r.changed_by,
                "changed_at": str(r.changed_at) if r.changed_at else None,
                "change_summary": r.change_summary,
            }
            for r in rows
        ]

    def get_version(
        self, entity_id: str, version_number: int
    ) -> dict[str, Any] | None:
        row = (
            self.db.query(DBPEntityVersion)
            .filter(
                DBPEntityVersion.entity_id == entity_id,
                DBPEntityVersion.version_number == version_number,
            )
            .first()
        )
        if not row:
            return None

        return {
            "id": row.id,
            "entity_id": row.entity_id,
            "version_number": row.version_number,
            "schema_snapshot": row.schema_snapshot,
            "change_type": row.change_type,
            "changed_by": row.changed_by,
            "changed_at": str(row.changed_at) if row.changed_at else None,
            "change_summary": row.change_summary,
        }

    def get_latest_version(self, entity_id: str) -> dict[str, Any] | None:
        row = (
            self.db.query(DBPEntityVersion)
            .filter(DBPEntityVersion.entity_id == entity_id)
            .order_by(DBPEntityVersion.version_number.desc())
            .first()
        )
        if not row:
            return None
        return row.version_number
