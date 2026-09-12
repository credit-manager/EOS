from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import ACTIVITY_STATUSES, ACTIVITY_TYPES, CONTACT_STATUSES, OPPORTUNITY_STAGES


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
class ContactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    lead_source: str | None = Field(default=None, max_length=100)
    status: str = "lead"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in CONTACT_STATUSES:
            raise ValueError(f"status must be one of {sorted(CONTACT_STATUSES)}")
        return v


class ContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    lead_source: str | None = Field(default=None, max_length=100)
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in CONTACT_STATUSES:
            raise ValueError(f"status must be one of {sorted(CONTACT_STATUSES)}")
        return v


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    company: str | None
    job_title: str | None
    lead_source: str | None
    status: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------
class OpportunityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    value: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    stage: str = "prospecting"
    probability: int = Field(default=0, ge=0, le=100)
    expected_close_date: date | None = None
    assigned_to: UUID | None = None

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str) -> str:
        if v not in OPPORTUNITY_STAGES:
            raise ValueError(f"stage must be one of {sorted(OPPORTUNITY_STAGES)}")
        return v


class OpportunityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    value: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    stage: str | None = None
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close_date: date | None = None
    assigned_to: UUID | None = None

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str | None) -> str | None:
        if v is not None and v not in OPPORTUNITY_STAGES:
            raise ValueError(f"stage must be one of {sorted(OPPORTUNITY_STAGES)}")
        return v


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contact_id: UUID | None
    title: str
    value: Decimal
    currency: str
    stage: str
    probability: int
    expected_close_date: date | None
    assigned_to: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Activity
# ---------------------------------------------------------------------------
class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: UUID
    opportunity_id: UUID | None = None
    activity_type: str
    subject: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    due_date: datetime | None = None
    status: str = "pending"

    @field_validator("activity_type")
    @classmethod
    def validate_activity_type(cls, v: str) -> str:
        if v not in ACTIVITY_TYPES:
            raise ValueError(f"activity_type must be one of {sorted(ACTIVITY_TYPES)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ACTIVITY_STATUSES:
            raise ValueError(f"status must be one of {sorted(ACTIVITY_STATUSES)}")
        return v


class ActivityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    due_date: datetime | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ACTIVITY_STATUSES:
            raise ValueError(f"status must be one of {sorted(ACTIVITY_STATUSES)}")
        return v


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contact_id: UUID
    opportunity_id: UUID | None
    activity_type: str
    subject: str
    description: str | None
    due_date: datetime | None
    status: str
    completed_at: datetime | None
    created_by: UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------
class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: UUID
    opportunity_id: UUID | None = None
    content: str = Field(min_length=1, max_length=10000)


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contact_id: UUID
    opportunity_id: UUID | None
    content: str
    created_by: UUID
    created_at: datetime
