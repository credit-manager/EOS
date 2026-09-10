from uuid import UUID

from fastapi import Depends, Request

from .auth.security import Principal, require_principal


def require_tenant(request: Request, principal: Principal = Depends(require_principal)) -> UUID:
    request.state.user_id = principal.user_id
    request.state.tenant_id = principal.tenant_id
    request.state.role = principal.role
    return principal.tenant_id


def require_admin(request: Request, principal: Principal = Depends(require_principal)) -> UUID:
    if principal.role != "admin":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="admin role required")
    request.state.user_id = principal.user_id
    request.state.tenant_id = principal.tenant_id
    request.state.role = principal.role
    return principal.tenant_id
