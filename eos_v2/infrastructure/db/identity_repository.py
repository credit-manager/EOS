from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import get_tenant_context
from eos_v2.domain.identity.entities import Actor
from eos_v2.domain.permissions.policy import Permission
from eos_v2.domain.tenancy.entities import Tenant
from eos_v2.infrastructure.db.identity_models import ActorModel, ActorRoleModel, RolePermissionModel, TenantModel


class SqlAlchemyIdentityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_tenant(self, tenant_id: UUID) -> Tenant:
        model = self.session.scalar(select(TenantModel).where(TenantModel.id == tenant_id))
        if model is None:
            raise KeyError("Tenant not found")
        return Tenant(id=model.id, name=model.name, active=model.active)

    def get_actor(self, actor_id: UUID) -> Actor:
        tenant_id = get_tenant_context().tenant_id
        model = self.session.scalar(select(ActorModel).where(
            ActorModel.id == actor_id,
            ActorModel.tenant_id == tenant_id,
        ))
        if model is None:
            raise KeyError("Actor not found")
        return Actor(id=model.id, tenant_id=model.tenant_id, subject=model.subject, active=model.active)

    def get_actor_permissions(self, actor_id: UUID) -> frozenset[Permission]:
        tenant_id = get_tenant_context().tenant_id
        rows = self.session.execute(
            select(RolePermissionModel.permission)
            .join(ActorRoleModel, ActorRoleModel.role_id == RolePermissionModel.role_id)
            .join(ActorModel, ActorModel.id == ActorRoleModel.actor_id)
            .where(
                ActorModel.id == actor_id,
                ActorModel.tenant_id == tenant_id,
                ActorModel.active.is_(True),
            )
        ).scalars()
        return frozenset(Permission(value) for value in rows)

    def get_actor_by_subject(self, subject: str) -> Actor:
        tenant_id = get_tenant_context().tenant_id
        model = self.session.scalar(select(ActorModel).where(
            ActorModel.tenant_id == tenant_id,
            ActorModel.subject == subject,
        ))
        if model is None:
            raise KeyError("Actor not found")
        return Actor(id=model.id, tenant_id=model.tenant_id, subject=model.subject, active=model.active)
