"""
P42 Tenant Lifecycle Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/tenant-lifecycle"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
HV = {"Authorization": f"Bearer {TOKEN_V}"}
p, f = 0, 0


def t(name, got, exp):
    global p, f
    if got == exp:
        p += 1
    else:
        f += 1
        print(f"  FAIL - {name}: got {got!r}, expected {exp!r}")


def start():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(5)
    return proc


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def setup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ['dbp_tenant_lifecycle_events', 'dbp_tenant_data_exports',
                     'dbp_tenant_invitations', 'dbp_tenant_activity_logs',
                     'dbp_tenant_notifications']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()


def cleanup():
    setup()


def test_events(c):
    print("\n--- 1. Lifecycle Events ---")
    r = c.post(f"{EP}/events", json={"event_type": "tenant_created",
               "event_data": {"plan": "enterprise"}, "reason": "New customer"}, headers=H_A)
    t("Record event", r.status_code, 200)
    eid = r.json()["data"]["id"]

    r = c.post(f"{EP}/events", json={"event_type": "plan_upgraded",
               "event_data": {"from": "starter", "to": "enterprise"}}, headers=H_A)
    t("Record upgrade event", r.status_code, 200)

    r = c.get(f"{EP}/events", headers=H_A)
    t("List events", r.status_code, 200)
    t("Two events", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/events/{eid}", headers=H_A)
    t("Get event", r.status_code, 200)
    t("Event type correct", r.json()["data"]["event_type"], "tenant_created")

    r = c.get(f"{EP}/events?event_type=tenant_created", headers=H_A)
    t("Filter by type", r.status_code, 200)
    t("One creation event", len(r.json()["data"]), 1)

    r = c.get(f"{EP}/events/{eid}", headers=H_B)
    t("Tenant B cant see A event", r.status_code, 404)


def test_data_exports(c):
    print("\n--- 2. Data Exports ---")
    r = c.post(f"{EP}/data-exports", json={"export_type": "full_backup",
               "entity_types": ["companies", "employees", "invoices"]}, headers=H_A)
    t("Create data export", r.status_code, 200)
    did = r.json()["data"]["id"]

    r = c.get(f"{EP}/data-exports", headers=H_A)
    t("List exports", r.status_code, 200)
    t("Export not empty", len(r.json()["data"]) > 0, True)

    r = c.put(f"{EP}/data-exports/{did}", json={"status": "running"}, headers=H_A)
    t("Update to running", r.status_code, 200)

    r = c.put(f"{EP}/data-exports/{did}", json={"status": "completed",
               "file_path": "/exports/full_backup.sql.gz",
               "file_size_bytes": 5242880, "record_count": 15000}, headers=H_A)
    t("Update to completed", r.status_code, 200)

    r = c.get(f"{EP}/data-exports/{did}" if False else f"{EP}/data-exports", headers=H_A)
    exports = r.json()["data"]
    comp = [x for x in exports if x.get("status") == "completed"]
    t("Export completed", len(comp) > 0, True)

    r = c.get(f"{EP}/data-exports", headers=H_B)
    t("Tenant B no A exports", len(r.json()["data"]), 0)


def test_invitations(c):
    print("\n--- 3. Invitations ---")
    r = c.post(f"{EP}/invitations", json={"email": "newuser@acme.com",
               "role": "operator"}, headers=H_A)
    t("Create invitation", r.status_code, 200)
    iid = r.json()["data"]["id"]

    r = c.post(f"{EP}/invitations", json={"email": "manager@acme.com",
               "role": "manager"}, headers=H_A)
    t("Create second invitation", r.status_code, 200)

    r = c.get(f"{EP}/invitations", headers=H_A)
    t("List invitations", r.status_code, 200)
    t("Two invitations", len(r.json()["data"]), 2)

    r = c.put(f"{EP}/invitations/{iid}/accept", headers=H_A)
    t("Accept invitation", r.status_code, 200)

    r = c.get(f"{EP}/invitations", headers=H_A)
    accepted = [x for x in r.json()["data"] if x.get("status") == "accepted"]
    t("One accepted", len(accepted), 1)

    r = c.get(f"{EP}/invitations", headers=H_B)
    t("Tenant B no A invitations", len(r.json()["data"]), 0)


def test_activity_logs(c):
    print("\n--- 4. Activity Logs ---")
    r = c.post(f"{EP}/activity-logs", json={"action": "login",
               "resource_type": "session", "ip_address": "192.168.1.1"}, headers=H_A)
    t("Log activity", r.status_code, 200)
    lid = r.json()["data"]["id"]

    r = c.post(f"{EP}/activity-logs", json={"action": "create_company",
               "resource_type": "company", "resource_id": "co123",
               "details": {"name": "Acme"}}, headers=H_A)
    t("Log create activity", r.status_code, 200)

    r = c.get(f"{EP}/activity-logs", headers=H_A)
    t("List activity logs", r.status_code, 200)
    t("Two activities", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/activity-logs?action=login", headers=H_A)
    t("Filter by action", r.status_code, 200)
    t("One login", len(r.json()["data"]), 1)

    r = c.get(f"{EP}/activity-logs", headers=H_B)
    t("Tenant B no A activities", len(r.json()["data"]), 0)


def test_notifications(c):
    print("\n--- 5. Notifications ---")
    r = c.post(f"{EP}/notifications", json={"notification_type": "system",
               "title": "Scheduled Maintenance",
               "message": "System maintenance on Sunday 2AM UTC",
               "severity": "warning"}, headers=H_A)
    t("Create notification", r.status_code, 200)
    nid = r.json()["data"]["id"]

    r = c.post(f"{EP}/notifications", json={"notification_type": "billing",
               "title": "Invoice Ready",
               "severity": "info"}, headers=H_A)
    t("Create billing notification", r.status_code, 200)

    r = c.get(f"{EP}/notifications", headers=H_A)
    t("List notifications", r.status_code, 200)
    t("Two notifications", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/notifications/{nid}", headers=H_A)
    t("Get notification", r.status_code, 200)
    t("Not read yet", r.json()["data"]["is_read"], False)

    r = c.put(f"{EP}/notifications/{nid}/read", headers=H_A)
    t("Mark as read", r.status_code, 200)

    r = c.get(f"{EP}/notifications/{nid}", headers=H_A)
    t("Notification is read", r.json()["data"]["is_read"], True)

    r = c.get(f"{EP}/notifications?is_read=false", headers=H_A)
    t("Unread filter", r.status_code, 200)
    t("One unread", len(r.json()["data"]), 1)

    r = c.delete(f"{EP}/notifications/{nid}", headers=H_A)
    t("Delete notification", r.status_code, 200)

    r = c.get(f"{EP}/notifications/{nid}", headers=H_A)
    t("Deleted notification 404", r.status_code, 404)


def test_rbac(c):
    print("\n--- 6. RBAC ---")
    r = c.get(f"{EP}/events", headers=HV)
    t("Viewer can list events", r.status_code, 200)
    r = c.post(f"{EP}/events", json={"event_type": "test"}, headers=HV)
    t("Viewer cannot create event", r.status_code, 403)
    r = c.get(f"{EP}/invitations", headers=HV)
    t("Viewer can list invitations", r.status_code, 200)
    r = c.get(f"{EP}/notifications", headers=HV)
    t("Viewer can list notifications", r.status_code, 200)
    r = c.get(f"{EP}/activity-logs", headers=HV)
    t("Viewer can list activity logs", r.status_code, 200)


def test_negative(c):
    print("\n--- 7. Negative Tests ---")
    r = c.get(f"{EP}/events/nonexistent", headers=H_A)
    t("Get non-existent event", r.status_code, 404)
    r = c.get(f"{EP}/notifications/nonexistent", headers=H_A)
    t("Get non-existent notification", r.status_code, 404)
    r = c.post(f"{EP}/events", json={}, headers=H_A)
    t("Create event missing fields", r.status_code, 400)
    r = c.post(f"{EP}/data-exports", json={}, headers=H_A)
    t("Create export missing fields", r.status_code, 400)
    r = c.post(f"{EP}/invitations", json={}, headers=H_A)
    t("Create invitation missing fields", r.status_code, 400)
    r = c.post(f"{EP}/activity-logs", json={}, headers=H_A)
    t("Log activity missing fields", r.status_code, 400)
    r = c.post(f"{EP}/notifications", json={}, headers=H_A)
    t("Create notification missing fields", r.status_code, 400)


if __name__ == "__main__":
    print("=" * 60)
    print("P42 TENANT LIFECYCLE TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_events(c)
        test_data_exports(c)
        test_invitations(c)
        test_activity_logs(c)
        test_notifications(c)
        test_rbac(c)
        test_negative(c)
    finally:
        c.close()
        stop(proc)
        cleanup()
    print("\n" + "=" * 60)
    print(f"P42 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
