from __future__ import annotations

from dataclasses import replace
from typing import Protocol
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.metadata.entities import EntityDefinition


class MetadataVersionRepository(Protocol):
    def get(self, entity_id: UUID) -> EntityDefinition: ...
    def get_latest_version(self, entity_name: str) -> int | None: ...
    def add(self, definition: EntityDefinition) -> None: ...


class MetadataVersioningService:
    """Creates immutable published versions instead of mutating live metadata."""

    def __init__(self, repository: MetadataVersionRepository) -> None:
        self.repository = repository

    def publish_new_version(self, draft: EntityDefinition) -> EntityDefinition:
        tenant_id = get_tenant_context().tenant_id
        if draft.tenant_id != tenant_id:
            raise PermissionError("Metadata tenant does not match current tenant")
        if draft.published:
            raise ValueError("Published metadata is immutable; create a new version")

        latest = self.repository.get_latest_version(draft.name)
        version = 1 if latest is None else latest + 1
        published = replace(draft, version=version, published=True)
        self.repository.add(published)
        return published
