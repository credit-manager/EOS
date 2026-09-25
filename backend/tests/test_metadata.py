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


def test_metadata_catalog_lists_only_published_latest_versions() -> None:
    headers, _ = _register()
    first = {"code": "catalog_a", "name": "Catalog A", "fields": [{"code": "name", "type": "text"}]}
    second = {"code": "catalog_b", "name": "Catalog B", "fields": [{"code": "amount", "type": "decimal"}]}
    assert client.post("/api/v1/metadata/entities", json=first, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/catalog_a/publish", headers=headers).status_code == 200
    assert client.post("/api/v1/metadata/entities", json=second, headers=headers).status_code == 201

    hidden = client.get("/api/v1/metadata/entities", headers=headers)
    assert hidden.status_code == 200
    assert {item["code"] for item in hidden.json()} == {"catalog_a"}

    revised = {
        **first,
        "name": "Catalog A Revised",
        "fields": [
            {"code": "name", "type": "text"},
            {"code": "active", "type": "boolean"},
        ],
    }
    created = client.post("/api/v1/metadata/entities", json=revised, headers=headers)
    assert created.status_code == 201
    assert created.json()["version"] == 2
    assert client.post("/api/v1/metadata/entities/catalog_a/publish", headers=headers).status_code == 200

    catalog = client.get("/api/v1/metadata/entities", headers=headers)
    assert catalog.status_code == 200
    items = {item["code"]: item for item in catalog.json()}
    assert items["catalog_a"]["name"] == "Catalog A Revised"
    assert items["catalog_a"]["version"] == 2
    assert items["catalog_a"]["field_count"] == 2


def test_metadata_catalog_is_tenant_scoped() -> None:
    headers, _ = _register()
    other_headers, _ = _register()
    payload = {"code": "private_entity", "name": "Private Entity", "fields": [{"code": "name", "type": "text"}]}
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/private_entity/publish", headers=headers).status_code == 200

    other_catalog = client.get("/api/v1/metadata/entities", headers=other_headers)
    assert other_catalog.status_code == 200
    assert all(item["code"] != "private_entity" for item in other_catalog.json())


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

    filtered = client.get(
        "/api/v1/entities/typed_example/records",
        params={"filter_field": "quantity", "filter_value": "3", "limit": 1},
        headers=headers,
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    invalid = {**valid, "data": {**valid["data"], "quantity": True}}
    response = client.post("/api/v1/entities/typed_example/records", json=invalid, headers=headers)
    assert response.status_code == 422
    assert "quantity" in str(response.json()["detail"])


def test_metadata_relations_are_tenant_scoped() -> None:
    headers, tenant_id = _register()
    other_headers, _ = _register()

    target = {"code": "worker", "name": "Worker", "fields": [{"code": "name", "type": "text", "required": True}]}
    assert client.post("/api/v1/metadata/entities", json=target, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/worker/publish", headers=headers).status_code == 200

    target_record = client.post(
        "/api/v1/entities/worker/records", json={"data": {"name": "Alice"}}, headers=headers
    )
    assert target_record.status_code == 201
    target_id = target_record.json()["id"]

    assignment = {
        "code": "assignment",
        "name": "Assignment",
        "fields": [{"code": "worker_id", "type": "relation", "target_entity": "worker", "required": True}],
    }
    assert client.post("/api/v1/metadata/entities", json=assignment, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/assignment/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/assignment/records",
        json={"data": {"worker_id": target_id}},
        headers=headers,
    )
    assert valid.status_code == 201
    assert valid.json()["tenant_id"] == str(tenant_id)

    wrong_tenant = client.post(
        "/api/v1/entities/assignment/records",
        json={"data": {"worker_id": target_id}},
        headers=other_headers,
    )
    assert wrong_tenant.status_code == 404


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
