"""
P27 Human Resources Router
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.hr_engine import HREngine

router = APIRouter(prefix="/api/v1/dynamic", tags=["Human Resources"])


@router.get("/companies/{cid}/employees", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_employees(cid: str, department_id: Optional[str] = None,
                         user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": HREngine(db).list_employees(cid, tenant_id=user.get("tenant_id"),
                                                                      department_id=department_id)}


@router.post("/companies/{cid}/employees", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_employee(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("first_name", "last_name", "hire_date"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    try:
        eid = HREngine(db).create_employee(user.get("tenant_id"), cid, body["first_name"],
                                            body["last_name"], body["hire_date"],
                                            email=body.get("email"), phone=body.get("phone"),
                                            department_id=body.get("department_id"),
                                            position=body.get("position"),
                                            salary=body.get("salary", 0),
                                            manager_id=body.get("manager_id"),
                                            cost_center_id=body.get("cost_center_id"))
    except Exception as e:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "CREATE_FAILED", "message": str(e)}})
    db.commit()
    return {"status": "success", "data": {"id": eid}}


@router.put("/employees/{eid}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_employee(eid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "At least one field required"}})
    result = HREngine(db).update_employee(eid, tenant_id=user.get("tenant_id"), **body)
    if not result["success"]:
        if result["error"] == "Employee not found":
            raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Employee not found"}})
        raise HTTPException(400, detail={"status": "error", "error": {"code": "UPDATE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.get("/companies/{cid}/leave-requests", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_leave_requests(cid: str, status: Optional[str] = None, employee_id: Optional[str] = None,
                              user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": HREngine(db).list_leave_requests(cid, tenant_id=user.get("tenant_id"),
                                                                           status=status, employee_id=employee_id)}


@router.post("/companies/{cid}/leave-requests", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_leave_request(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("employee_id", "leave_type", "start_date", "end_date", "days"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    lid = HREngine(db).create_leave_request(user.get("tenant_id"), body["employee_id"], body["leave_type"],
                                             body["start_date"], body["end_date"], body["days"],
                                             reason=body.get("reason"))
    db.commit()
    return {"status": "success", "data": {"id": lid}}


@router.post("/leave-requests/{rid}/approve", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def approve_leave_request(rid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = HREngine(db).approve_leave_request(rid, user.get("id") or "admin", user.get("tenant_id"))
    if not result["success"]:
        if result["error"] == "Leave request not found":
            raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Leave request not found"}})
        raise HTTPException(400, detail={"status": "error", "error": {"code": "APPROVE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/companies/{cid}/attendance", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def record_attendance(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("employee_id", "work_date"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    aid = HREngine(db).record_attendance(user.get("tenant_id"), body["employee_id"], body["work_date"],
                                          clock_in=body.get("clock_in"), clock_out=body.get("clock_out"),
                                          hours_worked=body.get("hours_worked", 0),
                                          overtime_hours=body.get("overtime_hours", 0))
    db.commit()
    return {"status": "success", "data": {"id": aid}}


@router.get("/companies/{cid}/attendance", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_attendance(cid: str, employee_id: Optional[str] = None, start_date: Optional[str] = None,
                         end_date: Optional[str] = None, user: dict = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    return {"status": "success", "data": HREngine(db).get_attendance(cid, tenant_id=user.get("tenant_id"),
                                                                      employee_id=employee_id,
                                                                      start_date=start_date, end_date=end_date)}


@router.get("/companies/{cid}/payroll-runs", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_payroll_runs(cid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": HREngine(db).list_payroll_runs(cid, tenant_id=user.get("tenant_id"))}


@router.post("/companies/{cid}/payroll-runs", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_payroll_run(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("pay_period_start", "pay_period_end"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    rid = HREngine(db).create_payroll_run(user.get("tenant_id"), cid,
                                           body["pay_period_start"], body["pay_period_end"])
    db.commit()
    return {"status": "success", "data": {"id": rid}}


@router.get("/payroll-runs/{rid}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_payroll_run(rid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    run = HREngine(db).get_payroll_run(rid, user.get("tenant_id"))
    if not run:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Payroll run not found"}})
    return {"status": "success", "data": run}


@router.post("/payroll-runs/{rid}/lines", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def add_payroll_line(rid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("employee_id", "basic_salary"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    try:
        lid = HREngine(db).add_payroll_line(user.get("tenant_id"), rid, body["employee_id"],
                                             body["basic_salary"], allowances=body.get("allowances", 0),
                                             bonus=body.get("bonus", 0), deductions=body.get("deductions", 0),
                                             tax=body.get("tax", 0))
    except ValueError as e:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": str(e)}})
    db.commit()
    return {"status": "success", "data": {"id": lid}}
