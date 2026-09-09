"""
P8.4 Import Tests
Tests CSV/Excel template download and record import.
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
TOKEN_VIEWER = create_test_token("tenant_a", roles=["dynamic_viewer"])
HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
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


def make_csv(headers, rows):
    """Create CSV content in memory."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


results = []


def test(name, actual, expected):
    ok = actual == expected
    results.append((name, ok))
    status = "PASS" if ok else "FAIL"
    print(f"  {status} - {name}: got {actual}, expected {expected}")
    return ok


print("\n" + "=" * 60)
print("P8.4 IMPORT TESTS")
print("=" * 60)

server = start_server()
client = httpx.Client(base_url=BASE, timeout=30)

# ──────────────────────────────────────────────
# Test 1: Download CSV template
# ──────────────────────────────────────────────
print("\n--- Test 1: Download CSV template ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/import/template",
    headers=HEADERS_A,
    params={"format": "csv"}
)
test("CSV template status 200", r.status_code, 200)
test("CSV content-type", "text/csv" in r.headers.get("content-type", ""), True)
csv_content = r.text
test("CSV has headers", "code" in csv_content, True)
test("CSV has example row", "EXAMPLE-001" in csv_content, True)
print(f"  Template preview: {csv_content[:100]}...")

# ──────────────────────────────────────────────
# Test 2: Download XLSX template
# ──────────────────────────────────────────────
print("\n--- Test 2: Download XLSX template ---")
r = client.get(
    f"/api/v1/dynamic/entities/{ENTITY}/import/template",
    headers=HEADERS_A,
    params={"format": "xlsx"}
)
test("XLSX template status 200", r.status_code, 200)
test("XLSX content-type",
     "spreadsheetml" in r.headers.get("content-type", ""), True)

# ──────────────────────────────────────────────
# Test 3: Import CSV — atomic mode, 3 records
# ──────────────────────────────────────────────
print("\n--- Test 3: Import CSV (atomic, 3 records) ---")
code1 = f"IMP-{uuid.uuid4().hex[:6]}"
code2 = f"IMP-{uuid.uuid4().hex[:6]}"
code3 = f"IMP-{uuid.uuid4().hex[:6]}"
csv_data = make_csv(
    ["code", "name", "price", "tenant_id"],
    [
        [code1, "Import A", "100", "tenant_a"],
        [code2, "Import B", "200", "tenant_a"],
        [code3, "Import C", "300", "tenant_a"],
    ]
)
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/import",
    headers=HEADERS_A,
    params={"mode": "atomic"},
    files={"file": ("test_import.csv", csv_data, "text/csv")}
)
data = r.json()
test("Import status 200", r.status_code, 200)
test("Imported = 3", data.get("imported"), 3)
test("Errors = 0", data.get("errors"), 0)
test("Tenant = tenant_a", data.get("effective_tenant"), "tenant_a")

# ──────────────────────────────────────────────
# Test 4: Import CSV — with validation errors (partial mode)
# ──────────────────────────────────────────────
print("\n--- Test 4: Import CSV (partial mode, some errors) ---")
good_code = f"IMP-{uuid.uuid4().hex[:6]}"
csv_data = make_csv(
    ["code", "name", "price", "tenant_id"],
    [
        [good_code, "Good Record", "50", "tenant_a"],
        ["", "Missing Code", "60", "tenant_a"],  # Missing required
    ]
)
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/import",
    headers=HEADERS_A,
    params={"mode": "partial"},
    files={"file": ("test_import.csv", csv_data, "text/csv")}
)
data = r.json()
test("Partial import status 200", r.status_code, 200)
test("Imported >= 1", data.get("imported", 0) >= 1, True)
test("Has errors", data.get("errors", 0) > 0, True)

# ──────────────────────────────────────────────
# Test 5: Import CSV — atomic mode with errors → 400
# ──────────────────────────────────────────────
print("\n--- Test 5: Import CSV (atomic mode, errors → 400) ---")
csv_data = make_csv(
    ["code", "name", "price", "tenant_id"],
    [
        ["", "No Code", "50", "tenant_a"],  # Missing required
    ]
)
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/import",
    headers=HEADERS_A,
    params={"mode": "atomic"},
    files={"file": ("test_import.csv", csv_data, "text/csv")}
)
test("Atomic error → 400", r.status_code, 400)

# ──────────────────────────────────────────────
# Test 6: Import empty file → 400
# ──────────────────────────────────────────────
print("\n--- Test 6: Import empty file → 400 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/import",
    headers=HEADERS_A,
    params={"mode": "atomic"},
    files={"file": ("empty.csv", b"", "text/csv")}
)
test("Empty file → 400", r.status_code, 400)

# ──────────────────────────────────────────────
# Test 7: Import invalid file type → 400
# ──────────────────────────────────────────────
print("\n--- Test 7: Import invalid file type → 400 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/import",
    headers=HEADERS_A,
    params={"mode": "atomic"},
    files={"file": ("test.txt", b"hello", "text/plain")}
)
test("Invalid file type → 400", r.status_code, 400)

# ──────────────────────────────────────────────
# Test 8: RBAC — viewer cannot import → 403
# ──────────────────────────────────────────────
print("\n--- Test 8: Viewer import → 403 ---")
csv_data = make_csv(
    ["code", "name", "price"],
    [["X", "X", "10"]]
)
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/import",
    headers=HEADERS_VIEWER,
    params={"mode": "atomic"},
    files={"file": ("test.csv", csv_data, "text/csv")}
)
test("Viewer import → 403", r.status_code, 403)

# ──────────────────────────────────────────────
# Test 9: No token → 401
# ──────────────────────────────────────────────
print("\n--- Test 9: No token → 401 ---")
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/import",
    params={"mode": "atomic"},
    files={"file": ("test.csv", csv_data, "text/csv")}
)
test("No token → 401", r.status_code, 401)

# ──────────────────────────────────────────────
# Test 10: Tenant spoofing in CSV ignored
# ──────────────────────────────────────────────
print("\n--- Test 10: Tenant spoofing in CSV ignored ---")
spoof_code = f"IMP-SPOOF-{uuid.uuid4().hex[:6]}"
csv_data = make_csv(
    ["code", "name", "price", "tenant_id"],
    [[spoof_code, "Spoof", "99", "tenant_b"]]
)
r = client.post(
    f"/api/v1/dynamic/entities/{ENTITY}/import",
    headers=HEADERS_A,
    params={"mode": "atomic"},
    files={"file": ("test.csv", csv_data, "text/csv")}
)
data = r.json()
test("Spoof import → 200", r.status_code, 200)
# Verify the record is under tenant_a
from database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
row = db.execute(text(
    "SELECT tenant_id FROM test_products WHERE code = :code"
), {"code": spoof_code}).fetchone()
db.close()
test("Spoofed tenant = tenant_a", row[0] if row else None, "tenant_a")

# ──────────────────────────────────────────────
# Test 11: Import audit logs
# ──────────────────────────────────────────────
print("\n--- Test 11: Import audit logs ---")
db = SessionLocal()
import_count = db.execute(text(
    "SELECT COUNT(*) FROM audit_logs "
    "WHERE module = 'dynamic' AND action = 'import'"
)).scalar()
db.close()
test("Import audit > 0", import_count > 0, True)
print(f"  (import audit entries: {import_count})")

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
    print("\nAll P8.4 tests passed!")
    sys.exit(0)
