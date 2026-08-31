"""
P28 Project Management Router
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from core.auth import require_permission, get_current_user
from core.rate_limit import read_limiter, write_limiter
from core.project_engine import ProjectEngine

router = APIRouter(prefix="/api/v1/dynamic", tags=["Project Management"])


def _ensure_project(db: Session, pid: str, user: dict) -> dict:
    proj = ProjectEngine(db).get_project(pid)
    if not proj or proj["tenant_id"] != user.get("tenant_id"):
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Project not found"}})
    return proj


# ── PROJECTS ──

@router.get("/companies/{cid}/projects", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_projects(cid: str, status: Optional[str] = None,
                        user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"status": "success", "data": ProjectEngine(db).list_projects(cid, tenant_id=user.get("tenant_id"), status=status)}


@router.post("/companies/{cid}/projects", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_project(cid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("name", "start_date", "end_date"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    try:
        pid = ProjectEngine(db).create_project(user.get("tenant_id"), cid, body["name"],
                                               body["start_date"], body["end_date"],
                                               description=body.get("description"),
                                               budget=body.get("budget", 0),
                                               manager_id=body.get("manager_id"))
    except Exception as e:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "CREATE_FAILED", "message": str(e)}})
    db.commit()
    return {"status": "success", "data": {"id": pid}}


@router.get("/projects/{pid}", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def get_project(pid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    proj = _ensure_project(db, pid, user)
    return {"status": "success", "data": proj}


@router.put("/projects/{pid}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_project(pid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_project(db, pid, user)
    if not body:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "At least one field required"}})
    result = ProjectEngine(db).update_project(pid, **body)
    if not result["success"]:
        if result["error"] == "Project not found":
            raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Project not found"}})
        raise HTTPException(400, detail={"status": "error", "error": {"code": "UPDATE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


# ── TASKS ──

@router.get("/projects/{pid}/tasks", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_tasks(pid: str, status: Optional[str] = None, assigned_to: Optional[str] = None,
                     user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_project(db, pid, user)
    return {"status": "success", "data": ProjectEngine(db).list_tasks(pid, status=status, assigned_to=assigned_to)}


@router.post("/projects/{pid}/tasks", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_task(pid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if "name" not in body:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "name required"}})
    try:
        tid = ProjectEngine(db).create_task(user.get("tenant_id"), pid, body["name"],
                                            description=body.get("description"),
                                            assigned_to=body.get("assigned_to"),
                                            priority=body.get("priority"),
                                            start_date=body.get("start_date"),
                                            due_date=body.get("due_date"),
                                            estimated_hours=body.get("estimated_hours"),
                                            parent_task_id=body.get("parent_task_id"))
    except ValueError as e:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": str(e)}})
    db.commit()
    return {"status": "success", "data": {"id": tid}}


@router.put("/tasks/{tid}", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def update_task(tid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "At least one field required"}})
    result = ProjectEngine(db).update_task(tid, tenant_guard=user.get("tenant_id"), **body)
    if not result["success"]:
        if result["error"] == "Task not found":
            raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Task not found"}})
        raise HTTPException(400, detail={"status": "error", "error": {"code": "UPDATE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


@router.post("/projects/{pid}/tasks/reorder", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def reorder_tasks(pid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_project(db, pid, user)
    task_ids = body.get("task_ids")
    if not isinstance(task_ids, list):
        raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": "task_ids (list) required"}})
    result = ProjectEngine(db).reorder_tasks(pid, task_ids)
    if not result["success"]:
        raise HTTPException(400, detail={"status": "error", "error": {"code": "REORDER_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


# ── MILESTONES ──

@router.get("/projects/{pid}/milestones", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_milestones(pid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_project(db, pid, user)
    return {"status": "success", "data": ProjectEngine(db).list_milestones(pid)}


@router.post("/projects/{pid}/milestones", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def create_milestone(pid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("name", "due_date"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    try:
        mid = ProjectEngine(db).create_milestone(user.get("tenant_id"), pid,
                                                 body["name"], body["due_date"])
    except ValueError as e:
        raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": str(e)}})
    db.commit()
    return {"status": "success", "data": {"id": mid}}


@router.post("/milestones/{mid}/complete", dependencies=[Depends(require_permission("dynamic", "update")), Depends(write_limiter.check)])
async def complete_milestone(mid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = ProjectEngine(db).complete_milestone(mid, tenant_guard=user.get("tenant_id"))
    if not result["success"]:
        if result["error"] == "Milestone not found":
            raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": "Milestone not found"}})
        raise HTTPException(400, detail={"status": "error", "error": {"code": "COMPLETE_FAILED", "message": result["error"]}})
    db.commit()
    return {"status": "success", "data": result}


# ── TIME ENTRIES ──

@router.get("/projects/{pid}/time-entries", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def list_time_entries(pid: str, task_id: Optional[str] = None, employee_id: Optional[str] = None,
                            user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_project(db, pid, user)
    return {"status": "success", "data": ProjectEngine(db).get_time_entries(pid, task_id=task_id, employee_id=employee_id)}


@router.post("/projects/{pid}/time-entries", dependencies=[Depends(require_permission("dynamic", "create")), Depends(write_limiter.check)])
async def log_time(pid: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    for f in ("task_id", "employee_id", "work_date", "hours"):
        if f not in body:
            raise HTTPException(400, detail={"status": "error", "error": {"code": "MISSING", "message": f"{f} required"}})
    try:
        teid = ProjectEngine(db).log_time(user.get("tenant_id"), pid, body["task_id"],
                                          body["employee_id"], body["work_date"],
                                          body["hours"], notes=body.get("notes"))
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(404, detail={"status": "error", "error": {"code": "NOT_FOUND", "message": msg}})
        raise HTTPException(400, detail={"status": "error", "error": {"code": "INVALID", "message": msg}})
    db.commit()
    return {"status": "success", "data": {"id": teid}}


@router.get("/projects/{pid}/time-summary", dependencies=[Depends(require_permission("dynamic", "read")), Depends(read_limiter.check)])
async def time_summary(pid: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_project(db, pid, user)
    return {"status": "success", "data": ProjectEngine(db).get_project_time_summary(pid)}
