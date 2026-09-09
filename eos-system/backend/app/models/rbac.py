"""
EOS System — RBAC Models (Roles, Permissions, User-Roles, Role-Permissions)
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base


class Role(Base):
    """Role model for RBAC."""
    
    __tablename__ = "roles"
    
    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100))
    description = Column(Text)
    is_system = Column(Boolean, default=False)  # System roles can't be deleted
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    
    def to_dict(self, include_permissions=False):
        data = {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "description": self.description,
            "is_system": self.is_system,
            "is_active": self.is_active,
            "tenant_id": self.tenant_id,
        }
        if include_permissions:
            data["permissions"] = [rp.permission.to_dict() for rp in self.permissions if rp.permission]
        return data


class Permission(Base):
    """Permission model for granular access control."""
    
    __tablename__ = "permissions"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g. "accounting:create"
    name_ar = Column(String(100))
    module = Column(String(50), nullable=False, index=True)  # e.g. "accounting"
    action = Column(String(50), nullable=False)  # e.g. "create", "read", "update", "delete"
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    roles = relationship("RolePermission", back_populates="permission")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "module": self.module,
            "action": self.action,
        }


class UserRole(Base):
    """Many-to-many: Users <-> Roles."""
    
    __tablename__ = "user_roles"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(String(36))
    
    # Relationships
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="users")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "role_name": self.role.name if self.role else None,
        }


class RolePermission(Base):
    """Many-to-many: Roles <-> Permissions."""
    
    __tablename__ = "role_permissions"
    
    id = Column(String(36), primary_key=True)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = Column(String(36), ForeignKey("permissions.id"), nullable=False, index=True)
    
    # Relationships
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")
    
    def to_dict(self):
        return {
            "id": self.id,
            "role_id": self.role_id,
            "permission_id": self.permission_id,
        }
