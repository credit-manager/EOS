from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eos_v2.app.tenant_context import TenantContext, reset_tenant_context, set_tenant_context
from eos_v2.application.identity.authentication import decode_access_token
from eos_v2.application.identity.service import authenticate_access_token
from eos_v2.domain.permissions.policy import Permission
from eos_v2.infrastructure.db.identity_models import ActorModel, ActorRoleModel, IdentityBase, RoleModel, RolePermissionModel, TenantModel
from eos_v2.infrastructure.db.identity_repository import SqlAlchemyIdentityRepository


def test_jwt_requires_exp_and_identity_claims() -> None:
    secret = "x" * 40
    token = jwt.encode({"sub": "user-1", "tenant_id": str(uuid4()), "actor_id": str(uuid4())}, secret, algorithm="HS256")
    with pytest.raises(ValueError, match="Invalid access token"):
        decode_access_token(token, secret)


def test_authenticated_actor_loads_only_current_tenant_permissions() -> None:
    engine = create_engine("sqlite:///:memory:")
    IdentityBase.metadata.create_all(engine)
    tenant = TenantModel(id=uuid4(), name="Acme")
    actor = ActorModel(id=uuid4(), tenant_id=tenant.id, subject="user-1", active=True)
    role = RoleModel(id=uuid4(), tenant_id=tenant.id, name="admin")
    with Session(engine) as session:
        session.add_all([tenant, actor, role, ActorRoleModel(actor_id=actor.id, role_id=role.id), RolePermissionModel(role_id=role.id, permission="read"), RolePermissionModel(role_id=role.id, permission="write")])
        session.commit()
        token = set_tenant_context(TenantContext(tenant.id, actor.id))
        try:
            access = jwt.encode({
                "sub": actor.subject,
                "tenant_id": str(tenant.id),
                "actor_id": str(actor.id),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            }, "x" * 40, algorithm="HS256")
            identity = authenticate_access_token(access, "x" * 40, SqlAlchemyIdentityRepository(session))
            assert identity.actor.id == actor.id
            assert identity.permissions == frozenset({Permission.READ, Permission.WRITE})
        finally:
            reset_tenant_context(token)


def test_token_actor_cannot_cross_tenant_context() -> None:
    engine = create_engine("sqlite:///:memory:")
    IdentityBase.metadata.create_all(engine)
    tenant_a = TenantModel(id=uuid4(), name="A")
    tenant_b = TenantModel(id=uuid4(), name="B")
    actor = ActorModel(id=uuid4(), tenant_id=tenant_a.id, subject="user-1", active=True)
    with Session(engine) as session:
        session.add_all([tenant_a, tenant_b, actor])
        session.commit()
        token = set_tenant_context(TenantContext(tenant_b.id, uuid4()))
        try:
            access = jwt.encode({
                "sub": actor.subject,
                "tenant_id": str(tenant_a.id),
                "actor_id": str(actor.id),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            }, "x" * 40, algorithm="HS256")
            with pytest.raises(KeyError, match="Actor not found"):
                authenticate_access_token(access, "x" * 40, SqlAlchemyIdentityRepository(session))
        finally:
            reset_tenant_context(token)
