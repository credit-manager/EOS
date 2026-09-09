"""
RBAC Authorization Test — All Modules
Tests: (1) no-role user gets 403, (2) after role assignment user gets 200, (3) admin always gets 200
"""
import asyncio
import httpx
import uuid

BASE = "http://localhost:8001/api/v1"


async def test_module_permissions(module_name: str, endpoints: list):
    uid = str(uuid.uuid4())[:8]

    async with httpx.AsyncClient(follow_redirects=True) as c:
        # 1. Register admin
        r = await c.post(f"{BASE}/auth/register", json={
            "email": f"admin-{module_name}-{uid}@example.com",
            "password": "Admin123!",
            "company_name": f"Co {module_name} {uid}",
            "company_name_ar": f"test {uid}",
            "industry": "technology",
        })
        if r.status_code != 200:
            print(f"[{module_name}] FAIL register: {r.status_code} {r.text[:200]}")
            return []
        tenant_id = r.json()["tenant_id"]
        print(f"[{module_name}] 1. Admin registered: tenant={tenant_id}")

        # 2. Login admin
        r = await c.post(f"{BASE}/auth/login", json={
            "email": f"admin-{module_name}-{uid}@example.com",
            "password": "Admin123!",
            "tenant_id": tenant_id,
        })
        if r.status_code != 200:
            print(f"[{module_name}] FAIL login: {r.status_code} {r.text[:200]}")
            return []
        admin_token = r.json()["access_token"]
        admin_h = {"Authorization": f"Bearer {admin_token}"}
        print(f"[{module_name}] 2. Admin logged in")

        # 3. Create test data as admin
        for ep in endpoints:
            if ep.get("admin_create"):
                r = await c.post(f"{BASE}/{tenant_id}{ep['admin_create']['url']}",
                                 json=ep["admin_create"]["data"], headers=admin_h)
                print(f"[{module_name}] 3. Admin create: {ep['name']} -> {r.status_code}")

        # 4. Invite clerk
        r = await c.post(f"{BASE}/auth/invite", json={
            "email": f"clerk-{module_name}-{uid}@example.com",
            "password": "Clerk123!",
            "first_name": "Staff",
            "last_name": "Clerk",
        }, headers=admin_h)
        if r.status_code != 200:
            print(f"[{module_name}] FAIL invite: {r.status_code} {r.text[:200]}")
            return []
        print(f"[{module_name}] 4. Invite sent")

        # 5. Login clerk
        r = await c.post(f"{BASE}/auth/login", json={
            "email": f"clerk-{module_name}-{uid}@example.com",
            "password": "Clerk123!",
            "tenant_id": tenant_id,
        })
        if r.status_code != 200:
            print(f"[{module_name}] FAIL clerk login: {r.status_code} {r.text[:200]}")
            return []
        clerk_token = r.json()["access_token"]
        clerk_h = {"Authorization": f"Bearer {clerk_token}"}
        print(f"[{module_name}] 5. Clerk logged in (no role yet)")

        # 6. BEFORE role assignment: clerk tries all endpoints (should get 403)
        results = []
        for ep in endpoints:
            url = f"{BASE}/{tenant_id}{ep['url']}"
            if ep["method"] == "GET":
                r = await c.get(url, headers=clerk_h)
            else:
                r = await c.post(url, json=ep.get("data", {}), headers=clerk_h)
            passed = r.status_code == 403
            results.append({"name": f"NoRole {ep['name']}", "status": r.status_code, "expected": 403, "passed": passed})
            mark = "PASS" if passed else "FAIL"
            print(f"[{module_name}] 6. NoRole {ep['name']}: {r.status_code} (expect 403) [{mark}]")

        # 7. Assign Sales Clerk role to clerk
        r = await c.get(f"{BASE}/auth/me", headers=clerk_h)
        clerk_user_id = r.json()["id"]
        r = await c.get(f"{BASE}/auth/roles", headers=admin_h)
        roles = r.json()
        sales_role = next((role for role in roles if role["name"] == "Sales Clerk"), None)
        if sales_role:
            r = await c.post(f"{BASE}/auth/users/{clerk_user_id}/role",
                             json={"role_id": sales_role["id"]}, headers=admin_h)
            print(f"[{module_name}] 7. Sales Clerk role assigned: {r.status_code}")
        else:
            print(f"[{module_name}] 7. Sales Clerk role not found!")

        # 8. AFTER role assignment: clerk tries all endpoints
        for ep in endpoints:
            url = f"{BASE}/{tenant_id}{ep['url']}"
            if ep["method"] == "GET":
                r = await c.get(url, headers=clerk_h)
            else:
                r = await c.post(url, json=ep.get("data", {}), headers=clerk_h)

            expected = ep.get("after_role_expected", 200)
            passed = r.status_code == expected
            results.append({"name": f"WithRole {ep['name']}", "status": r.status_code, "expected": expected, "passed": passed})
            mark = "PASS" if passed else "FAIL"
            print(f"[{module_name}] 8. WithRole {ep['name']}: {r.status_code} (expect {expected}) [{mark}]")

        # 9. Admin always gets 200
        for ep in endpoints:
            url = f"{BASE}/{tenant_id}{ep['url']}"
            if ep["method"] == "GET":
                r = await c.get(url, headers=admin_h)
            else:
                r = await c.post(url, json=ep.get("data", {}), headers=admin_h)
            passed = r.status_code == 200
            results.append({"name": f"Admin {ep['name']}", "status": r.status_code, "expected": 200, "passed": passed})
            mark = "PASS" if passed else "FAIL"
            print(f"[{module_name}] 9. Admin {ep['name']}: {r.status_code} (expect 200) [{mark}]")

        return results


