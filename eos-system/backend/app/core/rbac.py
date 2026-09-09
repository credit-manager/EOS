"""
EOS System — RBAC Dependency & Audit Logging
"""
from typing import Optional
from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.rbac import UserRole, RolePermission, Permission
from app.models.audit import AuditLog


async def get_user_permissions(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get all permission names for the current user.

    Priority:
    1. Check UserRole table for assigned roles (scoped to the user's tenant)
    2. If user has Admin role via UserRole → full access ["*:*"]
    3. If no UserRole entries → check User.role field (backward compat)

    Defense in depth: role lookups are ALWAYS filtered by the caller's
    canonical tenant_id so a UserRole row can never grant privileges from
    another tenant's role, even if IDs were reused or corrupted.
    """
    user_id = user["id"]
    tenant_id = user["tenant_id"]

    # Check UserRole table first (tenant-scoped)
    from app.models.rbac import Role
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, Role.tenant_id == tenant_id)
    )
    role_names = [row[0] for row in result.all()]

    # If user has Admin role via UserRole table → full access
    if "Admin" in role_names:
        return ["*:*"]

    # If user has roles via UserRole, get their permissions (tenant-scoped)
    if role_names:
        perm_result = await db.execute(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .join(Role, RolePermission.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.tenant_id == tenant_id)
        )
        return [row[0] for row in perm_result.all()]

    # Backward compat: check User.role field
    # If role="admin" (old users), give full access
    if user.get("roles") and "admin" in user["roles"]:
        return ["*:*"]

    # No roles assigned → no permissions
    return []


def require_permission(module: str, action: str):
    """Dependency factory: require a specific permission.
    
    Usage:
        @router.post("/accounts", dependencies=[Depends(require_permission("accounting", "create"))])
    """
    async def _check(permissions: list[str] = Depends(get_user_permissions)):
        required = f"{module}:{action}"
        if "*:*" not in permissions and required not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires {required}",
            )
    return _check


async def log_audit(
    db: AsyncSession,
    tenant_id: str,
    user: dict,
    action: str,
    module: str,
    entity_type: str = None,
    entity_id: str = None,
    entity_name: str = None,
    old_values: dict = None,
    new_values: dict = None,
    request: Request = None,
    status: str = "success",
    error_message: str = None,
):
    """Write an audit log entry."""
    user_id = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
    user_email = user.get("email") if isinstance(user, dict) else getattr(user, "email", None)
    
    entry = AuditLog(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        user_email=user_email,
        action=action,
        module=module,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        old_values=old_values,
        new_values=new_values,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        request_id=getattr(request.state, "request_id", None) if request else None,
        status=status,
        error_message=error_message,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    # Don't commit here — let the caller's transaction handle it
