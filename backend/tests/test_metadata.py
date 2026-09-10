from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.auth.models import TenantMembership, User
from backend.app.db import SessionLocal
from backend.app.main import app

client = TestClient(app)


def _register() -> tuple[dict[str, str], UUID]:
    email = f"user-{uuid4()}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Correct-Horse-Battery-42",
            "tenant_name": f"Tenant {uuid4()}",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, UUID(payload["tenant_id"])


def test_metadata_to_generic_crud_and_tenant_isolation() -> None:
    headers, tenant_id = _register()
    other_headers, _ = _register()
    payload = {
        "code": "subcontractor_evaluation",
        "name": "Subcontractor Evaluation",
        "fields": [
            {"code": "quality", "type": "integer", "required": True, "label": "Quality"},
            {"code": "safety", "type": "integer", "required": True, "label": "Safety"},
        ],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/subcontractor_evaluation/publish", headers=headers).status_code == 200

    created = client.post(
        "/api/v1/entities/subcontractor_evaluation/records",
        json={"data": {"quality": 90, "safety": 95}},
        headers=headers,
    )
    assert created.status_code == 201
    record = created.json()
    record_id = UUID(record["id"])
    assert record["tenant_id"] == str(tenant_id)
    assert record["version"] == 1

    listing = client.get("/api/v1/entities/subcontractor_evaluation/records", headers=headers)
    assert listing.status_code == 200
    assert any(item["id"] == str(record_id) for item in listing.json())

    conflict = client.patch(
        f"/api/v1/entities/subcontractor_evaluation/records/{record_id}",
        json={"data": {"quality": 91, "safety": 95}, "version": 99},
        headers=headers,
    )
    assert conflict.status_code == 409

    other_tenant = client.get(
        f"/api/v1/entities/subcontractor_evaluation/records/{record_id}",
        headers=other_headers,
    )
    assert other_tenant.status_code == 404


def test_generic_record_type_validation() -> None:
    headers, _ = _register()
    payload = {
        "code": "typed_example",
        "name": "Typed Example",
        "fields": [
            {"code": "name", "type": "text"},
            {"code": "quantity", "type": "integer"},
            {"code": "amount", "type": "decimal"},
            {"code": "active", "type": "boolean"},
            {"code": "due_date", "type": "date"},
            {"code": "external_id", "type": "uuid"},
            {"code": "notes", "type": "text", "nullable": True},
        ],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/typed_example/publish", headers=headers).status_code == 200

    valid = {
        "data": {
            "name": "Demo",
            "quantity": 3,
            "amount": "125.50",
            "active": True,
            "due_date": "2026-09-11",
            "external_id": str(uuid4()),
            "notes": None,
        }
    }
    assert client.post("/api/v1/entities/typed_example/records", json=valid, headers=headers).status_code == 201

    invalid = {**valid, "data": {**valid["data"], "quantity": True}}
    response = client.post("/api/v1/entities/typed_example/records", json=invalid, headers=headers)
    assert response.status_code == 422
    assert "quantity" in str(response.json()["detail"])


def test_duplicate_metadata_field_codes_are_rejected() -> None:
    headers, _ = _register()
    payload = {
        "code": "duplicate_fields",
        "name": "Duplicate Fields",
        "fields": [
            {"code": "name", "type": "text"},
            {"code": "name", "type": "text"},
        ],
    }
    response = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert response.status_code == 422


def test_metadata_administration_requires_admin_role() -> None:
    headers, _ = _register()
    me = client.get("/api/v1/auth/me", headers=headers).json()
    with SessionLocal() as db:
        user = db.get(User, UUID(me["user_id"]))
        assert user is not None
        membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == user.id))
        assert membership is not None
        membership.role = "member"
        db.commit()

    payload = {"code": "member_blocked", "name": "Blocked", "fields": [{"code": "name", "type": "text"}]}
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 403