async def main():
    all_results = []

    # Sales Clerk role has: sales:read, sales:create
    # So after assignment: sales=200, accounting/inventory/hr=403

    # ─── ACCOUNTING ──────────────────────────────────
    print("\n=== ACCOUNTING MODULE ===")
    uid_a = uuid.uuid4().hex[:4]
    all_results.extend(await test_module_permissions("accounting", [
        {"name": "List accounts", "method": "GET", "url": "/accounting/accounts",
         "admin_create": {"url": "/accounting/accounts",
                          "data": {"code": f"6{uid_a}", "name": "Test Cash", "name_ar": "test",
                                   "account_type": "asset", "normal_balance": "debit"}},
         "after_role_expected": 403},
        {"name": "Create account", "method": "POST", "url": "/accounting/accounts",
         "data": {"code": f"7{uid_a}", "name": "Test Payable", "name_ar": "test",
                  "account_type": "liability", "normal_balance": "credit"},
         "after_role_expected": 403},
    ]))

    # ─── INVENTORY ───────────────────────────────────
    print("\n=== INVENTORY MODULE ===")
    uid_i = uuid.uuid4().hex[:4]
    all_results.extend(await test_module_permissions("inventory", [
        {"name": "List products", "method": "GET", "url": "/inventory/products",
         "admin_create": {"url": "/inventory/products",
                          "data": {"sku": f"SKU-{uid_i}-1", "name": "Test", "name_ar": "test",
                                   "unit_price": 100, "cost_price": 80, "currency": "EGP"}},
         "after_role_expected": 403},
        {"name": "Create product", "method": "POST", "url": "/inventory/products",
         "data": {"sku": f"SKU-{uid_i}-2", "name": "Test2", "name_ar": "test",
                  "unit_price": 200, "cost_price": 150, "currency": "EGP"},
         "after_role_expected": 403},
    ]))

    # ─── HR ──────────────────────────────────────────
    print("\n=== HR MODULE ===")
    uid_h = uuid.uuid4().hex[:4]
    all_results.extend(await test_module_permissions("hr", [
        {"name": "List employees", "method": "GET", "url": "/hr/employees",
         "admin_create": {"url": "/hr/employees",
                          "data": {"employee_id": f"EMP-{uid_h}-1", "first_name": "Ahmed",
                                   "last_name": "Ali", "email": f"ahmed-{uid_h}@test.com",
                                   "hire_date": "2025-01-01", "salary": 10000, "currency": "EGP"}},
         "after_role_expected": 403},
        {"name": "Create employee", "method": "POST", "url": "/hr/employees",
         "data": {"employee_id": f"EMP-{uid_h}-2", "first_name": "Sara", "last_name": "Hassan",
                  "email": f"sara-{uid_h}@test.com", "hire_date": "2025-06-01",
                  "salary": 12000, "currency": "EGP"},
         "after_role_expected": 403},
    ]))

    # ─── SALES ───────────────────────────────────────
    print("\n=== SALES MODULE ===")
    uid_s = uuid.uuid4().hex[:4]
    all_results.extend(await test_module_permissions("sales", [
        {"name": "List customers", "method": "GET", "url": "/sales/customers",
         "admin_create": {"url": "/sales/customers",
                          "data": {"name": "Test Customer", "name_ar": "test",
                                   "type": "individual", "email": f"cust-{uid_s}@test.com"}},
         "after_role_expected": 200},
        {"name": "Create customer", "method": "POST", "url": "/sales/customers",
         "data": {"name": "Customer 2", "name_ar": "test",
                  "type": "company", "email": f"cust2-{uid_s}@test.com"},
         "after_role_expected": 200},
    ]))

    # ─── SUMMARY ─────────────────────────────────────
    print("\n" + "=" * 60)
    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    failed = total - passed
    print(f"TOTAL: {passed}/{total} passed")
    if failed:
        print("FAILED:")
        for r in all_results:
            if not r["passed"]:
                print(f"  - {r['name']}: got {r['status']}, expected {r['expected']}")
    else:
        print("ALL TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
