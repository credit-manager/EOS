from uuid import UUID

from fastapi import Depends, HTTPException, Request

from .auth.security import Principal, require_principal


def _set_context(request: Request, principal: Principal) -> UUID:
    request.state.user_id = principal.user_id
    request.state.tenant_id = principal.tenant_id
    request.state.role = principal.role
    return principal.tenant_id


def require_tenant(request: Request, principal: Principal = Depends(require_principal)) -> UUID:
    return _set_context(request, principal)


def require_admin(request: Request, principal: Principal = Depends(require_principal)) -> UUID:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    return _set_context(request, principal)
