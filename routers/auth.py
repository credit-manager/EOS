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
import jwt
import os

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _err(sc, code, msg):
    return HTTPException(sc, detail={"status": "error", "error": {"code": code, "message": msg}})


@router.post("/register", dependencies=[Depends(write_limiter.check)])
async def register(body: dict, request: Request, db: Session = Depends(get_db)):
    required = ["email", "password", "first_name", "last_name", "company_name"]
    for f in required:
        if not body.get(f):
            raise _err(400, "MISSING", f"{f} required")
    from database import SessionLocal
    from sqlalchemy import text
    import uuid, secrets
    db2 = SessionLocal()
    try:
        tenant_id = f"tenant_{secrets.token_hex(8)}"
        company_name = body["company_name"]
        db2.execute(text(
            "INSERT INTO dbp_companies (id, tenant_id, code, name_en, name_ar) "
            "VALUES (:id, :tid, :code, :name, :name)"
        ), {"id": str(uuid.uuid4()), "tid": tenant_id,
            "code": company_name.lower().replace(" ", "_")[:30], "name": company_name})
        db2.commit()
        engine = UserEngine(db2)
        result = engine.register(
            tenant_id=tenant_id, email=body["email"], password=body["password"],
            first_name=body["first_name"], last_name=body["last_name"],
            first_name_ar=body.get("first_name_ar"), last_name_ar=body.get("last_name_ar"),
            phone=body.get("phone"), role="admin"
        )
        db2.commit()
        if not result["success"]:
            raise _err(400, "REGISTER_FAILED", result["error"])
        email_svc = get_email_service()
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
        verification_token = result.get("verification_token", "")
        verification_url = f"{frontend_url}/verify-email?token={verification_token}"
        tpl = EmailTemplateEngine.verification_email(verification_url, body["first_name"])
        email_svc.send(to_email=body["email"], subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
        return {"status": "success", "data": {
            "user_id": result["user_id"], "tenant_id": tenant_id, "email": result["email"],
            "requires_verification": result["requires_verification"],
            "verification_token": verification_token if email_svc.__class__.__name__ == "ConsoleEmailProvider" else None,
            "message": "Registration successful. Please verify your email."
        }}
    finally:
        db2.close()


@router.post("/verify-email")
async def verify_email(body: dict, db: Session = Depends(get_db)):
    token = body.get("token")
    if not token:
        raise _err(400, "MISSING", "token required")
    engine = UserEngine(db)
    result = engine.verify_email(token)
    if not result["success"]:
        raise _err(400, "VERIFY_FAILED", result["error"])
    db.commit()
    email_svc = get_email_service()
    user = engine.get_user_by_id(result["user_id"])
    if user:
        tpl = EmailTemplateEngine.welcome_email(
            user.get("first_name", "User"), user.get("email", "user@example.com").split("@")[0]
        )
        email_svc.send(to_email=user["email"], subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
    return {"status": "success", "data": {"message": "Email verified"}}


@router.post("/login", dependencies=[Depends(write_limiter.check)])
async def login(body: dict, db: Session = Depends(get_db)):
    email = body.get("email")
    password = body.get("password")
    if not email or not password:
        raise _err(400, "MISSING", "email and password required")
    engine = UserEngine(db)
    result = engine.login(email, password)
    if not result["success"]:
        sc = 403 if result.get("requires_verification") else 401
        raise _err(sc, "LOGIN_FAILED", result["error"])
    mode = os.getenv("EOS_AUTH_MODE", "test").lower()
    secret_key = os.getenv("EOS_SECRET_KEY")
    if mode == "production":
        if not secret_key:
            raise _err(500, "SERVER_CONFIG", "EOS_SECRET_KEY is not configured")
    else:
        secret_key = TEST_SECRET_KEY
        if not secret_key:
            raise _err(500, "SERVER_CONFIG", "EOS_TEST_SECRET_KEY is not configured")
    algorithm = os.getenv("EOS_ALGORITHM", TEST_ALGORITHM)
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=60)
    payload = {
        "sub": result["user_id"], "exp": expire, "iat": now, "type": "access",
        "tenant_id": result["tenant_id"], "email": result["email"], "roles": [result["role"]],
    }
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return {"status": "success", "data": {
        "access_token": token, "token_type": "bearer",
        "user": {
            "id": result["user_id"], "email": result["email"],
            "first_name": result.get("first_name"), "last_name": result.get("last_name"),
            "tenant_id": result["tenant_id"], "role": result["role"]
        }
    }}


@router.post("/forgot-password", dependencies=[Depends(write_limiter.check)])
async def forgot_password(body: dict, request: Request, db: Session = Depends(get_db)):
    email = body.get("email")
    if not email:
        raise _err(400, "MISSING", "email required")
    engine = UserEngine(db)
    result = engine.request_password_reset(email)
    db.commit()
    if result.get("reset_token"):
        user = engine.get_user_by_id(result.get("user_id", "")) if result.get("user_id") else None
        first_name = user.get("first_name", "User") if user else "User"
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password?token={result['reset_token']}"
        tpl = EmailTemplateEngine.password_reset_email(reset_url, first_name)
        email_svc = get_email_service()
        email_svc.send(to_email=email, subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
    return {"status": "success", "data": {
        "message": "If email exists, reset link sent",
        "reset_token": result.get("reset_token") if os.getenv("EOS_EMAIL_PROVIDER", "console") == "console" else None
    }}


@router.post("/reset-password")
async def reset_password(body: dict, db: Session = Depends(get_db)):
    token = body.get("token")
    new_password = body.get("new_password")
    if not token or not new_password:
        raise _err(400, "MISSING", "token and new_password required")
    engine = UserEngine(db)
    result = engine.reset_password(token, new_password)
    if not result["success"]:
        raise _err(400, "RESET_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": {"message": "Password reset successful"}}


@router.post("/change-password", dependencies=[Depends(require_permission("dynamic", "update"))])
async def change_password(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    current = body.get("current_password")
    new = body.get("new_password")
    if not current or not new:
        raise _err(400, "MISSING", "current_password and new_password required")
    engine = UserEngine(db)
    result = engine.change_password(user["id"], current, new)
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
async def update_user(user_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.update_user(user_id, user["tenant_id"], body)
    if not result["success"]:
        raise _err(400, "UPDATE_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": {"message": result["message"]}}


@router.put("/users/{user_id}/role", dependencies=[Depends(require_permission("dynamic", "update"))])
async def change_role(user_id: str, body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
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
async def deactivate_user(user_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = UserEngine(db)
    result = engine.deactivate_user(user_id, user["tenant_id"])
    if not result["success"]:
        raise _err(400, "DELETE_FAILED", result["error"])
    db.commit()
    return {"status": "success", "data": {"message": result["message"]}}


@router.post("/users/invite", dependencies=[Depends(require_permission("dynamic", "create"))])
async def invite_user(body: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    email = body.get("email")
    role = body.get("role", "dynamic_viewer")
    if not email:
        raise _err(400, "MISSING", "email required")
    engine = UserEngine(db)
    result = engine.invite_user(
        tenant_id=user["tenant_id"], email=email, role=role,
        first_name=body.get("first_name", ""), last_name=body.get("last_name", "")
    )
    if not result["success"]:
        raise _err(400, "INVITE_FAILED", result["error"])
    db.commit()
    email_svc = get_email_service()
    if result.get("verification_token"):
        frontend_url = os.getenv("EOS_FRONTEND_URL", "http://localhost:3000")
        verify_url = f"{frontend_url}/verify-email?token={result['verification_token']}"
        tpl = EmailTemplateEngine.verification_email(verify_url, body.get("first_name", "User"))
        email_svc.send(to_email=email, subject=tpl["subject"], html_body=tpl["html"], text_body=tpl.get("text"))
    return {"status": "success", "data": {"message": f"Invitation sent to {email}", "user_id": result["user_id"]}}
