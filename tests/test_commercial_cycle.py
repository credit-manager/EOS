"""Real commercial-cycle integration test: registration -> customer -> invoice -> issue -> payment -> GL."""
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import text
from main import app
from database import SessionLocal


def test_real_commercial_cycle_posts_to_general_ledger():
    email = f"commercial-{uuid4().hex[:10]}@example.test"
    password = "StrongPass!123"
    test_client = TestClient(app)
    registration = test_client.post("/api/v1/auth/register", json={"email": email, "password": password, "company_name": "Commercial Smoke Company", "company_code": f"CSC-{uuid4().hex[:8].upper()}"})
    assert registration.status_code in (200, 201), registration.text
    db = SessionLocal()
    try:
        user = db.execute(text("SELECT id, tenant_id, company_id FROM dbp_users WHERE email = :email"), {"email": email}).fetchone()
        assert user
        tenant_id, company_id = user[1], user[2]
    finally:
        db.close()
    login = test_client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    customer = test_client.post(f"/api/v1/dynamic/companies/{company_id}/customers", headers=headers, json={"name": "Commercial Smoke Customer", "email": "customer@example.test"})
    assert customer.status_code == 200, customer.text
    customer_id = customer.json()["data"]["id"]
    invoice = test_client.post(f"/api/v1/dynamic/companies/{company_id}/invoices", headers=headers, json={"customer_id": customer_id, "invoice_date": "2026-09-05", "currency_code": "SAR", "lines": [{"description": "ERP implementation service", "quantity": 2, "unit_price": 500, "tax_rate": 15}]})
    assert invoice.status_code == 200, invoice.text
    invoice_id = invoice.json()["data"]["id"]
    issued = test_client.post(f"/api/v1/dynamic/invoices/{invoice_id}/issue", headers=headers)
    assert issued.status_code == 200, issued.text
    assert issued.json()["data"]["status"] == "issued"
    payment = test_client.post(f"/api/v1/dynamic/invoices/{invoice_id}/payments", headers=headers, json={"amount": 1150, "payment_date": "2026-09-05"})
    assert payment.status_code == 200, payment.text
    assert payment.json()["data"]["status"] == "paid"
    db = SessionLocal()
    try:
        entries = db.execute(text("SELECT id, reference FROM dbp_journal_entries WHERE tenant_id = :tid AND company_id = :cid AND reference IN (:invoice_ref, :payment_ref) ORDER BY reference"), {"tid": tenant_id, "cid": company_id, "invoice_ref": f"invoice:{invoice_id}", "payment_ref": f"payment:{invoice_id}:1150"}).fetchall()
        assert len(entries) == 2
        for entry_id, _ in entries:
            totals = db.execute(text("SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) FROM dbp_journal_lines WHERE journal_entry_id = :eid AND tenant_id = :tid"), {"eid": entry_id, "tid": tenant_id}).fetchone()
            assert round(float(totals[0]), 4) == round(float(totals[1]), 4)
    finally:
        db.close()
