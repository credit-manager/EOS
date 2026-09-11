from uuid import UUID

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
_PASSWORD = "Correct-Horse-Battery-42"


def _register(email: str) -> tuple[dict, dict[str, str]]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD, "tenant_name": f"Tenant {email}"},
    )
    assert response.status_code == 201
    body = response.json()
    return body, {"Authorization": f"Bearer {body['access_token']}"}


def test_metadata_record_starts_bound_workflow() -> None:
    registered, headers = _register("workflow-record@example.com")

    definition = client.post(
        "/api/v1/workflows/definitions",
        headers=headers,
        json={
            "code": "record_review",
            "name": "Record Review",
            "states": ["draft", "reviewed"],
            "initial_state": "draft",
            "transitions": [
                {
                    "from_state": "draft",
                    "to_state": "reviewed",
                    "action": "review",
                    "roles": ["admin"],
                    "requires_approval": False,
                }
            ],
        },
    )
    assert definition.status_code == 201

    metadata = client.post(
        "/api/v1/metadata/entities",
        headers=headers,
        json={
            "code": "review_item",
            "name": "Review Item",
            "fields": [{"code": "name", "type": "text", "required": True, "label": "Name"}],
            "workflow": {
                "code": "record_review",
                "reference_type": "review_item",
                "auto_start_on_create": True,
            },
        },
    )
    assert metadata.status_code == 201
    published = client.post("/api/v1/metadata/entities/review_item/publish", headers=headers)
    assert published.status_code == 200

    created = client.post(
        "/api/v1/entities/review_item/records",
        headers=headers,
        json={"data": {"name": "Needs review"}},
    )
    assert created.status_code == 201
    body = created.json()
    workflow_instance_id = UUID(body["workflow_instance_id"])
    assert workflow_instance_id

    instances = client.get("/api/v1/workflows/instances", headers=headers)
    assert instances.status_code == 200
    row = next(item for item in instances.json() if item["id"] == str(workflow_instance_id))
    assert row["workflow_code"] == "record_review"
    assert row["reference_type"] == "review_item"
    assert row["reference_id"] == body["id"]
    assert row["current_state"] == "draft"
    assert row["status"] == "active"
    assert registered["tenant_id"] == row["tenant_id"]


def test_workflow_action_updates_bound_record_atomically() -> None:
    _, headers = _register("workflow-action@example.com")

    definition = client.post(
        "/api/v1/workflows/definitions",
        headers=headers,
        json={
            "code": "record_approval",
            "name": "Record Approval",
            "states": ["draft", "approved"],
            "initial_state": "draft",
            "transitions": [
                {
                    "from_state": "draft",
                    "to_state": "approved",
                    "action": "approve",
                    "roles": ["admin"],
                    "requires_approval": False,
                    "actions": [{"type": "set_record_field", "field": "status", "value": "approved"}],
                }
            ],
        },
    )
    assert definition.status_code == 201

    metadata = client.post(
        "/api/v1/metadata/entities",
        headers=headers,
        json={
            "code": "approval_item",
            "name": "Approval Item",
            "fields": [
                {"code": "name", "type": "text", "required": True},
                {"code": "status", "type": "text", "required": True},
            ],
            "workflow": {
                "code": "record_approval",
                "reference_type": "approval_item",
                "auto_start_on_create": True,
            },
        },
    )
    assert metadata.status_code == 201
    assert client.post("/api/v1/metadata/entities/approval_item/publish", headers=headers).status_code == 200

    created = client.post(
        "/api/v1/entities/approval_item/records",
        headers=headers,
        json={"data": {"name": "Purchase request", "status": "draft"}},
    )
    assert created.status_code == 201
    record = created.json()
    instance_id = record["workflow_instance_id"]

    transitioned = client.post(
        f"/api/v1/workflows/instances/{instance_id}/transitions",
        headers=headers,
        json={"action": "approve"},
    )
    assert transitioned.status_code == 200
    assert transitioned.json()["current_state"] == "approved"

    fetched = client.get(f"/api/v1/entities/approval_item/records/{record['id']}", headers=headers)
    assert fetched.status_code == 200
    updated = fetched.json()
    assert updated["data"]["status"] == "approved"
    assert updated["version"] == 2


def test_available_transitions_are_role_and_tenant_scoped() -> None:
    _, headers = _register("workflow-discovery@example.com")
    _, other_headers = _register("workflow-discovery-other@example.com")

    definition = client.post(
        "/api/v1/workflows/definitions",
        headers=headers,
        json={
            "code": "review_flow",
            "name": "Review Flow",
            "states": ["draft", "review", "approved"],
            "initial_state": "draft",
            "transitions": [
                {
                    "from_state": "draft",
                    "to_state": "review",
                    "action": "submit",
                    "roles": ["admin"],
                    "requires_approval": True,
                },
                {
                    "from_state": "review",
                    "to_state": "approved",
                    "action": "approve",
                    "roles": ["admin"],
                    "requires_approval": False,
                },
            ],
        },
    )
    assert definition.status_code == 201

    instance = client.post(
        "/api/v1/workflows/instances",
        headers=headers,
        json={
            "workflow_code": "review_flow",
            "reference_type": "manual",
            "reference_id": str(UUID(int=1)),
        },
    )
    assert instance.status_code == 201
    instance_id = instance.json()["id"]

    available = client.get(
        f"/api/v1/workflows/instances/{instance_id}/available-transitions",
        headers=headers,
    )
    assert available.status_code == 200
    assert available.json() == [
        {
            "action": "submit",
            "from_state": "draft",
            "to_state": "review",
            "requires_approval": True,
        }
    ]

    isolated = client.get(
        f"/api/v1/workflows/instances/{instance_id}/available-transitions",
        headers=other_headers,
    )
    assert isolated.status_code == 404

    transitioned = client.post(
        f"/api/v1/workflows/instances/{instance_id}/transitions",
        headers=headers,
        json={"action": "submit"},
    )
    assert transitioned.status_code == 200
    assert transitioned.json()["status"] == "pending_approval"
