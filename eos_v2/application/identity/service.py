from __future__ import annotations

from typing import Protocol
from uuid import UUID

from eos_v2.application.identity.authentication import AuthenticatedIdentity, decode_access_token
from eos_v2.domain.identity.entities import Actor
from eos_v2.domain.permissions.policy import Permission
from eos_v2.domain.tenancy.entities import Tenant


class IdentityRepository(Protocol):
    def get_tenant(self, tenant_id: UUID) -> Tenant: ...
    def get_actor(self, actor_id: UUID) -> Actor: ...
    def get_actor_permissions(self, actor_id: UUID) -> frozenset[Permission]: ...


def authenticate_access_token(token: str, secret_key: str, repository: IdentityRepository) -> AuthenticatedIdentity:
    tenant_id, actor_id, subject = decode_access_token(token, secret_key)
    tenant = repository.get_tenant(tenant_id)
    if not tenant.active:
        raise PermissionError("Tenant is inactive")
    actor = repository.get_actor(actor_id)
    if actor.subject != subject or actor.tenant_id != tenant_id:
        raise PermissionError("Token identity does not match tenant actor")
    if not actor.active:
        raise PermissionError("Actor is inactive")
    return AuthenticatedIdentity(actor, tenant, repository.get_actor_permissions(actor.id))
