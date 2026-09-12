from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from .models import (
    VALID_PROJECT_TRANSITIONS,
    VALID_TASK_TRANSITIONS,
    Milestone,
    Project,
    Task,
    TimeEntry,
)

# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

def create_project(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    code: str,
    name: str,
    description: str | None = None,
    status: str = "planning",
    priority: str = "medium",
    start_date=None,
    end_date=None,
    budget: Decimal = Decimal("0"),
    progress: int = 0,
    manager_id: UUID | None = None,
    request_id: str | None = None,
) -> Project:
    existing = db.scalar(
        select(Project).where(Project.tenant_id == tenant_id, Project.code == code)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="project code already exists")
    project = Project(
        tenant_id=tenant_id,
        created_by=user_id,
        code=code,
        name=name,
        description=description,
        status=status,
        priority=priority,
        start_date=start_date,
        end_date=end_date,
        budget=budget,
        progress=progress,
        manager_id=manager_id,
    )
    db.add(project)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.project.created",
        resource_type="pm_project",
        resource_id=project.id,
        request_id=request_id,
        metadata={"code": code, "name": name},
    )
    db.flush()
    return project


def get_project(db: Session, *, tenant_id: UUID, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


def list_projects(db: Session, *, tenant_id: UUID) -> list[Project]:
    return db.scalars(
        select(Project).where(Project.tenant_id == tenant_id).order_by(Project.created_at.desc())
    ).all()


def update_project(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Project:
    project = get_project(db, tenant_id=tenant_id, project_id=project_id)
    new_status = data.get("status")
    if new_status is not None and new_status != project.status:
        allowed = VALID_PROJECT_TRANSITIONS.get(project.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"cannot transition project from '{project.status}' to '{new_status}'",
            )
    allowed = {
        "name", "description", "status", "priority", "start_date",
        "end_date", "budget", "progress", "manager_id",
    }
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(project, key, value)
    project.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.project.updated",
        resource_type="pm_project",
        resource_id=project.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return project


def delete_project(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    request_id: str | None = None,
) -> None:
    project = get_project(db, tenant_id=tenant_id, project_id=project_id)
    task_count = db.scalar(
        select(Task).where(Task.tenant_id == tenant_id, Task.project_id == project_id).limit(1)
    )
    if task_count is not None:
        raise HTTPException(status_code=409, detail="cannot delete project with existing tasks")
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.project.deleted",
        resource_type="pm_project",
        resource_id=project.id,
        request_id=request_id,
    )
    db.delete(project)
    db.flush()


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

def create_task(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    title: str,
    description: str | None = None,
    status: str = "todo",
    priority: str = "medium",
    assigned_to: UUID | None = None,
    due_date=None,
    estimated_hours: Decimal | None = None,
    actual_hours: Decimal | None = None,
    request_id: str | None = None,
) -> Task:
    project = get_project(db, tenant_id=tenant_id, project_id=project_id)
    if project.status in ("completed", "cancelled"):
        raise HTTPException(status_code=409, detail="cannot add tasks to a completed or cancelled project")
    task = Task(
        tenant_id=tenant_id,
        created_by=user_id,
        project_id=project_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        due_date=due_date,
        estimated_hours=estimated_hours,
        actual_hours=actual_hours,
    )
    db.add(task)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.task.created",
        resource_type="pm_task",
        resource_id=task.id,
        request_id=request_id,
        metadata={"project_id": str(project_id), "title": title},
    )
    db.flush()
    return task


def get_task(db: Session, *, tenant_id: UUID, task_id: UUID) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="task not found")
    return task


def list_tasks(db: Session, *, tenant_id: UUID, project_id: UUID | None = None) -> list[Task]:
    stmt = select(Task).where(Task.tenant_id == tenant_id)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    return db.scalars(stmt.order_by(Task.created_at.desc())).all()


def update_task(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    task_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Task:
    task = get_task(db, tenant_id=tenant_id, task_id=task_id)
    new_status = data.get("status")
    if new_status is not None and new_status != task.status:
        allowed = VALID_TASK_TRANSITIONS.get(task.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"cannot transition task from '{task.status}' to '{new_status}'",
            )
    allowed = {
        "title", "description", "status", "priority", "assigned_to",
        "due_date", "estimated_hours", "actual_hours",
    }
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(task, key, value)
    task.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.task.updated",
        resource_type="pm_task",
        resource_id=task.id,
        request_id=request_id,
        metadata=data,
    )
    db.flush()
    return task


def delete_task(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    task_id: UUID,
    request_id: str | None = None,
) -> None:
    task = get_task(db, tenant_id=tenant_id, task_id=task_id)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.task.deleted",
        resource_type="pm_task",
        resource_id=task.id,
        request_id=request_id,
    )
    db.delete(task)
    db.flush()


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------

