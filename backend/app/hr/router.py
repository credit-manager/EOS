from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import commit_db, get_db
from ..tenant import require_tenant
from . import schemas, service

router = APIRouter(prefix="/api/v1/hr", tags=["hr"])


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

@router.post("/departments", status_code=201, response_model=schemas.DepartmentResponse)
def create_department(
    payload: schemas.DepartmentCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    dept = service.create_department(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        manager_id=payload.manager_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return dept


@router.get("/departments", response_model=list[schemas.DepartmentResponse])
def list_departments(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_departments(db, tenant_id=tenant_id)


@router.get("/departments/{department_id}", response_model=schemas.DepartmentResponse)
def get_department(
    department_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_department(db, tenant_id=tenant_id, department_id=department_id)


@router.patch("/departments/{department_id}", response_model=schemas.DepartmentResponse)
def update_department(
    department_id: UUID,
    payload: schemas.DepartmentUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    dept = service.update_department(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        department_id=department_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return dept


@router.delete("/departments/{department_id}", status_code=204)
def delete_department(
    department_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_department(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        department_id=department_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

@router.post("/employees", status_code=201, response_model=schemas.EmployeeResponse)
def create_employee(
    payload: schemas.EmployeeCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    emp = service.create_employee(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        department_id=payload.department_id,
        employee_number=payload.employee_number,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        hire_date=payload.hire_date,
        job_title=payload.job_title,
        salary=payload.salary,
        status=payload.status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return emp


@router.get("/employees", response_model=list[schemas.EmployeeResponse])
def list_employees(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_employees(db, tenant_id=tenant_id)


@router.get("/employees/{employee_id}", response_model=schemas.EmployeeResponse)
def get_employee(
    employee_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_employee(db, tenant_id=tenant_id, employee_id=employee_id)


@router.patch("/employees/{employee_id}", response_model=schemas.EmployeeResponse)
def update_employee(
    employee_id: UUID,
    payload: schemas.EmployeeUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    emp = service.update_employee(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        employee_id=employee_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return emp


@router.delete("/employees/{employee_id}", status_code=204)
def delete_employee(
    employee_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_employee(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        employee_id=employee_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

@router.post("/attendance", status_code=201, response_model=schemas.AttendanceResponse)
def create_attendance(
    payload: schemas.AttendanceCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    att = service.create_attendance(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        employee_id=payload.employee_id,
        date_val=payload.date,
        check_in=payload.check_in,
        check_out=payload.check_out,
        status=payload.status,
        notes=payload.notes,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return att


@router.get("/attendance", response_model=list[schemas.AttendanceResponse])
def list_attendance(
    tenant_id: UUID = Depends(require_tenant),
    employee_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return service.list_attendance(db, tenant_id=tenant_id, employee_id=employee_id)


@router.get("/attendance/{attendance_id}", response_model=schemas.AttendanceResponse)
def get_attendance(
    attendance_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_attendance(db, tenant_id=tenant_id, attendance_id=attendance_id)


@router.patch("/attendance/{attendance_id}", response_model=schemas.AttendanceResponse)
def update_attendance(
    attendance_id: UUID,
    payload: schemas.AttendanceUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    att = service.update_attendance(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        attendance_id=attendance_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return att


# ---------------------------------------------------------------------------
# Leave Requests
# ---------------------------------------------------------------------------

@router.post("/leave-requests", status_code=201, response_model=schemas.LeaveRequestResponse)
def create_leave_request(
    payload: schemas.LeaveRequestCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    lr = service.create_leave_request(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        employee_id=payload.employee_id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        days=payload.days,
        reason=payload.reason,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return lr


@router.get("/leave-requests", response_model=list[schemas.LeaveRequestResponse])
def list_leave_requests(
    tenant_id: UUID = Depends(require_tenant),
    employee_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return service.list_leave_requests(db, tenant_id=tenant_id, employee_id=employee_id)


@router.get("/leave-requests/{leave_request_id}", response_model=schemas.LeaveRequestResponse)
def get_leave_request(
    leave_request_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_leave_request(db, tenant_id=tenant_id, leave_request_id=leave_request_id)


@router.post(
    "/leave-requests/{leave_request_id}/approve",
    response_model=schemas.LeaveRequestResponse,
)
def approve_leave_request(
    leave_request_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    lr = service.approve_leave_request(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        leave_request_id=leave_request_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return lr


@router.post(
    "/leave-requests/{leave_request_id}/reject",
    response_model=schemas.LeaveRequestResponse,
)
def reject_leave_request(
    leave_request_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    lr = service.reject_leave_request(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        leave_request_id=leave_request_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return lr


# ---------------------------------------------------------------------------
# Payroll Runs
# ---------------------------------------------------------------------------

@router.post("/payroll-runs", status_code=201, response_model=schemas.PayrollRunResponse)
def create_payroll_run(
    payload: schemas.PayrollRunCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    pr = service.create_payroll_run(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        status=payload.status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return pr


@router.get("/payroll-runs", response_model=list[schemas.PayrollRunResponse])
def list_payroll_runs(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_payroll_runs(db, tenant_id=tenant_id)


@router.get("/payroll-runs/{payroll_run_id}", response_model=schemas.PayrollRunResponse)
def get_payroll_run(
    payroll_run_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_payroll_run(db, tenant_id=tenant_id, payroll_run_id=payroll_run_id)


@router.patch("/payroll-runs/{payroll_run_id}", response_model=schemas.PayrollRunResponse)
def update_payroll_run(
    payroll_run_id: UUID,
    payload: schemas.PayrollRunUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    pr = service.update_payroll_run(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        payroll_run_id=payroll_run_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return pr


# ---------------------------------------------------------------------------
# Payroll Lines
# ---------------------------------------------------------------------------

@router.post("/payroll-lines", status_code=201, response_model=schemas.PayrollLineResponse)
def create_payroll_line(
    payload: schemas.PayrollLineCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    pl = service.create_payroll_line(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        payroll_run_id=payload.payroll_run_id,
        employee_id=payload.employee_id,
        base_salary=payload.base_salary,
        deductions=payload.deductions,
        net_pay=payload.net_pay,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return pl


@router.get("/payroll-lines", response_model=list[schemas.PayrollLineResponse])
def list_payroll_lines(
    tenant_id: UUID = Depends(require_tenant),
    payroll_run_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    if payroll_run_id is None:
        return []
    return service.list_payroll_lines(db, tenant_id=tenant_id, payroll_run_id=payroll_run_id)
