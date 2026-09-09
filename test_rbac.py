"""
RBAC Authorization Test for Dynamic CRUD
Tests permission matrix for Dynamic Viewer/Operator/Manager roles
"""
import subprocess
import time
import sys
import httpx
import os

BASE = "http://localhost:8000/api/v1"
ENTITY = "test_product"
TABLE = "test_products"


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


def test_rbac():
    print("=" * 60)
    print("RBAC AUTHORIZATION TEST FOR DYNAMIC CRUD")
    print("=" * 60)
    
    results = []
    
    # Test 1: No token -> 200 (schema is public)
    print("\n--- Test 1: No token -> 200 (schema public) ---")
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema")
    passed = r.status_code == 200
    results.append({"name": "No token", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Status: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Test 2: Invalid token -> 401
    print("\n--- Test 2: Invalid token -> 401 ---")
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema",
                  headers={"Authorization": "Bearer invalid-token"})
    passed = r.status_code == 401
    results.append({"name": "Invalid token", "status": r.status_code, "expected": 401, "passed": passed})
    print(f"  Status: {r.status_code} (expected 401) {'PASS' if passed else 'FAIL'}")
    
    # Test 3: Admin role -> all allowed
    print("\n--- Test 3: Admin role -> all allowed ---")
    admin_token = get_token(["admin"])
    h = {"Authorization": f"Bearer {admin_token}"}
    
    # Admin READ
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 200
    results.append({"name": "Admin READ", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Admin READ: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Admin CREATE
    import uuid
    admin_code = f"ADM-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": admin_code, "name": "Admin Record RBAC", "name_ar": "Admin Record RBAC", "tenant_id": "tenant_a"},
                   headers=h)
    passed = r.status_code == 200
    results.append({"name": "Admin CREATE", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Admin CREATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    if not passed:
        print(f"    Detail: {r.status_code} - {r.json()}")
    
    # Test 4: Dynamic Viewer role
    print("\n--- Test 4: Dynamic Viewer role ---")
    viewer_token = get_token(["dynamic_viewer"])
    h = {"Authorization": f"Bearer {viewer_token}"}
    
    # Viewer READ
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 200
    results.append({"name": "Viewer READ", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Viewer READ: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Viewer CREATE -> 403
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": "VIEWER-001", "name": "Viewer Record", "name_ar": "Viewer Record"},
                   headers=h)
    passed = r.status_code == 403
    results.append({"name": "Viewer CREATE", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  Viewer CREATE: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Viewer UPDATE -> 403
    r = httpx.put(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id",
                  json={"name": "Updated"},
                  headers=h)
    passed = r.status_code == 403
    results.append({"name": "Viewer UPDATE", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  Viewer UPDATE: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Viewer DELETE -> 403
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id", headers=h)
    passed = r.status_code == 403
    results.append({"name": "Viewer DELETE", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  Viewer DELETE: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Test 5: Dynamic Operator role
    print("\n--- Test 5: Dynamic Operator role ---")
    operator_token = get_token(["dynamic_operator"])
    h = {"Authorization": f"Bearer {operator_token}"}
    
    # Operator READ
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 200
    results.append({"name": "Operator READ", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Operator READ: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Operator CREATE
    operator_code = f"OPR-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": operator_code, "name": "Operator Record RBAC", "name_ar": "Operator Record RBAC", "tenant_id": "tenant_a"},
                   headers=h)
    passed = r.status_code == 200
    results.append({"name": "Operator CREATE", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Operator CREATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    if not passed:
        print(f"    Detail: {r.status_code} - {r.json()}")
    
    # Operator UPDATE
    r = httpx.put(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id",
                  json={"name": "Updated"},
                  headers=h)
    passed = r.status_code == 404  # Not found, but not 403
    results.append({"name": "Operator UPDATE", "status": r.status_code, "expected": 404, "passed": passed})
    print(f"  Operator UPDATE: {r.status_code} (expected 404) {'PASS' if passed else 'FAIL'}")
    
    # Operator DELETE -> 403
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id", headers=h)
    passed = r.status_code == 403
    results.append({"name": "Operator DELETE", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  Operator DELETE: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
    # Test 6: Dynamic Manager role
    print("\n--- Test 6: Dynamic Manager role ---")
    manager_token = get_token(["dynamic_manager"])
    h = {"Authorization": f"Bearer {manager_token}"}
    
    # Manager READ
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 200
    results.append({"name": "Manager READ", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Manager READ: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    
    # Manager CREATE
    manager_code = f"MGR-{uuid.uuid4().hex[:6]}"
    r = httpx.post(f"{BASE}/dynamic/entities/{ENTITY}/records",
                   json={"code": manager_code, "name": "Manager Record RBAC", "name_ar": "Manager Record RBAC", "tenant_id": "tenant_a"},
                   headers=h)
    passed = r.status_code == 200
    results.append({"name": "Manager CREATE", "status": r.status_code, "expected": 200, "passed": passed})
    print(f"  Manager CREATE: {r.status_code} (expected 200) {'PASS' if passed else 'FAIL'}")
    if not passed:
        print(f"    Detail: {r.status_code} - {r.json()}")
    
    # Manager UPDATE
    r = httpx.put(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id",
                  json={"name": "Updated"},
                  headers=h)
    passed = r.status_code == 404  # Not found, but not 403
    results.append({"name": "Manager UPDATE", "status": r.status_code, "expected": 404, "passed": passed})
    print(f"  Manager UPDATE: {r.status_code} (expected 404) {'PASS' if passed else 'FAIL'}")
    
    # Manager DELETE
    r = httpx.delete(f"{BASE}/dynamic/entities/{ENTITY}/records/test-id", headers=h)
    passed = r.status_code == 404  # Not found, but not 403
    results.append({"name": "Manager DELETE", "status": r.status_code, "expected": 404, "passed": passed})
    print(f"  Manager DELETE: {r.status_code} (expected 404) {'PASS' if passed else 'FAIL'}")
    
    # Test 7: No role -> 403
    print("\n--- Test 7: No role -> 403 ---")
    no_role_token = get_token(["user"])
    h = {"Authorization": f"Bearer {no_role_token}"}
    
    r = httpx.get(f"{BASE}/dynamic/entities/{ENTITY}/schema", headers=h)
    passed = r.status_code == 403
    results.append({"name": "No role READ", "status": r.status_code, "expected": 403, "passed": passed})
    print(f"  No role READ: {r.status_code} (expected 403) {'PASS' if passed else 'FAIL'}")
    
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
                print(f"  - {r['name']}: got {r['status']}, expected {r['expected']}")
    
    return failed_count == 0


if __name__ == "__main__":
    proc = start_server()
    try:
        success = test_rbac()
        sys.exit(0 if success else 1)
    finally:
        stop_server(proc)
