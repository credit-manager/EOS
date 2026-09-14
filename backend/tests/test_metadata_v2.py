from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.formula import evaluate_formula
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


def _publish(headers: dict, payload: dict) -> None:
    created = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    published = client.post(f"/api/v1/metadata/entities/{payload['code']}/publish", headers=headers)
    assert published.status_code == 200, published.text


def _record(headers: dict, entity: str, data: dict) -> dict:
    resp = client.post(f"/api/v1/entities/{entity}/records", json={"data": data}, headers=headers)
    return resp


def _setup_quotation(headers: dict) -> None:
    _publish(
        headers,
        {
            "code": "quotation",
            "name": "Quotation",
            "fields": [
                {"code": "number", "type": "text", "required": True},
                {"code": "quantity", "type": "integer", "required": True},
                {"code": "unit_price", "type": "decimal", "required": True},
                {
                    "code": "total",
                    "type": "decimal",
                    "computed": {"formula": "quantity * unit_price"},
                },
                {"code": "tax", "type": "decimal", "default": 14},
            ],
            "groups": [
                {"code": "basic", "name": "Basic", "fields": ["number", "quantity"]},
                {"code": "pricing", "name": "Pricing", "fields": ["unit_price", "total", "tax"]},
            ],
        },
    )


def test_formula_evaluator_is_safe_and_correct() -> None:
    assert evaluate_formula("quantity * unit_price", {"quantity": 3, "unit_price": "2500"}) == 7500.0
    assert evaluate_formula("2 + 3 * 4", {}) == 14.0
    assert evaluate_formula("3.5 * 2", {}) == 7.0
    assert evaluate_formula("1 - (2 - 3)", {}) == 2.0
    assert evaluate_formula("10 / 0", {}) is None
    assert evaluate_formula("missing + 1", {}) is None
    assert evaluate_formula("__import__('os')", {}) is None
    assert evaluate_formula("lambda: 1", {}) is None
    assert evaluate_formula("1 ~ 2", {}) is None


def test_computed_field_is_calculated_on_create() -> None:
    user = _register(f"md2-create-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_quotation(headers)
    resp = _record(headers, "quotation", {"number": "Q-1", "quantity": 3, "unit_price": 2500})
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["total"] == 7500.0


def test_computed_field_recalculates_on_update() -> None:
    user = _register(f"md2-update-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_quotation(headers)
    row = _record(headers, "quotation", {"number": "Q-1", "quantity": 3, "unit_price": 2500}).json()
    updated = client.patch(
        f"/api/v1/entities/quotation/records/{row['id']}",
        json={
            "data": {"number": "Q-1", "quantity": 4, "unit_price": 2500},
            "version": row["version"],
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["total"] == 10000.0


def test_computed_field_cannot_be_written() -> None:
    user = _register(f"md2-readonly-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_quotation(headers)
    resp = _record(
        headers, "quotation", {"number": "Q-1", "quantity": 3, "unit_price": 2500, "total": 999}
    )
    assert resp.status_code == 422
    assert "readonly_fields" in resp.json()["detail"]


def test_computed_field_skips_when_dependency_missing() -> None:
    user = _register(f"md2-partial-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _publish(
        headers,
        {
            "code": "item",
            "name": "Item",
            "fields": [
                {"code": "qty", "type": "decimal", "required": True},
                {"code": "price", "type": "decimal", "nullable": True},
                {"code": "line_total", "type": "decimal", "computed": {"formula": "qty * price"}},
            ],
        },
    )
    resp = _record(headers, "item", {"qty": 2})
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert "line_total" not in data


def test_field_pattern_validation() -> None:
    user = _register(f"md2-pattern-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _publish(
        headers,
        {
            "code": "vendor",
            "name": "Vendor",
            "fields": [
                {
                    "code": "code",
                    "type": "text",
                    "required": True,
                    "validation": {"pattern": r"^V-[0-9]{3}$"},
                }
            ],
        },
    )
    good = _record(headers, "vendor", {"code": "V-123"})
    assert good.status_code == 201, good.text
    bad = _record(headers, "vendor", {"code": "bad"})
    assert bad.status_code == 422


def test_numeric_range_validation() -> None:
    user = _register(f"md2-range-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _publish(
        headers,
        {
            "code": "budget_line",
            "name": "Budget Line",
            "fields": [
                {
                    "code": "amount",
                    "type": "decimal",
                    "required": True,
                    "validation": {"min": 0, "max": 100000},
                }
            ],
        },
    )
    assert _record(headers, "budget_line", {"amount": 500}).status_code == 201
    assert _record(headers, "budget_line", {"amount": -5}).status_code == 422
    assert _record(headers, "budget_line", {"amount": 150000}).status_code == 422


def test_default_value_is_applied() -> None:
    user = _register(f"md2-default-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_quotation(headers)
    resp = _record(headers, "quotation", {"number": "Q-9", "quantity": 1, "unit_price": 100})
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["tax"] == 14


def test_field_groups_are_defined_and_validated() -> None:
    user = _register(f"md2-groups-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _publish(
        headers,
        {
            "code": "asset",
            "name": "Asset",
            "fields": [
                {"code": "name", "type": "text", "required": True},
                {"code": "cost", "type": "decimal", "required": True},
            ],
            "groups": [
                {"code": "identity", "name": "Identity", "fields": ["name"]},
                {"code": "valuation", "name": "Valuation", "fields": ["cost"]},
            ],
        },
    )
    detail = client.get("/api/v1/metadata/entities/asset", headers=headers).json()
    assert detail["definition"]["groups"][0]["fields"] == ["name"]

    invalid = client.post(
        "/api/v1/metadata/entities",
        headers=headers,
        json={
            "code": "broken",
            "name": "Broken",
            "fields": [{"code": "name", "type": "text", "required": True}],
            "groups": [{"code": "g", "name": "G", "fields": ["missing"]}],
        },
    )
    assert invalid.status_code == 422


def test_computed_totals_feed_analytics() -> None:
    user = _register(f"md2-analytics-{uuid4()}@example.com")
    headers = _headers(user["access_token"])
    _setup_quotation(headers)
    _record(headers, "quotation", {"number": "Q-1", "quantity": 3, "unit_price": 2500})
    _record(headers, "quotation", {"number": "Q-2", "quantity": 1, "unit_price": 500})

    report = client.post(
        "/api/v1/analytics/reports",
        headers=headers,
        json={
            "code": "quotation_total",
            "name": "Quotation Total",
            "entity_code": "quotation",
            "metric": "sum",
            "field": "total",
        },
    )
    assert report.status_code == 201, report.text
    run = client.post("/api/v1/analytics/reports/quotation_total/run", headers=headers)
    assert run.status_code == 200, run.text
    assert run.json()["result"]["value"] == "8000.0"