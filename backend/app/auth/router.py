from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from .models import Tenant, TenantMembership, User
from .schemas import MeResponse, RegisterRequest, TokenRequest, TokenResponse
from .security import Principal, create_access_token, hash_password, require_principal, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _token_response(user_id: UUID, tenant_id: UUID, role: str) -> TokenResponse:
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user_id=user_id, tenant_id=tenant_id, role=role),
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
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="account could not be created") from exc
    return _token_response(user.id, tenant.id, "admin")


@router.post("/token", response_model=TokenResponse)
def token(payload: TokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
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
    return _token_response(user.id, membership.tenant_id, membership.role)


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
