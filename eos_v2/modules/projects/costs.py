from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class ProjectCost:
    """A tenant-owned cost attributable to a project and optionally a work package."""

    tenant_id: UUID
    project_id: UUID
    amount: Decimal
    category: str
    source: str
    work_package_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Project cost amount must be positive")
        if not self.category.strip() or not self.source.strip():
            raise ValueError("Project cost category and source are required")

    def posting_source(self) -> str:
        return "projects.cost"
