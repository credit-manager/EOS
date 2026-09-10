"""
Production authentication endpoints: registration, verification, password reset,
rotating refresh sessions and tenant user administration.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from database import current_tenant_id, get_db
from core.auth import get_current_user, require_permission
from core.user_engine import UserEngine
from core.email_adapter import get_email_service, EmailTemplateEngine
from core.rate_limit import auth_limiter
from core.runtime_config import resolve_auth_mode
from core.schemas import RegisterRequest, LoginRequest

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
_REFRESH_DAYS = 30
_REFRESH_COOKIE = "eos_refresh_token"


class TokenRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)


class RefreshRequest(BaseModel):
    # Legacy clients may still send this field. Browser clients should use the
    # HttpOnly cookie, which is not readable from JavaScript.
    refresh_token: str | None = Field(default=None, min_length=40, max_length=512)


class PasswordResetRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


def _err(sc, code, msg):
    return HTTPException(sc, detail={"status": "error", "error": {"code": code, "message": msg}})


def _refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        max_age=_REFRESH_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=resolve_auth_mode() == "production",
        samesite="lax",
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/v1/auth")


def _auth_tenant(db: Session, function_name: str, value: str):
    """Resolve a tenant through a narrow SECURITY DEFINER lookup and establish RLS context."""
    row = db.execute(text(f"SELECT public.{function_name}(:value)"), {"value": value}).fetchone()
    if not row or row[0] is None:
        return None
    return current_tenant_id.set(str(row[0]).lower())


def _issue_refresh_token(db: Session, user_id: str, tenant_id: str, family_id: str | None = None, *, mfa_verified: bool = False) -> str:
    raw = secrets.token_urlsafe(64)
    db.execute(text(
        "INSERT INTO dbp_refresh_tokens "
        "(id, token_hash, user_id, tenant_id, family_id, mfa_verified, expires_at) "
        "VALUES (:id, :hash, :user_id, :tenant_id, :family_id, :mfa_verified, :expires_at)"
    ), {
        "id": str(uuid.uuid4()), "hash": _refresh_hash(raw), "user_id": user_id, "tenant_id": tenant_id,
        "family_id": family_id or str(uuid.uuid4()), "mfa_verified": mfa_verified,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=_REFRESH_DAYS),
    })
    return raw


def _issue_access_token(result: dict, *, mfa_verified: bool = False) -> str:
    """Issue access tokens through the central runtime/auth contract."""
    try:
        mode = resolve_auth_mode()
        if mode == "production":
            from core.production_auth import create_access_token
            return create_access_token(subject=str(result["user_id"]), extra_data={
                "tenant_id": result["tenant_id"], "email": result["email"],
                "roles": [result["role"]], "mfa_verified": bool(mfa_verified),
            })
        from core.auth import create_test_token
        return create_test_token(tenant_id=result["tenant_id"], user_id=str(result["user_id"]), email=result["email"], roles=[result["role"]])
    except (HTTPException, ValueError) as exc:
        if isinstance(exc, HTTPException):
            raise
        raise _err(500, "SERVER_CONFIG", "Authentication signing configuration is invalid") from exc


def _mfa_enabled(db: Session, user_id: str) -> bool:
    row = db.execute(text("SELECT 1 FROM dbp_2fa_settings WHERE user_id=:uid AND is_enabled=TRUE"), {"uid": user_id}).fetchone()
    return row is not None


@router.post("/register", dependencies=[Depends(auth_limiter.check)])
async def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    tenant_token = None
    try:
        tenant_id = f"tenant_{secrets.token_hex(8)}"
        tenant_token = current_tenant_id.set(tenant_id)
        company_name = body.company_name
        company_id = str(uuid.uuid4())
        company_code = (body.company_code or company_name.lower().replace(" ", "_"))[:30]
        db.execute(text("INSERT INTO dbp_companies (id, tenant_id, code, name_en, name_ar) VALUES (:id, :tid, :code, :name, :name)"), {"id": company_id, "tid": tenant_id, "code": company_code, "name": company_name})
        result = UserEngine(db).register(tenant_id=tenant_id, email=body.email, password=body.password, first_name=body.first_name, last_name=body.last_name, first_name_ar=body.first_name_ar, last_name_ar=body.last_name_ar, phone=body.phone, role="admin")
        if not result["success"]:
            db.rollback()
            raise _err(400, "REGISTER_FAILED", result["error"])
        db.commit()
        email_svc = get_email_service()
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
        verification_token = result.get("verification_token", "")
        tpl = EmailTemplateEngine.verification_email(f"{frontend_url}/verify-email?token={verification_token}", body.first_name)
        email_svc.send(to_email=body.email, subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
        return {"status": "success", "data": {"user_id": result["user_id"], "tenant_id": tenant_id, "company_id": company_id, "email": result["email"], "requires_verification": result["requires_verification"], "verification_token": verification_token if email_svc.__class__.__name__ == "ConsoleEmailProvider" else None, "message": "Registration successful. Please verify your email."}}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        if tenant_token is not None:
            current_tenant_id.reset(tenant_token)


@router.post("/verify-email", dependencies=[Depends(auth_limiter.check)])
async def verify_email(body: TokenRequest, db: Session = Depends(get_db)):
    tenant_token = _auth_tenant(db, "eos_auth_tenant_by_verification_hash", _refresh_hash(body.token))
    if tenant_token is None:
        raise _err(400, "VERIFY_FAILED", "Invalid or expired verification token")
    try:
        result = UserEngine(db).verify_email(body.token)
        if not result["success"]:
            raise _err(400, "VERIFY_FAILED", result["error"])
        db.commit()
        user = UserEngine(db).get_user_by_id(result["user_id"])
        email_svc = get_email_service()
        if user:
            tpl = EmailTemplateEngine.welcome_email(user.get("first_name", "User"), user.get("email", "user@example.com").split("@")[0])
            email_svc.send(to_email=user["email"], subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
        return {"status": "success", "data": {"message": "Email verified"}}
    finally:
        current_tenant_id.reset(tenant_token)


@router.post("/login", dependencies=[Depends(auth_limiter.check)])
async def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    email = body.email
    tenant_token = _auth_tenant(db, "eos_auth_tenant_by_email", email)
    if tenant_token is None:
        raise _err(401, "LOGIN_FAILED", "Invalid email or password")
    try:
        result = UserEngine(db).login(email, body.password)
        if not result["success"]:
            raise _err(403 if result.get("requires_verification") else 401, "LOGIN_FAILED", result["error"])
        mfa_required = _mfa_enabled(db, str(result["user_id"]))
        access = _issue_access_token(result, mfa_verified=not mfa_required)
        refresh = _issue_refresh_token(db, result["user_id"], result["tenant_id"], mfa_verified=not mfa_required)
        company = db.execute(text("SELECT id FROM dbp_companies WHERE tenant_id = :tenant_id ORDER BY id LIMIT 1"), {"tenant_id": result["tenant_id"]}).fetchone()
        db.commit()
        _set_refresh_cookie(response, refresh)
        return {"status": "success", "data": {"access_token": access, "token_type": "bearer", "expires_in": 1800, "user": {"id": result["user_id"], "email": result["email"], "first_name": result.get("first_name"), "last_name": result.get("last_name"), "tenant_id": result["tenant_id"], "company_id": company[0] if company else None, "role": result["role"], "mfa_required": mfa_required}}}
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise _err(500, "SESSION_FAILED", "Unable to create authenticated session")
    finally:
        current_tenant_id.reset(tenant_token)


@router.post("/refresh", dependencies=[Depends(auth_limiter.check)])
async def refresh_token(body: RefreshRequest, response: Response, cookie_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE), db: Session = Depends(get_db)):
    raw = (body.refresh_token or cookie_token or "").strip()
    if not raw or len(raw) < 40:
        _clear_refresh_cookie(response)
        raise _err(401, "INVALID_REFRESH_TOKEN", "Invalid refresh token")
    token_hash = _refresh_hash(raw)
    tenant_token = _auth_tenant(db, "eos_auth_tenant_by_refresh_hash", token_hash)
    if tenant_token is None:
        _clear_refresh_cookie(response)
        raise _err(401, "INVALID_REFRESH_TOKEN", "Invalid refresh token")
    try:
        now = datetime.now(timezone.utc)
        row = db.execute(text("SELECT id, user_id, tenant_id, family_id, mfa_verified, expires_at, rotated_at, revoked_at FROM dbp_refresh_tokens WHERE token_hash = :hash FOR UPDATE"), {"hash": token_hash}).mappings().first()
        if not row:
            _clear_refresh_cookie(response)
            raise _err(401, "INVALID_REFRESH_TOKEN", "Invalid refresh token")
        if row["revoked_at"] is not None or row["rotated_at"] is not None:
            db.execute(text("UPDATE dbp_refresh_tokens SET revoked_at = COALESCE(revoked_at, :now) WHERE family_id = :family_id AND revoked_at IS NULL"), {"now": now, "family_id": row["family_id"]})
            db.commit(); _clear_refresh_cookie(response)
            raise _err(401, "REFRESH_REUSE_DETECTED", "Refresh session has been revoked")
        if row["expires_at"] <= now:
            db.execute(text("UPDATE dbp_refresh_tokens SET revoked_at = :now WHERE id = :id"), {"now": now, "id": row["id"]})
            db.commit(); _clear_refresh_cookie(response)
            raise _err(401, "REFRESH_EXPIRED", "Refresh token expired")
        user = UserEngine(db).get_user_by_id_tenant(row["user_id"], row["tenant_id"])
        if not user or not user.get("is_active", True):
            db.execute(text("UPDATE dbp_refresh_tokens SET revoked_at = :now WHERE family_id = :family_id AND revoked_at IS NULL"), {"now": now, "family_id": row["family_id"]})
            db.commit(); _clear_refresh_cookie(response)
            raise _err(401, "SESSION_REVOKED", "User session is no longer active")
        mfa_required = _mfa_enabled(db, str(row["user_id"]))
        if mfa_required and not bool(row["mfa_verified"]):
            raise _err(401, "MFA_VERIFICATION_REQUIRED", "MFA verification required before refreshing this session")
        result = {"user_id": row["user_id"], "tenant_id": row["tenant_id"], "email": user["email"], "role": user["role"]}
        new_raw = secrets.token_urlsafe(64)
        new_hash = _refresh_hash(new_raw)
        db.execute(text("INSERT INTO dbp_refresh_tokens (id, token_hash, user_id, tenant_id, family_id, mfa_verified, expires_at) VALUES (:id, :hash, :user_id, :tenant_id, :family_id, :mfa_verified, :expires_at)"), {"id": str(uuid.uuid4()), "hash": new_hash, "user_id": row["user_id"], "tenant_id": row["tenant_id"], "family_id": row["family_id"], "mfa_verified": bool(row["mfa_verified"]), "expires_at": now + timedelta(days=_REFRESH_DAYS)})
        db.execute(text("UPDATE dbp_refresh_tokens SET rotated_at = :now, last_used_at = :now, replaced_by_hash = :new_hash WHERE id = :id AND rotated_at IS NULL AND revoked_at IS NULL"), {"now": now, "new_hash": new_hash, "id": row["id"]})
        access = _issue_access_token(result, mfa_verified=bool(row["mfa_verified"]))
        db.commit()
        _set_refresh_cookie(response, new_raw)
        return {"status": "success", "data": {"access_token": access, "token_type": "bearer", "expires_in": 1800}}
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise _err(500, "SESSION_FAILED", "Unable to refresh authenticated session")
    finally:
        current_tenant_id.reset(tenant_token)


@router.post("/logout", dependencies=[Depends(auth_limiter.check)])
async def logout(body: RefreshRequest | None, response: Response, cookie_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE), db: Session = Depends(get_db)):
    raw = ((body.refresh_token if body else None) or cookie_token or "").strip()
    if raw:
        tenant_token = _auth_tenant(db, "eos_auth_tenant_by_refresh_hash", _refresh_hash(raw))
        if tenant_token is not None:
            try:
                db.execute(text("UPDATE dbp_refresh_tokens SET revoked_at = :now WHERE token_hash = :hash AND revoked_at IS NULL"), {"now": datetime.now(timezone.utc), "hash": _refresh_hash(raw)})
                db.commit()
            finally:
                current_tenant_id.reset(tenant_token)
    _clear_refresh_cookie(response)
    return {"status": "success", "data": {"message": "Logged out"}}


@router.post("/forgot-password", dependencies=[Depends(auth_limiter.check)])
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    email = str(body.email).lower()
    tenant_token = _auth_tenant(db, "eos_auth_tenant_by_email", email)
    try:
        result = UserEngine(db).request_password_reset(email)
        db.commit()
        if result.get("reset_token"):
            user = UserEngine(db).get_user_by_id(result.get("user_id", "")) if result.get("user_id") else None
            first_name = user.get("first_name", "User") if user else "User"
            frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
            tpl = EmailTemplateEngine.password_reset_email(f"{frontend_url}/reset-password?token={result['reset_token']}", first_name)
            email_svc = get_email_service()
            email_svc.send(to_email=email, subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
        return {"status": "success", "data": {"message": "If email exists, reset link sent", "reset_token": result.get("reset_token") if os.getenv("EOS_EMAIL_PROVIDER", "console") == "console" else None}}
    finally:
        if tenant_token is not None:
            current_tenant_id.reset(tenant_token)


@router.post("/reset-password", dependencies=[Depends(auth_limiter.check)])
async def reset_password(body: PasswordResetRequest, db: Session = Depends(get_db)):
    tenant_token = _auth_tenant(db, "eos_auth_tenant_by_reset_hash", _refresh_hash(body.token))
    if tenant_token is None:
        raise _err(400, "RESET_FAILED", "Invalid or expired reset token")
    try:
        result = UserEngine(db).reset_password(body.token, body.new_password)
        if not result["success"]:
            raise _err(400, "RESET_FAILED", result["error"])
        db.commit()
        return {"status": "success", "data": {"message": "Password reset successful"}}
    finally:
        current_tenant_id.reset(tenant_token)


@router.post("/change-password", dependencies=[Depends(require_permission("dynamic", "update"))])
async def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    result = UserEngine(db).change_password(user["id"], body.current_password, body.new_password)
    if not result["success"]:
        raise _err(400, "CHANGE_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": {"message": "Password changed"}}


@router.get("/me", dependencies=[Depends(require_permission("dynamic", "read"))])
async def get_me(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    u = UserEngine(db).get_user_by_id_tenant(user["id"], user["tenant_id"])
    if not u:
        raise _err(404, "NOT_FOUND", "User not found")
    company = db.execute(text("SELECT id FROM dbp_companies WHERE tenant_id = :tenant_id ORDER BY id LIMIT 1"), {"tenant_id": user["tenant_id"]}).fetchone()
    u["company_id"] = company[0] if company else None
    return {"status": "success", "data": u}


@router.get("/users", dependencies=[Depends(require_permission("dynamic", "read"))])
async def list_users(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    users = UserEngine(db).list_users(user["tenant_id"])
    return {"status": "success", "data": users, "count": len(users)}


@router.get("/users/{user_id}", dependencies=[Depends(require_permission("dynamic", "read"))])
async def get_user(user_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    u = UserEngine(db).get_user_by_id_tenant(user_id, user["tenant_id"])
    if not u:
        raise _err(404, "NOT_FOUND", "User not found")
    return {"status": "success", "data": u}
