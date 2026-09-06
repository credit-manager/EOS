from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


TenantId = UUID


@dataclass(frozen=True, slots=True)
class Tenant:
    id: TenantId
    name: str
    active: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tenant name is required")
