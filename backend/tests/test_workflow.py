from uuid import UUID, uuid4

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


def test_workflow_approval_lifecycle() -> None:
    owner = _register("workflow-owner@example.com")
    member = _register("workflow-member@example.com")
    admin_headers = {"Authorization": f"Bearer {owner['access_token']}"}

    added = client.post(
        "/api/v1/auth/members",
        headers=admin_headers,
        json={"email": "workflow-member@example.com", "role": "member"},
    )
    assert added.status_code == 201
    login = client.post(
        "/api/v1/auth/token",
        json={"email": "workflow-member@example.com", "password": _PASSWORD, "tenant_id": owner["tenant_id"]},
    )
    assert login.status_code == 200
    member_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    definition = client.post(
        "/api/v1/workflows/definitions",
        headers=admin_headers,
        json={
            "code": "purchase_approval",
            "name": "Purchase Approval",
            "states": ["draft", "approved"],
            "initial_state": "draft",
            "transitions": [
                {
                    "from_state": "draft",
                    "to_state": "approved",
                    "action": "submit",
                    "roles": ["member", "admin"],
                    "requires_approval": True,
                }
            ],
        },
    )
    assert definition.status_code == 201

    instance = client.post(
        "/api/v1/workflows/instances",
        headers=member_headers,
        json={
            "workflow_code": "purchase_approval",
            "reference_type": "purchase_order",
            "reference_id": str(uuid4()),
        },
    )
    assert instance.status_code == 201
    instance_id = UUID(instance.json()["id"])
    assert instance.json()["current_state"] == "draft"

    requested = client.post(
        f"/api/v1/workflows/instances/{instance_id}/transitions",
        headers=member_headers,
        json={"action": "submit"},
    )
    assert requested.status_code == 200
    task_id = UUID(requested.json()["approval_task_id"])

    decision = client.post(
        f"/api/v1/workflows/approvals/{task_id}/decision",
        headers=admin_headers,
        json={"approved": True},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    instances = client.get("/api/v1/workflows/instances", headers=admin_headers)
    assert instances.status_code == 200
    row = next(item for item in instances.json() if item["id"] == str(instance_id))
    assert row["current_state"] == "approved"
    assert row["status"] == "completed"


def test_workflow_requester_cannot_approve_own_task() -> None:
    owner = _register("workflow-self@example.com")
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    definition = client.post(
        "/api/v1/workflows/definitions",
        headers=headers,
        json={
            "code": "self_check",
            "name": "Self Check",
            "states": ["draft", "done"],
            "initial_state": "draft",
            "transitions": [
                {
                    "from_state": "draft",
                    "to_state": "done",
                    "action": "approve",
                    "roles": ["admin"],
                    "requires_approval": True,
                }
            ],
        },
    )
    assert definition.status_code == 201
    instance = client.post(
        "/api/v1/workflows/instances",
        headers=headers,
        json={"workflow_code": "self_check", "reference_type": "test", "reference_id": str(uuid4())},
    )
    assert instance.status_code == 201
    requested = client.post(
        f"/api/v1/workflows/instances/{instance.json()['id']}/transitions",
        headers=headers,
        json={"action": "approve"},
    )
    assert requested.status_code == 200
    denied = client.post(
        f"/api/v1/workflows/approvals/{requested.json()['approval_task_id']}/decision",
        headers=headers,
        json={"approved": True},
    )
    assert denied.status_code == 403


def test_workflow_is_tenant_scoped() -> None:
    first = _register("workflow-first@example.com")
    second = _register("workflow-second@example.com")
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    created = client.post(
        "/api/v1/workflows/definitions",
        headers=first_headers,
        json={
            "code": "tenant_only",
            "name": "Tenant Only",
            "states": ["draft", "done"],
            "initial_state": "draft",
            "transitions": [
                {
                    "from_state": "draft",
                    "to_state": "done",
                    "action": "finish",
                    "roles": ["admin"],
                    "requires_approval": False,
                }
            ],
        },
    )
    assert created.status_code == 201
    listed = client.get("/api/v1/workflows/definitions", headers=second_headers)
    assert listed.status_code == 200
    assert listed.json() == []
