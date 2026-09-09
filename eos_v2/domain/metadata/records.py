from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class DynamicRecord:
    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID | None = None
    entity_id: UUID | None = None
    entity_version: int = 1
    data: dict[str, Any] = field(default_factory=dict)
    row_version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.tenant_id is None or self.entity_id is None:
            raise ValueError("DynamicRecord requires tenant_id and entity_id")
        if self.entity_version < 1:
            raise ValueError("Entity version must be positive")
        if self.row_version < 1:
            raise ValueError("Row version must be positive")
