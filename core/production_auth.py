"""Production JWT authentication with explicit issuer, audience and algorithm."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SUPPORTED_JWT_ALGORITHMS = frozenset({"HS256", "RS256"})
JWT_ALGORITHM = "HS256"
security = HTTPBearer()
_RESERVED_CLAIMS = {"sub", "exp", "iat", "type", "iss", "aud", "jti"}


def _get_algorithm() -> str:
    configured = os.getenv("EOS_ALGORITHM", JWT_ALGORITHM).strip().upper() or JWT_ALGORITHM
    if configured not in SUPPORTED_JWT_ALGORITHMS:
        raise ValueError(
            f"Unsupported EOS_ALGORITHM: {configured}; expected one of {sorted(SUPPORTED_JWT_ALGORITHMS)}"
        )
    return configured


def _get_secret_key() -> str:
    key = os.getenv("EOS_SECRET_KEY", "").strip()
    if len(key) < 32:
        raise ValueError("EOS_SECRET_KEY must be at least 32 characters for HS256")
    return key


def _get_private_key() -> str:
    key = os.getenv("EOS_JWT_PRIVATE_KEY", "").strip()
    if not key:
        raise ValueError("EOS_JWT_PRIVATE_KEY is required for RS256 production auth")
    return key


def _get_public_key() -> str:
    key = os.getenv("EOS_JWT_PUBLIC_KEY", "").strip()
    if not key:
        raise ValueError("EOS_JWT_PUBLIC_KEY is required for RS256 production auth")
    return key


def _get_signing_key() -> str:
    algorithm = _get_algorithm()
    return _get_secret_key() if algorithm == "HS256" else _get_private_key()


def _get_verification_key() -> str:
    algorithm = _get_algorithm()
    return _get_secret_key() if algorithm == "HS256" else _get_public_key()


def _get_issuer() -> str:
    return os.getenv("EOS_JWT_ISSUER", "eos-dbp").strip() or "eos-dbp"


def _get_audience() -> str:
    return os.getenv("EOS_JWT_AUDIENCE", "eos-api").strip() or "eos-api"


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[dict] = None,
) -> str:
    """Create a signed access token using the configured production algorithm."""
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
        payload.update({k: v for k, v in extra_data.items() if k not in _RESERVED_CLAIMS})
    return jwt.encode(payload, _get_signing_key(), algorithm=algorithm)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _get_verification_key(),
            algorithms=[_get_algorithm()],
            issuer=_get_issuer(),
            audience=_get_audience(),
            options={"require": ["exp", "iat", "sub", "iss", "aud", "type", "jti"]},
        )
    except (InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    payload = verify_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token missing user ID")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Token missing tenant ID")
    return {
        "id": str(user_id),
        "tenant_id": str(tenant_id).lower(),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }
