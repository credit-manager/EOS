from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    MILESTONE_STATUSES,
    PROJECT_PRIORITIES,
    PROJECT_STATUSES,
    TASK_PRIORITIES,
    TASK_STATUSES,
)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str = "planning"
    priority: str = "medium"
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal = Field(default=Decimal("0"), ge=0)
    progress: int = Field(default=0, ge=0, le=100)
    manager_id: UUID | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PROJECT_STATUSES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PROJECT_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(PROJECT_PRIORITIES)}")
        return v


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    priority: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = Field(default=None, ge=0)
    progress: int | None = Field(default=None, ge=0, le=100)
    manager_id: UUID | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of {sorted(PROJECT_STATUSES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is not None and v not in PROJECT_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(PROJECT_PRIORITIES)}")
        return v


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None
    status: str
    priority: str
    start_date: date | None
    end_date: date | None
    budget: Decimal
    progress: int
    manager_id: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------
class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    status: str = "todo"
    priority: str = "medium"
    assigned_to: UUID | None = None
    due_date: date | None = None
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    actual_hours: Decimal | None = Field(default=None, ge=0)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in TASK_STATUSES:
            raise ValueError(f"status must be one of {sorted(TASK_STATUSES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in TASK_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(TASK_PRIORITIES)}")
        return v


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    priority: str | None = None
    assigned_to: UUID | None = None
    due_date: date | None = None
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    actual_hours: Decimal | None = Field(default=None, ge=0)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in TASK_STATUSES:
            raise ValueError(f"status must be one of {sorted(TASK_STATUSES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is not None and v not in TASK_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(TASK_PRIORITIES)}")
        return v


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: str
    priority: str
    assigned_to: UUID | None
    due_date: date | None
    estimated_hours: Decimal | None
    actual_hours: Decimal | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------
class MilestoneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    name: str = Field(min_length=1, max_length=200)
    due_date: date
    status: str = "pending"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in MILESTONE_STATUSES:
            raise ValueError(f"status must be one of {sorted(MILESTONE_STATUSES)}")
        return v


class MilestoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    due_date: date | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in MILESTONE_STATUSES:
            raise ValueError(f"status must be one of {sorted(MILESTONE_STATUSES)}")
        return v


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    name: str
    due_date: date
    status: str
    completed_at: datetime | None
    created_at: datetime


# ---------------------------------------------------------------------------
# TimeEntry
# ---------------------------------------------------------------------------
class TimeEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    date: date
    hours: Decimal = Field(gt=0, le=24)
    description: str | None = Field(default=None, max_length=2000)


class TimeEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    task_id: UUID
    user_id: UUID
    date: date
    hours: Decimal
    description: str | None
    created_at: datetime
