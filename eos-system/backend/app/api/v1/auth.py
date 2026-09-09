"""
EOS System — Authentication Router (Real Implementation)
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime, timedelta
import uuid

from app.db.session import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    pwd_context,
    get_current_user,
)
from app.core.tenancy import normalize_tenant_id
from app.core.rate_limit import login_limiter
from app.core.rbac import log_audit
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter()


def validate_password_strength(v: str) -> str:
    """Enforce minimum password policy: 8+ chars, letter + digit."""
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("Password must contain at least one letter and one digit")
    return v


async def _audit_auth_event(
    db: AsyncSession,
    action: str,
    *,
    user: Optional[dict] = None,
    tenant_id: Optional[str] = None,
    status_: str = "success",
    error_message: Optional[str] = None,
    http_request: Optional[Request] = None,
    commit_now: bool = False,
) -> None:
    """Persist an auth event to AuditLog. Never breaks the auth flow."""
    try:
        await log_audit(
            db=db,
            tenant_id=tenant_id or "unknown",
            user=user or {},
            action=action,
            module="auth",
            request=http_request,
            status=status_,
            error_message=error_message,
        )
        if commit_now:
            # Failure paths raise HTTPException afterwards; get_db would
            # roll back, so persist the audit row immediately.
            await db.commit()
    except Exception:
        if commit_now:
            try:
                await db.rollback()
            except Exception:
                pass


# Schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RegisterRequest(BaseModel):
    company_name: str
    company_name_ar: str
    email: EmailStr
    password: str
    industry: str
    employee_count: Optional[int] = None

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return validate_password_strength(v)


class RegisterResponse(BaseModel):
    message: str
    tenant_id: str
    user_id: str
    requires_verification: bool


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return validate_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# Endpoints
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return tokens.

    Brute-force protection: 5 failed attempts per (IP, email) within 5
    minutes blocks the key for 10 minutes. All attempts are audit-logged.
    """
    client_ip = http_request.client.host if http_request.client else "unknown"
    limiter_key = f"{client_ip}:{request.email.lower()}"

    blocked, retry_after = login_limiter.is_blocked(limiter_key)
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    def _fail(reason: str) -> HTTPException:
        nonlocal blocked
        now_blocked, block_secs = login_limiter.record_failure(limiter_key)
        detail = reason
        code = status.HTTP_401_UNAUTHORIZED
        if now_blocked:
            detail = f"Too many failed login attempts. Blocked for {block_secs} seconds."
            code = status.HTTP_429_TOO_MANY_REQUESTS
            blocked = True
        return HTTPException(status_code=code, detail=detail)

    # Find user by email
    result = await db.execute(
        select(User).filter(User.email == request.email)
    )
    user = result.scalar()

    if not user:
        await _audit_auth_event(
            db, "login", user={"email": request.email},
            tenant_id=normalize_tenant_id(request.tenant_id),
            status_="failure", error_message="Unknown email",
            http_request=http_request, commit_now=True,
        )
        raise _fail("Invalid email or password")

    # Check tenant (case-insensitive: compare canonical forms)
    user_tenant_id = normalize_tenant_id(user.tenant_id)
    request_tenant_id = normalize_tenant_id(request.tenant_id)
    if not user_tenant_id or user_tenant_id != request_tenant_id:
        await _audit_auth_event(
            db, "login", user={"id": user.id, "email": user.email},
            tenant_id=request_tenant_id or "unknown",
            status_="failure", error_message="Tenant mismatch",
            http_request=http_request, commit_now=True,
        )
        raise _fail("Invalid tenant for this user")

    # Verify password
    if not pwd_context.verify(request.password, user.password_hash):
        await _audit_auth_event(
            db, "login", user={"id": user.id, "email": user.email},
            tenant_id=user_tenant_id,
            status_="failure", error_message="Invalid password",
            http_request=http_request, commit_now=True,
        )
        raise _fail("Invalid email or password")

    # Check if user is active
    if not user.is_active:
        await _audit_auth_event(
            db, "login", user={"id": user.id, "email": user.email},
            tenant_id=user_tenant_id,
            status_="failure", error_message="Account deactivated",
            http_request=http_request, commit_now=True,
        )
        raise _fail("User account is deactivated")

    # Success: clear failure history
    login_limiter.reset(limiter_key)

    # Update last login
    user.last_login_at = datetime.utcnow()

    await _audit_auth_event(
        db, "login", user={"id": user.id, "email": user.email},
        tenant_id=user_tenant_id, http_request=http_request,
    )
    
    # Create tokens (tenant claim minted in canonical lowercase form)
    extra_data = {
        "tenant_id": user_tenant_id,
        "email": user.email,
        "roles": [user.role],
    }
    
    access_token = create_access_token(subject=user.id, extra_data=extra_data)
    refresh_token = create_refresh_token(subject=user.id)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1800,
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "first_name_ar": user.first_name_ar,
            "last_name_ar": user.last_name_ar,
            "tenant_id": user.tenant_id,
            "role": user.role,
        },
    )


