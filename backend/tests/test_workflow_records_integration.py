from uuid import UUID

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
_PASSWORD = "Correct-Horse-Battery-42"


def test_metadata_record_starts_bound_workflow() -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "workflow-record@example.com",
            "password": _PASSWORD,
            "tenant_name": "Workflow Record Tenant",
        },
    )
    assert registered.status_code == 201
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

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
            "fields": [
                {"code": "name", "type": "text", "required": True, "label": "Name"}
            ],
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
