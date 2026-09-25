from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import permissions
from .auth.models import TenantMembership, User
from .auth.security import Principal, require_principal
from .db import get_db
from .tenant import require_tenant

router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])


@router.get("/roles")
def list_roles(
    principal: Principal = Depends(require_principal),
) -> dict:
    return {"roles": permissions.list_roles()}


@router.get("/my-permissions")
def get_my_permissions(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    role = permissions.get_user_role(principal.user_id, tenant_id, db)
    if not role:
        raise HTTPException(status_code=403, detail="not a member of this tenant")
    
    perms = permissions.get_user_permissions(role)
    return {
        "role": role,
        "permissions": [p.value for p in perms],
    }


@router.get("/users")
def list_user_roles(
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    current_role = permissions.get_user_role(principal.user_id, tenant_id, db)
    if current_role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="insufficient permissions")
    
    memberships = db.scalars(
        select(TenantMembership).where(TenantMembership.tenant_id == tenant_id)
    ).all()
    
    users = []
    for m in memberships:
        user = db.get(User, m.user_id)
        if user:
            users.append({
                "user_id": str(user.id),
                "email": user.email,
                "role": m.role,
                "permissions": [p.value for p in permissions.get_user_permissions(m.role)],
            })
    
    return {"users": users}


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: UUID,
    role: str,
    principal: Principal = Depends(require_principal),
    tenant_id: UUID = Depends(require_tenant),
    db: Session = Depends(get_db),
) -> dict:
    current_role = permissions.get_user_role(principal.user_id, tenant_id, db)
    if current_role != "admin":
        raise HTTPException(status_code=403, detail="only admins can change roles")
    
    if role not in permissions.ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"invalid role: {role}")
    
    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
        )
    )
    
    if not membership:
        raise HTTPException(status_code=404, detail="user not found in this tenant")
    
    membership.role = role
    db.flush()
    
    return {
        "user_id": str(user_id),
        "role": role,
        "permissions": [p.value for p in permissions.get_user_permissions(role)],
    }
