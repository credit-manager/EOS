"""Organization user invitation endpoints.

Invitations are tenant-scoped, administrator-only, single-use tokens and are
sent through the configured EOS email provider. The invite recipient chooses
an initial password through the invitation link; no password is emailed.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from core.auth import get_current_user, require_admin_role
from core.email_adapter import get_email_service
from core.user_engine import UserEngine, _hash_token, pwd_context
from core.rate_limit import auth_limiter, write_limiter

router = APIRouter(prefix="/api/v1/invitations", tags=["Organization Invitations"])
_INVITE_EXPIRE_HOURS = 72


def _err(status: int, code: str, message: str):
    return HTTPException(status_code=status, detail={"status": "error", "error": {"code": code, "message": message}})


def _invite_email(invite_url: str, first_name: str, company_name: str) -> dict:
    return {
        "subject": f"You have been invited to {company_name} on EOS",
        "html": f"""
        <div style=\"font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px\">
          <h2 style=\"color:#2563eb\">You're invited to {company_name}</h2>
          <p>Hello {first_name},</p>
          <p>An administrator invited you to join <strong>{company_name}</strong> on EOS.</p>
          <p>Use the button below to accept the invitation and choose your password.</p>
          <p style=\"text-align:center;margin:32px 0\">
            <a href=\"{invite_url}\" style=\"background:#2563eb;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold\">Accept Invitation</a>
          </p>
          <p style=\"color:#666;font-size:12px\">This invitation expires in 72 hours and can only be used once. If you were not expecting this invitation, you can ignore this email.</p>
        </div>
        """,
        "text": f"You have been invited to {company_name} on EOS. Accept your invitation: {invite_url}",
    }


@router.post("", dependencies=[Depends(auth_limiter.check), Depends(write_limiter.check)])
async def invite_user(
    body: dict,
    user: dict = Depends(require_admin_role),
    db: Session = Depends(get_db),
):
    email = str(body.get("email") or "").strip().lower()
    first_name = str(body.get("first_name") or "").strip()
    last_name = str(body.get("last_name") or "").strip()
    role = str(body.get("role") or "user").strip()
    if not email or "@" not in email:
        raise _err(400, "INVALID_EMAIL", "A valid email is required")
    if not first_name or not last_name:
        raise _err(400, "MISSING", "first_name and last_name are required")
    if role in {"owner", "super_admin"}:
        raise _err(400, "INVALID_ROLE", "This role cannot be granted through an invitation")

    tenant_id = user["tenant_id"]
    existing = db.execute(
        text("SELECT id, tenant_id FROM dbp_users WHERE email = :email"),
        {"email": email},
    ).fetchone()
    if existing:
        if existing[1] == tenant_id:
            raise _err(409, "ALREADY_MEMBER", "This email is already a member of the organization")
        raise _err(409, "EMAIL_IN_USE", "This email is already registered")

    company = db.execute(
        text("SELECT id, COALESCE(name_en, code) FROM dbp_companies WHERE tenant_id = :tid ORDER BY id LIMIT 1"),
        {"tid": tenant_id},
    ).fetchone()
    if not company:
        raise _err(409, "ORGANIZATION_NOT_READY", "The organization has no company record")

    # Reuse the existing verification-token columns for invitations. The token
    # is stored only as SHA-256 and is never returned to the administrator.
    invite_token = secrets.token_urlsafe(32)
    invite_expires = datetime.now(timezone.utc) + timedelta(hours=_INVITE_EXPIRE_HOURS)
    uid = str(uuid.uuid4())
    unusable_password = pwd_context.hash(secrets.token_urlsafe(32))
    db.execute(
        text(
            "INSERT INTO dbp_users (id, tenant_id, email, password_hash, first_name, last_name, role, "
            "is_active, email_verified, verification_token_hash, verification_expires_at) "
            "VALUES (:id, :tid, :email, :pw, :fn, :ln, :role, true, false, :th, :exp)"
        ),
        {
            "id": uid, "tid": tenant_id, "email": email, "pw": unusable_password,
            "fn": first_name, "ln": last_name, "role": role,
            "th": _hash_token(invite_token), "exp": invite_expires,
        },
    )
    db.flush()

    frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
    tpl = _invite_email(f"{frontend_url}/accept-invitation?token={invite_token}", first_name, company[1])
    email_result = get_email_service().send(
        to_email=email,
        subject=tpl["subject"],
        html_body=tpl["html"],
        text_body=tpl["text"],
    )
    if not email_result.get("success"):
        db.rollback()
        raise _err(502, "EMAIL_DELIVERY_FAILED", "Invitation could not be delivered")

    db.commit()
    return {"status": "success", "data": {"user_id": uid, "email": email, "tenant_id": tenant_id, "role": role, "message": "Invitation sent"}}


@router.post("/accept", dependencies=[Depends(auth_limiter.check)])
async def accept_invitation(body: dict, db: Session = Depends(get_db)):
    token = str(body.get("token") or "").strip()
    password = str(body.get("password") or "")
    if not token or not password:
        raise _err(400, "MISSING", "token and password are required")

    err = UserEngine(db)
    # Reuse the same password policy as normal password creation.
    from core.user_engine import _validate_password
    password_error = _validate_password(password)
    if password_error:
        raise _err(400, "INVALID_PASSWORD", password_error)

    row = db.execute(
        text(
            "SELECT id, tenant_id, verification_expires_at FROM dbp_users "
            "WHERE verification_token_hash = :th AND email_verified = false AND is_active = true FOR UPDATE"
        ),
        {"th": _hash_token(token)},
    ).fetchone()
    if not row:
        raise _err(400, "INVALID_INVITATION", "Invalid or expired invitation")
    expires = row[2]
    if expires and expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise _err(400, "INVITATION_EXPIRED", "Invitation expired")

    db.execute(
        text(
            "UPDATE dbp_users SET password_hash = :pw, email_verified = true, "
            "verification_token_hash = NULL, verification_expires_at = NULL, "
            "failed_login_attempts = 0, locked_until = NULL, updated_at = NOW() WHERE id = :id"
        ),
        {"pw": pwd_context.hash(password), "id": row[0]},
    )
    db.commit()
    return {"status": "success", "data": {"message": "Invitation accepted. You can now sign in.", "tenant_id": row[1]}}
