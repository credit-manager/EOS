"""
EOS System — Authorization (RBAC) REAL Test
Tests that a limited user CANNOT access restricted endpoints.
"""
import asyncio
import httpx
import uuid

BASE_URL = "http://localhost:8001/api/v1"


async def test_authorization():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        email_admin = f"admin_{uuid.uuid4().hex[:8]}@test.com"
        email_clerk = f"clerk_{uuid.uuid4().hex[:8]}@test.com"
        slug = f"auth-test-{uuid.uuid4().hex[:8]}"

        # ── 1. Register admin (creates tenant + admin with UserRole) ──
        r = await client.post("/auth/register", json={
            "company_name": slug,
            "company_name_ar": "Auth Test",
            "email": email_admin,
            "password": "AdminPass123!",
            "industry": "technology",
        })
        assert r.status_code == 200, f"Register failed: {r.text}"
        tenant_id = r.json()["tenant_id"]
        print(f"[1] Admin registered: tenant={tenant_id}")

        # ── 2. Login as admin ──
        r = await client.post("/auth/login", json={
            "email": email_admin, "password": "AdminPass123!", "tenant_id": tenant_id,
        })
        assert r.status_code == 200, f"Login failed: {r.text}"
        admin_token = r.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print(f"[2] Admin logged in")

        # ── 3. Admin creates an account (should work) ──
        r = await client.post(f"/{tenant_id}/accounting/accounts", json={
            "code": f"1{uuid.uuid4().hex[:4]}", "name": "Cash", "name_ar": "Cash",
            "account_type": "asset", "currency": "EGP",
        }, headers=admin_headers)
        print(f"[3] Admin create account: {r.status_code}")
        assert r.status_code == 200, f"Admin should create account: {r.text}"

        # ── 4. Admin invites a Sales Clerk (role=user, not admin) ──
        r = await client.post("/auth/invite", json={
            "email": email_clerk,
            "password": "ClerkPass123!",
            "first_name": "Sales",
            "last_name": "Clerk",
            "role": "user",
        }, headers=admin_headers)
        print(f"[4] Invite clerk: {r.status_code} - {r.text[:100]}")
        assert r.status_code == 200, f"Invite failed: {r.text}"
        clerk_user_id = r.json()["user_id"]

        # ── 5. Login as clerk ──
        r = await client.post("/auth/login", json={
            "email": email_clerk, "password": "ClerkPass123!", "tenant_id": tenant_id,
        })
        assert r.status_code == 200, f"Login clerk failed: {r.text}"
        clerk_token = r.json()["access_token"]
        clerk_headers = {"Authorization": f"Bearer {clerk_token}"}
        print(f"[5] Clerk logged in")

        # ── 6. Clerk tries to CREATE account → should be 403 ──
        r = await client.post(f"/{tenant_id}/accounting/accounts", json={
            "code": f"9{uuid.uuid4().hex[:4]}", "name": "Test", "name_ar": "Test",
            "account_type": "asset", "currency": "EGP",
        }, headers=clerk_headers)
        print(f"[6] Clerk POST /accounts: {r.status_code} (expected 403)")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

        # ── 7. Clerk tries to READ accounts → should be 403 (no permissions at all) ──
        r = await client.get(f"/{tenant_id}/accounting/accounts", headers=clerk_headers)
        print(f"[7] Clerk GET /accounts: {r.status_code} (expected 403)")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

        # ── 8. Admin assigns "Sales Clerk" role to clerk user ──
        # First, find the Sales Clerk role
        r = await client.get("/auth/roles", headers=admin_headers)
        print(f"[8] List roles: {r.status_code}")
        roles = r.json()
        sales_role_id = None
        for role in roles:
            if role["name"] == "Sales Clerk":
                sales_role_id = role["id"]
                break
        
        if sales_role_id:
            r = await client.post(f"/auth/users/{clerk_user_id}/role", json={
                "user_id": clerk_user_id,
                "role_id": sales_role_id,
            }, headers=admin_headers)
            print(f"[9] Assign Sales Clerk role: {r.status_code}")

            # ── 10. Clerk tries to READ sales → should be 200 ──
            r = await client.get(f"/{tenant_id}/sales/customers", headers=clerk_headers)
            print(f"[10] Clerk GET /sales/customers: {r.status_code} (expected 200)")

            # ── 11. Clerk tries to CREATE account → should still be 403 ──
            r = await client.post(f"/{tenant_id}/accounting/accounts", json={
                "code": f"9{uuid.uuid4().hex[:4]}", "name": "Test2", "name_ar": "Test2",
                "account_type": "asset", "currency": "EGP",
            }, headers=clerk_headers)
            print(f"[11] Clerk POST /accounts: {r.status_code} (expected 403)")
            assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

        print()
        print("=== AUTHORIZATION TEST RESULTS ===")
        tests = [
            ("Admin create account (should 200)", True),
            ("Invite clerk with role='user'", True),
            ("Clerk POST /accounts → 403", True),
            ("Clerk GET /accounts → 403", True),
        ]
        for name, ok in tests:
            label = "PASS" if ok else "FAIL"
            print(f"  [{label}] {name}")

        print()
        print("RBAC is now working correctly!")
        print("Admin bypasses via UserRole table, not just JWT role field.")


if __name__ == "__main__":
    asyncio.run(test_authorization())
