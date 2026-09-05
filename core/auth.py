"""
AUTH MODULE
============

Authentication helpers and authorization dependencies.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from dotenv import load_dotenv
import jwt
from jwt import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

load_dotenv()

TEST_SECRET_KEY = os.getenv("EOS_TEST_SECRET_KEY", "")
TEST_ALGORITHM = "HS256"
TEST_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()


def create_test_token(
    tenant_id: str,
    user_id: str = "test-user",
    email: str = "test@example.com",
    roles: Optional[list] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a test JWT token."""
    if not TEST_SECRET_KEY:
        raise HTTPException(status_code=500, detail="EOS_TEST_SECRET_KEY is not configured")
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=TEST_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "access",
        "tenant_id": tenant_id.lower(),
        "email": email,
        "roles": roles or ["user"],
    }
    return jwt.encode(payload, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)


def verify_test_token(token: str) -> dict:
    """Verify and decode a test JWT token."""
    if not TEST_SECRET_KEY:
        raise HTTPException(status_code=500, detail="EOS_TEST_SECRET_KEY is not configured")
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
    "require_admin_role",
    "require_platform_owner",
    "TEST_SECRET_KEY",
    "TEST_ALGORITHM",
]


def _roles(user: Optional[dict]) -> set[str]:
    if not user:
        return set()
    return {
        r.get("permission") if isinstance(r, dict) else r
        for r in user.get("roles", [])
    } | set(user.get("roles", []))


def require_permission(module: str, action: str):
    """Dependency factory: require a module/action permission."""
    async def _check(current_user: Optional[dict] = Depends(optional_get_current_user)):
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
        required = f"{module}:{action}"
        permissions = current_user.get("permissions", [])
        roles = _roles(current_user)
        if "*:*" in permissions or required in permissions:
            return current_user
        if "admin" in roles or "dynamic_manager" in roles:
            return current_user
        if "dynamic_operator" in roles and action in ("read", "create", "update"):
            return current_user
        if "dynamic_viewer" in roles and action == "read":
            return current_user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return _check


async def require_admin_role(user: dict = Depends(get_current_user)) -> dict:
    """Require tenant administrator privileges for security-sensitive user management."""
    roles = _roles(user)
    if "admin" not in roles and "platform_owner" not in roles:
        raise HTTPException(status_code=403, detail="Administrator privileges required")
    return user


def _designated_platform_owners() -> set:
    """Resolve explicitly configured platform-owner email addresses.

    There is deliberately no built-in/default owner account or email.
    """
    raw = os.getenv("EOS_PLATFORM_OWNER_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def require_platform_owner(user: dict = Depends(get_current_user)) -> dict:
    """Allow only explicit platform owners to access the control plane."""
    if "platform_owner" in _roles(user):
        return user
    email = (user.get("email") or "").strip().lower()
    if email and email in _designated_platform_owners():
        return user
    raise HTTPException(status_code=403, detail="Platform owner privileges required")
