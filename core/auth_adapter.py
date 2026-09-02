"""Authentication adapter shared by test and production modes."""

import os
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


def _is_production() -> bool:
    return os.getenv("EOS_AUTH_MODE", "test").lower() == "production"


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> dict:
    """Validate bearer credentials and establish server-side tenant context."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    if _is_production():
        from core.production_auth import verify_token, _get_secret_key
        try:
            _get_secret_key()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
        payload = verify_token(credentials.credentials)
    else:
        from core.auth import verify_test_token
        payload = verify_test_token(credentials.credentials)

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user ID")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing tenant ID")

    tenant_id = str(tenant_id).lower()
    user = {
        "id": str(user_id),
        "tenant_id": tenant_id,
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }

    # Server-side state only. The effective tenant is never read from X-Tenant-ID.
    request.state.user = user
    request.state.tenant_id = tenant_id
    from database import current_tenant_id
    current_tenant_id.set(tenant_id)
    return user


async def optional_get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Optional[dict]:
    if credentials is None:
        return None
    return await get_current_user(request, credentials)
