"""
AUTH MODULE
============

This module provides:
1. Test authentication functions (for verification/testing)
2. Delegation to auth_adapter for get_current_user

The auth_adapter switches between test and production auth
based on EOS_AUTH_MODE environment variable.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from dotenv import load_dotenv
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

# Test-only secret key — MUST be set explicitly via env.
# H3 FIX: No hardcoded fallback key. If EOS_TEST_SECRET_KEY is not set,
# test token creation/verification raises instead of using a known default.
TEST_SECRET_KEY = os.getenv("EOS_TEST_SECRET_KEY", "")
TEST_ALGORITHM = "HS256"
TEST_TOKEN_EXPIRE_MINUTES = 60

# Bearer Token extractor
security = HTTPBearer()


def create_test_token(
    tenant_id: str,
    user_id: str = "test-user",
    email: str = "test@example.com",
    roles: Optional[list] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a test JWT token.

    This is for verification/testing only.
    The tenant_id embedded in the token is the
    AUTHENTICATED TENANT — the source of truth
    for tenant isolation.
    """
    if not TEST_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="EOS_TEST_SECRET_KEY is not configured",
        )
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=TEST_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "tenant_id": tenant_id.lower(),
        "email": email,
        "roles": roles or ["user"],
    }

    return jwt.encode(payload, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)


def verify_test_token(token: str) -> dict:
    """
    Verify and decode a test JWT token.

    Returns the full payload including tenant_id.
    Raises HTTPException on invalid/expired token.
    """
    try:
        payload = jwt.decode(
            token,
            TEST_SECRET_KEY,
            algorithms=[TEST_ALGORITHM]
        )
        return payload
    except JWTError:
        # Never expose JWT error details to client
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Delegate to auth_adapter for get_current_user
# This allows switching between test and production auth
# via EOS_AUTH_MODE environment variable
from core.auth_adapter import get_current_user, optional_get_current_user

__all__ = [
    "create_test_token",
    "verify_test_token",
    "get_current_user",
    "optional_get_current_user",
    "require_permission",
    "require_platform_owner",
    "TEST_SECRET_KEY",
    "TEST_ALGORITHM",
]


def require_permission(module: str, action: str):
    """
    Dependency factory: require a specific permission.
    
    Usage:
        @router.post("/accounts", dependencies=[Depends(require_permission("dynamic", "create"))])
    """
    async def _check(current_user: Optional[dict] = Depends(optional_get_current_user)):
        # H2 FIX: Never bypass auth. A permission requirement implies the
        # caller must be authenticated. Previously a missing token (None user)
        # fell through and accessed the endpoint without any permission check.
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        required = f"{module}:{action}"
        
        # Check if user has wildcard permission
        if "*:*" in current_user.get("permissions", []):
            return
        
        # Check direct permissions
        if required in current_user.get("permissions", []):
            return
        
        # Check roles for permission (test mode fallback)
        roles = current_user.get("roles", [])
        for role in roles:
            if role == "admin":
                return
            if role == "dynamic_manager":
                return
            if role == "dynamic_operator" and action in ("read", "create", "update"):
                return
            if role == "dynamic_viewer" and action == "read":
                return
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return _check


def _designated_platform_owners() -> set:
    """Resolve the set of designated platform-owner email addresses.

    Read from EOS_PLATFORM_OWNER_EMAILS (comma-separated). Defaults to the
    demo platform admin. This is an EXPLICIT allow-list independent of the
    generic 'admin' role, so a tenant admin cannot access the control plane
    merely by holding the 'admin' role.
    """
    raw = os.getenv("EOS_PLATFORM_OWNER_EMAILS", "admin@demo.com")
    owners = {e.strip().lower() for e in raw.split(",") if e.strip()}
    return owners


async def require_platform_owner(user: dict = Depends(get_current_user)) -> dict:
    """
    Platform Owner dependency for the Owner Control Plane (/api/v1/control).

    Grants access ONLY to:
      1. users whose token carries the 'platform_owner' role, OR
      2. users explicitly listed as designated platform owners (email).

    The generic 'admin'/'tenant_admin' role is NOT sufficient — this closes the
    vulnerability where any tenant admin could impersonate/manage other tenants.
    Returns the authenticated user dict on success, 403 otherwise.
    """
    if "platform_owner" in user.get("roles", []):
        return user

    email = (user.get("email") or "").strip().lower()
    if email and email in _designated_platform_owners():
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Platform owner privileges required",
    )
