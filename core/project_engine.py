"""
P28 Project Management Engine
"""
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class ProjectEngine:
    """Projects, Tasks, Milestones, Time Entries."""

    PROJECT_FIELDS = ("name", "description", "start_date", "end_date", "status",
                      "budget", "actual_cost", "manager_id")
    TASK_FIELDS = ("name", "description", "assigned_to", "status", "priority",
                   "start_date", "due_date", "estimated_hours", "actual_hours",
                   "sort_order")

    def __init__(self, db: Session):
        self.db = db

    # ── PROJECTS ──

    def create_project(self, tenant_id: str, company_id: str, name: str,
                       start_date, end_date, **kw) -> str:
        pid = str(uuid.uuid4())
        code = self._next_code(company_id)
        self.db.execute(text(
            "INSERT INTO dbp_projects (id, tenant_id, company_id, code, name, "
            "description, start_date, end_date, status, budget, manager_id) "
            "VALUES (:id, :tid, :cid, :code, :name, :desc, :sd, :ed, :st, :bud, :mgr)"
        ), {"id": pid, "tid": tenant_id, "cid": company_id, "code": code,
            "name": name, "desc": kw.get("description"), "sd": start_date,
            "ed": end_date, "st": kw.get("status", "planning"),
            "bud": kw.get("budget", 0), "mgr": kw.get("manager_id")})
        self.db.flush()
        return pid

    def list_projects(self, company_id: str, tenant_id: str | None = None,
                      status: str | None = None) -> list[dict[str, Any]]:
        conditions = ["company_id = :cid"]
        params: dict[str, Any] = {"cid": company_id}
        if tenant_id:
            conditions.append("tenant_id = :tid")
            params["tid"] = tenant_id
        if status:
            conditions.append("status = :st")
            params["st"] = status
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, code, name, status, start_date, end_date, "
            f"budget, actual_cost, manager_id, created_at FROM dbp_projects "
            f"WHERE {where} ORDER BY created_at"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "code": r[2], "name": r[3],
                 "status": r[4],
                 "start_date": r[5].isoformat() if r[5] else None,
                 "end_date": r[6].isoformat() if r[6] else None,
                 "budget": float(r[7]) if r[7] is not None else 0,
                 "actual_cost": float(r[8]) if r[8] is not None else 0,
                 "manager_id": r[9],
                 "created_at": r[10].isoformat() if r[10] else None} for r in rows]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        row = self.db.execute(text(
            "SELECT id, tenant_id, company_id, code, name, description, "
            "start_date, end_date, status, budget, actual_cost, manager_id, created_at "
            "FROM dbp_projects WHERE id = :pid"
        ), {"pid": project_id}).fetchone()
        if not row:
            return None
        task_count = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_project_tasks WHERE project_id = :pid"
        ), {"pid": project_id}).scalar()
        completed_count = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_project_tasks "
            "WHERE project_id = :pid AND status = 'done'"
        ), {"pid": project_id}).scalar()
        return {"id": row[0], "tenant_id": row[1], "company_id": row[2],
                "code": row[3], "name": row[4], "description": row[5],
                "start_date": row[6].isoformat() if row[6] else None,
                "end_date": row[7].isoformat() if row[7] else None,
                "status": row[8],
                "budget": float(row[9]) if row[9] is not None else 0,
                "actual_cost": float(row[10]) if row[10] is not None else 0,
                "manager_id": row[11],
                "created_at": row[12].isoformat() if row[12] else None,
                "task_count": int(task_count or 0),
                "completed_task_count": int(completed_count or 0)}

    def update_project(self, project_id: str, **kw) -> dict[str, Any]:
        fields = {k: v for k, v in kw.items()
                  if k in self.PROJECT_FIELDS and v is not None}
        if not fields:
            return {"success": False, "error": "No valid fields to update"}
        exists = self.db.execute(text(
            "SELECT id FROM dbp_projects WHERE id = :pid"
        ), {"pid": project_id}).fetchone()
        if not exists:
            return {"success": False, "error": "Project not found"}
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        params: dict[str, Any] = dict(fields)
        params["pid"] = project_id
        self.db.execute(text(
            f"UPDATE dbp_projects SET {sets} WHERE id = :pid"
        ), params)
        self.db.flush()
        return {"success": True}

    # ── TASKS ──

    def create_task(self, tenant_id: str, project_id: str, name: str, **kw) -> str:
        proj = self.db.execute(text(
            "SELECT tenant_id FROM dbp_projects WHERE id = :pid"
        ), {"pid": project_id}).fetchone()
        if not proj or (tenant_id and proj[0] != tenant_id):
            raise ValueError("Project not found")
        tid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_project_tasks (id, tenant_id, project_id, parent_task_id, "
            "name, description, assigned_to, priority, start_date, due_date, "
            "estimated_hours, sort_order) "
            "VALUES (:id, :tid, :pid, :parent, :name, :desc, :assigned, :prio, "
            ":sd, :dd, :est, :sort)"
        ), {"id": tid, "tid": tenant_id, "pid": project_id,
            "parent": kw.get("parent_task_id"), "name": name,
            "desc": kw.get("description"), "assigned": kw.get("assigned_to"),
            "prio": kw.get("priority", "normal"), "sd": kw.get("start_date"),
            "dd": kw.get("due_date"), "est": kw.get("estimated_hours"),
            "sort": kw.get("sort_order", 0)})
        self.db.flush()
        return tid

    def list_tasks(self, project_id: str, status: str | None = None,
                   assigned_to: str | None = None) -> list[dict[str, Any]]:
        conditions = ["project_id = :pid"]
        params: dict[str, Any] = {"pid": project_id}
        if status:
            conditions.append("status = :st")
            params["st"] = status
        if assigned_to:
            conditions.append("assigned_to = :who")
            params["who"] = assigned_to
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, parent_task_id, name, description, assigned_to, "
            f"status, priority, start_date, due_date, estimated_hours, actual_hours, "
            f"sort_order FROM dbp_project_tasks WHERE {where} "
            f"ORDER BY sort_order, created_at"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "project_id": project_id,
                 "parent_task_id": r[2], "name": r[3], "description": r[4],
                 "assigned_to": r[5], "status": r[6], "priority": r[7],
                 "start_date": r[8].isoformat() if r[8] else None,
                 "due_date": r[9].isoformat() if r[9] else None,
                 "estimated_hours": float(r[10]) if r[10] is not None else None,
                 "actual_hours": float(r[11]) if r[11] is not None else 0,
                 "sort_order": r[12]} for r in rows]

    def update_task(self, task_id: str, tenant_guard: str | None = None, **kw) -> dict[str, Any]:
        row = self.db.execute(text(
            "SELECT tenant_id FROM dbp_project_tasks WHERE id = :tid"
        ), {"tid": task_id}).fetchone()
        if not row or (tenant_guard and row[0] != tenant_guard):
            return {"success": False, "error": "Task not found"}
        fields = {k: v for k, v in kw.items()
                  if k in self.TASK_FIELDS and v is not None}
        if not fields:
            return {"success": False, "error": "No valid fields to update"}
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        params: dict[str, Any] = dict(fields)
        params["tid"] = task_id
        self.db.execute(text(
            f"UPDATE dbp_project_tasks SET {sets} WHERE id = :tid"
        ), params)
        self.db.flush()
        return {"success": True}

    def reorder_tasks(self, project_id: str, task_ids: list[str]) -> dict[str, Any]:
        rows = self.db.execute(text(
            "SELECT id FROM dbp_project_tasks WHERE project_id = :pid"
        ), {"pid": project_id}).fetchall()
        owned = {r[0] for r in rows}
        for tid in task_ids:
            if tid not in owned:
                return {"success": False,
                        "error": f"Task {tid} does not belong to this project"}
        for i, tid in enumerate(task_ids):
            self.db.execute(text(
                "UPDATE dbp_project_tasks SET sort_order = :so WHERE id = :tid"
            ), {"so": i, "tid": tid})
        self.db.flush()
        return {"success": True, "count": len(task_ids)}

    # ── MILESTONES ──

    def create_milestone(self, tenant_id: str, project_id: str, name: str,
                         due_date) -> str:
        proj = self.db.execute(text(
            "SELECT tenant_id FROM dbp_projects WHERE id = :pid"
        ), {"pid": project_id}).fetchone()
        if not proj or (tenant_id and proj[0] != tenant_id):
            raise ValueError("Project not found")
        mid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_project_milestones (id, tenant_id, project_id, "
            "name, due_date, status) VALUES (:id, :tid, :pid, :name, :dd, 'pending')"
        ), {"id": mid, "tid": tenant_id, "pid": project_id, "name": name, "dd": due_date})
        self.db.flush()
        return mid

    def list_milestones(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(text(
            "SELECT id, tenant_id, name, due_date, status, completed_at, created_at "
            "FROM dbp_project_milestones WHERE project_id = :pid "
            "ORDER BY due_date NULLS LAST, created_at"
        ), {"pid": project_id}).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "project_id": project_id,
                 "name": r[2],
                 "due_date": r[3].isoformat() if r[3] else None,
                 "status": r[4],
                 "completed_at": r[5].isoformat() if r[5] else None,
                 "created_at": r[6].isoformat() if r[6] else None} for r in rows]

    def complete_milestone(self, milestone_id: str,
                           tenant_guard: str | None = None) -> dict[str, Any]:
        row = self.db.execute(text(
            "SELECT tenant_id, status FROM dbp_project_milestones WHERE id = :mid"
        ), {"mid": milestone_id}).fetchone()
        if not row or (tenant_guard and row[0] != tenant_guard):
            return {"success": False, "error": "Milestone not found"}
        if row[1] == "completed":
            return {"success": False, "error": "Milestone already completed"}
        self.db.execute(text(
            "UPDATE dbp_project_milestones SET status = 'completed', "
            "completed_at = NOW() WHERE id = :mid"
        ), {"mid": milestone_id})
        self.db.flush()
        return {"success": True, "milestone_id": milestone_id, "status": "completed"}

    # ── TIME ENTRIES ──

    def log_time(self, tenant_id: str, project_id: str, task_id: str,
                 employee_id: str, work_date, hours, notes: str | None = None) -> str:
        proj = self.db.execute(text(
            "SELECT tenant_id FROM dbp_projects WHERE id = :pid"
        ), {"pid": project_id}).fetchone()
        if not proj or (tenant_id and proj[0] != tenant_id):
            raise ValueError("Project not found")
        if float(hours) <= 0:
            raise ValueError("Hours must be positive")
        task = self.db.execute(text(
            "SELECT id FROM dbp_project_tasks WHERE id = :tid AND project_id = :pid"
        ), {"tid": task_id, "pid": project_id}).fetchone()
        if not task:
            raise ValueError("Task not found in project")
        teid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_project_time_entries (id, tenant_id, project_id, "
            "task_id, employee_id, work_date, hours, notes) "
            "VALUES (:id, :tid, :pid, :task, :emp, :wd, :h, :notes)"
        ), {"id": teid, "tid": tenant_id, "pid": project_id, "task": task_id,
            "emp": employee_id, "wd": work_date, "h": hours, "notes": notes})
        self.db.execute(text(
            "UPDATE dbp_project_tasks SET actual_hours = COALESCE(actual_hours, 0) + :h "
            "WHERE id = :tid"
        ), {"h": hours, "tid": task_id})
        self.db.flush()
        return teid

    def get_time_entries(self, project_id: str, task_id: str | None = None,
                         employee_id: str | None = None) -> list[dict[str, Any]]:
        conditions = ["project_id = :pid"]
        params: dict[str, Any] = {"pid": project_id}
        if task_id:
            conditions.append("task_id = :tid")
            params["tid"] = task_id
        if employee_id:
            conditions.append("employee_id = :eid")
            params["eid"] = employee_id
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, tenant_id, task_id, employee_id, work_date, hours, notes, "
            f"created_at FROM dbp_project_time_entries WHERE {where} "
            f"ORDER BY work_date, created_at"
        ), params).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "project_id": project_id,
                 "task_id": r[2], "employee_id": r[3],
                 "work_date": r[4].isoformat() if r[4] else None,
                 "hours": float(r[5]) if r[5] is not None else 0,
                 "notes": r[6],
                 "created_at": r[7].isoformat() if r[7] else None} for r in rows]

    def get_project_time_summary(self, project_id: str) -> dict[str, Any]:
        total = self.db.execute(text(
            "SELECT COALESCE(SUM(hours), 0) FROM dbp_project_time_entries "
            "WHERE project_id = :pid"
        ), {"pid": project_id}).scalar()
        entry_count = self.db.execute(text(
            "SELECT COUNT(*) FROM dbp_project_time_entries WHERE project_id = :pid"
        ), {"pid": project_id}).scalar()
        by_emp = self.db.execute(text(
            "SELECT employee_id, SUM(hours) AS total, COUNT(*) AS entries "
            "FROM dbp_project_time_entries WHERE project_id = :pid "
            "GROUP BY employee_id ORDER BY total DESC"
        ), {"pid": project_id}).fetchall()
        return {"project_id": project_id,
                "total_hours": float(total) if total is not None else 0,
                "entry_count": int(entry_count or 0),
                "by_employee": [{"employee_id": e[0],
                                 "hours": float(e[1]) if e[1] is not None else 0,
                                 "entries": int(e[2])} for e in by_emp]}

    # ── HELPERS ──

    def _next_code(self, company_id: str, prefix: str = "PRJ") -> str:
        rows = self.db.execute(text(
            "SELECT code FROM dbp_projects WHERE company_id = :cid AND code LIKE :pre"
        ), {"cid": company_id, "pre": f"{prefix}-%"}).fetchall()
        num = 0
        for r in rows:
            try:
                num = max(num, int(str(r[0]).rsplit("-", 1)[1]))
            except (ValueError, IndexError):
                continue
        return f"{prefix}-{num + 1:06d}"
