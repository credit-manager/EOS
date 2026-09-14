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


def _definition(
    *,
    headers: dict,
    code: str,
    require_approval: bool = False,
    conditions: list | None = None,
) -> dict:
    resp = client.post(
        "/api/v1/workflows/definitions",
        headers=headers,
        json={
            "code": code,
            "name": code,
            "states": ["draft", "pending", "approved", "rejected", "done"],
            "initial_state": "draft",
            "transitions": [
                {
                    "from_state": "draft",
                    "to_state": "pending",
                    "action": "submit",
                    "roles": ["admin", "member"],
                    "requires_approval": False,
                    "conditions": conditions or [],
                },
                {
                    "from_state": "pending",
                    "to_state": "approved",
                    "action": "approve",
                    "roles": ["admin", "member"],
                    "requires_approval": require_approval,
                },
                {
                    "from_state": "approved",
                    "to_state": "done",
                    "action": "finalize",
                    "roles": ["admin"],
                    "requires_approval": False,
                },
            ],
        },
    )
    assert resp.status_code == 201
    return resp


def _start_workflow(headers: dict, code: str, ref: str = "doc") -> dict:
    resp = client.post(
        "/api/v1/workflows/instances",
        headers=headers,
        json={
            "workflow_code": code,
            "reference_type": ref,
            "reference_id": "11111111-1111-4111-8111-111111111111",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_missing_payload_isolation() -> None:
    user = _register("wf2-missing@example.com")
    headers = _headers(user["access_token"])
    _definition(headers=headers, code="wf2-missing")
    instance = _start_workflow(headers, "wf2-missing")
    resp = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "submit"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"


def test_condition_gates_direct_transition() -> None:
    user = _register("wf2-cond@example.com")
    headers = _headers(user["access_token"])
    _definition(
        headers=headers,
        code="wf2-cond",
        conditions=[{"field": "payload.amount", "op": "gt", "value": 1000}],
    )
    instance = _start_workflow(headers, "wf2-cond")

    resp = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "submit"},
    )
    assert resp.status_code == 422

    resp = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "submit", "payload": {"amount": 500}},
    )
    assert resp.status_code == 422

    resp = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "submit", "payload": {"amount": 5000}},
    )
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "pending"


def test_condition_visible_in_available_transitions() -> None:
    user = _register("wf2-avail@example.com")
    headers = _headers(user["access_token"])
    _definition(
        headers=headers,
        code="wf2-avail",
        conditions=[{"field": "payload.amount", "op": "gt", "value": 1000}],
    )
    instance = _start_workflow(headers, "wf2-avail")

    available = client.get(
        f"/api/v1/workflows/instances/{instance['id']}/available-transitions",
        headers=headers,
    ).json()
    submit = next(item for item in available if item["action"] == "submit")
    assert submit["condition_satisfied"] is False


def test_transition_publishes_bus_event() -> None:
    user = _register("wf2-evt@example.com")
    headers = _headers(user["access_token"])
    _definition(headers=headers, code="wf2-evt")
    instance = _start_workflow(headers, "wf2-evt", ref="invoice")

    client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "submit"},
    )
    started = client.get(
        "/api/v1/events?event_type=workflow.instance.started", headers=headers
    ).json()
    assert started["total"] == 1
    assert started["items"][0]["entity_id"] == "11111111-1111-4111-8111-111111111111"

    applied = client.get(
        "/api/v1/events?event_type=workflow.transition.applied", headers=headers
    ).json()
    assert applied["total"] == 1
    event = applied["items"][0]
    assert event["payload"]["action"] == "submit"
    assert event["payload"]["from_state"] == "draft"
    assert event["payload"]["to_state"] == "pending"


def test_terminal_transition_emits_completed() -> None:
    user = _register("wf2-done@example.com")
    headers = _headers(user["access_token"])
    _definition(headers=headers, code="wf2-done")
    instance = _start_workflow(headers, "wf2-done")
    for action in ("submit", "approve", "finalize"):
        resp = client.post(
            f"/api/v1/workflows/instances/{instance['id']}/transitions",
            headers=headers,
            json={"action": action},
        )
        assert resp.status_code == 200
    completed = client.get(
        "/api/v1/events?event_type=workflow.instance.completed", headers=headers
    ).json()
    assert completed["total"] == 1


