from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..auth.security import Principal, require_principal
from ..db import commit_db, get_db
from ..tenant import require_tenant
from . import schemas, service

router = APIRouter(prefix="/api/v1/pm", tags=["pm"])


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@router.post("/projects", status_code=201, response_model=schemas.ProjectResponse)
def create_project(
    payload: schemas.ProjectCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    project = service.create_project(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget=payload.budget,
        progress=payload.progress,
        manager_id=payload.manager_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return project


@router.get("/projects", response_model=list[schemas.ProjectResponse])
def list_projects(
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_projects(db, tenant_id=tenant_id)


@router.get("/projects/{project_id}", response_model=schemas.ProjectResponse)
def get_project(
    project_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_project(db, tenant_id=tenant_id, project_id=project_id)


@router.patch("/projects/{project_id}", response_model=schemas.ProjectResponse)
def update_project(
    project_id: UUID,
    payload: schemas.ProjectUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    project = service.update_project(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=project_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_project(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=project_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@router.post("/tasks", status_code=201, response_model=schemas.TaskResponse)
def create_task(
    payload: schemas.TaskCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    task = service.create_task(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        assigned_to=payload.assigned_to,
        due_date=payload.due_date,
        estimated_hours=payload.estimated_hours,
        actual_hours=payload.actual_hours,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return task


@router.get("/tasks", response_model=list[schemas.TaskResponse])
def list_tasks(
    project_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_tasks(db, tenant_id=tenant_id, project_id=project_id)


@router.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def get_task(
    task_id: UUID,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.get_task(db, tenant_id=tenant_id, task_id=task_id)


@router.patch("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(
    task_id: UUID,
    payload: schemas.TaskUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    task = service.update_task(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        task_id=task_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_task(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        task_id=task_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

@router.post("/milestones", status_code=201, response_model=schemas.MilestoneResponse)
def create_milestone(
    payload: schemas.MilestoneCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    milestone = service.create_milestone(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        project_id=payload.project_id,
        name=payload.name,
        due_date=payload.due_date,
        status=payload.status,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return milestone


@router.get("/milestones", response_model=list[schemas.MilestoneResponse])
def list_milestones(
    project_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_milestones(db, tenant_id=tenant_id, project_id=project_id)


@router.patch("/milestones/{milestone_id}", response_model=schemas.MilestoneResponse)
def update_milestone(
    milestone_id: UUID,
    payload: schemas.MilestoneUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    milestone = service.update_milestone(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        milestone_id=milestone_id,
        data=data,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return milestone


@router.delete("/milestones/{milestone_id}", status_code=204)
def delete_milestone(
    milestone_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_milestone(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        milestone_id=milestone_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)


# ---------------------------------------------------------------------------
# Time Entries
# ---------------------------------------------------------------------------

@router.post("/time-entries", status_code=201, response_model=schemas.TimeEntryResponse)
def create_time_entry(
    payload: schemas.TimeEntryCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    entry = service.create_time_entry(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        task_id=payload.task_id,
        date_val=payload.date,
        hours=payload.hours,
        description=payload.description,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
    return entry


@router.get("/time-entries", response_model=list[schemas.TimeEntryResponse])
def list_time_entries(
    task_id: UUID | None = None,
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.list_time_entries(db, tenant_id=tenant_id, task_id=task_id)


@router.delete("/time-entries/{entry_id}", status_code=204)
def delete_time_entry(
    entry_id: UUID,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    service.delete_time_entry(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        entry_id=entry_id,
        request_id=getattr(request.state, "request_id", None),
    )
    commit_db(db)
