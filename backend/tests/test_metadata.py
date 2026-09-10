from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)
TENANT_A = uuid4()
TENANT_B = uuid4()


def test_metadata_to_generic_crud_and_tenant_isolation() -> None:
    headers = {"X-Tenant-ID": str(TENANT_A)}
    payload = {
        "code": "subcontractor_evaluation",
        "name": "Subcontractor Evaluation",
        "fields": [
            {"code": "quality", "type": "integer", "required": True, "label": "Quality"},
            {"code": "safety", "type": "integer", "required": True, "label": "Safety"},
        ],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/subcontractor_evaluation/publish", headers=headers).status_code == 200

    created = client.post(
        "/api/v1/entities/subcontractor_evaluation/records",
        json={"data": {"quality": 90, "safety": 95}},
        headers=headers,
    )
    assert created.status_code == 201
    record = created.json()
    record_id = UUID(record["id"])
    assert record["version"] == 1

    listing = client.get("/api/v1/entities/subcontractor_evaluation/records", headers=headers)
    assert listing.status_code == 200
    assert any(item["id"] == str(record_id) for item in listing.json())

    conflict = client.patch(
        f"/api/v1/entities/subcontractor_evaluation/records/{record_id}",
        json={"data": {"quality": 91, "safety": 95}, "version": 99},
        headers=headers,
    )
    assert conflict.status_code == 409

    other_tenant = client.get(
        f"/api/v1/entities/subcontractor_evaluation/records/{record_id}",
        headers={"X-Tenant-ID": str(TENANT_B)},
    )
    assert other_tenant.status_code == 404
