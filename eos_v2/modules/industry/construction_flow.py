from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class ContractMode(StrEnum):
    SALE = "sale"
    RENT = "rent"


class FlowStatus(StrEnum):
    LAND_ACQUIRED = "land_acquired"
    DEVELOPMENT_STARTED = "development_started"
    UNIT_READY = "unit_ready"
    CONTRACTED = "contracted"
    DELIVERED = "delivered"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class ConstructionFlow:
    tenant_id: UUID
    land_id: UUID
    project_id: UUID
    unit_id: UUID
    customer_id: UUID
    mode: ContractMode
    land_cost: Decimal
    construction_cost: Decimal
    contract_value: Decimal
    status: FlowStatus = FlowStatus.LAND_ACQUIRED
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.land_cost < 0 or self.construction_cost < 0 or self.contract_value <= 0:
            raise ValueError("Flow monetary values are invalid")
        if any(identifier.int == 0 for identifier in (self.land_id, self.project_id, self.unit_id, self.customer_id)):
            raise ValueError("Flow identifiers are required")

    @property
    def total_cost(self) -> Decimal:
        return self.land_cost + self.construction_cost

    @property
    def projected_margin(self) -> Decimal:
        return self.contract_value - self.total_cost

    def start_development(self) -> "ConstructionFlow":
        self._expect(FlowStatus.LAND_ACQUIRED)
        return replace(self, status=FlowStatus.DEVELOPMENT_STARTED)

    def mark_unit_ready(self) -> "ConstructionFlow":
        self._expect(FlowStatus.DEVELOPMENT_STARTED)
        return replace(self, status=FlowStatus.UNIT_READY)

    def contract(self) -> "ConstructionFlow":
        self._expect(FlowStatus.UNIT_READY)
        return replace(self, status=FlowStatus.CONTRACTED)

    def deliver(self) -> "ConstructionFlow":
        self._expect(FlowStatus.CONTRACTED)
        return replace(self, status=FlowStatus.DELIVERED)

    def close(self) -> "ConstructionFlow":
        self._expect(FlowStatus.DELIVERED)
        return replace(self, status=FlowStatus.CLOSED)

    def _expect(self, expected: FlowStatus) -> None:
        if self.status is not expected:
            raise ValueError(f"Invalid flow transition from {self.status} to next stage; expected {expected}")
