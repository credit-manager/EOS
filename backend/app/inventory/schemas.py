from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import MOVEMENT_TYPES, REQUISITION_PRIORITIES, REQUISITION_STATUSES


# ---------------------------------------------------------------------------
# Warehouse
# ---------------------------------------------------------------------------
class WarehouseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=500)
    manager_id: UUID | None = None


class WarehouseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=500)
    manager_id: UUID | None = None


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    location: str | None
    manager_id: UUID | None
    created_by: UUID


# ---------------------------------------------------------------------------
# Product Category
# ---------------------------------------------------------------------------
class ProductCategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    parent_id: UUID | None = None


class ProductCategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_id: UUID | None = None


class ProductCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    parent_id: UUID | None


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    unit: str = Field(min_length=1, max_length=20)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    reorder_level: int = Field(default=0, ge=0)
    is_active: bool = True
    category_id: UUID | None = None


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    category_id: UUID | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    category_id: UUID | None
    sku: str
    name: str
    description: str | None
    unit: str
    unit_cost: Decimal
    reorder_level: int
    is_active: bool
    created_by: UUID


# ---------------------------------------------------------------------------
# Stock Level
# ---------------------------------------------------------------------------
class StockLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    product_id: UUID
    quantity: Decimal
    reserved: Decimal


# ---------------------------------------------------------------------------
# Stock Movement
# ---------------------------------------------------------------------------
class StockMovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warehouse_id: UUID
    product_id: UUID
    movement_type: str
    quantity: Decimal = Field(gt=0)
    reference: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("movement_type")
    @classmethod
    def validate_movement_type(cls, v: str) -> str:
        if v not in MOVEMENT_TYPES:
            raise ValueError(f"movement_type must be one of {sorted(MOVEMENT_TYPES)}")
        return v


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    product_id: UUID
    movement_type: str
    quantity: Decimal
    reference: str | None
    notes: str | None
    created_by: UUID


# ---------------------------------------------------------------------------
# Purchase Requisition
# ---------------------------------------------------------------------------
class PurchaseRequisitionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requisition_number: str = Field(min_length=1, max_length=50)
    priority: str = "medium"
    lines: list["PurchaseRequisitionLineCreate"] = Field(default_factory=list)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in REQUISITION_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(REQUISITION_PRIORITIES)}")
        return v


class PurchaseRequisitionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    priority: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in REQUISITION_STATUSES:
            raise ValueError(f"status must be one of {sorted(REQUISITION_STATUSES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is not None and v not in REQUISITION_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(REQUISITION_PRIORITIES)}")
        return v


class PurchaseRequisitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    requisition_number: str
    status: str
    priority: str
    requested_by: UUID
    lines: list["PurchaseRequisitionLineResponse"] = []


class PurchaseRequisitionLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)


class PurchaseRequisitionLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    requisition_id: UUID
    product_id: UUID
    quantity: Decimal
    unit_cost: Decimal
