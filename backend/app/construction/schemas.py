from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    CLAIM_STATUSES,
    CONTRACT_STATUSES,
    CONTRACT_TYPES,
    PROCUREMENT_PRIORITIES,
    PROCUREMENT_STATUSES,
    PROJECT_STATUSES,
)


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str = "planning"
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal = Field(default=Decimal("0"), ge=0)
    client_name: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=500)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PROJECT_STATUSES)}")
        return v


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = Field(default=None, ge=0)
    client_name: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=500)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PROJECT_STATUSES)}")
        return v


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None
    status: str
    start_date: date | None
    end_date: date | None
    budget: Decimal
    client_name: str | None
    location: str | None
    created_by: UUID


class ContractCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    contract_number: str = Field(min_length=1, max_length=50)
    contract_type: str = "main"
    title: str = Field(min_length=1, max_length=200)
    counterparty: str = Field(min_length=1, max_length=200)
    contract_value: Decimal = Field(default=Decimal("0"), ge=0)
    status: str = "draft"
    signed_date: date | None = None
    completion_date: date | None = None

    @field_validator("contract_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in CONTRACT_TYPES:
            raise ValueError(f"contract_type must be one of {sorted(CONTRACT_TYPES)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in CONTRACT_STATUSES:
            raise ValueError(f"status must be one of {sorted(CONTRACT_STATUSES)}")
        return v


class ContractUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    counterparty: str | None = Field(default=None, min_length=1, max_length=200)
    contract_value: Decimal | None = Field(default=None, ge=0)
    status: str | None = None
    signed_date: date | None = None
    completion_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in CONTRACT_STATUSES:
            raise ValueError(f"status must be one of {sorted(CONTRACT_STATUSES)}")
        return v


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    contract_number: str
    contract_type: str
    title: str
    counterparty: str
    contract_value: Decimal
    status: str
    signed_date: date | None
    completion_date: date | None
    created_by: UUID


class BOQCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: UUID
    version: int = 1


class BOQResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contract_id: UUID
    version: int
    status: str
    created_by: UUID


class BOQItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_number: int = Field(ge=1)
    description: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=0)
    unit_rate: Decimal = Field(ge=0)
    amount: Decimal = Field(ge=0)


class BOQItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    boq_id: UUID
    item_number: int
    description: str
    unit: str
    quantity: Decimal
    unit_rate: Decimal
    amount: Decimal


class ProgressClaimCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: UUID
    claim_number: str = Field(min_length=1, max_length=50)
    claim_date: date
    period_start: date
    period_end: date

    @field_validator("claim_date", "period_start", "period_end", mode="before")
    @classmethod
    def parse_date(cls, v: date | str) -> date:
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v


class ProgressClaimUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in CLAIM_STATUSES:
            raise ValueError(f"status must be one of {sorted(CLAIM_STATUSES)}")
        return v


class ProgressClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contract_id: UUID
    claim_number: str
    claim_date: date
    period_start: date
    period_end: date
    status: str
    total_amount: Decimal
    created_by: UUID


class ProgressClaimLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boq_item_id: UUID
    description: str = Field(min_length=1, max_length=500)
    quantity_completed: Decimal = Field(ge=0)
    amount: Decimal = Field(ge=0)


class ProgressClaimLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    claim_id: UUID
    boq_item_id: UUID
    description: str
    quantity_completed: Decimal
    amount: Decimal


class ProcurementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    requisition_number: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: str = "medium"

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PROCUREMENT_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(PROCUREMENT_PRIORITIES)}")
        return v


class ProcurementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    priority: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROCUREMENT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PROCUREMENT_STATUSES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is not None and v not in PROCUREMENT_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(PROCUREMENT_PRIORITIES)}")
        return v


class ProcurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    requisition_number: str
    title: str
    description: str | None
    requested_by: UUID
    status: str
    priority: str
    total_estimated: Decimal


class ProcurementLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=0)
    estimated_unit_price: Decimal = Field(ge=0)
    estimated_total: Decimal = Field(ge=0)


class ProcurementLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    procurement_id: UUID
    description: str
    unit: str
    quantity: Decimal
    estimated_unit_price: Decimal
    estimated_total: Decimal
