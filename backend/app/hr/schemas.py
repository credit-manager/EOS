from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    ATTENDANCE_STATUSES,
    DEPARTMENT_STATUSES,
    EMPLOYEE_STATUSES,
    LEAVE_REQUEST_STATUSES,
    LEAVE_TYPES,
    PAYROLL_RUN_STATUSES,
)


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------
class DepartmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str = "active"
    manager_id: UUID | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in DEPARTMENT_STATUSES:
            raise ValueError(f"status must be one of {sorted(DEPARTMENT_STATUSES)}")
        return v


class DepartmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = None
    manager_id: UUID | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in DEPARTMENT_STATUSES:
            raise ValueError(f"status must be one of {sorted(DEPARTMENT_STATUSES)}")
        return v


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None
    status: str
    manager_id: UUID | None
    created_by: UUID


# ---------------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------------
class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department_id: UUID | None = None
    employee_number: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    hire_date: date
    job_title: str = Field(min_length=1, max_length=200)
    salary: Decimal = Field(default=Decimal("0"), ge=0)
    status: str = "active"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in EMPLOYEE_STATUSES:
            raise ValueError(f"status must be one of {sorted(EMPLOYEE_STATUSES)}")
        return v


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department_id: UUID | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, min_length=1, max_length=200)
    salary: Decimal | None = Field(default=None, ge=0)
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in EMPLOYEE_STATUSES:
            raise ValueError(f"status must be one of {sorted(EMPLOYEE_STATUSES)}")
        return v


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    department_id: UUID | None
    employee_number: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    hire_date: date
    job_title: str
    salary: Decimal
    status: str
    created_by: UUID


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------
class AttendanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: UUID
    date: date
    check_in: str | None = None
    check_out: str | None = None
    status: str = "present"
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ATTENDANCE_STATUSES:
            raise ValueError(f"status must be one of {sorted(ATTENDANCE_STATUSES)}")
        return v


class AttendanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_in: str | None = None
    check_out: str | None = None
    status: str | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ATTENDANCE_STATUSES:
            raise ValueError(f"status must be one of {sorted(ATTENDANCE_STATUSES)}")
        return v


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    date: date
    check_in: str | None
    check_out: str | None
    status: str
    notes: str | None


# ---------------------------------------------------------------------------
# LeaveRequest
# ---------------------------------------------------------------------------
class LeaveRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: UUID
    leave_type: str = Field(min_length=1, max_length=30)
    start_date: date
    end_date: date
    days: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=5000)

    @field_validator("leave_type")
    @classmethod
    def validate_leave_type(cls, v: str) -> str:
        if v not in LEAVE_TYPES:
            raise ValueError(f"leave_type must be one of {sorted(LEAVE_TYPES)}")
        return v


class LeaveRequestUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in LEAVE_REQUEST_STATUSES:
            raise ValueError(f"status must be one of {sorted(LEAVE_REQUEST_STATUSES)}")
        return v


class LeaveRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    leave_type: str
    start_date: date
    end_date: date
    days: int
    status: str
    reason: str | None
    approved_by: UUID | None


# ---------------------------------------------------------------------------
# PayrollRun
# ---------------------------------------------------------------------------
class PayrollRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: date
    period_end: date
    status: str = "draft"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in PAYROLL_RUN_STATUSES:
            raise ValueError(f"status must be one of {sorted(PAYROLL_RUN_STATUSES)}")
        return v


class PayrollRunUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PAYROLL_RUN_STATUSES:
            raise ValueError(f"status must be one of {sorted(PAYROLL_RUN_STATUSES)}")
        return v


class PayrollRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    period_start: date
    period_end: date
    status: str
    total_amount: Decimal
    processed_by: UUID | None


# ---------------------------------------------------------------------------
# PayrollLine
# ---------------------------------------------------------------------------
class PayrollLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payroll_run_id: UUID
    employee_id: UUID
    base_salary: Decimal = Field(default=Decimal("0"), ge=0)
    deductions: Decimal = Field(default=Decimal("0"), ge=0)
    net_pay: Decimal = Field(default=Decimal("0"), ge=0)


class PayrollLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    payroll_run_id: UUID
    employee_id: UUID
    base_salary: Decimal
    deductions: Decimal
    net_pay: Decimal
