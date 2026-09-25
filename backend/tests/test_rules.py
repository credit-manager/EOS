from fastapi.testclient import TestClient

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


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_rule(
    headers: dict,
    *,
    event_type: str = "demo.invoice.created",
    conditions: list | None = None,
    actions: list | None = None,
    name: str = "High Value Invoice",
    enabled: bool = True,
) -> dict:
    resp = client.post(
        "/api/v1/rules",
        headers=headers,
        json={
            "name": name,
            "event_type": event_type,
            "conditions": conditions or [{"field": "payload.amount", "op": "gt", "value": 1000}],
            "actions": actions
            or [
                {
                    "type": "notify",
                    "role": "admin",
                    "title": "Invoice {{payload.amount}} needs attention",
                    "message": "High value invoice {{payload.amount}} for {{event.entity_id}}",
                },
                {
                    "type": "publish_event",
                    "event_type": "demo.invoice.high_value",
                    "entity_type": "invoice",
                    "payload": {"amount": "{{payload.amount}}"},
                },
            ],
            "enabled": enabled,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _publish_invoice(headers: dict, *, amount: str, entity_id: str = "INV-1") -> dict:
    resp = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "event_type": "demo.invoice.created",
            "entity_type": "invoice",
            "entity_id": entity_id,
            "payload": {"amount": amount},
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _admin_only_rule() -> tuple[dict, dict, str]:
    admin = _register("rules-admin@example.com")
    _register("rules-member@example.com")
    admin_headers = _headers(admin["access_token"])
    resp = client.post(
        "/api/v1/auth/members",
        headers=admin_headers,
        json={"email": "rules-member@example.com", "role": "member"},
    )
    assert resp.status_code == 201
    member_login = client.post(
        "/api/v1/auth/token",
        json={
            "email": "rules-member@example.com",
            "password": "Correct-Horse-Battery-42",
            "tenant_id": admin["tenant_id"],
        },
    ).json()
    return admin_headers, _headers(member_login["access_token"]), admin["tenant_id"]


def test_rules_admin_only() -> None:
    _, member_headers, _ = _admin_only_rule()
    resp = client.post("/api/v1/rules", headers=member_headers, json={"name": "n", "event_type": "demo.x", "actions": []})
    assert resp.status_code == 403
    resp = client.patch("/api/v1/rules/00000000-0000-0000-0000-000000000000", headers=member_headers, json={"enabled": False})
    assert resp.status_code == 403


def test_rule_crud_cycle() -> None:
    admin = _register("rules-crud@example.com")
    headers = _headers(admin["access_token"])
    created = _create_rule(headers)
    rule_id = created["id"]
    assert created["event_type"] == "demo.invoice.created"
    assert created["conditions"][0] == {"field": "payload.amount", "op": "gt", "value": 1000}
    assert created["actions"][0]["type"] == "notify"

    listed = client.get("/api/v1/rules", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(f"/api/v1/rules/{rule_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == rule_id

    patched = client.patch(f"/api/v1/rules/{rule_id}", headers=headers, json={"name": "Renamed", "enabled": False})
    assert patched.status_code == 200
    assert patched.json()["name"] == "Renamed"
    assert patched.json()["enabled"] is False

    deleted = client.delete(f"/api/v1/rules/{rule_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/rules/{rule_id}", headers=headers).status_code == 404


def test_rule_fires_high_value() -> None:
    admin = _register("rules-fire@example.com")
    headers = _headers(admin["access_token"])
    rule = _create_rule(headers)
    assert rule["enabled"] is True

    _publish_invoice(headers, amount="5000.00", entity_id="INV-9000")

    events = client.get("/api/v1/events?event_type=demo.invoice.high_value", headers=headers).json()
    assert events["total"] == 1
    assert events["items"][0]["payload"]["amount"] == "5000.00"

    notifications = client.get("/api/v1/notifications", headers=headers).json()
    assert notifications["total"] >= 1
    assert "5000.00" in notifications["items"][0]["title"]

    executions = client.get("/api/v1/rules/executions", headers=headers).json()
    assert executions["total"] >= 1
    assert executions["items"][0]["matched"] is True


def test_rule_below_threshold() -> None:
    admin = _register("rules-low@example.com")
    headers = _headers(admin["access_token"])
    rule = _create_rule(headers)
    _publish_invoice(headers, amount="500.00")

    assert client.get("/api/v1/events?event_type=demo.invoice.high_value", headers=headers).json()["total"] == 0
    assert client.get("/api/v1/notifications", headers=headers).json()["total"] == 0

    executions = client.get(f"/api/v1/rules/executions?rule_id={rule['id']}", headers=headers).json()
    assert executions["total"] == 1
    assert executions["items"][0]["matched"] is False


def test_rule_disable_stops_firing() -> None:
    admin = _register("rules-off@example.com")
    headers = _headers(admin["access_token"])
    rule = _create_rule(headers)
    _publish_invoice(headers, amount="5000.00")
    assert client.get("/api/v1/rules/executions?rule_id=" + rule["id"], headers=headers).json()["total"] == 1

    client.patch(f"/api/v1/rules/{rule['id']}", headers=headers, json={"enabled": False})
    _publish_invoice(headers, amount="9000.00")
    assert client.get("/api/v1/rules/executions?rule_id=" + rule["id"], headers=headers).json()["total"] == 1


def test_rule_tenant_isolation() -> None:
    admin_a = _register("rules-iso-a@example.com")
    admin_b = _register("rules-iso-b@example.com")
    headers_a = _headers(admin_a["access_token"])
    headers_b = _headers(admin_b["access_token"])
    _create_rule(headers_a)
    _publish_invoice(headers_a, amount="5000.00")
    _publish_invoice(headers_b, amount="5000.00")
    assert client.get("/api/v1/rules/executions", headers=headers_a).json()["total"] == 1
    assert client.get("/api/v1/rules/executions", headers=headers_b).json()["total"] == 0


def test_rule_condition_in_operator() -> None:
    admin = _register("rules-in@example.com")
    headers = _headers(admin["access_token"])
    rule = _create_rule(
        headers,
        conditions=[{"field": "payload.sector", "op": "in", "value": ["construction", "energy"]}],
    )
    resp = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "event_type": "demo.invoice.created",
            "entity_type": "invoice",
            "payload": {"sector": "energy"},
        },
    )
    assert resp.status_code == 201
    executions = client.get(f"/api/v1/rules/executions?rule_id={rule['id']}", headers=headers).json()
    assert executions["total"] == 1
    assert executions["items"][0]["matched"] is True


def test_rule_validation_errors() -> None:
    admin = _register("rules-validate@example.com")
    headers = _headers(admin["access_token"])
    bad_event = client.post(
        "/api/v1/rules",
        headers=headers,
        json={"name": "Bad", "event_type": "NOT_VALID", "actions": []},
    )
    assert bad_event.status_code == 422
    bad_op = client.post(
        "/api/v1/rules",
        headers=headers,
        json={
            "name": "BadOp",
            "event_type": "demo.x",
            "conditions": [{"field": "payload.amount", "op": "greater_than", "value": 10}],
            "actions": [],
        },
    )
    assert bad_op.status_code == 422
    bad_action = client.post(
        "/api/v1/rules",
        headers=headers,
        json={"name": "BadAction", "event_type": "demo.x", "actions": [{"type": "explode"}]},
    )
    assert bad_action.status_code == 422


def test_rule_engine_cascades_with_cap() -> None:
    admin = _register("rules-cascade@example.com")
    headers = _headers(admin["access_token"])
    client.post(
        "/api/v1/rules",
        headers=headers,
        json={
            "name": "Loop Guard",
            "event_type": "demo.loop",
            "conditions": [],
            "actions": [
                {"type": "publish_event", "event_type": "demo.loop", "payload": {}},
            ],
        },
    )
    resp = client.post(
        "/api/v1/events",
        headers=headers,
        json={"event_type": "demo.loop", "entity_type": "x"},
    )
    assert resp.status_code == 201
    executions = client.get("/api/v1/rules/executions", headers=headers).json()
    assert executions["total"] <= 5