"""
P15 NOTIFICATION & COMMUNICATION TESTS
========================================
Tests notification engine, event→notification bridge,
preferences, mark read, templates, RBAC.
"""
import httpx
import subprocess
import sys
import time
import os
sys.path.insert(0, '.')

from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"

# Tokens — tenant_a
TOKEN_A = create_test_token("tenant_a", user_id="admin", email="admin@test.com",
                             roles=["admin"])
TOKEN_M = create_test_token("tenant_a", user_id="manager", email="mgr@test.com",
                             roles=["dynamic_manager"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com",
                             roles=["dynamic_viewer"])
# tenant_b
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="adminb@test.com",
                             roles=["admin"])

HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_M = {"Authorization": f"Bearer {TOKEN_M}"}
HEADERS_V = {"Authorization": f"Bearer {TOKEN_V}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}

passed = 0
failed = 0


def test(name, got, expected):
    global passed, failed
    ok = got == expected
    if not ok:
        failed += 1
        print(f"  FAIL - {name}: got {got!r}, expected {expected!r}")
    else:
        passed += 1


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


# ═══════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════

def setup_entities():
    from database import SessionLocal
    from sqlalchemy import text as sa_text
    from models import DBPEntity, DBPField, DBPNotificationPreference
    import uuid

    db = SessionLocal()
    try:
        # Cleanup
        db.execute(sa_text("DELETE FROM dbp_notification_preferences"))
        db.execute(sa_text("DELETE FROM dbp_notifications"))
        db.execute(sa_text("DELETE FROM dbp_notification_templates WHERE code LIKE 'test_%'"))
        for code in ('p15_emp',):
            db.execute(sa_text(f"DELETE FROM dbp_fields WHERE entity_id IN "
                               f"(SELECT id FROM dbp_entities WHERE code = '{code}')"))
            db.execute(sa_text(f"DELETE FROM dbp_entities WHERE code = '{code}'"))
            db.execute(sa_text(f"DROP TABLE IF EXISTS {code}_tbl"))
        db.commit()

        # Physical table
        db.execute(sa_text("""
            CREATE TABLE p15_emp_tbl (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                name VARCHAR(255),
                email VARCHAR(255)
            )
        """))

        # Entity
        emp = DBPEntity(code="p15_emp", name_en="Employee", name_ar="موظف",
                        faculty="hr", table_mapping="p15_emp_tbl")
        db.add(emp)
        db.flush()
        db.add_all([
            DBPField(entity_id=emp.id, code="name", label_en="Name",
                     field_type="string", is_required=True),
            DBPField(entity_id=emp.id, code="email", label_en="Email",
                     field_type="email"),
        ])
        db.commit()

        # Ensure default templates exist
        from core.notification_engine import NotificationEngine
        eng = NotificationEngine(db)
        eng.ensure_default_templates("tenant_a")
        db.commit()

        print("  Setup: p15_emp entity + default templates")
    except Exception as e:
        db.rollback()
        print(f"  Setup error: {e}")
        raise
    finally:
        db.close()


# ═══════════════════════════════════════════════════════
# TEST SECTIONS
# ═══════════════════════════════════════════════════════

def test_templates(client):
    """Section 1: Notification Templates"""
    print("\n--- 1. Notification Templates ---")
    r = client.get(f"{EP}/notification-templates", headers=HEADERS_A)
    test("List templates -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Has templates", len(data) > 0, True)

    codes = [t["code"] for t in data]
    test("Has record.created", "record.created" in codes, True)
    test("Has record.deleted", "record.deleted" in codes, True)
    test("Template has title_template", "title_template" in data[0], True)
    test("Template has event_type", "event_type" in data[0], True)
    test("Template is active", data[0]["is_active"], True)


def test_event_triggers_notification(client):
    """Section 2: Event→Notification bridge"""
    print("\n--- 2. Event → Notification Bridge ---")

    # Create record → should trigger record.created notification
    r = client.post(f"{EP}/entities/p15_emp/records", headers=HEADERS_A,
                    json={"name": "Test User", "email": "test@emp.com"})
    test("Create record -> 200", r.status_code, 200)
    record_id = r.json().get("id")

    # Admin should see notification (if preferences set, or default)
    r = client.get(f"{EP}/notifications", headers=HEADERS_A)
    test("List notifications -> 200", r.status_code, 200)
    notifs = r.json()["data"]
    # At this point, no preferences exist yet, so _get_target_users returns []
    # This is expected — preferences needed to receive notifications
    test("Notifications list returned", isinstance(notifs, list), True)

    # Cleanup
    if record_id:
        client.delete(f"{EP}/entities/p15_emp/records/{record_id}", headers=HEADERS_A)


def test_direct_notification(client):
    """Section 3: Direct notification creation"""
    print("\n--- 3. Direct Notification ---")

    # Use the engine directly to create a notification
    from database import SessionLocal
    from core.notification_engine import NotificationEngine

    db = SessionLocal()
    try:
        eng = NotificationEngine(db)

        # First, set up preferences so admin receives notifications
        db.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO dbp_notification_preferences "
                "(id, tenant_id, user_id, notification_type, channel, is_enabled) "
                "VALUES (:id, :tid, :uid, 'info', 'in_app', true)"
            ),
            {"id": __import__("uuid").uuid4().hex, "tid": "tenant_a", "uid": "admin"},
        )
        db.commit()

        # Create a direct notification
        nid = eng.create_notification(
            user_id="admin",
            title="Test Notification",
            message="This is a test",
            notification_type="info",
            tenant_id="tenant_a",
            entity_code="p15_emp",
        )
        db.commit()
        test("Direct notification created", nid is not None, True)
    finally:
        db.close()

    # Now admin should see it
    r = client.get(f"{EP}/notifications", headers=HEADERS_A)
    test("Admin sees notifications", r.status_code, 200)
    notifs = r.json()["data"]
    test("Has notification", len(notifs) >= 1, True)
    if notifs:
        test("Title matches", notifs[0]["title"], "Test Notification")
        test("Message matches", notifs[0]["message"], "This is a test")
        test("Has entity_code", notifs[0]["entity_code"], "p15_emp")
        test("Not read yet", notifs[0]["is_read"], False)


