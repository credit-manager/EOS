"""
PRODUCTION AUTHENTICATION
==========================

JWT authentication for production use. The signing secret is read from the
EOS_SECRET_KEY environment variable and is never hardcoded.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


def _get_secret_key() -> str:
    key = os.getenv("EOS_SECRET_KEY")
    if not key:
        raise ValueError(
            "EOS_SECRET_KEY environment variable is required for production auth. "
            "Set it in .env or environment before starting the server."
        )
    return key


def _get_algorithm() -> str:
    return os.getenv("EOS_ALGORITHM", "HS256")


security = HTTPBearer()


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[dict] = None
) -> str:
    """Create a JWT access token for production use."""
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
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get the current authenticated user from a production JWT."""
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
