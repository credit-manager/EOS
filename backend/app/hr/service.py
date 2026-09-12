from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from .models import (
    Attendance,
    Department,
    Employee,
    LeaveRequest,
    PayrollLine,
    PayrollRun,
)

# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------

def create_department(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    code: str,
    name: str,
    description: str | None = None,
    status: str = "active",
    manager_id: UUID | None = None,
    request_id: str | None = None,
) -> Department:
    existing = db.scalar(
        select(Department).where(Department.tenant_id == tenant_id, Department.code == code)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="department code already exists")
    dept = Department(
        tenant_id=tenant_id,
        created_by=user_id,
        code=code,
        name=name,
        description=description,
        status=status,
        manager_id=manager_id,
    )
    db.add(dept)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.department.created",
        resource_type="department",
        resource_id=dept.id,
        request_id=request_id,
        metadata={"code": code, "name": name},
    )
    db.flush()
    return dept


def get_department(db: Session, *, tenant_id: UUID, department_id: UUID) -> Department:
    dept = db.get(Department, department_id)
    if dept is None or dept.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="department not found")
    return dept


def list_departments(db: Session, *, tenant_id: UUID) -> list[Department]:
    return db.scalars(
        select(Department).where(Department.tenant_id == tenant_id).order_by(Department.created_at.desc())
    ).all()


def update_department(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    department_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Department:
    dept = get_department(db, tenant_id=tenant_id, department_id=department_id)
    allowed = {"name", "description", "status", "manager_id"}
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(dept, key, value)
    dept.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.department.updated",
        resource_type="department",
        resource_id=dept.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return dept


def delete_department(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    department_id: UUID,
    request_id: str | None = None,
) -> None:
    dept = get_department(db, tenant_id=tenant_id, department_id=department_id)
    employees = db.scalars(
        select(Employee).where(Employee.tenant_id == tenant_id, Employee.department_id == department_id)
    ).all()
    if employees:
        raise HTTPException(status_code=409, detail="cannot delete department with existing employees")
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.department.deleted",
        resource_type="department",
        resource_id=dept.id,
        request_id=request_id,
    )
    db.delete(dept)
    db.flush()


# ---------------------------------------------------------------------------
# Employee
# ---------------------------------------------------------------------------

def create_employee(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    department_id: UUID | None = None,
    employee_number: str,
    first_name: str,
    last_name: str,
    email: str,
    phone: str | None = None,
    hire_date: date,
    job_title: str,
    salary: Decimal = Decimal("0"),
    status: str = "active",
    request_id: str | None = None,
) -> Employee:
    existing = db.scalar(
        select(Employee).where(
            Employee.tenant_id == tenant_id, Employee.employee_number == employee_number
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="employee number already exists")
    emp = Employee(
        tenant_id=tenant_id,
        created_by=user_id,
        department_id=department_id,
        employee_number=employee_number,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        hire_date=hire_date,
        job_title=job_title,
        salary=salary,
        status=status,
    )
    db.add(emp)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.employee.created",
        resource_type="employee",
        resource_id=emp.id,
        request_id=request_id,
        metadata={"employee_number": employee_number, "first_name": first_name, "last_name": last_name},
    )
    db.flush()
    return emp


def get_employee(db: Session, *, tenant_id: UUID, employee_id: UUID) -> Employee:
    emp = db.get(Employee, employee_id)
    if emp is None or emp.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="employee not found")
    return emp


def list_employees(db: Session, *, tenant_id: UUID) -> list[Employee]:
    return db.scalars(
        select(Employee).where(Employee.tenant_id == tenant_id).order_by(Employee.created_at.desc())
    ).all()


def update_employee(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    employee_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Employee:
    emp = get_employee(db, tenant_id=tenant_id, employee_id=employee_id)
    allowed = {
        "department_id", "employee_number", "first_name", "last_name",
        "email", "phone", "hire_date", "job_title", "salary", "status",
    }
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(emp, key, value)
    emp.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.employee.updated",
        resource_type="employee",
        resource_id=emp.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return emp


def delete_employee(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    employee_id: UUID,
    request_id: str | None = None,
) -> None:
    emp = get_employee(db, tenant_id=tenant_id, employee_id=employee_id)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.employee.deleted",
        resource_type="employee",
        resource_id=emp.id,
        request_id=request_id,
    )
    db.delete(emp)
    db.flush()


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

def create_attendance(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    employee_id: UUID,
    date_val: date,
    check_in: str | None = None,
    check_out: str | None = None,
    status: str = "present",
    notes: str | None = None,
    request_id: str | None = None,
) -> Attendance:
    existing = db.scalar(
        select(Attendance).where(
            Attendance.tenant_id == tenant_id,
            Attendance.employee_id == employee_id,
            Attendance.date == date_val,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="attendance record already exists for this date")
    att = Attendance(
        tenant_id=tenant_id,
        employee_id=employee_id,
        date=date_val,
        check_in=check_in,
        check_out=check_out,
        status=status,
        notes=notes,
    )
    db.add(att)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.attendance.created",
        resource_type="attendance",
        resource_id=att.id,
        request_id=request_id,
        metadata={"employee_id": str(employee_id), "date": str(date_val), "status": status},
    )
    db.flush()
    return att


def get_attendance(db: Session, *, tenant_id: UUID, attendance_id: UUID) -> Attendance:
    att = db.get(Attendance, attendance_id)
    if att is None or att.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="attendance record not found")
    return att


def list_attendance(db: Session, *, tenant_id: UUID, employee_id: UUID | None = None) -> list[Attendance]:
    stmt = select(Attendance).where(Attendance.tenant_id == tenant_id)
    if employee_id is not None:
        stmt = stmt.where(Attendance.employee_id == employee_id)
    return db.scalars(stmt.order_by(Attendance.date.desc())).all()


