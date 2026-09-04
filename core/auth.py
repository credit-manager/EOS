"""
AUTH MODULE
============

Authentication and authorization dependencies for EOS DBP.
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

load_dotenv()

TEST_SECRET_KEY = os.getenv("EOS_TEST_SECRET_KEY", "")
TEST_ALGORITHM = "HS256"
TEST_TOKEN_EXPIRE_MINUTES = 60
security = HTTPBearer()


def create_test_token(
    tenant_id: str,
    user_id: str = "test-user",
    email: str = "test@example.com",
    roles: list | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a test JWT token for verification/testing only."""
    if not TEST_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="EOS_TEST_SECRET_KEY is not configured",
        )
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=TEST_TOKEN_EXPIRE_MINUTES))
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
    try:
        return jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


from core.auth_adapter import get_current_user, optional_get_current_user

__all__ = [
    "TEST_ALGORITHM",
    "TEST_SECRET_KEY",
    "create_test_token",
    "get_current_user",
    "optional_get_current_user",
    "require_permission",
    "require_platform_owner",
    "verify_test_token",
]


def require_permission(module: str, action: str):
    """Dependency factory requiring a specific permission."""

    async def _check(current_user: dict = Depends(get_current_user)):
        required = f"{module}:{action}"
        if "*:*" in current_user.get("permissions", []):
            return current_user
        if required in current_user.get("permissions", []):
            return current_user
        roles = current_user.get("roles", [])
        for role in roles:
            if role in ("admin", "dynamic_manager"):
                return current_user
            if role == "dynamic_operator" and action in ("read", "create", "update"):
                return current_user
            if role == "dynamic_viewer" and action == "read":
                return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return _check


def _designated_platform_owners() -> set:
    """Resolve the explicit platform-owner email allow-list."""
    raw = os.getenv("EOS_PLATFORM_OWNER_EMAILS", "admin@demo.com")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def require_platform_owner(user: dict = Depends(get_current_user)) -> dict:
    """Allow only explicit platform owners into the control plane."""
    if "platform_owner" in user.get("roles", []):
        return user
    email = (user.get("email") or "").strip().lower()
    if email and email in _designated_platform_owners():
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform owner privileges required")
