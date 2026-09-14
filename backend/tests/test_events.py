from fastapi.testclient import TestClient

from backend.app.events import service as events_service
from backend.app.main import app

client = TestClient(app)


def _register(email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Correct-Horse-Battery-42",
            "tenant_name": f"Tenant {email}",
        },
    )
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# API: publish + list
# ---------------------------------------------------------------------------

def test_register_emits_event() -> None:
    user = _register("events-register@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.get("/api/v1/events", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["items"][0]["event_type"] == "auth.user.registered"
    assert body["items"][0]["entity_type"] == "user"
    assert body["items"][0]["payload"]["email"] == "events-register@example.com"


def test_publish_and_list_via_api() -> None:
    events_service.clear_subscribers()
    user = _register("events-publish@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "event_type": "demo.invoice.created",
            "entity_type": "invoice",
            "entity_id": "INV-9001",
            "payload": {"amount": "1500.00", "currency": "SAR"},
        },
    )
    assert resp.status_code == 201
    event = resp.json()
    assert event["event_type"] == "demo.invoice.created"
    assert event["entity_id"] == "INV-9001"
    assert event["payload"] == {"amount": "1500.00", "currency": "SAR"}

    resp = client.get(
        "/api/v1/events?event_type=demo.invoice.created", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == event["id"]


def test_entity_filter_and_pagination() -> None:
    user = _register("events-filter@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    for n in range(3):
        client.post(
            "/api/v1/events",
            headers=headers,
            json={
                "event_type": "project.status.changed",
                "entity_type": "project",
                "entity_id": f"PRJ-{n}",
                "payload": {"status": "active"},
            },
        )
    resp = client.get(
        "/api/v1/events?entity_type=project&entity_id=PRJ-1", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["entity_id"] == "PRJ-1"

    resp = client.get("/api/v1/events?event_type=project.status.changed&limit=2", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 2
    assert len(body["items"]) == 2
    assert body["total"] == 3


def test_tenant_isolation() -> None:
    tenant_a = _register("events-iso-a@example.com")
    tenant_b = _register("events-iso-b@example.com")
    headers_a = {"Authorization": f"Bearer {tenant_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {tenant_b['access_token']}"}
    client.post(
        "/api/v1/events",
        headers=headers_a,
        json={"event_type": "demo.sensitive.created", "entity_type": "secret"},
    )
    resp_a = client.get("/api/v1/events?event_type=demo.sensitive.created", headers=headers_a)
    resp_b = client.get("/api/v1/events?event_type=demo.sensitive.created", headers=headers_b)
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json()["total"] == 1
    assert resp_b.json()["total"] == 0


def test_publish_requires_auth() -> None:
    resp = client.get("/api/v1/events")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Subscribers (in-process dispatch)
# ---------------------------------------------------------------------------

def test_subscriber_dispatch() -> None:
    events_service.clear_subscribers()
    calls: list[str] = []

    def handler(event) -> None:
        calls.append(event.event_type)

    user = _register("events-subscribers@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    events_service.subscribe("demo.handler.ran", handler)
    try:
        resp = client.post(
            "/api/v1/events",
            headers=headers,
            json={"event_type": "demo.handler.ran", "entity_type": "job"},
        )
        assert resp.status_code == 201
        assert calls == ["demo.handler.ran"]
    finally:
        events_service.unsubscribe("demo.handler.ran", handler)
        events_service.clear_subscribers()


def test_constructor_project_create_emits_event() -> None:
    user = _register("events-project@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    proj = client.post(
        "/api/v1/construction/projects",
        headers=headers,
        json={"code": "PRJ-EVT", "name": "Event Bus Building"},
    )
    assert proj.status_code == 201
    resp = client.get("/api/v1/events?event_type=construction.project.created", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["entity_type"] == "project"
    assert item["entity_id"] == proj.json()["id"]
    assert item["payload"]["code"] == "PRJ-EVT"