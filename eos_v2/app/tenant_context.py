from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantContext:
    tenant_id: UUID
    actor_id: UUID | None = None


_current: ContextVar[TenantContext | None] = ContextVar("eos_tenant_context", default=None)


def set_tenant_context(context: TenantContext):
    return _current.set(context)


def reset_tenant_context(token) -> None:
    _current.reset(token)


def get_tenant_context() -> TenantContext:
    context = _current.get()
    if context is None:
        raise RuntimeError("Tenant context is required for tenant-scoped operations")
    return context
