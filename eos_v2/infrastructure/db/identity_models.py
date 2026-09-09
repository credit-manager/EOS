from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


class IdentityBase(DeclarativeBase):
    pass


class TenantModel(IdentityBase):
    __tablename__ = "eos_v2_tenants"
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ActorModel(IdentityBase):
    __tablename__ = "eos_v2_actors"
    __table_args__ = (UniqueConstraint("tenant_id", "subject", name="uq_eos_v2_actor_subject"),)
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("eos_v2_tenants.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RoleModel(IdentityBase):
    __tablename__ = "eos_v2_roles"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_eos_v2_role_name"),)
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("eos_v2_tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class ActorRoleModel(IdentityBase):
    __tablename__ = "eos_v2_actor_roles"
    actor_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("eos_v2_actors.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("eos_v2_roles.id", ondelete="CASCADE"), primary_key=True)


class RolePermissionModel(IdentityBase):
    __tablename__ = "eos_v2_role_permissions"
    role_id: Mapped[UUID] = mapped_column(Uuid(), ForeignKey("eos_v2_roles.id", ondelete="CASCADE"), primary_key=True)
    permission: Mapped[str] = mapped_column(String(50), primary_key=True)
