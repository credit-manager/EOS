from __future__ import annotations

from uuid import uuid4

import pytest

from eos_v2.app.tenant_context import reset_tenant_context, set_tenant_context
from eos_v2.application.metadata.versioning import MetadataVersioningService
from eos_v2.domain.metadata.entities import EntityDefinition, FieldDefinition, FieldType


class MemoryRepo:
    def __init__(self) -> None:
        self.items: list[EntityDefinition] = []

    def get(self, entity_id):
        return next(item for item in self.items if item.id == entity_id)

    def get_latest_version(self, entity_name):
        versions = [item.version for item in self.items if item.name == entity_name]
        return max(versions) if versions else None

    def add(self, definition):
        self.items.append(definition)


def test_publishing_creates_immutable_incrementing_version() -> None:
    tenant = uuid4()
    token = set_tenant_context(tenant)
    try:
        repo = MemoryRepo()
        service = MetadataVersioningService(repo)
        draft = EntityDefinition(tenant_id=tenant, name="customer", fields=(FieldDefinition("name", FieldType.TEXT),))
        first = service.publish_new_version(draft)
        second = service.publish_new_version(EntityDefinition(tenant_id=tenant, name="customer", fields=draft.fields))
        assert first.published is True and first.version == 1
        assert second.published is True and second.version == 2
    finally:
        reset_tenant_context(token)


def test_published_definition_cannot_be_published_as_new_version() -> None:
    tenant = uuid4()
    token = set_tenant_context(tenant)
    try:
        repo = MemoryRepo()
        service = MetadataVersioningService(repo)
        with pytest.raises(ValueError, match="immutable"):
            service.publish_new_version(EntityDefinition(tenant_id=tenant, name="customer", published=True))
    finally:
        reset_tenant_context(token)
