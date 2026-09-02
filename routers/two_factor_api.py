"""
P74.9 Two-Factor Authentication — API
======================================
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from core.auth import get_current_user
from core.industry_security import audit_log, success_response
from core.two_factor import (
    disable_2fa,
    enable_2fa,
    get_2fa_status,
    verify_recovery_code,
    verify_totp,
)
from database import get_db

router = APIRouter(prefix="/api/v1/auth/2fa", tags=["Two-Factor Authentication"])


class Enable2FA(BaseModel):
    method: str = Field(default="totp", pattern="^(totp)$")


class Verify2FA(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class VerifyRecovery(BaseModel):
    code: str = Field(min_length=8, max_length=8)


@router.get("/status")
def get_status(user: dict | None=None, db=Depends(get_db)):
    status = get_2fa_status(db, user["id"])
    return success_response("2FA status", status)


@router.post("/enable")
def enable(body: Enable2FA, user: dict | None=None, db=Depends(get_db)):
    result = enable_2fa(db, user["id"], body.method)
    audit_log(db, user["tenant_id"], user["id"], "enable", "2fa", user["id"], new_values={"method": body.method})
    return success_response("2FA enabled. Save your recovery codes.", {
        "secret": result["secret"],
        "recovery_codes": result["recovery_codes"],
        "provisioning_uri": result["provisioning_uri"],
        "method": result["method"],
    })


@router.post("/disable")
def disable(user: dict | None=None, db=Depends(get_db)):
    disable_2fa(db, user["id"])
    audit_log(db, user["tenant_id"], user["id"], "disable", "2fa", user["id"])
    return success_response("2FA disabled")


@router.post("/verify")
def verify(body: Verify2FA, request: Request, user: dict | None=None, db=Depends(get_db)):
    ip = request.client.host if request.client else None
    valid, msg = verify_totp(db, user["id"], body.code, ip)
    if not valid:
        raise HTTPException(status_code=401, detail=msg)
    audit_log(db, user["tenant_id"], user["id"], "verify", "2fa", user["id"])
    return success_response("2FA verified")


@router.post("/verify-recovery")
def verify_recovery(body: VerifyRecovery, request: Request, user: dict | None=None, db=Depends(get_db)):
    ip = request.client.host if request.client else None
    valid, msg = verify_recovery_code(db, user["id"], body.code, ip)
    if not valid:
        raise HTTPException(status_code=401, detail=msg)
    audit_log(db, user["tenant_id"], user["id"], "verify_recovery", "2fa", user["id"])
    return success_response("Recovery code verified")


@router.get("/attempts")
def get_attempts(
    limit: int | None=None,
    user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    rows = db.execute(text(
        "SELECT id, method, success, ip_address, attempted_at "
        "FROM dbp_2fa_attempts WHERE user_id = :uid "
        "ORDER BY attempted_at DESC LIMIT :limit"
    ), {"uid": user["id"], "limit": limit}).fetchall()
    
    data = [{"id": r[0], "method": r[1], "success": r[2], "ip_address": r[3], "attempted_at": str(r[4]) if r[4] else None} for r in rows]
    return success_response("2FA attempts", {"attempts": data, "count": len(data)})
