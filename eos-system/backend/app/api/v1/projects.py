"""
EOS System — Projects Module Router (Real Implementation)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.projects import Project, Task, TimeEntry

router = APIRouter()


# Schemas
class ProjectCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    budget: Optional[Decimal] = None
    currency: str = "EGP"
    manager_id: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    name_ar: Optional[str]
    description: Optional[str]
    client_id: Optional[str]
    start_date: date
    end_date: Optional[date]
    budget: Optional[float]
    currency: str
    manager_id: Optional[str]
    status: str
    progress: int
    created_at: datetime


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int


class TaskCreate(BaseModel):
    project_id: str
    name: str
    name_ar: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = None
    priority: str = "medium"
    parent_task_id: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    project_id: str
    name: str
    name_ar: Optional[str]
    description: Optional[str]
    assignee_id: Optional[str]
    assignee_name: Optional[str]
    start_date: Optional[date]
    due_date: Optional[date]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    priority: str
    status: str
    parent_task_id: Optional[str]
    created_at: datetime


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int


class TimeEntryCreate(BaseModel):
    task_id: str
    project_id: str
    date: date
    hours: Decimal
    description: Optional[str] = None


class TimeEntryResponse(BaseModel):
    id: str
    task_id: str
    project_id: str
    employee_id: str
    date: date
    hours: float
    description: Optional[str]
    created_at: datetime


class TimeEntryListResponse(BaseModel):
    entries: List[TimeEntryResponse]
    total: int


# Endpoints
@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[str] = None,
    manager_id: Optional[str] = None,
    client_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List projects."""
    query = select(Project)
    
    if status:
        query = query.filter(Project.status == status)
    
    if manager_id:
        query = query.filter(Project.manager_id == manager_id)
    
    if client_id:
        query = query.filter(Project.client_id == client_id)
    
    query = query.order_by(Project.created_at.desc())
    
    # Count total
    count_query = select(func.count(Project.id))
    if status:
        count_query = count_query.filter(Project.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ProjectListResponse(
        projects=[ProjectResponse(
            id=project.id,
            name=project.name,
            name_ar=project.name_ar,
            description=project.description,
            client_id=project.client_id,
            start_date=project.start_date,
            end_date=project.end_date,
            budget=float(project.budget) if project.budget else None,
            currency=project.currency,
            manager_id=project.manager_id,
            status=project.status,
            progress=project.progress,
            created_at=project.created_at,
        ) for project in projects],
        total=total,
    )


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new project."""
    new_project = Project(
        id=str(uuid.uuid4()),
        name=project.name,
        name_ar=project.name_ar,
        description=project.description,
        client_id=project.client_id,
        start_date=project.start_date,
        end_date=project.end_date,
        budget=project.budget,
        currency=project.currency,
        manager_id=project.manager_id,
        status="planning",
        progress=0,
    )
    
    db.add(new_project)
    await db.flush()
    
    return ProjectResponse(
        id=new_project.id,
        name=new_project.name,
        name_ar=new_project.name_ar,
        description=new_project.description,
        client_id=new_project.client_id,
        start_date=new_project.start_date,
        end_date=new_project.end_date,
        budget=float(new_project.budget) if new_project.budget else None,
        currency=new_project.currency,
        manager_id=new_project.manager_id,
        status=new_project.status,
        progress=new_project.progress,
        created_at=new_project.created_at,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get project by ID."""
    result = await db.execute(
        select(Project).filter(Project.id == project_id)
    )
    project = result.scalar()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        name_ar=project.name_ar,
        description=project.description,
        client_id=project.client_id,
        start_date=project.start_date,
        end_date=project.end_date,
        budget=float(project.budget) if project.budget else None,
        currency=project.currency,
        manager_id=project.manager_id,
        status=project.status,
        progress=project.progress,
        created_at=project.created_at,
    )


