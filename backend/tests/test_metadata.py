from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_metadata_definition_publish_and_read() -> None:
    code = "subcontractor_evaluation"
    payload = {
        "code": code,
        "name": "Subcontractor Evaluation",
        "fields": [
            {"code": "quality", "type": "integer", "required": True},
            {"code": "safety", "type": "integer", "required": True},
        ],
    }
    created = client.post("/api/v1/metadata/entities", json=payload)
    assert created.status_code == 201
    assert created.json()["version"] >= 1

    published = client.post(f"/api/v1/metadata/entities/{code}/publish")
    assert published.status_code == 200
    assert published.json()["published"] is True

    fetched = client.get(f"/api/v1/metadata/entities/{code}")
    assert fetched.status_code == 200
    assert fetched.json()["definition"]["fields"][0]["code"] == "quality"
