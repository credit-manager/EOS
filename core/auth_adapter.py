"""
AUTH ADAPTER
=============

Switches between test and production authentication
based on environment configuration.

Usage:
    from core.auth_adapter import get_current_user, optional_get_current_user

Rules:
    - EOS_AUTH_MODE=production → uses production_auth.py
    - EOS_AUTH_MODE=test (or unset) → uses test auth (core/auth.py)
    - No fallback from production secret to test secret
    - Same return format in both modes
"""

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
    credentials: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=False)
    )
) -> dict:
    """
    Get current authenticated user.

    Production mode:
        - Uses EOS_SECRET_KEY from environment
        - Raises 401 if SECRET_KEY not set

    Test mode:
        - Uses hardcoded TEST_SECRET_KEY
        - For verification/testing only
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if _is_production():
        from core.production_auth import _get_secret_key, verify_token

        # Verify SECRET_KEY is set (will raise ValueError if not)
        try:
            _get_secret_key()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

        payload = verify_token(credentials.credentials)

    else:
        from core.auth import verify_test_token as verify_token

        payload = verify_token(credentials.credentials)

    # Extract user info (same format for both modes)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant ID",
        )

    # Bind the authenticated tenant into the DB context so RLS policies
    # (app.tenant_id) are applied to every query in this request.
    from database import current_tenant_id
    current_tenant_id.set(str(tenant_id).lower())

    return {
        "id": user_id,
        "tenant_id": tenant_id.lower(),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }


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

    return await get_current_user(credentials)
