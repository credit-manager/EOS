from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _register(email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Correct-Horse-Battery-42", "tenant_name": f"Tenant {email}"},
    )
    assert response.status_code == 201
    return response.json()


def _account(token: str, code: str, account_type: str) -> dict:
    response = client.post(
        "/api/v1/financial/accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": code, "name": code, "account_type": account_type, "currency": "USD"},
    )
    assert response.status_code == 201
    return response.json()


def test_double_entry_posting_and_trial_balance() -> None:
    owner = _register("financial-owner@example.com")
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    cash = _account(owner["access_token"], "1000", "asset")
    revenue = _account(owner["access_token"], "4000", "revenue")

    entry = client.post(
        "/api/v1/financial/journal-entries",
        headers=headers,
        json={
            "accounting_date": str(date.today()),
            "currency": "USD",
            "description": "Initial sale",
            "reference": "INV-1",
            "lines": [
                {"account_id": cash["id"], "debit": "125.500000", "credit": "0"},
                {"account_id": revenue["id"], "debit": "0", "credit": "125.500000"},
            ],
        },
    )
    assert entry.status_code == 201
    assert entry.json()["status"] == "draft"

    posted = client.post(
        f"/api/v1/financial/journal-entries/{entry.json()['id']}/post",
        headers=headers,
    )
    assert posted.status_code == 200
    assert posted.json()["status"] == "posted"

    trial = client.get("/api/v1/financial/trial-balance?currency=USD", headers=headers)
    assert trial.status_code == 200
    body = trial.json()
    assert body["total_debit"] == "125.500000"
    assert body["total_credit"] == "125.500000"
    assert {line["code"] for line in body["lines"]} == {"1000", "4000"}

    repeated = client.post(
        f"/api/v1/financial/journal-entries/{entry.json()['id']}/post",
        headers=headers,
    )
    assert repeated.status_code == 409


def test_unbalanced_entry_is_rejected_before_persistence() -> None:
    owner = _register("unbalanced@example.com")
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    cash = _account(owner["access_token"], "1000", "asset")
    expense = _account(owner["access_token"], "5000", "expense")

    response = client.post(
        "/api/v1/financial/journal-entries",
        headers=headers,
        json={
            "accounting_date": str(date.today()),
            "currency": "USD",
            "description": "Broken entry",
            "lines": [
                {"account_id": cash["id"], "debit": "10", "credit": "0"},
                {"account_id": expense["id"], "debit": "0", "credit": "9"},
            ],
        },
    )
    assert response.status_code == 422


def test_financial_data_is_tenant_scoped() -> None:
    first = _register("financial-first@example.com")
    second = _register("financial-second@example.com")
    account = _account(first["access_token"], "1100", "asset")

    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    read = client.get(f"/api/v1/financial/journal-entries/{UUID(account['id'])}", headers=second_headers)
    assert read.status_code in {403, 404}

    second_accounts = client.get("/api/v1/financial/accounts", headers=second_headers)
    assert second_accounts.status_code == 200
    assert all(item["id"] != account["id"] for item in second_accounts.json())


def test_member_cannot_mutate_financial_core() -> None:
    owner = _register("financial-admin@example.com")
    member = _register("financial-member@example.com")
    admin_headers = {"Authorization": f"Bearer {owner['access_token']}"}
    added = client.post(
        "/api/v1/auth/members",
        headers=admin_headers,
        json={"email": "financial-member@example.com", "role": "member"},
    )
    assert added.status_code == 201

    login = client.post(
        "/api/v1/auth/token",
        json={
            "email": "financial-member@example.com",
            "password": "Correct-Horse-Battery-42",
            "tenant_id": owner["tenant_id"],
        },
    )
    assert login.status_code == 200
    member_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = client.get("/api/v1/financial/accounts", headers=member_headers)
    assert denied.status_code == 403
    assert member["tenant_id"] != owner["tenant_id"]
