from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit.service import record as audit_record
from ..config import get_settings
from ..db import get_db
from .models import Tenant, TenantMembership, User
from .schemas import (
    MemberCreateRequest,
    MemberResponse,
    MemberRoleUpdate,
    MeResponse,
    RegisterRequest,
    TokenRequest,
    TokenResponse,
)
from .security import (
    Principal,
    create_access_token,
    hash_password,
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
    access_token, session = create_access_token(user_id=user_id, tenant_id=tenant_id, role=role)
    db.add(session)
    db.flush()
    return TokenResponse(
        access_token=access_token,
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        expires_in=settings.access_token_ttl_seconds,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="email already registered")
    tenant = Tenant(name=payload.tenant_name.strip())
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add_all([tenant, user])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="admin"))
    try:
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
