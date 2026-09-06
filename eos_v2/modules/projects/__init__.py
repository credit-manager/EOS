from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from uuid import UUID, uuid4

from eos_v2.modules.foundation import ModuleDescriptor

DESCRIPTOR = ModuleDescriptor("projects", "1.0.0", "Projects")


class ProjectStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Project:
    tenant_id: UUID
    code: str
    name: str
    start_date: date
    id: UUID = field(default_factory=uuid4)
    end_date: date | None = None
    status: ProjectStatus = ProjectStatus.PLANNED

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.name.strip():
            raise ValueError("Project code and name are required")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("Project end date cannot precede start date")
