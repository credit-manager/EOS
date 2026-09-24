from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..config import get_settings
from ..db import get_db
from ..events.service import publish as publish_event
from .models import AuthSession, Tenant, TenantMembership, User
from .schemas import (
    MemberCreateRequest,
    MemberResponse,
    MemberRoleUpdate,
    MeResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenRequest,
    TokenResponse,
)
from .password_policy import validate_password
from .rate_limiting import check_auth_rate_limit, reset_rate_limit
from .security import (
    Principal,
    create_access_token,
    hash_password,
    hash_token,
    require_principal,
    revoke_session,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _forbidden(
    db: Session, request: Request, principal: Principal, path: str
) -> None:
    audit_record(
        db,
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        action="auth.forbidden",
        resource_type="route",
        resource_id=None,
        metadata={"path": path, "role": principal.role},
        request_id=request.state.request_id,
    )
    db.commit()


def _token_response(user_id: UUID, tenant_id: UUID, role: str, db: Session) -> TokenResponse:
    settings = get_settings()
    access_token, refresh_token, session = create_access_token(user_id=user_id, tenant_id=tenant_id, role=role)
    db.add(session)
    db.flush()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        expires_in=settings.access_token_ttl_seconds,
        refresh_expires_in=settings.refresh_token_ttl_seconds,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    is_valid, errors = validate_password(payload.password)
    if not is_valid:
        raise HTTPException(status_code=422, detail="; ".join(errors))
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="email already registered")
    tenant = Tenant(name=payload.tenant_name.strip())
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add_all([tenant, user])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="admin"))
    try:
        publish_event(
            db,
            tenant_id=tenant.id,
            event_type="auth.user.registered",
            entity_type="user",
            entity_id=str(user.id),
            actor_id=str(user.id),
            payload={"email": email},
        )
        response = _token_response(user.id, tenant.id, "admin", db)
        audit_record(
            db,
            tenant_id=tenant.id,
            actor_id=user.id,
            action="auth.registered",
            resource_type="user",
            resource_id=user.id,
            metadata={"email": email},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="account could not be created") from exc
    return response


