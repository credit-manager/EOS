"""Test the ETA invoice endpoint"""
import sys
sys.path.insert(0, r'D:\EOS\Eos final\eos-system\backend')
import httpx
import json

BASE = "http://127.0.0.1:8001/api/v1"

# First register and login
uid = "test001"
r = httpx.post(f"{BASE}/auth/register", json={
    "email": f"eta-{uid}@test.com",
    "password": "EtaTest!@#",
    "company_name": f"ETA Test {uid}",
    "company_name_ar": "اختبار ETA",
    "industry": "tech"})
print(f"Register: {r.status_code}")

r = httpx.post(f"{BASE}/auth/login", json={
    "email": f"eta-{uid}@test.com",
    "password": "EtaTest!@#",
    "tenant_id": r.json()["tenant_id"]})
print(f"Login: {r.status_code}")
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

# Test the ETA invoice endpoint
r = httpx.post(f"{BASE}/eta/1/eta-invoices", json={
    "invoice_number": "EI-20260820-000001",
    "issue_date": "2026-08-20",
    "due_date": "2026-09-20",
    "supplier_id": "supplier-001",
    "buyer_id": "customer-001",
    "supplier_name_ar": "شركة الغذاء",
    "buyer_name_ar": "شركة التوزيع",
    "items": [
        {"description": "منتج غذائي", "quantity": 100, "unit_price": 50.00, "total_price": 5000.00}
    ],
    "currency": "EGP"
}, headers=h)
print(f"ETA Invoice: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  invoice_number: {data.get('invoice_number')}")
    print(f"  tax_amount: {data.get('tax_amount')}")
    print(f"  total_amount: {data.get('total_amount')}")
    print(f"  eta_status: {data.get('eta_status')}")
else:
    print(f"  Error: {r.text[:200]}")
" 2>&1