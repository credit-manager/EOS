from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType, RelationshipDefinition
from eos_v2.infrastructure.db.metadata_models import MetadataEntityModel


class SqlAlchemyMetadataRepository:
    """Persistence adapter; tenant scope is always derived from TenantContext."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _to_domain(model: MetadataEntityModel) -> EntityDefinition:
        data = model.definition
        return EntityDefinition(
            id=model.id, tenant_id=model.tenant_id, name=model.name,
            label=model.label, version=model.version, published=model.published,
            fields=tuple(FieldDefinition(
                name=item["name"], field_type=FieldType(item["field_type"]),
                required=item.get("required", False), unique=item.get("unique", False),
            ) for item in data.get("fields", [])),
            relationships=tuple(RelationshipDefinition(
                name=item["name"], target_entity_id=UUID(item["target_entity_id"]),
                required=item.get("required", False),
            ) for item in data.get("relationships", [])),
        )

    def add(self, definition: EntityDefinition) -> None:
        tenant_id = get_tenant_context().tenant_id
        if definition.tenant_id != tenant_id:
            raise PermissionError("Metadata tenant does not match authenticated tenant")
        payload = {
            "fields": [{"name": f.name, "field_type": f.field_type.value, "required": f.required, "unique": f.unique} for f in definition.fields],
            "relationships": [{"name": r.name, "target_entity_id": str(r.target_entity_id), "required": r.required} for r in definition.relationships],
        }
        self.session.add(MetadataEntityModel(
            id=definition.id, tenant_id=tenant_id, name=definition.name,
            label=definition.label, version=definition.version,
            published=definition.published, definition=payload,
        ))

    def get(self, entity_id: UUID) -> EntityDefinition:
        tenant_id = get_tenant_context().tenant_id
        model = self.session.scalar(select(MetadataEntityModel).where(
            MetadataEntityModel.id == entity_id,
            MetadataEntityModel.tenant_id == tenant_id,
        ))
        if model is None:
            raise KeyError("Metadata entity not found")
        return self._to_domain(model)

    def get_latest_version(self, entity_name: str) -> int | None:
        tenant_id = get_tenant_context().tenant_id
        return self.session.scalar(select(func.max(MetadataEntityModel.version)).where(
            MetadataEntityModel.tenant_id == tenant_id,
            MetadataEntityModel.name == entity_name,
        ))

    def get_published(self, entity_name: str) -> EntityDefinition:
        tenant_id = get_tenant_context().tenant_id
        model = self.session.scalar(select(MetadataEntityModel).where(
            MetadataEntityModel.tenant_id == tenant_id,
            MetadataEntityModel.name == entity_name,
            MetadataEntityModel.published.is_(True),
        ).order_by(MetadataEntityModel.version.desc()))
        if model is None:
            raise KeyError("Published metadata entity not found")
        return self._to_domain(model)
