"""Tenant member administration with explicit tenant boundaries and safety invariants."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from core.auth import get_current_user, require_admin_role
from core.rate_limit import read_limiter, write_limiter
from core.user_engine import UserEngine

router = APIRouter(prefix="/api/v1/members", tags=["Organization Members"])
_ALLOWED_ROLES = {"user", "admin", "manager", "viewer", "operator", "dynamic_manager", "dynamic_operator", "dynamic_viewer"}


def _tenant(user: dict) -> str:
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(403, "Tenant context is required")
    return tenant_id


def _guard_self(user: dict, target_id: str) -> None:
    if user.get("id") == target_id:
        raise HTTPException(409, "You cannot modify your own membership through this endpoint")


def _ensure_not_last_admin(db: Session, tenant_id: str, target_id: str) -> None:
    target = db.execute(text("SELECT role, is_active FROM dbp_users WHERE id = :id AND tenant_id = :tid FOR UPDATE"),
                        {"id": target_id, "tid": tenant_id}).fetchone()
    if not target:
        raise HTTPException(404, "Member not found")
    if target[0] == "admin" and target[1]:
        count = db.execute(text("SELECT COUNT(*) FROM dbp_users WHERE tenant_id = :tid AND role = 'admin' AND is_active = true"),
                           {"tid": tenant_id}).scalar() or 0
        if count <= 1:
            raise HTTPException(409, "The organization must retain at least one active administrator")


@router.get("", dependencies=[Depends(read_limiter.check)])
async def list_members(user: dict = Depends(require_admin_role), db: Session = Depends(get_db)):
    tid = _tenant(user)
    rows = db.execute(text(
        "SELECT id, email, first_name, last_name, role, is_active, email_verified, "
        "verification_expires_at, last_login_at, created_at FROM dbp_users "
        "WHERE tenant_id = :tid ORDER BY created_at DESC"
    ), {"tid": tid}).fetchall()
    return {"status": "success", "data": [
        {"id": r[0], "email": r[1], "first_name": r[2], "last_name": r[3], "role": r[4],
         "is_active": bool(r[5]), "email_verified": bool(r[6]),
         "invitation_pending": not bool(r[6]) and r[7] is not None,
         "last_login_at": str(r[8]) if r[8] else None, "created_at": str(r[9]) if r[9] else None}
        for r in rows
    ]}


@router.patch("/{member_id}/role", dependencies=[Depends(write_limiter.check)])
async def change_member_role(member_id: str, body: dict, user: dict = Depends(require_admin_role), db: Session = Depends(get_db)):
    tid = _tenant(user)
    _guard_self(user, member_id)
    role = str(body.get("role") or "").strip()
    if role not in _ALLOWED_ROLES:
        raise HTTPException(400, "Invalid member role")
    if role != "admin":
        _ensure_not_last_admin(db, tid, member_id)
    result = UserEngine(db).change_role(member_id, tid, role)
    if not result["success"]:
        db.rollback()
        raise HTTPException(404, result["error"])
    db.commit()
    return {"status": "success", "data": {"message": "Member role changed", "role": role}}


@router.post("/{member_id}/deactivate", dependencies=[Depends(write_limiter.check)])
async def deactivate_member(member_id: str, user: dict = Depends(require_admin_role), db: Session = Depends(get_db)):
    tid = _tenant(user)
    _guard_self(user, member_id)
    _ensure_not_last_admin(db, tid, member_id)
    result = UserEngine(db).deactivate_user(member_id, tid)
    if not result["success"]:
        db.rollback()
        raise HTTPException(404, result["error"])
    db.commit()
    return {"status": "success", "data": {"message": "Member deactivated"}}


@router.post("/{member_id}/reactivate", dependencies=[Depends(write_limiter.check)])
async def reactivate_member(member_id: str, user: dict = Depends(require_admin_role), db: Session = Depends(get_db)):
    tid = _tenant(user)
    _guard_self(user, member_id)
    result = db.execute(text("UPDATE dbp_users SET is_active = true, updated_at = NOW() WHERE id = :id AND tenant_id = :tid"),
                        {"id": member_id, "tid": tid})
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(404, "Member not found")
    db.commit()
    return {"status": "success", "data": {"message": "Member reactivated"}}


@router.delete("/{member_id}/invitation", dependencies=[Depends(write_limiter.check)])
async def revoke_invitation(member_id: str, user: dict = Depends(require_admin_role), db: Session = Depends(get_db)):
    tid = _tenant(user)
    row = db.execute(text(
        "SELECT id, email_verified FROM dbp_users WHERE id = :id AND tenant_id = :tid FOR UPDATE"
    ), {"id": member_id, "tid": tid}).fetchone()
    if not row:
        raise HTTPException(404, "Member not found")
    if row[1]:
        raise HTTPException(409, "The member has already accepted the invitation")
    result = db.execute(text(
        "UPDATE dbp_users SET is_active = false, verification_token_hash = NULL, "
        "verification_expires_at = NULL, updated_at = NOW() WHERE id = :id AND tenant_id = :tid"
    ), {"id": member_id, "tid": tid})
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(404, "Invitation not found")
    db.commit()
    return {"status": "success", "data": {"message": "Invitation revoked"}}
