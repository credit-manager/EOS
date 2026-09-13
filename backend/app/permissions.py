import logging
from enum import StrEnum
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth.models import TenantMembership
from .db import get_db

logger = logging.getLogger("2to-eos.permissions")


class Permission(StrEnum):
    PROJECT_VIEW = "project:view"
    PROJECT_CREATE = "project:create"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"
    
    CONTRACT_VIEW = "contract:view"
    CONTRACT_CREATE = "contract:create"
    CONTRACT_EDIT = "contract:edit"
    CONTRACT_DELETE = "contract:delete"
    
    BOQ_VIEW = "boq:view"
    BOQ_CREATE = "boq:create"
    BOQ_EDIT = "boq:edit"
    
    CLAIM_VIEW = "claim:view"
    CLAIM_CREATE = "claim:create"
    CLAIM_APPROVE = "claim:approve"
    
    PROCUREMENT_VIEW = "procurement:view"
    PROCUREMENT_CREATE = "procurement:create"
    PROCUREMENT_APPROVE = "procurement:approve"
    
    FINANCIAL_VIEW = "financial:view"
    FINANCIAL_CREATE = "financial:create"
    FINANCIAL_APPROVE = "financial:approve"
    
    REPORT_VIEW = "report:view"
    REPORT_EXPORT = "report:export"
    
    USER_VIEW = "user:view"
    USER_MANAGE = "user:manage"
    
    SETTINGS_VIEW = "settings:view"
    SETTINGS_MANAGE = "settings:manage"
    
    AUDIT_VIEW = "audit:view"
    
    NOTIFICATION_VIEW = "notification:view"
    NOTIFICATION_MANAGE = "notification:manage"


ROLE_PERMISSIONS: dict[str, list[Permission]] = {
    "admin": [
        Permission.PROJECT_VIEW,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_EDIT,
        Permission.PROJECT_DELETE,
        Permission.CONTRACT_VIEW,
        Permission.CONTRACT_CREATE,
        Permission.CONTRACT_EDIT,
        Permission.CONTRACT_DELETE,
        Permission.BOQ_VIEW,
        Permission.BOQ_CREATE,
        Permission.BOQ_EDIT,
        Permission.CLAIM_VIEW,
        Permission.CLAIM_CREATE,
        Permission.CLAIM_APPROVE,
        Permission.PROCUREMENT_VIEW,
        Permission.PROCUREMENT_CREATE,
        Permission.PROCUREMENT_APPROVE,
        Permission.FINANCIAL_VIEW,
        Permission.FINANCIAL_CREATE,
        Permission.FINANCIAL_APPROVE,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.USER_VIEW,
        Permission.USER_MANAGE,
        Permission.SETTINGS_VIEW,
        Permission.SETTINGS_MANAGE,
        Permission.AUDIT_VIEW,
        Permission.NOTIFICATION_VIEW,
        Permission.NOTIFICATION_MANAGE,
    ],
    "manager": [
        Permission.PROJECT_VIEW,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_EDIT,
        Permission.CONTRACT_VIEW,
        Permission.CONTRACT_CREATE,
        Permission.CONTRACT_EDIT,
        Permission.BOQ_VIEW,
        Permission.BOQ_CREATE,
        Permission.BOQ_EDIT,
        Permission.CLAIM_VIEW,
        Permission.CLAIM_CREATE,
        Permission.CLAIM_APPROVE,
        Permission.PROCUREMENT_VIEW,
        Permission.PROCUREMENT_CREATE,
        Permission.PROCUREMENT_APPROVE,
        Permission.FINANCIAL_VIEW,
        Permission.FINANCIAL_CREATE,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.USER_VIEW,
        Permission.NOTIFICATION_VIEW,
    ],
    "member": [
        Permission.PROJECT_VIEW,
        Permission.CONTRACT_VIEW,
        Permission.BOQ_VIEW,
        Permission.CLAIM_VIEW,
        Permission.CLAIM_CREATE,
        Permission.PROCUREMENT_VIEW,
        Permission.PROCUREMENT_CREATE,
        Permission.FINANCIAL_VIEW,
        Permission.REPORT_VIEW,
        Permission.NOTIFICATION_VIEW,
    ],
    "viewer": [
        Permission.PROJECT_VIEW,
        Permission.CONTRACT_VIEW,
        Permission.BOQ_VIEW,
        Permission.CLAIM_VIEW,
        Permission.PROCUREMENT_VIEW,
        Permission.FINANCIAL_VIEW,
        Permission.REPORT_VIEW,
        Permission.NOTIFICATION_VIEW,
    ],
}


def get_user_permissions(role: str) -> list[Permission]:
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(role: str, permission: Permission) -> bool:
    permissions = get_user_permissions(role)
    return permission in permissions


def require_permission(permission: Permission):
    async def _check(
        request: Request,
        db: Session = Depends(get_db),
    ):
        user_id = getattr(request.state, "user_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        
        if not user_id or not tenant_id:
            raise HTTPException(status_code=401, detail="authentication required")
        
        membership = db.scalar(
            select(TenantMembership).where(
                TenantMembership.user_id == user_id,
                TenantMembership.tenant_id == tenant_id,
            )
        )
        
        if not membership:
            raise HTTPException(status_code=403, detail="tenant membership not found")
        
        if not has_permission(membership.role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"permission denied: {permission.value}",
            )
        
        return membership.role
    
    return _check


def get_user_role(
    user_id: UUID,
    tenant_id: UUID,
    db: Session,
) -> str | None:
    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
        )
    )
    return membership.role if membership else None


def list_roles() -> dict[str, list[str]]:
    return {
        role: [p.value for p in permissions]
        for role, permissions in ROLE_PERMISSIONS.items()
    }
