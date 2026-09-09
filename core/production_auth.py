"""Production JWT authentication using persistent RS256 key material."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_ALGORITHM = "RS256"
security = HTTPBearer()
_RESERVED_CLAIMS = {"sub", "exp", "iat", "type", "iss", "aud", "jti"}


def _key(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} environment variable is required for production auth")
    return value.replace("\\n", "\n")


def _get_private_key() -> str:
    return _key("EOS_JWT_PRIVATE_KEY")


def _get_public_key() -> str:
    return _key("EOS_JWT_PUBLIC_KEY")


def _get_algorithm() -> str:
    configured = os.getenv("EOS_ALGORITHM", JWT_ALGORITHM).strip()
    if configured != JWT_ALGORITHM:
        raise ValueError(f"Unsupported EOS_ALGORITHM: {configured}; production requires {JWT_ALGORITHM}")
    return JWT_ALGORITHM


def _get_issuer() -> str:
    return os.getenv("EOS_JWT_ISSUER", "eos-dbp").strip() or "eos-dbp"


def _get_audience() -> str:
    return os.getenv("EOS_JWT_AUDIENCE", "eos-api").strip() or "eos-api"


def _get_key_id() -> str:
    return os.getenv("EOS_JWT_KEY_ID", "eos-primary-1").strip() or "eos-primary-1"


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None, extra_data: Optional[dict] = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=30))
    payload = {
        "sub": subject, "exp": expire, "iat": now, "type": "access",
        "iss": _get_issuer(), "aud": _get_audience(), "jti": str(uuid.uuid4()),
    }
    if extra_data:
        payload.update({k: v for k, v in extra_data.items() if k not in _RESERVED_CLAIMS})
    return jwt.encode(payload, _get_private_key(), algorithm=_get_algorithm(), headers={"kid": _get_key_id()})


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _get_public_key(),
            algorithms=[_get_algorithm()],
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
