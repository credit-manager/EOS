"""
EOS System — Extended HR Models (Job Titles, Leaves, Leave Types, Payroll, Evaluations, Trainings)
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class JobTitle(Base):
    """Job Title / Designation."""
    
    __tablename__ = "job_titles"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100))
    department_id = Column(String(36), ForeignKey("departments.id"))
    min_salary = Column(Numeric(18, 2))
    max_salary = Column(Numeric(18, 2))
    is_active = Column(Boolean, default=True)
    
    department = relationship("Department")
    
    def to_dict(self):
        return {"id": self.id, "name": self.name, "name_ar": self.name_ar}


class LeaveType(Base):
    """Leave Type (Annual, Sick, etc.)."""
    
    __tablename__ = "leave_types"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100))
    days_per_year = Column(Integer, default=0)
    is_paid = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    def to_dict(self):
        return {"id": self.id, "name": self.name, "days_per_year": self.days_per_year}


class Leave(Base):
    """Leave Request / Balance."""
    
    __tablename__ = "leaves"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id = Column(String(36), ForeignKey("leave_types.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Integer, nullable=False)
    reason = Column(Text)
    status = Column(String(20), default="pending", index=True)  # pending, approved, rejected
    approved_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    employee = relationship("Employee")
    leave_type = relationship("LeaveType")
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "leave_type": self.leave_type.name if self.leave_type else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "days": self.days,
            "status": self.status,
        }


class Payroll(Base):
    """Monthly Payroll Run."""
    
    __tablename__ = "payroll"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g. "August 2026"
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    status = Column(String(20), default="draft", index=True)  # draft, processing, completed, paid
    total_gross = Column(Numeric(18, 2), default=0)
    total_deductions = Column(Numeric(18, 2), default=0)
    total_net = Column(Numeric(18, 2), default=0)
    processed_by = Column(String(36), ForeignKey("users.id"))
    processed_at = Column(DateTime)
    paid_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    items = relationship("PayrollItem", back_populates="payroll", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "month": self.month,
            "year": self.year,
            "status": self.status,
            "total_net": float(self.total_net) if self.total_net else 0,
        }


class PayrollItem(Base):
    """Individual Employee Payroll Record."""
    
    __tablename__ = "payroll_lines"
    
    id = Column(String(36), primary_key=True)
    payroll_id = Column(String(36), ForeignKey("payroll.id"), nullable=False, index=True)
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False)
    basic_salary = Column(Numeric(18, 2), nullable=False)
    allowances = Column(Numeric(18, 2), default=0)
    bonuses = Column(Numeric(18, 2), default=0)
    social_insurance = Column(Numeric(18, 2), default=0)  # 11% employee
    tax = Column(Numeric(18, 2), default=0)
    deductions = Column(Numeric(18, 2), default=0)
    net_salary = Column(Numeric(18, 2), nullable=False)
    
    payroll = relationship("Payroll", back_populates="items")
    employee = relationship("Employee")
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "basic_salary": float(self.basic_salary),
            "net_salary": float(self.net_salary),
        }


class Evaluation(Base):
    """Employee Performance Evaluation."""
    
    __tablename__ = "evaluations"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False, index=True)
    period = Column(String(50))  # e.g. "Q3 2026"
    score = Column(Numeric(5, 2))  # e.g. 4.50 out of 5
    strengths = Column(Text)
    improvements = Column(Text)
    comments = Column(Text)
    evaluated_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    employee = relationship("Employee")
    
    def to_dict(self):
        return {"id": self.id, "employee_id": self.employee_id, "period": self.period, "score": float(self.score) if self.score else None}


class Training(Base):
    """Training Program."""
    
    __tablename__ = "trainings"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255))
    description = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    instructor = Column(String(255))
    max_participants = Column(Integer)
    status = Column(String(20), default="planned")  # planned, ongoing, completed
    
    def to_dict(self):
        return {"id": self.id, "name": self.name, "status": self.status}


class TrainingEnrollment(Base):
    """Employee Training Enrollment."""
    
    __tablename__ = "training_enrollments"
    
    id = Column(String(36), primary_key=True)
    training_id = Column(String(36), ForeignKey("trainings.id"), nullable=False, index=True)
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False)
    status = Column(String(20), default="enrolled")  # enrolled, completed, dropped
    score = Column(Numeric(5, 2))
    certificate_url = Column(String(500))
    
    training = relationship("Training")
    employee = relationship("Employee")
