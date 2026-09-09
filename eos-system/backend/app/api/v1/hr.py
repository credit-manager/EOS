"""
EOS System — HR Module Router (with RBAC + Audit)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.rbac import log_audit, get_user_permissions
from app.models.hr import Employee, Department, Position, AttendanceRecord

router = APIRouter()


# Schemas
class EmployeeCreate(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    first_name_ar: Optional[str] = None
    last_name_ar: Optional[str] = None
    email: str
    phone: Optional[str] = None
    department_id: Optional[str] = None
    position_id: Optional[str] = None
    hire_date: date
    salary: Decimal
    currency: str = "EGP"
    national_id: Optional[str] = None
    social_insurance_number: Optional[str] = None


class EmployeeResponse(BaseModel):
    id: str
    employee_id: str
    first_name: str
    last_name: str
    first_name_ar: Optional[str]
    last_name_ar: Optional[str]
    email: str
    phone: Optional[str]
    department_id: Optional[str]
    position_id: Optional[str]
    hire_date: date
    salary: float
    currency: str
    status: str
    created_at: datetime


class EmployeeListResponse(BaseModel):
    employees: List[EmployeeResponse]
    total: int


class DepartmentCreate(BaseModel):
    code: str
    name: str
    name_ar: str
    manager_id: Optional[str] = None
    parent_id: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: str
    code: str
    name: str
    name_ar: str
    manager_id: Optional[str]
    parent_id: Optional[str]
    created_at: datetime


class AttendanceCreate(BaseModel):
    employee_id: str
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: str = "present"
    notes: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: str
    employee_id: str
    date: date
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    status: str
    notes: Optional[str]
    created_at: datetime


class AttendanceRecordListResponse(BaseModel):
    records: List[AttendanceResponse]
    total: int


# ─── EMPLOYEES ────────────────────────────────────────────

@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(
    department_id: Optional[str] = None,
    status: Optional[str] = "active",
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "hr:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires hr:read")

    query = select(Employee)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if status:
        query = query.filter(Employee.status == status)
    if search:
        query = query.filter(
            (Employee.first_name.ilike(f"%{search}%"))
            | (Employee.last_name.ilike(f"%{search}%"))
            | (Employee.email.ilike(f"%{search}%"))
        )
    query = query.order_by(Employee.last_name, Employee.first_name)

    count_q = select(func.count(Employee.id))
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    employees = result.scalars().all()

    return EmployeeListResponse(
        employees=[
            EmployeeResponse(
                id=e.id, employee_id=e.employee_id, first_name=e.first_name,
                last_name=e.last_name, first_name_ar=e.first_name_ar,
                last_name_ar=e.last_name_ar, email=e.email, phone=e.phone,
                department_id=e.department_id, position_id=e.position_id,
                hire_date=e.hire_date, salary=float(e.salary), currency=e.currency,
                status=e.status, created_at=e.created_at,
            )
            for e in employees
        ],
        total=total,
    )


@router.post("/employees", response_model=EmployeeResponse)
async def create_employee(
    employee: EmployeeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "hr:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires hr:create")

    existing = await db.execute(
        select(Employee).filter(Employee.employee_id == employee.employee_id)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Employee ID already exists")

    new_emp = Employee(
        id=str(uuid.uuid4()), employee_id=employee.employee_id,
        first_name=employee.first_name, last_name=employee.last_name,
        first_name_ar=employee.first_name_ar, last_name_ar=employee.last_name_ar,
        email=employee.email, phone=employee.phone,
        department_id=employee.department_id, position_id=employee.position_id,
        hire_date=employee.hire_date, salary=employee.salary,
        currency=employee.currency, national_id=employee.national_id,
        social_insurance_number=employee.social_insurance_number, status="active",
    )
    db.add(new_emp)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="hr",
        entity_type="Employee", entity_id=new_emp.id,
        entity_name=f"{new_emp.first_name} {new_emp.last_name}",
        request=request,
    )

    return EmployeeResponse(
        id=new_emp.id, employee_id=new_emp.employee_id,
        first_name=new_emp.first_name, last_name=new_emp.last_name,
        first_name_ar=new_emp.first_name_ar, last_name_ar=new_emp.last_name_ar,
        email=new_emp.email, phone=new_emp.phone,
        department_id=new_emp.department_id, position_id=new_emp.position_id,
        hire_date=new_emp.hire_date, salary=float(new_emp.salary),
        currency=new_emp.currency, status=new_emp.status, created_at=new_emp.created_at,
    )


@router.delete("/employees/{employee_id}")
async def delete_employee(
    employee_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "hr:delete" not in permissions:
        raise HTTPException(status_code=403, detail="Requires hr:delete")

    result = await db.execute(select(Employee).filter(Employee.id == employee_id))
    emp = result.scalar()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    old_name = f"{emp.first_name} {emp.last_name}"
    emp.status = "terminated"
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="delete", module="hr",
        entity_type="Employee", entity_id=employee_id,
        entity_name=old_name, request=request,
    )

    return {"message": "Employee terminated"}


# ─── DEPARTMENTS ──────────────────────────────────────────

@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "hr:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires hr:read")

    result = await db.execute(select(Department).order_by(Department.name))
    departments = result.scalars().all()
    return [DepartmentResponse(
        id=d.id, code=d.code, name=d.name, name_ar=d.name_ar,
        manager_id=d.manager_id, parent_id=d.parent_id, created_at=d.created_at,
    ) for d in departments]


@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    department: DepartmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "hr:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires hr:create")

    new_dept = Department(
        id=str(uuid.uuid4()), code=department.code, name=department.name,
        name_ar=department.name_ar, manager_id=department.manager_id,
        parent_id=department.parent_id,
    )
    db.add(new_dept)
    await db.flush()

    await log_audit(
        db, tenant_id=current_user["tenant_id"], user=current_user,
        action="create", module="hr",
        entity_type="Department", entity_id=new_dept.id,
        entity_name=new_dept.name, request=request,
    )

    return DepartmentResponse(
        id=new_dept.id, code=new_dept.code, name=new_dept.name,
        name_ar=new_dept.name_ar, manager_id=new_dept.manager_id,
        parent_id=new_dept.parent_id, created_at=new_dept.created_at,
    )


# ─── ATTENDANCE ───────────────────────────────────────────

@router.get("/attendance", response_model=AttendanceRecordListResponse)
async def list_attendance(
    employee_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "hr:read" not in permissions:
        raise HTTPException(status_code=403, detail="Requires hr:read")

    query = select(AttendanceRecord)
    if employee_id:
        query = query.filter(AttendanceRecord.employee_id == employee_id)
    if start_date:
        query = query.filter(AttendanceRecord.date >= start_date)
    if end_date:
        query = query.filter(AttendanceRecord.date <= end_date)
    query = query.order_by(AttendanceRecord.date.desc())

    count_q = select(func.count(AttendanceRecord.id))
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    return AttendanceRecordListResponse(
        records=[
            AttendanceResponse(
                id=r.id, employee_id=r.employee_id, date=r.date,
                check_in=r.check_in, check_out=r.check_out,
                status=r.status, notes=r.notes, created_at=r.created_at,
            )
            for r in records
        ],
        total=total,
    )


@router.post("/attendance", response_model=AttendanceResponse)
async def create_attendance(
    record: AttendanceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    permissions: list[str] = Depends(get_user_permissions),
):
    if "*:*" not in permissions and "hr:create" not in permissions:
        raise HTTPException(status_code=403, detail="Requires hr:create")

    new_record = AttendanceRecord(
        id=str(uuid.uuid4()), employee_id=record.employee_id,
        date=record.date, check_in=record.check_in, check_out=record.check_out,
        status=record.status, notes=record.notes,
    )
    db.add(new_record)
    await db.flush()

    return AttendanceResponse(
        id=new_record.id, employee_id=new_record.employee_id,
        date=new_record.date, check_in=new_record.check_in,
        check_out=new_record.check_out, status=new_record.status,
        notes=new_record.notes, created_at=new_record.created_at,
    )