def test_approval_flow_emits_applied_and_rejected() -> None:
    user = _register("wf2-approve@example.com")
    headers = _headers(user["access_token"])
    _definition(headers=headers, code="wf2-approve", require_approval=True)

    _register("wf2-approve-member@example.com")
    client.post(
        "/api/v1/auth/members",
        headers=headers,
        json={"email": "wf2-approve-member@example.com", "role": "member"},
    )
    member_login = client.post(
        "/api/v1/auth/token",
        json={
            "email": "wf2-approve-member@example.com",
            "password": "Correct-Horse-Battery-42",
            "tenant_id": user["tenant_id"],
        },
    ).json()
    member_headers = _headers(member_login["access_token"])

    instance = _start_workflow(headers, "wf2-approve")
    submit = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "submit"},
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "applied"

    requested = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "approve"},
    )
    assert requested.status_code == 200
    assert requested.json()["status"] == "pending_approval"
    task_id = requested.json()["approval_task_id"]

    rejected = client.post(
        f"/api/v1/workflows/approvals/{task_id}/decision",
        headers=member_headers,
        json={"approved": False},
    )
    assert rejected.status_code == 200
    rejected_events = client.get(
        "/api/v1/events?event_type=workflow.transition.rejected", headers=headers
    ).json()
    assert rejected_events["total"] == 1
    assert rejected_events["items"][0]["payload"]["action"] == "approve"

    requested = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "approve"},
    )
    task_id = requested.json()["approval_task_id"]
    approved = client.post(
        f"/api/v1/workflows/approvals/{task_id}/decision",
        headers=member_headers,
        json={"approved": True},
    )
    assert approved.status_code == 200
    applied = client.get(
        "/api/v1/events?event_type=workflow.transition.applied", headers=headers
    ).json()
    assert applied["total"] == 2
    approve_event = next(item for item in applied["items"] if item["payload"]["action"] == "approve")
    assert approve_event["payload"]["to_state"] == "approved"


def test_condition_uses_actor_context() -> None:
    user = _register("wf2-actor@example.com")
    headers = _headers(user["access_token"])
    resp = client.post(
        "/api/v1/workflows/definitions",
        headers=headers,
        json={
            "code": "wf2-actor",
            "name": "wf2-actor",
            "states": ["draft", "pending"],
            "initial_state": "draft",
            "transitions": [
                {
                    "from_state": "draft",
                    "to_state": "pending",
                    "action": "submit",
                    "roles": ["admin"],
                    "requires_approval": False,
                    "conditions": [{"field": "actor.role", "op": "eq", "value": "admin"}],
                }
            ],
        },
    )
    assert resp.status_code == 201
    instance = _start_workflow(headers, "wf2-actor")
    resp = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "submit"},
    )
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "pending"


def test_rule_fires_from_workflow_transition() -> None:
    user = _register("wf2-loop@example.com")
    headers = _headers(user["access_token"])
    _definition(headers=headers, code="wf2-loop")

    rule = client.post(
        "/api/v1/rules",
        headers=headers,
        json={
            "name": "notify transition to pending",
            "event_type": "workflow.transition.applied",
            "conditions": [{"field": "payload.to_state", "op": "eq", "value": "pending"}],
            "priority": 10,
            "enabled": True,
            "actions": [
                {
                    "type": "publish_event",
                    "event_type": "wf.test.derived",
                    "payload": {
                        "message": "submit observed",
                        "state": "{{payload.to_state}}",
                    },
                }
            ],
        },
    )
    assert rule.status_code == 201

    instance = _start_workflow(headers, "wf2-loop")
    resp = client.post(
        f"/api/v1/workflows/instances/{instance['id']}/transitions",
        headers=headers,
        json={"action": "submit"},
    )
    assert resp.status_code == 200

    derived = client.get(
        "/api/v1/events?event_type=wf.test.derived", headers=headers
    ).json()
    assert derived["total"] == 1
    assert derived["items"][0]["payload"]["state"] == "pending"