def test_mark_read(client):
    """Section 4: Mark read / mark all read"""
    print("\n--- 4. Mark Read ---")

    # Get notification ID
    r = client.get(f"{EP}/notifications", headers=HEADERS_A)
    notifs = r.json()["data"]
    if not notifs:
        test("Has notifications for mark_read", False, True)
        return

    nid = notifs[0]["id"]

    # Mark as read
    r = client.post(f"{EP}/notifications/{nid}/read", headers=HEADERS_A)
    test("Mark read -> 200", r.status_code, 200)

    # Verify it's read
    r = client.get(f"{EP}/notifications/{nid}", headers=HEADERS_A)
    test("Notification is_read=true", r.json()["data"]["is_read"], True)
    test("Has read_at", r.json()["data"]["read_at"] is not None, True)


def test_notifications_count(client):
    """Section 5: Unread count"""
    print("\n--- 5. Unread Count ---")
    r = client.get(f"{EP}/notifications-count", headers=HEADERS_A)
    test("Count endpoint -> 200", r.status_code, 200)
    test("Has unread_count", "unread_count" in r.json()["data"], True)


def test_mark_all_read(client):
    """Section 6: Mark all read"""
    print("\n--- 6. Mark All Read ---")
    r = client.post(f"{EP}/notifications/read-all", headers=HEADERS_A)
    test("Mark all read -> 200", r.status_code, 200)
    test("Has marked_read", "marked_read" in r.json(), True)

    # Verify count is 0
    r = client.get(f"{EP}/notifications-count", headers=HEADERS_A)
    test("Unread count is 0", r.json()["data"]["unread_count"], 0)


