from __future__ import annotations

from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from eos_v2.app.tenant_context import TenantContext, clear_tenant_context, set_tenant_context
from eos_v2.application.identity.authentication import decode_access_token
from eos_v2.application.identity.service import authenticate_access_token
from eos_v2.domain.permissions.policy import Permission, authorize
from eos_v2.infrastructure.db.identity_repository import SqlAlchemyIdentityRepository

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


def get_current_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Iterator[object]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    database = getattr(request.app.state, "database", None)
    settings = request.app.state.settings
    if database is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication database unavailable")

    oidc_jwks_client = getattr(request.app.state, "oidc_jwks_client", None)
    try:
        tenant_id, actor_id, _ = decode_access_token(
            credentials.credentials,
            settings.secret_key,
            auth_mode=settings.auth_mode,
            oidc_issuer=settings.oidc_issuer,
            oidc_audience=settings.oidc_audience,
            oidc_jwks_client=oidc_jwks_client,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    set_tenant_context(TenantContext(tenant_id, actor_id))
    try:
        with database.session() as session:
            try:
                identity = authenticate_access_token(
                    credentials.credentials,
                    settings.secret_key,
                    SqlAlchemyIdentityRepository(session),
                    auth_mode=settings.auth_mode,
                    oidc_issuer=settings.oidc_issuer,
                    oidc_audience=settings.oidc_audience,
                    oidc_jwks_client=oidc_jwks_client,
                )
            except (KeyError, ValueError, PermissionError) as exc:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authenticated identity") from exc
            yield identity
    finally:
        # FastAPI may resume generator dependencies in a different AnyIO context.
        clear_tenant_context()


def require_permission(identity, permission: Permission) -> None:
    decision = authorize(identity.actor, identity.tenant.id, permission, identity.permissions)
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)


@router.get("/me")
def current_identity(identity=Depends(get_current_identity)) -> dict[str, object]:
    require_permission(identity, Permission.READ)
    return {
        "actor_id": str(identity.actor.id),
        "tenant_id": str(identity.tenant.id),
        "subject": identity.actor.subject,
        "permissions": sorted(permission.value for permission in identity.permissions),
    }