def create_milestone(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    project_id: UUID,
    name: str,
    due_date,
    status: str = "pending",
    request_id: str | None = None,
) -> Milestone:
    get_project(db, tenant_id=tenant_id, project_id=project_id)
    milestone = Milestone(
        tenant_id=tenant_id,
        project_id=project_id,
        name=name,
        due_date=due_date,
        status=status,
    )
    db.add(milestone)
    db.flush()
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.milestone.created",
        resource_type="pm_milestone",
        resource_id=milestone.id,
        request_id=request_id,
        metadata={"project_id": str(project_id), "name": name},
    )
    db.flush()
    return milestone


def get_milestone(db: Session, *, tenant_id: UUID, milestone_id: UUID) -> Milestone:
    milestone = db.get(Milestone, milestone_id)
    if milestone is None or milestone.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="milestone not found")
    return milestone


def list_milestones(
    db: Session, *, tenant_id: UUID, project_id: UUID | None = None
) -> list[Milestone]:
    stmt = select(Milestone).where(Milestone.tenant_id == tenant_id)
    if project_id is not None:
        stmt = stmt.where(Milestone.project_id == project_id)
    return db.scalars(stmt.order_by(Milestone.due_date)).all()


def update_milestone(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    milestone_id: UUID,
    data: dict,
    request_id: str | None = None,
) -> Milestone:
    milestone = get_milestone(db, tenant_id=tenant_id, milestone_id=milestone_id)
    new_status = data.get("status")
    if new_status == "achieved" and milestone.status != "achieved":
        milestone.completed_at = datetime.now(UTC)
    allowed = {"name", "due_date", "status"}
    for key, value in data.items():
        if value is not None and key in allowed:
            setattr(milestone, key, value)
    audit_metadata = {k: str(v) if isinstance(v, (datetime, UUID)) else v for k, v in data.items()}
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.milestone.updated",
        resource_type="pm_milestone",
        resource_id=milestone.id,
        request_id=request_id,
        metadata=audit_metadata,
    )
    db.flush()
    return milestone


def delete_milestone(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    milestone_id: UUID,
    request_id: str | None = None,
) -> None:
    milestone = get_milestone(db, tenant_id=tenant_id, milestone_id=milestone_id)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.milestone.deleted",
        resource_type="pm_milestone",
        resource_id=milestone.id,
        request_id=request_id,
    )
    db.delete(milestone)
    db.flush()


# ---------------------------------------------------------------------------
# TimeEntry
# ---------------------------------------------------------------------------

def create_time_entry(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    task_id: UUID,
    date_val,
    hours: Decimal,
    description: str | None = None,
    request_id: str | None = None,
) -> TimeEntry:
    task = get_task(db, tenant_id=tenant_id, task_id=task_id)
    if task.status == "done":
        raise HTTPException(status_code=409, detail="cannot log time on a completed task")
    entry = TimeEntry(
        tenant_id=tenant_id,
        task_id=task_id,
        user_id=user_id,
        date=date_val,
        hours=hours,
        description=description,
    )
    db.add(entry)
    db.flush()
    if task.actual_hours is None:
        task.actual_hours = Decimal("0")
    task.actual_hours = task.actual_hours + hours
    task.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.time_entry.created",
        resource_type="pm_time_entry",
        resource_id=entry.id,
        request_id=request_id,
        metadata={"task_id": str(task_id), "hours": str(hours)},
    )
    db.flush()
    return entry


def list_time_entries(
    db: Session, *, tenant_id: UUID, task_id: UUID | None = None, user_id: UUID | None = None
) -> list[TimeEntry]:
    stmt = select(TimeEntry).where(TimeEntry.tenant_id == tenant_id)
    if task_id is not None:
        stmt = stmt.where(TimeEntry.task_id == task_id)
    if user_id is not None:
        stmt = stmt.where(TimeEntry.user_id == user_id)
    return db.scalars(stmt.order_by(TimeEntry.date.desc())).all()


def delete_time_entry(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    entry_id: UUID,
    request_id: str | None = None,
) -> None:
    entry = db.get(TimeEntry, entry_id)
    if entry is None or entry.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="time entry not found")
    task = get_task(db, tenant_id=tenant_id, task_id=entry.task_id)
    if task.actual_hours is not None:
        task.actual_hours = max(Decimal("0"), task.actual_hours - entry.hours)
        task.updated_at = datetime.now(UTC)
    audit_record(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        action="pm.time_entry.deleted",
        resource_type="pm_time_entry",
        resource_id=entry.id,
        request_id=request_id,
    )
    db.delete(entry)
    db.flush()
