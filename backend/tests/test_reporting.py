from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
_PASSWORD = "Correct-Horse-Battery-42"


def _register(email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD, "tenant_name": f"Tenant {email}"},
    )
    assert response.status_code == 201
    return response.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _publish_entity(headers: dict, payload: dict) -> None:
    created = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert created.status_code == 201
    published = client.post(f"/api/v1/metadata/entities/{payload['code']}/publish", headers=headers)
    assert published.status_code == 200


def _record(headers: dict, entity: str, data: dict) -> dict:
    resp = client.post(f"/api/v1/entities/{entity}/records", json={"data": data}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _setup_invoice_entity(headers: dict, *, member_read: bool = True) -> None:
    permissions = {"admin": ["create", "read", "update", "delete"]}
    if member_read:
        permissions["member"] = ["create", "read", "update", "delete"]
    else:
        permissions["member"] = ["create"]
    _publish_entity(
        headers,
        {
            "code": "invoice",
            "name": "Invoice",
            "fields": [
                {"code": "number", "type": "text", "required": True},
                {"code": "amount", "type": "decimal", "required": True},
                {"code": "status", "type": "text"},
            ],
            "permissions": permissions,
        },
    )


def _create_report(headers: dict, payload: dict) -> dict:
    resp = client.post("/api/v1/analytics/reports", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def _seeded_invoices(headers: dict) -> list[dict]:
    rows = [
        {"number": "INV-1", "amount": 100, "status": "approved"},
        {"number": "INV-2", "amount": 200, "status": "approved"},
        {"number": "INV-3", "amount": 300, "status": "pending"},
    ]
    return [_record(headers, "invoice", row) for row in rows]


def test_report_count_and_sum_with_refs() -> None:
    user = _register(f"rep-basic-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_invoice_entity(headers)
    invoices = _seeded_invoices(headers)

    _create_report(
        headers,
        {
            "code": "approved_amount",
            "name": "Approved Invoices Amount",
            "entity_code": "invoice",
            "metric": "sum",
            "field": "amount",
            "conditions": [{"field": "record.status", "op": "eq", "value": "approved"}],
        },
    )
    result = client.post(
        "/api/v1/analytics/reports/approved_amount/run", headers=headers
    ).json()
    assert result["result"]["value"] == "300"
    assert result["result"]["count"] == 2
    approved_ids = {invoice["id"] for invoice in invoices[:2]}
    assert {ref.split(":", 1)[1] for ref in result["result"]["refs"]} == approved_ids


def test_report_group_by_series() -> None:
    user = _register(f"rep-group-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_invoice_entity(headers)
    _seeded_invoices(headers)

    _create_report(
        headers,
        {
            "code": "by_status",
            "name": "Invoices By Status",
            "entity_code": "invoice",
            "metric": "count",
            "group_by": "status",
        },
    )
    result = client.post("/api/v1/analytics/reports/by_status/run", headers=headers).json()
    assert result["result"]["value"] == "3"
    assert {item["key"]: item["value"] for item in result["result"]["series"]} == {
        "approved": "2",
        "pending": "1",
    }


def test_report_avg_and_min() -> None:
    user = _register(f"rep-agg-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_invoice_entity(headers)
    _seeded_invoices(headers)

    _create_report(
        headers,
        {
            "code": "avg_amount",
            "name": "Average Amount",
            "entity_code": "invoice",
            "metric": "avg",
            "field": "amount",
        },
    )
    avg = client.post("/api/v1/analytics/reports/avg_amount/run", headers=headers).json()
    assert avg["result"]["value"] == "200"
    assert avg["result"]["count"] == 3

    _create_report(
        headers,
        {
            "code": "min_amount",
            "name": "Minimum Amount",
            "entity_code": "invoice",
            "metric": "min",
            "field": "amount",
        },
    )
    minimum = client.post("/api/v1/analytics/reports/min_amount/run", headers=headers).json()
    assert minimum["result"]["value"] == "100"


def test_report_value_metric_requires_field() -> None:
    user = _register(f"rep-field-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_invoice_entity(headers)
    resp = client.post(
        "/api/v1/analytics/reports",
        headers=headers,
        json={
            "code": "bad",
            "name": "Bad",
            "entity_code": "invoice",
            "metric": "sum",
        },
    )
    assert resp.status_code == 422


def test_report_refs_drill_to_graph_source() -> None:
    user = _register(f"rep-drill-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_invoice_entity(headers)
    invoice = _record(headers, "invoice", {"number": "INV-9", "amount": 900, "status": "approved"})

    _create_report(
        headers,
        {
            "code": "all_amount",
            "name": "All Amount",
            "entity_code": "invoice",
            "metric": "sum",
            "field": "amount",
        },
    )
    result = client.post("/api/v1/analytics/reports/all_amount/run", headers=headers).json()
    ref = f"invoice:{invoice['id']}"
    assert ref in result["result"]["refs"]

    story = client.get(f"/api/v1/graph/invoice/{invoice['id']}", headers=headers)
    assert story.status_code == 200
    assert story.json()["root"]["ref"] == ref


def test_report_run_publishes_event_and_rule_reaction() -> None:
    user = _register(f"rep-evt-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_invoice_entity(headers)
    _seeded_invoices(headers)

    rule = client.post(
        "/api/v1/rules",
        headers=headers,
        json={
            "name": "alert on analytics",
            "event_type": "report.run.completed",
            "conditions": [{"field": "payload.entity_code", "op": "eq", "value": "invoice"}],
            "priority": 5,
            "enabled": True,
            "actions": [
                {
                    "type": "publish_event",
                    "event_type": "wf.report.alert",
                    "payload": {"value": "{{payload.value}}"},
                }
            ],
        },
    )
    assert rule.status_code == 201

    _create_report(
        headers,
        {
            "code": "total_amount",
            "name": "Total Amount",
            "entity_code": "invoice",
            "metric": "sum",
            "field": "amount",
        },
    )
    client.post("/api/v1/analytics/reports/total_amount/run", headers=headers)

    completed = client.get(
        "/api/v1/events?event_type=report.run.completed", headers=headers
    ).json()
    assert completed["total"] == 1
    assert completed["items"][0]["payload"]["report_code"] == "total_amount"
    assert completed["items"][0]["payload"]["value"] == "600"

    derived = client.get("/api/v1/events?event_type=wf.report.alert", headers=headers).json()
    assert derived["total"] == 1
    assert derived["items"][0]["payload"]["value"] == "600"


def test_report_run_respects_entity_read_permission() -> None:
    user = _register(f"rep-perm-{uuid4()}@example.com")
    member_email = f"rep-perm-member-{uuid4()}@example.com"
    _register(member_email)
    headers = _headers(user["access_token"])
    assert (
        client.post(
            "/api/v1/auth/members", json={"email": member_email, "role": "member"}, headers=headers
        ).status_code
        == 201
    )
    member_login = client.post(
        "/api/v1/auth/token",
        json={"email": member_email, "password": _PASSWORD, "tenant_id": user["tenant_id"]},
    )
    assert member_login.status_code == 200
    member_headers = _headers(member_login.json()["access_token"])

    _setup_invoice_entity(headers, member_read=False)
    _record(headers, "invoice", {"number": "INV-1", "amount": 100, "status": "pending"})

    _create_report(
        headers,
        {
            "code": "hidden_amount",
            "name": "Hidden Amount",
            "entity_code": "invoice",
            "metric": "sum",
            "field": "amount",
        },
    )
    denied = client.post(
        "/api/v1/analytics/reports/hidden_amount/run", headers=member_headers
    )
    assert denied.status_code == 404
    allowed = client.post(
        "/api/v1/analytics/reports/hidden_amount/run", headers=headers
    )
    assert allowed.status_code == 200
    assert allowed.json()["result"]["value"] == "100"


def test_report_history_records_runs() -> None:
    user = _register(f"rep-hist-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_invoice_entity(headers)
    _seeded_invoices(headers)
    _create_report(
        headers,
        {
            "code": "count_all",
            "name": "Count All",
            "entity_code": "invoice",
            "metric": "count",
        },
    )
    client.post("/api/v1/analytics/reports/count_all/run", headers=headers)
    client.post("/api/v1/analytics/reports/count_all/run", headers=headers)

    history = client.get(
        "/api/v1/analytics/reports/count_all/runs", headers=headers
    ).json()
    assert len(history) == 2
    assert all(float(item["result"]["value"]) == 3.0 for item in history)


def test_workspace_feed_lists_pending_approvals_by_role() -> None:
    user = _register(f"rep-feed-{uuid4()}@example.com")
    member_email = f"rep-feed-member-{uuid4()}@example.com"
    _register(member_email)
    headers = _headers(user["access_token"])
    assert (
        client.post(
            "/api/v1/auth/members", json={"email": member_email, "role": "member"}, headers=headers
        ).status_code
        == 201
    )
    member_login = client.post(
        "/api/v1/auth/token",
        json={"email": member_email, "password": _PASSWORD, "tenant_id": user["tenant_id"]},
    )
    member_headers = _headers(member_login.json()["access_token"])

    definition = client.post(
        "/api/v1/workflows/definitions",
        headers=headers,
        json={
            "code": "rep-feed",
            "name": "feed",
            "states": ["draft", "pending", "approved"],
            "initial_state": "draft",
            "transitions": [
                {
                    "from_state": "draft",
                    "to_state": "pending",
                    "action": "submit",
                    "roles": ["admin", "member"],
                    "requires_approval": False,
                },
                {
                    "from_state": "pending",
                    "to_state": "approved",
                    "action": "approve",
                    "roles": ["admin", "member"],
                    "requires_approval": True,
                },
            ],
        },
    )
    assert definition.status_code == 201
    instance = client.post(
        "/api/v1/workflows/instances",
        headers=headers,
        json={
            "workflow_code": "rep-feed",
            "reference_type": "po",
            "reference_id": "22222222-2222-4222-8222-222222222222",
        },
    ).json()
    client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "submit"},
    )
    requested = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "approve"},
    )
    assert requested.status_code == 200
    assert requested.json()["status"] == "pending_approval"

    admin_feed = client.get("/api/v1/analytics/home", headers=headers).json()
    assert admin_feed["approvals_pending"] == []

    member_feed = client.get("/api/v1/analytics/home", headers=member_headers).json()
    assert len(member_feed["approvals_pending"]) == 1
    approval = member_feed["approvals_pending"][0]
    assert approval["workflow_code"] == "rep-feed"
    assert approval["action"] == "approve"
    assert approval["roles"] == ["admin", "member"]
    assert len(member_feed["workflows_needing_action"]) == 1
    assert member_feed["workflows_needing_action"][0]["current_state"] == "pending"