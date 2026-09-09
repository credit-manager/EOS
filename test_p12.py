"""
P12 Events / Webhooks TESTS
Full verification matrix for event emission, event log, webhook CRUD, delivery.
"""
import httpx
import subprocess
import sys
import time
import os
import uuid
import traceback
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"

TOKEN_ADMIN = create_test_token("tenant_a", user_id="admin", roles=["dynamic_manager", {"permission": "*:*"}])
TOKEN_A = create_test_token("tenant_a", roles=["dynamic_manager"])
TOKEN_VIEWER = create_test_token("tenant_a", roles=["dynamic_viewer"])
TOKEN_B = create_test_token("tenant_b", roles=["dynamic_manager"])
HEADERS_ADMIN = {"Authorization": f"Bearer {TOKEN_ADMIN}"}
HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_VIEWER = {"Authorization": f"Bearer {TOKEN_VIEWER}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}

passed = 0
failed = 0


def test(name, got, expected):
    global passed, failed
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed += 1
        print(f"  {status} - {name}: got {got!r}, expected {expected!r}")
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
proc = start_server()
client = httpx.Client(base_url=BASE, timeout=30)

from database import SessionLocal
from sqlalchemy import text as sa_text

db_setup = SessionLocal()
db_setup.execute(sa_text("DROP TABLE IF EXISTS evt_test_table"))
db_setup.execute(sa_text("DROP TABLE IF EXISTS evt_test_table2"))
db_setup.execute(sa_text("""
    CREATE TABLE evt_test_table (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36),
        name VARCHAR(255),
        value NUMERIC,
        deleted_at TIMESTAMPTZ,
        deleted_by VARCHAR(100)
    )
"""))
db_setup.execute(sa_text("""
    CREATE TABLE evt_test_table2 (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36),
        name VARCHAR(255),
        value NUMERIC,
        deleted_at TIMESTAMPTZ,
        deleted_by VARCHAR(100)
    )
"""))
db_setup.commit()
db_setup.close()

try:
    print("=" * 60)
    print("P12 EVENTS & WEBHOOKS TESTS")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════
    # SECTION 1: Event emission on record CRUD
    # ═══════════════════════════════════════════════════════
    print("\n--- 1. Record CRUD Event Emission ---")

    ecode = f"evt_{uuid.uuid4().hex[:6]}"
    r = client.post(f"{EP}/entities", headers=HEADERS_ADMIN, json={
        "code": ecode,
        "name_en": "Event Test Entity",
        "faculty": "inventory",
        "table_mapping": "evt_test_table",
        "fields": [
            {"code": "code", "label_en": "Code", "field_type": "string", "is_required": True},
            {"code": "name", "label_en": "Name", "field_type": "string", "is_required": True},
        ],
    })
    test("Create entity -> 200", r.status_code, 200)

    # Create record -> should emit record.created
    r = client.post(f"{EP}/entities/{ecode}/records", headers=HEADERS_A, json={
        "code": "EVT001",
        "name": "Event Test Item",
    })
    test("Create record -> 200", r.status_code, 200)
    rec_id = r.json().get("id")

    # Check event log
    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode, "event_type": "record.created"})
    test("Event log has record.created", r.status_code, 200)
    events = r.json().get("data", [])
    test("record.created event found", len(events) >= 1, True)

    # Update record -> should emit record.updated
    r = client.put(f"{EP}/entities/{ecode}/records/{rec_id}", headers=HEADERS_A, json={
        "code": "EVT001",
        "name": "Updated Event Item",
    })
    test("Update record -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode, "event_type": "record.updated"})
    events = r.json().get("data", [])
    test("record.updated event found", len(events) >= 1, True)

    # Delete record -> should emit record.deleted
    r = client.delete(f"{EP}/entities/{ecode}/records/{rec_id}", headers=HEADERS_A)
    test("Delete record -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode, "event_type": "record.deleted"})
    events = r.json().get("data", [])
    test("record.deleted event found", len(events) >= 1, True)

    # Restore record -> should emit record.restored
    r = client.post(f"{EP}/entities/{ecode}/records/{rec_id}/restore", headers=HEADERS_ADMIN)
    test("Restore record -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode, "event_type": "record.restored"})
    events = r.json().get("data", [])
    test("record.restored event found", len(events) >= 1, True)

    # ═══════════════════════════════════════════════════════
    # SECTION 2: Bulk event emission
    # ═══════════════════════════════════════════════════════
    print("\n--- 2. Bulk Event Emission ---")

    # Bulk create
    r = client.post(f"{EP}/entities/{ecode}/records/bulk", headers=HEADERS_A, json={
        "records": [
            {"code": "BLK001", "name": "Bulk 1"},
            {"code": "BLK002", "name": "Bulk 2"},
        ]
    })
    test("Bulk create -> 200", r.status_code, 200)
    bulk_ids = r.json().get("created", [])

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode, "event_type": "record.bulk_created"})
    events = r.json().get("data", [])
    test("record.bulk_created event found", len(events) >= 1, True)

    # Bulk update
    r = client.put(f"{EP}/entities/{ecode}/records/bulk", headers=HEADERS_A, json={
        "records": [
            {"id": bulk_ids[0], "fields": {"name": "Bulk 1 Updated"}},
        ]
    })
    test("Bulk update -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode, "event_type": "record.bulk_updated"})
    events = r.json().get("data", [])
    test("record.bulk_updated event found", len(events) >= 1, True)

    # Bulk delete
    r = client.request("DELETE", f"{EP}/entities/{ecode}/records/bulk", headers=HEADERS_A, json={
        "ids": bulk_ids,
    })
    test("Bulk delete -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode, "event_type": "record.bulk_deleted"})
    events = r.json().get("data", [])
    test("record.bulk_deleted event found", len(events) >= 1, True)

    # ═══════════════════════════════════════════════════════
    # SECTION 3: Entity management events
    # ═══════════════════════════════════════════════════════
    print("\n--- 3. Entity Management Events ---")

    ecode2 = f"evt2_{uuid.uuid4().hex[:6]}"
    r = client.post(f"{EP}/entities", headers=HEADERS_ADMIN, json={
        "code": ecode2,
        "name_en": "Entity for Event Testing",
        "faculty": "inventory",
        "table_mapping": "evt_test_table2",
    })
    test("Create entity -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode2, "event_type": "entity.created"})
    events = r.json().get("data", [])
    test("entity.created event found", len(events) >= 1, True)

    # Update entity -> entity.updated
    r = client.put(f"{EP}/entities/{ecode2}", headers=HEADERS_ADMIN, json={
        "name_en": "Updated Entity Name",
    })
    test("Update entity -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode2, "event_type": "entity.updated"})
    events = r.json().get("data", [])
    test("entity.updated event found", len(events) >= 1, True)

    # Add field -> field.added
    r = client.post(f"{EP}/entities/{ecode2}/fields", headers=HEADERS_ADMIN, json={
        "code": "test_field",
        "label_en": "Test Field",
        "field_type": "string",
    })
    test("Add field -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode2, "event_type": "field.added"})
    events = r.json().get("data", [])
    test("field.added event found", len(events) >= 1, True)

    # Update field -> field.updated
    r = client.put(f"{EP}/entities/{ecode2}/fields/test_field", headers=HEADERS_ADMIN, json={
        "label_en": "Updated Test Field",
    })
    test("Update field -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode2, "event_type": "field.updated"})
    events = r.json().get("data", [])
    test("field.updated event found", len(events) >= 1, True)

    # Remove field -> field.removed
    r = client.delete(f"{EP}/entities/{ecode2}/fields/test_field", headers=HEADERS_ADMIN)
    test("Remove field -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode2, "event_type": "field.removed"})
    events = r.json().get("data", [])
    test("field.removed event found", len(events) >= 1, True)

    # Delete entity -> entity.deleted
    r = client.delete(f"{EP}/entities/{ecode2}", headers=HEADERS_ADMIN)
    test("Delete entity -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode2, "event_type": "entity.deleted"})
    events = r.json().get("data", [])
    test("entity.deleted event found", len(events) >= 1, True)

    # ═══════════════════════════════════════════════════════
    # SECTION 4: Single event retrieval
    # ═══════════════════════════════════════════════════════
    print("\n--- 4. Single Event Retrieval ---")

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"limit": 1})
    test("List events -> 200", r.status_code, 200)
    first_event = r.json().get("data", [])
    if first_event:
        event_id = first_event[0]["id"]
        r2 = client.get(f"{EP}/events/{event_id}", headers=HEADERS_A)
        test("Get single event -> 200", r2.status_code, 200)
        test("Event ID matches", r2.json().get("data", {}).get("id"), event_id)
    else:
        test("Get single event (no events)", False, True)

    r = client.get(f"{EP}/events/{uuid.uuid4()}", headers=HEADERS_A)
    test("Nonexistent event -> 404", r.status_code, 404)

    # ═══════════════════════════════════════════════════════
    # SECTION 5: Webhook CRUD
    # ═══════════════════════════════════════════════════════
    print("\n--- 5. Webhook CRUD ---")

    wh_code = f"wh_{uuid.uuid4().hex[:6]}"
    r = client.post(f"{EP}/webhooks", headers=HEADERS_ADMIN, json={
        "code": wh_code,
        "target_url": "https://example.com/webhook",
        "entity_code": ecode,
        "event_types": ["record.created", "record.updated"],
        "secret": "test-secret-key",
    })
    test("Create webhook -> 200", r.status_code, 200)

    r = client.get(f"{EP}/webhooks", headers=HEADERS_A)
    test("List webhooks -> 200", r.status_code, 200)
    whs = r.json().get("data", [])
    test("Webhook in list", any(w["code"] == wh_code for w in whs), True)

    r = client.get(f"{EP}/webhooks/{wh_code}", headers=HEADERS_A)
    test("Get webhook -> 200", r.status_code, 200)
    wh_data = r.json().get("data", {})
    test("Webhook URL matches", wh_data.get("target_url"), "https://example.com/webhook")
    test("Webhook entity matches", wh_data.get("entity_code"), ecode)

    r = client.put(f"{EP}/webhooks/{wh_code}", headers=HEADERS_ADMIN, json={
        "target_url": "https://example.com/updated",
        "is_active": False,
    })
    test("Update webhook -> 200", r.status_code, 200)

    r = client.get(f"{EP}/webhooks/{wh_code}", headers=HEADERS_A)
    test("Updated URL", r.json().get("data", {}).get("target_url"), "https://example.com/updated")
    test("Updated is_active", r.json().get("data", {}).get("is_active"), False)

    # Duplicate code -> 409
    r = client.post(f"{EP}/webhooks", headers=HEADERS_ADMIN, json={
        "code": wh_code,
        "target_url": "https://example.com/dup",
        "entity_code": ecode,
        "event_types": ["record.created"],
    })
    test("Duplicate webhook code -> 409", r.status_code, 409)

    # Invalid event type -> 400
    r = client.post(f"{EP}/webhooks", headers=HEADERS_ADMIN, json={
        "code": f"wh_{uuid.uuid4().hex[:6]}",
        "target_url": "https://example.com",
        "entity_code": ecode,
        "event_types": ["invalid.type"],
    })
    test("Invalid event type -> 400", r.status_code, 400)

    r = client.delete(f"{EP}/webhooks/{wh_code}", headers=HEADERS_ADMIN)
    test("Delete webhook -> 200", r.status_code, 200)

    r = client.get(f"{EP}/webhooks/{wh_code}", headers=HEADERS_A)
    test("Deleted webhook -> 404", r.status_code, 404)

    # ═══════════════════════════════════════════════════════
    # SECTION 6: Webhook deliveries
    # ═══════════════════════════════════════════════════════
    print("\n--- 6. Webhook Deliveries ---")

    wh_code2 = f"wh2_{uuid.uuid4().hex[:6]}"
    r = client.post(f"{EP}/webhooks", headers=HEADERS_ADMIN, json={
        "code": wh_code2,
        "target_url": "https://example.com/deliver",
        "entity_code": ecode,
        "event_types": ["*"],
    })
    test("Create wildcard webhook -> 200", r.status_code, 200)

    r = client.post(f"{EP}/entities/{ecode}/records", headers=HEADERS_A, json={
        "code": "EVT002",
        "name": "Delivery Test",
    })
    test("Trigger delivery via record.create -> 200", r.status_code, 200)

    r = client.get(f"{EP}/webhooks/{wh_code2}/deliveries", headers=HEADERS_A)
    test("List deliveries -> 200", r.status_code, 200)
    deliveries = r.json().get("data", [])
    test("Delivery record created", len(deliveries) >= 1, True)

    r = client.get(f"{EP}/webhooks/nonexistent/deliveries", headers=HEADERS_A)
    test("Nonexistent webhook deliveries -> 404", r.status_code, 404)

    # ═══════════════════════════════════════════════════════
    # SECTION 7: RBAC
    # ═══════════════════════════════════════════════════════
    print("\n--- 7. RBAC ---")

    r = client.get(f"{EP}/events", headers=HEADERS_VIEWER)
    test("Viewer read events -> 200", r.status_code, 200)

    r = client.post(f"{EP}/webhooks", headers=HEADERS_VIEWER, json={
        "code": f"wh_{uuid.uuid4().hex[:6]}",
        "target_url": "https://example.com",
        "entity_code": ecode,
        "event_types": ["record.created"],
    })
    test("Viewer create webhook -> 403", r.status_code, 403)

    r = client.get(f"{EP}/events", headers=HEADERS_A)
    test("Operator read events -> 200", r.status_code, 200)

    # ═══════════════════════════════════════════════════════
    # SECTION 8: Event Filtering
    # ═══════════════════════════════════════════════════════
    print("\n--- 8. Event Filtering ---")

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode})
    test("Filter by entity_code -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"event_type": "record.created"})
    test("Filter by event_type -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode, "event_type": "record.created"})
    test("Combined filter -> 200", r.status_code, 200)
    for ev in r.json().get("data", []):
        test("Event matches entity_code", ev.get("entity_code"), ecode)
        test("Event matches event_type", ev.get("event_type"), "record.created")

    # ═══════════════════════════════════════════════════════
    # SECTION 9: Import events
    # ═══════════════════════════════════════════════════════
    print("\n--- 9. Import Events ---")

    import csv
    csv_content = "code,name\nIMP_EVT1,Import Event 1\nIMP_EVT2,Import Event 2\n"
    buf = csv_content.encode("utf-8")

    files = {"file": ("import.csv", buf, "text/csv")}
    r = client.post(
        f"{EP}/entities/{ecode}/import?mode=partial",
        headers=HEADERS_A,
        files=files,
    )
    test("Import -> 200", r.status_code, 200)

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"entity_code": ecode, "event_type": "record.imported"})
    events = r.json().get("data", [])
    test("record.imported event found", len(events) >= 1, True)

    # ═══════════════════════════════════════════════════════
    # SECTION 10: Edge Cases
    # ═══════════════════════════════════════════════════════
    print("\n--- 10. Edge Cases ---")

    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"limit": 2})
    data = r.json().get("data", [])
    test("Limit respected", len(data) <= 2, True)

    r = client.put(f"{EP}/webhooks/nonexistent", headers=HEADERS_ADMIN, json={"target_url": "x"})
    test("Update nonexistent webhook -> 404", r.status_code, 404)

    r = client.delete(f"{EP}/webhooks/nonexistent", headers=HEADERS_ADMIN)
    test("Delete nonexistent webhook -> 404", r.status_code, 404)

    # ═══════════════════════════════════════════════════════
    # RESULTS
    # ═══════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"P12 RESULTS: {passed}/{total} PASSED, {failed} FAILED")
    print("=" * 60)

except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    traceback.print_exc()
    failed += 1

finally:
    client.close()
    stop_server(proc)
    print(f"\nFinal: {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
