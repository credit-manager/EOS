"""
P20 ADVANCED VALIDATION ENGINE TESTS
======================================
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"

TOKEN_A = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])

HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_V = {"Authorization": f"Bearer {TOKEN_V}"}

passed = 0
failed = 0
entity_id = None

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
    global entity_id
    from database import SessionLocal
    from sqlalchemy import text as sa_text
    db = SessionLocal()
    try:
        db.execute(sa_text("DELETE FROM dbp_validation_rules"))
        db.commit()

        existing = db.execute(sa_text(
            "SELECT id FROM dbp_entities WHERE code='p20_products'"
        )).fetchone()
        if existing:
            entity_id = existing[0]
        else:
            db.execute(sa_text(
                "INSERT INTO dbp_entities (id, code, name_en, faculty, table_mapping) "
                "VALUES (:id, 'p20_products', 'P20 Products', 'test', 'p20_products')"
            ), {"id": "p20_ent"})
            db.commit()
            entity_id = "p20_ent"
    finally:
        db.close()


def test_create_rules(client):
    """Section 1: Create validation rules"""
    print("\n--- 1. Create Rules ---")

    # Required rule
    r = client.post(f"{EP}/validation-rules", headers=HEADERS_A, json={
        "entity_id": entity_id,
        "field_code": "name",
        "rule_type": "required",
        "rule_config": {"message": "Name is required"},
        "name_en": "Name Required",
    })
    test("Create required rule -> 200", r.status_code, 200)
    req_id = r.json()["data"]["id"]

    # Min length rule
    r = client.post(f"{EP}/validation-rules", headers=HEADERS_A, json={
        "entity_id": entity_id,
        "field_code": "name",
        "rule_type": "min_length",
        "rule_config": {"value": 3, "message": "Name must be at least 3 chars"},
    })
    test("Create min_length rule -> 200", r.status_code, 200)

    # Max rule
    r = client.post(f"{EP}/validation-rules", headers=HEADERS_A, json={
        "entity_id": entity_id,
        "field_code": "price",
        "rule_type": "min",
        "rule_config": {"value": 0.01, "message": "Price must be positive"},
    })
    test("Create min rule -> 200", r.status_code, 200)

    # Email rule
    r = client.post(f"{EP}/validation-rules", headers=HEADERS_A, json={
        "entity_id": entity_id,
        "field_code": "email",
        "rule_type": "email",
        "rule_config": {"message": "Invalid email"},
    })
    test("Create email rule -> 200", r.status_code, 200)

    # Match field rule (cross-field)
    r = client.post(f"{EP}/validation-rules", headers=HEADERS_A, json={
        "entity_id": entity_id,
        "field_code": "confirm_email",
        "rule_type": "match_field",
        "rule_config": {"other_field": "email", "message": "Emails must match"},
    })
    test("Create match_field rule -> 200", r.status_code, 200)

    # Enum rule
    r = client.post(f"{EP}/validation-rules", headers=HEADERS_A, json={
        "entity_id": entity_id,
        "field_code": "category",
        "rule_type": "enum",
        "rule_config": {"values": ["electronics", "clothing", "food"], "message": "Invalid category"},
    })
    test("Create enum rule -> 200", r.status_code, 200)

    # List rules
    r = client.get(f"{EP}/validation-rules?entity_id={entity_id}", headers=HEADERS_A)
    test("List rules -> 200", r.status_code, 200)
    test("Has 6 rules", len(r.json()["data"]), 6)

    # Missing fields
    r = client.post(f"{EP}/validation-rules", headers=HEADERS_A, json={
        "entity_id": entity_id,
    })
    test("Missing rule_type -> 400", r.status_code, 400)

    # Invalid type
    r = client.post(f"{EP}/validation-rules", headers=HEADERS_A, json={
        "entity_id": entity_id, "rule_type": "magic",
    })
    test("Invalid rule_type -> 400", r.status_code, 400)


def test_validate_valid(client):
    """Section 2: Validate valid records"""
    print("\n--- 2. Validate Valid Records ---")

    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {
            "name": "Widget Pro",
            "price": 29.99,
            "email": "test@example.com",
            "confirm_email": "test@example.com",
            "category": "electronics",
        },
    })
    test("Valid record -> 200", r.status_code, 200)
    test("Is valid", r.json()["data"]["valid"], True)
    test("No errors", len(r.json()["data"]["errors"]), 0)


def test_validate_required(client):
    """Section 3: Required validation"""
    print("\n--- 3. Required Validation ---")

    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {"price": 10.0},
    })
    test("Missing name -> valid=False", r.json()["data"]["valid"], False)
    errors = r.json()["data"]["errors"]
    name_errors = [e for e in errors if e["field"] == "name"]
    test("Name error present", len(name_errors) > 0, True)


def test_validate_min_length(client):
    """Section 4: Min length validation"""
    print("\n--- 4. Min Length Validation ---")

    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {"name": "ab", "price": 10.0},
    })
    test("Short name -> valid=False", r.json()["data"]["valid"], False)
    errors = r.json()["data"]["errors"]
    ml_errors = [e for e in errors if e["rule"] == "min_length"]
    test("Min length error present", len(ml_errors) > 0, True)


def test_validate_min(client):
    """Section 5: Min value validation"""
    print("\n--- 5. Min Value Validation ---")

    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {"name": "Widget", "price": -5},
    })
    test("Negative price -> valid=False", r.json()["data"]["valid"], False)
    errors = r.json()["data"]["errors"]
    min_errors = [e for e in errors if e["rule"] == "min"]
    test("Min error present", len(min_errors) > 0, True)


def test_validate_email(client):
    """Section 6: Email validation"""
    print("\n--- 6. Email Validation ---")

    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {"name": "Widget", "price": 10, "email": "not-an-email"},
    })
    test("Bad email -> valid=False", r.json()["data"]["valid"], False)
    errors = r.json()["data"]["errors"]
    email_errors = [e for e in errors if e["rule"] == "email"]
    test("Email error present", len(email_errors) > 0, True)

    # Valid email
    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {"name": "Widget", "price": 10, "email": "ok@test.com"},
    })
    test("Valid email -> valid=True", r.json()["data"]["valid"], True)


def test_validate_cross_field(client):
    """Section 7: Cross-field validation"""
    print("\n--- 7. Cross-Field Validation ---")

    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {
            "name": "Widget", "price": 10,
            "email": "test@test.com",
            "confirm_email": "different@test.com",
        },
    })
    test("Mismatched emails -> valid=False", r.json()["data"]["valid"], False)
    errors = r.json()["data"]["errors"]
    match_errors = [e for e in errors if e["rule"] == "match_field"]
    test("Match field error present", len(match_errors) > 0, True)

    # Matching emails
    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {
            "name": "Widget", "price": 10,
            "email": "test@test.com",
            "confirm_email": "test@test.com",
        },
    })
    test("Matched emails -> valid=True", r.json()["data"]["valid"], True)


def test_validate_enum(client):
    """Section 8: Enum validation"""
    print("\n--- 8. Enum Validation ---")

    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {"name": "Widget", "price": 10, "category": "invalid_cat"},
    })
    test("Invalid category -> valid=False", r.json()["data"]["valid"], False)
    errors = r.json()["data"]["errors"]
    enum_errors = [e for e in errors if e["rule"] == "enum"]
    test("Enum error present", len(enum_errors) > 0, True)

    # Valid category
    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {"name": "Widget", "price": 10, "category": "electronics"},
    })
    test("Valid category -> valid=True", r.json()["data"]["valid"], True)


def test_validate_conditional(client):
    """Section 9: Conditional validation"""
    print("\n--- 9. Conditional Validation ---")

    # Create conditional rule: if category == 'food', then name must contain 'food'
    r = client.post(f"{EP}/validation-rules", headers=HEADERS_A, json={
        "entity_id": entity_id,
        "field_code": "name",
        "rule_type": "regex",
        "rule_config": {"pattern": ".*food.*", "message": "Food items must have 'food' in name"},
        "severity": "error",
        "condition": {"type": "field_equals", "field": "category", "value": "food"},
    })
    test("Create conditional rule -> 200", r.status_code, 200)

    # Category is food, name doesn't contain 'food' -> should fail
    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {"name": "Widget", "price": 10, "category": "food"},
    })
    test("Conditional: food item without 'food' -> valid=False", r.json()["data"]["valid"], False)

    # Category is electronics -> conditional rule shouldn't fire
    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_A, json={
        "data": {"name": "Widget", "price": 10, "category": "electronics"},
    })
    test("Conditional: non-food item -> rule skipped", r.json()["data"]["valid"], True)


def test_batch_validation(client):
    """Section 10: Batch validation"""
    print("\n--- 10. Batch Validation ---")

    r = client.post(f"{EP}/validate/p20_products/batch", headers=HEADERS_A, json={
        "records": [
            {"name": "Good Product", "price": 10, "email": "a@b.com", "category": "food", "confirm_email": "a@b.com"},
            {"name": "X", "price": -1, "email": "bad", "category": "invalid"},
            {"name": "Another Good", "price": 25, "email": "c@d.com", "category": "clothing"},
        ],
    })
    test("Batch validate -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Not all valid", data["valid"], False)
    test("3 total", data["total"], 3)
    test("Invalid count >= 1", data["invalid_count"] >= 1, True)
    test("Has per-record results", len(data["results"]), 3)


def test_delete_rule(client):
    """Section 11: Delete rule"""
    print("\n--- 11. Delete Rule ---")

    # Get first rule
    r = client.get(f"{EP}/validation-rules?entity_id={entity_id}", headers=HEADERS_A)
    rules = r.json()["data"]
    if rules:
        rule_id = rules[0]["id"]
        r = client.delete(f"{EP}/validation-rules/{rule_id}", headers=HEADERS_A)
        test("Delete rule -> 200", r.status_code, 200)

        # Verify deleted
        r = client.get(f"{EP}/validation-rules?entity_id={entity_id}", headers=HEADERS_A)
        remaining_ids = [rl["id"] for rl in r.json()["data"]]
        test("Rule removed from list", rule_id not in remaining_ids, True)

    # Delete nonexistent
    r = client.delete(f"{EP}/validation-rules/nonexistent", headers=HEADERS_A)
    test("Delete nonexistent -> 404", r.status_code, 404)


def test_rbac(client):
    """Section 12: RBAC"""
    print("\n--- 12. RBAC ---")

    r = client.get(f"{EP}/validation-rules?entity_id={entity_id}", headers=HEADERS_V)
    test("Viewer list rules -> 200", r.status_code, 200)

    r = client.post(f"{EP}/validate/p20_products", headers=HEADERS_V, json={"data": {}})
    test("Viewer validate -> 200", r.status_code, 200)


# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("P20 ADVANCED VALIDATION ENGINE TESTS")
    print("=" * 60)

    setup()

    print("\nStarting server...")
    proc = start_server()
    client = httpx.Client(base_url=BASE, timeout=30)

    try:
        test_create_rules(client)
        test_validate_valid(client)
        test_validate_required(client)
        test_validate_min_length(client)
        test_validate_min(client)
        test_validate_email(client)
        test_validate_cross_field(client)
        test_validate_enum(client)
        test_validate_conditional(client)
        test_batch_validation(client)
        test_delete_rule(client)
        test_rbac(client)
    finally:
        client.close()
        stop_server(proc)

    print("\n" + "=" * 60)
    print(f"P20 RESULTS: {passed}/{passed + failed} PASSED, {failed} FAILED")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
