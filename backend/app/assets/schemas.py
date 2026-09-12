from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import ASSET_STATUSES, MAINTENANCE_FREQUENCIES, MAINTENANCE_TYPES


# ---------------------------------------------------------------------------
# AssetCategory
# ---------------------------------------------------------------------------
class AssetCategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class AssetCategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)


class AssetCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------
class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: UUID | None = None
    asset_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    purchase_date: date | None = None
    purchase_cost: Decimal = Field(default=Decimal("0"), ge=0)
    current_value: Decimal = Field(default=Decimal("0"), ge=0)
    status: str = "active"
    location: str | None = Field(default=None, max_length=500)
    assigned_to: UUID | None = None
    warranty_expiry: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ASSET_STATUSES:
            raise ValueError(f"status must be one of {sorted(ASSET_STATUSES)}")
        return v


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    purchase_date: date | None = None
    purchase_cost: Decimal | None = Field(default=None, ge=0)
    current_value: Decimal | None = Field(default=None, ge=0)
    status: str | None = None
    location: str | None = Field(default=None, max_length=500)
    assigned_to: UUID | None = None
    warranty_expiry: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ASSET_STATUSES:
            raise ValueError(f"status must be one of {sorted(ASSET_STATUSES)}")
        return v


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    category_id: UUID | None
    asset_code: str
    name: str
    description: str | None
    purchase_date: date | None
    purchase_cost: Decimal
    current_value: Decimal
    status: str
    location: str | None
    assigned_to: UUID | None
    warranty_expiry: date | None
    created_by: UUID


# ---------------------------------------------------------------------------
# MaintenanceSchedule
# ---------------------------------------------------------------------------
class MaintenanceScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: UUID
    frequency: str
    next_due_date: date
    last_performed: date | None = None

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        if v not in MAINTENANCE_FREQUENCIES:
            raise ValueError(f"frequency must be one of {sorted(MAINTENANCE_FREQUENCIES)}")
        return v


class MaintenanceScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frequency: str | None = None
    next_due_date: date | None = None
    last_performed: date | None = None

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str | None) -> str | None:
        if v is not None and v not in MAINTENANCE_FREQUENCIES:
            raise ValueError(f"frequency must be one of {sorted(MAINTENANCE_FREQUENCIES)}")
        return v


class MaintenanceScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    asset_id: UUID
    frequency: str
    next_due_date: date
    last_performed: date | None


# ---------------------------------------------------------------------------
# MaintenanceLog
# ---------------------------------------------------------------------------
class MaintenanceLogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: UUID
    schedule_id: UUID | None = None
    maintenance_type: str
    description: str | None = Field(default=None, max_length=5000)
    cost: Decimal = Field(default=Decimal("0"), ge=0)
    performed_by: UUID | None = None
    performed_at: datetime

    @field_validator("maintenance_type")
    @classmethod
    def validate_maintenance_type(cls, v: str) -> str:
        if v not in MAINTENANCE_TYPES:
            raise ValueError(f"maintenance_type must be one of {sorted(MAINTENANCE_TYPES)}")
        return v


class MaintenanceLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    asset_id: UUID
    schedule_id: UUID | None
    maintenance_type: str
    description: str | None
    cost: Decimal
    performed_by: UUID | None
    performed_at: datetime
