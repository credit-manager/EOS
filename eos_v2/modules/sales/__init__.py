from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from eos_v2.modules.foundation import ModuleDescriptor

DESCRIPTOR = ModuleDescriptor("sales", "1.0.0", "Sales")


class SalesOrderStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class SalesOrderLine:
    item_id: UUID
    quantity: Decimal
    unit_price: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.unit_price < 0:
            raise ValueError("Sales quantity must be positive and unit price non-negative")

    @property
    def total(self) -> Decimal:
        return self.quantity * self.unit_price


@dataclass(frozen=True, slots=True)
class SalesOrder:
    tenant_id: UUID
    customer_id: UUID
    currency: str
    lines: tuple[SalesOrderLine, ...]
    id: UUID = field(default_factory=uuid4)
    status: SalesOrderStatus = SalesOrderStatus.DRAFT

    def __post_init__(self) -> None:
        if len(self.lines) == 0:
            raise ValueError("Sales order requires at least one line")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("Currency must be a 3-letter code")
