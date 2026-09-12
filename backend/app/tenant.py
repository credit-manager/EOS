from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .audit.service import record as audit_record
from .auth.security import Principal, require_principal
from .db import get_db


def _set_context(request: Request, principal: Principal) -> UUID:
    request.state.user_id = principal.user_id
    request.state.tenant_id = principal.tenant_id
    request.state.role = principal.role
    return principal.tenant_id


def require_tenant(request: Request, principal: Principal = Depends(require_principal)) -> UUID:
    return _set_context(request, principal)


def require_admin(
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> UUID:
    if principal.role != "admin":
        audit_record(
            db,
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            action="auth.forbidden",
            resource_type="route",
            resource_id=None,
            metadata={"path": request.url.path, "role": principal.role},
            request_id=getattr(request.state, "request_id", None),
        )
        db.commit()
        raise HTTPException(status_code=403, detail="admin role required")
    return _set_context(request, principal)
