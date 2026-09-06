from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from eos_v2.domain.metadata.entities import EntityDefinition


class ProposalStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ProposalChange:
    entity: EntityDefinition
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.rationale or len(self.rationale) > 4000:
            raise ValueError("Proposal rationale must contain 1-4000 characters")


@dataclass(frozen=True, slots=True)
class ComposerProposal:
    tenant_id: UUID
    actor_id: UUID
    prompt: str
    changes: tuple[ProposalChange, ...]
    provider: str
    id: UUID = field(default_factory=uuid4)
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.prompt.strip() or len(self.prompt) > 12000:
            raise ValueError("Prompt must contain 1-12000 characters")
        if not self.changes:
            raise ValueError("AI Composer proposal must contain at least one change")
        if not self.provider.strip() or len(self.provider) > 100:
            raise ValueError("Provider is required")
        if self.status is not ProposalStatus.DRAFT and self.decided_at is None:
            raise ValueError("A decided proposal must have a decision timestamp")
        if self.status is ProposalStatus.DRAFT and self.decided_at is not None:
            raise ValueError("Draft proposal cannot have a decision timestamp")