@router.get("/{project_id}/tasks", response_model=TaskListResponse)
async def list_tasks(
    project_id: str,
    assignee_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List tasks for a project."""
    query = select(Task).filter(Task.project_id == project_id)
    
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    
    if status:
        query = query.filter(Task.status == status)
    
    if priority:
        query = query.filter(Task.priority == priority)
    
    query = query.order_by(Task.created_at.desc())
    
    # Count total
    count_query = select(func.count(Task.id)).filter(Task.project_id == project_id)
    if status:
        count_query = count_query.filter(Task.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return TaskListResponse(
        tasks=[TaskResponse(
            id=task.id,
            project_id=task.project_id,
            name=task.name,
            name_ar=task.name_ar,
            description=task.description,
            assignee_id=task.assignee_id,
            assignee_name=task.assignee.full_name if task.assignee else None,
            start_date=task.start_date,
            due_date=task.due_date,
            estimated_hours=float(task.estimated_hours) if task.estimated_hours else None,
            actual_hours=float(task.actual_hours) if task.actual_hours else None,
            priority=task.priority,
            status=task.status,
            parent_task_id=task.parent_task_id,
            created_at=task.created_at,
        ) for task in tasks],
        total=total,
    )


@router.post("/{project_id}/tasks", response_model=TaskResponse)
async def create_task(
    project_id: str,
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new task."""
    # Verify project exists
    project_result = await db.execute(
        select(Project).filter(Project.id == project_id)
    )
    project = project_result.scalar()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    new_task = Task(
        id=str(uuid.uuid4()),
        project_id=project_id,
        name=task.name,
        name_ar=task.name_ar,
        description=task.description,
        assignee_id=task.assignee_id,
        start_date=task.start_date,
        due_date=task.due_date,
        estimated_hours=task.estimated_hours,
        priority=task.priority,
        status="todo",
        parent_task_id=task.parent_task_id,
    )
    
    db.add(new_task)
    await db.flush()
    
    return TaskResponse(
        id=new_task.id,
        project_id=new_task.project_id,
        name=new_task.name,
        name_ar=new_task.name_ar,
        description=new_task.description,
        assignee_id=new_task.assignee_id,
        assignee_name=None,
        start_date=new_task.start_date,
        due_date=new_task.due_date,
        estimated_hours=float(new_task.estimated_hours) if new_task.estimated_hours else None,
        actual_hours=None,
        priority=new_task.priority,
        status=new_task.status,
        parent_task_id=new_task.parent_task_id,
        created_at=new_task.created_at,
    )


@router.get("/time-entries", response_model=TimeEntryListResponse)
async def list_time_entries(
    task_id: Optional[str] = None,
    project_id: Optional[str] = None,
    employee_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List time entries."""
    query = select(TimeEntry)
    
    if task_id:
        query = query.filter(TimeEntry.task_id == task_id)
    
    if project_id:
        query = query.filter(TimeEntry.project_id == project_id)
    
    if employee_id:
        query = query.filter(TimeEntry.employee_id == employee_id)
    
    if start_date:
        query = query.filter(TimeEntry.date >= start_date)
    
    if end_date:
        query = query.filter(TimeEntry.date <= end_date)
    
    query = query.order_by(TimeEntry.date.desc())
    
    # Count total
    count_query = select(func.count(TimeEntry.id))
    if project_id:
        count_query = count_query.filter(TimeEntry.project_id == project_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return TimeEntryListResponse(
        entries=[TimeEntryResponse(
            id=entry.id,
            task_id=entry.task_id,
            project_id=entry.project_id,
            employee_id=entry.employee_id,
            date=entry.date,
            hours=float(entry.hours),
            description=entry.description,
            created_at=entry.created_at,
        ) for entry in entries],
        total=total,
    )


@router.post("/time-entries", response_model=TimeEntryResponse)
async def create_time_entry(
    entry: TimeEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Log time entry."""
    # Verify task exists
    task_result = await db.execute(
        select(Task).filter(Task.id == entry.task_id)
    )
    task = task_result.scalar()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    new_entry = TimeEntry(
        id=str(uuid.uuid4()),
        task_id=entry.task_id,
        project_id=entry.project_id,
        employee_id=current_user["id"],
        date=entry.date,
        hours=entry.hours,
        description=entry.description,
    )
    
    db.add(new_entry)
    
    # Update task actual hours
    if task.actual_hours:
        task.actual_hours += entry.hours
    else:
        task.actual_hours = entry.hours
    
    await db.flush()
    
    return TimeEntryResponse(
        id=new_entry.id,
        task_id=new_entry.task_id,
        project_id=new_entry.project_id,
        employee_id=new_entry.employee_id,
        date=new_entry.date,
        hours=float(new_entry.hours),
        description=new_entry.description,
        created_at=new_entry.created_at,
    )
