"""
EOS System — Projects Models
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Project(Base):
    """Project model."""
    
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text)
    client_id = Column(String(36), ForeignKey("customers.id"), index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    budget = Column(Numeric(18, 2))
    currency = Column(String(3), default="EGP")
    manager_id = Column(String(36), ForeignKey("employees.id"))
    status = Column(String(20), default="planning", index=True)
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Customer")
    manager = relationship("Employee")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="project")
    
    def __repr__(self):
        return f"<Project {self.name}>"
    
    def to_dict(self, include_tasks=False):
        data = {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "description": self.description,
            "client_id": self.client_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "budget": float(self.budget) if self.budget else None,
            "currency": self.currency,
            "manager_id": self.manager_id,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_tasks:
            data["tasks"] = [task.to_dict() for task in self.tasks]
        
        return data
    
    @property
    def total_hours_logged(self):
        """Calculate total hours logged on project."""
        return sum(entry.hours for entry in self.time_entries if entry.hours)
    
    @property
    def is_overdue(self):
        """Check if project is overdue."""
        if self.end_date and self.status != "completed":
            return self.end_date < datetime.now().date()
        return False


class Task(Base):
    """Task model."""
    
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text)
    assignee_id = Column(String(36), ForeignKey("employees.id"), index=True)
    start_date = Column(Date)
    due_date = Column(Date)
    estimated_hours = Column(Numeric(8, 2))
    actual_hours = Column(Numeric(8, 2))
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    status = Column(String(20), default="todo", index=True)  # todo, in_progress, review, done
    parent_task_id = Column(String(36), ForeignKey("tasks.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("Employee")
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    time_entries = relationship("TimeEntry", back_populates="task")
    
    def __repr__(self):
        return f"<Task {self.name}>"
    
    def to_dict(self, include_subtasks=False):
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "name_ar": self.name_ar,
            "description": self.description,
            "assignee_id": self.assignee_id,
            "assignee_name": self.assignee.full_name if self.assignee else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "estimated_hours": float(self.estimated_hours) if self.estimated_hours else None,
            "actual_hours": float(self.actual_hours) if self.actual_hours else None,
            "priority": self.priority,
            "status": self.status,
            "parent_task_id": self.parent_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_subtasks:
            data["subtasks"] = [subtask.to_dict() for subtask in self.subtasks]
        
        return data
    
    @property
    def is_overdue(self):
        """Check if task is overdue."""
        if self.due_date and self.status != "done":
            return self.due_date < datetime.now().date()
        return False
    
    @property
    def progress_percentage(self):
        """Calculate task progress based on subtasks."""
        if not self.subtasks:
            return 100 if self.status == "done" else 0
        
        completed = sum(1 for subtask in self.subtasks if subtask.status == "done")
        return int((completed / len(self.subtasks)) * 100)


class TimeEntry(Base):
    """Time Entry model."""
    
    __tablename__ = "time_entries"
    
    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    hours = Column(Numeric(8, 2), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", back_populates="time_entries")
    project = relationship("Project", back_populates="time_entries")
    employee = relationship("Employee")
    
    def __repr__(self):
        return f"<TimeEntry {self.employee_id} - {self.date} - {self.hours}h>"
    
    def to_dict(self, include_task=False, include_employee=False):
        data = {
            "id": self.id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "employee_id": self.employee_id,
            "date": self.date.isoformat() if self.date else None,
            "hours": float(self.hours) if self.hours else 0,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_task and self.task:
            data["task"] = self.task.to_dict()
        
        if include_employee and self.employee:
            data["employee"] = self.employee.to_dict()
        
        return data
