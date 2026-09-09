"""
P8.5 Export Tests
Tests CSV/Excel export with tenant scope and P7 filters.
"""

import subprocess
import time
import sys
import os
import uuid
import csv
import io

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


print("\n" + "=" * 60)
print("P8.5 EXPORT TESTS")
print("=" * 60)

server = start_server()
client = httpx.Client(base_url=BASE, timeout=30)

# ─── Setup: create test data ───
print("\n--- Setup: Create export test data ---")
exp_ids_a = []
exp_ids_b = []
for i in range(3):
    code = f"EXP-A-{uuid.uuid4().hex[:6]}"
    r = client.post(
        f"/api/v1/dynamic/entities/{ENTITY}/records",
        headers=HEADERS_A,
        json={"code": code, "name": f"Export A{i}", "price": 100 + i, "tenant_id": "tenant_a"}
    )
    if r.status_code == 200:
        exp_ids_a.append(r.json().get("id"))

for i in range(2):
    code = f"EXP-B-{uuid.uuid4().hex[:6]}"
    r = client.post(
        f"/api/v1/dynamic/entities/{ENTITY}/records",
        headers=HEADERS_B,
        json={"code": code, "name": f"Export B{i}", "price": 200 + i, "tenant_id": "tenant_b"}
    )
    if r.status_code == 200:
        exp_ids_b.append(r.json().get("id"))
print(f"  Created {len(exp_ids_a)} A records, {len(exp_ids_b)} B records")

# ──────────────────────────────────────────────
# Test 1: Export CSV — basic
# ──────────────────────────────────────────────
print("\n--- Test 1: Export CSV basic ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    headers=HEADERS_A,
    params={"format": "csv", "limit": 100}
)
test("CSV export status 200", r.status_code, 200)
test("CSV content-type", "text/csv" in r.headers.get("content-type", ""), True)
test("Has X-Export-Total header", "x-export-total" in r.headers, True)

# Parse CSV content
csv_text = r.text
reader = csv.DictReader(io.StringIO(csv_text))
exported_rows = list(reader)
test("Has rows", len(exported_rows) > 0, True)

# Verify tenant isolation — all rows should be tenant_a
for row in exported_rows:
    if "tenant_id" in row:
        test("Tenant isolation in export", row.get("tenant_id"), "tenant_a")
        break

# ──────────────────────────────────────────────
# Test 2: Export CSV — tenant B sees only B
# ──────────────────────────────────────────────
print("\n--- Test 2: Export CSV tenant B ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    headers=HEADERS_B,
    params={"format": "csv", "limit": 100}
)
csv_text = r.text
reader = csv.DictReader(io.StringIO(csv_text))
b_rows = list(reader)
test("Tenant B export has rows", len(b_rows) > 0, True)

# ──────────────────────────────────────────────
# Test 3: Cross-tenant isolation — A can't see B's data
# ──────────────────────────────────────────────
print("\n--- Test 3: Cross-tenant isolation ---")
r_a = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    headers=HEADERS_A,
    params={"format": "csv", "limit": 100}
)
r_b = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    headers=HEADERS_B,
    params={"format": "csv", "limit": 100}
)
csv_a = csv.DictReader(io.StringIO(r_a.text))
csv_b = csv.DictReader(io.StringIO(r_b.text))
ids_a = set(row.get("id", "") for row in csv_a)
ids_b = set(row.get("id", "") for row in csv_b)
test("No cross-tenant overlap in export", ids_a.isdisjoint(ids_b), True)

# ──────────────────────────────────────────────
# Test 4: Export XLSX
# ──────────────────────────────────────────────
print("\n--- Test 4: Export XLSX ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    headers=HEADERS_A,
    params={"format": "xlsx", "limit": 100}
)
test("XLSX export status 200", r.status_code, 200)
test("XLSX content-type",
     "spreadsheetml" in r.headers.get("content-type", ""), True)

# ──────────────────────────────────────────────
# Test 5: Export with P7 filter
# ──────────────────────────────────────────────
print("\n--- Test 5: Export with filter ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    headers=HEADERS_A,
    params={"format": "csv", "filters": "price:gte:101", "limit": 100}
)
csv_text = r.text
reader = csv.DictReader(io.StringIO(csv_text))
filtered_rows = list(reader)
# All rows should have price >= 101
prices_ok = all(float(row.get("price", 0)) >= 101 for row in filtered_rows)
test("Filter applied in export", prices_ok, True)

# ──────────────────────────────────────────────
# Test 6: Export with sort
# ──────────────────────────────────────────────
print("\n--- Test 6: Export with sort ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    headers=HEADERS_A,
    params={"format": "csv", "sort": "price", "limit": 100}
)
csv_text = r.text
reader = csv.DictReader(io.StringIO(csv_text))
sorted_rows = list(reader)
if len(sorted_rows) > 1:
    prices = [float(row.get("price", 0)) for row in sorted_rows]
    test("Sort applied in export", prices == sorted(prices), True)
else:
    test("Sort applied in export (skip)", True, True)

# ──────────────────────────────────────────────
# Test 7: No token → 401
# ──────────────────────────────────────────────
print("\n--- Test 7: No token → 401 ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    params={"format": "csv", "limit": 10}
)
test("No token → 401", r.status_code, 401)

# ──────────────────────────────────────────────
# Test 8: RBAC — viewer can export (read permission)
# ──────────────────────────────────────────────
print("\n--- Test 8: Viewer export → 200 ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    headers=HEADERS_VIEWER,
    params={"format": "csv", "limit": 10}
)
test("Viewer export → 200", r.status_code, 200)

# ──────────────────────────────────────────────
# Test 9: tenant_id column not in export
# ──────────────────────────────────────────────
print("\n--- Test 9: tenant_id excluded from export ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/export",
    headers=HEADERS_A,
    params={"format": "csv", "limit": 10}
)
csv_text = r.text
reader = csv.DictReader(io.StringIO(csv_text))
headers_list = reader.fieldnames or []
test("tenant_id not in CSV headers", "tenant_id" not in headers_list, True)

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
    print("\nAll P8.5 tests passed!")
    sys.exit(0)
