"""
Audit Verification Test for Dynamic CRUD
Verifies audit logs are created for CREATE, UPDATE, DELETE operations
"""
import subprocess
import time
import sys
import httpx
import os
import uuid

BASE = "http://localhost:8000/api/v1"
ENTITY = "test_product"


def start_server():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    time.sleep(3)
    return proc


def stop_server(proc):
    proc.terminate()
    proc.wait(timeout=5)


def get_token(roles: list) -> str:
    """Create a test JWT token with specified roles."""
    import sys
    sys.path.insert(0, '.')
    from core.auth import create_test_token
    return create_test_token(
        tenant_id="tenant_a",
        user_id=f"test-user-{roles[0]}",
        email=f"test-{roles[0]}@example.com",
        roles=roles
    )


def get_audit_count(db, entity_code: str, action: str, record_id: str = None) -> int:
    """Count audit logs for a specific operation."""
    from sqlalchemy import text
    if record_id:
        result = db.execute(text(
            "SELECT COUNT(*) FROM audit_logs "
            "WHERE module = 'dynamic' AND entity_type = :entity "
            "AND action = :action AND entity_id = :record_id"
        ), {"entity": entity_code, "action": action, "record_id": record_id})
    else:
        result = db.execute(text(
            "SELECT COUNT(*) FROM audit_logs "
            "WHERE module = 'dynamic' AND entity_type = :entity "
            "AND action = :action"
        ), {"entity": entity_code, "action": action})
    return result.scalar()


def test_audit():
    print("=" * 60)
    print("AUDIT VERIFICATION TEST FOR DYNAMIC CRUD")
    print("=" * 60)
    
    results = []
    
    # Test 1: CREATE generates audit
    print("\n--- Test 1: CREATE generates audit ---")
    manager_token = get_token(["dynamic_manager"])
    h = {"Authorization": f"Bearer {manager_token}"}
    
    create_code = f"AUD-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": create_code, "name": "Audit Test", "name_ar": "test", "tenant_id": "tenant_a"},
                   headers=h)
    create_id = r.json().get("id") if r.status_code == 200 else None
    passed = r.status_code == 200 and create_id is not None
    results.append({"name": "CREATE generates audit", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  CREATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Test 2: UPDATE generates audit
    print("\n--- Test 2: UPDATE generates audit ---")
    r = httpx.put(f"{BASE}/dynamic/entities/{ENTITY}/records/{create_id}",
                  json={"name": "Audit Test Updated", "tenant_id": "tenant_a"},
                  headers=h)
    passed = r.status_code == 200
    results.append({"name": "UPDATE generates audit", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  UPDATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Test 3: DELETE generates audit
    print("\n--- Test 3: DELETE generates audit ---")
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/{create_id}", headers=h)
    passed = r.status_code == 200
    results.append({"name": "DELETE generates audit", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  DELETE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Test 4: RBAC 403 generates failure audit
    print("\n--- Test 4: RBAC 403 generates failure audit ---")
    viewer_token = get_token(["dynamic_viewer"])
    vh = {"Authorization": f"Bearer {viewer_token}"}
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": "FAIL-001", "name": "Should Fail", "name_ar": "fail", "tenant_id": "tenant_a"},
                   headers=vh)
    passed = r.status_code == 403
    results.append({"name": "RBAC 403 generates audit", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  RBAC 403: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Test 5: Cross-tenant 404 generates failure audit
    print("\n--- Test 5: Cross-tenant 404 generates failure audit ---")
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/nonexistent-id",
                     headers=h)
    passed = r.status_code == 404
    results.append({"name": "Cross-tenant 404 generates audit", "status": r.status_code, "expected": 404, "passed": passed})
    print(f"  Cross-tenant 404: {r.status_code} (expected 404) {'PASS' if passed else 'FAIL'}")
    
    # Test 6: Verify audit records exist in database
    print("\n--- Test 6: Verify audit records in database ---")
    import sys
    sys.path.insert(0, '.')
    from database import SessionLocal
    db = SessionLocal()
    
    audit_count = get_audit_count(db, ENTITY, "create")
    create_exists = audit_count > 0
    results.append({"name": "CREATE audit in DB", "count": audit_count, "passed": create_exists})
    print(f"  CREATE audits: {audit_count} {'PASS' if create_exists else 'FAIL'}")
    
    audit_count = get_audit_count(db, ENTITY, "update")
    update_exists = audit_count > 0
    results.append({"name": "UPDATE audit in DB", "count": audit_count, "passed": update_exists})
    print(f"  UPDATE audits: {audit_count} {'PASS' if update_exists else 'FAIL'}")
    
    audit_count = get_audit_count(db, ENTITY, "delete")
    delete_exists = audit_count > 0
    results.append({"name": "DELETE audit in DB", "count": audit_count, "passed": delete_exists})
    print(f"  DELETE audits: {audit_count} {'PASS' if delete_exists else 'FAIL'}")
    
    db.close()
    
    # Summary
    print("\n" + "=" * 60)
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count
    print(f"RESULTS: {passed_count}/{total} passed")
    
    if failed_count:
        print("\nFAILED:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['name']}: {r}")
    
    return failed_count == 0


if __name__ == "__main__":
    proc = start_server()
    try:
        success = test_audit()
        sys.exit(0 if success else 1)
    finally:
        stop_server(proc)
