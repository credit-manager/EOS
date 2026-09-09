"""
Live Tenant Normalization Matrix — runs against a running EOS server.
Covers login case-insensitivity, refresh-token tenant preservation,
and JWT/request consistency enforcement end-to-end.

Usage: python app/tests/test_live_tenant_matrix.py
Requires server on http://127.0.0.1:8001
"""
import asyncio
import json
import sys
import uuid

import httpx
from jose import jwt

BASE = "http://127.0.0.1:8001/api/v1"
SECRET = None  # filled from /health-free path below via settings import fallback

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), str(detail)[:100]))


async def main():
    uid = uuid.uuid4().hex[:8]
    email = f"norm-{uid}@example.com"
    password = "Admin123!"

    async with httpx.AsyncClient(timeout=20) as c:
        # ── Register fresh tenant ──
        r = await c.post(f"{BASE}/auth/register", json={
            "email": email, "password": password,
            "company_name": f"NormalCo {uid}", "company_name_ar": "شركة",
            "industry": "tech"})
        check("register -> 200/201", r.status_code in (200, 201), f"{r.status_code} {r.text[:80]}")
        tid = r.json()["tenant_id"]

        def decode(tok):
            return jwt.decode(tok, "", options={"verify_signature": False})

        # ── Login exact ──
        r = await c.post(f"{BASE}/auth/login", json={
            "email": email, "password": password, "tenant_id": tid})
        check("login exact tenant -> 200", r.status_code == 200, r.text[:80])
        tok1 = r.json()["access_token"]
        claims1 = decode(tok1)
        check("login token claim canonical", claims1.get("tenant_id") == tid.lower(),
              claims1.get("tenant_id"))

        # ── Login UPPERCASE tenant (case-insensitive closure) ──
        r = await c.post(f"{BASE}/auth/login", json={
            "email": email, "password": password, "tenant_id": tid.upper()})
        check("login UPPER tenant -> 200", r.status_code == 200, f"{r.status_code} {r.text[:60]}")

        # ── Login padded tenant ──
        r = await c.post(f"{BASE}/auth/login", json={
            "email": email, "password": password, "tenant_id": f"  {tid}  "})
        check("login padded tenant -> 200", r.status_code == 200, f"{r.status_code}")

        # ── Login WRONG tenant rejected ──
        r = await c.post(f"{BASE}/auth/login", json={
            "email": email, "password": password, "tenant_id": str(uuid.uuid4())})
        check("login wrong tenant -> 401", r.status_code == 401, r.status_code)

        h = {"Authorization": f"Bearer {tok1}"}

        # ── /auth/me with token only (reserved route, no header) ──
        r = await c.get(f"{BASE}/auth/me", headers=h)
        check("/auth/me token-only -> 200", r.status_code == 200, f"{r.status_code} {r.text[:60]}")
        me_tenant = r.json().get("tenant_id")
        check("/auth/me returns canonical tenant", me_tenant == tid.lower(), me_tenant)

        # ── Business call with FOREIGN header rejected ──
        other_tid = str(uuid.uuid4())
        r = await c.get(f"{BASE}/{tid}/sales/customers",
                        headers={**h, "X-Tenant-ID": other_tid})
        check("foreign X-Tenant-ID -> 403", r.status_code == 403, r.status_code)

        # ── Business call via FOREIGN path rejected ──
        r = await c.get(f"{BASE}/{other_tid}/sales/customers", headers=h)
        check("foreign path tenant -> 403", r.status_code == 403, r.status_code)

        # ── Legitimate business call still works ──
        r = await c.post(f"{BASE}/{tid}/sales/customers",
                         json={"name": "NC", "type": "individual"}, headers=h)
        check("own-tenant create customer ok", r.status_code in (200, 201),
              f"{r.status_code} {r.text[:60]}")

        # ── REFRESH: new token MUST carry tenant claims (critical fix) ──
        r = await c.post(f"{BASE}/auth/login", json={
            "email": email, "password": password, "tenant_id": tid})
        tokens = r.json()
        r = await c.post(f"{BASE}/auth/refresh",
                         json={"refresh_token": tokens["refresh_token"]})
        check("refresh -> 200", r.status_code == 200, f"{r.status_code} {r.text[:60]}")
        tok2 = r.json()["access_token"]
        claims2 = decode(tok2)
        check("refreshed token HAS tenant claim", claims2.get("tenant_id") is not None,
              json.dumps(claims2.get("tenant_id")))
        check("refreshed tenant canonical+matches", claims2.get("tenant_id") == tid.lower(),
              claims2.get("tenant_id"))
        check("refreshed token has roles", bool(claims2.get("roles")), claims2.get("roles"))

        # ── Refreshed token usable on protected endpoints ──
        r = await c.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {tok2}"})
        check("/auth/me with refreshed token -> 200", r.status_code == 200, r.status_code)

    print("=" * 64)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"LIVE TENANT MATRIX: {passed}/{len(RESULTS)} checks passed")
    for name, ok, detail in RESULTS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} | {detail}")
    print("=" * 64)
    return passed == len(RESULTS)


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
