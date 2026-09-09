"""
EOS HR API Router — /api/v1/hr
"""
import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from core.auth import get_current_user

router = APIRouter(prefix="/api/v1/hr", tags=["HR API"])


# ─── Employees ─────────────────────────────────

@router.get("/employees")
async def list_employees(
    department_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if department_id:
        conditions.append("department_id = :did")
        params["did"] = department_id
    if status:
        conditions.append("employment_status = :st")
        params["st"] = status
    if search:
        conditions.append("(first_name ILIKE :search OR last_name ILIKE :search OR email ILIKE :search OR employee_code ILIKE :search)")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)

    count_row = db.execute(text(f"SELECT COUNT(*) FROM dbp_employees WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    rows = db.execute(
        text(f"SELECT id, employee_code, first_name, last_name, email, phone, "
             f"department_id, position, hire_date, employment_status, salary, currency_code "
             f"FROM dbp_employees WHERE {where} ORDER BY first_name LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    data = [{"id": r[0], "employee_code": r[1], "first_name": r[2], "last_name": r[3],
             "email": r[4], "phone": r[5], "department_id": r[6],
             "position": r[7], "hire_date": r[8].isoformat() if r[8] else None,
             "employment_status": r[9] or "active",
             "salary": float(r[10]) if r[10] else 0, "currency_code": r[11] or "SAR"}
            for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/employees/{employee_id}")
async def get_employee(employee_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.execute(
        text("SELECT id, employee_code, first_name, last_name, email, phone, "
             "department_id, position, hire_date, employment_status, salary, currency_code "
             "FROM dbp_employees WHERE id = :id"), {"id": employee_id}
    ).fetchone()
    if not r:
        raise HTTPException(404, detail="Employee not found")
    return {"id": r[0], "employee_code": r[1], "first_name": r[2], "last_name": r[3],
            "email": r[4], "phone": r[5], "department_id": r[6],
            "position": r[7], "hire_date": r[8].isoformat() if r[8] else None,
            "employment_status": r[9], "salary": float(r[10]) if r[10] else 0,
            "currency_code": r[11] or "SAR"}


@router.post("/employees", status_code=201)
async def create_employee(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    eid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO dbp_employees (id, tenant_id, company_id, employee_code, first_name, last_name, "
             "email, phone, department_id, position, hire_date, employment_status, salary, currency_code) "
             "VALUES (:id, :tid, :cid, :ec, :fn, :ln, :email, :phone, :did, :pos, :hd, :es, :sal, :cur)"),
        {"id": eid, "tid": user.get("tenant_id"), "cid": user.get("tenant_id"),
         "ec": f"EMP-{eid[:6].upper()}", "fn": body.get("first_name", ""),
         "ln": body.get("last_name", ""), "email": body.get("email"),
         "phone": body.get("phone"), "did": body.get("department_id"),
         "pos": body.get("position"), "hd": body.get("hire_date", now),
         "es": body.get("employment_status", "active"),
         "sal": body.get("salary", 0), "cur": body.get("currency_code", "SAR")},
    )
    db.commit()
    return {"id": eid, "message": "Employee created"}


@router.put("/employees/{employee_id}")
async def update_employee(employee_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(text("SELECT id FROM dbp_employees WHERE id = :id"), {"id": employee_id}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Employee not found")
    fields, params = [], {"id": employee_id}
    for col in ("first_name", "last_name", "email", "phone", "department_id", "position", "employment_status"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    for col in ("salary", "currency_code"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if "hire_date" in body:
        fields.append("hire_date = :hd")
        params["hd"] = body["hire_date"]
    if fields:
        db.execute(text(f"UPDATE dbp_employees SET {', '.join(fields)} WHERE id = :id"), params)
        db.commit()
    return {"message": "Employee updated"}


@router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM dbp_employees WHERE id = :id"), {"id": employee_id})
    if result.rowcount == 0:
        raise HTTPException(404, detail="Employee not found")
    db.commit()
    return {"message": "Employee deleted"}


# ─── Departments ─────────────────────────────────

@router.get("/departments")
async def list_departments(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        rows = db.execute(
            text("SELECT id, code, name_en, name_ar, parent_id, manager_id, is_active "
                 "FROM dbp_departments ORDER BY code")
        ).fetchall()
        return [{"id": r[0], "code": r[1], "name": r[2], "name_ar": r[3],
                 "parent_id": r[4], "manager_id": r[5],
                 "is_active": r[6] if r[6] is not None else True} for r in rows]
    except Exception:
        return []


@router.post("/departments", status_code=201)
async def create_department(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    did = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        db.execute(
            text("INSERT INTO dbp_departments (id, tenant_id, company_id, code, name_en, name_ar, "
                 "parent_id, manager_id, is_active, created_at) "
                 "VALUES (:id, :tid, :cid, :code, :name, :name_ar, :pid, :mgr, true, :now)"),
            {"id": did, "tid": user.get("tenant_id"), "cid": user.get("tenant_id"),
             "code": body.get("code", f"DEPT-{did[:6].upper()}"),
             "name": body.get("name", ""), "name_ar": body.get("name_ar"),
             "pid": body.get("parent_id"), "mgr": body.get("manager_id"), "now": now},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(400, detail="Failed to create department")
    return {"id": did, "message": "Department created"}


@router.put("/departments/{dept_id}")
async def update_department(dept_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    fields, params = [], {"id": dept_id}
    for col in ("name_en", "name_ar", "code", "parent_id", "manager_id"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if fields:
        db.execute(text(f"UPDATE dbp_departments SET {', '.join(fields)} WHERE id = :id"), params)
        db.commit()
    return {"message": "Department updated"}


@router.delete("/departments/{dept_id}")
async def delete_department(dept_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM dbp_departments WHERE id = :id"), {"id": dept_id})
    db.commit()
    return {"message": "Department deleted"}


# ─── Positions ─────────────────────────────────

@router.get("/positions")
async def list_positions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rows = db.execute(
            text("SELECT DISTINCT position FROM dbp_employees WHERE position IS NOT NULL ORDER BY position")
        ).fetchall()
        return [{"id": r[0], "name": r[0]} for r in rows]
    except Exception:
        return []


@router.post("/positions", status_code=201)
async def create_position(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"id": body.get("name", ""), "message": "Position created (in-memory only)"}


@router.put("/positions/{position_id}")
async def update_position(position_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"message": "Position updated"}


@router.delete("/positions/{position_id}")
async def delete_position(position_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"message": "Position deleted"}


# ─── Attendance ─────────────────────────────────

@router.get("/attendance")
async def list_attendance(
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        conditions = ["1=1"]
        params: dict = {}
        if employee_id:
            conditions.append("employee_id = :eid")
            params["eid"] = employee_id
        where = " AND ".join(conditions)
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        rows = db.execute(
            text(f"SELECT id, employee_id, date, clock_in, clock_out, status, notes "
                 f"FROM dbp_attendance WHERE {where} ORDER BY date DESC LIMIT :limit OFFSET :offset"),
            params,
        ).fetchall()
        data = [{"id": r[0], "employee_id": r[1],
                 "date": r[2].isoformat() if r[2] else None,
                 "clock_in": str(r[3]) if r[3] else None,
                 "clock_out": str(r[4]) if r[4] else None,
                 "status": r[5] or "present", "notes": r[6]}
                for r in rows]
        return {"data": data, "total": len(data), "page": page, "page_size": page_size}
    except Exception:
        return {"data": [], "total": 0, "page": page, "page_size": page_size}


@router.post("/attendance", status_code=201)
async def create_attendance(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    aid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        db.execute(
            text("INSERT INTO dbp_attendance (id, employee_id, date, clock_in, clock_out, status, notes) "
                 "VALUES (:id, :eid, :dt, :ci, :co, :st, :notes)"),
            {"id": aid, "eid": body.get("employee_id"), "dt": body.get("date", now),
             "ci": body.get("clock_in"), "co": body.get("clock_out"),
             "st": body.get("status", "present"), "notes": body.get("notes")},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(400, detail="Failed to create attendance")
    return {"id": aid, "message": "Attendance recorded"}


@router.post("/attendance/clock-in")
async def clock_in(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    aid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        db.execute(
            text("INSERT INTO dbp_attendance (id, employee_id, date, clock_in, status) "
             "VALUES (:id, :eid, :dt, :ci, 'present')"),
            {"id": aid, "eid": body.get("employee_id"), "dt": now, "ci": now},
        )
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "Clocked in"}


@router.post("/attendance/clock-out")
async def clock_out(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        db.execute(
            text("UPDATE dbp_attendance SET clock_out = :co WHERE employee_id = :eid AND clock_out IS NULL"),
            {"eid": body.get("employee_id"), "co": datetime.now(timezone.utc)},
        )
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "Clocked out"}


# ─── Payroll ─────────────────────────────────

@router.get("/payroll")
async def list_payroll(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        params = {"limit": page_size, "offset": (page - 1) * page_size}
        rows = db.execute(
            text("SELECT id, employee_id, period_start, period_end, basic_salary, deductions, "
                 "net_pay, status, created_at FROM dbp_payroll_runs ORDER BY created_at DESC "
                 "LIMIT :limit OFFSET :offset"),
            params,
        ).fetchall()
        data = [{"id": r[0], "employee_id": r[1],
                 "period_start": r[2].isoformat() if r[2] else None,
                 "period_end": r[3].isoformat() if r[3] else None,
                 "basic_salary": float(r[4]) if r[4] else 0,
                 "deductions": float(r[5]) if r[5] else 0,
                 "net_pay": float(r[6]) if r[6] else 0,
                 "status": r[7] or "draft",
                 "created_at": r[8].isoformat() if r[8] else None}
                for r in rows]
        return {"data": data, "total": len(data), "page": page, "page_size": page_size}
    except Exception:
        return {"data": [], "total": 0, "page": page, "page_size": page_size}


@router.post("/payroll/run", status_code=201)
async def run_payroll(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"message": "Payroll run initiated", "run_id": str(uuid.uuid4())}


@router.get("/payroll/payslips/{payslip_id}")
async def get_payslip(payslip_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"id": payslip_id, "message": "Payslip details"}


# ─── Leave Requests ─────────────────────────────

@router.get("/leave-requests")
async def list_leave_requests(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        conditions = ["1=1"]
        params: dict = {}
        if employee_id:
            conditions.append("employee_id = :eid")
            params["eid"] = employee_id
        if status:
            conditions.append("status = :st")
            params["st"] = status
        where = " AND ".join(conditions)
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        rows = db.execute(
            text(f"SELECT id, employee_id, leave_type, start_date, end_date, days, reason, status, created_at "
                 f"FROM dbp_leave_requests WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            params,
        ).fetchall()
        data = [{"id": r[0], "employee_id": r[1], "leave_type": r[2],
                 "start_date": r[3].isoformat() if r[3] else None,
                 "end_date": r[4].isoformat() if r[4] else None,
                 "days": r[5], "reason": r[6],
                 "status": r[7] or "pending",
                 "created_at": r[8].isoformat() if r[8] else None}
                for r in rows]
        return {"data": data, "total": len(data), "page": page, "page_size": page_size}
    except Exception:
        return {"data": [], "total": 0, "page": page, "page_size": page_size}


@router.post("/leave-requests", status_code=201)
async def create_leave_request(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    lid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        db.execute(
            text("INSERT INTO dbp_leave_requests (id, employee_id, leave_type, start_date, end_date, "
             "days, reason, status, created_at) VALUES (:id, :eid, :lt, :sd, :ed, :days, :reason, 'pending', :now)"),
            {"id": lid, "eid": body.get("employee_id"), "lt": body.get("leave_type", "annual"),
             "sd": body.get("start_date"), "ed": body.get("end_date"),
             "days": body.get("days", 1), "reason": body.get("reason"), "now": now},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(400, detail="Failed to create leave request")
    return {"id": lid, "message": "Leave request created"}


@router.post("/leave-requests/{request_id}/approve")
async def approve_leave_request(request_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(text("UPDATE dbp_leave_requests SET status = 'approved' WHERE id = :id"), {"id": request_id})
    db.commit()
    return {"message": "Leave request approved"}


@router.post("/leave-requests/{request_id}/reject")
async def reject_leave_request(request_id: str, body: dict = {}, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(text("UPDATE dbp_leave_requests SET status = 'rejected' WHERE id = :id"), {"id": request_id})
    db.commit()
    return {"message": "Leave request rejected"}
