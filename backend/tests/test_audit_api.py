from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
_PASSWORD = "Correct-Horse-Battery-42"


def _register(email: str, tenant_name: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD, "tenant_name": tenant_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _headers(session: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


def test_admin_can_query_own_tenant_audit_events() -> None:
    session = _register(f"audit-{uuid4()}@example.com", f"Audit {uuid4()}")
    response = client.get("/api/v1/audit/events", headers=_headers(session))
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert all(event["tenant_id"] == session["tenant_id"] for event in payload)


def test_member_cannot_query_audit_events() -> None:
    admin = _register(f"admin-{uuid4()}@example.com", f"Tenant {uuid4()}")
    member_email = f"member-{uuid4()}@example.com"
    _register(member_email, f"Member {uuid4()}")
    added = client.post(
        "/api/v1/auth/members",
        json={"email": member_email, "role": "member"},
        headers=_headers(admin),
    )
    assert added.status_code == 201
    login = client.post(
        "/api/v1/auth/token",
        json={"email": member_email, "password": _PASSWORD, "tenant_id": admin["tenant_id"]},
    )
    assert login.status_code == 200
    response = client.get("/api/v1/audit/events", headers=_headers(login.json()))
    assert response.status_code == 403


def test_audit_query_filters_by_action_and_limit() -> None:
    session = _register(f"filter-{uuid4()}@example.com", f"Filter {uuid4()}")
    headers = _headers(session)
    response = client.get("/api/v1/audit/events?action=metadata.create&limit=2", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) <= 2
    assert all(event["action"] == "metadata.create" for event in response.json())


def test_audit_query_cannot_read_another_tenant() -> None:
    first = _register(f"one-{uuid4()}@example.com", f"One {uuid4()}")
    second = _register(f"two-{uuid4()}@example.com", f"Two {uuid4()}")
    first_events = client.get("/api/v1/audit/events", headers=_headers(first)).json()
    second_events = client.get("/api/v1/audit/events", headers=_headers(second)).json()
    assert all(event["tenant_id"] == first["tenant_id"] for event in first_events)
    assert all(event["tenant_id"] == second["tenant_id"] for event in second_events)
    assert not ({event["id"] for event in first_events} & {event["id"] for event in second_events})
