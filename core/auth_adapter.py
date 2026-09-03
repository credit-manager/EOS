"""Authentication adapter shared by test and production modes."""

import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


def _is_production() -> bool:
    """Check if running in production auth mode."""
    mode = os.getenv("EOS_AUTH_MODE", "test").lower()
    return mode == "production"


def _get_production_auth():
    """Lazy import of production auth module."""
    from core.production_auth import (
        security as prod_security,
    )
    from core.production_auth import (
        verify_token as prod_verify_token,
    )
    return prod_security, prod_verify_token


def _get_test_auth():
    """Lazy import of test auth module."""
    from core.auth import (
        security as test_security,
    )
    from core.auth import (
        verify_token as test_verify_token,
    )
    return test_security, test_verify_token


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> dict:
    """Validate bearer credentials and establish server-side tenant context."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    if _is_production():
        from core.production_auth import _get_secret_key, verify_token

        # Verify SECRET_KEY is set (will raise ValueError if not)
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
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    )
) -> dict | None:
    """
    Optional version of get_current_user.

    Returns None when no token is provided.
    Raises HTTPException only when token is provided but invalid.

    Used for NONE entities where auth is not required.
    """
    if credentials is None:
        return None
    return await get_current_user(request, credentials)
