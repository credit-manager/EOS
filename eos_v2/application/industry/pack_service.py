from __future__ import annotations

from uuid import UUID

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.application.metadata.versioning import MetadataVersioningService
from eos_v2.infrastructure.db.metadata_repository import SqlAlchemyMetadataRepository
from eos_v2.modules.industry import IndustryPackBuilder


class IndustryPackService:
    def __init__(self, repository: SqlAlchemyMetadataRepository) -> None:
        self.repository = repository

    def install(self, builder: IndustryPackBuilder) -> tuple[UUID, ...]:
        tenant_id = get_tenant_context().tenant_id
        pack = builder.build(tenant_id)
        if pack.tenant_id != tenant_id:
            raise PermissionError("Industry pack tenant does not match current tenant")
        versioning = MetadataVersioningService(self.repository)
        published: list[UUID] = []
        for entity in pack.entities:
            created = versioning.publish_new_version(entity)
            published.append(created.id)
        return tuple(published)