def update_attendance(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    attendance_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Attendance:
    att = get_attendance(db, tenant_id=tenant_id, attendance_id=attendance_id)
    allowed = {"check_in", "check_out", "status", "notes"}
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(att, key, value)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.attendance.updated",
        resource_type="attendance",
        resource_id=att.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return att


# ---------------------------------------------------------------------------
# LeaveRequest
# ---------------------------------------------------------------------------

def create_leave_request(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    employee_id: UUID,
    leave_type: str,
    start_date: date,
    end_date: date,
    days: int,
    reason: str | None = None,
    request_id: str | None = None,
) -> LeaveRequest:
    existing = db.scalar(
        select(LeaveRequest).where(
            LeaveRequest.tenant_id == tenant_id,
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.start_date == start_date,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="leave request already exists for this start date")
    lr = LeaveRequest(
        tenant_id=tenant_id,
        employee_id=employee_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days=days,
        reason=reason,
    )
    db.add(lr)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.leave_request.created",
        resource_type="leave_request",
        resource_id=lr.id,
        request_id=request_id,
        metadata={"employee_id": str(employee_id), "leave_type": leave_type, "days": days},
    )
    db.flush()
    return lr


def get_leave_request(db: Session, *, tenant_id: UUID, leave_request_id: UUID) -> LeaveRequest:
    lr = db.get(LeaveRequest, leave_request_id)
    if lr is None or lr.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="leave request not found")
    return lr


def list_leave_requests(db: Session, *, tenant_id: UUID, employee_id: UUID | None = None) -> list[LeaveRequest]:
    stmt = select(LeaveRequest).where(LeaveRequest.tenant_id == tenant_id)
    if employee_id is not None:
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    return db.scalars(stmt.order_by(LeaveRequest.created_at.desc())).all()


def approve_leave_request(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    leave_request_id: UUID,
    request_id: str | None = None,
) -> LeaveRequest:
    lr = get_leave_request(db, tenant_id=tenant_id, leave_request_id=leave_request_id)
    if lr.status != "pending":
        raise HTTPException(status_code=409, detail="only pending leave requests can be approved")
    lr.status = "approved"
    lr.approved_by = user_id
    lr.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.leave_request.approved",
        resource_type="leave_request",
        resource_id=lr.id,
        request_id=request_id,
    )
    db.flush()
    return lr


def reject_leave_request(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    leave_request_id: UUID,
    request_id: str | None = None,
) -> LeaveRequest:
    lr = get_leave_request(db, tenant_id=tenant_id, leave_request_id=leave_request_id)
    if lr.status != "pending":
        raise HTTPException(status_code=409, detail="only pending leave requests can be rejected")
    lr.status = "rejected"
    lr.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.leave_request.rejected",
        resource_type="leave_request",
        resource_id=lr.id,
        request_id=request_id,
    )
    db.flush()
    return lr


# ---------------------------------------------------------------------------
# PayrollRun
# ---------------------------------------------------------------------------

def create_payroll_run(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    period_start: date,
    period_end: date,
    status: str = "draft",
    request_id: str | None = None,
) -> PayrollRun:
    existing = db.scalar(
        select(PayrollRun).where(
            PayrollRun.tenant_id == tenant_id, PayrollRun.period_start == period_start
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="payroll run already exists for this period")
    pr = PayrollRun(
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        status=status,
    )
    db.add(pr)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.payroll_run.created",
        resource_type="payroll_run",
        resource_id=pr.id,
        request_id=request_id,
        metadata={"period_start": str(period_start), "period_end": str(period_end)},
    )
    db.flush()
    return pr


def get_payroll_run(db: Session, *, tenant_id: UUID, payroll_run_id: UUID) -> PayrollRun:
    pr = db.get(PayrollRun, payroll_run_id)
    if pr is None or pr.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="payroll run not found")
    return pr


def list_payroll_runs(db: Session, *, tenant_id: UUID) -> list[PayrollRun]:
    return db.scalars(
        select(PayrollRun).where(PayrollRun.tenant_id == tenant_id).order_by(PayrollRun.created_at.desc())
    ).all()


def update_payroll_run(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    payroll_run_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> PayrollRun:
    pr = get_payroll_run(db, tenant_id=tenant_id, payroll_run_id=payroll_run_id)
    allowed = {"status"}
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(pr, key, value)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.payroll_run.updated",
        resource_type="payroll_run",
        resource_id=pr.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return pr


# ---------------------------------------------------------------------------
# PayrollLine
# ---------------------------------------------------------------------------

def create_payroll_line(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    payroll_run_id: UUID,
    employee_id: UUID,
    base_salary: Decimal = Decimal("0"),
    deductions: Decimal = Decimal("0"),
    net_pay: Decimal = Decimal("0"),
    request_id: str | None = None,
) -> PayrollLine:
    pl = PayrollLine(
        tenant_id=tenant_id,
        payroll_run_id=payroll_run_id,
        employee_id=employee_id,
        base_salary=base_salary,
        deductions=deductions,
        net_pay=net_pay,
    )
    db.add(pl)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="hr.payroll_line.created",
        resource_type="payroll_line",
        resource_id=pl.id,
        request_id=request_id,
        metadata={
            "payroll_run_id": str(payroll_run_id),
            "employee_id": str(employee_id),
            "net_pay": str(net_pay),
        },
    )
    db.flush()
    return pl


def list_payroll_lines(db: Session, *, tenant_id: UUID, payroll_run_id: UUID) -> list[PayrollLine]:
    return db.scalars(
        select(PayrollLine).where(
            PayrollLine.tenant_id == tenant_id, PayrollLine.payroll_run_id == payroll_run_id
        )
    ).all()
