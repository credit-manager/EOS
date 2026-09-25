from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ── BOM ──

class BOMCreate(BaseModel):
    tenant_id: int
    product_name: str
    version: int = 1
    description: str | None = None
    is_active: bool = True


class BOMUpdate(BaseModel):
    product_name: str | None = None
    version: int | None = None
    description: str | None = None
    is_active: bool | None = None


class BOMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    product_name: str
    version: int
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BOMItemCreate(BaseModel):
    material_name: str
    quantity: int = 1
    unit_cost: int = 0


class BOMItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bom_id: int
    material_name: str
    quantity: int
    unit_cost: int


# ── Work Order ──

class WorkOrderCreate(BaseModel):
    tenant_id: int
    order_number: str
    bom_id: int
    quantity: int = 1
    planned_start: datetime | None = None
    planned_end: datetime | None = None


class WorkOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    order_number: str
    bom_id: int
    quantity: int
    status: str
    planned_start: datetime | None
    planned_end: datetime | None
    actual_start: datetime | None
    actual_end: datetime | None
    created_at: datetime


# ── Production Tracking ──

class ProductionTrackingCreate(BaseModel):
    good_quantity: int = 0
    scrap_quantity: int = 0
    notes: str | None = None


class ProductionTrackingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_order_id: int
    timestamp: datetime
    good_quantity: int
    scrap_quantity: int
    notes: str | None


# ── Quality Inspection ──

class QualityInspectionCreate(BaseModel):
    inspector: str
    result: str = "pending"
    defect_count: int = 0
    notes: str | None = None


class QualityInspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_order_id: int
    inspector: str
    result: str
    defect_count: int
    notes: str | None
    created_at: datetime
