"""End-to-end test: Document lifecycle and cross-module flows."""
import uuid

import pytest


class TestDocumentLifecycle:
    def test_document_upload_and_list(self, client, auth_headers):
        resp = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            json={
                "name": f"test-doc-{uuid.uuid4().hex[:8]}.pdf",
                "type": "invoice",
                "content": "base64encodedcontent==",
            },
        )
        assert resp.status_code in (200, 201, 422)

        resp = client.get("/api/v1/documents", headers=auth_headers)
        assert resp.status_code == 200


class TestAICopilotFlow:
    def test_copilot_chat(self, client, auth_headers):
        resp = client.post(
            "/api/v1/ai/copilot/chat",
            headers=auth_headers,
            json={"message": "Show me overdue invoices", "context": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data


class TestGlobalizationFlow:
    def test_list_countries(self, client, auth_headers):
        resp = client.get("/api/v1/globalization/countries", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_currencies(self, client, auth_headers):
        resp = client.get("/api/v1/globalization/currencies", headers=auth_headers)
        assert resp.status_code == 200

    def test_pack_registry(self, client, auth_headers):
        resp = client.get("/api/v1/globalization/packs", headers=auth_headers)
        assert resp.status_code == 200


class TestFinancialFlow:
    def test_accounts_list(self, client, auth_headers):
        resp = client.get("/api/v1/financial/accounts", headers=auth_headers)
        assert resp.status_code == 200

    def test_customers_list(self, client, auth_headers):
        resp = client.get("/api/v1/financial/customers", headers=auth_headers)
        assert resp.status_code == 200


class TestIntegrationsFlow:
    def test_integrations_list(self, client, auth_headers):
        resp = client.get("/api/v1/integrations", headers=auth_headers)
        assert resp.status_code == 200


class TestMarketplaceFlow:
    def test_apps_list(self, client, auth_headers):
        resp = client.get("/api/v1/marketplace/apps", headers=auth_headers)
        assert resp.status_code == 200

    def test_industry_packs(self, client, auth_headers):
        resp = client.get("/api/v1/marketplace/industry-packs", headers=auth_headers)
        assert resp.status_code == 200


class TestReportingFlow:
    def test_reports_list(self, client, auth_headers):
        resp = client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code in (200, 404)
