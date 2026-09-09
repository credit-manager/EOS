from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from eos_v2.modules.foundation import ModuleDescriptor

DESCRIPTOR = ModuleDescriptor("purchasing", "1.0.0", "Purchasing")


class PurchaseOrderStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class PurchaseOrderLine:
    item_id: UUID
    quantity: Decimal
    unit_cost: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0 or self.unit_cost < 0:
            raise ValueError("Purchase quantity must be positive and unit cost non-negative")

    @property
    def total(self) -> Decimal:
        return self.quantity * self.unit_cost


@dataclass(frozen=True, slots=True)
class PurchaseOrder:
    tenant_id: UUID
    supplier_id: UUID
    currency: str
    lines: tuple[PurchaseOrderLine, ...]
    id: UUID = field(default_factory=uuid4)
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError("Purchase order requires at least one line")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("Currency must be a 3-letter code")
