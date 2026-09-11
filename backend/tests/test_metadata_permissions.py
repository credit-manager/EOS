from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
_PASSWORD = "Correct-Horse-Battery-42"


def _register(email: str, tenant_name: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD, "tenant_name": tenant_name},
    )
    assert response.status_code == 201
    return response.json()


def test_member_permissions_are_driven_by_metadata() -> None:
    admin = _register(f"admin-{uuid4()}@example.com", f"Tenant {uuid4()}")
    member = _register(f"member-{uuid4()}@example.com", f"Tenant {uuid4()}")
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}

    added = client.post(
        "/api/v1/auth/members",
        json={"email": member["email"], "role": "member"},
        headers=admin_headers,
    )
    assert added.status_code == 201

    member_login = client.post(
        "/api/v1/auth/token",
        json={"email": member["email"], "password": _PASSWORD, "tenant_id": admin["tenant_id"]},
    )
    assert member_login.status_code == 200
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}

    entity = {
        "code": "restricted_document",
        "name": "Restricted Document",
        "fields": [{"code": "title", "type": "text", "required": True}],
        "permissions": {"admin": ["create", "read", "update", "delete"], "member": ["read"]},
    }
    created = client.post("/api/v1/metadata/entities", json=entity, headers=admin_headers)
    assert created.status_code == 201
    assert client.post("/api/v1/metadata/entities/restricted_document/publish", headers=admin_headers).status_code == 200

    catalog = client.get("/api/v1/metadata/entities", headers=member_headers)
    assert catalog.status_code == 200
    assert {item["code"] for item in catalog.json()} == {"restricted_document"}
    metadata = client.get("/api/v1/metadata/entities/restricted_document", headers=member_headers)
    assert metadata.status_code == 200

    admin_record = client.post(
        "/api/v1/entities/restricted_document/records",
        json={"data": {"title": "Protected"}},
        headers=admin_headers,
    )
    assert admin_record.status_code == 201
    record_id = UUID(admin_record.json()["id"])

    assert client.get("/api/v1/entities/restricted_document/records", headers=member_headers).status_code == 200
    assert client.post(
        "/api/v1/entities/restricted_document/records",
        json={"data": {"title": "Member cannot create"}},
        headers=member_headers,
    ).status_code == 403
    assert client.patch(
        f"/api/v1/entities/restricted_document/records/{record_id}",
        json={"data": {"title": "Member cannot update"}, "version": 1},
        headers=member_headers,
    ).status_code == 403
    assert client.delete(
        f"/api/v1/entities/restricted_document/records/{record_id}",
        headers=member_headers,
    ).status_code == 403


def test_member_cannot_discover_entity_without_read_permission() -> None:
    admin = _register(f"admin-{uuid4()}@example.com", f"Tenant {uuid4()}")
    member = _register(f"member-{uuid4()}@example.com", f"Tenant {uuid4()}")
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}
    assert client.post(
        "/api/v1/auth/members",
        json={"email": member["email"], "role": "member"},
        headers=admin_headers,
    ).status_code == 201
    member_login = client.post(
        "/api/v1/auth/token",
        json={"email": member["email"], "password": _PASSWORD, "tenant_id": admin["tenant_id"]},
    )
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}

    entity = {
        "code": "hidden_entity",
        "name": "Hidden Entity",
        "fields": [{"code": "title", "type": "text"}],
        "permissions": {"admin": ["create", "read", "update", "delete"], "member": ["create"]},
    }
    assert client.post("/api/v1/metadata/entities", json=entity, headers=admin_headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/hidden_entity/publish", headers=admin_headers).status_code == 200

    catalog = client.get("/api/v1/metadata/entities", headers=member_headers)
    assert catalog.status_code == 200
    assert all(item["code"] != "hidden_entity" for item in catalog.json())
    assert client.get("/api/v1/metadata/entities/hidden_entity", headers=member_headers).status_code == 403
