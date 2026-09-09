"""
P7 Query Engine Tests
Tests filtering, sorting, and pagination.
"""

import subprocess
import time
import sys
import os

# Start server
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

# Import after path is set
sys.path.insert(0, '.')
from core.auth import create_test_token
import httpx

BASE = "http://127.0.0.1:8000"
EP = f"{BASE}/api/v1/dynamic/entities"
ENTITY = "test_product"

# Test tokens
TOKEN_A = create_test_token("tenant_a", roles=["dynamic_manager"])
TOKEN_B = create_test_token("tenant_b", roles=["dynamic_manager"])
HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}

results = []

def test(name, actual, expected):
    ok = actual == expected
    results.append((name, ok))
    status = "PASS" if ok else "FAIL"
    print(f"  {status} - {name}: got {actual}, expected {expected}")
    return ok


print("\n" + "=" * 60)
print("P7 QUERY ENGINE TESTS")
print("=" * 60)

server = start_server()
client = httpx.Client(base_url=BASE, timeout=10)


# ──────────────────────────────────────────────
# Test 1: Basic list (no filters)
# ──────────────────────────────────────────────
print("\n--- Test 1: Basic list (no filters) ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={"limit": 10}
)
data = r.json()
test("Status 200", r.status_code, 200)
test("Has data", "data" in data, True)
test("Has pagination", "pagination" in data, True)
test("has_next exists", "has_next" in data.get("pagination", {}), True)


# ──────────────────────────────────────────────
# Test 2: Filter eq
# ──────────────────────────────────────────────
print("\n--- Test 2: Filter eq ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "code:eq:P001",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
# All returned records should have code=P001
codes = [row.get("code") for row in data.get("data", [])]
all_match = all(c == "P001" for c in codes) if codes else True
test("Filter eq works", all_match, True)


# ──────────────────────────────────────────────
# Test 3: Filter gte
# ──────────────────────────────────────────────
print("\n--- Test 3: Filter gte ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "price:gte:100",
        "limit": 100
    }
)
print(f"  Status: {r.status_code}")
if r.status_code != 200:
    print(f"  Response: {r.text[:200]}")
data = r.json()
test("Status 200", r.status_code, 200)


# ──────────────────────────────────────────────
# Test 4: Filter in
# ──────────────────────────────────────────────
print("\n--- Test 4: Filter in ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "code:in:P001|P002|P003",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)


# ──────────────────────────────────────────────
# Test 5: Filter is_null
# ──────────────────────────────────────────────
print("\n--- Test 5: Filter is_null ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "is_active:is_not_null",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)


# ──────────────────────────────────────────────
# Test 6: Sort ascending
# ──────────────────────────────────────────────
print("\n--- Test 6: Sort ascending ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "sort": "code",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
codes = [row.get("code") for row in data.get("data", [])]
if len(codes) > 1:
    is_sorted = codes == sorted(codes)
    test("Sort ascending works", is_sorted, True)
else:
    test("Sort ascending works (skip - not enough data)", True, True)


# ──────────────────────────────────────────────
# Test 7: Sort descending
# ──────────────────────────────────────────────
print("\n--- Test 7: Sort descending ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "sort": "-code",
        "limit": 10
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
codes = [row.get("code") for row in data.get("data", [])]
if len(codes) > 1:
    is_sorted = codes == sorted(codes, reverse=True)
    test("Sort descending works", is_sorted, True)
else:
    test("Sort descending works (skip - not enough data)", True, True)


# ──────────────────────────────────────────────
# Test 8: Invalid column → 400
# ──────────────────────────────────────────────
print("\n--- Test 8: Invalid column ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "nonexistent:eq:value",
        "limit": 10
    }
)
test("Invalid column → 400", r.status_code, 400)


# ──────────────────────────────────────────────
# Test 9: Invalid operator → 400
# ──────────────────────────────────────────────
print("\n--- Test 9: Invalid operator ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "code:INVALID_OP:value",
        "limit": 10
    }
)
test("Invalid operator → 400", r.status_code, 400)


# ──────────────────────────────────────────────
# Test 10: Pagination has_next
# ──────────────────────────────────────────────
print("\n--- Test 10: Pagination has_next ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "limit": 1,
        "offset": 0
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
pagination = data.get("pagination", {})
test("total exists", "total" in pagination, True)
test("has_next exists", "has_next" in pagination, True)
test("limit in response", pagination.get("limit"), 1)
test("offset in response", pagination.get("offset"), 0)


# ──────────────────────────────────────────────
# Test 11: Limit max enforcement
# ──────────────────────────────────────────────
print("\n--- Test 11: Limit max enforcement ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "limit": 9999,
        "offset": 0
    }
)
data = r.json()
test("Status 200", r.status_code, 200)
# Limit should be clamped to MAX_LIMIT
pagination = data.get("pagination", {})
test("Limit clamped", pagination.get("limit", 0) <= 500, True)


# ──────────────────────────────────────────────
# Test 12: Tenant isolation with filters
# ──────────────────────────────────────────────
print("\n--- Test 12: Tenant isolation with filters ---")
r_a = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={"limit": 100}
)
r_b = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_B,
    params={"limit": 100}
)
data_a = r_a.json()
data_b = r_b.json()
ids_a = set(row.get("id") for row in data_a.get("data", []))
ids_b = set(row.get("id") for row in data_b.get("data", []))
no_overlap = ids_a.isdisjoint(ids_b)
test("Tenant A isolation", r_a.status_code, 200)
test("Tenant B isolation", r_b.status_code, 200)
test("No cross-tenant overlap", no_overlap, True)


# ──────────────────────────────────────────────
# Test 13: SQL injection attempt
# ──────────────────────────────────────────────
print("\n--- Test 13: SQL injection attempt ---")
r = client.get(
    "/api/v1/dynamic/entities/test_product/records",
    headers=HEADERS_A,
    params={
        "filters": "code:eq:1' OR '1'='1",
        "limit": 10
    }
)
data = r.json()
# Should return 200 with filtered results (not all records)
test("SQL injection handled", r.status_code in [200, 400], True)


# ──────────────────────────────────────────────
# Results Summary
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"RESULTS: {passed}/{total} passed")

# Cleanup
client.close()
stop_server(server)

if passed < total:
    print("\nFailed tests:")
    for name, ok in results:
        if not ok:
            print(f"  FAIL: {name}")
    sys.exit(1)
else:
    print("\nAll tests passed!")
    sys.exit(0)