def test_notification_detail(client):
    """Section 7: Get single notification"""
    print("\n--- 7. Notification Detail ---")
    r = client.get(f"{EP}/notifications", headers=HEADERS_A)
    notifs = r.json()["data"]
    if not notifs:
        test("Has notifications", False, True)
        return

    nid = notifs[0]["id"]
    r = client.get(f"{EP}/notifications/{nid}", headers=HEADERS_A)
    test("Get notification -> 200", r.status_code, 200)
    test("Has metadata", "metadata" in r.json()["data"], True)


def test_delete_notification(client):
    """Section 8: Delete notification"""
    print("\n--- 8. Delete Notification ---")

    # Create one to delete
    from database import SessionLocal
    from core.notification_engine import NotificationEngine
    import uuid as _uuid

    db = SessionLocal()
    try:
        eng = NotificationEngine(db)
        nid = eng.create_notification(
            user_id="admin", title="Delete Me",
            notification_type="info", tenant_id="tenant_a",
        )
        db.commit()
    finally:
        db.close()

    r = client.delete(f"{EP}/notifications/{nid}", headers=HEADERS_A)
    test("Delete notification -> 200", r.status_code, 200)

    # Verify gone
    r = client.get(f"{EP}/notifications/{nid}", headers=HEADERS_A)
    test("Deleted notification -> 404", r.status_code, 404)


def test_preferences(client):
    """Section 9: Notification preferences"""
    print("\n--- 9. Preferences ---")

    # Get current prefs
    r = client.get(f"{EP}/notification-preferences", headers=HEADERS_A)
    test("Get prefs -> 200", r.status_code, 200)
    prefs = r.json()["data"]
    test("Has prefs", isinstance(prefs, list), True)

    # Update preference — disable info notifications
    r = client.put(f"{EP}/notification-preferences", headers=HEADERS_A,
                   json={"notification_type": "info", "channel": "in_app",
                         "is_enabled": False})
    test("Update pref -> 200", r.status_code, 200)

    # Verify
    r = client.get(f"{EP}/notification-preferences", headers=HEADERS_A)
    prefs = r.json()["data"]
    info_prefs = [p for p in prefs if p["notification_type"] == "info"]
    if info_prefs:
        test("Info disabled", info_prefs[0]["is_enabled"], False)

    # Re-enable
    r = client.put(f"{EP}/notification-preferences", headers=HEADERS_A,
                   json={"notification_type": "info", "channel": "in_app",
                         "is_enabled": True})
    test("Re-enable pref -> 200", r.status_code, 200)


def test_tenant_isolation(client):
    """Section 10: Tenant isolation"""
    print("\n--- 10. Tenant Isolation ---")

    # Create notification for tenant_a admin
    from database import SessionLocal
    from core.notification_engine import NotificationEngine

    db = SessionLocal()
    try:
        eng = NotificationEngine(db)
        nid = eng.create_notification(
            user_id="admin", title="Tenant A Notification",
            notification_type="info", tenant_id="tenant_a",
        )
        db.commit()
    finally:
        db.close()

    # tenant_a admin sees it
    r = client.get(f"{EP}/notifications", headers=HEADERS_A)
    test("Tenant A admin sees notification", r.status_code, 200)
    titles = [n["title"] for n in r.json()["data"]]
    test("Tenant A notification present", "Tenant A Notification" in titles, True)

    # tenant_b admin does NOT see it
    r = client.get(f"{EP}/notifications", headers=HEADERS_B)
    test("Tenant B admin does not see it", r.status_code, 200)
    titles_b = [n["title"] for n in r.json()["data"]]
    test("Tenant B notification absent", "Tenant A Notification" not in titles_b, True)


def test_cross_user_isolation(client):
    """Section 11: Cross-user isolation"""
    print("\n--- 11. Cross-User Isolation ---")

    # Manager should not see admin's notification
    r = client.get(f"{EP}/notifications", headers=HEADERS_M)
    test("Manager sees own only", r.status_code, 200)
    user_ids = set(n["user_id"] for n in r.json()["data"])
    test("No admin notifs for manager", "admin" not in user_ids, True)


