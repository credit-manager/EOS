from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from eos_v2.modules.foundation import ModuleDescriptor

DESCRIPTOR = ModuleDescriptor("inventory", "1.0.0", "Inventory")


@dataclass(frozen=True, slots=True)
class InventoryMovement:
    tenant_id: UUID
    item_id: UUID
    warehouse_id: UUID
    quantity: Decimal
    reference_type: str
    reference_id: UUID
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.quantity == 0:
            raise ValueError("Inventory movement quantity cannot be zero")
        if not self.reference_type.strip():
            raise ValueError("Inventory movement reference type is required")


@dataclass(frozen=True, slots=True)
class StockBalance:
    tenant_id: UUID
    item_id: UUID
    warehouse_id: UUID
    quantity: Decimal

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("Stock balance cannot be negative")
