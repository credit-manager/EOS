"""
P9 Relationship Tests
Tests relationship CRUD, nested reads, referential validation, tenant isolation.
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

REL_CODE = f"rel_{uuid.uuid4().hex[:8]}"


def start_server():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env
    )
    time.sleep(4)
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


def test_contains(name, actual, expected_sub):
    ok = expected_sub in str(actual)
    results.append((name, ok))
    status = "PASS" if ok else "FAIL"
    print(f"  {status} - {name}: contains '{expected_sub}' in '{actual}'")
    return ok


print("\n" + "=" * 60)
print("P9 RELATIONSHIP TESTS")
print("=" * 60)

server = start_server()
client = httpx.Client(base_url=BASE, timeout=60)

# Clean old relationships
from database import SessionLocal
from sqlalchemy import text
db_clean = SessionLocal()
db_clean.execute(text("DELETE FROM dbp_relationships"))
db_clean.commit()
db_clean.close()
print("  Cleaned old relationships")

# ─── Setup: create test data ───
print("\n--- Setup: Create test records ---")
rec_ids = []
for i in range(3):
    code = f"REL-{uuid.uuid4().hex[:6]}"
    r = client.post(
        f"/api/v1/dynamic/entities/{ENTITY}/records",
        headers=HEADERS_A,
        json={"code": code, "name": f"RelTest{i}", "price": 100 + i}
    )
    if r.status_code == 200:
        rec_ids.append(r.json().get("id"))
print(f"  Created {len(rec_ids)} records")

# ──────────────────────────────────────────────
# Test 1: Create relationship
# ──────────────────────────────────────────────
print("\n--- Test 1: Create relationship ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships",
    headers=HEADERS_A,
    json={
        "code": REL_CODE,
        "target_entity_code": ENTITY,
        "relationship_type": "one_to_many",
        "source_column": "code",
        "target_column": "code",
        "lookup_field": "name",
        "is_required": False,
        "tenant_scope": True,
    }
)
data = r.json()
test("Create rel status 200", r.status_code, 200)
test("Has relationship id", "id" in data.get("relationship", {}), True)
test("Rel code matches", data.get("relationship", {}).get("code"), REL_CODE)

# ──────────────────────────────────────────────
# Test 2: List relationships
# ──────────────────────────────────────────────
print("\n--- Test 2: List relationships ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships",
    headers=HEADERS_A,
)
data = r.json()
test("List status 200", r.status_code, 200)
test("Has data", "data" in data, True)
test("Count >= 1", data.get("count", 0) >= 1, True)

# ──────────────────────────────────────────────
# Test 3: Get single relationship
# ──────────────────────────────────────────────
print("\n--- Test 3: Get single relationship ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships/{REL_CODE}",
    headers=HEADERS_A,
)
data = r.json()
test("Get rel status 200", r.status_code, 200)
test("Rel code correct", data.get("data", {}).get("code"), REL_CODE)
test("Target entity", data.get("data", {}).get("target_entity_code"), ENTITY)

# ──────────────────────────────────────────────
# Test 4: Create duplicate → 400
# ──────────────────────────────────────────────
print("\n--- Test 4: Duplicate relationship → 400 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships",
    headers=HEADERS_A,
    json={
        "code": REL_CODE,
        "target_entity_code": ENTITY,
        "relationship_type": "one_to_many",
        "source_column": "code",
    }
)
test("Duplicate rel → 400", r.status_code, 400)

# ──────────────────────────────────────────────
# Test 5: Missing required field → 422/400
# ──────────────────────────────────────────────
print("\n--- Test 5: Missing required field → 400 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships",
    headers=HEADERS_A,
    json={"code": "test_missing"}
)
test("Missing field → 400", r.status_code, 400)

# ──────────────────────────────────────────────
# Test 6: Invalid relationship type → 400
# ──────────────────────────────────────────────
print("\n--- Test 6: Invalid type → 400 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships",
    headers=HEADERS_A,
    json={
        "code": "bad_type",
        "target_entity_code": ENTITY,
        "relationship_type": "INVALID",
        "source_column": "code",
    }
)
test("Invalid type → 400", r.status_code, 400)

# ──────────────────────────────────────────────
# Test 7: Non-existent entity → 404
# ──────────────────────────────────────────────
print("\n--- Test 7: Non-existent entity → 404 ---")
r = client.post(
    f"/api/v1/dynamic/entities/nonexistent_entity/relationships",
    headers=HEADERS_A,
    json={
        "code": "test_404",
        "target_entity_code": ENTITY,
        "relationship_type": "one_to_many",
        "source_column": "code",
    }
)
test("Non-existent entity → 404", r.status_code, 404)

# ──────────────────────────────────────────────
# Test 8: RBAC — viewer cannot create
# ──────────────────────────────────────────────
print("\n--- Test 8: Viewer create → 403 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships",
    headers=HEADERS_VIEWER,
    json={
        "code": "viewer_test",
        "target_entity_code": ENTITY,
        "relationship_type": "one_to_many",
        "source_column": "code",
    }
)
test("Viewer create → 403", r.status_code, 403)

# ──────────────────────────────────────────────
# Test 9: Viewer CAN list (read)
# ──────────────────────────────────────────────
print("\n--- Test 9: Viewer list → 200 ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships",
    headers=HEADERS_VIEWER,
)
test("Viewer list → 200", r.status_code, 200)

# ──────────────────────────────────────────────
# Test 10: No token → 401
# ──────────────────────────────────────────────
print("\n--- Test 10: No token → 401 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships",
    json={
        "code": "no_token",
        "target_entity_code": ENTITY,
        "relationship_type": "one_to_many",
        "source_column": "code",
    }
)
test("No token → 401", r.status_code, 401)

# ──────────────────────────────────────────────
# Test 11: Nested read (depth=0 — flat)
# ──────────────────────────────────────────────
print("\n--- Test 11: Nested read depth=0 ---")
if rec_ids:
    r = client.get(
        f"/api/v1/dynamic/entities/{ENTITY}/records/{rec_ids[0]}/nested",
        headers=HEADERS_A,
        params={"depth": 0}
    )
    data = r.json()
    test("Nested depth=0 status 200", r.status_code, 200)
    test("Has data", "data" in data, True)

# ──────────────────────────────────────────────
# Test 12: Nested read (depth=1 — with relationships)
# ──────────────────────────────────────────────
print("\n--- Test 12: Nested read depth=1 ---")
if rec_ids:
    r = client.get(
        f"/api/v1/dynamic/entities/{ENTITY}/records/{rec_ids[0]}/nested",
        headers=HEADERS_A,
        params={"depth": 1}
    )
    data = r.json()
    test("Nested depth=1 status 200", r.status_code, 200)
    record = data.get("data", {})
    test("Has relationship key", REL_CODE in record, True)

# ──────────────────────────────────────────────
# Test 13: Nested read — non-existent record → 404
# ──────────────────────────────────────────────
print("\n--- Test 13: Nested non-existent → 404 ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/records/nonexistent-id/nested",
    headers=HEADERS_A,
    params={"depth": 1}
)
test("Nested non-existent → 404", r.status_code, 404)

# ──────────────────────────────────────────────
# Test 14: Cross-tenant nested — tenant B can't see A's data
# ──────────────────────────────────────────────
print("\n--- Test 14: Cross-tenant nested isolation ---")
if rec_ids:
    r = client.get(
        f"/api/v1/dynamic/entities/{ENTITY}/records/{rec_ids[0]}/nested",
        headers=HEADERS_B,
        params={"depth": 1}
    )
    test("Cross-tenant nested → 404", r.status_code, 404)

# ──────────────────────────────────────────────
# Test 15: Delete relationship
# ──────────────────────────────────────────────
print("\n--- Test 15: Delete relationship ---")
r = client.delete(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships/{REL_CODE}",
    headers=HEADERS_A,
)
test("Delete rel status 200", r.status_code, 200)

# Verify deleted
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships/{REL_CODE}",
    headers=HEADERS_A,
)
test("Deleted rel → 404", r.status_code, 404)

# ──────────────────────────────────────────────
# Test 16: Delete non-existent → 404
# ──────────────────────────────────────────────
print("\n--- Test 16: Delete non-existent → 404 ---")
r = client.delete(
    f"/api/v1/dynamic/entities/{ENTITY}/relationships/nonexistent",
    headers=HEADERS_A,
)
test("Delete non-existent → 404", r.status_code, 404)

# ──────────────────────────────────────────────
# Test 17: Invalid entity code format → 422
# ──────────────────────────────────────────────
print("\n--- Test 17: Invalid entity code → 404 ---")
r = client.get(
    f"/api/v1/dynamic/entities/INVALID CODE/relationships",
    headers=HEADERS_A,
)
test("Invalid entity code → 404", r.status_code, 404)

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
    print("\nAll P9 tests passed!")
    sys.exit(0)
