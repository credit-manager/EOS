from __future__ import annotations

from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.metadata.entities import EntityDefinition


class MetadataService:
    """Application boundary for tenant-owned metadata definitions."""

    def __init__(self) -> None:
        self._definitions: dict[tuple[UUID, UUID], EntityDefinition] = {}

    def publish(self, definition: EntityDefinition) -> EntityDefinition:
        context = get_tenant_context()
        if definition.tenant_id != context.tenant_id:
            raise PermissionError("Metadata tenant does not match authenticated tenant")
        if definition.published:
            raise ValueError("Metadata definition is already published")
        published = EntityDefinition(
            id=definition.id,
            tenant_id=definition.tenant_id,
            name=definition.name,
            label=definition.label,
            version=definition.version,
            fields=definition.fields,
            relationships=definition.relationships,
            published=True,
        )
        self._definitions[(context.tenant_id, published.id)] = published
        return published

    def get(self, entity_id: UUID) -> EntityDefinition:
        context = get_tenant_context()
        definition = self._definitions.get((context.tenant_id, entity_id))
        if definition is None:
            raise KeyError("Metadata entity not found")
        return definition
