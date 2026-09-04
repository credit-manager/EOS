"""
PRODUCTION AUTHENTICATION
==========================

JWT-based production authentication. Secrets are read only from the
runtime environment; no credentials are embedded in source code.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError


def _get_secret_key() -> str:
    """Return the production signing key or fail closed."""
    key = os.getenv("EOS_SECRET_KEY")
    if not key:
        raise ValueError(
            "EOS_SECRET_KEY environment variable is required for production auth. "
            "Set it in the runtime environment before starting the server."
        )
    return key


def _get_algorithm() -> str:
    return os.getenv("EOS_ALGORITHM", "HS256")


security = HTTPBearer()


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_data: dict | None = None,
) -> str:
    """Create a short-lived access token for production use."""
    secret_key = _get_secret_key()
    algorithm = _get_algorithm()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=30)
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_data:
        payload.update(extra_data)
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def verify_token(token: str) -> dict:
    """Verify and decode a production JWT token."""
    secret_key = _get_secret_key()
    algorithm = _get_algorithm()
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = None,
) -> dict:
    """Extract the authenticated production principal from a bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(credentials.credentials)
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token missing user ID")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Token missing tenant ID")
    return {
        "id": user_id,
        "tenant_id": str(tenant_id).lower(),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }
