from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eos_v2.app.app import create_app
from eos_v2.app.config import Settings
from eos_v2.infrastructure.db.identity_models import ActorModel, ActorRoleModel, IdentityBase, RoleModel, RolePermissionModel, TenantModel
from eos_v2.infrastructure.db.metadata_models import Base as MetadataBase
from eos_v2.infrastructure.db.record_models import RecordBase


def test_authenticated_metadata_and_record_api() -> None:
    engine = create_engine("sqlite:///file:eos_v2_api?mode=memory&cache=shared&uri=true")
    IdentityBase.metadata.create_all(engine)
    MetadataBase.metadata.create_all(engine)
    RecordBase.metadata.create_all(engine)
    tenant = TenantModel(id=uuid4(), name="Acme")
    actor = ActorModel(id=uuid4(), tenant_id=tenant.id, subject="api-user")
    role = RoleModel(id=uuid4(), tenant_id=tenant.id, name="platform-admin")
    with Session(engine) as session:
        session.add_all([
            tenant, actor, role,
            ActorRoleModel(actor_id=actor.id, role_id=role.id),
            RolePermissionModel(role_id=role.id, permission="read"),
            RolePermissionModel(role_id=role.id, permission="write"),
            RolePermissionModel(role_id=role.id, permission="admin"),
        ])
        session.commit()

    secret = "s" * 40
    token = jwt.encode({
        "sub": actor.subject,
        "tenant_id": str(tenant.id),
        "actor_id": str(actor.id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }, secret, algorithm="HS256")
    app = create_app(Settings(environment="test", database_url="sqlite:///file:eos_v2_api?mode=memory&cache=shared&uri=true", secret_key=secret))
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(tenant.id)

    metadata = client.post("/api/v1/metadata", headers=headers, json={
        "name": "customer",
        "label": "Customer",
        "fields": [{"name": "code", "field_type": "text", "required": True, "unique": True}],
    })
    assert metadata.status_code == 201, metadata.text
    entity_id = metadata.json()["id"]

    created = client.post(f"/api/v1/entities/{entity_id}/records", headers=headers, json={"data": {"code": "C-001"}})
    assert created.status_code == 201, created.text
    record_id = created.json()["id"]
    assert created.json()["row_version"] == 1

    duplicate = client.post(f"/api/v1/entities/{entity_id}/records", headers=headers, json={"data": {"code": "C-001"}})
    assert duplicate.status_code == 409

    fetched = client.get(f"/api/v1/records/{record_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["data"]["code"] == "C-001"


def test_record_api_requires_authentication() -> None:
    app = create_app(Settings(environment="test"))
    client = TestClient(app)
    response = client.get(f"/api/v1/records/{uuid4()}")
    assert response.status_code == 401
