"""
Hardening Matrix — Live tests against running EOS server.
Covers: password policy, login rate limiting, auth audit trail,
and tenant-scoped RBAC role resolution.

Usage: python app/tests/test_hardening_matrix.py
"""
import asyncio
import sys
import uuid

import asyncpg
import httpx

BASE = "http://127.0.0.1:8001/api/v1"
DB = "postgres://eos:0100@127.0.0.1:5432/eos_main"

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), str(detail)[:90]))


async def main():
    uid = uuid.uuid4().hex[:8]
    email = f"harden-{uid}@example.com"
    password = "Strong123!"
    async with httpx.AsyncClient(timeout=20) as c:
        # ── Password policy ──
        r = await c.post(f"{BASE}/auth/register", json={
            "email": f"weak-{uid}@example.com", "password": "short1",
            "company_name": f"W{uid}", "company_name_ar": "w", "industry": "tech"})
        check("register short password -> 422", r.status_code == 422,
              f"{r.status_code}")

        r = await c.post(f"{BASE}/auth/register", json={
            "email": f"nodigit-{uid}@example.com", "password": "NoDigitsHere",
            "company_name": f"N{uid}", "company_name_ar": "n", "industry": "tech"})
        check("register no-digit password -> 422", r.status_code == 422,
              r.status_code)

        r = await c.post(f"{BASE}/auth/register", json={
            "email": email, "password": password,
            "company_name": f"HardenCo {uid}", "company_name_ar": "شركة",
            "industry": "tech"})
        check("register strong password -> 200", r.status_code == 200,
              f"{r.status_code} {r.text[:60]}")
        tid = r.json()["tenant_id"]

        r = await c.post(f"{BASE}/auth/login", json={
            "email": email, "password": password, "tenant_id": tid})
        check("login strong -> 200", r.status_code == 200, r.status_code)

        # ── Rate limiting ──
        codes = []
        for i in range(6):
            r = await c.post(f"{BASE}/auth/login", json={
                "email": email, "password": "WrongPass999!", "tenant_id": tid})
            codes.append(r.status_code)
        check("4 attempts then blocked on 5th", codes[:4] == [401] * 4 and codes[4:] == [429, 429],
              str(codes))
        ra = r.headers.get("Retry-After")
        check("429 carries Retry-After header", bool(ra and int(ra) > 0), ra)

        # different email on same IP must NOT inherit the block
        r2 = await c.post(f"{BASE}/auth/login", json={
            "email": f"other-{uid}@example.com", "password": "WrongPass999!",
            "tenant_id": tid})
        check("limiter keyed per-email (other -> 401)", r2.status_code == 401,
              r2.status_code)

    # ── Audit trail in DB ──
    conn = await asyncpg.connect(DB)
    reg = await conn.fetchval(
        "SELECT count(*) FROM audit_logs WHERE action='register' AND tenant_id=$1", tid)
    ok_logins = await conn.fetchval(
        "SELECT count(*) FROM audit_logs WHERE action='login' AND tenant_id=$1 AND status='success'", tid)
    fail_logins = await conn.fetchval(
        "SELECT count(*) FROM audit_logs WHERE action='login' AND tenant_id=$1 AND status='failure'", tid)
    check("audit: register logged", int(reg) >= 1, reg)
    check("audit: successful logins logged", int(ok_logins) >= 1, ok_logins)
    check("audit: failed logins logged", int(fail_logins) >= 5, fail_logins)

    # ── Cross-tenant RBAC scoping ──
    uid_b = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{BASE}/auth/register", json={
            "email": f"victim-{uid_b}@example.com", "password": "Strong123!",
            "company_name": f"VictimCo {uid_b}", "company_name_ar": "v",
            "industry": "tech"})
        tid_b = r.json()["tenant_id"]
        r = await c.post(f"{BASE}/auth/login", json={
            "email": f"victim-{uid_b}@example.com", "password": "Strong123!",
            "tenant_id": tid_b})
        tok_admin_b = r.json()["access_token"]

        r = await c.post(f"{BASE}/auth/invite",
                         headers={"Authorization": f"Bearer {tok_admin_b}"},
                         json={"email": f"clerk-{uid_b}@example.com",
                               "password": "Clerk123!", "first_name": "C",
                               "last_name": "B", "role": "user"})
        check("invite clerk in tenant B -> 200", r.status_code == 200,
              f"{r.status_code} {r.text[:60]}")
        clerk_b_id = r.json()["user_id"]

        # weak invite password rejected
        r = await c.post(f"{BASE}/auth/invite",
                         headers={"Authorization": f"Bearer {tok_admin_b}"},
                         json={"email": f"w2-{uid_b}@example.com",
                               "password": "tiny1", "first_name": "W",
                               "last_name": "W"})
        check("invite weak password -> 422", r.status_code == 422, r.status_code)

        r = await c.post(f"{BASE}/auth/login", json={
            "email": f"clerk-{uid_b}@example.com", "password": "Clerk123!",
            "tenant_id": tid_b})
        tok_clerk = r.json()["access_token"]
        h_clerk = {"Authorization": f"Bearer {tok_clerk}"}

        # baseline: clerk has no permissions yet
        r = await c.get(f"{BASE}/{tid_b}/sales/customers", headers=h_clerk)
        check("clerk baseline denied -> 403", r.status_code == 403, r.status_code)

    # ATTACK: link tenant-B clerk to tenant-A's Admin role
    admin_role_a = await conn.fetchval(
        "SELECT id FROM roles WHERE tenant_id=$1 AND name='Admin' LIMIT 1", tid)
    fake_id = str(uuid.uuid4())
    await conn.execute(
        "INSERT INTO user_roles (id, user_id, role_id) VALUES ($1,$2,$3)",
        fake_id, clerk_b_id, admin_role_a)
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(f"{BASE}/{tid_b}/sales/customers", headers=h_clerk)
            check("cross-tenant role hijack BLOCKED -> still 403",
                  r.status_code == 403, r.status_code)
    finally:
        await conn.execute("DELETE FROM user_roles WHERE id=$1", fake_id)

    await conn.close()

    print("=" * 64)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"HARDENING MATRIX: {passed}/{len(RESULTS)} checks passed")
    for name, ok, detail in RESULTS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} | {detail}")
    print("=" * 64)
    return passed == len(RESULTS)


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
