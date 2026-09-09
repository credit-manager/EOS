"""
P13 Advanced Security & Governance TESTS
Full verification matrix for field-level security, row-level security,
sensitive data masking, input validation, webhook security, audit hardening.
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
TOKEN_A = create_test_token("tenant_a", user_id="user_a", roles=["dynamic_manager"])
TOKEN_VIEWER = create_test_token("tenant_a", roles=["dynamic_viewer"])
TOKEN_B = create_test_token("tenant_b", user_id="user_b", roles=["dynamic_manager"])
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
db_setup.execute(sa_text("DROP TABLE IF EXISTS sec_test_table"))
db_setup.execute(sa_text("""
    CREATE TABLE sec_test_table (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36),
        branch_id VARCHAR(36),
        code VARCHAR(100),
        name VARCHAR(255),
        email VARCHAR(255),
        password VARCHAR(255),
        salary NUMERIC,
        national_id VARCHAR(50),
        deleted_at TIMESTAMPTZ,
        deleted_by VARCHAR(100)
    )
"""))
db_setup.commit()
db_setup.close()

try:
    print("=" * 60)
    print("P13 ADVANCED SECURITY & GOVERNANCE TESTS")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════
    # SECTION 1: Security Headers & Request ID
    # ═══════════════════════════════════════════════════════
    print("\n--- 1. Security Headers & Request ID ---")

    r = client.get(f"{EP}/entities", headers=HEADERS_A)
    test("X-Content-Type-Options nosniff", r.headers.get("x-content-type-options"), "nosniff")
    test("X-Frame-Options DENY", r.headers.get("x-frame-options"), "DENY")
    test("Referrer-Policy present", "referrer-policy" in r.headers, True)
    test("CSP frame-ancestors none", r.headers.get("content-security-policy"), "frame-ancestors 'none'")
    test("X-Request-ID present", "x-request-id" in r.headers, True)
    test("Cache-Control no-store", "no-store" in r.headers.get("cache-control", ""), True)

    # Custom request ID echoed
    r = client.get(f"{EP}/entities", headers={**HEADERS_A, "X-Request-ID": "test-corr-123"})
    test("Custom X-Request-ID echoed", r.headers.get("x-request-id"), "test-corr-123")

    # ═══════════════════════════════════════════════════════
    # SECTION 2: Field-Level Security Setup
    # ═══════════════════════════════════════════════════════
    print("\n--- 2. Field-Level Security ---")

    ecode = f"sec_{uuid.uuid4().hex[:6]}"
    r = client.post(f"{EP}/entities", headers=HEADERS_ADMIN, json={
        "code": ecode,
        "name_en": "Security Test Entity",
        "faculty": "inventory",
        "table_mapping": "sec_test_table",
        "fields": [
            {"code": "code", "label_en": "Code", "field_type": "string", "is_required": True},
            {"code": "name", "label_en": "Name", "field_type": "string", "is_required": True},
            {"code": "email", "label_en": "Email", "field_type": "string"},
            {"code": "password", "label_en": "Password", "field_type": "string"},
            {"code": "salary", "label_en": "Salary", "field_type": "number"},
            {"code": "national_id", "label_en": "National ID", "field_type": "string"},
        ],
    })
    test("Create entity -> 200", r.status_code, 200)

    # Get field security state
    r = client.get(f"{EP}/entities/{ecode}/security/fields", headers=HEADERS_A)
    test("Get field security -> 200", r.status_code, 200)

    # Mark password + national_id as sensitive
    r = client.put(f"{EP}/entities/{ecode}/security/fields/password", headers=HEADERS_ADMIN, json={
        "is_sensitive": True,
        "writable_roles": ["dynamic_manager"],
    })
    test("Mark password sensitive -> 200", r.status_code, 200)

    r = client.put(f"{EP}/entities/{ecode}/security/fields/national_id", headers=HEADERS_ADMIN, json={
        "is_sensitive": True,
    })
    test("Mark national_id sensitive -> 200", r.status_code, 200)

    # Mark salary as restricted visibility (managers only)
    r = client.put(f"{EP}/entities/{ecode}/security/fields/salary", headers=HEADERS_ADMIN, json={
        "visible_roles": ["dynamic_manager"],
    })
    test("Set salary visible_roles -> 200", r.status_code, 200)

    # ═══════════════════════════════════════════════════════
    # SECTION 3: Field Write Protection
    # ═══════════════════════════════════════════════════════
    print("\n--- 3. Field Write Protection ---")

    # Mark email as read-only for viewers
    r = client.put(f"{EP}/entities/{ecode}/security/fields/email", headers=HEADERS_ADMIN, json={
        "writable_roles": ["dynamic_manager"],
    })
    test("Set email writable_roles -> 200", r.status_code, 200)

    # Create record as admin (can write everything)
    r = client.post(f"{EP}/entities/{ecode}/records", headers=HEADERS_ADMIN, json={
        "code": "SEC001",
        "name": "Sec User",
        "email": "admin@test.com",
        "password": "secret123",
        "salary": 50000,
        "national_id": "EG-12345",
    })
    test("Admin create record -> 200", r.status_code, 200)
    sec_rec_id = r.json().get("id")

    # Verify field security info endpoint works
    r = client.get(f"{EP}/entities/{ecode}/security/fields", headers=HEADERS_A)
    test("Field security list -> 200", r.status_code, 200)
    fields_data = r.json().get("data", [])
    pwd_field = next((f for f in fields_data if f["code"] == "password"), None)
    if pwd_field:
        test("Password is_sensitive=true", pwd_field.get("is_sensitive"), True)

    # ═══════════════════════════════════════════════════════
    # SECTION 4: Row-Level Security
    # ═══════════════════════════════════════════════════════
    print("\n--- 4. Row-Level Security ---")

    # Create records in different branches
    r = client.post(f"{EP}/entities/{ecode}/records", headers=HEADERS_A, json={
        "code": "SEC002",
        "name": "Branch A User",
        "branch_id": "branch_a",
    })
    test("Create branch_a record -> 200", r.status_code, 200)

    r = client.post(f"{EP}/entities/{ecode}/records", headers=HEADERS_A, json={
        "code": "SEC003",
        "name": "Branch B User",
        "branch_id": "branch_b",
    })
    test("Create branch_b record -> 200", r.status_code, 200)

    # Create a row rule: filter by branch_id = user's branch
    r = client.post(f"{EP}/entities/{ecode}/security/rows", headers=HEADERS_ADMIN, json={
        "filter_column": "branch_id",
        "filter_type": "equals",
        "filter_value": None,
        "allowed_roles": ["dynamic_viewer"],
        "priority": 1,
    })
    test("Create row rule -> 200", r.status_code, 200)
    row_rule_id = r.json().get("rule_id")

    # List row rules
    r = client.get(f"{EP}/entities/{ecode}/security/rows", headers=HEADERS_A)
    test("List row rules -> 200", r.status_code, 200)
    rules = r.json().get("data", [])
    test("Row rule in list", len(rules) >= 1, True)

    # Delete row rule
    r = client.delete(f"{EP}/entities/{ecode}/security/rows/{row_rule_id}", headers=HEADERS_ADMIN)
    test("Delete row rule -> 200", r.status_code, 200)

    # ═══════════════════════════════════════════════════════
    # SECTION 5: Sensitive Data Audit Redaction
    # ═══════════════════════════════════════════════════════
    print("\n--- 5. Audit Redaction ---")

    from core.audit import _redact_values
    raw = {"name": "John", "password": "secret123", "email": "j@x.com", "token": "abc"}
    redacted = _redact_values(raw)
    test("Redact password", redacted.get("password"), "***REDACTED***")
    test("Redact token", redacted.get("token"), "***REDACTED***")
    test("Keep name", redacted.get("name"), "John")
    test("Keep email", redacted.get("email"), "j@x.com")

    nested = {"old": {"password": "old_pass", "name": "x"}, "new": {"password": "new_pass"}}
    red_nested = _redact_values(nested)
    test("Nested password redacted", red_nested["old"]["password"], "***REDACTED***")
    test("Nested name kept", red_nested["old"]["name"], "x")

    # ═══════════════════════════════════════════════════════
    # SECTION 6: Correlation IDs
    # ═══════════════════════════════════════════════════════
    print("\n--- 6. Correlation IDs ---")

    from core.audit import set_request_id, get_request_id
    set_request_id("test-corr-001")
    test("ContextVar set", get_request_id(), "test-corr-001")
    set_request_id(None)
    test("ContextVar cleared", get_request_id(), None)

    # ═══════════════════════════════════════════════════════
    # SECTION 7: Webhook Tenant Isolation Fix
    # ═══════════════════════════════════════════════════════
    print("\n--- 7. Webhook Tenant Isolation ---")

    # Create webhook as tenant_a
    wh_code = f"wh_{uuid.uuid4().hex[:6]}"
    r = client.post(f"{EP}/webhooks", headers=HEADERS_ADMIN, json={
        "code": wh_code,
        "target_url": "https://example.com/hook",
        "entity_code": ecode,
        "event_types": ["*"],
    })
    test("Create webhook tenant_a -> 200", r.status_code, 200)

    # Create event via record creation
    r = client.post(f"{EP}/entities/{ecode}/records", headers=HEADERS_A, json={
        "code": "EVT_SEC",
        "name": "Event Security Test",
    })
    test("Create record for event -> 200", r.status_code, 200)

    # Tenant_a can see events
    r = client.get(f"{EP}/events", headers=HEADERS_A, params={"limit": 5})
    test("Tenant_a sees events -> 200", r.status_code, 200)
    evts_a = r.json().get("data", [])

    # Tenant_b sees ONLY their events (tenant leak fixed)
    r = client.get(f"{EP}/events", headers=HEADERS_B, params={"limit": 5})
    test("Tenant_b sees events -> 200", r.status_code, 200)
    evts_b = r.json().get("data", [])

    # tenant_a events should not appear in tenant_b's view
    tenant_a_ids = {e["id"] for e in evts_a}
    tenant_b_ids = {e["id"] for e in evts_b}
    overlap = tenant_a_ids & tenant_b_ids
    test("No cross-tenant event leak", len(overlap), 0)

    # Nonexistent event returns 404 (not cross-tenant access)
    r = client.get(f"{EP}/events/{uuid.uuid4()}", headers=HEADERS_A)
    test("Nonexistent event -> 404", r.status_code, 404)

    # ═══════════════════════════════════════════════════════
    # SECTION 8: Input Validation Engine
    # ═══════════════════════════════════════════════════════
    print("\n--- 8. Input Validation Engine ---")

    from core.security import InputValidator

    # Type validation
    errors = InputValidator.validate_field("age", "not_a_number", {"field_type": "number"})
    test("String in number field", len(errors) > 0, True)

    errors = InputValidator.validate_field("age", 25, {"field_type": "number"})
    test("Valid number", len(errors), 0)

    # Required validation
    errors = InputValidator.validate_field("name", None, {"field_type": "string", "is_required": True})
    test("Required field null", len(errors) > 0, True)

    # Min/max
    errors = InputValidator.validate_field("score", 200, {"field_type": "number", "ui_config": {"max": 100}})
    test("Max exceeded", len(errors) > 0, True)

    errors = InputValidator.validate_field("score", 50, {"field_type": "number", "ui_config": {"min": 0, "max": 100}})
    test("Valid range", len(errors), 0)

    # String length
    errors = InputValidator.validate_field("code", "ab", {"field_type": "string", "ui_config": {"min_length": 3}})
    test("Min length violated", len(errors) > 0, True)

    # Regex pattern
    errors = InputValidator.validate_field("code", "ABC123", {"field_type": "string", "ui_config": {"pattern": "^[a-z]+$"}})
    test("Pattern mismatch", len(errors) > 0, True)

    errors = InputValidator.validate_field("code", "abc", {"field_type": "string", "ui_config": {"pattern": "^[a-z]+$"}})
    test("Pattern match", len(errors), 0)

    # Enum
    errors = InputValidator.validate_field("status", "invalid", {"field_type": "string", "enum_values": ["active", "inactive"]})
    test("Invalid enum", len(errors) > 0, True)

    # ═══════════════════════════════════════════════════════
    # SECTION 9: Field Security Filtering
    # ═══════════════════════════════════════════════════════
    print("\n--- 9. Field Security Filtering ---")

    from core.security import FieldSecurity, mask_sensitive_data

    field_sec = {
        "password": {"is_sensitive": True, "writable_roles": ["admin"], "visible_roles": []},
        "salary": {"is_sensitive": False, "writable_roles": [], "visible_roles": ["admin"]},
        "email": {"is_sensitive": False, "writable_roles": ["admin"], "visible_roles": []},
    }

    # Write filter
    _, blocked = FieldSecurity.filter_writable_columns(
        {"password": "x", "email": "y", "name": "z"},
        field_sec,
        ["user"],
    )
    test("Password blocked for user", "password" in blocked, True)
    test("Email blocked for user", "email" in blocked, True)

    _, blocked = FieldSecurity.filter_writable_columns(
        {"password": "x", "email": "y"},
        field_sec,
        ["admin"],
    )
    test("Admin can write password", "password" in blocked, False)

    # Visible filter
    data = {"password": "secret", "salary": 50000, "name": "John"}
    filtered = FieldSecurity.filter_visible_columns(data, field_sec, ["user"], is_admin=False)
    test("Salary restricted for user", filtered.get("salary"), "***RESTRICTED***")

    filtered = FieldSecurity.filter_visible_columns(data, field_sec, ["admin"], is_admin=True)
    test("Admin sees salary", filtered.get("salary"), 50000)

    # Masking
    masked = mask_sensitive_data({"password": "secret", "name": "John"}, field_sec)
    test("Password masked", masked["password"], "***REDACTED***")
    test("Name kept", masked["name"], "John")

    # ═══════════════════════════════════════════════════════
    # SECTION 10: RBAC on Security Endpoints
    # ═══════════════════════════════════════════════════════
    print("\n--- 10. Security Endpoint RBAC ---")

    # Viewer can read field security
    r = client.get(f"{EP}/entities/{ecode}/security/fields", headers=HEADERS_VIEWER)
    test("Viewer read field security -> 200", r.status_code, 200)

    # Viewer cannot update field security
    r = client.put(f"{EP}/entities/{ecode}/security/fields/name", headers=HEADERS_VIEWER, json={
        "is_sensitive": True,
    })
    test("Viewer update field security -> 403", r.status_code, 403)

    # Viewer cannot create row rule
    r = client.post(f"{EP}/entities/{ecode}/security/rows", headers=HEADERS_VIEWER, json={
        "filter_column": "branch_id",
        "filter_type": "equals",
    })
    test("Viewer create row rule -> 403", r.status_code, 403)

    # ═══════════════════════════════════════════════════════
    # SECTION 11: Nonexistent entity edge cases
    # ═══════════════════════════════════════════════════════
    print("\n--- 11. Edge Cases ---")

    r = client.get(f"{EP}/entities/nonexistent/security/fields", headers=HEADERS_A)
    test("Nonexistent entity fields -> 404", r.status_code, 404)

    r = client.put(f"{EP}/entities/nonexistent/security/fields/x", headers=HEADERS_ADMIN, json={
        "is_sensitive": True,
    })
    test("Nonexistent entity update -> 404", r.status_code, 404)

    r = client.get(f"{EP}/entities/nonexistent/security/rows", headers=HEADERS_A)
    test("Nonexistent entity rows -> 404", r.status_code, 404)

    # ═══════════════════════════════════════════════════════
    # SECTION 12: Body Size Limit
    # ═══════════════════════════════════════════════════════
    print("\n--- 12. Body Size Limit ---")

    # Normal request passes
    r = client.get(f"{EP}/entities/{ecode}/schema", headers=HEADERS_A)
    test("Normal request -> 200", r.status_code, 200)

    # ═══════════════════════════════════════════════════════
    # RESULTS
    # ═══════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"P13 RESULTS: {passed}/{total} PASSED, {failed} FAILED")
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
