from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base

DEPARTMENT_STATUSES = {"active", "inactive"}
EMPLOYEE_STATUSES = {"active", "inactive", "terminated"}
ATTENDANCE_STATUSES = {"present", "absent", "late", "leave"}
LEAVE_TYPES = {"annual", "sick", "personal", "maternity", "paternity", "unpaid"}
LEAVE_REQUEST_STATUSES = {"pending", "approved", "rejected"}
PAYROLL_RUN_STATUSES = {"draft", "processed", "paid"}


class Department(Base):
    __tablename__ = "hr_departments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_hr_department_tenant_code"),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_hr_department_status",
        ),
        Index("ix_hr_department_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    manager_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Employee(Base):
    __tablename__ = "hr_employees"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "employee_number", name="uq_hr_employee_tenant_number"
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'terminated')",
            name="ck_hr_employee_status",
        ),
        Index("ix_hr_employee_tenant_status", "tenant_id", "status"),
        Index("ix_hr_employee_tenant_department", "tenant_id", "department_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("hr_departments.id", ondelete="SET NULL"), nullable=True
    )
    employee_number: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    salary: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Attendance(Base):
    __tablename__ = "hr_attendance"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "employee_id", "date", name="uq_hr_attendance_tenant_emp_date"
        ),
        CheckConstraint(
            "status IN ('present', 'absent', 'late', 'leave')",
            name="ck_hr_attendance_status",
        ),
        Index("ix_hr_attendance_tenant_employee", "tenant_id", "employee_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="present")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeaveRequest(Base):
    __tablename__ = "hr_leave_requests"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "employee_id", "start_date",
            name="uq_hr_leave_tenant_emp_start",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_hr_leave_request_status",
        ),
        CheckConstraint(
            "leave_type IN ('annual', 'sick', 'personal', 'maternity', 'paternity', 'unpaid')",
            name="ck_hr_leave_request_type",
        ),
        Index("ix_hr_leave_request_tenant_employee", "tenant_id", "employee_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False
    )
    leave_type: Mapped[str] = mapped_column(String(30), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PayrollRun(Base):
    __tablename__ = "hr_payroll_runs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "period_start", name="uq_hr_payroll_tenant_period"
        ),
        CheckConstraint(
            "status IN ('draft', 'processed', 'paid')",
            name="ck_hr_payroll_run_status",
        ),
        Index("ix_hr_payroll_run_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0")
    )
    processed_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PayrollLine(Base):
    __tablename__ = "hr_payroll_lines"
    __table_args__ = (
        Index("ix_hr_payroll_line_tenant_run", "tenant_id", "payroll_run_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payroll_run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hr_payroll_runs.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False
    )
    base_salary: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0")
    )
    deductions: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0")
    )
    net_pay: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=Decimal("0")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
