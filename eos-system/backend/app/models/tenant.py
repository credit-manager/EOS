"""
EOS System — Tenant Model
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Tenant(Base):
    """Tenant model for multi-tenancy."""
    
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    industry = Column(String(50), nullable=False, index=True)
    employee_count = Column(Integer)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    status = Column(String(20), default="active", index=True)
    subscription_plan = Column(String(50), default="basic")
    subscription_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tenant {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "slug": self.slug,
            "industry": self.industry,
            "employee_count": self.employee_count,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
            "subscription_plan": self.subscription_plan,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
