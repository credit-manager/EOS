from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from eos_v2.modules.foundation import ModuleDescriptor

DESCRIPTOR = ModuleDescriptor("hr", "1.0.0", "Human Resources")


@dataclass(frozen=True, slots=True)
class Employee:
    tenant_id: UUID
    employee_number: str
    name: str
    hire_date: date
    id: UUID = field(default_factory=uuid4)
    active: bool = True

    def __post_init__(self) -> None:
        if not self.employee_number.strip():
            raise ValueError("Employee number is required")
        if not self.name.strip():
            raise ValueError("Employee name is required")
