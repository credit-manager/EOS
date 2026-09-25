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


def _headers(session: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


def _create_published_entity(headers: dict[str, str], code: str, member_permissions=None) -> None:
    permissions = {
        "admin": ["create", "read", "update", "delete"],
        "member": member_permissions or ["create", "read", "update", "delete"],
    }
    response = client.post(
        "/api/v1/metadata/entities",
        json={
            "code": code,
            "name": code.replace("_", " ").title(),
            "fields": [
                {"code": "name", "type": "text", "required": True},
                {"code": "description", "type": "text"},
            ],
            "permissions": permissions,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    published = client.post(f"/api/v1/metadata/entities/{code}/publish", headers=headers)
    assert published.status_code == 200, published.text


def test_lookup_searches_published_entity_text_fields() -> None:
    admin = _register(f"admin-{uuid4()}@example.com", f"Tenant {uuid4()}")
    headers = _headers(admin)
    code = f"customer_{uuid4().hex[:8]}"
    _create_published_entity(headers, code)

    first = client.post(
        f"/api/v1/entities/{code}/records",
        json={"data": {"name": "Acme Construction", "description": "Concrete works"}},
        headers=headers,
    )
    second = client.post(
        f"/api/v1/entities/{code}/records",
        json={"data": {"name": "Northwind", "description": "General trading"}},
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(f"/api/v1/entities/{code}/lookup?q=construction", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["label"] == "Acme Construction"
    assert UUID(payload[0]["id"]) == UUID(first.json()["id"])


def test_lookup_is_tenant_scoped() -> None:
    tenant_a = _register(f"a-{uuid4()}@example.com", f"Tenant A {uuid4()}")
    tenant_b = _register(f"b-{uuid4()}@example.com", f"Tenant B {uuid4()}")
    headers_a = _headers(tenant_a)
    headers_b = _headers(tenant_b)
    code = f"shared_{uuid4().hex[:8]}"
    _create_published_entity(headers_a, code)
    _create_published_entity(headers_b, code)

    created = client.post(
        f"/api/v1/entities/{code}/records",
        json={"data": {"name": "Tenant A Secret", "description": "Private"}},
        headers=headers_a,
    )
    assert created.status_code == 201

    response = client.get(f"/api/v1/entities/{code}/lookup?q=Secret", headers=headers_b)
    assert response.status_code == 200
    assert response.json() == []


def test_member_without_read_cannot_use_lookup() -> None:
    admin_email = f"admin-{uuid4()}@example.com"
    member_email = f"member-{uuid4()}@example.com"
    admin = _register(admin_email, f"Tenant {uuid4()}")
    _register(member_email, f"Member Tenant {uuid4()}")
    admin_headers = _headers(admin)
    added = client.post(
        "/api/v1/auth/members",
        json={"email": member_email, "role": "member"},
        headers=admin_headers,
    )
    assert added.status_code == 201
    member_login = client.post(
        "/api/v1/auth/token",
        json={"email": member_email, "password": _PASSWORD, "tenant_id": admin["tenant_id"]},
    )
    assert member_login.status_code == 200
    member_headers = _headers(member_login.json())

    code = f"restricted_{uuid4().hex[:8]}"
    _create_published_entity(admin_headers, code, member_permissions=["create"])
    response = client.get(f"/api/v1/entities/{code}/lookup", headers=member_headers)
    assert response.status_code == 403


def test_lookup_returns_at_most_limit_results() -> None:
    admin = _register(f"admin-{uuid4()}@example.com", f"Tenant {uuid4()}")
    headers = _headers(admin)
    code = f"items_{uuid4().hex[:8]}"
    _create_published_entity(headers, code)

    for index in range(5):
        response = client.post(
            f"/api/v1/entities/{code}/records",
            json={"data": {"name": f"Item {index}", "description": "Lookup"}},
            headers=headers,
        )
        assert response.status_code == 201

    response = client.get(f"/api/v1/entities/{code}/lookup?q=Item&limit=2", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2
