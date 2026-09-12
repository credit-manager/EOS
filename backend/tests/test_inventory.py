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
# Warehouses
# ---------------------------------------------------------------------------

def test_create_warehouse() -> None:
    user = _register("inv-warehouse@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/inventory/warehouses",
        headers=headers,
        json={"code": "WH-001", "name": "Main Warehouse", "location": "Riyadh"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == "WH-001"
    assert body["name"] == "Main Warehouse"
    assert body["location"] == "Riyadh"


def test_list_warehouses() -> None:
    user = _register("inv-list-wh@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/inventory/warehouses", headers=headers, json={"code": "WH-L1", "name": "WH One"})
    client.post("/api/v1/inventory/warehouses", headers=headers, json={"code": "WH-L2", "name": "WH Two"})
    resp = client.get("/api/v1/inventory/warehouses", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_update_warehouse() -> None:
    user = _register("inv-upd-wh@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    wh = client.post("/api/v1/inventory/warehouses", headers=headers, json={"code": "WH-U1", "name": "Old"}).json()
    resp = client.patch(f"/api/v1/inventory/warehouses/{wh['id']}", headers=headers, json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


def test_delete_warehouse() -> None:
    user = _register("inv-del-wh@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    wh = client.post("/api/v1/inventory/warehouses", headers=headers, json={"code": "WH-D1", "name": "Delete Me"}).json()
    resp = client.delete(f"/api/v1/inventory/warehouses/{wh['id']}", headers=headers)
    assert resp.status_code == 204


def test_duplicate_warehouse_code_rejected() -> None:
    user = _register("inv-dup-wh@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/inventory/warehouses", headers=headers, json={"code": "WH-DUP", "name": "First"})
    resp = client.post("/api/v1/inventory/warehouses", headers=headers, json={"code": "WH-DUP", "name": "Second"})
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Product Categories
# ---------------------------------------------------------------------------

def test_create_category() -> None:
    user = _register("inv-cat@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/inventory/categories", headers=headers, json={"code": "CAT-001", "name": "Electronics"}
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "CAT-001"


def test_category_tenant_scoped() -> None:
    user_a = _register("inv-ten-cat-a@example.com")
    user_b = _register("inv-ten-cat-b@example.com")
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}
    cat = client.post("/api/v1/inventory/categories", headers=headers_a, json={"code": "CAT-T", "name": "Shared"}).json()
    resp = client.get(f"/api/v1/inventory/categories/{cat['id']}", headers=headers_b)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def test_create_product() -> None:
    user = _register("inv-prod@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/inventory/products",
        headers=headers,
        json={"sku": "SKU-001", "name": "Widget", "unit": "pcs", "unit_cost": "12.50"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["sku"] == "SKU-001"
    assert body["unit"] == "pcs"


def test_duplicate_sku_rejected() -> None:
    user = _register("inv-dup-sku@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/inventory/products", headers=headers, json={"sku": "SKU-DUP", "name": "First", "unit": "pcs"})
    resp = client.post("/api/v1/inventory/products", headers=headers, json={"sku": "SKU-DUP", "name": "Second", "unit": "pcs"})
    assert resp.status_code == 409


def test_update_product() -> None:
    user = _register("inv-upd-prod@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    prod = client.post("/api/v1/inventory/products", headers=headers, json={"sku": "SKU-U", "name": "Old", "unit": "pcs"}).json()
    resp = client.patch(f"/api/v1/inventory/products/{prod['id']}", headers=headers, json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


# ---------------------------------------------------------------------------
# Stock Movements
# ---------------------------------------------------------------------------

def test_inbound_movement() -> None:
    user = _register("inv-movement@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    wh = client.post("/api/v1/inventory/warehouses", headers=headers, json={"code": "WH-MV", "name": "MV WH"}).json()
    prod = client.post("/api/v1/inventory/products", headers=headers, json={"sku": "SKU-MV", "name": "Move", "unit": "pcs"}).json()
    resp = client.post(
        "/api/v1/inventory/movements",
        headers=headers,
        json={
            "warehouse_id": wh["id"],
            "product_id": prod["id"],
            "movement_type": "inbound",
            "quantity": "100",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["movement_type"] == "inbound"


def test_insufficient_stock_rejected() -> None:
    user = _register("inv-stock-err@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    wh = client.post("/api/v1/inventory/warehouses", headers=headers, json={"code": "WH-SE", "name": "SE WH"}).json()
    prod = client.post("/api/v1/inventory/products", headers=headers, json={"sku": "SKU-SE", "name": "Low", "unit": "pcs"}).json()
    client.post(
        "/api/v1/inventory/movements",
        headers=headers,
        json={"warehouse_id": wh["id"], "product_id": prod["id"], "movement_type": "inbound", "quantity": "10"},
    )
    resp = client.post(
        "/api/v1/inventory/movements",
        headers=headers,
        json={"warehouse_id": wh["id"], "product_id": prod["id"], "movement_type": "outbound", "quantity": "20"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Purchase Requisitions
# ---------------------------------------------------------------------------

def test_create_requisition() -> None:
    user = _register("inv-req@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    resp = client.post(
        "/api/v1/inventory/requisitions",
        headers=headers,
        json={"requisition_number": "REQ-001", "priority": "high"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["requisition_number"] == "REQ-001"
    assert body["status"] == "draft"


def test_requisition_status_transition() -> None:
    user = _register("inv-req-status@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    req = client.post(
        "/api/v1/inventory/requisitions",
        headers=headers,
        json={"requisition_number": "REQ-ST", "priority": "medium"},
    ).json()
    resp = client.patch(f"/api/v1/inventory/requisitions/{req['id']}", headers=headers, json={"status": "submitted"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


def test_invalid_requisition_transition_rejected() -> None:
    user = _register("inv-req-bad@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    req = client.post(
        "/api/v1/inventory/requisitions",
        headers=headers,
        json={"requisition_number": "REQ-BAD", "priority": "low"},
    ).json()
    resp = client.patch(f"/api/v1/inventory/requisitions/{req['id']}", headers=headers, json={"status": "received"})
    assert resp.status_code == 409


def test_delete_draft_requisition() -> None:
    user = _register("inv-req-del@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    req = client.post(
        "/api/v1/inventory/requisitions",
        headers=headers,
        json={"requisition_number": "REQ-DEL", "priority": "medium"},
    ).json()
    resp = client.delete(f"/api/v1/inventory/requisitions/{req['id']}", headers=headers)
    assert resp.status_code == 204


def test_duplicate_requisition_number_rejected() -> None:
    user = _register("inv-req-dup@example.com")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    client.post("/api/v1/inventory/requisitions", headers=headers, json={"requisition_number": "REQ-DUP"})
    resp = client.post("/api/v1/inventory/requisitions", headers=headers, json={"requisition_number": "REQ-DUP"})
    assert resp.status_code == 409
