"""
EOS System — Security Module
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.tenancy import normalize_tenant_id

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer Token
security = HTTPBearer()


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None, extra_data: Optional[dict] = None) -> str:
    """Create a JWT access token.

    The tenant_id claim is canonicalized at mint time so every token in
    circulation carries the lowercase form regardless of what callers pass.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }

    if extra_data:
        extra_data = dict(extra_data)
        if "tenant_id" in extra_data:
            canonical = normalize_tenant_id(extra_data["tenant_id"])
            if canonical is None:
                raise ValueError(f"Refusing to mint token with invalid tenant_id: {extra_data['tenant_id']!r}")
            extra_data["tenant_id"] = canonical
        to_encode.update(extra_data)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_cors_origins() -> list[str]:
    """Get CORS allowed origins."""
    return settings.CORS_ORIGINS


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current authenticated user from JWT token.

    Tenant security policy:
    1. Tokens without a tenant_id claim are REJECTED (401) — an empty or
       missing tenant can never be treated as valid context.
    2. The tenant_id claim is canonicalized via the shared normalizer.
    3. If the request carries a tenant context (URL path segment or
       X-Tenant-ID header, canonicalized by TenantMiddleware), it must match
       the token's tenant — mismatch is a cross-tenant access attempt (403).
    """
    payload = verify_token(credentials.credentials)

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    raw_tenant_id = payload.get("tenant_id")
    if raw_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant ID",
        )

    tenant_id = normalize_tenant_id(raw_tenant_id)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token contains invalid tenant ID",
        )

    # Enforce JWT <-> request consistency when middleware extracted a tenant.
    request_tenant_id = getattr(request.state, "tenant_id", None)
    if request_tenant_id and request_tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant mismatch between token and request",
        )

    return {
        "id": user_id,
        "tenant_id": tenant_id,
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
    }
