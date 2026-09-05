"""Commercial smoke test: company -> customer -> invoice -> collection -> GL."""
import os
import uuid

from sqlalchemy import create_engine, text


PASSWORD = "CommercialTestPassword123!"


def _auth(client):
    email = f"commercial-{uuid.uuid4().hex}@example.test"
    company_name = f"Commercial Smoke {uuid.uuid4().hex[:8]}"
    registration = client.post("/api/v1/auth/register", json={
        "email": email, "password": PASSWORD, "first_name": "Commercial", "last_name": "Tester", "company_name": company_name,
    })
    assert registration.status_code in (200, 201), registration.text
    data = registration.json()["data"]
    engine = create_engine(os.environ["DATABASE_URL"], future=True)
    try:
        with engine.begin() as conn:
            updated = conn.execute(text("UPDATE dbp_users SET email_verified = TRUE, updated_at = CURRENT_TIMESTAMP WHERE email = :email"), {"email": email}).rowcount
            assert updated == 1
    finally:
        engine.dispose()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"tenant_id": data["tenant_id"], "company_id": data["company_id"], "token": login.json()["data"]["access_token"]}


def test_real_commercial_cycle_posts_to_general_ledger(test_client):
    ctx = _auth(test_client)
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    customer = test_client.post(
        f"/api/v1/dynamic/companies/{ctx['company_id']}/customers",
        headers=headers,
        json={"name": "Commercial Smoke Customer", "email": "customer@example.test"},
    )
    assert customer.status_code == 200, customer.text
    customer_id = customer.json()["data"]["id"]

    invoice = test_client.post(
        f"/api/v1/dynamic/companies/{ctx['company_id']}/invoices",
        headers=headers,
        json={
            "customer_id": customer_id,
            "invoice_date": "2026-09-05",
            "lines": [{"description": "ERP implementation service", "quantity": 2, "unit_price": 500, "tax_rate": 15}],
        },
    )
    assert invoice.status_code == 200, invoice.text
    invoice_id = invoice.json()["data"]["id"]

    issued = test_client.post(f"/api/v1/dynamic/invoices/{invoice_id}/issue", headers=headers)
    assert issued.status_code == 200, issued.text
    issue_data = issued.json()["data"]
    assert issue_data["status"] == "issued"
    assert issue_data["journal_entry_id"]

    payment = test_client.post(
        f"/api/v1/dynamic/invoices/{invoice_id}/payments",
        headers=headers,
        json={"amount": 1150, "payment_date": "2026-09-05"},
    )
    assert payment.status_code == 200, payment.text
    assert payment.json()["data"]["status"] == "paid"

    engine = create_engine(os.environ["DATABASE_URL"], future=True)
    try:
        with engine.connect() as conn:
            entries = conn.execute(text(
                "SELECT reference, total_debit, total_credit FROM dbp_journal_entries "
                "WHERE tenant_id = :tid AND company_id = :cid ORDER BY created_at"
            ), {"tid": ctx["tenant_id"], "cid": ctx["company_id"]}).fetchall()
            assert any(r[0] == f"invoice:{invoice_id}" for r in entries)
            assert any(str(r[0]).startswith(f"payment:{invoice_id}:") for r in entries)
            assert all(abs(float(r[1]) - float(r[2])) < 0.001 for r in entries)
    finally:
        engine.dispose()
