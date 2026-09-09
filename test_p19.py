"""
P19 WEBHOOK MANAGEMENT DASHBOARD TESTS
========================================
"""
import httpx, subprocess, sys, time, os, uuid as uuid_mod
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"

TOKEN_A = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="adminb@test.com", roles=["admin"])

HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
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

def setup():
    """Clean webhook deliveries and create test entity."""
    from database import SessionLocal
    from sqlalchemy import text as sa_text
    db = SessionLocal()
    try:
        db.execute(sa_text("DELETE FROM dbp_webhook_deliveries"))
        db.execute(sa_text("DELETE FROM dbp_webhooks WHERE code LIKE 'p19_%'"))
        db.commit()
        existing = db.execute(sa_text(
            "SELECT id FROM dbp_entities WHERE code='p19_test'"
        )).fetchone()
        if not existing:
            db.execute(sa_text(
                "INSERT INTO dbp_entities (id, code, name_en, faculty, table_mapping) "
                "VALUES ('p19_ent', 'p19_test', 'P19 Test', 'test', 'p19_test')"
            ))
            db.commit()
    finally:
        db.close()


WH_CODE = "p19_test_hook"


def create_test_webhook(client):
    """Helper to create a webhook via P12 endpoint."""
    r = client.post(f"{EP}/webhooks", headers=HEADERS_A, json={
        "code": WH_CODE,
        "target_url": "https://httpbin.org/post",
        "entity_code": "p19_test",
        "event_types": ["record.created", "record.updated"],
    })
    assert r.status_code == 200, f"Create webhook failed: {r.status_code} {r.text}"
    return r.json()["webhook_id"]


def test_delivery_history(client):
    """Section 1: Delivery history"""
    print("\n--- 1. Delivery History ---")

    # P12 already has this route, P19 doesn't duplicate it
    r = client.get(f"{EP}/webhooks/{WH_CODE}/deliveries", headers=HEADERS_A)
    test("List deliveries -> 200", r.status_code, 200)
    test("Has data", "data" in r.json(), True)


def test_retry_delivery(client):
    """Section 2: Retry deliveries"""
    print("\n--- 2. Retry Deliveries ---")

    # Insert a failed delivery directly
    from database import SessionLocal
    from sqlalchemy import text as sa_text

    wh_id = None
    db = SessionLocal()
    try:
        row = db.execute(sa_text(f"SELECT id FROM dbp_webhooks WHERE code='{WH_CODE}'")).fetchone()
        wh_id = row[0] if row else None
    finally:
        db.close()

    if not wh_id:
        print("  SKIP: webhook not found")
        return

    delivery_id = str(uuid_mod.uuid4())
    event_id = str(uuid_mod.uuid4())
    db = SessionLocal()
    try:
        db.execute(sa_text(
            "INSERT INTO dbp_events (id, tenant_id, event_type, entity_code, "
            "record_id, user_id, payload, created_at) "
            "VALUES (:id, 'tenant_a', 'record.created', 'p19_test', 'rec1', 'admin', '{}', NOW())"
        ), {"id": event_id})
        db.execute(sa_text(
            "INSERT INTO dbp_webhook_deliveries "
            "(id, webhook_id, event_id, status, attempts, last_response_code, last_error) "
            "VALUES (:id, :wid, :eid, 'failed', 3, 500, 'Internal Server Error')"
        ), {"id": delivery_id, "wid": wh_id, "eid": event_id})
        db.commit()
    finally:
        db.close()

    # Retry single
    r = client.post(f"{EP}/webhook-deliveries/{delivery_id}/retry", headers=HEADERS_A)
    test("Retry delivery -> 200", r.status_code, 200)
    test("Status reset to pending", r.json()["data"]["status"], "pending")

    # Can't retry nonexistent
    r = client.post(f"{EP}/webhook-deliveries/nonexistent/retry", headers=HEADERS_A)
    test("Retry nonexistent -> 404", r.status_code, 404)

    # Retry all failed — insert more
    db = SessionLocal()
    try:
        for i in range(3):
            did = str(uuid_mod.uuid4())
            eid = str(uuid_mod.uuid4())
            db.execute(sa_text(
                "INSERT INTO dbp_events (id, tenant_id, event_type, entity_code, "
                "record_id, user_id, payload, created_at) "
                "VALUES (:id, 'tenant_a', 'record.updated', 'p19_test', :rid, 'admin', '{}', NOW())"
            ), {"id": eid, "rid": f"rec{i}"})
            db.execute(sa_text(
                "INSERT INTO dbp_webhook_deliveries "
                "(id, webhook_id, event_id, status, attempts, last_error) "
                "VALUES (:id, :wid, :eid, 'failed', 1, 'timeout')"
            ), {"id": did, "wid": wh_id, "eid": eid})
        db.commit()
    finally:
        db.close()

    r = client.post(f"{EP}/webhooks/{WH_CODE}/retry-failed", headers=HEADERS_A)
    test("Retry all failed -> 200", r.status_code, 200)
    test("Retrying count >= 3", r.json()["data"]["retrying_count"] >= 3, True)

    # Retry all failed - nonexistent webhook
    r = client.post(f"{EP}/webhooks/nonexistent/retry-failed", headers=HEADERS_A)
    test("Retry failed nonexistent -> 404", r.status_code, 404)


