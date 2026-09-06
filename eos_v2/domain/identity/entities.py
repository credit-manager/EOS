from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


ActorId = UUID


@dataclass(frozen=True, slots=True)
class Actor:
    id: ActorId
    tenant_id: UUID
    subject: str
    active: bool = True

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError("Actor subject is required")
