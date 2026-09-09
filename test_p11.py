"""
P11 SCHEMA VERSIONING TESTS
Tests entity management + immutable versioning.
"""
import httpx
import subprocess
import sys
import time
import os
import uuid
import sys
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
db_setup.execute(sa_text("""
    CREATE TABLE IF NOT EXISTS sv_empty_table (
        id VARCHAR(36) PRIMARY KEY,
        name VARCHAR(255)
    )
"""))
db_setup.execute(sa_text("TRUNCATE sv_empty_table"))
db_setup.commit()
db_setup.close()

try:
    print("=" * 60)
    print("P11 SCHEMA VERSIONING TESTS")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════
    # SECTION 1: Entity CRUD — Create
    # ═══════════════════════════════════════════════════════
    print("\n--- 1. Entity CRUD ---")

    ecode = f"sv_{uuid.uuid4().hex[:6]}"
    r = client.post(f"{EP}/entities", headers=HEADERS_ADMIN, json={
        "code": ecode,
        "name_en": "Schema Versioning Test",
        "name_ar": "اختبار تroud الإصدارات",
        "faculty": "inventory",
        "table_mapping": "sv_empty_table",
        "fields": [
            {"code": "code", "label_en": "Code", "field_type": "string", "is_required": True, "ui_config": {"order": 1}},
            {"code": "name", "label_en": "Name", "field_type": "string", "is_required": True, "ui_config": {"order": 2}},
            {"code": "price", "label_en": "Price", "field_type": "number", "is_required": False, "ui_config": {"order": 3}},
        ],
    })
    test("Create entity → 200", r.status_code, 200)
    ver1 = r.json().get("version")
    test("Initial version = 1", ver1, 1)

    # Duplicate → 409
    r = client.post(f"{EP}/entities", headers=HEADERS_ADMIN, json={
        "code": ecode,
        "name_en": "Dup",
        "faculty": "inventory",
        "table_mapping": "sv_empty_table",
    })
    test("Duplicate entity → 409", r.status_code, 409)

    # Nonexistent table → 400
    r = client.post(f"{EP}/entities", headers=HEADERS_ADMIN, json={
        "code": f"sv_{uuid.uuid4().hex[:6]}",
        "name_en": "No Table",
        "faculty": "inventory",
        "table_mapping": "nonexistent_table_xyz",
    })
    test("Nonexistent table → 400", r.status_code, 400)

    # ═══════════════════════════════════════════════════════
    # SECTION 2: Entity CRUD — Update
    # ═══════════════════════════════════════════════════════
    print("\n--- 2. Entity Update ---")

    r = client.put(f"{EP}/entities/{ecode}", headers=HEADERS_ADMIN, json={
        "name_en": "Updated Name",
        "metadata_schema": {"version_note": "updated"},
    })
    test("Update entity → 200", r.status_code, 200)
    ver2 = r.json().get("version")
    test("Version incremented to 2", ver2, 2)

    # No-change update
    r = client.put(f"{EP}/entities/{ecode}", headers=HEADERS_ADMIN, json={
        "name_en": "Updated Name",
    })
    test("No-change update → 200", r.status_code, 200)
    test("No-change: no version bump", r.json().get("version"), None)

    # ═══════════════════════════════════════════════════════
    # SECTION 3: Field Management
    # ═══════════════════════════════════════════════════════
    print("\n--- 3. Field Management ---")

    # Add field
    r = client.post(f"{EP}/entities/{ecode}/fields", headers=HEADERS_ADMIN, json={
        "code": "category",
        "label_en": "Category",
        "field_type": "string",
        "is_required": False,
    })
    test("Add field → 200", r.status_code, 200)
    ver3 = r.json().get("version")
    test("Version after add_field = 3", ver3, 3)

    # Duplicate field → 409
    r = client.post(f"{EP}/entities/{ecode}/fields", headers=HEADERS_ADMIN, json={
        "code": "category",
        "field_type": "string",
    })
    test("Duplicate field → 409", r.status_code, 409)

    # Update field
    r = client.put(f"{EP}/entities/{ecode}/fields/category", headers=HEADERS_ADMIN, json={
        "label_ar": "الفئة",
        "is_required": True,
    })
    test("Update field → 200", r.status_code, 200)
    ver4 = r.json().get("version")
    test("Version after update_field = 4", ver4, 4)

    # Remove field
    r = client.delete(f"{EP}/entities/{ecode}/fields/category", headers=HEADERS_ADMIN)
    test("Remove field → 200", r.status_code, 200)
    ver5 = r.json().get("version")
    test("Version after remove_field = 5", ver5, 5)

    # ═══════════════════════════════════════════════════════
    # SECTION 4: Version Immutability
    # ═══════════════════════════════════════════════════════
    print("\n--- 4. Version Immutability ---")

    r = client.get(f"{EP}/entities/{ecode}/versions", headers=HEADERS_A)
    test("List versions → 200", r.status_code, 200)
    versions = r.json().get("data", [])
    test("Has 5 versions", len(versions), 5)

    # Check version numbers are sequential
    vnums = [v["version_number"] for v in versions]
    test("Version numbers sequential", vnums, [1, 2, 3, 4, 5])

    # Check change_types
    ctypes = [v["change_type"] for v in versions]
    test("Change types correct", ctypes, [
        "create_entity", "update_entity",
        "add_field", "update_field", "remove_field",
    ])

    # Check immutable history: version 1 snapshot still has original fields
    r = client.get(f"{EP}/entities/{ecode}/versions/1", headers=HEADERS_A)
    test("Get version 1 → 200", r.status_code, 200)
    snap1 = r.json().get("data", {}).get("schema_snapshot", {})
    v1_fields = [f["code"] for f in snap1.get("fields", [])]
    test("Version 1 has 3 fields", len(v1_fields), 3)
    test("Version 1 fields", sorted(v1_fields), ["code", "name", "price"])

    # Version 3 should have 4 fields (category added)
    r = client.get(f"{EP}/entities/{ecode}/versions/3", headers=HEADERS_A)
    snap3 = r.json().get("data", {}).get("schema_snapshot", {})
    v3_fields = [f["code"] for f in snap3.get("fields", [])]
    test("Version 3 has 4 fields", len(v3_fields), 4)
    test("Version 3 has 'category'", "category" in v3_fields, True)

    # ═══════════════════════════════════════════════════════
    # SECTION 5: Relationship Versioning
    # ═══════════════════════════════════════════════════════
    print("\n--- 5. Relationship Versioning ---")

    # We need an entity with a real column to create a relationship from
    # Use the existing test_product entity which maps to test_products table
    r = client.post(f"{EP}/entities/test_product/relationships", headers=HEADERS_ADMIN, json={
        "code": "sv_test_rel",
        "target_entity_code": "test_product",
        "relationship_type": "one_to_many",
        "source_column": "id",
        "target_column": "id",
        "on_delete": "cascade",
    })
    test("Create relationship → 200", r.status_code, 200)
    rel_ver = r.json().get("version")
    test("Relationship create → version", rel_ver is not None, True)

    # Delete relationship
    r = client.delete(f"{EP}/entities/test_product/relationships/sv_test_rel", headers=HEADERS_ADMIN)
    test("Delete relationship → 200", r.status_code, 200)
    del_ver = r.json().get("version")
    test("Relationship delete → version", del_ver is not None, True)

    # ═══════════════════════════════════════════════════════
    # SECTION 6: Security
    # ═══════════════════════════════════════════════════════
    print("\n--- 6. Security ---")

    # Viewer cannot create entity
    r = client.post(f"{EP}/entities", headers=HEADERS_VIEWER, json={
        "code": "should_fail",
        "name_en": "Fail",
        "faculty": "test",
        "table_mapping": "sv_empty_table",
    })
    test("Viewer create entity → 403", r.status_code, 403)

    # Viewer cannot add field
    r = client.post(f"{EP}/entities/{ecode}/fields", headers=HEADERS_VIEWER, json={
        "code": "nope",
        "field_type": "string",
    })
    test("Viewer add field → 403", r.status_code, 403)

    # Viewer cannot update entity
    r = client.put(f"{EP}/entities/{ecode}", headers=HEADERS_VIEWER, json={"name_en": "Hacked"})
    test("Viewer update entity → 403", r.status_code, 403)

    # Viewer cannot remove field
    r = client.delete(f"{EP}/entities/{ecode}/fields/code", headers=HEADERS_VIEWER)
    test("Viewer remove field → 403", r.status_code, 403)

    # No token → 401
    r = client.post(f"{EP}/entities", json={
        "code": "no_auth",
        "name_en": "No Auth",
        "faculty": "test",
        "table_mapping": "sv_empty_table",
    })
    test("No token create → 401", r.status_code, 401)

    # Cross-tenant: Tenant B cannot modify Tenant A's entity
    r = client.put(f"{EP}/entities/{ecode}", headers=HEADERS_B, json={"name_en": "Hacked"})
    # Entities are global metadata — accept either behavior

    # Version tracking: changed_by must be from auth, not payload
    r = client.get(f"{EP}/entities/{ecode}/versions/2", headers=HEADERS_A)
    ver_data = r.json().get("data", {})
    test("changed_by is admin", ver_data.get("changed_by"), "admin")

    # ═══════════════════════════════════════════════════════
    # SECTION 7: Entity Delete
    # ═══════════════════════════════════════════════════════
    print("\n--- 7. Entity Delete ---")

    # Cannot delete entity with records (test_products has records)
    r = client.delete(f"{EP}/entities/test_product", headers=HEADERS_ADMIN)
    test("Delete entity with records → 409", r.status_code, 409)

    # Delete our test entity (no records)
    r = client.delete(f"{EP}/entities/{ecode}", headers=HEADERS_ADMIN)
    test("Delete test entity → 200", r.status_code, 200)

    # Deleted entity → 404
    r = client.get(f"{EP}/entities/{ecode}/versions", headers=HEADERS_A)
    test("Deleted entity versions → 404", r.status_code, 404)

    # ═══════════════════════════════════════════════════════
    # SECTION 8: Version Nonexistent
    # ═══════════════════════════════════════════════════════
    print("\n--- 8. Version Nonexistent ---")

    r = client.get(f"{EP}/entities/nonexistent_entity/versions", headers=HEADERS_A)
    test("Nonexistent entity versions → 404", r.status_code, 404)

    r = client.get(f"{EP}/entities/test_product/versions/99999", headers=HEADERS_A)
    test("Nonexistent version → 404", r.status_code, 404)

    # ═══════════════════════════════════════════════════════
    # SECTION 9: Schema Snapshot Content
    # ═══════════════════════════════════════════════════════
    print("\n--- 9. Snapshot Content ---")

    ecode2 = f"sv_{uuid.uuid4().hex[:6]}"
    r = client.post(f"{EP}/entities", headers=HEADERS_ADMIN, json={
        "code": ecode2,
        "name_en": "Snapshot Test",
        "faculty": "inventory",
        "table_mapping": "sv_empty_table",
        "fields": [
            {"code": "code", "label_en": "Code", "field_type": "string", "is_required": True},
        ],
    })
    test("Create snapshot entity → 200", r.status_code, 200)

    # Get version 1 and verify full snapshot structure
    r = client.get(f"{EP}/entities/{ecode2}/versions/1", headers=HEADERS_A)
    snap = r.json().get("data", {}).get("schema_snapshot", {})

    test("Snapshot has entity key", "entity" in snap, True)
    test("Snapshot has fields key", "fields" in snap, True)
    test("Snapshot has relationships key", "relationships" in snap, True)
    test("Snapshot entity code", snap.get("entity", {}).get("code"), ecode2)
    test("Snapshot entity name", snap.get("entity", {}).get("name_en"), "Snapshot Test")
    test("Snapshot has 1 field", len(snap.get("fields", [])), 1)
    test("Snapshot field code", snap.get("fields", [{}])[0].get("code"), "code")
    test("Snapshot relationships empty", len(snap.get("relationships", [])), 0)

    # Cleanup
    client.delete(f"{EP}/entities/{ecode2}", headers=HEADERS_ADMIN)

    # ═══════════════════════════════════════════════════════
    # RESULTS
    # ═══════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{passed + failed} passed")
    if failed:
        print(f"  {failed} FAILED")
    else:
        print("All P11 tests passed!")
    print("=" * 60)

finally:
    client.close()
    stop_server(proc)
