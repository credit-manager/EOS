"""
AUTH ADAPTER
=============

Switches between test and production authentication based on the central runtime
configuration. Production authentication additionally re-checks the user's
current database state so deactivation, role changes and MFA state take effect
without waiting for JWT expiry.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.runtime_config import resolve_auth_mode


def _is_production() -> bool:
    return resolve_auth_mode() == "production"


def _load_identity(payload: dict) -> tuple[str, str, str | None, list, bool]:
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token missing user ID")
    if tenant_id is None:
        raise HTTPException(status_code=401, detail="Token missing tenant ID")
    return str(user_id), str(tenant_id).lower(), payload.get("email"), payload.get("roles", []), bool(payload.get("mfa_verified", False))


async def _authenticate(credentials: HTTPAuthorizationCredentials, enforce_mfa: bool = True) -> dict:
    production = _is_production()
    if production:
        from core.production_auth import verify_token
        try:
            payload = verify_token(credentials.credentials, expected_type="access")
        except HTTPException:
            raise
        except ValueError:
            raise HTTPException(status_code=500, detail="Production authentication is not configured")
    else:
        from core.auth import verify_test_token
        payload = verify_test_token(credentials.credentials)

    user_id, tenant_id, email, roles, mfa_verified = _load_identity(payload)

    if production:
        from database import SessionLocal, current_tenant_id
        current_tenant_id.set(tenant_id)
        db = SessionLocal()
        try:
            from sqlalchemy import text
            row = db.execute(text(
                "SELECT email, role, is_active FROM dbp_users WHERE id=:id AND tenant_id=:tenant_id"
            ), {"id": user_id, "tenant_id": tenant_id}).fetchone()
            if not row or not row[2]:
                raise HTTPException(status_code=401, detail="Account is inactive or no longer exists")

            if enforce_mfa:
                mfa_row = db.execute(text(
                    "SELECT 1 FROM dbp_2fa_settings WHERE user_id=:id AND is_enabled=TRUE"
                ), {"id": user_id}).fetchone()
                if mfa_row and not mfa_verified:
                    raise HTTPException(status_code=401, detail="MFA verification required", headers={"WWW-Authenticate": "Bearer"})
        finally:
            db.close()
        email = row[0]
        roles = [row[1]]

    from database import current_tenant_id
    current_tenant_id.set(tenant_id)
    return {"id": user_id, "tenant_id": tenant_id, "email": email, "roles": roles, "mfa_verified": mfa_verified}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return await _authenticate(credentials, enforce_mfa=True)


async def get_mfa_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> dict:
    """Authenticate an access token for the MFA endpoints without authorizing application APIs."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return await _authenticate(credentials, enforce_mfa=False)


async def optional_get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    if credentials is None:
        return None
    return await get_current_user(credentials)
