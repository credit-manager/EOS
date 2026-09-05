"""End-to-end tenant isolation tests through the real FastAPI application.

The test authenticates two independently registered tenants, creates data through
public API endpoints, and verifies that a tenant cannot read, update, delete, or
reassign another tenant's record by identifier or request payload.
"""
import os
import uuid

from sqlalchemy import create_engine, text


PASSWORD = "TestPassword123!"


def _register_and_login(client, label: str) -> tuple[str, str]:
    email = f"api-isolation-{label}-{uuid.uuid4().hex}@example.test"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "first_name": "API",
            "last_name": label.title(),
            "company_name": f"API Isolation {label} {uuid.uuid4().hex[:8]}",
        },
    )
    assert response.status_code in (200, 201), response.text
    registration = response.json()
    tenant_id = registration["data"]["tenant_id"]

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return tenant_id, token


def test_fastapi_cross_tenant_account_isolation(test_client):
    """Tenant B must never access Tenant A's account through FastAPI."""
    tenant_a, token_a = _register_and_login(test_client, "tenant-a")
    tenant_b, token_b = _register_and_login(test_client, "tenant-b")
    assert tenant_a != tenant_b

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Positive control: Tenant A can create and read its own record.
    create_response = test_client.post(
        "/api/v1/accounting/accounts",
        headers=headers_a,
        json={
            "code": f"E2E-{uuid.uuid4().hex[:10]}",
            "name": "Tenant A Confidential Account",
            "account_type": "asset",
        },
    )
    assert create_response.status_code == 201, create_response.text
    account_id = create_response.json()["id"]

    own_response = test_client.get(
        f"/api/v1/accounting/accounts/{account_id}", headers=headers_a
    )
    assert own_response.status_code == 200, own_response.text
    assert own_response.json()["id"] == account_id

    # Negative read: Tenant B cannot read Tenant A's record by direct ID.
    cross_read = test_client.get(
        f"/api/v1/accounting/accounts/{account_id}", headers=headers_b
    )
    assert cross_read.status_code == 404, cross_read.text

    # Negative collection read: Tenant B's account list cannot contain A's record.
    list_response = test_client.get("/api/v1/accounting/accounts", headers=headers_b)
    assert list_response.status_code == 200, list_response.text
    assert all(item["id"] != account_id for item in list_response.json()["data"])

    # Negative update: Tenant B cannot change A's record by ID.
    cross_update = test_client.put(
        f"/api/v1/accounting/accounts/{account_id}",
        headers=headers_b,
        json={"name_en": "Cross Tenant Mutation"},
    )
    assert cross_update.status_code == 404, cross_update.text

    # Negative delete: Tenant B cannot delete A's record by ID.
    cross_delete = test_client.delete(
        f"/api/v1/accounting/accounts/{account_id}", headers=headers_b
    )
    assert cross_delete.status_code == 404, cross_delete.text

    # Tenant spoofing: a client-supplied tenant_id must not move a record into A.
    spoof_create = test_client.post(
        "/api/v1/accounting/accounts",
        headers=headers_b,
        json={
            "code": f"SPOOF-{uuid.uuid4().hex[:10]}",
            "name": "Tenant B Own Account",
            "account_type": "asset",
            "tenant_id": tenant_a,
        },
    )
    assert spoof_create.status_code == 201, spoof_create.text
    spoof_id = spoof_create.json()["id"]

    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as conn:
            stored = conn.execute(
                text("SELECT tenant_id FROM dbp_accounts WHERE id = :id"),
                {"id": spoof_id},
            ).scalar_one()
        assert stored == tenant_b
    finally:
        engine.dispose()
