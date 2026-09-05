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

# Kept for backwards compatibility with callers importing this symbol. JWT
# signing/verification below resolves the environment value at call time so
# test application imports cannot retain a stale secret from an earlier env.
TEST_SECRET_KEY = os.getenv("EOS_TEST_SECRET_KEY", "")
TEST_ALGORITHM = "HS256"
TEST_TOKEN_EXPIRE_MINUTES = 60
security = HTTPBearer()


def _get_test_secret_key() -> str:
    secret = os.getenv("EOS_TEST_SECRET_KEY", "").strip()
    if not secret:
        raise HTTPException(status_code=500, detail="EOS_TEST_SECRET_KEY is not configured")
    return secret


def create_test_token(tenant_id: str, user_id: str = "test-user", email: str = "test@example.com", roles: Optional[list] = None, expires_delta: Optional[timedelta] = None) -> str:
    secret_key = _get_test_secret_key()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=TEST_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": user_id, "exp": expire, "iat": now, "type": "access", "tenant_id": tenant_id.lower(), "email": email, "roles": roles or ["user"]}
    return jwt.encode(payload, secret_key, algorithm=TEST_ALGORITHM)


def verify_test_token(token: str) -> dict:
    secret_key = _get_test_secret_key()
    try:
        return jwt.decode(token, secret_key, algorithms=[TEST_ALGORITHM])
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})


from core.auth_adapter import get_current_user, optional_get_current_user

__all__ = ["create_test_token", "verify_test_token", "get_current_user", "optional_get_current_user", "require_permission", "require_admin_role", "require_platform_owner", "TEST_SECRET_KEY", "TEST_ALGORITHM"]


def _roles(user: Optional[dict]) -> set[str]:
    """Normalize role strings while tolerating legacy dict-shaped role entries."""
    if not user:
        return set()
    result = {str(r) for r in user.get("roles", []) if isinstance(r, str)}
    result.update(str(r.get("permission")) for r in user.get("roles", []) if isinstance(r, dict) and r.get("permission"))
    return result


def require_permission(module: str, action: str):
    async def _check(current_user: Optional[dict] = Depends(optional_get_current_user)):
        if current_user is None:
            raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
        required = f"{module}:{action}"
        permissions = current_user.get("permissions", [])
        roles = _roles(current_user)
        if "*:*" in permissions or required in permissions or "admin" in roles or "dynamic_manager" in roles:
            return current_user
        if "dynamic_operator" in roles and action in ("read", "create", "update"):
            return current_user
        if "dynamic_viewer" in roles and action == "read":
            return current_user
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return _check


async def require_admin_role(user: dict = Depends(get_current_user)) -> dict:
    """Require tenant administrator privileges for security-sensitive user management."""
    if not ({"admin", "platform_owner"} & _roles(user)):
        raise HTTPException(status_code=403, detail="Administrator privileges required")
    return user


def _designated_platform_owners() -> set:
    raw = os.getenv("EOS_PLATFORM_OWNER_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def require_platform_owner(user: dict = Depends(get_current_user)) -> dict:
    if "platform_owner" in _roles(user):
        return user
    email = (user.get("email") or "").strip().lower()
    if email and email in _designated_platform_owners():
        return user
    raise HTTPException(status_code=403, detail="Platform owner privileges required")
