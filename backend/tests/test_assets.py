from datetime import datetime

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


# ---------------------------------------------------------------------------
# Asset Categories
# ---------------------------------------------------------------------------

def test_create_asset_category() -> None:
    user = _register("assets-cat-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/assets/categories",
        headers=headers,
        json={"code": "CAT-001", "name": "Heavy Machinery", "description": "Construction equipment"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "CAT-001"
    assert body["name"] == "Heavy Machinery"


def test_list_asset_categories() -> None:
    user = _register("assets-cat-list@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/assets/categories", headers=headers, json={"code": "C-L1", "name": "Cat1"})
    client.post("/api/v1/assets/categories", headers=headers, json={"code": "C-L2", "name": "Cat2"})
    resp = client.get("/api/v1/assets/categories", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_duplicate_category_code_rejected() -> None:
    user = _register("assets-cat-dup@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/assets/categories", headers=headers, json={"code": "C-DUP", "name": "First"})
    resp = client.post("/api/v1/assets/categories", headers=headers, json={"code": "C-DUP", "name": "Second"})
    assert resp.status_code == 409


def test_delete_asset_category() -> None:
    user = _register("assets-cat-del@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    cat = client.post("/api/v1/assets/categories", headers=headers, json={"code": "C-DEL", "name": "Del"}).json()
    resp = client.delete(f"/api/v1/assets/categories/{cat['id']}", headers=headers)
    assert resp.status_code == 204


def test_category_tenant_scoped() -> None:
    user_a = _register("assets-ten-cat-a@example.com")
    user_b = _register("assets-ten-cat-b@example.com")
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}
    cat = client.post("/api/v1/assets/categories", headers=headers_a, json={"code": "C-SC", "name": "Scoped"}).json()
    resp = client.get(f"/api/v1/assets/categories/{cat['id']}", headers=headers_b)
    assert resp.status_code in {403, 404}


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

def test_create_asset() -> None:
    user = _register("assets-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/assets",
        headers=headers,
        json={
            "asset_code": "AST-001",
            "name": "Excavator CAT 320",
            "purchase_cost": "150000.00",
            "current_value": "120000.00",
            "location": "Site A",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["asset_code"] == "AST-001"
    assert body["name"] == "Excavator CAT 320"
    assert body["status"] == "active"


def test_list_assets() -> None:
    user = _register("assets-list@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/assets", headers=headers, json={"asset_code": "A-L1", "name": "Asset1"})
    client.post("/api/v1/assets", headers=headers, json={"asset_code": "A-L2", "name": "Asset2"})
    resp = client.get("/api/v1/assets", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_duplicate_asset_code_rejected() -> None:
    user = _register("assets-dup@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/assets", headers=headers, json={"asset_code": "A-DUP", "name": "First"})
    resp = client.post("/api/v1/assets", headers=headers, json={"asset_code": "A-DUP", "name": "Second"})
    assert resp.status_code == 409


def test_asset_status_transition() -> None:
    user = _register("assets-status@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    asset = client.post(
        "/api/v1/assets", headers=headers, json={"asset_code": "A-ST", "name": "Status Test"}
    ).json()
    resp = client.patch(f"/api/v1/assets/{asset['id']}", headers=headers, json={"status": "maintenance"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "maintenance"
    resp2 = client.patch(f"/api/v1/assets/{asset['id']}", headers=headers, json={"status": "active"})
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "active"


def test_invalid_status_transition_rejected() -> None:
    user = _register("assets-invalid-trans@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    asset = client.post(
        "/api/v1/assets", headers=headers, json={"asset_code": "A-INV", "name": "Invalid"}
    ).json()
    client.patch(f"/api/v1/assets/{asset['id']}", headers=headers, json={"status": "disposed"})
    resp = client.patch(f"/api/v1/assets/{asset['id']}", headers=headers, json={"status": "active"})
    assert resp.status_code == 409


def test_invalid_asset_status_rejected() -> None:
    user = _register("assets-invalid-stat@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/assets", headers=headers, json={"asset_code": "A-INV2", "name": "Bad", "status": "garbage"}
    )
    assert resp.status_code == 422


def test_asset_tenant_scoped() -> None:
    user_a = _register("assets-ten-a@example.com")
    user_b = _register("assets-ten-b@example.com")
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}
    asset = client.post("/api/v1/assets", headers=headers_a, json={"asset_code": "A-SC", "name": "Scoped"}).json()
    resp = client.get(f"/api/v1/assets/{asset['id']}", headers=headers_b)
    assert resp.status_code in {403, 404}


# ---------------------------------------------------------------------------
# Maintenance Schedules & Logs
# ---------------------------------------------------------------------------

def test_create_maintenance_schedule() -> None:
    user = _register("assets-sched-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    asset = client.post(
        "/api/v1/assets", headers=headers, json={"asset_code": "A-MS1", "name": "Schedule Test"}
    ).json()
    resp = client.post(
        "/api/v1/assets/schedules",
        headers=headers,
        json={
            "asset_id": asset["id"],
            "frequency": "monthly",
            "next_due_date": "2026-10-01",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["frequency"] == "monthly"


def test_create_maintenance_log() -> None:
    user = _register("assets-log-create@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    asset = client.post(
        "/api/v1/assets", headers=headers, json={"asset_code": "A-ML1", "name": "Log Test"}
    ).json()
    resp = client.post(
        "/api/v1/assets/logs",
        headers=headers,
        json={
            "asset_id": asset["id"],
            "maintenance_type": "preventive",
            "description": "Oil change",
            "cost": "250.00",
            "performed_at": datetime.now().isoformat(),
        },
    )
    assert resp.status_code == 201
    assert resp.json()["maintenance_type"] == "preventive"
    assert resp.json()["cost"] == "250.00"


def test_list_maintenance_logs() -> None:
    user = _register("assets-log-list@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    asset = client.post(
        "/api/v1/assets", headers=headers, json={"asset_code": "A-ML2", "name": "Log List"}
    ).json()
    client.post(
        "/api/v1/assets/logs",
        headers=headers,
        json={
            "asset_id": asset["id"],
            "maintenance_type": "corrective",
            "performed_at": datetime.now().isoformat(),
        },
    )
    resp = client.get("/api/v1/assets/logs", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) >= 1
