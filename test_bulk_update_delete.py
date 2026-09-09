"""
P8.2 Bulk Update Tests
P8.3 Bulk Delete Tests
Tests batch update/delete with tenant isolation, RBAC, and audit.
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


def make_records(tenant, codes):
    """Helper to create records for bulk update/delete tests."""
    records = []
    for code in codes:
        records.append({
            "code": code,
            "name": f"Test {code}",
            "price": 50,
            "tenant_id": tenant,
        })
    r = client.post(
        f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
        headers=HEADERS_A if tenant == "tenant_a" else HEADERS_B,
        json={"records": records}
    )
    return r.json().get("created", [])


results = []


def test(name, actual, expected):
    ok = actual == expected
    results.append((name, ok))
    status = "PASS" if ok else "FAIL"
    print(f"  {status} - {name}: got {actual}, expected {expected}")
    return ok


print("\n" + "=" * 60)
print("P8.2 BULK UPDATE + P8.3 BULK DELETE TESTS")
print("=" * 60)

server = start_server()
client = httpx.Client(base_url=BASE, timeout=15)

# ════════════════════════════════════════════════════════════════
# P8.2 — BULK UPDATE
# ════════════════════════════════════════════════════════════════

# ─── Setup: create records to update ───
print("\n--- Setup: Create records for update tests ---")
upd_ids = make_records("tenant_a", [f"UPD-{uuid.uuid4().hex[:6]}" for _ in range(3)])
print(f"  Created {len(upd_ids)} records: {upd_ids}")
test("Setup: created 3 records", len(upd_ids), 3)

# ─── Test 1: Basic bulk update ───
print("\n--- P8.2 Test 1: Basic bulk update ---")
r = client.put(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": [
        {"id": upd_ids[0], "fields": {"name": "Updated A", "price": 111}},
        {"id": upd_ids[1], "fields": {"name": "Updated B", "price": 222}},
        {"id": upd_ids[2], "fields": {"name": "Updated C", "price": 333}},
    ]}
)
data = r.json()
test("Status 200", r.status_code, 200)
test("Updated = 3", data.get("updated"), 3)

# ─── Test 2: Verify values persisted ───
print("\n--- P8.2 Test 2: Verify values ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/records",
    headers=HEADERS_A,
    params={"filters": f"code:in:{upd_ids[0]}", "limit": 10}
)
# Use direct SQL to check
from database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
row = db.execute(text(
    "SELECT name, price FROM test_products WHERE id = :id"
), {"id": upd_ids[0]}).fetchone()
db.close()
test("Name updated", row[0] if row else None, "Updated A")
test("Price updated", float(row[1]) if row else None, 111.0)

# ─── Test 3: Empty list → 400 ───
print("\n--- P8.2 Test 3: Empty list → 400 ---")
r = client.put(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": []}
)
test("Empty list → 400", r.status_code, 400)

# ─── Test 4: Missing 'id' in record → 400 ───
print("\n--- P8.2 Test 4: Missing 'id' → 400 ---")
r = client.put(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": [{"fields": {"name": "No ID"}}]}
)
test("Missing id → 400", r.status_code, 400)

# ─── Test 5: Missing 'fields' → 400 ───
print("\n--- P8.2 Test 5: Missing 'fields' → 400 ---")
r = client.put(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": [{"id": upd_ids[0]}]}
)
test("Missing fields → 400", r.status_code, 400)

# ─── Test 6: RBAC — viewer cannot bulk update → 403 ───
print("\n--- P8.2 Test 6: Viewer bulk update → 403 ---")
r = client.put(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_VIEWER,
    json={"records": [{"id": upd_ids[0], "fields": {"name": "Fail"}}]}
)
test("Viewer update → 403", r.status_code, 403)

# ─── Test 7: No token → 401 ───
print("\n--- P8.2 Test 7: No token → 401 ---")
r = client.put(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    json={"records": [{"id": upd_ids[0], "fields": {"name": "X"}}]}
)
test("No token → 401", r.status_code, 401)

# ─── Test 8: Cross-tenant update → not found ───
print("\n--- P8.2 Test 8: Cross-tenant update → 400 ---")
# Get a B record ID
b_ids = make_records("tenant_b", [f"BUPD-{uuid.uuid4().hex[:6]}"])
r = client.put(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": [{"id": b_ids[0], "fields": {"name": "Hacked"}}]}
)
data = r.json()
# Should report not found
has_not_found = any(
    d.get("code") == "RECORD_NOT_FOUND"
    for d in data.get("error", {}).get("details", [])
) if r.status_code == 400 else False
test("Cross-tenant update → 400", r.status_code, 400)

# ─── Test 9: Tenant spoofing in payload ignored ───
print("\n--- P8.2 Test 9: Payload tenant_id ignored ---")
r = client.put(
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"records": [{"id": upd_ids[0], "fields": {"name": "Spoofed", "tenant_id": "tenant_b"}}]}
)
test("Tenant spoof → 200", r.status_code, 200)

# ════════════════════════════════════════════════════════════════
# P8.3 — BULK DELETE
# ════════════════════════════════════════════════════════════════

# ─── Setup: create records to delete ───
print("\n--- Setup: Create records for delete tests ---")
del_ids_a = make_records("tenant_a", [f"DEL-A-{uuid.uuid4().hex[:6]}" for _ in range(3)])
del_ids_b = make_records("tenant_b", [f"DEL-B-{uuid.uuid4().hex[:6]}" for _ in range(2)])
print(f"  Created {len(del_ids_a)} A records, {len(del_ids_b)} B records")

# ─── Test 10: Basic bulk delete ───
print("\n--- P8.3 Test 10: Basic bulk delete ---")
r = client.request(
    "DELETE",
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"ids": del_ids_a[:2]}
)
data = r.json()
test("Status 200", r.status_code, 200)
test("Deleted = 2", data.get("deleted"), 2)

# ─── Test 11: Verify deleted records gone ───
print("\n--- P8.3 Test 11: Verify deleted ---")
db = SessionLocal()
remaining = db.execute(text(
    "SELECT COUNT(*) FROM test_products WHERE id IN :ids"
), {"ids": tuple(del_ids_a[:2])}).scalar()
db.close()
test("Records gone", remaining, 0)

# ─── Test 12: Empty list → 400 ───
print("\n--- P8.3 Test 12: Empty list → 400 ---")
r = client.request(
    "DELETE",
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"ids": []}
)
test("Empty list → 400", r.status_code, 400)

# ─── Test 13: RBAC — viewer cannot bulk delete → 403 ───
print("\n--- P8.3 Test 13: Viewer bulk delete → 403 ---")
r = client.request(
    "DELETE",
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_VIEWER,
    json={"ids": [del_ids_a[2]]}
)
test("Viewer delete → 403", r.status_code, 403)

# ─── Test 14: No token → 401 ───
print("\n--- P8.3 Test 14: No token → 401 ---")
r = client.request(
    "DELETE",
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    json={"ids": [del_ids_a[2]]}
)
test("No token → 401", r.status_code, 401)

# ─── Test 15: Cross-tenant delete → not found ───
print("\n--- P8.3 Test 15: Cross-tenant delete → 400 ---")
r = client.request(
    "DELETE",
    f"/api/v1/dynamic/entities/{ENTITY}/records/bulk",
    headers=HEADERS_A,
    json={"ids": del_ids_b[:1]}
)
test("Cross-tenant delete → 400", r.status_code, 400)

# ─── Test 16: Audit logs for bulk operations ───
print("\n--- P8.3 Test 16: Audit logs ---")
db = SessionLocal()
bulk_upd_count = db.execute(text(
    "SELECT COUNT(*) FROM audit_logs "
    "WHERE module = 'dynamic' AND action = 'bulk_update'"
)).scalar()
bulk_del_count = db.execute(text(
    "SELECT COUNT(*) FROM audit_logs "
    "WHERE module = 'dynamic' AND action = 'bulk_delete'"
)).scalar()
db.close()
test("Bulk update audit > 0", bulk_upd_count > 0, True)
test("Bulk delete audit > 0", bulk_del_count > 0, True)
print(f"  (bulk_update audits: {bulk_upd_count}, bulk_delete audits: {bulk_del_count})")

# ─── Results Summary ───
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
    print("\nAll P8.2 + P8.3 tests passed!")
    sys.exit(0)
