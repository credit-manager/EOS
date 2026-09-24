"""Tests for Financial Ledger — chart of accounts, journal entries, posting, reversal, trial balance."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from backend.app.db import SessionLocal
from backend.app.main import app

client = TestClient(app)
_PASSWORD = "Correct-Horse-Battery-42"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register(email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": _PASSWORD, "tenant_name": f"Tenant {email}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_account(token: str, code: str, account_type: str, normal_balance: str = "debit") -> dict:
    resp = client.post(
        "/api/v1/financial/ledger/accounts",
        headers=_headers(token),
        json={
            "account_code": code,
            "account_name": f"Account {code}",
            "account_type": account_type,
            "normal_balance": normal_balance,
            "currency": "USD",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_journal_entry(token: str, lines: list[dict], description: str = "Test entry") -> dict:
    resp = client.post(
        "/api/v1/financial/ledger/entries",
        headers=_headers(token),
        json={
            "entry_date": str(date.today()),
            "currency": "USD",
            "description": description,
            "lines": lines,
        },
    )
    return resp


def _post_entry(token: str, entry_id: str) -> dict:
    resp = client.post(
        f"/api/v1/financial/ledger/entries/{entry_id}/post",
        headers=_headers(token),
    )
    return resp


# ===================================================================
# 1. Creating a chart of accounts (debit/credit accounts)
# ===================================================================

class TestChartOfAccounts:
    def test_create_debit_account(self):
        user = _register(f"ledger-coa-debit-{uuid.uuid4()}@example.com")
        account = _create_account(user["access_token"], "1000", "asset", "debit")
        assert account["account_code"] == "1000"
        assert account["account_type"] == "asset"
        assert account["is_active"] is True

    def test_create_credit_account(self):
        user = _register(f"ledger-coa-credit-{uuid.uuid4()}@example.com")
        account = _create_account(user["access_token"], "4000", "revenue", "credit")
        assert account["account_code"] == "4000"
        assert account["account_type"] == "revenue"

    def test_create_all_account_types(self):
        user = _register(f"ledger-coa-all-{uuid.uuid4()}@example.com")
        types = [
            ("1000", "asset", "debit"),
            ("2000", "liability", "credit"),
            ("3000", "equity", "credit"),
            ("4000", "revenue", "credit"),
            ("5000", "expense", "debit"),
        ]
        for code, acct_type, normal in types:
            account = _create_account(user["access_token"], code, acct_type, normal)
            assert account["account_code"] == code
            assert account["account_type"] == acct_type

    def test_accounts_are_listed(self):
        user = _register(f"ledger-coa-list-{uuid.uuid4()}@example.com")
        _create_account(user["access_token"], "1000", "asset")
        _create_account(user["access_token"], "4000", "revenue")
        resp = client.get("/api/v1/financial/ledger/accounts", headers=_headers(user["access_token"]))
        assert resp.status_code == 200
        codes = {a["account_code"] for a in resp.json()}
        assert "1000" in codes
        assert "4000" in codes

    def test_duplicate_account_code_rejected(self):
        user = _register(f"ledger-coa-dup-{uuid.uuid4()}@example.com")
        _create_account(user["access_token"], "1000", "asset")
        resp = client.post(
            "/api/v1/financial/ledger/accounts",
            headers=_headers(user["access_token"]),
            json={"account_code": "1000", "account_name": "Dup", "account_type": "asset", "currency": "USD", "normal_balance": "debit"},
        )
        assert resp.status_code == 409


# ===================================================================
# 2. Creating a journal entry with balanced debits/credits
# ===================================================================

class TestJournalEntryCreation:
    def test_create_balanced_entry(self):
        user = _register(f"ledger-je-bal-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        revenue = _create_account(user["access_token"], "4000", "revenue")

        resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "500.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "500.000000"},
        ])
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "draft"
        assert body["currency"] == "USD"

    def test_entry_has_sequential_number(self):
        user = _register(f"ledger-je-seq-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        revenue = _create_account(user["access_token"], "4000", "revenue")

        first = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "100.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "100.000000"},
        ])
        second = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "200.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "200.000000"},
        ])
        assert first.status_code == 201
        assert second.status_code == 201
        assert second.json()["entry_number"] > first.json()["entry_number"]

    def test_entry_with_multiple_lines(self):
        user = _register(f"ledger-je-multi-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        expense1 = _create_account(user["access_token"], "5100", "expense")
        expense2 = _create_account(user["access_token"], "5200", "expense")

        resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "300.000000", "credit": "0.000000"},
            {"account_id": expense1["id"], "debit": "0.000000", "credit": "150.000000"},
            {"account_id": expense2["id"], "debit": "0.000000", "credit": "150.000000"},
        ], description="Compound entry")
        assert resp.status_code == 201, resp.text


# ===================================================================
# 3. Unbalanced entries are rejected
# ===================================================================

class TestUnbalancedRejection:
    def test_debits_not_equal_credits(self):
        user = _register(f"ledger-unbal-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        revenue = _create_account(user["access_token"], "4000", "revenue")

        resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "100.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "90.000000"},
        ])
        assert resp.status_code == 422

    def test_zero_amount_rejected(self):
        user = _register(f"ledger-zero-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        revenue = _create_account(user["access_token"], "4000", "revenue")

        resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "0", "credit": "0"},
            {"account_id": revenue["id"], "debit": "0", "credit": "0"},
        ])
        assert resp.status_code == 422

    def test_single_line_rejected(self):
        user = _register(f"ledger-single-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")

        resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "100.000000", "credit": "0.000000"},
        ])
        assert resp.status_code == 422

    def test_credit_exceeds_debit_rejected(self):
        user = _register(f"ledger-exceed-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        revenue = _create_account(user["access_token"], "4000", "revenue")

        resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "50.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "100.000000"},
        ])
        assert resp.status_code == 422


# ===================================================================
# 4. Posting a draft entry
# ===================================================================

class TestPosting:
    def test_post_draft_entry(self):
        user = _register(f"ledger-post-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        revenue = _create_account(user["access_token"], "4000", "revenue")

        entry_resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "1000.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "1000.000000"},
        ])
        assert entry_resp.status_code == 201
        entry_id = entry_resp.json()["id"]

        post_resp = _post_entry(user["access_token"], entry_id)
        assert post_resp.status_code == 200
        assert post_resp.json()["status"] == "posted"
        assert post_resp.json()["posted_by"] is not None

    def test_cannot_post_twice(self):
        user = _register(f"ledger-post2-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        revenue = _create_account(user["access_token"], "4000", "revenue")

        entry_resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "500.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "500.000000"},
        ])
        entry_id = entry_resp.json()["id"]

        first_post = _post_entry(user["access_token"], entry_id)
        assert first_post.status_code == 200

        second_post = _post_entry(user["access_token"], entry_id)
        assert second_post.status_code == 409

    def test_post_nonexistent_entry(self):
        user = _register(f"ledger-post-no-{uuid.uuid4()}@example.com")
        fake_id = str(uuid.uuid4())
        resp = _post_entry(user["access_token"], fake_id)
        assert resp.status_code == 404


# ===================================================================
# 5. Reversing a posted entry
# ===================================================================

class TestReversal:
    def test_reverse_posted_entry(self):
        user = _register(f"ledger-rev-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        revenue = _create_account(user["access_token"], "4000", "revenue")

        entry_resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "750.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "750.000000"},
        ])
        entry_id = entry_resp.json()["id"]
        _post_entry(user["access_token"], entry_id)

        resp = client.post(
            f"/api/v1/financial/ledger/entries/{entry_id}/reverse",
            headers=_headers(user["access_token"]),
            json={"reason": "Testing reversal"},
        )
        assert resp.status_code == 200
        reversal = resp.json()
        assert reversal["status"] == "draft"
        assert reversal["reference_type"] == "reversal"

    def test_cannot_reverse_draft_entry(self):
        user = _register(f"ledger-rev-draft-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset")
        revenue = _create_account(user["access_token"], "4000", "revenue")

        entry_resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "200.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "200.000000"},
        ])
        entry_id = entry_resp.json()["id"]

        resp = client.post(
            f"/api/v1/financial/ledger/entries/{entry_id}/reverse",
            headers=_headers(user["access_token"]),
            json={"reason": "Oops"},
        )
        assert resp.status_code == 409


# ===================================================================
# 6. Trial balance calculation
# ===================================================================

class TestTrialBalance:
    def test_trial_balance_after_posting(self):
        user = _register(f"ledger-tb-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset", "debit")
        revenue = _create_account(user["access_token"], "4000", "revenue", "credit")

        entry_resp = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "1000.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "1000.000000"},
        ])
        _post_entry(user["access_token"], entry_resp.json()["id"])

        resp = client.get(
            "/api/v1/financial/ledger/trial-balance?currency=USD",
            headers=_headers(user["access_token"]),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_balanced"] is True
        assert Decimal(body["total_debit"]) == Decimal("1000.000000")
        assert Decimal(body["total_credit"]) == Decimal("1000.000000")

    def test_trial_balance_empty_when_no_postings(self):
        user = _register(f"ledger-tb-empty-{uuid.uuid4()}@example.com")
        _create_account(user["access_token"], "1000", "asset")
        resp = client.get(
            "/api/v1/financial/ledger/trial-balance?currency=USD",
            headers=_headers(user["access_token"]),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_balanced"] is True
        assert Decimal(body["total_debit"]) == Decimal("0.000000")
        assert Decimal(body["total_credit"]) == Decimal("0.000000")

    def test_trial_balance_multiple_entries(self):
        user = _register(f"ledger-tb-multi-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset", "debit")
        revenue = _create_account(user["access_token"], "4000", "revenue", "credit")

        for amt in ["100.000000", "250.000000", "650.000000"]:
            entry = _create_journal_entry(user["access_token"], [
                {"account_id": cash["id"], "debit": amt, "credit": "0.000000"},
                {"account_id": revenue["id"], "debit": "0.000000", "credit": amt},
            ])
            _post_entry(user["access_token"], entry.json()["id"])

        resp = client.get(
            "/api/v1/financial/ledger/trial-balance?currency=USD",
            headers=_headers(user["access_token"]),
        )
        body = resp.json()
        assert body["is_balanced"] is True
        assert Decimal(body["total_debit"]) == Decimal("1000.000000")
        assert Decimal(body["total_credit"]) == Decimal("1000.000000")
        assert len(body["lines"]) >= 2

    def test_trial_balance_shows_account_balances(self):
        user = _register(f"ledger-tb-bal-{uuid.uuid4()}@example.com")
        cash = _create_account(user["access_token"], "1000", "asset", "debit")
        revenue = _create_account(user["access_token"], "4000", "revenue", "credit")

        entry = _create_journal_entry(user["access_token"], [
            {"account_id": cash["id"], "debit": "500.000000", "credit": "0.000000"},
            {"account_id": revenue["id"], "debit": "0.000000", "credit": "500.000000"},
        ])
        _post_entry(user["access_token"], entry.json()["id"])

        resp = client.get(
            "/api/v1/financial/ledger/trial-balance?currency=USD",
            headers=_headers(user["access_token"]),
        )
        lines = resp.json()["lines"]
        cash_line = next(l for l in lines if l["code"] == "1000")
        rev_line = next(l for l in lines if l["code"] == "4000")
        assert Decimal(cash_line["debit"]) == Decimal("500.000000")
        assert Decimal(cash_line["credit"]) == Decimal("0.000000")
        assert Decimal(rev_line["debit"]) == Decimal("0.000000")
        assert Decimal(rev_line["credit"]) == Decimal("500.000000")
