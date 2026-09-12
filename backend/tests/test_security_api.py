"""S2/S3/S4 API security regression tests.

Covers: anonymous denial on protected routes, member/admin separation,
cross-tenant denial (read, relation create, transition), injection-safe
inputs, malformed identifiers, request-id sanitization, and error shape.
"""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

_PASSWORD = "Correct-Horse-Battery-42"


def _register(email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": _PASSWORD,
            "tenant_name": f"Tenant {email}",
        },
    )
    assert response.status_code == 201
    return response.json()


def _headers(token: dict) -> dict:
    return {"Authorization": f"Bearer {token['access_token']}"}


def test_anonymous_requests_are_rejected() -> None:
    assert client.get("/api/construction/projects").status_code == 401
    assert client.get("/api/v1/financial/accounts").status_code == 401
    assert client.get("/api/v1/workflows/definitions").status_code == 401
    assert client.get("/api/v1/audit/events").status_code == 401
    assert client.get("/api/v1/metadata/entities").status_code == 401
    forged = client.get(
        "/api/construction/projects",
        headers={"Authorization": "Bearer not-a-token"},
    )
    assert forged.status_code == 401


def test_member_cannot_use_admin_only_routes() -> None:
    admin = _register("s2-admin@example.com")
    member = _register("s2-member@example.com")
    admin_headers = _headers(admin)
    added = client.post(
        "/api/v1/auth/members",
        json={"email": "s2-member@example.com", "role": "member"},
        headers=admin_headers,
    )
    assert added.status_code == 201
    member_login = client.post(
        "/api/v1/auth/token",
        json={
            "email": "s2-member@example.com",
            "password": _PASSWORD,
            "tenant_id": admin["tenant_id"],
        },
    )
    assert member_login.status_code == 200
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}

    account = client.post(
        "/api/v1/financial/accounts",
        json={"code": "CASH", "name": "Cash", "account_type": "asset"},
        headers=member_headers,
    )
    assert account.status_code == 403
    events = client.get("/api/v1/audit/events", headers=admin_headers)
    assert events.status_code == 200
    forbidden = [
        event
        for event in events.json()
        if event["action"] == "auth.forbidden"
        and event["tenant_id"] == admin["tenant_id"]
    ]
    assert len(forbidden) >= 1
    assert all(event["actor_id"] is not None and event["request_id"] for event in forbidden)
    entity = client.post(
        "/api/v1/metadata/entities",
        json={"code": "widget", "name": "Widget", "fields": []},
        headers=member_headers,
    )
    assert entity.status_code == 403
    assert member["tenant_id"] != admin["tenant_id"]


def test_cross_tenant_construction_access_is_denied() -> None:
    admin_a = _register("s3-owner@example.com")
    admin_b = _register("s3-intruder@example.com")
    headers_a = _headers(admin_a)
    headers_b = _headers(admin_b)

    project = client.post(
        "/api/construction/projects",
        json={"code": "S3-P1", "name": "Secret Project"},
        headers=headers_a,
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    assert (
        client.get(f"/api/construction/projects/{project_id}", headers=headers_b).status_code
        == 404
    )
    listing = client.get("/api/construction/projects", headers=headers_b)
    assert listing.status_code == 200
    assert all(item["id"] != project_id for item in listing.json())

    foreign_contract = client.post(
        "/api/construction/contracts",
        json={
            "project_id": project_id,
            "contract_number": "S3-C1",
            "title": "Hijack",
            "counterparty": "Evil Corp",
        },
        headers=headers_b,
    )
    assert foreign_contract.status_code in (403, 404, 409, 422)

    tamper = client.patch(
        f"/api/construction/projects/{project_id}",
        json={"name": "Hijacked"},
        headers=headers_b,
    )
    assert tamper.status_code in (403, 404)
    assert admin_a["tenant_id"] != admin_b["tenant_id"]


def test_injection_strings_are_treated_as_data() -> None:
    admin = _register("s4-injection@example.com")
    headers = _headers(admin)
    payload = "' OR '1'='1'; --"
    response = client.post(
        "/api/construction/projects",
        json={"code": "S4-P1", "name": payload},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] == payload
    fetched = client.get(
        f"/api/construction/projects/{response.json()['id']}", headers=headers
    )
    assert fetched.status_code == 200
    assert fetched.json()["name"] == payload


def test_malformed_identifiers_are_rejected_without_leakage() -> None:
    admin = _register("s4-malformed@example.com")
    headers = _headers(admin)
    response = client.get("/api/construction/projects/not-a-uuid", headers=headers)
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert "Traceback" not in str(body)
    assert "psycopg" not in str(body).lower()
    assert "sqlalchemy" not in str(body).lower()


def test_request_id_header_is_sanitized() -> None:
    admin = _register("s4-request-id@example.com")
    headers = _headers(admin)
    headers["X-Request-ID"] = "evil\r\nX-Injected: true"
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("X-Injected") is None
    assert "X-Request-ID" in response.headers


def test_oversized_body_is_rejected() -> None:
    big = "x" * (2 * 1024 * 1024)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "s4-big@example.com", "password": _PASSWORD, "tenant_name": big},
    )
    assert response.status_code == 413


def test_error_responses_do_not_leak_internals() -> None:
    admin = _register("s4-errors@example.com")
    headers = _headers(admin)
    missing = client.get(
        "/api/construction/projects/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert missing.status_code == 404
    assert "Traceback" not in missing.text
    assert "File \"" not in missing.text
