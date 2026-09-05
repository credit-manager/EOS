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
import jwt
from jwt import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

# Test-only secret key — MUST be set explicitly via env.
TEST_SECRET_KEY = os.getenv("EOS_TEST_SECRET_KEY", "")
TEST_ALGORITHM = "HS256"
TEST_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()


def create_test_token(
    tenant_id: str,
    user_id: str = "test-user",
    email: str = "test@example.com",
    roles: Optional[list] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a test JWT token."""
    if not TEST_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="EOS_TEST_SECRET_KEY is not configured",
        )
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=TEST_TOKEN_EXPIRE_MINUTES)
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
    """Verify and decode a test JWT token."""
    if not TEST_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="EOS_TEST_SECRET_KEY is not configured",
        )
    try:
        return jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


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
    """Dependency factory: require a specific permission."""
    async def _check(current_user: Optional[dict] = Depends(optional_get_current_user)):
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        required = f"{module}:{action}"
        if "*:*" in current_user.get("permissions", []):
            return
        if required in current_user.get("permissions", []):
            return
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
    """Resolve designated platform-owner email addresses."""
    raw = os.getenv("EOS_PLATFORM_OWNER_EMAILS", "admin@demo.com")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def require_platform_owner(user: dict = Depends(get_current_user)) -> dict:
    """Allow only explicit platform owners to access the control plane."""
    if "platform_owner" in user.get("roles", []):
        return user
    email = (user.get("email") or "").strip().lower()
    if email and email in _designated_platform_owners():
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Platform owner privileges required",
    )