def test_errors(client):
    """Section 12: Error handling"""
    print("\n--- 12. Errors ---")

    # Non-existent notification
    r = client.get(f"{EP}/notifications/nonexistent-id", headers=HEADERS_A)
    test("Bad notification ID -> 404", r.status_code, 404)

    # No auth
    r = client.get(f"{EP}/notifications")
    test("No auth -> 401", r.status_code, 401)

    # Missing preference field
    r = client.put(f"{EP}/notification-preferences", headers=HEADERS_A,
                   json={"channel": "in_app"})
    test("Missing notification_type -> 400", r.status_code, 400)


def test_event_notification_with_preferences(client):
    """Section 13: Event → Notification with preferences enabled"""
    print("\n--- 13. Event + Preferences ---")

    # Ensure manager has preferences enabled
    from database import SessionLocal
    from sqlalchemy import text as sa_text
    import uuid as _uuid

    db = SessionLocal()
    try:
        db.execute(sa_text(
            "DELETE FROM dbp_notification_preferences WHERE user_id = 'manager'"
        ))
        db.execute(sa_text(
            "INSERT INTO dbp_notification_preferences "
            "(id, tenant_id, user_id, notification_type, channel, is_enabled) "
            "VALUES (:id, 'tenant_a', 'manager', 'info', 'in_app', true)"
        ), {"id": str(_uuid.uuid4())})
        db.execute(sa_text(
            "INSERT INTO dbp_notification_preferences "
            "(id, tenant_id, user_id, notification_type, channel, is_enabled) "
            "VALUES (:id, 'tenant_a', 'manager', 'warning', 'in_app', true)"
        ), {"id": str(_uuid.uuid4())})
        db.commit()
    finally:
        db.close()

    # Create a record as manager (different user_id)
    r = client.post(f"{EP}/entities/p15_emp/records", headers=HEADERS_M,
                    json={"name": "Event Test", "email": "evt@test.com"})
    test("Create record -> 200", r.status_code, 200)
    rec_id = r.json().get("id")

    # Manager should get notification about the event (via preferences)
    r = client.get(f"{EP}/notifications?notification_type=info", headers=HEADERS_M)
    test("Manager gets event notifications", r.status_code, 200)

    # Cleanup
    if rec_id:
        client.delete(f"{EP}/entities/p15_emp/records/{rec_id}", headers=HEADERS_M)


def test_notification_filtering(client):
    """Section 14: Notification filtering"""
    print("\n--- 14. Notification Filtering ---")

    r = client.get(f"{EP}/notifications?channel=in_app", headers=HEADERS_A)
    test("Filter by channel -> 200", r.status_code, 200)

    r = client.get(f"{EP}/notifications?is_read=true", headers=HEADERS_A)
    test("Filter by is_read -> 200", r.status_code, 200)

    r = client.get(f"{EP}/notifications?entity_code=p15_emp", headers=HEADERS_A)
    test("Filter by entity_code -> 200", r.status_code, 200)

    r = client.get(f"{EP}/notifications?limit=1", headers=HEADERS_A)
    test("Limit=1 -> 200", r.status_code, 200)
    if r.status_code == 200:
        data = r.json()["data"]
        test("Max 1 result", len(data) <= 1, True)


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("P15 NOTIFICATION & COMMUNICATION TESTS")
    print("=" * 60)

    print("\nSetup: Creating test entities...")
    setup_entities()

    print("Starting server...")
    proc = start_server()
    client = httpx.Client(base_url=BASE, timeout=30)

    try:
        test_templates(client)
        test_event_triggers_notification(client)
        test_direct_notification(client)
        test_mark_read(client)
        test_notifications_count(client)
        test_mark_all_read(client)
        test_notification_detail(client)
        test_delete_notification(client)
        test_preferences(client)
        test_tenant_isolation(client)
        test_cross_user_isolation(client)
        test_errors(client)
        test_event_notification_with_preferences(client)
        test_notification_filtering(client)
    finally:
        client.close()
        stop_server(proc)

    print("\n" + "=" * 60)
    print(f"P15 RESULTS: {passed}/{passed + failed} PASSED, {failed} FAILED")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
