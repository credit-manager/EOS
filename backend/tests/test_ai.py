"""Tests for AI-powered features: smart search, auto-tagging, similarity, dedup, anomaly."""

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _register(email: str | None = None) -> dict[str, str]:
    email = email or f"ai-{uuid4()}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Correct-Horse-Battery-42",
            "tenant_name": f"AI Tenant {uuid4()}",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _setup_entity(headers: dict, code: str = "ai_docs") -> None:
    payload = {
        "code": code,
        "name": "AI Documents",
        "fields": [
            {"code": "title", "type": "text"},
            {"code": "description", "type": "text"},
            {"code": "category", "type": "enum", "options": [
                {"value": "tech", "label": "Technology"},
                {"value": "finance", "label": "Finance"},
                {"value": "hr", "label": "Human Resources"},
            ]},
            {"code": "amount", "type": "decimal"},
        ],
    }
    resp = client.post("/api/v1/metadata/entities", json=payload, headers=headers)
    assert resp.status_code == 201
    resp = client.post(f"/api/v1/metadata/entities/{code}/publish", headers=headers)
    assert resp.status_code == 200


def _create_record(headers: dict, data: dict, code: str = "ai_docs") -> str:
    resp = client.post(f"/api/v1/entities/{code}/records", json={"data": data}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Smart Search
# ---------------------------------------------------------------------------


def test_smart_search_returns_ranked_results() -> None:
    headers = _register()
    _setup_entity(headers)

    _create_record(headers, {"title": "Python Programming Guide", "description": "Learn Python for data science", "category": "tech", "amount": "50.00"})
    _create_record(headers, {"title": "Financial Analysis", "description": "Quarterly financial report for investors", "category": "finance", "amount": "1500.00"})
    _create_record(headers, {"title": "HR Policy Manual", "description": "Employee handbook and HR policies", "category": "hr", "amount": "0.00"})

    results = client.post(
        "/api/v1/ai/entities/ai_docs/search",
        json={"query": "Python programming", "limit": 3},
        headers=headers,
    )
    assert results.status_code == 200
    items = results.json()
    assert len(items) > 0
    assert items[0]["score"] > 0
    assert "id" in items[0]
    assert "data" in items[0]


def test_smart_search_empty_query() -> None:
    headers = _register()
    _setup_entity(headers)
    _create_record(headers, {"title": "Test", "category": "tech"})

    results = client.post(
        "/api/v1/ai/entities/ai_docs/search",
        json={"query": "", "limit": 5},
        headers=headers,
    )
    assert results.status_code == 422


def test_smart_search_no_records() -> None:
    headers = _register()
    _setup_entity(headers, "empty_entity")

    results = client.post(
        "/api/v1/ai/entities/empty_entity/search",
        json={"query": "anything", "limit": 5},
        headers=headers,
    )
    assert results.status_code == 200
    assert results.json() == []


def test_smart_search_tenant_isolation() -> None:
    headers_a = _register()
    headers_b = _register()
    _setup_entity(headers_a, "tenant_docs")
    _setup_entity(headers_b, "tenant_docs")

    _create_record(headers_a, {"title": "Secret Document", "category": "tech"}, "tenant_docs")

    results_a = client.post(
        "/api/v1/ai/entities/tenant_docs/search",
        json={"query": "Secret", "limit": 5},
        headers=headers_a,
    )
    results_b = client.post(
        "/api/v1/ai/entities/tenant_docs/search",
        json={"query": "Secret", "limit": 5},
        headers=headers_b,
    )
    assert results_a.status_code == 200
    assert len(results_a.json()) == 1
    assert results_b.status_code == 200
    assert len(results_b.json()) == 0


# ---------------------------------------------------------------------------
# Auto-tagging
# ---------------------------------------------------------------------------


def test_auto_tag_extracts_keywords() -> None:
    headers = _register()
    _setup_entity(headers, "tag_entity")

    rid = _create_record(headers, {
        "title": "Machine Learning in Construction",
        "description": "Using machine learning algorithms for construction project optimization",
        "category": "tech",
    }, "tag_entity")

    tags = client.post(
        f"/api/v1/ai/entities/tag_entity/records/{rid}/tags",
        headers=headers,
    )
    assert tags.status_code == 200
    tag_list = tags.json()
    assert isinstance(tag_list, list)
    assert len(tag_list) > 0
    assert any("machine" in t or "learning" in t or "construction" in t for t in tag_list)


def test_auto_tag_nonexistent_record() -> None:
    headers = _register()
    _setup_entity(headers, "tag_entity2")
    fake_id = str(uuid4())

    tags = client.post(
        f"/api/v1/ai/entities/tag_entity2/records/{fake_id}/tags",
        headers=headers,
    )
    assert tags.status_code == 200
    assert tags.json() == []


# ---------------------------------------------------------------------------
# Record Similarity
# ---------------------------------------------------------------------------


def test_find_similar_records() -> None:
    headers = _register()
    _setup_entity(headers, "sim_entity")

    id1 = _create_record(headers, {
        "title": "Python programming tutorial for beginners",
        "description": "Learn Python step by step",
        "category": "tech",
    }, "sim_entity")

    id2 = _create_record(headers, {
        "title": "Advanced Python programming techniques",
        "description": "Master Python advanced concepts",
        "category": "tech",
    }, "sim_entity")

    _create_record(headers, {
        "title": "Financial quarterly report",
        "description": "Q3 financial analysis and projections",
        "category": "finance",
    }, "sim_entity")

    results = client.post(
        f"/api/v1/ai/entities/sim_entity/records/{id1}/similar",
        params={"limit": 5, "min_score": 0.05},
        headers=headers,
    )
    assert results.status_code == 200
    items = results.json()
    assert len(items) >= 1
    assert items[0]["id"] == id2
    assert items[0]["similarity"] > 0


# ---------------------------------------------------------------------------
# Smart Deduplication
# ---------------------------------------------------------------------------


def test_detect_duplicates() -> None:
    headers = _register()
    _setup_entity(headers, "dup_entity")

    _create_record(headers, {
        "title": "Company registration document",
        "description": "Official company registration papers",
        "category": "tech",
    }, "dup_entity")

    _create_record(headers, {
        "title": "Company registration documentation",
        "description": "Official company registration paperwork",
        "category": "tech",
    }, "dup_entity")

    _create_record(headers, {
        "title": "Unrelated financial report",
        "description": "Quarterly earnings analysis",
        "category": "finance",
    }, "dup_entity")

    results = client.post(
        "/api/v1/ai/entities/dup_entity/duplicates",
        params={"threshold": 0.3, "limit": 10},
        headers=headers,
    )
    assert results.status_code == 200
    pairs = results.json()
    assert len(pairs) >= 1
    assert pairs[0]["similarity"] > 0.3


def test_detect_duplicates_no_duplicates() -> None:
    headers = _register()
    _setup_entity(headers, "no_dup_entity")

    _create_record(headers, {"title": "Alpha", "description": "Completely different content A", "category": "tech"}, "no_dup_entity")
    _create_record(headers, {"title": "Beta", "description": "Unrelated content B", "category": "finance"}, "no_dup_entity")

    results = client.post(
        "/api/v1/ai/entities/no_dup_entity/duplicates",
        params={"threshold": 0.9, "limit": 10},
        headers=headers,
    )
    assert results.status_code == 200
    assert results.json() == []


# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------


def test_detect_anomalies() -> None:
    headers = _register()
    _setup_entity(headers, "anom_entity")

    for i in range(10):
        _create_record(headers, {
            "title": f"Record {i}",
            "amount": str(100 + i * 10),
            "category": "tech",
        }, "anom_entity")

    _create_record(headers, {
        "title": "Outlier",
        "amount": "99999.00",
        "category": "tech",
    }, "anom_entity")

    results = client.post(
        "/api/v1/ai/entities/anom_entity/anomalies",
        params={"z_score_threshold": 1.5},
        headers=headers,
    )
    assert results.status_code == 200
    anomalies = results.json()
    assert len(anomalies) >= 1
    assert any(a["field"] == "amount" for a in anomalies)
    assert any(a["direction"] == "high" for a in anomalies)


def test_detect_anomalies_no_numeric_fields() -> None:
    headers = _register()
    _setup_entity(headers, "text_only_entity")

    _create_record(headers, {"title": "Just text", "category": "tech"}, "text_only_entity")

    results = client.post(
        "/api/v1/ai/entities/text_only_entity/anomalies",
        headers=headers,
    )
    assert results.status_code == 200
    assert results.json() == []