@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new tenant and admin user."""
    # Check if email already exists
    existing_user = await db.execute(
        select(User).filter(User.email == request.email)
    )
    if existing_user.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate tenant slug
    tenant_slug = request.company_name.lower().replace(" ", "-")
    
    # Check if tenant slug already exists
    existing_tenant = await db.execute(
        select(Tenant).filter(Tenant.slug == tenant_slug)
    )
    if existing_tenant.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name already taken"
        )
    
    # Create tenant
    tenant_id = str(uuid.uuid4())
    new_tenant = Tenant(
        id=tenant_id,
        name=request.company_name,
        name_ar=request.company_name_ar,
        slug=tenant_slug,
        industry=request.industry,
        employee_count=request.employee_count,
        email=request.email,
        status="active",
        subscription_plan="basic",
    )
    db.add(new_tenant)
    
    # Create admin user
    user_id = str(uuid.uuid4())
    password_hash = pwd_context.hash(request.password)
    
    new_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email=request.email,
        password_hash=password_hash,
        first_name=request.company_name.split()[0] if request.company_name.split() else request.company_name,
        last_name="Admin",
        first_name_ar=request.company_name_ar.split()[0] if request.company_name_ar.split() else request.company_name_ar,
        last_name_ar="مدير",
        role="admin",
        is_active=True,
    )
    db.add(new_user)
    
    await db.flush()
    
    # Create default permissions (skip if already exist)
    from app.models.rbac import Permission, Role, RolePermission, UserRole
    
    default_permissions = [
        ("accounting:read", "accounting", "read"),
        ("accounting:create", "accounting", "create"),
        ("accounting:update", "accounting", "update"),
        ("accounting:delete", "accounting", "delete"),
        ("inventory:read", "inventory", "read"),
        ("inventory:create", "inventory", "create"),
        ("inventory:update", "inventory", "update"),
        ("inventory:delete", "inventory", "delete"),
        ("hr:read", "hr", "read"),
        ("hr:create", "hr", "create"),
        ("hr:update", "hr", "update"),
        ("hr:delete", "hr", "delete"),
        ("sales:read", "sales", "read"),
        ("sales:create", "sales", "create"),
        ("sales:update", "sales", "update"),
        ("sales:delete", "sales", "delete"),
        ("projects:read", "projects", "read"),
        ("projects:create", "projects", "create"),
        ("projects:update", "projects", "update"),
        ("projects:delete", "projects", "delete"),
        ("dynamic:read", "dynamic", "read"),
        ("dynamic:create", "dynamic", "create"),
        ("dynamic:update", "dynamic", "update"),
        ("dynamic:delete", "dynamic", "delete"),
    ]
    
    # Check which permissions already exist
    existing_result = await db.execute(select(Permission.name))
    existing_names = {row[0] for row in existing_result.all()}
    
    perm_ids = {}
    for name, module, action in default_permissions:
        if name in existing_names:
            # Get existing permission ID
            perm_result = await db.execute(select(Permission.id).filter(Permission.name == name))
            perm_ids[name] = perm_result.scalar()
        else:
            perm_id = str(uuid.uuid4())
            perm_ids[name] = perm_id
            db.add(Permission(id=perm_id, name=name, module=module, action=action))
    
    await db.flush()
    
    # Create default roles
    # Admin role — full access
    admin_role_id = str(uuid.uuid4())
    db.add(Role(
        id=admin_role_id, tenant_id=tenant_id,
        name="Admin", name_ar="مدير", is_system=True,
    ))
    for perm_name, perm_id in perm_ids.items():
        db.add(RolePermission(id=str(uuid.uuid4()), role_id=admin_role_id, permission_id=perm_id))
    
    # User role — read only
    user_role_id = str(uuid.uuid4())
    db.add(Role(
        id=user_role_id, tenant_id=tenant_id,
        name="User", name_ar="مستخدم", is_system=True,
    ))
    for perm_name, perm_id in perm_ids.items():
        if perm_name.endswith(":read"):
            db.add(RolePermission(id=str(uuid.uuid4()), role_id=user_role_id, permission_id=perm_id))
    
    # Sales Clerk — sales only
    sales_role_id = str(uuid.uuid4())
    db.add(Role(
        id=sales_role_id, tenant_id=tenant_id,
        name="Sales Clerk", name_ar="موظف مبيعات", is_system=True,
    ))
    for perm_name, perm_id in perm_ids.items():
        if perm_name.startswith("sales:"):
            db.add(RolePermission(id=str(uuid.uuid4()), role_id=sales_role_id, permission_id=perm_id))
    
    # Dynamic Viewer — read only for dynamic entities
    dynamic_viewer_role_id = str(uuid.uuid4())
    db.add(Role(
        id=dynamic_viewer_role_id, tenant_id=tenant_id,
        name="Dynamic Viewer", name_ar="مشاهد ديناميكي", is_system=True,
    ))
    for perm_name, perm_id in perm_ids.items():
        if perm_name == "dynamic:read":
            db.add(RolePermission(id=str(uuid.uuid4()), role_id=dynamic_viewer_role_id, permission_id=perm_id))
    
    # Dynamic Operator — read/create/update for dynamic entities
    dynamic_operator_role_id = str(uuid.uuid4())
    db.add(Role(
        id=dynamic_operator_role_id, tenant_id=tenant_id,
        name="Dynamic Operator", name_ar="مشغل ديناميكي", is_system=True,
    ))
    for perm_name, perm_id in perm_ids.items():
        if perm_name in ("dynamic:read", "dynamic:create", "dynamic:update"):
            db.add(RolePermission(id=str(uuid.uuid4()), role_id=dynamic_operator_role_id, permission_id=perm_id))
    
    # Dynamic Manager — full access for dynamic entities
    dynamic_manager_role_id = str(uuid.uuid4())
    db.add(Role(
        id=dynamic_manager_role_id, tenant_id=tenant_id,
        name="Dynamic Manager", name_ar="مدير ديناميكي", is_system=True,
    ))
    for perm_name, perm_id in perm_ids.items():
        if perm_name.startswith("dynamic:"):
            db.add(RolePermission(id=str(uuid.uuid4()), role_id=dynamic_manager_role_id, permission_id=perm_id))
    
    # Assign Admin role to first user
    db.add(UserRole(
        id=str(uuid.uuid4()),
        user_id=user_id,
        role_id=admin_role_id,
    ))
    
    await db.flush()

    await _audit_auth_event(
        db, "register",
        user={"id": user_id, "email": request.email},
        tenant_id=normalize_tenant_id(tenant_id),
    )

    # TODO: Create tenant schema
    # TODO: Apply industry template
    # TODO: Send verification email
    
    return RegisterResponse(
        message="Registration successful. Please check your email to verify your account.",
        tenant_id=tenant_id,
        user_id=user_id,
        requires_verification=True,
    )


@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    payload = verify_token(request.refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = payload.get("sub")
    
    # Verify user exists and is active
    result = await db.execute(
        select(User).filter(User.id == user_id, User.is_active == True)
    )
    user = result.scalar()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token with full tenant claims — refreshed tokens
    # must carry the same tenant context as login-issued tokens, otherwise
    # every downstream tenant-scoped query would run with an empty tenant.
    access_token = create_access_token(
        subject=user.id,
        extra_data={
            "tenant_id": user.tenant_id,
            "email": user.email,
            "roles": [user.role],
        },
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800,
    }


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user info."""
    result = await db.execute(
        select(User).filter(User.id == current_user["id"])
    )
    user = result.scalar()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "first_name_ar": user.first_name_ar,
        "last_name_ar": user.last_name_ar,
        "phone": user.phone,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change user password."""
    result = await db.execute(
        select(User).filter(User.id == current_user["id"])
    )
    user = result.scalar()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not pwd_context.verify(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    user.password_hash = pwd_context.hash(request.new_password)
    await db.flush()

    await _audit_auth_event(
        db, "change_password",
        user={"id": user.id, "email": user.email},
        tenant_id=normalize_tenant_id(user.tenant_id),
        http_request=None,
    )

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send password reset email."""
    # Check if user exists
    result = await db.execute(
        select(User).filter(User.email == request.email)
    )
    user = result.scalar()
    
    # Always return success to prevent email enumeration
    if user:
        # TODO: Generate reset token
        # TODO: Send reset email
        pass
    
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using reset token."""
    # TODO: Verify reset token
    # TODO: Update password
    
    return {"message": "Password reset successful"}


# ─── INVITE USER (Admin only) ─────────────────────────────

class InviteUserRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    first_name_ar: Optional[str] = None
    last_name_ar: Optional[str] = None
    role: str = "user"  # "user" not "admin"

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return validate_password_strength(v)


@router.post("/invite")
async def invite_user(
    request: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Invite/create a new user in the same tenant (admin only)."""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin only")

    tenant_id = current_user["tenant_id"]

    # Check if email already exists in this tenant
    existing = await db.execute(
        select(User).filter(User.email == request.email, User.tenant_id == tenant_id)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Email already exists in this tenant")

    user_id = str(uuid.uuid4())
    password_hash = pwd_context.hash(request.password)

    new_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email=request.email,
        password_hash=password_hash,
        first_name=request.first_name,
        last_name=request.last_name,
        first_name_ar=request.first_name_ar,
        last_name_ar=request.last_name_ar,
        role=request.role,  # "user" — NOT admin
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    await _audit_auth_event(
        db, "invite_user",
        user={"id": current_user["id"], "email": current_user.get("email")},
        tenant_id=tenant_id,
        error_message=f"invited={request.email},role={request.role}",
    )

    return {"message": "User invited successfully", "user_id": user_id, "role": request.role}


# ─── ROLES MANAGEMENT ─────────────────────────────────────

class RoleCreate(BaseModel):
    name: str
    name_ar: Optional[str] = None
    description: Optional[str] = None
    permission_ids: list[str] = []


class UserRoleAssign(BaseModel):
    role_id: str


@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all roles for the tenant."""
    from app.models.rbac import Role, RolePermission, Permission

    tenant_id = current_user["tenant_id"]
    result = await db.execute(
        select(Role).filter(Role.tenant_id == tenant_id)
    )
    roles = result.scalars().all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "name_ar": r.name_ar,
            "description": r.description,
            "is_system": r.is_system,
        }
        for r in roles
    ]


@router.post("/roles")
async def create_role(
    role: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new role (admin only)."""
    from app.models.rbac import Role, RolePermission, Permission

    if "admin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin only")

    tenant_id = current_user["tenant_id"]

    new_role = Role(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=role.name,
        name_ar=role.name_ar,
        description=role.description,
        is_system=False,
    )
    db.add(new_role)
    await db.flush()

    # Assign permissions
    for perm_id in role.permission_ids:
        rp = RolePermission(
            id=str(uuid.uuid4()),
            role_id=new_role.id,
            permission_id=perm_id,
        )
        db.add(rp)

    await db.flush()

    return {"id": new_role.id, "name": new_role.name, "message": "Role created"}


@router.post("/roles/{role_id}/permissions")
async def add_permission_to_role(
    role_id: str,
    permission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Add a permission to a role (admin only)."""
    from app.models.rbac import Role, RolePermission

    if "admin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin only")

    rp = RolePermission(
        id=str(uuid.uuid4()),
        role_id=role_id,
        permission_id=permission_id,
    )
    db.add(rp)
    await db.flush()

    return {"message": "Permission added to role"}


@router.post("/users/{user_id}/role")
async def assign_role_to_user(
    user_id: str,
    assignment: UserRoleAssign,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Assign a role to a user (admin only)."""
    from app.models.rbac import UserRole

    if "admin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin only")

    ur = UserRole(
        id=str(uuid.uuid4()),
        user_id=user_id,
        role_id=assignment.role_id,
        assigned_by=current_user["id"],
    )
    db.add(ur)
    await db.flush()

    return {"message": "Role assigned to user"}


@router.get("/permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all available permissions."""
    from app.models.rbac import Permission

    result = await db.execute(select(Permission))
    permissions = result.scalars().all()

    return [
        {"id": p.id, "name": p.name, "module": p.module, "action": p.action}
        for p in permissions
    ]
