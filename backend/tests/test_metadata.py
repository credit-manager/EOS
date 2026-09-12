from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.auth.models import TenantMembership, User
from backend.app.db import SessionLocal
from backend.app.main import app

client = TestClient(app)


def _register() -> tuple[dict[str, str], UUID]:
    email = f"user-{uuid4()}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Correct-Horse-Battery-42",
            "tenant_name": f"Tenant {uuid4()}",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, UUID(payload["tenant_id"])


def test_metadata_to_generic_crud_and_tenant_isolation() -> None:
    headers, tenant_id = _register()
    other_headers, _ = _register()
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
    assert record["tenant_id"] == str(tenant_id)
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
        headers=other_headers,
    )
    assert other_tenant.status_code == 404


def test_metadata_catalog_lists_only_published_latest_versions() -> None:
    headers, _ = _register()
    first = {"code": "catalog_a", "name": "Catalog A", "fields": [{"code": "name", "type": "text"}]}
    second = {"code": "catalog_b", "name": "Catalog B", "fields": [{"code": "amount", "type": "decimal"}]}
    assert client.post("/api/v1/metadata/entities", json=first, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/catalog_a/publish", headers=headers).status_code == 200
    assert client.post("/api/v1/metadata/entities", json=second, headers=headers).status_code == 201

    hidden = client.get("/api/v1/metadata/entities", headers=headers)
    assert hidden.status_code == 200
    assert {item["code"] for item in hidden.json()} == {"catalog_a"}

    revised = {
        **first,
        "name": "Catalog A Revised",
        "fields": [
            {"code": "name", "type": "text"},
            {"code": "active", "type": "boolean"},
        ],
    }
    created = client.post("/api/v1/metadata/entities", json=revised, headers=headers)
    assert created.status_code == 201
    assert created.json()["version"] == 2
    assert client.post("/api/v1/metadata/entities/catalog_a/publish", headers=headers).status_code == 200

    catalog = client.get("/api/v1/metadata/entities", headers=headers)
    assert catalog.status_code == 200
    items = {item["code"]: item for item in catalog.json()}
    assert items["catalog_a"]["name"] == "Catalog A Revised"
    assert items["catalog_a"]["version"] == 2
    assert items["catalog_a"]["field_count"] == 2


def test_metadata_catalog_is_tenant_scoped() -> None:
    headers, _ = _register()
    other_headers, _ = _register()
    payload = {"code": "private_entity", "name": "Private Entity", "fields": [{"code": "name", "type": "text"}]}
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/private_entity/publish", headers=headers).status_code == 200

    other_catalog = client.get("/api/v1/metadata/entities", headers=other_headers)
    assert other_catalog.status_code == 200
    assert all(item["code"] != "private_entity" for item in other_catalog.json())


def test_generic_record_type_validation() -> None:
    headers, _ = _register()
    payload = {
        "code": "typed_example",
        "name": "Typed Example",
        "fields": [
            {"code": "name", "type": "text"},
            {"code": "quantity", "type": "integer"},
            {"code": "amount", "type": "decimal"},
            {"code": "active", "type": "boolean"},
            {"code": "due_date", "type": "date"},
            {"code": "external_id", "type": "uuid"},
            {"code": "notes", "type": "text", "nullable": True},
        ],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/typed_example/publish", headers=headers).status_code == 200

    valid = {
        "data": {
            "name": "Demo",
            "quantity": 3,
            "amount": "125.50",
            "active": True,
            "due_date": "2026-09-11",
            "external_id": str(uuid4()),
            "notes": None,
        }
    }
    assert client.post("/api/v1/entities/typed_example/records", json=valid, headers=headers).status_code == 201

    filtered = client.get(
        "/api/v1/entities/typed_example/records",
        params={"filter_field": "quantity", "filter_value": "3", "limit": 1},
        headers=headers,
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    invalid = {**valid, "data": {**valid["data"], "quantity": True}}
    response = client.post("/api/v1/entities/typed_example/records", json=invalid, headers=headers)
    assert response.status_code == 422
    assert "quantity" in str(response.json()["detail"])


def test_metadata_relations_are_tenant_scoped() -> None:
    headers, tenant_id = _register()
    other_headers, _ = _register()

    target = {"code": "worker", "name": "Worker", "fields": [{"code": "name", "type": "text", "required": True}]}
    assert client.post("/api/v1/metadata/entities", json=target, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/worker/publish", headers=headers).status_code == 200

    target_record = client.post(
        "/api/v1/entities/worker/records", json={"data": {"name": "Alice"}}, headers=headers
    )
    assert target_record.status_code == 201
    target_id = target_record.json()["id"]

    assignment = {
        "code": "assignment",
        "name": "Assignment",
        "fields": [{"code": "worker_id", "type": "relation", "target_entity": "worker", "required": True}],
    }
    assert client.post("/api/v1/metadata/entities", json=assignment, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/assignment/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/assignment/records",
        json={"data": {"worker_id": target_id}},
        headers=headers,
    )
    assert valid.status_code == 201
    assert valid.json()["tenant_id"] == str(tenant_id)

    wrong_tenant = client.post(
        "/api/v1/entities/assignment/records",
        json={"data": {"worker_id": target_id}},
        headers=other_headers,
    )
    assert wrong_tenant.status_code == 404


def test_duplicate_metadata_field_codes_are_rejected() -> None:
    headers, _ = _register()
    payload = {
        "code": "duplicate_fields",
        "name": "Duplicate Fields",
        "fields": [
            {"code": "name", "type": "text"},
            {"code": "name", "type": "text"},
        ],
    }
    response = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert response.status_code == 422


def test_metadata_administration_requires_admin_role() -> None:
    headers, _ = _register()
    me = client.get("/api/v1/auth/me", headers=headers).json()
    with SessionLocal() as db:
        user = db.get(User, UUID(me["user_id"]))
        assert user is not None
        membership = db.scalar(select(TenantMembership).where(TenantMembership.user_id == user.id))
        assert membership is not None
        membership.role = "member"
        db.commit()

    payload = {"code": "member_blocked", "name": "Blocked", "fields": [{"code": "name", "type": "text"}]}
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# New Field Types: enum, email, url, json, array
# ---------------------------------------------------------------------------


def test_enum_field_type() -> None:
    headers, _ = _register()
    payload = {
        "code": "priority_enum",
        "name": "Priority Enum",
        "fields": [
            {
                "code": "priority",
                "type": "enum",
                "required": True,
                "options": [
                    {"value": "low", "label": "Low"},
                    {"value": "medium", "label": "Medium"},
                    {"value": "high", "label": "High"},
                ],
            }
        ],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/priority_enum/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/priority_enum/records",
        json={"data": {"priority": "high"}},
        headers=headers,
    )
    assert valid.status_code == 201

    invalid = client.post(
        "/api/v1/entities/priority_enum/records",
        json={"data": {"priority": "urgent"}},
        headers=headers,
    )
    assert invalid.status_code == 422


def test_enum_requires_options() -> None:
    headers, _ = _register()
    payload = {
        "code": "bad_enum",
        "name": "Bad Enum",
        "fields": [{"code": "status", "type": "enum"}],
    }
    response = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert response.status_code == 422


def test_email_field_type() -> None:
    headers, _ = _register()
    payload = {
        "code": "contact_email",
        "name": "Contact Email",
        "fields": [{"code": "email", "type": "email", "required": True}],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/contact_email/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/contact_email/records",
        json={"data": {"email": "test@example.com"}},
        headers=headers,
    )
    assert valid.status_code == 201

    invalid = client.post(
        "/api/v1/entities/contact_email/records",
        json={"data": {"email": "not-an-email"}},
        headers=headers,
    )
    assert invalid.status_code == 422


def test_url_field_type() -> None:
    headers, _ = _register()
    payload = {
        "code": "website_url",
        "name": "Website URL",
        "fields": [{"code": "url", "type": "url", "required": True}],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/website_url/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/website_url/records",
        json={"data": {"url": "https://example.com"}},
        headers=headers,
    )
    assert valid.status_code == 201

    invalid = client.post(
        "/api/v1/entities/website_url/records",
        json={"data": {"url": "ftp://files.example.com"}},
        headers=headers,
    )
    assert invalid.status_code == 422


def test_json_field_type() -> None:
    headers, _ = _register()
    payload = {
        "code": "config_json",
        "name": "Config JSON",
        "fields": [{"code": "config", "type": "json", "required": True}],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/config_json/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/config_json/records",
        json={"data": {"config": {"theme": "dark", "lang": "ar"}}},
        headers=headers,
    )
    assert valid.status_code == 201

    invalid = client.post(
        "/api/v1/entities/config_json/records",
        json={"data": {"config": "not-json"}},
        headers=headers,
    )
    assert invalid.status_code == 422


def test_array_field_type() -> None:
    headers, _ = _register()
    payload = {
        "code": "tags_array",
        "name": "Tags Array",
        "fields": [{"code": "tags", "type": "array", "item_type": "text", "required": True}],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/tags_array/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/tags_array/records",
        json={"data": {"tags": ["construction", "urgent", "ksa"]}},
        headers=headers,
    )
    assert valid.status_code == 201

    invalid = client.post(
        "/api/v1/entities/tags_array/records",
        json={"data": {"tags": "not-a-list"}},
        headers=headers,
    )
    assert invalid.status_code == 422


# ---------------------------------------------------------------------------
# Rendering Hints: widget, placeholder, help_text
# ---------------------------------------------------------------------------


def test_rendering_hints_are_preserved_in_definition() -> None:
    headers, _ = _register()
    payload = {
        "code": "render_hints",
        "name": "Render Hints",
        "fields": [
            {
                "code": "description",
                "type": "text",
                "widget": "textarea",
                "placeholder": "Enter description...",
                "help_text": "Detailed description of the item",
                "min_length": 10,
                "max_length": 500,
            }
        ],
    }
    created = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert created.status_code == 201
    definition = created.json()["definition"]
    field = definition["fields"][0]
    assert field["widget"] == "textarea"
    assert field["placeholder"] == "Enter description..."
    assert field["help_text"] == "Detailed description of the item"
    assert field["min_length"] == 10
    assert field["max_length"] == 500


def test_widget_type_validation() -> None:
    headers, _ = _register()
    payload = {
        "code": "bad_widget",
        "name": "Bad Widget",
        "fields": [{"code": "date", "type": "date", "widget": "text"}],
    }
    response = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Default Values
# ---------------------------------------------------------------------------


def test_default_values_populated_on_create() -> None:
    headers, _ = _register()
    payload = {
        "code": "defaults_test",
        "name": "Defaults Test",
        "fields": [
            {"code": "status", "type": "enum", "default": "draft", "options": [
                {"value": "draft", "label": "Draft"},
                {"value": "active", "label": "Active"},
            ]},
            {"code": "count", "type": "integer", "default": 0},
        ],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/defaults_test/publish", headers=headers).status_code == 200

    created = client.post(
        "/api/v1/entities/defaults_test/records",
        json={"data": {}},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["data"]["status"] == "draft"
    assert created.json()["data"]["count"] == 0

    explicit = client.post(
        "/api/v1/entities/defaults_test/records",
        json={"data": {"status": "active", "count": 5}},
        headers=headers,
    )
    assert explicit.status_code == 201
    assert explicit.json()["data"]["status"] == "active"
    assert explicit.json()["data"]["count"] == 5


# ---------------------------------------------------------------------------
# Field Groups
# ---------------------------------------------------------------------------


def test_field_groups_are_preserved() -> None:
    headers, _ = _register()
    payload = {
        "code": "grouped_fields",
        "name": "Grouped Fields",
        "groups": ["Personal Info", "Contact"],
        "fields": [
            {"code": "name", "type": "text", "group": "Personal Info"},
            {"code": "age", "type": "integer", "group": "Personal Info"},
            {"code": "email", "type": "email", "group": "Contact"},
        ],
    }
    created = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert created.status_code == 201
    definition = created.json()["definition"]
    assert definition["groups"] == ["Personal Info", "Contact"]
    assert definition["fields"][0]["group"] == "Personal Info"


# ---------------------------------------------------------------------------
# Validation Constraints
# ---------------------------------------------------------------------------


def test_text_min_max_length_validation() -> None:
    headers, _ = _register()
    payload = {
        "code": "length_test",
        "name": "Length Test",
        "fields": [{"code": "code", "type": "text", "min_length": 3, "max_length": 10}],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/length_test/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/length_test/records",
        json={"data": {"code": "ABC"}},
        headers=headers,
    )
    assert valid.status_code == 201

    too_short = client.post(
        "/api/v1/entities/length_test/records",
        json={"data": {"code": "AB"}},
        headers=headers,
    )
    assert too_short.status_code == 422

    too_long = client.post(
        "/api/v1/entities/length_test/records",
        json={"data": {"code": "ABCDEFGHIJK"}},
        headers=headers,
    )
    assert too_long.status_code == 422


def test_integer_min_max_value_validation() -> None:
    headers, _ = _register()
    payload = {
        "code": "range_test",
        "name": "Range Test",
        "fields": [{"code": "score", "type": "integer", "min_value": 0, "max_value": 100}],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/range_test/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/range_test/records",
        json={"data": {"score": 50}},
        headers=headers,
    )
    assert valid.status_code == 201

    too_low = client.post(
        "/api/v1/entities/range_test/records",
        json={"data": {"score": -1}},
        headers=headers,
    )
    assert too_low.status_code == 422

    too_high = client.post(
        "/api/v1/entities/range_test/records",
        json={"data": {"score": 101}},
        headers=headers,
    )
    assert too_high.status_code == 422


def test_text_pattern_validation() -> None:
    headers, _ = _register()
    payload = {
        "code": "pattern_test",
        "name": "Pattern Test",
        "fields": [{"code": "phone", "type": "text", "pattern": r"^\+?\d{10,15}$"}],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/pattern_test/publish", headers=headers).status_code == 200

    valid = client.post(
        "/api/v1/entities/pattern_test/records",
        json={"data": {"phone": "+966501234567"}},
        headers=headers,
    )
    assert valid.status_code == 201

    invalid = client.post(
        "/api/v1/entities/pattern_test/records",
        json={"data": {"phone": "abc"}},
        headers=headers,
    )
    assert invalid.status_code == 422


# ---------------------------------------------------------------------------
# Lookup searchable types
# ---------------------------------------------------------------------------


def test_lookup_searches_enum_and_email_fields() -> None:
    headers, _ = _register()
    payload = {
        "code": "lookup_search",
        "name": "Lookup Search",
        "fields": [
            {"code": "name", "type": "text"},
            {"code": "status", "type": "enum", "options": [
                {"value": "active", "label": "Active"},
                {"value": "inactive", "label": "Inactive"},
            ]},
            {"code": "email", "type": "email"},
        ],
    }
    assert client.post("/api/v1/metadata/entities", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/metadata/entities/lookup_search/publish", headers=headers).status_code == 200

    client.post(
        "/api/v1/entities/lookup_search/records",
        json={"data": {"name": "Alice", "status": "active", "email": "alice@test.com"}},
        headers=headers,
    )

    by_email = client.get("/api/v1/entities/lookup_search/lookup", params={"q": "alice@test"}, headers=headers)
    assert by_email.status_code == 200
    assert len(by_email.json()) == 1
