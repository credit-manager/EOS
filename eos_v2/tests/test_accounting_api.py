from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eos_v2.app.app import create_app
from eos_v2.app.config import Settings
from eos_v2.infrastructure.db.accounting_models import AccountingBase
from eos_v2.infrastructure.db.identity_models import ActorModel, ActorRoleModel, IdentityBase, RoleModel, RolePermissionModel, TenantModel


def test_accounting_api_posts_balanced_entry() -> None:
    engine = create_engine("sqlite:///file:eos_v2_accounting?mode=memory&cache=shared&uri=true")
    IdentityBase.metadata.create_all(engine)
    AccountingBase.metadata.create_all(engine)
    tenant = TenantModel(id=uuid4(), name="Acme")
    actor = ActorModel(id=uuid4(), tenant_id=tenant.id, subject="accountant")
    role = RoleModel(id=uuid4(), tenant_id=tenant.id, name="accounting-admin")
    tenant_id, actor_id, actor_subject = tenant.id, actor.id, actor.subject
    with Session(engine) as session:
        session.add_all([
            tenant, actor, role,
            ActorRoleModel(actor_id=actor_id, role_id=role.id),
            RolePermissionModel(role_id=role.id, permission="write"),
            RolePermissionModel(role_id=role.id, permission="admin"),
        ])
        session.commit()

    secret = "a" * 40
    token = jwt.encode({"sub": actor_subject, "tenant_id": str(tenant_id), "actor_id": str(actor_id), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, secret, algorithm="HS256")
    app = create_app(Settings(environment="test", database_url="sqlite:///file:eos_v2_accounting?mode=memory&cache=shared&uri=true", secret_key=secret))
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    cash = client.post("/api/v1/accounting/accounts", headers=headers, json={"code": "1000", "name": "Cash", "account_type": "asset"})
    revenue = client.post("/api/v1/accounting/accounts", headers=headers, json={"code": "4000", "name": "Revenue", "account_type": "revenue"})
    assert cash.status_code == 201
    assert revenue.status_code == 201
    entry = client.post("/api/v1/accounting/journal-entries", headers=headers, json={"entry_date": "2026-09-06", "currency": "usd", "description": "Sale", "lines": [{"account_id": cash.json()["id"], "debit": "100.00", "credit": "0"}, {"account_id": revenue.json()["id"], "debit": "0", "credit": "100.00"}]})
    assert entry.status_code == 201, entry.text
    assert entry.json()["posted"] is True
    assert entry.json()["currency"] == "USD"
