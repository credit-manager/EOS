"""
EOS System — HR Models
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Department(Base):
    """Department model."""
    
    __tablename__ = "departments"
    
    id = Column(String(36), primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=False)
    manager_id = Column(String(36), ForeignKey("employees.id"))
    parent_id = Column(String(36), ForeignKey("departments.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    manager = relationship("Employee", foreign_keys=[manager_id])
    parent = relationship("Department", remote_side=[id], backref="children")
    employees = relationship("Employee", back_populates="department", foreign_keys="Employee.department_id")
    positions = relationship("Position", back_populates="department")
    
    def __repr__(self):
        return f"<Department {self.code} - {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "name_ar": self.name_ar,
            "manager_id": self.manager_id,
            "parent_id": self.parent_id,
            "employee_count": len(self.employees) if self.employees else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Position(Base):
    """Position model."""
    
    __tablename__ = "positions"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=False)
    department_id = Column(String(36), ForeignKey("departments.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    department = relationship("Department", back_populates="positions")
    employees = relationship("Employee", back_populates="position")
    
    def __repr__(self):
        return f"<Position {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "department_id": self.department_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Employee(Base):
    """Employee model."""
    
    __tablename__ = "employees"
    
    id = Column(String(36), primary_key=True)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    first_name_ar = Column(String(100))
    last_name_ar = Column(String(100))
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    department_id = Column(String(36), ForeignKey("departments.id"), index=True)
    position_id = Column(String(36), ForeignKey("positions.id"), index=True)
    hire_date = Column(Date, nullable=False)
    salary = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), default="EGP")
    national_id = Column(String(50))
    social_insurance_number = Column(String(50))
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="employee")
    department = relationship("Department", back_populates="employees", foreign_keys=[department_id])
    position = relationship("Position", back_populates="employees")
    attendance_records = relationship("AttendanceRecord", back_populates="employee")
    
    def __repr__(self):
        return f"<Employee {self.employee_id} - {self.first_name} {self.last_name}>"
    
    def to_dict(self, include_department=False, include_position=False):
        data = {
            "id": self.id,
            "employee_id": self.employee_id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "first_name_ar": self.first_name_ar,
            "last_name_ar": self.last_name_ar,
            "email": self.email,
            "phone": self.phone,
            "department_id": self.department_id,
            "position_id": self.position_id,
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "salary": float(self.salary) if self.salary else 0,
            "currency": self.currency,
            "national_id": self.national_id,
            "social_insurance_number": self.social_insurance_number,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_department and self.department:
            data["department"] = self.department.to_dict()
        
        if include_position and self.position:
            data["position"] = self.position.to_dict()
        
        return data
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name_ar(self):
        if self.first_name_ar and self.last_name_ar:
            return f"{self.first_name_ar} {self.last_name_ar}"
        return None


class AttendanceRecord(Base):
    """Attendance Record model."""
    
    __tablename__ = "attendance_records"
    
    id = Column(String(36), primary_key=True)
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    clock_in = Column(DateTime)
    clock_out = Column(DateTime)
    status = Column(String(20), nullable=False)  # present, absent, late, leave
    overtime_hours = Column(Numeric(8, 2), default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee", back_populates="attendance_records")
    
    def __repr__(self):
        return f"<AttendanceRecord {self.employee_id} - {self.date}>"
    
    def to_dict(self, include_employee=False):
        data = {
            "id": self.id,
            "employee_id": self.employee_id,
            "date": self.date.isoformat() if self.date else None,
            "clock_in": self.clock_in.isoformat() if self.clock_in else None,
            "clock_out": self.clock_out.isoformat() if self.clock_out else None,
            "status": self.status,
            "overtime_hours": float(self.overtime_hours) if self.overtime_hours else 0,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_employee and self.employee:
            data["employee"] = self.employee.to_dict()
        
        return data
    
    @property
    def hours_worked(self):
        """Calculate hours worked."""
        if self.clock_in and self.clock_out:
            delta = self.clock_out - self.clock_in
            return delta.total_seconds() / 3600
        return 0
