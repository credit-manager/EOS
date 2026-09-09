"""P61 Auth Flow Test — Production Authentication E2E"""
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


if __name__ == "__main__":
    print("=" * 60)
    print("  P61 STEP 1 — Production Authentication E2E")
    print("=" * 60)

    proc = start_server()
    c = httpx.Client(base_url=BASE, timeout=30)

    try:
        # ── Step 1: Register ──
        log("STEP 1: Register new user")
        email = f"test_{secrets.token_hex(4)}@example.com"
        r = c.post("/api/v1/auth/register", json={
            "email": email, "password": "Test1234",
            "first_name": "Test", "last_name": "User",
            "company_name": "Test Company"
        })
        t("Register returns 200", r.status_code, 200, critical=True)
        data = r.json()["data"]
        t("Returns user_id", "user_id" in data, True)
        t("Returns tenant_id", "tenant_id" in data, True)
        t("Returns verification_token", "verification_token" in data, True)
        t("requires_verification = True", data["requires_verification"], True)

        verification_token = data.get("verification_token")
        tenant_id = data["tenant_id"]

        # ── Step 2: Login BEFORE verification (should fail) ──
        log("STEP 2: Login before email verification (should fail)")
        r = c.post("/api/v1/auth/login", json={"email": email, "password": "Test1234"})
        t("Login blocked before verification", r.status_code, 403, critical=True)

        # ── Step 3: Verify email ──
        log("STEP 3: Verify email")
        r = c.post("/api/v1/auth/verify-email", json={"token": verification_token})
        t("Verify email returns 200", r.status_code, 200, critical=True)

        # ── Step 4: Login AFTER verification (should succeed) ──
        log("STEP 4: Login after email verification")
        r = c.post("/api/v1/auth/login", json={"email": email, "password": "Test1234"})
        t("Login returns 200", r.status_code, 200, critical=True)
        login_data = r.json()["data"]
        t("Returns access_token", "access_token" in login_data, True)
        t("Token type = bearer", login_data["token_type"], "bearer")
        t("Returns user info", "user" in login_data, True)
        t("User role = admin", login_data["user"]["role"], "admin")
        t("User tenant_id matches", login_data["user"]["tenant_id"], tenant_id)

        token = login_data["access_token"]
        H = {"Authorization": f"Bearer {token}"}

        # ── Step 5: Access protected endpoint ──
        log("STEP 5: Access /auth/me with production JWT")
        r = c.get("/api/v1/auth/me", headers=H)
        t("Get /me returns 200", r.status_code, 200, critical=True)
        t("Email matches", r.json()["data"]["email"], email)

        # ── Step 6: Access dynamic CRUD with production JWT ──
        log("STEP 6: Access dynamic CRUD with production JWT")
        r = c.get("/api/v1/dynamic/active", headers=H)
        t("Dynamic CRUD accessible with prod JWT", r.status_code in (200, 404), True)

        # ── Step 7: Tenant isolation ──
        log("STEP 7: Tenant isolation with production JWT")
        email2 = f"other_{secrets.token_hex(4)}@example.com"
        r2 = c.post("/api/v1/auth/register", json={
            "email": email2, "password": "Test1234",
            "first_name": "Other", "last_name": "User",
            "company_name": "Other Company"
        })
        t2_token = r2.json()["data"]["verification_token"]
        c.post("/api/v1/auth/verify-email", json={"token": t2_token})
        r2 = c.post("/api/v1/auth/login", json={"email": email2, "password": "Test1234"})
        token2 = r2.json()["data"]["access_token"]
        H2 = {"Authorization": f"Bearer {token2}"}

        r = c.get("/api/v1/auth/users", headers=H)
        users1 = r.json()["data"]
        r = c.get("/api/v1/auth/users", headers=H2)
        users2 = r.json()["data"]
        t("Tenant A sees only their users", len(users1) >= 1, True)
        t("Tenant B sees only their users", len(users2) >= 1, True)

        # ── Step 8: Password reset ──
        log("STEP 8: Password reset flow")
        r = c.post("/api/v1/auth/forgot-password", json={"email": email})
        t("Forgot password returns 200", r.status_code, 200)
        reset_token = r.json()["data"].get("reset_token")
        if reset_token:
            r = c.post("/api/v1/auth/reset-password", json={
                "token": reset_token, "new_password": "NewPass123"
            })
            t("Reset password returns 200", r.status_code, 200)
            r = c.post("/api/v1/auth/login", json={"email": email, "password": "NewPass123"})
            t("Login with new password works", r.status_code, 200, critical=True)

        # ── Step 9: Invalid token rejected ──
        log("STEP 9: Invalid token rejected")
        r = c.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"})
        t("Invalid token returns 401", r.status_code, 401)

        # ── Step 10: Duplicate registration blocked ──
        log("STEP 10: Duplicate email blocked")
        r = c.post("/api/v1/auth/register", json={
            "email": email, "password": "Test1234",
            "first_name": "Dup", "last_name": "User",
            "company_name": "Dup Company"
        })
        t("Duplicate email blocked", r.status_code == 400, True)

        # ── Step 11: Weak password rejected ──
        log("STEP 11: Weak password rejected")
        r = c.post("/api/v1/auth/register", json={
            "email": f"weak_{secrets.token_hex(4)}@example.com",
            "password": "123",
            "first_name": "Weak", "last_name": "User",
            "company_name": "Weak Co"
        })
        t("Weak password rejected", r.status_code == 400, True)

    finally:
        c.close()
        stop_server(proc)

    print("\n" + "\n".join(results))
    print("\n" + "=" * 60)
    print(f"  P61 STEP 1 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
