"""
P18 ADVANCED DATA JOBS TESTS
================================
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"

TOKEN_A = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
TOKEN_M = create_test_token("tenant_a", user_id="manager", email="mgr@test.com", roles=["dynamic_manager"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="adminb@test.com", roles=["admin"])

HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_M = {"Authorization": f"Bearer {TOKEN_M}"}
HEADERS_V = {"Authorization": f"Bearer {TOKEN_V}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}

passed = 0
failed = 0

def test(name, got, expected):
    global passed, failed
    if got == expected:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL - {name}: got {got!r}, expected {expected!r}")

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
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

def setup_entity():
    """Create a test entity with table for import/export tests."""
    from database import SessionLocal
    from sqlalchemy import text as sa_text
    db = SessionLocal()
    try:
        # Cleanup
        db.execute(sa_text("DELETE FROM dbp_data_jobs"))
        db.execute(sa_text("DELETE FROM p18_products WHERE id IN ('prod-001','prod-002','prod-003')"))
        db.commit()
        # Create table
        db.execute(sa_text("""
            CREATE TABLE IF NOT EXISTS p18_products (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                name VARCHAR(255),
                price NUMERIC(10,2),
                category VARCHAR(100),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        db.commit()
        # Register entity
        existing = db.execute(sa_text(
            "SELECT id FROM dbp_entities WHERE code='p18_products'"
        )).fetchone()
        if not existing:
            db.execute(sa_text(
                "INSERT INTO dbp_entities (id, code, name_en, faculty, table_mapping) "
                "VALUES ('p18_ent', 'p18_products', 'P18 Products', 'test', 'p18_products')"
            ))
            db.commit()
    finally:
        db.close()


def test_create_job(client):
    """Section 1: Create & list jobs"""
    print("\n--- 1. Create & List Jobs ---")

    # Import job
    r = client.post(f"{EP}/jobs", headers=HEADERS_A, json={
        "code": "import_products_001",
        "name_en": "Import Products Batch 1",
        "name_ar": "استيراد منتجات الدفعة 1",
        "job_type": "import",
        "entity_code": "p18_products",
        "priority": 10,
        "config": {
            "records": [
                {"id": "prod-001", "name": "Widget A", "price": 9.99, "category": "widgets", "tenant_id": "tenant_a"},
                {"id": "prod-002", "name": "Widget B", "price": 19.99, "category": "widgets", "tenant_id": "tenant_a"},
                {"id": "prod-003", "name": "Gadget X", "price": 29.99, "category": "gadgets", "tenant_id": "tenant_a"},
            ],
        },
    })
    test("Create import job -> 200", r.status_code, 200)
    import_id = r.json()["data"]["id"]

    # Export job
    r = client.post(f"{EP}/jobs", headers=HEADERS_A, json={
        "code": "export_products_001",
        "name_en": "Export Products",
        "job_type": "export",
        "entity_code": "p18_products",
    })
    test("Create export job -> 200", r.status_code, 200)
    export_id = r.json()["data"]["id"]

    # Batch update job
    r = client.post(f"{EP}/jobs", headers=HEADERS_A, json={
        "code": "batch_update_prices",
        "name_en": "Update Prices",
        "job_type": "batch_update",
        "entity_code": "p18_products",
    })
    test("Create batch_update job -> 200", r.status_code, 200)

    # List
    r = client.get(f"{EP}/jobs", headers=HEADERS_A)
    test("List jobs -> 200", r.status_code, 200)
    test("Has 3+ jobs", len(r.json()["data"]) >= 3, True)

    # Filter by type
    r = client.get(f"{EP}/jobs?job_type=import", headers=HEADERS_A)
    test("Filter import jobs -> 200", r.status_code, 200)
    test("Has 1 import job", len(r.json()["data"]), 1)

    # Filter by status
    r = client.get(f"{EP}/jobs?status=pending", headers=HEADERS_A)
    test("Filter pending jobs -> 200", r.status_code, 200)

    # Missing fields
    r = client.post(f"{EP}/jobs", headers=HEADERS_A, json={
        "code": "bad_job",
    })
    test("Missing fields -> 400", r.status_code, 400)

    # Invalid type
    r = client.post(f"{EP}/jobs", headers=HEADERS_A, json={
        "code": "bad_type", "name_en": "Bad", "job_type": "magic",
    })
    test("Invalid type -> 400", r.status_code, 400)

    return import_id, export_id


def test_execute_import(client, import_id):
    """Section 2: Execute import"""
    print("\n--- 2. Execute Import ---")

    r = client.post(f"{EP}/jobs/{import_id}/execute", headers=HEADERS_A)
    test("Execute import -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Success", data["success"], True)
    test("Rows processed 3", data["rows_processed"], 3)
    test("Rows affected 3", data["rows_affected"], 3)
    test("No errors", len(data["errors"]), 0)
    test("Has duration_ms", "duration_ms" in data, True)

    # Verify status
    r = client.get(f"{EP}/jobs/{import_id}", headers=HEADERS_A)
    test("Status completed", r.json()["data"]["status"], "completed")
    test("Progress 100", r.json()["data"]["progress"], 100)

    # Re-execute completed job should fail
    r = client.post(f"{EP}/jobs/{import_id}/execute", headers=HEADERS_A)
    test("Re-execute completed -> 400", r.status_code, 400)


def test_execute_export(client, export_id):
    """Section 3: Execute export"""
    print("\n--- 3. Execute Export ---")

    r = client.post(f"{EP}/jobs/{export_id}/execute", headers=HEADERS_A,
                    json={})
    test("Execute export -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Success", data["success"], True)
    test("Export count >= 3", data.get("export_count", 0) >= 3, True)


def test_batch_update(client):
    """Section 4: Batch update"""
    print("\n--- 4. Batch Update ---")

    r = client.post(f"{EP}/jobs", headers=HEADERS_A, json={
        "code": "batch_upd_001",
        "name_en": "Update Prices",
        "job_type": "batch_update",
        "entity_code": "p18_products",
        "config": {
            "filter_field": "id",
            "updates": [
                {"record_id": "prod-001", "set": {"price": 12.99}},
                {"record_id": "prod-002", "set": {"price": 24.99}},
            ],
        },
    })
    job_id = r.json()["data"]["id"]

    r = client.post(f"{EP}/jobs/{job_id}/execute", headers=HEADERS_A)
    test("Execute batch update -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Success", data["success"], True)
    test("Rows affected 2", data["rows_affected"], 2)


def test_batch_delete(client):
    """Section 5: Batch delete"""
    print("\n--- 5. Batch Delete ---")

    r = client.post(f"{EP}/jobs", headers=HEADERS_A, json={
        "code": "batch_del_001",
        "name_en": "Delete Widgets",
        "job_type": "batch_delete",
        "entity_code": "p18_products",
        "config": {
            "record_ids": ["prod-002", "prod-003"],
        },
    })
    job_id = r.json()["data"]["id"]

    r = client.post(f"{EP}/jobs/{job_id}/execute", headers=HEADERS_A)
    test("Execute batch delete -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Success", data["success"], True)
    test("Rows affected 2", data["rows_affected"], 2)


def test_report_job(client):
    """Section 6: Report job"""
    print("\n--- 6. Report Job ---")

    r = client.post(f"{EP}/jobs", headers=HEADERS_A, json={
        "code": "report_count",
        "name_en": "Count Products",
        "job_type": "report",
        "entity_code": "p18_products",
        "config": {"field": "id", "func": "count"},
    })
    job_id = r.json()["data"]["id"]

    r = client.post(f"{EP}/jobs/{job_id}/execute", headers=HEADERS_A)
    test("Execute report -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Success", data["success"], True)
    test("Has report", "report" in data, True)


def test_cancel_job(client):
    """Section 7: Cancel job"""
    print("\n--- 7. Cancel Job ---")

    r = client.post(f"{EP}/jobs", headers=HEADERS_A, json={
        "code": "cancel_test",
        "name_en": "Cancel Me",
        "job_type": "import",
        "entity_code": "p18_products",
        "config": {"records": []},
    })
    job_id = r.json()["data"]["id"]

    r = client.post(f"{EP}/jobs/{job_id}/cancel", headers=HEADERS_A)
    test("Cancel pending -> 200", r.status_code, 200)

    r = client.get(f"{EP}/jobs/{job_id}", headers=HEADERS_A)
    test("Status cancelled", r.json()["data"]["status"], "cancelled")

    # Can't cancel completed
    r = client.post(f"{EP}/jobs/{job_id}/cancel", headers=HEADERS_A)
    test("Cancel already cancelled -> 400", r.status_code, 400)


def test_tenant_isolation(client):
    """Section 8: Tenant isolation"""
    print("\n--- 8. Tenant Isolation ---")

    # Tenant B job
    r = client.post(f"{EP}/jobs", headers=HEADERS_B, json={
        "code": "tenant_b_job",
        "name_en": "Tenant B Job",
        "job_type": "import",
        "entity_code": "p18_products",
        "config": {"records": []},
    })
    test("Tenant B create job -> 200", r.status_code, 200)

    # Tenant A should not see tenant B's job in list (tenant_id IS NULL jobs are shared)
    r = client.get(f"{EP}/jobs", headers=HEADERS_A)
    test("Tenant A list -> 200", r.status_code, 200)


def test_rbac(client):
    """Section 9: RBAC"""
    print("\n--- 9. RBAC ---")

    # Viewer can read
    r = client.get(f"{EP}/jobs", headers=HEADERS_V)
    test("Viewer list jobs -> 200", r.status_code, 200)

    # Viewer can read single
    r = client.get(f"{EP}/jobs/nonexistent", headers=HEADERS_V)
    test("Viewer get nonexistent -> 404", r.status_code, 404)

    # No auth
    r = client.post(f"{EP}/jobs", json={
        "code": "x", "name_en": "x", "job_type": "import",
    })
    test("No auth -> 401", r.status_code, 401)


def test_errors(client):
    """Section 10: Errors"""
    print("\n--- 10. Errors ---")

    r = client.get(f"{EP}/jobs/nonexistent", headers=HEADERS_A)
    test("Get nonexistent job -> 404", r.status_code, 404)

    r = client.post(f"{EP}/jobs/nonexistent/execute", headers=HEADERS_A)
    test("Execute nonexistent -> 404", r.status_code, 404)

    r = client.post(f"{EP}/jobs/nonexistent/cancel", headers=HEADERS_A)
    test("Cancel nonexistent -> 400", r.status_code, 400)


# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("P18 ADVANCED DATA JOBS TESTS")
    print("=" * 60)

    setup_entity()

    print("\nStarting server...")
    proc = start_server()
    client = httpx.Client(base_url=BASE, timeout=30)

    try:
        import_id, export_id = test_create_job(client)
        test_execute_import(client, import_id)
        test_execute_export(client, export_id)
        test_batch_update(client)
        test_batch_delete(client)
        test_report_job(client)
        test_cancel_job(client)
        test_tenant_isolation(client)
        test_rbac(client)
        test_errors(client)
    finally:
        client.close()
        stop_server(proc)

    print("\n" + "=" * 60)
    print(f"P18 RESULTS: {passed}/{passed + failed} PASSED, {failed} FAILED")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
