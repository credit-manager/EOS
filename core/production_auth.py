"""
PRODUCTION AUTHENTICATION
==========================

This module provides JWT-based authentication for
production use. It reads SECRET_KEY from environment.

DO NOT import this module in tests.
DO NOT hardcode secrets here.
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt


def _get_secret_key() -> str:
    """
    Get SECRET_KEY from environment.

    Raises ValueError if not set.
    This prevents accidental use of test auth in production.
    """
    key = os.getenv("EOS_SECRET_KEY")
    if not key:
        raise ValueError(
            "EOS_SECRET_KEY environment variable is required for production auth. "
            "Set it in .env or environment before starting the server."
        )
    return key


def _get_algorithm() -> str:
    return os.getenv("EOS_ALGORITHM", "HS256")


# Bearer Token extractor
security = HTTPBearer()


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_data: dict | None = None
) -> str:
    """Create a JWT access token for production use."""
    secret_key = _get_secret_key()
    algorithm = _get_algorithm()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)

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
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm]
        )
        return payload
    except JWTError:
        # Never expose JWT error details to client
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials=None
) -> dict:
    """
    Get current authenticated user from production JWT token.

    Returns:
        {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "roles": roles
        }
    """
    payload = verify_token(credentials.credentials)

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

    return {
        "id": user_id,
        "tenant_id": tenant_id.lower(),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }
