"""Industry packs are composable metadata bundles plus explicit domain policies."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from eos_v2.domain.metadata.entities import EntityDefinition


@dataclass(frozen=True, slots=True)
class IndustryPack:
    key: str
    version: str
    display_name: str
    tenant_id: UUID
    entities: tuple[EntityDefinition, ...]


class IndustryPackBuilder(Protocol):
    key: str
    version: str

    def build(self, tenant_id: UUID) -> IndustryPack: ...
