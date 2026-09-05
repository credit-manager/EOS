"""Production JWT authentication with explicit issuer, audience and algorithm."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from jwt import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_ALGORITHM = "HS256"
security = HTTPBearer()


def _get_secret_key() -> str:
    key = os.getenv("EOS_SECRET_KEY")
    if not key:
        raise ValueError("EOS_SECRET_KEY environment variable is required for production auth")
    if len(key) < 32:
        raise ValueError("EOS_SECRET_KEY must be at least 32 characters")
    return key


def _get_algorithm() -> str:
    configured = os.getenv("EOS_ALGORITHM", JWT_ALGORITHM)
    if configured != JWT_ALGORITHM:
        raise ValueError(f"Unsupported EOS_ALGORITHM: {configured}; production requires {JWT_ALGORITHM}")
    return JWT_ALGORITHM


def _get_issuer() -> str:
    return os.getenv("EOS_JWT_ISSUER", "eos-dbp")


def _get_audience() -> str:
    return os.getenv("EOS_JWT_AUDIENCE", "eos-api")


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None, extra_data: Optional[dict] = None) -> str:
    secret_key = _get_secret_key()
    algorithm = _get_algorithm()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=30))
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "access",
        "iss": _get_issuer(),
        "aud": _get_audience(),
        "jti": str(uuid.uuid4()),
    }
    if extra_data:
        payload.update(extra_data)
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def verify_token(token: str) -> dict:
    try:
        secret_key = _get_secret_key()
        algorithm = _get_algorithm()
        return jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            issuer=_get_issuer(),
            audience=_get_audience(),
            options={"require": ["exp", "iat", "sub", "iss", "aud", "type", "jti"]},
        )
    except (InvalidTokenError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = verify_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token missing user ID")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Token missing tenant ID")
    return {"id": user_id, "tenant_id": str(tenant_id).lower(), "email": payload.get("email"), "roles": payload.get("roles", [])}
