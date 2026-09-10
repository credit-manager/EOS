"""P74.9 Two-Factor Authentication API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from database import get_db
from sqlalchemy import text
from core.auth import get_current_user
from core.industry_security import success_response, audit_log
from core.runtime_config import resolve_auth_mode
from core.two_factor import (
    get_2fa_status, enable_2fa, disable_2fa, is_2fa_enabled,
    verify_totp, verify_recovery_code,
)

router = APIRouter(prefix="/api/v1/auth/2fa", tags=["Two-Factor Authentication"])
_pre_mfa_bearer = HTTPBearer(auto_error=False)


class Enable2FA(BaseModel):
    method: str = Field(default="totp", pattern="^(totp)$")


class Verify2FA(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class VerifyRecovery(BaseModel):
    code: str = Field(min_length=8, max_length=8)


async def get_pre_mfa_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_pre_mfa_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="MFA challenge token required", headers={"WWW-Authenticate": "Bearer"})
    token = credentials.credentials
    try:
        if resolve_auth_mode() == "production":
            from core.production_auth import verify_token
            payload = verify_token(token, expected_type="access")
            user_id = str(payload.get("sub") or "")
            tenant_id = str(payload.get("tenant_id") or "").lower()
            if not user_id or not tenant_id:
                raise HTTPException(status_code=401, detail="Invalid MFA challenge token", headers={"WWW-Authenticate": "Bearer"})
            from database import current_tenant_id, SessionLocal
            current_tenant_id.set(tenant_id)
            db = None
            try:
                db = SessionLocal()
                row = db.execute(text(
                    "SELECT email, role, is_active FROM dbp_users WHERE id=:id AND tenant_id=:tenant_id"
                ), {"id": user_id, "tenant_id": tenant_id}).fetchone()
                if not row or not row[2]:
                    raise HTTPException(status_code=401, detail="Account is inactive or no longer exists")
                return {"id": user_id, "tenant_id": tenant_id, "email": row[0], "roles": [row[1]], "mfa_verified": bool(payload.get("mfa_verified", False))}
            finally:
                if db is not None:
                    db.close()
        from core.auth import verify_test_token
        payload = verify_test_token(token, expected_type="access")
        return {
            "id": str(payload["sub"]),
            "tenant_id": str(payload["tenant_id"]).lower(),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "mfa_verified": bool(payload.get("mfa_verified", False)),
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid MFA challenge token", headers={"WWW-Authenticate": "Bearer"})


def _issue_verified_tokens(db, user: dict) -> tuple[str, str]:
    """Rotate access + refresh credentials after successful MFA."""
    from routers.auth import _issue_refresh_token, _issue_access_token

    db.execute(text(
        "UPDATE dbp_refresh_tokens SET revoked_at=NOW() "
        "WHERE user_id=:uid AND tenant_id=:tid AND mfa_verified=FALSE AND revoked_at IS NULL"
    ), {"uid": user["id"], "tid": user["tenant_id"]})

    result = {
        "user_id": user["id"],
        "tenant_id": user["tenant_id"],
        "email": user.get("email") or "user@example.com",
        "role": (user.get("roles") or ["user"])[0],
    }
    access_token = _issue_access_token(result, mfa_verified=True)
    refresh_token = _issue_refresh_token(
        db, user["id"], user["tenant_id"], mfa_verified=True
    )
    return access_token, refresh_token


@router.get("/status")
def get_status(user: dict = Depends(get_current_user), db=Depends(get_db)):
    status = get_2fa_status(db, user["id"])
    return success_response("2FA status", status)


@router.post("/enable")
def enable(body: Enable2FA, user: dict = Depends(get_current_user), db=Depends(get_db)):
    result = enable_2fa(db, user["id"], body.method)
    audit_log(db, user["tenant_id"], user["id"], "enable", "2fa", user["id"], new_values={"method": body.method})
    return success_response("2FA enabled. Save your recovery codes.", {
        "secret": result["secret"], "recovery_codes": result["recovery_codes"],
        "provisioning_uri": result["provisioning_uri"], "method": result["method"],
    })


@router.post("/disable")
def disable(user: dict = Depends(get_current_user), db=Depends(get_db)):
    disable_2fa(db, user["id"])
    audit_log(db, user["tenant_id"], user["id"], "disable", "2fa", user["id"])
    return success_response("2FA disabled")


@router.post("/verify")
def verify(body: Verify2FA, request: Request, user: dict = Depends(get_pre_mfa_user), db=Depends(get_db)):
    if not is_2fa_enabled(db, user["id"]):
        raise HTTPException(status_code=409, detail="2FA is not enabled for this account")
    ip = request.client.host if request.client else None
    valid, msg = verify_totp(db, user["id"], body.code, ip)
    if not valid:
        raise HTTPException(status_code=401, detail=msg)
    access_token, refresh_token = _issue_verified_tokens(db, user)
    audit_log(db, user["tenant_id"], user["id"], "verify", "2fa", user["id"])
    db.commit()
    return success_response("2FA verified", {
        "access_token": access_token, "refresh_token": refresh_token,
        "token_type": "bearer", "expires_in": 1800,
    })


@router.post("/verify-recovery")
def verify_recovery(body: VerifyRecovery, request: Request, user: dict = Depends(get_pre_mfa_user), db=Depends(get_db)):
    if not is_2fa_enabled(db, user["id"]):
        raise HTTPException(status_code=409, detail="2FA is not enabled for this account")
    ip = request.client.host if request.client else None
    valid, msg = verify_recovery_code(db, user["id"], body.code, ip)
    if not valid:
        raise HTTPException(status_code=401, detail=msg)
    access_token, refresh_token = _issue_verified_tokens(db, user)
    audit_log(db, user["tenant_id"], user["id"], "verify_recovery", "2fa", user["id"])
    db.commit()
    return success_response("Recovery code verified", {
        "access_token": access_token, "refresh_token": refresh_token,
        "token_type": "bearer", "expires_in": 1800,
    })


@router.get("/attempts")
def get_attempts(limit: int = Query(20, ge=1, le=100), user: dict = Depends(get_current_user), db=Depends(get_db)):
    rows = db.execute(text(
        "SELECT id, method, success, ip_address, attempted_at "
        "FROM dbp_2fa_attempts WHERE user_id = :uid "
        "ORDER BY attempted_at DESC LIMIT :limit"
    ), {"uid": user["id"], "limit": limit}).fetchall()
    data = [{"id": r[0], "method": r[1], "success": r[2], "ip_address": r[3], "attempted_at": str(r[4]) if r[4] else None} for r in rows]
    return success_response("2FA attempts", {"attempts": data, "count": len(data)})