@router.post("/token", response_model=TokenResponse)
def token(payload: TokenRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    rate_key = f"auth:token:{request.client.host if request.client else 'unknown'}"
    if not check_auth_rate_limit(rate_key, max_attempts=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="too many login attempts, please try again later")
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        if user is not None:
            tenant_id = payload.tenant_id
            if tenant_id is None:
                first = db.scalar(
                    select(TenantMembership)
                    .where(TenantMembership.user_id == user.id)
                    .order_by(TenantMembership.created_at)
                )
                tenant_id = first.tenant_id if first is not None else None
            if tenant_id is not None:
                audit_record(
                    db,
                    tenant_id=tenant_id,
                    actor_id=user.id,
                    action="auth.login_failed",
                    resource_type="user",
                    resource_id=user.id,
                    metadata={"email": email},
                    request_id=request.state.request_id,
                )
                db.commit()
        raise HTTPException(status_code=401, detail="invalid email or password")
    memberships = db.scalars(
        select(TenantMembership).where(TenantMembership.user_id == user.id).order_by(TenantMembership.created_at)
    ).all()
    if payload.tenant_id is not None:
        membership = next((item for item in memberships if item.tenant_id == payload.tenant_id), None)
        if membership is None:
            raise HTTPException(status_code=403, detail="tenant membership not found")
    elif len(memberships) == 1:
        membership = memberships[0]
    else:
        raise HTTPException(status_code=409, detail="tenant_id is required for multi-tenant users")
    response = _token_response(user.id, membership.tenant_id, membership.role, db)
    reset_rate_limit(rate_key)
    audit_record(
        db,
        tenant_id=membership.tenant_id,
        actor_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=user.id,
        metadata={"email": email},
        request_id=request.state.request_id,
    )
    db.commit()
    return response


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    session = db.scalar(
        select(AuthSession).where(AuthSession.refresh_token_hash == hash_token(payload.refresh_token))
    )
    if session is None:
        raise HTTPException(status_code=401, detail="invalid refresh token")

    if session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="session is revoked")

    if session.refresh_expires_at is not None and session.refresh_expires_at.replace(tzinfo=UTC) <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="refresh token expired")

    session.revoked_at = datetime.now(UTC)
    session.refresh_token_hash = None
    db.flush()

    user = db.scalar(select(User).where(User.id == session.user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=401, detail="user not found or inactive")

    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == session.user_id,
            TenantMembership.tenant_id == session.tenant_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="tenant membership not found")

    response = _token_response(session.user_id, session.tenant_id, membership.role, db)

    audit_record(
        db,
        tenant_id=session.tenant_id,
        actor_id=session.user_id,
        action="auth.token_refreshed",
        resource_type="auth_session",
        resource_id=session.id,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return response


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> None:
    revoke_session(db, principal.session_id)
    audit_record(
        db,
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        action="auth.logout",
        resource_type="auth_session",
        resource_id=principal.session_id,
        request_id=request.state.request_id,
    )
    db.commit()


@router.get("/me", response_model=MeResponse)
def me(principal: Principal = Depends(require_principal), db: Session = Depends(get_db)) -> MeResponse:
    user = db.get(User, principal.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return MeResponse(
        user_id=user.id,
        email=user.email,
        tenant_id=principal.tenant_id,
        role=principal.role,
    )


@router.get("/members", response_model=list[MemberResponse])


def list_members(
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> list[MemberResponse]:
    if principal.role != "admin":
        _forbidden(db, request, principal, "/api/v1/auth/members")
        raise HTTPException(status_code=403, detail="admin role required")
    rows = db.execute(
        select(TenantMembership, User)
        .join(User, User.id == TenantMembership.user_id)
        .where(TenantMembership.tenant_id == principal.tenant_id)
        .order_by(User.email)
    ).all()
    return [
        MemberResponse(
            user_id=user.id,
            email=user.email,
            tenant_id=membership.tenant_id,
            role=membership.role,
        )
        for membership, user in rows
    ]


@router.post("/members", response_model=MemberResponse, status_code=201)
def add_member(
    payload: MemberCreateRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> MemberResponse:
    if principal.role != "admin":
        _forbidden(db, request, principal, "/api/v1/auth/members")
        raise HTTPException(status_code=403, detail="admin role required")
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=404, detail="user must register before being added to a tenant")
    existing = db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == principal.tenant_id,
            TenantMembership.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="user is already a tenant member")
    membership = TenantMembership(tenant_id=principal.tenant_id, user_id=user.id, role=payload.role)
    db.add(membership)
    audit_record(
        db,
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        action="tenant.member_added",
        resource_type="tenant_membership",
        resource_id=membership.id,
        metadata={"user_id": str(user.id), "role": payload.role},
        request_id=request.state.request_id,
    )
    db.commit()
    return MemberResponse(user_id=user.id, email=user.email, tenant_id=membership.tenant_id, role=membership.role)


@router.patch("/members/{user_id}", response_model=MemberResponse)
def update_member_role(
    user_id: UUID,
    payload: MemberRoleUpdate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> MemberResponse:
    if principal.role != "admin":
        _forbidden(db, request, principal, f"/api/v1/auth/members/{user_id}")
        raise HTTPException(status_code=403, detail="admin role required")
    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == principal.tenant_id,
            TenantMembership.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="tenant member not found")
    if membership.role == "admin" and payload.role != "admin":
        admin_count = db.scalar(
            select(func.count()).select_from(TenantMembership).where(
                TenantMembership.tenant_id == principal.tenant_id,
                TenantMembership.role == "admin",
            )
        )
        if admin_count == 1:
            raise HTTPException(status_code=409, detail="cannot remove the last tenant admin")
    membership.role = payload.role
    audit_record(
        db,
        tenant_id=principal.tenant_id,
        actor_id=principal.user_id,
        action="tenant.member_role_changed",
        resource_type="tenant_membership",
        resource_id=membership.id,
        metadata={"user_id": str(user_id), "role": payload.role},
        request_id=request.state.request_id,
    )
    db.commit()
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return MemberResponse(user_id=user.id, email=user.email, tenant_id=membership.tenant_id, role=membership.role)


# ---------------------------------------------------------------------------
# Enterprise Admin - SSO Configuration
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field


class SSOConfigCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    client_id: str | None = None
    client_secret: str | None = None
    metadata_url: str | None = None
    redirect_url: str | None = None
    domain: str | None = None


class SSOConfigResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    provider: str
    name: str
    client_id: str | None
    metadata_url: str | None
    redirect_url: str | None
    domain: str | None
    is_active: bool
    created_at: datetime


@router.get("/sso", response_model=list[SSOConfigResponse])
def list_sso_configs(
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    from .models import SSOConfiguration
    configs = db.scalars(
        select(SSOConfiguration).where(SSOConfiguration.tenant_id == principal.tenant_id)
    ).all()
    return [SSOConfigResponse(
        id=c.id, tenant_id=c.tenant_id, provider=c.provider, name=c.name,
        client_id=c.client_id, metadata_url=c.metadata_url, redirect_url=c.redirect_url,
        domain=c.domain, is_active=c.is_active, created_at=c.created_at,
    ) for c in configs]


@router.post("/sso", response_model=SSOConfigResponse, status_code=201)
def create_sso_config(
    payload: SSOConfigCreate,
    request: Request,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    from .models import SSOConfiguration
    config = SSOConfiguration(
        tenant_id=principal.tenant_id,
        provider=payload.provider,
        name=payload.name,
        client_id=payload.client_id,
        client_secret=payload.client_secret,
        metadata_url=payload.metadata_url,
        redirect_url=payload.redirect_url,
        domain=payload.domain,
    )
    db.add(config)
    audit_record(
        db, tenant_id=principal.tenant_id, actor_id=principal.user_id,
        action="auth.sso_config_created", resource_type="sso_config",
        resource_id=config.id, metadata={"provider": payload.provider},
        request_id=request.state.request_id,
    )
    db.commit()
    db.refresh(config)
    return SSOConfigResponse(
        id=config.id, tenant_id=config.tenant_id, provider=config.provider,
        name=config.name, client_id=config.client_id, metadata_url=config.metadata_url,
        redirect_url=config.redirect_url, domain=config.domain,
        is_active=config.is_active, created_at=config.created_at,
    )


# ---------------------------------------------------------------------------
# Enterprise Admin - Audit Trail
# ---------------------------------------------------------------------------

@router.get("/audit-trail")
def get_audit_trail(
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(None),
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    from ..audit.models import AuditEvent
    q = select(AuditEvent).where(AuditEvent.tenant_id == principal.tenant_id)
    if action:
        q = q.where(AuditEvent.action == action)
    events = db.scalars(q.order_by(AuditEvent.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": e.id,
            "actor_id": e.actor_id,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "metadata": e.metadata_json,
            "created_at": e.created_at,
        }
        for e in events
    ]


# ---------------------------------------------------------------------------
# Enterprise Admin - Role Permissions
# ---------------------------------------------------------------------------

class RolePermissionCreate(BaseModel):
    role: str = Field(min_length=1, max_length=30)
    resource: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=50)
    allowed: bool = True


class RolePermissionResponse(BaseModel):
    id: UUID
    role: str
    resource: str
    action: str
    allowed: bool


@router.get("/permissions", response_model=list[RolePermissionResponse])
def list_permissions(
    role: str | None = Query(None),
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    from .models import RolePermission
    q = select(RolePermission).where(RolePermission.tenant_id == principal.tenant_id)
    if role:
        q = q.where(RolePermission.role == role)
    perms = db.scalars(q.order_by(RolePermission.role, RolePermission.resource)).all()
    return [RolePermissionResponse(
        id=p.id, role=p.role, resource=p.resource, action=p.action, allowed=p.allowed,
    ) for p in perms]


@router.post("/permissions", response_model=RolePermissionResponse, status_code=201)
def create_permission(
    payload: RolePermissionCreate,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
):
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    from .models import RolePermission
    perm = RolePermission(
        tenant_id=principal.tenant_id,
        role=payload.role,
        resource=payload.resource,
        action=payload.action,
        allowed=payload.allowed,
    )
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return RolePermissionResponse(
        id=perm.id, role=perm.role, resource=perm.resource, action=perm.action, allowed=perm.allowed,
    )


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/password")
def change_password(
    payload: ChangePasswordRequest,
    principal: Principal = Depends(require_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Change the current user's password."""
    from .password_policy import validate_password

    user = db.query(User).filter(User.id == principal.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")

    errors = validate_password(payload.new_password)
    if errors:
        raise HTTPException(422, detail={"errors": errors})

    user.hashed_password = hash_password(payload.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


# ---------------------------------------------------------------------------
# SSO / OAuth2 endpoints
# ---------------------------------------------------------------------------

from .sso import SSOService


class SSOAuthURLRequest(BaseModel):
    provider: str
    redirect_uri: str


class SSOCallbackRequest(BaseModel):
    provider: str
    code: str
    state: str
    redirect_uri: str


@router.post("/sso/auth-url")
def get_sso_auth_url(payload: SSOAuthURLRequest) -> dict:
    """Get the SSO authorization URL for a provider."""
    sso = SSOService(get_settings().model_dump())
    result = sso.get_auth_url(payload.provider, payload.redirect_uri)
    return result


@router.post("/sso/callback")
def sso_callback(
    payload: SSOCallbackRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Handle SSO callback — exchange code and create/find user."""
    from ..config import get_settings as _gs
    from .security import create_access_token, hash_password

    sso = SSOService(_gs().model_dump())

    if not sso.validate_state(payload.state):
        raise HTTPException(400, "Invalid or expired SSO state")

    tokens = sso.exchange_code(payload.provider, payload.code, payload.redirect_uri)
    if "error" in tokens:
        raise HTTPException(400, f"SSO token exchange failed: {tokens['error']}")

    user_info = sso.get_user_info(payload.provider, tokens.get("access_token", ""))
    if "error" in user_info:
        raise HTTPException(400, f"SSO userinfo failed: {user_info['error']}")

    email = user_info.get("email", "")
    if not email:
        raise HTTPException(400, "No email in SSO response")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        tenant = Tenant(name=f"{email}'s Organization")
        db.add(tenant)
        db.flush()
        user = User(
            email=email,
            display_name=user_info.get("name", email),
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            tenant_id=tenant.id,
            role="user",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access, refresh, session = create_access_token(
        user_id=user.id, tenant_id=user.tenant_id, role=user.role,
    )

    from .security import hash_token
    from .models import AuthSession
    auth_session = AuthSession(
        user_id=user.id,
        tenant_id=user.tenant_id,
        refresh_token_hash=hash_token(refresh),
        user_agent="sso",
        ip_address=None,
        expires_at=session.expires_at,
    )
    db.add(auth_session)
    db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
        expires_in=session.expires_in,
        refresh_expires_in=session.refresh_expires_in,
    )
