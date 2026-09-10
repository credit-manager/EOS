"""
Production authentication endpoints: registration, login, verification,
password reset, rotating refresh sessions and tenant user administration.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db, RLS_CONTEXT_PARAM, current_tenant_id, get_db_no_rls
from core.auth import get_current_user, require_permission, require_admin_role
from core.user_engine import UserEngine
from core.email_adapter import get_email_service, EmailTemplateEngine
from core.rate_limit import write_limiter, auth_limiter
from core.schemas import RegisterRequest, LoginRequest, VerifyEmailRequest, RefreshTokenRequest, ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
from datetime import datetime, timedelta, timezone
import hashlib
import jwt
import os
import secrets
import uuid

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
_REFRESH_DAYS = 30


def _err(sc, code, msg):
    return HTTPException(sc, detail={"status": "error", "error": {"code": code, "message": msg}})


def _refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_refresh_token(db: Session, user_id: str, tenant_id: str, family_id: str | None = None) -> str:
    raw = secrets.token_urlsafe(64)
    db.execute(text(
        "INSERT INTO dbp_refresh_tokens (id, token_hash, user_id, tenant_id, family_id, expires_at) "
        "VALUES (:id, :hash, :user_id, :tenant_id, :family_id, :expires_at)"
    ), {"id": str(uuid.uuid4()), "hash": _refresh_hash(raw), "user_id": user_id, "tenant_id": tenant_id,
        "family_id": family_id or str(uuid.uuid4()), "expires_at": datetime.now(timezone.utc) + timedelta(days=_REFRESH_DAYS)})
    return raw


def _issue_access_token(result: dict) -> str:
    mode = os.getenv("EOS_AUTH_MODE", "test").lower()
    if mode == "production":
        secret_key = os.getenv("EOS_SECRET_KEY")
        if not secret_key or len(secret_key) < 32:
            raise _err(500, "SERVER_CONFIG", "Production JWT secret is not configured correctly")
    else:
        secret_key = os.getenv("EOS_TEST_SECRET_KEY", "").strip()
        if not secret_key:
            raise _err(500, "SERVER_CONFIG", "EOS_TEST_SECRET_KEY is not configured")
    now = datetime.now(timezone.utc)
    payload = {"sub": result["user_id"], "exp": now + timedelta(minutes=30), "iat": now, "type": "access",
               "tenant_id": result["tenant_id"], "email": result["email"], "roles": [result["role"]],
               "iss": os.getenv("EOS_JWT_ISSUER", "eos-dbp"), "aud": os.getenv("EOS_JWT_AUDIENCE", "eos-api"),
               "jti": str(uuid.uuid4())}
    return jwt.encode(payload, secret_key, algorithm="HS256")


@router.post("/register", dependencies=[Depends(auth_limiter.check)])
async def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    from database import SessionLocal
    tenant_id = f"tenant_{secrets.token_hex(8)}"
    token = current_tenant_id.set(tenant_id)
    db2 = SessionLocal()
    try:
        company_name = body.company_name
        company_id = str(uuid.uuid4())
        db2.execute(text("INSERT INTO dbp_companies (id, tenant_id, code, name_en, name_ar) VALUES (:id, :tid, :code, :name, :name)"),
                    {"id": company_id, "tid": tenant_id, "code": company_name.lower().replace(" ", "_")[:30], "name": company_name})
        engine = UserEngine(db2)
        result = engine.register(tenant_id=tenant_id, email=body.email, password=body.password, first_name=body.first_name,
                                 last_name=body.last_name, first_name_ar=body.first_name_ar, last_name_ar=body.last_name_ar,
                                 phone=body.phone, role="admin")
        if not result["success"]:
            db2.rollback()
            raise _err(400, "REGISTER_FAILED", result["error"])
        db2.commit()
        email_svc = get_email_service()
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
        verification_token = result.get("verification_token", "")
        tpl = EmailTemplateEngine.verification_email(f"{frontend_url}/verify-email?token={verification_token}", body.first_name)
        email_svc.send(to_email=body.email, subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
        return {"status": "success", "data": {"user_id": result["user_id"], "tenant_id": tenant_id, "company_id": company_id, "email": result["email"],
                "requires_verification": result["requires_verification"],
                "verification_token": verification_token if email_svc.__class__.__name__ == "ConsoleEmailProvider" else None,
                "message": "Registration successful. Please verify your email."}}
    except HTTPException:
        raise
    except Exception:
        db2.rollback()
        raise
    finally:
        db2.close()
        current_tenant_id.reset(token)


@router.post("/verify-email", dependencies=[Depends(auth_limiter.check)])
async def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    token_val = current_tenant_id.set("*")
    try:
        engine = UserEngine(db)
        result = engine.verify_email(body.token)
        if not result["success"]:
            raise _err(400, "VERIFY_FAILED", result["error"])
        db.commit()
        email_svc = get_email_service()
        user = engine.get_user_by_id(result["user_id"])
        if user:
            tpl = EmailTemplateEngine.welcome_email(user.get("first_name", "User"), user.get("email", "user@example.com").split("@")[0])
            email_svc.send(to_email=user["email"], subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
        return {"status": "success", "data": {"message": "Email verified"}}
    finally:
        current_tenant_id.reset(token_val)


@router.post("/login", dependencies=[Depends(auth_limiter.check)])
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email
    password = body.password
    if not email or not password:
        raise _err(400, "MISSING", "email and password required")
    token_claim = current_tenant_id.set("*")
    try:
        result = UserEngine(db).login(email, password)
    finally:
        current_tenant_id.reset(token_claim)
    if not result["success"]:
        raise _err(403 if result.get("requires_verification") else 401, "LOGIN_FAILED", result["error"])
    try:
        token_claim2 = current_tenant_id.set(result["tenant_id"])
        try:
            token = _issue_access_token(result)
            refresh_token = _issue_refresh_token(db, result["user_id"], result["tenant_id"])
            company = db.execute(text("SELECT id FROM dbp_companies WHERE tenant_id = :tenant_id ORDER BY id LIMIT 1"),
                                 {"tenant_id": result["tenant_id"]}).fetchone()
            db.commit()
        finally:
            current_tenant_id.reset(token_claim2)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise _err(500, "SESSION_FAILED", "Unable to create authenticated session")
    return {"status": "success", "data": {"access_token": token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": 1800,
            "user": {"id": result["user_id"], "email": result["email"], "first_name": result.get("first_name"),
                      "last_name": result.get("last_name"), "tenant_id": result["tenant_id"], "company_id": company[0] if company else None, "role": result["role"]}}}


@router.post("/refresh", dependencies=[Depends(auth_limiter.check)])
async def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    import logging, traceback as tb
    _log = logging.getLogger("eos.auth")
    from database import SessionLocal
    raw = body.refresh_token.strip()
    if len(raw) < 40:
        raise _err(401, "INVALID_REFRESH_TOKEN", "Invalid refresh token")
    now = datetime.now(timezone.utc)
    token_hash = _refresh_hash(raw)
    db_cross = SessionLocal()
    cross_claim = current_tenant_id.set("*")
    try:
        row = db_cross.execute(text(
            "SELECT id, user_id, tenant_id, family_id, expires_at, rotated_at, revoked_at FROM dbp_refresh_tokens "
            "WHERE token_hash = :hash"
        ), {"hash": token_hash}).mappings().first()
        db_cross.commit()
    finally:
        current_tenant_id.reset(cross_claim)
        db_cross.close()
    if not row:
        raise _err(401, "INVALID_REFRESH_TOKEN", "Invalid refresh token")
    tenant_id = row["tenant_id"]
    token_claim = current_tenant_id.set(tenant_id)
    try:
        try:
            if row["revoked_at"] is not None or row["rotated_at"] is not None:
                db.execute(text("UPDATE dbp_refresh_tokens SET revoked_at = COALESCE(revoked_at, :now) WHERE family_id = :family_id AND revoked_at IS NULL"),
                           {"now": now, "family_id": row["family_id"]})
                db.commit()
                raise _err(401, "REFRESH_REUSE_DETECTED", "Refresh session has been revoked")
            if row["expires_at"] <= now:
                db.execute(text("UPDATE dbp_refresh_tokens SET revoked_at = :now WHERE id = :id"), {"now": now, "id": row["id"]})
                db.commit()
                raise _err(401, "REFRESH_EXPIRED", "Refresh token expired")
            user = UserEngine(db).get_user_by_id_tenant(str(row["user_id"]), tenant_id)
            if not user or not user.get("is_active", True):
                db.execute(text("UPDATE dbp_refresh_tokens SET revoked_at = :now WHERE family_id = :family_id AND revoked_at IS NULL"),
                           {"now": now, "family_id": row["family_id"]})
                db.commit()
                raise _err(401, "SESSION_REVOKED", "User session is no longer active")
            result = {"user_id": str(row["user_id"]), "tenant_id": tenant_id, "email": user["email"], "role": user["role"]}
            new_raw = secrets.token_urlsafe(64)
            new_hash = _refresh_hash(new_raw)
            db.execute(text("INSERT INTO dbp_refresh_tokens (id, token_hash, user_id, tenant_id, family_id, expires_at) VALUES (:id, :hash, :user_id, :tenant_id, :family_id, :expires_at)"),
                       {"id": str(uuid.uuid4()), "hash": new_hash, "user_id": row["user_id"], "tenant_id": tenant_id,
                        "family_id": row["family_id"], "expires_at": now + timedelta(days=_REFRESH_DAYS)})
            db.execute(text("UPDATE dbp_refresh_tokens SET rotated_at = :now, last_used_at = :now, replaced_by_hash = :new_hash WHERE id = :id AND rotated_at IS NULL AND revoked_at IS NULL"),
                       {"now": now, "new_hash": new_hash, "id": row["id"]})
            try:
                access = _issue_access_token(result)
                db.commit()
            except HTTPException:
                db.rollback()
                raise
            except Exception as exc:
                db.rollback()
                raise _err(500, "SESSION_FAILED", str(exc))
        except HTTPException:
            raise
        except Exception as exc:
            _log.error("refresh_token_error: %s\n%s", exc, tb.format_exc())
            db.rollback()
            raise _err(500, "REFRESH_FAILED", str(exc))
    finally:
        current_tenant_id.reset(token_claim)
    return {"status": "success", "data": {"access_token": access, "refresh_token": new_raw, "token_type": "bearer", "expires_in": 1800}}


@router.post("/logout", dependencies=[Depends(auth_limiter.check)])
async def logout(body: dict | None = None, db: Session = Depends(get_db)):
    raw = str((body or {}).get("refresh_token") or "").strip()
    if raw:
        token_claim = current_tenant_id.set("*")
        try:
            db.execute(text("UPDATE dbp_refresh_tokens SET revoked_at = :now WHERE token_hash = :hash AND revoked_at IS NULL"),
                       {"now": datetime.now(timezone.utc), "hash": _refresh_hash(raw)})
            db.commit()
        finally:
            current_tenant_id.reset(token_claim)
    return {"status": "success", "data": {"message": "Logged out"}}


@router.post("/forgot-password", dependencies=[Depends(auth_limiter.check)])
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    token_claim = current_tenant_id.set("*")
    try:
        engine = UserEngine(db)
        result = engine.request_password_reset(body.email)
        db.commit()
    finally:
        current_tenant_id.reset(token_claim)
    if result.get("reset_token"):
        token_claim2 = current_tenant_id.set("*")
        try:
            user = engine.get_user_by_id(result.get("user_id", "")) if result.get("user_id") else None
        finally:
            current_tenant_id.reset(token_claim2)
        first_name = user.get("first_name", "User") if user else "User"
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
        tpl = EmailTemplateEngine.password_reset_email(f"{frontend_url}/reset-password?token={result['reset_token']}", first_name)
        email_svc = get_email_service()
        email_svc.send(to_email=body.email, subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
    return {"status": "success", "data": {"message": "If email exists, reset link sent",
            "reset_token": result.get("reset_token") if os.getenv("EOS_EMAIL_PROVIDER", "console") == "console" else None}}


@router.post("/reset-password", dependencies=[Depends(auth_limiter.check)])
async def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_claim = current_tenant_id.set("*")
    try:
        result = UserEngine(db).reset_password(body.token, body.new_password)
        if not result["success"]:
            raise _err(400, "RESET_FAILED", result["error"])
        db.commit()
    finally:
        current_tenant_id.reset(token_claim)
    return {"status": "success", "data": {"message": "Password reset successful"}}


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
    company = db.execute(text("SELECT id FROM dbp_companies WHERE tenant_id = :tenant_id ORDER BY id LIMIT 1"),
                         {"tenant_id": user["tenant_id"]}).fetchone()
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
