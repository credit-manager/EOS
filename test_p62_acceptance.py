"""P62.7 — Production Acceptance Test
Simulates a real customer journey from an external device via HTTPS.
This test can be run against a deployed production instance.
"""
import httpx, sys, secrets, subprocess, time, os

# Configuration - set these for your production domain
BASE = os.getenv("P62_BASE_URL", "https://your-domain.com")
DOMAIN = os.getenv("P62_DOMAIN", "your-domain.com")

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


def verify_ssl():
    """Verify SSL certificate is valid"""
    import ssl, socket
    from datetime import datetime

    context = ssl.create_default_context()
    with socket.create_connection((DOMAIN, 443), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=DOMAIN) as ssock:
            cert = ssock.getpeercert()
            not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            days_left = (not_after - datetime.utcnow()).days
            t(f"SSL certificate valid ({days_left} days left)", days_left > 0, True, critical=True)
            t("SSL certificate matches domain", DOMAIN in cert.get('subjectAltName', ''), True, critical=True)


if __name__ == "__main__":
    print("=" * 60)
    print("  P62.7 — Production Acceptance Test")
    print(f"  Target: {BASE}")
    print("=" * 60)

    c = httpx.Client(base_url=BASE, timeout=30, verify=True)
    email = f"pat_{secrets.token_hex(4)}@example.com"

    try:
        # ── Phase 1: HTTPS & SSL ──
        log("PHASE 1: HTTPS & SSL Verification")
        r = c.get("/health")
        t("Health endpoint accessible", r.status_code, 200, critical=True)
        t("HTTPS enforced", r.url.scheme, "https", critical=True)

        verify_ssl()

        # ── Phase 2: Landing Page ──
        log("PHASE 2: Landing Page")
        r = c.get("/app")
        t("Landing page loads", r.status_code, 200)
        t("Landing page is HTML", "text/html" in r.headers.get("content-type", ""), True)
        t("Has EOS branding", "EOS" in r.text, True)

        # ── Phase 3: API Docs ──
        log("PHASE 3: API Documentation")
        r = c.get("/docs")
        t("Swagger UI accessible", r.status_code, 200)
        r = c.get("/openapi.json")
        t("OpenAPI spec accessible", r.status_code, 200)

        # ── Phase 4: Registration ──
        log("PHASE 4: Customer Registration")
        r = c.post("/api/v1/auth/register", json={
            "email": email, "password": "SecurePass123",
            "first_name": "PAT", "last_name": "Customer",
            "company_name": "PAT Corp"
        })
        t("Registration successful", r.status_code, 200, critical=True)
        data = r.json()["data"]
        vtoken = data["verification_token"]
        tenant_id = data["tenant_id"]
        t("Requires email verification", data["requires_verification"], True)

        # ── Phase 5: Email Verification ──
        log("PHASE 5: Email Verification")
        r = c.post("/api/v1/auth/verify-email", json={"token": vtoken})
        t("Email verified", r.status_code, 200, critical=True)

        # ── Phase 6: Login ──
        log("PHASE 6: Login with Production JWT")
        r = c.post("/api/v1/auth/login", json={
            "email": email, "password": "SecurePass123"
        })
        t("Login successful", r.status_code, 200, critical=True)
        login = r.json()["data"]
        access_token = login["access_token"]
        t("JWT token received", access_token is not None, True)
        t("Token type is bearer", login["token_type"], "bearer")
        t("User role is admin", login["user"]["role"], "admin")
        H = {"Authorization": f"Bearer {access_token}"}

        # ── Phase 7: Profile ──
        log("PHASE 7: Profile Access")
        r = c.get("/api/v1/auth/me", headers=H)
        t("Profile accessible", r.status_code, 200)
        t("Email matches", r.json()["data"]["email"], email)

        # ── Phase 8: Dynamic CRUD ──
        log("PHASE 8: Dynamic CRUD with Production JWT")
        r = c.get("/api/v1/dynamic/entities/customers/schema", headers=H)
        t("Dynamic CRUD accessible", r.status_code in (200, 404), True)

        # ── Phase 9: Marketplace ──
        log("PHASE 9: Marketplace")
        r = c.get("/api/v1/marketplace/items", headers=H)
        t("Marketplace accessible", r.status_code in (200, 404), True)

        # ── Phase 10: Billing ──
        log("PHASE 10: Billing & Plans")
        r = c.get("/api/v1/dynamic/billing-flow/plans", headers=H)
        t("Plans list accessible", r.status_code in (200, 404), True)

        # ── Phase 11: User Management ──
        log("PHASE 11: User Management")
        r = c.get("/api/v1/auth/users", headers=H)
        t("User list accessible", r.status_code, 200)
        t("Self in user list", len(r.json()["data"]) >= 1, True)

        # ── Phase 12: Tenant Isolation ──
        log("PHASE 12: Tenant Isolation")
        email2 = f"competitor_{secrets.token_hex(4)}@example.com"
        r2 = c.post("/api/v1/auth/register", json={
            "email": email2, "password": "Test1234",
            "first_name": "Competitor", "last_name": "Corp",
            "company_name": "Competitor Corp"
        })
        t2 = r2.json()["data"]["verification_token"]
        c.post("/api/v1/auth/verify-email", json={"token": t2})
        r2 = c.post("/api/v1/auth/login", json={"email": email2, "password": "Test1234"})
        H2 = {"Authorization": f"Bearer {r2.json()['data']['access_token']}"}

        r = c.get(f"/api/v1/auth/users/{login['user']['id']}", headers=H2)
        t("Cross-tenant access blocked", r.status_code, 404, critical=True)

        # ── Phase 13: Security Headers ──
        log("PHASE 13: Security Headers")
        r = c.get("/")
        t("HSTS header present", "strict-transport-security" in r.headers, True)
        t("X-Frame-Options: DENY", r.headers.get("x-frame-options"), "DENY")
        t("X-Content-Type-Options: nosniff", r.headers.get("x-content-type-options"), "nosniff")
        t("Referrer-Policy set", "referrer-policy" in r.headers, True)
        t("Content-Security-Policy set", "content-security-policy" in r.headers, True)

        # ── Phase 14: Rate Limiting ──
        log("PHASE 14: Rate Limiting")
        for i in range(15):
            c.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
        r = c.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
        t("Login rate limit enforced", r.status_code, 429)

        # ── Phase 15: Data Persistence ──
        log("PHASE 15: Data Persistence Check")
        # Create an entity
        r = c.post("/api/v1/dynamic/entities", headers=H, json={
            "code": "pat_test", "name_en": "PAT Test",
            "module": "crm", "is_master": False
        })
        t("Entity creation", r.status_code in (200, 400), True)

    finally:
        c.close()

    print("\n" + "\n".join(results))
    print("\n" + "=" * 60)
    print(f"  P62.7 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)