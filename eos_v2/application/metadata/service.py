from __future__ import annotations

from uuid import UUID
from typing import Protocol

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.metadata.entities import EntityDefinition


class MetadataRepository(Protocol):
    def add(self, definition: EntityDefinition) -> None: ...
    def get(self, entity_id: UUID) -> EntityDefinition: ...
    def get_published(self, entity_name: str) -> EntityDefinition: ...


class MetadataService:
    """Application boundary for tenant-owned metadata definitions.

    Persistence is delegated to the infrastructure repository; the service never
    keeps production metadata only in process memory.
    """

    def __init__(self, repository: MetadataRepository) -> None:
        self.repository = repository

    def publish(self, definition: EntityDefinition) -> EntityDefinition:
        context = get_tenant_context()
        if definition.tenant_id != context.tenant_id:
            raise PermissionError("Metadata tenant does not match authenticated tenant")
        if definition.published:
            raise ValueError("Metadata definition is already published")
        self.repository.add(definition)
        return definition

    def get(self, entity_id: UUID) -> EntityDefinition:
        context = get_tenant_context()
        definition = self.repository.get(entity_id)
        if definition.tenant_id != context.tenant_id:
            raise PermissionError("Cross-tenant metadata access denied")
        return definition

    def get_published(self, entity_name: str) -> EntityDefinition:
        return self.repository.get_published(entity_name)
