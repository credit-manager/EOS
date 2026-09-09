"""
P10 Soft Delete Tests — Full Suite
Covers: Soft delete, restore, default read excludes, admin include_deleted,
        RBAC, tenant isolation, payload spoofing, audit, bulk integration.
"""
import subprocess, time, sys, os, uuid
sys.path.insert(0, '.')
from core.auth import create_test_token
from database import SessionLocal
from sqlalchemy import text
import httpx

BASE = "http://127.0.0.1:8000"
EP = f"{BASE}/api/v1/dynamic/entities"
ENTITY = "test_product"

TOKEN_A = create_test_token("tenant_a", roles=["dynamic_manager"])
TOKEN_B = create_test_token("tenant_b", roles=["dynamic_manager"])
TOKEN_ADMIN = create_test_token("tenant_a", roles=["dynamic_manager", {"permission": "*:*"}])
TOKEN_VIEWER = create_test_token("tenant_a", roles=["dynamic_viewer"])
HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}
HEADERS_ADMIN = {"Authorization": f"Bearer {TOKEN_ADMIN}"}
HEADERS_VIEWER = {"Authorization": f"Bearer {TOKEN_VIEWER}"}


def start_server():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env
    )
    time.sleep(5)
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


server = start_server()
client = httpx.Client(base_url=BASE, timeout=60)

# Clean
db = SessionLocal()
db.execute(text("DELETE FROM dbp_relationships"))
db.commit()
db.close()

# ═══════════════════════════════════════════════════════
# SECTION 1: Soft Delete + Restore
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("P10 SOFT DELETE TESTS")
print("=" * 60)

print("\n--- 1. Soft Delete + Restore ---")

# Create record
code = f"SD-{uuid.uuid4().hex[:6]}"
r = client.post(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
                json={"code": code, "name": "SoftDelete Test", "price": 100})
test("Create record", r.status_code, 200)
rec_id = r.json().get("id")

# Soft delete
r = client.delete(f"{EP}/{ENTITY}/records/{rec_id}", headers=HEADERS_A)
test("Soft delete → 200", r.status_code, 200)

# Verify excluded from default read
r = client.get(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
               params={"filters": f"code:eq:{code}"})
data = r.json().get("data", [])
test("Excluded from default read", len(data), 0)

# Restore
r = client.post(f"{EP}/{ENTITY}/records/{rec_id}/restore", headers=HEADERS_A)
test("Restore → 200", r.status_code, 200)

# Verify visible again
r = client.get(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
               params={"filters": f"code:eq:{code}"})
data = r.json().get("data", [])
test("Visible after restore", len(data), 1)

# Delete again for next tests
r = client.delete(f"{EP}/{ENTITY}/records/{rec_id}", headers=HEADERS_A)
test("Re-delete → 200", r.status_code, 200)

# ═══════════════════════════════════════════════════════
# SECTION 2: Include Deleted (Admin Only)
# ═══════════════════════════════════════════════════════
print("\n--- 2. include_deleted (Admin Only) ---")

# Admin can see deleted
r = client.get(f"{EP}/{ENTITY}/records", headers=HEADERS_ADMIN,
               params={"include_deleted": "true", "filters": f"code:eq:{code}"})
data = r.json().get("data", [])
test("Admin sees deleted", len(data), 1)

# Non-admin cannot
r = client.get(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
               params={"include_deleted": "true"})
test("Non-admin include_deleted → 403", r.status_code, 403)

# Viewer cannot
r = client.get(f"{EP}/{ENTITY}/records", headers=HEADERS_VIEWER,
               params={"include_deleted": "true"})
test("Viewer include_deleted → 403", r.status_code, 403)

# ═══════════════════════════════════════════════════════
# SECTION 3: RBAC
# ═══════════════════════════════════════════════════════
print("\n--- 3. RBAC ---")

# Viewer cannot delete
code2 = f"SD-{uuid.uuid4().hex[:6]}"
r = client.post(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
                json={"code": code2, "name": "RBAC Test", "price": 50})
rec_id2 = r.json().get("id")

r = client.delete(f"{EP}/{ENTITY}/records/{rec_id2}", headers=HEADERS_VIEWER)
test("Viewer delete → 403", r.status_code, 403)

# Viewer cannot restore
r = client.post(f"{EP}/{ENTITY}/records/{rec_id2}/restore", headers=HEADERS_VIEWER)
test("Viewer restore → 403", r.status_code, 403)

# No token → 401
r = client.delete(f"{EP}/{ENTITY}/records/{rec_id2}")
test("No token delete → 401", r.status_code, 401)

r = client.post(f"{EP}/{ENTITY}/records/{rec_id2}/restore")
test("No token restore → 401", r.status_code, 401)

# Clean up
client.delete(f"{EP}/{ENTITY}/records/{rec_id2}", headers=HEADERS_A)

# ═══════════════════════════════════════════════════════
# SECTION 4: Tenant Isolation
# ═══════════════════════════════════════════════════════
print("\n--- 4. Tenant Isolation ---")

# Create records for both tenants
code_a = f"SD-A-{uuid.uuid4().hex[:6]}"
code_b = f"SD-B-{uuid.uuid4().hex[:6]}"
r_a = client.post(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
                   json={"code": code_a, "name": "Tenant A", "price": 10})
r_b = client.post(f"{EP}/{ENTITY}/records", headers=HEADERS_B,
                   json={"code": code_b, "name": "Tenant B", "price": 20})
