from __future__ import annotations

from typing import Protocol
from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.application.metadata.versioning import MetadataVersioningService
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.modules.industry import IndustryPackBuilder


class IndustryInstallationRepository(Protocol):
    def get_pack_installation(self, pack_key: str, pack_version: str) -> tuple[UUID, ...] | None: ...
    def record_pack_installation(
        self, pack_key: str, pack_version: str, entity_ids: tuple[UUID, ...]
    ) -> None: ...


class IndustryPackService:
    def __init__(self, repository: SqlAlchemyMetadataRepository) -> None:
        self.repository = repository

    def install(self, builder: IndustryPackBuilder) -> tuple[UUID, ...]:
        tenant_id = get_tenant_context().tenant_id
        pack = builder.build(tenant_id)
        if pack.tenant_id != tenant_id:
            raise PermissionError("Industry pack tenant does not match current tenant")
        if pack.key != builder.key or pack.version != builder.version:
            raise ValueError("Industry pack builder manifest does not match built pack")

        installed = self.repository.get_pack_installation(pack.key, pack.version)
        if installed is not None:
            return installed

        versioning = MetadataVersioningService(self.repository)
        published: list[UUID] = []
        for entity in pack.entities:
            created = versioning.publish_new_version(entity)
            published.append(created.id)
        entity_ids = tuple(published)
        self.repository.record_pack_installation(pack.key, pack.version, entity_ids)
        return entity_ids
