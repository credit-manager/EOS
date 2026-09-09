"""
EOS System — RBAC Test Script
Run: python -m app.tests.test_rbac
"""
import asyncio
import httpx
import uuid

BASE_URL = "http://localhost:8001/api/v1"


async def create_test_data():
    """Create test tenant, user, role, and permissions."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        email = f"rbac_test_{uuid.uuid4().hex[:8]}@test.com"

        # 1. Register a test tenant
        company_slug = f"rbac-test-{uuid.uuid4().hex[:8]}"
        register_resp = await client.post("/auth/register", json={
            "company_name": company_slug,
            "company_name_ar": "RBAC Test",
            "email": email,
            "password": "TestPass123!",
            "industry": "technology",
        })
        print(f"[1] Register: {register_resp.status_code}")

        if register_resp.status_code != 200:
            print(f"    FAILED: {register_resp.text}")
            return

        data = register_resp.json()
        tenant_id = data.get("tenant_id")
        user_id = data.get("user_id")
        print(f"    tenant={tenant_id}, user={user_id}")

        # 2. Login to get token
        login_resp = await client.post("/auth/login", json={
            "email": email,
            "password": "TestPass123!",
            "tenant_id": tenant_id,
        })
        print(f"[2] Login: {login_resp.status_code}")

        if login_resp.status_code != 200:
            print(f"    FAILED: {login_resp.text}")
            return

        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create account (admin should work) — unique code per run
        r3 = await client.post(f"/{tenant_id}/accounting/accounts", json={
            "code": f"1{uuid.uuid4().hex[:6]}", "name": "Cash", "name_ar": "Cash",
            "account_type": "asset", "currency": "EGP",
        }, headers=headers)
        print(f"[3] Admin create account: {r3.status_code} - {r3.text[:200]}")

        # 4. Access trial balance
        r4 = await client.get(f"/{tenant_id}/accounting/reports/trial-balance", headers=headers)
        print(f"[4] Admin trial balance: {r4.status_code} - {r4.text[:200]}")

        # 5. No auth = should be 401/403
        r5 = await client.get(f"/{tenant_id}/accounting/accounts")
        print(f"[5] No auth: {r5.status_code} - {r5.text[:200]}")

        # 6. Wrong password = should be 401
        r6 = await client.post("/auth/login", json={
            "email": email, "password": "WrongPassword123!", "tenant_id": tenant_id,
        })
        print(f"[6] Wrong password: {r6.status_code}")

        # 7. Create another user with limited permissions
        email2 = f"limited_{uuid.uuid4().hex[:8]}@test.com"
        company2 = f"limited-{uuid.uuid4().hex[:8]}"
        reg2 = await client.post("/auth/register", json={
            "company_name": company2,
            "company_name_ar": "Limited User",
            "email": email2,
            "password": "LimitedPass123!",
            "industry": "retail",
        })
        print(f"[7] Register limited user: {reg2.status_code}")

        if reg2.status_code == 200:
            data2 = reg2.json()
            tenant2 = data2.get("tenant_id")

            login2 = await client.post("/auth/login", json={
                "email": email2, "password": "LimitedPass123!", "tenant_id": tenant2,
            })
            if login2.status_code == 200:
                token2 = login2.json().get("access_token")
                headers2 = {"Authorization": f"Bearer {token2}"}

                # Limited user tries to create account (should work as admin of own tenant)
                r7 = await client.post(f"/{tenant2}/accounting/accounts", json={
                    "code": "2000", "name": "Test", "name_ar": "Test",
                    "account_type": "liability", "currency": "EGP",
                }, headers=headers2)
                print(f"[8] Limited user create account: {r7.status_code}")

        print("\n=== RBAC TEST RESULTS ===")
        tests = [
            ("Register new user", register_resp.status_code == 200),
            ("Login successful", login_resp.status_code == 200),
            ("Admin create account", r3.status_code == 200),
            ("Admin trial balance", r4.status_code == 200),
            ("No auth rejected", r5.status_code in [401, 403]),
            ("Wrong password rejected", r6.status_code in [400, 401]),
        ]

        for name, ok in tests:
            status_label = "PASS" if ok else "FAIL"
            print(f"  [{status_label}] {name}")

        passed = sum(1 for _, p in tests if p)
        total = len(tests)
        print(f"\n{passed}/{total} tests passed")


if __name__ == "__main__":
    asyncio.run(create_test_data())