def test_health(client):
    """Section 3: Health metrics"""
    print("\n--- 3. Health Metrics ---")

    r = client.get(f"{EP}/webhooks/{WH_CODE}/health", headers=HEADERS_A)
    test("Health -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Has total_deliveries", "total_deliveries" in data, True)
    test("Has success_rate", "success_rate" in data, True)
    test("Has error_breakdown", "error_breakdown" in data, True)
    test("Has period_hours", data["period_hours"], 24)
    test("Has webhook_code", data["webhook_code"], WH_CODE)

    # Custom period
    r = client.get(f"{EP}/webhooks/{WH_CODE}/health?hours=1", headers=HEADERS_A)
    test("Health 1 hour -> 200", r.status_code, 200)
    test("Period is 1", r.json()["data"]["period_hours"], 1)

    # Nonexistent
    r = client.get(f"{EP}/webhooks/nonexistent_health/health", headers=HEADERS_A)
    test("Nonexistent health -> 404", r.status_code, 404)


def test_rbac(client):
    """Section 4: RBAC"""
    print("\n--- 4. RBAC ---")

    # Viewer can read health
    r = client.get(f"{EP}/webhooks/{WH_CODE}/health", headers=HEADERS_V)
    test("Viewer health -> 200", r.status_code, 200)

    # No auth
    r = client.post(f"{EP}/webhooks/{WH_CODE}/retry-failed")
    test("No auth retry-failed -> 401", r.status_code, 401)

    r = client.post(f"{EP}/webhooks/{WH_CODE}/test")
    test("No auth test -> 401", r.status_code, 401)


def test_errors(client):
    """Section 5: Errors"""
    print("\n--- 5. Errors ---")

    r = client.post(f"{EP}/webhooks/nonexistent/retry-failed", headers=HEADERS_A)
    test("Retry failed nonexistent -> 404", r.status_code, 404)

    r = client.get(f"{EP}/webhooks/nonexistent/health", headers=HEADERS_A)
    test("Health nonexistent -> 404", r.status_code, 404)


# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("P19 WEBHOOK MANAGEMENT DASHBOARD TESTS")
    print("=" * 60)

    setup()

    print("\nStarting server...")
    proc = start_server()
    client = httpx.Client(base_url=BASE, timeout=30)

    try:
        create_test_webhook(client)
        test_delivery_history(client)
        test_retry_delivery(client)
        test_health(client)
        test_rbac(client)
        test_errors(client)
    finally:
        client.close()
        stop_server(proc)

    print("\n" + "=" * 60)
    print(f"P19 RESULTS: {passed}/{passed + failed} PASSED, {failed} FAILED")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
