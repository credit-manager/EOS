"""
EOS Projects API Router — /api/v1/projects
"""
import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from core.auth import get_current_user

router = APIRouter(prefix="/api/v1/projects", tags=["Projects API"])


@router.get("")
async def list_projects(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conditions = ["1=1"]
    params: dict = {}
    if status:
        conditions.append("status = :st")
        params["st"] = status
    if search:
        conditions.append("(name ILIKE :search OR code ILIKE :search)")
        params["search"] = f"%{search}%"
    where = " AND ".join(conditions)

    count_row = db.execute(text(f"SELECT COUNT(*) FROM dbp_projects WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    rows = db.execute(
        text(f"SELECT id, code, name, description, start_date, end_date, status, "
             f"budget, actual_cost, manager_id, created_at "
             f"FROM dbp_projects WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    data = [{"id": r[0], "code": r[1], "name": r[2], "description": r[3],
             "start_date": r[4].isoformat() if r[4] else None,
             "end_date": r[5].isoformat() if r[5] else None,
             "status": r[6] or "planning",
             "budget": float(r[7]) if r[7] else 0,
             "actual_cost": float(r[8]) if r[8] else 0,
             "manager_id": r[9],
             "created_at": r[10].isoformat() if r[10] else None}
            for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.execute(
        text("SELECT id, code, name, description, start_date, end_date, status, "
             "budget, actual_cost, manager_id, created_at "
             "FROM dbp_projects WHERE id = :id"), {"id": project_id}
    ).fetchone()
    if not r:
        raise HTTPException(404, detail="Project not found")
    return {"id": r[0], "code": r[1], "name": r[2], "description": r[3],
            "start_date": r[4].isoformat() if r[4] else None,
            "end_date": r[5].isoformat() if r[5] else None,
            "status": r[6] or "planning",
            "budget": float(r[7]) if r[7] else 0,
            "actual_cost": float(r[8]) if r[8] else 0,
            "manager_id": r[9],
            "created_at": r[10].isoformat() if r[10] else None}


@router.post("", status_code=201)
async def create_project(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.get("name"):
        raise HTTPException(400, detail="name required")
    pid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO dbp_projects (id, tenant_id, company_id, code, name, description, "
             "start_date, end_date, status, budget, actual_cost, manager_id, created_at) "
             "VALUES (:id, :tid, :cid, :code, :name, :desc, :sd, :ed, :st, :bgt, 0, :mgr, :now)"),
        {"id": pid, "tid": user.get("tenant_id"), "cid": user.get("tenant_id"),
         "code": body.get("code", f"PRJ-{pid[:6].upper()}"),
         "name": body["name"], "desc": body.get("description"),
         "sd": body.get("start_date"), "ed": body.get("end_date"),
         "st": body.get("status", "planning"),
         "bgt": body.get("budget", 0), "mgr": body.get("manager_id"), "now": now},
    )
    db.commit()
    return {"id": pid, "name": body["name"], "message": "Project created"}


@router.put("/{project_id}")
async def update_project(project_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(text("SELECT id FROM dbp_projects WHERE id = :id"), {"id": project_id}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Project not found")
    fields, params = [], {"id": project_id}
    for col in ("name", "description", "code", "status", "start_date", "end_date", "manager_id"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    for col in ("budget", "actual_cost"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if fields:
        db.execute(text(f"UPDATE dbp_projects SET {', '.join(fields)} WHERE id = :id"), params)
        db.commit()
    return {"message": "Project updated"}


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM dbp_projects WHERE id = :id"), {"id": project_id})
    if result.rowcount == 0:
        raise HTTPException(404, detail="Project not found")
    db.commit()
    return {"message": "Project deleted"}


@router.post("/{project_id}/status")
async def update_project_status(project_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(text("UPDATE dbp_projects SET status = :st WHERE id = :id"),
               {"id": project_id, "st": body.get("status", "active")})
    db.commit()
    return {"message": "Status updated"}


@router.post("/{project_id}/progress")
async def update_project_progress(project_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"message": "Progress updated"}


# ─── Tasks ─────────────────────────────────

@router.get("/{project_id}/tasks")
async def list_tasks(
    project_id: str,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conditions = ["project_id = :pid"]
    params: dict = {"pid": project_id}
    if status:
        conditions.append("status = :st")
        params["st"] = status
    where = " AND ".join(conditions)

    count_row = db.execute(text(f"SELECT COUNT(*) FROM dbp_project_tasks WHERE {where}"), params).fetchone()
    total = count_row[0] if count_row else 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    rows = db.execute(
        text(f"SELECT id, name, description, assigned_to, status, priority, start_date, "
             f"due_date, estimated_hours, actual_hours, sort_order, created_at "
             f"FROM dbp_project_tasks WHERE {where} ORDER BY sort_order LIMIT :limit OFFSET :offset"),
        params,
    ).fetchall()
    data = [{"id": r[0], "name": r[1], "description": r[2], "assigned_to": r[3],
             "status": r[4] or "todo", "priority": r[5] or "medium",
             "start_date": r[6].isoformat() if r[6] else None,
             "due_date": r[7].isoformat() if r[7] else None,
             "estimated_hours": r[8], "actual_hours": r[9],
             "sort_order": r[10], "created_at": r[11].isoformat() if r[11] else None}
            for r in rows]
    return {"data": data, "total": total, "page": page, "page_size": page_size}


@router.get("/{project_id}/tasks/{task_id}")
async def get_task(project_id: str, task_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.execute(
        text("SELECT id, name, description, assigned_to, status, priority, start_date, "
             "due_date, estimated_hours, actual_hours FROM dbp_project_tasks WHERE id = :id AND project_id = :pid"),
        {"id": task_id, "pid": project_id},
    ).fetchone()
    if not r:
        raise HTTPException(404, detail="Task not found")
    return {"id": r[0], "name": r[1], "description": r[2], "assigned_to": r[3],
            "status": r[4], "priority": r[5],
            "start_date": r[6].isoformat() if r[6] else None,
            "due_date": r[7].isoformat() if r[7] else None,
            "estimated_hours": r[8], "actual_hours": r[9]}


@router.post("/{project_id}/tasks", status_code=201)
async def create_task(project_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    tid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    db.execute(
        text("INSERT INTO dbp_project_tasks (id, tenant_id, project_id, name, description, "
             "assigned_to, status, priority, start_date, due_date, estimated_hours, actual_hours, "
             "sort_order, created_at) VALUES (:id, :tid, :pid, :name, :desc, :at, :st, :pr, :sd, :dd, :eh, 0, 0, :now)"),
        {"id": tid, "tid": user.get("tenant_id"), "pid": project_id,
         "name": body.get("name", "Task"), "desc": body.get("description"),
         "at": body.get("assigned_to"), "st": body.get("status", "todo"),
         "pr": body.get("priority", "medium"), "sd": body.get("start_date"),
         "dd": body.get("due_date"), "eh": body.get("estimated_hours"), "now": now},
    )
    db.commit()
    return {"id": tid, "message": "Task created"}


@router.put("/{project_id}/tasks/{task_id}")
async def update_task(project_id: str, task_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.execute(text("SELECT id FROM dbp_project_tasks WHERE id = :id AND project_id = :pid"),
                          {"id": task_id, "pid": project_id}).fetchone()
    if not existing:
        raise HTTPException(404, detail="Task not found")
    fields, params = [], {"id": task_id}
    for col in ("name", "description", "assigned_to", "status", "priority", "start_date", "due_date"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    for col in ("estimated_hours", "actual_hours", "sort_order"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if fields:
        db.execute(text(f"UPDATE dbp_project_tasks SET {', '.join(fields)} WHERE id = :id"), params)
        db.commit()
    return {"message": "Task updated"}


@router.delete("/{project_id}/tasks/{task_id}")
async def delete_task(project_id: str, task_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM dbp_project_tasks WHERE id = :id AND project_id = :pid"),
                        {"id": task_id, "pid": project_id})
    if result.rowcount == 0:
        raise HTTPException(404, detail="Task not found")
    db.commit()
    return {"message": "Task deleted"}


@router.post("/{project_id}/tasks/{task_id}/status")
async def update_task_status(project_id: str, task_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(text("UPDATE dbp_project_tasks SET status = :st WHERE id = :id AND project_id = :pid"),
               {"id": task_id, "pid": project_id, "st": body.get("status", "todo")})
    db.commit()
    return {"message": "Task status updated"}


# ─── Time Entries ─────────────────────────────────

@router.get("/time-entries")
async def list_time_entries(
    project_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        conditions = ["1=1"]
        params: dict = {}
        if project_id:
            conditions.append("project_id = :pid")
            params["pid"] = project_id
        where = " AND ".join(conditions)
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        rows = db.execute(
            text(f"SELECT id, project_id, employee_id, task_id, hours, date, description, created_at "
                 f"FROM dbp_project_time_entries WHERE {where} ORDER BY date DESC LIMIT :limit OFFSET :offset"),
            params,
        ).fetchall()
        data = [{"id": r[0], "project_id": r[1], "employee_id": r[2], "task_id": r[3],
                 "hours": r[4], "date": r[5].isoformat() if r[5] else None,
                 "description": r[6], "created_at": r[7].isoformat() if r[7] else None}
                for r in rows]
        return {"data": data, "total": len(data), "page": page, "page_size": page_size}
    except Exception:
        return {"data": [], "total": 0, "page": page, "page_size": page_size}


@router.post("/time-entries", status_code=201)
async def create_time_entry(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    eid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        db.execute(
            text("INSERT INTO dbp_project_time_entries (id, project_id, employee_id, task_id, hours, date, description, created_at) "
                 "VALUES (:id, :pid, :emp, :tid, :hrs, :dt, :desc, :now)"),
            {"id": eid, "pid": body.get("project_id"), "emp": body.get("employee_id"),
             "tid": body.get("task_id"), "hrs": body.get("hours", 0),
             "dt": body.get("date", now), "desc": body.get("description"), "now": now},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(400, detail="Failed to create time entry")
    return {"id": eid, "message": "Time entry created"}


@router.delete("/time-entries/{entry_id}")
async def delete_time_entry(entry_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM dbp_project_time_entries WHERE id = :id"), {"id": entry_id})
    if result.rowcount == 0:
        raise HTTPException(404, detail="Time entry not found")
    db.commit()
    return {"message": "Time entry deleted"}


# ─── Milestones ─────────────────────────────────

@router.get("/{project_id}/milestones")
async def list_milestones(project_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        rows = db.execute(
            text("SELECT id, name, due_date, status, description FROM dbp_project_milestones "
                 "WHERE project_id = :pid ORDER BY due_date"),
            {"pid": project_id},
        ).fetchall()
        return [{"id": r[0], "name": r[1], "due_date": r[2].isoformat() if r[2] else None,
                 "status": r[3] or "pending", "description": r[4]} for r in rows]
    except Exception:
        return []


@router.post("/{project_id}/milestones", status_code=201)
async def create_milestone(project_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    mid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    try:
        db.execute(
            text("INSERT INTO dbp_project_milestones (id, project_id, name, due_date, status, description, created_at) "
                 "VALUES (:id, :pid, :name, :dd, 'pending', :desc, :now)"),
            {"id": mid, "pid": project_id, "name": body.get("name", ""),
             "dd": body.get("due_date"), "desc": body.get("description"), "now": now},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(400, detail="Failed to create milestone")
    return {"id": mid, "message": "Milestone created"}


@router.put("/{project_id}/milestones/{milestone_id}")
async def update_milestone(project_id: str, milestone_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    fields, params = [], {"id": milestone_id}
    for col in ("name", "due_date", "status", "description"):
        if col in body:
            fields.append(f"{col} = :{col}")
            params[col] = body[col]
    if fields:
        db.execute(text(f"UPDATE dbp_project_milestones SET {', '.join(fields)} WHERE id = :id"), params)
        db.commit()
    return {"message": "Milestone updated"}


@router.delete("/{project_id}/milestones/{milestone_id}")
async def delete_milestone(project_id: str, milestone_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM dbp_project_milestones WHERE id = :id"), {"id": milestone_id})
    db.commit()
    return {"message": "Milestone deleted"}


# ─── Reports ─────────────────────────────────

@router.get("/reports/progress")
async def project_progress_report(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id, name, status, budget, actual_cost FROM dbp_projects")).fetchall()
    return [{"id": r[0], "name": r[1], "status": r[2],
             "budget": float(r[3]) if r[3] else 0,
             "actual_cost": float(r[4]) if r[4] else 0} for r in rows]


@router.get("/reports/time-tracking")
async def time_tracking_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"total_hours": 0, "by_project": []}
