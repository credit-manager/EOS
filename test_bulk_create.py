"""
P8.1 Bulk Create Tests
Tests batch creation of records with validation, tenant isolation, RBAC, and audit.
"""

import subprocess
import time
import sys
import os
import uuid

sys.path.insert(0, '.')

from core.auth import create_test_token
import httpx

BASE = "http://127.0.0.1:8000"
EP = f"{BASE}/api/v1/dynamic/entities"
ENTITY = "test_product"

TOKEN_A = create_test_token("tenant_a", roles=["dynamic_manager"])
TOKEN_B = create_test_token("tenant_b", roles=["dynamic_manager"])
TOKEN_VIEWER = create_test_token("tenant_a", roles=["dynamic_viewer"])
HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}
HEADERS_VIEWER = {"Authorization": f"Bearer {TOKEN_VIEWER}"}


def start_server():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    time.sleep(3)
    return proc


def stop_server(proc):
    proc.terminate()
    proc.wait(timeout=5)


results = []


def test(name, actual, expected):
    ok = actual == expected
    results.append((name, ok))
    status = "PASS" if ok else "FAIL"
    print(f"  {status} - {name}: got {actual}, expected {expected}")
    return ok


print("\n" + "=" * 60)
print("P8.1 BULK CREATE TESTS")
print("=" * 60)

server = start_server()
client = httpx.Client(base_url=BASE, timeout=15)


# ──────────────────────────────────────────────
# Test 1: Basic bulk create (3 records)
# ──────────────────────────────────────────────
print("\n--- Test 1: Basic bulk create (3 records) ---")
code1 = f"BULK-{uuid.uuid4().hex[:6]}"
code2 = f"BULK-{uuid.uuid4().hex[:6]}"
code3 = f"BULK-{uuid.uuid4().hex[:6]}"
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": [
        {"code": code1, "name": "Bulk A1", "price": 10, "tenant_id": "tenant_a"},
        {"code": code2, "name": "Bulk A2", "price": 20, "tenant_id": "tenant_a"},
        {"code": code3, "name": "Bulk A3", "price": 30, "tenant_id": "tenant_a"},
    ]}
)
data = r.json()
test("Status 200", r.status_code, 200)
test("Count = 3", data.get("count"), 3)
test("Has created IDs", len(data.get("created", [])), 3)
test("Tenant = tenant_a", data.get("effective_tenant"), "tenant_a")


# ──────────────────────────────────────────────
# Test 2: Bulk create — empty list → 400
# ──────────────────────────────────────────────
print("\n--- Test 2: Empty list → 400 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": []}
)
test("Empty list → 400", r.status_code, 400)


# ──────────────────────────────────────────────
# Test 3: Bulk create — missing records field → 400
# ──────────────────────────────────────────────
print("\n--- Test 3: Missing 'records' field → 400 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"data": [{}]}
)
test("Missing records → 400", r.status_code, 400)


# ──────────────────────────────────────────────
# Test 4: Tenant isolation — payload.tenant_id ignored
# ──────────────────────────────────────────────
print("\n--- Test 4: Tenant spoofing → under tenant_a ---")
spoof_code = f"SPOOF-{uuid.uuid4().hex[:6]}"
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": [
        {"code": spoof_code, "name": "Spoof Test", "price": 99, "tenant_id": "tenant_b"},
    ]}
)
data = r.json()
test("Status 200", r.status_code, 200)
test("Effective tenant = tenant_a", data.get("effective_tenant"), "tenant_a")


# ──────────────────────────────────────────────
# Test 5: RBAC — viewer cannot bulk create → 403
# ──────────────────────────────────────────────
print("\n--- Test 5: Viewer bulk create → 403 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_VIEWER,
    json={"records": [
        {"code": f"FAIL-{uuid.uuid4().hex[:6]}", "name": "Fail", "price": 1},
    ]}
)
test("Viewer bulk create → 403", r.status_code, 403)


# ──────────────────────────────────────────────
# Test 6: Validation error — missing required field
# ──────────────────────────────────────────────
print("\n--- Test 6: Missing required field → 400 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": [
        {"name": "No Code", "price": 10},  # code is required
    ]}
)
test("Missing required → 400", r.status_code, 400)


# ──────────────────────────────────────────────
# Test 7: Duplicate code within batch
# ──────────────────────────────────────────────
print("\n--- Test 7: Duplicate in batch → 400 ---")
dup_code = f"DUP-{uuid.uuid4().hex[:6]}"
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": [
        {"code": dup_code, "name": "Dup1", "price": 10, "tenant_id": "tenant_a"},
        {"code": dup_code, "name": "Dup2", "price": 20, "tenant_id": "tenant_a"},
    ]}
)
# First insert should fail on duplicate unique constraint
test("Duplicate in batch → 400 or 409", r.status_code in [400, 409], True)


# ──────────────────────────────────────────────
# Test 8: Bulk create — no token → 401
# ──────────────────────────────────────────────
print("\n--- Test 8: No token → 401 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    json={"records": [
        {"code": f"NOAUTH-{uuid.uuid4().hex[:6]}", "name": "No Auth", "price": 1},
    ]}
)
test("No token → 401", r.status_code, 401)


# ──────────────────────────────────────────────
# Test 9: Bulk create — tenant B separate scope
# ──────────────────────────────────────────────
print("\n--- Test 9: Tenant B bulk create ---")
b_code1 = f"BULK-B-{uuid.uuid4().hex[:6]}"
b_code2 = f"BULK-B-{uuid.uuid4().hex[:6]}"
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_B,
    json={"records": [
        {"code": b_code1, "name": "Bulk B1", "price": 100, "tenant_id": "tenant_b"},
        {"code": b_code2, "name": "Bulk B2", "price": 200, "tenant_id": "tenant_b"},
    ]}
)
data = r.json()
test("Status 200", r.status_code, 200)
test("Count = 2", data.get("count"), 2)
test("Tenant = tenant_b", data.get("effective_tenant"), "tenant_b")


# ──────────────────────────────────────────────
# Test 10: Verify cross-tenant isolation
# ──────────────────────────────────────────────
print("\n--- Test 10: Cross-tenant isolation ---")
r_a = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/records",
    headers=HEADERS_A,
    params={"limit": 200}
)
r_b = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/records",
    headers=HEADERS_B,
    params={"limit": 200}
)
ids_a = set(row.get("id") for row in r_a.json().get("data", []))
ids_b = set(row.get("id") for row in r_b.json().get("data", []))
no_overlap = ids_a.isdisjoint(ids_b)
test("No cross-tenant overlap", no_overlap, True)


# ──────────────────────────────────────────────
# Test 11: Audit logs created
# ──────────────────────────────────────────────
print("\n--- Test 11: Audit logs ---")
from database import SessionLocal
db = SessionLocal()
from sqlalchemy import text
audit_count = db.execute(text(
    "SELECT COUNT(*) FROM audit_logs "
    "WHERE module = 'dynamic' AND action = 'bulk_create' "
    "AND entity_type = :entity"
), {"entity": ENTITY}).scalar()
db.close()
test("Audit logs created", audit_count > 0, True)
print(f"  (audit entries: {audit_count})")


# ──────────────────────────────────────────────
# Results Summary
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"RESULTS: {passed}/{total} passed")

client.close()
stop_server(server)

if passed < total:
    print("\nFailed tests:")
    for name, ok in results:
        if not ok:
            print(f"  FAIL: {name}")
    sys.exit(1)
else:
    print("\nAll P8.1 tests passed!")
    sys.exit(0)
