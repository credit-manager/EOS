"""Integration tests — end-to-end flows through the API."""
import uuid

import pytest


class TestHealthAndVersion:
    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "service" in data
        assert "version" in data


class TestAuthFlow:
    def test_register_login_me(self, client):
        email = f"e2e-{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "TestPass12345!",
            "tenant_name": f"E2E Tenant {uuid.uuid4().hex[:8]}",
        })
        assert resp.status_code in (200, 201)

        resp = client.post("/api/v1/auth/token", json={
            "email": email,
            "password": "TestPass12345!",
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == email


class TestMetadataFlow:
    def test_create_entity(self, client, auth_headers):
        code = f"e2e_entity_{uuid.uuid4().hex[:6]}"
        resp = client.post("/api/v1/metadata/entities", headers=auth_headers, json={
            "code": code,
            "name": f"E2E_Entity_{uuid.uuid4().hex[:6]}",
            "label": "E2E Test Entity",
            "description": "Integration test entity",
            "fields": [
                {"code": "title", "label": "Title", "type": "text", "required": True},
                {"code": "amount", "label": "Amount", "type": "integer"},
                {"code": "status", "label": "Status", "type": "select", "select_options": [
                    {"value": "active", "label": "Active"},
                    {"value": "inactive", "label": "Inactive"},
                ]},
            ],
        })
        assert resp.status_code in (200, 201)
        entity = resp.json()

        # Publish the entity
        resp = client.post(f"/api/v1/metadata/entities/{code}/publish", headers=auth_headers)
        assert resp.status_code in (200, 201)

        # List entities - should now include our entity
        resp = client.get("/api/v1/metadata/entities", headers=auth_headers)
        assert resp.status_code == 200
        entities = resp.json()
        assert any(e.get("code") == code for e in entities)


class TestGraphFlow:
    def test_graph_map(self, client, auth_headers):
        resp = client.get("/api/v1/graph/map", headers=auth_headers)
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (dict, list))

    def test_graph_stats(self, client, auth_headers):
        resp = client.get("/api/v1/graph/stats", headers=auth_headers)
        assert resp.status_code == 200


class TestAnalyticsFlow:
    def test_home_analytics(self, client, auth_headers):
        resp = client.get("/api/v1/analytics/home", headers=auth_headers)
        assert resp.status_code == 200


class TestSettingsFlow:
    def test_get_settings(self, client, auth_headers):
        resp = client.get("/api/v1/settings", headers=auth_headers)
        assert resp.status_code == 200

    def test_update_settings(self, client, auth_headers):
        resp = client.patch(
            "/api/v1/settings",
            headers=auth_headers,
            json={"company_name": "E2E Test Company"},
        )
        assert resp.status_code in (200, 204)


class TestBillingFlow:
    def test_plans_then_subscribe(self, client, auth_headers):
        resp = client.get("/api/v1/billing/plans")
        assert resp.status_code == 200
        plans = resp.json()
        assert isinstance(plans, (list, dict))

        resp = client.get("/api/v1/billing/subscription", headers=auth_headers)
        assert resp.status_code in (200, 404)


class TestWorkflowsFlow:
    def test_list_workflows(self, client, auth_headers):
        resp = client.get("/api/v1/workflows/instances", headers=auth_headers)
        assert resp.status_code in (200, 404)

    def test_my_tasks(self, client, auth_headers):
        resp = client.get("/api/v1/workflows/my-tasks", headers=auth_headers)
        assert resp.status_code == 200


class TestSecurityAudit:
    def test_security_audit(self, client, auth_headers):
        resp = client.get("/api/v1/monitoring/security-audit", headers=auth_headers)
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert "score" in data
            assert "checks" in data
            assert len(data["checks"]) >= 5

    def test_monitoring_health(self, client, auth_headers):
        resp = client.get("/api/v1/monitoring/health", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert body["status"] in ("healthy", "degraded")
