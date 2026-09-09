"""
P61 Auth Router — Production authentication endpoints.
Register, login, verify email, password reset, user management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from core.auth import get_current_user, require_permission, TEST_SECRET_KEY, TEST_ALGORITHM
from core.user_engine import UserEngine
from core.email_adapter import get_email_service, EmailTemplateEngine
from core.rate_limit import write_limiter
from datetime import datetime, timedelta, timezone
from jose import jwt as jose_jwt
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import os

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# ──────────────────────────────────────────────────────────────
# INPUT VALIDATION SCHEMAS
# ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    company_name: str = Field(..., min_length=1, max_length=200)
    first_name_ar: Optional[str] = Field(None, max_length=100)
    last_name_ar: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1)


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="dynamic_viewer")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


def _err(sc, code, msg):
    return HTTPException(sc, detail={"status": "error", "error": {"code": code, "message": msg}})


@router.post("/register", dependencies=[Depends(write_limiter.check)])
async def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    from database import SessionLocal
    from sqlalchemy import text
    import uuid, secrets

    db2 = SessionLocal()
    try:
        tenant_id = f"tenant_{secrets.token_hex(8)}"
        company_name = body.company_name

        db2.execute(text(
            "INSERT INTO dbp_companies (id, tenant_id, code, name_en, name_ar) "
            "VALUES (:id, :tid, :code, :name, :name)"
        ), {"id": str(uuid.uuid4()), "tid": tenant_id,
            "code": company_name.lower().replace(" ", "_")[:30],
            "name": company_name})
        db2.commit()

        engine = UserEngine(db2)
        result = engine.register(
            tenant_id=tenant_id,
            email=body.email,
            password=body.password,
            first_name=body.first_name,
            last_name=body.last_name,
            first_name_ar=body.first_name_ar,
            last_name_ar=body.last_name_ar,
            phone=body.phone,
            role="admin"
        )
        db2.commit()

        if not result["success"]:
            raise _err(400, "REGISTER_FAILED", result["error"])

        email_svc = get_email_service()
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
        verification_token = result.get("verification_token", "")
        verification_url = f"{frontend_url}/verify-email?token={verification_token}"
        tpl = EmailTemplateEngine.verification_email(verification_url, body.first_name)
        email_svc.send(to_email=body.email, subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))

        return {"status": "success", "data": {
            "user_id": result["user_id"],
            "tenant_id": tenant_id,
            "email": result["email"],
            "requires_verification": result["requires_verification"],
            "verification_token": verification_token if email_svc.__class__.__name__ == "ConsoleEmailProvider" else None,
            "message": "Registration successful. Please verify your email."
        }}
    finally:
        db2.close()


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.verify_email(body.token)
    if not result["success"]:
        raise _err(400, "VERIFY_FAILED", result["error"])
    db.commit()

    email_svc = get_email_service()
    user = engine.get_user_by_id(result["user_id"])
    if user:
        tpl = EmailTemplateEngine.welcome_email(
            user.get("first_name", "User"),
            user.get("email", "user@example.com").split("@")[0]
        )
        email_svc.send(to_email=user["email"], subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))

    return {"status": "success", "data": {"message": "Email verified"}}


@router.post("/login", dependencies=[Depends(write_limiter.check)])
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.login(body.email, body.password)
    if not result["success"]:
        sc = 403 if result.get("requires_verification") else 401
        raise _err(sc, "LOGIN_FAILED", result["error"])

    import os
    secret_key = os.getenv("EOS_SECRET_KEY") or TEST_SECRET_KEY
    algorithm = os.getenv("EOS_ALGORITHM", TEST_ALGORITHM)
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)

    payload = {
        "sub": result["user_id"],
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "tenant_id": result["tenant_id"],
        "email": result["email"],
        "roles": [result["role"]],
    }
    token = jose_jwt.encode(payload, secret_key, algorithm=algorithm)
    return {"status": "success", "data": {
        "access_token": token, "token_type": "bearer",
        "user": {
            "id": result["user_id"], "email": result["email"],
            "first_name": result.get("first_name"),
            "last_name": result.get("last_name"),
            "tenant_id": result["tenant_id"], "role": result["role"]
        }
    }}


@router.post("/forgot-password", dependencies=[Depends(write_limiter.check)])
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.request_password_reset(body.email)
    db.commit()

    if result.get("reset_token"):
        user = engine.get_user_by_id(result.get("user_id", "")) if result.get("user_id") else None
        first_name = user.get("first_name", "User") if user else "User"
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password?token={result['reset_token']}"
        tpl = EmailTemplateEngine.password_reset_email(reset_url, first_name)
        email_svc = get_email_service()
        email_svc.send(to_email=body.email, subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))

    return {"status": "success", "data": {
        "message": "If email exists, reset link sent",
        "reset_token": result.get("reset_token") if os.getenv("EOS_EMAIL_PROVIDER", "console") == "console" else None
    }}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.reset_password(body.token, body.new_password)
    if not result["success"]:
        raise _err(400, "RESET_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": {"message": "Password reset successful"}}


@router.post("/change-password", dependencies=[Depends(require_permission("dynamic", "update"))])
async def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.change_password(user["id"], body.current_password, body.new_password)
    if not result["success"]:
        raise _err(400, "CHANGE_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": {"message": "Password changed"}}


@router.get("/me", dependencies=[Depends(require_permission("dynamic", "read"))])
async def get_me(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = UserEngine(db)
    u = engine.get_user_by_id(user["id"])
    if not u:
        raise _err(404, "NOT_FOUND", "User not found")
    return {"status": "success", "data": u}


@router.get("/users", dependencies=[Depends(require_permission("dynamic", "read"))])
async def list_users(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = UserEngine(db)
    users = engine.list_users(user["tenant_id"])
    return {"status": "success", "data": users, "count": len(users)}


@router.get("/users/{user_id}", dependencies=[Depends(require_permission("dynamic", "read"))])
async def get_user(user_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = UserEngine(db)
    u = engine.get_user_by_id_tenant(user_id, user["tenant_id"])
    if not u:
        raise _err(404, "NOT_FOUND", "User not found")
    return {"status": "success", "data": u}


@router.put("/users/{user_id}", dependencies=[Depends(require_permission("dynamic", "update"))])
async def update_user(user_id: str, body: dict, user: dict = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.update_user(user_id, user["tenant_id"], body)
    if not result["success"]:
        raise _err(400, "UPDATE_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": {"message": result["message"]}}


@router.put("/users/{user_id}/role", dependencies=[Depends(require_permission("dynamic", "update"))])
async def change_role(user_id: str, body: dict, user: dict = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    new_role = body.get("role")
    if not new_role:
        raise _err(400, "MISSING", "role required")
    engine = UserEngine(db)
    result = engine.change_role(user_id, user["tenant_id"], new_role)
    if not result["success"]:
        raise _err(400, "ROLE_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": {"message": result["message"]}}


@router.delete("/users/{user_id}", dependencies=[Depends(require_permission("dynamic", "update"))])
async def deactivate_user(user_id: str, user: dict = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.deactivate_user(user_id, user["tenant_id"])
    if not result["success"]:
        raise _err(400, "DELETE_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": {"message": result["message"]}}


@router.post("/users/invite", dependencies=[Depends(require_permission("dynamic", "create"))])
async def invite_user(body: InviteUserRequest, user: dict = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.invite_user(
        tenant_id=user["tenant_id"], email=body.email, role=body.role,
        first_name=body.first_name or "", last_name=body.last_name or ""
    )
    if not result["success"]:
        raise _err(400, "INVITE_FAILED", result["error"])
    db.commit()

    email_svc = get_email_service()
    if result.get("verification_token"):
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
        verify_url = f"{frontend_url}/verify-email?token={result['verification_token']}"
        tpl = EmailTemplateEngine.verification_email(verify_url, body.first_name or "User")
        email_svc.send(to_email=body.email, subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))

    return {"status": "success", "data": {
        "message": f"Invitation sent to {body.email}",
        "user_id": result["user_id"]
    }}
