"""
AUTH ADAPTER
=============

Switches between test and production authentication based on environment.
Production authentication additionally re-checks the user's current database
state so deactivation and role changes take effect without waiting for JWT expiry.
"""

import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


def _is_production() -> bool:
    return os.getenv("EOS_AUTH_MODE", "test").lower() == "production"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    # Never let a tenant context left by an earlier request influence the
    # authentication lookup for this request. The authenticated tenant is set
    # only after the token and current user record have both been validated.
    from database import current_tenant_id
    current_tenant_id.set(None)

    production = _is_production()
    if production:
        from core.production_auth import verify_token, _get_secret_key
        try:
            _get_secret_key()
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        payload = verify_token(credentials.credentials)
    else:
        from core.auth import verify_test_token as verify_token
        payload = verify_token(credentials.credentials)

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token missing user ID")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Token missing tenant ID")

    tenant_id = str(tenant_id).lower()
    email = payload.get("email")
    roles = payload.get("roles", [])

    if production:
        # Access JWTs are intentionally short-lived, but deactivation and
        # privilege changes must take effect immediately. Query before setting
        # the request RLS context it is establishing.
        from database import SessionLocal
        db = SessionLocal()
        try:
            from sqlalchemy import text
            row = db.execute(text(
                "SELECT email, role, is_active FROM dbp_users WHERE id = :id AND tenant_id = :tenant_id"
            ), {"id": user_id, "tenant_id": tenant_id}).fetchone()
        finally:
            db.close()
        if not row or not row[2]:
            raise HTTPException(status_code=401, detail="Account is inactive or no longer exists")
        email = row[0]
        roles = [row[1]]

    current_tenant_id.set(tenant_id)
    return {"id": user_id, "tenant_id": tenant_id, "email": email, "roles": roles}


async def optional_get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    if credentials is None:
        return None
    return await get_current_user(credentials)
