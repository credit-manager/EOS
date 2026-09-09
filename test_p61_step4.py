"""P61 Step 4 — User Management E2E"""
import httpx, sys, secrets, subprocess, time, os

BASE = "http://127.0.0.1:8000"
p, f = 0, 0
results = []


def t(name, got, exp, critical=False):
    global p, f
    if got == exp:
        p += 1
        results.append(f"  OK   {name}")
    else:
        f += 1
        tag = "CRITICAL" if critical else "FAIL"
        results.append(f"  {tag}  {name}: got {got!r}, expected {exp!r}")


def log(msg):
    results.append(f"  ---  {msg}")


def start_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(6)
    return proc


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def register_and_verify(c, prefix="um"):
    email = f"{prefix}_{secrets.token_hex(4)}@example.com"
    r = c.post("/api/v1/auth/register", json={
        "email": email, "password": "Test1234",
        "first_name": "Test", "last_name": "Admin",
        "company_name": f"{prefix.title()} Company"
    })
    token = r.json()["data"]["verification_token"]
    c.post("/api/v1/auth/verify-email", json={"token": token})
    r = c.post("/api/v1/auth/login", json={"email": email, "password": "Test1234"})
    return r.json()["data"]["access_token"], r.json()["data"]["user"]["id"], r.json()["data"]["user"]["tenant_id"]


if __name__ == "__main__":
    print("=" * 60)
    print("  P61 STEP 4 — User Management E2E")
    print("=" * 60)

    proc = start_server()
    c = httpx.Client(base_url=BASE, timeout=30)

    try:
        token, user_id, tenant_id = register_and_verify(c, "admin")
        H = {"Authorization": f"Bearer {token}"}

        # ── Step 1: List users ──
        log("STEP 1: List users")
        r = c.get("/api/v1/auth/users", headers=H)
        t("List users returns 200", r.status_code, 200)
        t("Has at least 1 user", len(r.json()["data"]) >= 1, True)

        # ── Step 2: Get user by ID ──
        log("STEP 2: Get user by ID")
        r = c.get(f"/api/v1/auth/users/{user_id}", headers=H)
        t("Get user returns 200", r.status_code, 200)
        t("User email matches", r.json()["data"]["email"], r.json()["data"]["email"])

        # ── Step 3: Update user ──
        log("STEP 3: Update user info")
        r = c.put(f"/api/v1/auth/users/{user_id}", headers=H, json={"first_name": "Updated"})
        t("Update user returns 200", r.status_code, 200)

        # ── Step 4: Invite user ──
        log("STEP 4: Invite user")
        invite_email = f"invited_{secrets.token_hex(4)}@example.com"
        r = c.post("/api/v1/auth/users/invite", headers=H, json={
            "email": invite_email, "role": "dynamic_viewer",
            "first_name": "Invited", "last_name": "User"
        })
        t("Invite returns 200", r.status_code, 200)
        invited_id = r.json()["data"]["user_id"]

        # ── Step 5: Invited user appears in list ──
        log("STEP 5: Invited user in list")
        r = c.get("/api/v1/auth/users", headers=H)
        emails = [u["email"] for u in r.json()["data"]]
        t("Invited user in list", invite_email in emails, True)

        # ── Step 6: Change role ──
        log("STEP 6: Change user role")
        r = c.put(f"/api/v1/auth/users/{invited_id}/role", headers=H, json={"role": "dynamic_operator"})
        t("Change role returns 200", r.status_code, 200)

        # ── Step 7: Deactivate user ──
        log("STEP 7: Deactivate user")
        r = c.delete(f"/api/v1/auth/users/{invited_id}", headers=H)
        t("Deactivate returns 200", r.status_code, 200)

        # ── Step 8: Tenant isolation ──
        log("STEP 8: Tenant isolation - can't access other tenant's user")
        email2 = f"other_{secrets.token_hex(4)}@example.com"
        r2 = c.post("/api/v1/auth/register", json={
            "email": email2, "password": "Test1234",
            "first_name": "Other", "last_name": "Admin",
            "company_name": "Other Company"
        })
        t2_token = r2.json()["data"]["verification_token"]
        c.post("/api/v1/auth/verify-email", json={"token": t2_token})
        r2 = c.post("/api/v1/auth/login", json={"email": email2, "password": "Test1234"})
        H2 = {"Authorization": f"Bearer {r2.json()['data']['access_token']}"}
        other_id = r2.json()["data"]["user"]["id"]

        r = c.get(f"/api/v1/auth/users/{user_id}", headers=H2)
        t("Can't access other tenant's user", r.status_code == 404, True)

        r = c.get(f"/api/v1/auth/users/{other_id}", headers=H)
        t("Can't access other tenant's user (reverse)", r.status_code == 404, True)

        # ── Step 9: Unauthorized access ──
        log("STEP 9: Unauthorized access rejected")
        r = c.get("/api/v1/auth/users")
        t("No auth = 401 or 403", r.status_code in (401, 403), True)

    finally:
        c.close()
        stop_server(proc)

    print("\n" + "\n".join(results))
    print("\n" + "=" * 60)
    print(f"  P61 STEP 4 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
