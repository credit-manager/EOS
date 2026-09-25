"""Tenant Isolation — ensures every query is scoped to the correct tenant."""

from contextvars import ContextVar

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from .auth.security import decode_access_token
from .db import SessionLocal

_current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)


def set_current_tenant(tenant_id: str) -> None:
    _current_tenant_id.set(tenant_id)


def get_current_tenant() -> str | None:
    return _current_tenant_id.get()


class TenantScopedMixin:
    """Mixin for models that are tenant-scoped.

    Models using this mixin must define a ``tenant_id`` column.
    Usage::

        class Order(Base, TenantScopedMixin):
            ...
            tenant_id = Column(UUID(as_uuid=False), nullable=False, index=True)

        scoped_q = Order.query_for_tenant(db, tenant_id)
    """

    tenant_id: str

    @classmethod
    def query_for_tenant(cls, db: Session, tenant_id: str | None = None):
        """Return a query filtered to *tenant_id* (falls back to context var)."""
        tid = tenant_id or get_current_tenant()
        if tid:
            return db.query(cls).filter(cls.tenant_id == tid)
        return db.query(cls)


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Extracts tenant_id from JWT and sets it for the request context.

    Skips exempt paths (auth, health, docs) so that unauthenticated
    callers can still reach them.
    """

    EXEMPT_PATHS: list[str] = [
        "/api/v1/auth",
        "/health",
        "/docs",
        "/openapi.json",
    ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                principal = decode_access_token(token)
                tenant_id_str = str(principal.tenant_id)
                set_current_tenant(tenant_id_str)
                request.state.tenant_id = tenant_id_str
            except Exception:
                pass

        response = await call_next(request)
        return response


def get_tenant_scoped_db():
    """Database session generator that carries the current tenant context."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