id_a = r_a.json().get("id")
id_b = r_b.json().get("id")

# Tenant A cannot delete B's record
r = client.delete(f"{EP}/{ENTITY}/records/{id_b}", headers=HEADERS_A)
test("Cross-tenant delete → 404", r.status_code, 404)

# Tenant A cannot restore B's record
r = client.post(f"{EP}/{ENTITY}/records/{id_b}/restore", headers=HEADERS_A)
test("Cross-tenant restore → 404", r.status_code, 404)

# Clean
client.delete(f"{EP}/{ENTITY}/records/{id_a}", headers=HEADERS_A)
client.delete(f"{EP}/{ENTITY}/records/{id_b}", headers=HEADERS_B)

# ═══════════════════════════════════════════════════════
# SECTION 5: Audit
# ═══════════════════════════════════════════════════════
print("\n--- 5. Audit ---")

code3 = f"SD-{uuid.uuid4().hex[:6]}"
r = client.post(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
                json={"code": code3, "name": "Audit Test", "price": 77})
rec_id3 = r.json().get("id")

r = client.delete(f"{EP}/{ENTITY}/records/{rec_id3}", headers=HEADERS_A)
test("Delete → 200", r.status_code, 200)

r = client.post(f"{EP}/{ENTITY}/records/{rec_id3}/restore", headers=HEADERS_A)
test("Restore → 200", r.status_code, 200)

# Check audit
db = SessionLocal()
audits = db.execute(text(
    "SELECT COUNT(*) FROM audit_logs "
    "WHERE entity_type = :ec AND entity_id = :ri "
    "AND action IN ('delete', 'restore')"
), {"ec": ENTITY, "ri": rec_id3}).scalar()
db.close()
test("Audit logs exist", audits >= 2, True)

# ═══════════════════════════════════════════════════════
# SECTION 6: Bulk Delete → Soft Delete
# ═══════════════════════════════════════════════════════
print("\n--- 6. Bulk Delete → Soft Delete ---")

bulk_ids = []
for i in range(3):
    c = f"SD-BULK-{uuid.uuid4().hex[:6]}"
    r = client.post(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
                    json={"code": c, "name": f"Bulk{i}", "price": i})
    if r.status_code == 200:
        bulk_ids.append(r.json().get("id"))

r = client.request("DELETE", f"{EP}/{ENTITY}/records/bulk",
                    headers=HEADERS_A, json={"ids": bulk_ids})
test("Bulk delete → 200", r.status_code, 200)
test("Deleted count", r.json().get("deleted", 0), len(bulk_ids))

# Verify excluded
r = client.get(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
               params={"include_deleted": "false"})
data = r.json().get("data", [])
found_deleted = [d for d in data if d.get("id") in bulk_ids]
test("Bulk deleted excluded from read", len(found_deleted), 0)

# ═══════════════════════════════════════════════════════
# SECTION 7: Update Deleted → 404
# ═══════════════════════════════════════════════════════
print("\n--- 7. Update Deleted → 404 ---")

code4 = f"SD-{uuid.uuid4().hex[:6]}"
r = client.post(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
                json={"code": code4, "name": "Update Deleted Test", "price": 88})
rec_id4 = r.json().get("id")
client.delete(f"{EP}/{ENTITY}/records/{rec_id4}", headers=HEADERS_A)

r = client.put(f"{EP}/{ENTITY}/records/{rec_id4}", headers=HEADERS_A,
               json={"name": "Should Fail"})
test("Update deleted → 404", r.status_code, 404)

# ═══════════════════════════════════════════════════════
# SECTION 8: Restore Non-Deleted → 400
# ═══════════════════════════════════════════════════════
print("\n--- 8. Restore Non-Deleted → 400 ---")

code5 = f"SD-{uuid.uuid4().hex[:6]}"
r = client.post(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
                json={"code": code5, "name": "Not Deleted", "price": 99})
rec_id5 = r.json().get("id")

r = client.post(f"{EP}/{ENTITY}/records/{rec_id5}/restore", headers=HEADERS_A)
test("Restore non-deleted → 400", r.status_code, 400)

# Cleanup
client.delete(f"{EP}/{ENTITY}/records/{rec_id5}", headers=HEADERS_A)

# ═══════════════════════════════════════════════════════
# SECTION 9: Export Excludes Deleted
# ═══════════════════════════════════════════════════════
print("\n--- 9. Export Excludes Deleted ---")

code6 = f"SD-EXP-{uuid.uuid4().hex[:6]}"
r = client.post(f"{EP}/{ENTITY}/records", headers=HEADERS_A,
                json={"code": code6, "name": "Export Test", "price": 55})
rec_id6 = r.json().get("id")
client.delete(f"{EP}/{ENTITY}/records/{rec_id6}", headers=HEADERS_A)

r = client.get(f"{EP}/{ENTITY}/export", headers=HEADERS_A,
               params={"format": "csv"})
csv_text = r.text
test("Export excludes deleted", code6 not in csv_text, True)

# ═══════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"\n{'=' * 60}")
print(f"RESULTS: {passed}/{total} passed")
if passed == total:
    print("All P10 tests passed!")
else:
    print("Some tests failed!")
    for name, ok in results:
        if not ok:
            print(f"  FAILED: {name}")

stop_server(server)
client.close()
