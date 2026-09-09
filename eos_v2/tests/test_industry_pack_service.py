from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from eos_v2.app.tenant_context import reset_tenant_context, set_tenant_context
from eos_v2.application.industry.pack_service import IndustryPackService
from eos_v2.domain.metadata.entities import EntityDefinition
from eos_v2.modules.industry import IndustryPack


class MemoryInstallationRepo:
    def __init__(self) -> None:
        self.versions: dict[str, int] = {}
        self.installations: dict[tuple[str, str], tuple[UUID, ...]] = {}
        self.items: dict[UUID, EntityDefinition] = {}

    def get(self, entity_id: UUID) -> EntityDefinition:
        return self.items[entity_id]

    def get_latest_version(self, entity_name: str) -> int | None:
        return self.versions.get(entity_name)

    def add(self, definition: EntityDefinition) -> None:
        self.items[definition.id] = definition
        self.versions[definition.name] = definition.version

    def get_pack_installation(self, pack_key: str, pack_version: str) -> tuple[UUID, ...] | None:
        return self.installations.get((pack_key, pack_version))

    def record_pack_installation(self, pack_key: str, pack_version: str, entity_ids: tuple[UUID, ...]) -> None:
        self.installations[(pack_key, pack_version)] = entity_ids


class FixedBuilder:
    key = "test-pack"
    version = "1.0.0"

    def __init__(self, tenant_id: UUID) -> None:
        self.tenant_id = tenant_id
        self.calls = 0

    def build(self, tenant_id: UUID) -> IndustryPack:
        self.calls += 1
        entity = EntityDefinition(tenant_id=tenant_id, name="test_entity", label="Test")
        return IndustryPack(self.key, self.version, "Test Pack", tenant_id, (entity,))


def test_installation_is_idempotent_for_same_pack_version() -> None:
    tenant = uuid4()
    token = set_tenant_context(tenant)
    try:
        repo = MemoryInstallationRepo()
        builder = FixedBuilder(tenant)
        service = IndustryPackService(repo)

        first = service.install(builder)
        second = service.install(builder)

        assert first == second
        assert len(first) == 1
        assert repo.versions["test_entity"] == 1
        assert builder.calls == 2
    finally:
        reset_tenant_context(token)


def test_installation_rejects_builder_manifest_mismatch() -> None:
    tenant = uuid4()
    token = set_tenant_context(tenant)
    try:
        repo = MemoryInstallationRepo()

        class BadBuilder(FixedBuilder):
            version = "2.0.0"

            def build(self, tenant_id: UUID) -> IndustryPack:
                return IndustryPack("test-pack", "1.0.0", "Test Pack", tenant_id, ())

        with pytest.raises(ValueError, match="manifest"):
            IndustryPackService(repo).install(BadBuilder(tenant))
    finally:
        reset_tenant_context(token)
