"""
P47 Identity & SSO Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/identity"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
p, f = 0, 0


def t(name, got, exp):
    global p, f
    if got == exp: p += 1
    else: f += 1; print(f"  FAIL - {name}: got {got!r}, expected {exp!r}")


def start():
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(5)
    return proc

def stop(proc):
    proc.terminate()
    try: proc.wait(timeout=5)
    except: proc.kill()

def setup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ['dbp_sso_providers', 'dbp_sso_sessions', 'dbp_mfa_configs',
                     'dbp_role_mappings', 'dbp_api_keys']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()

def cleanup(): setup()


def test_providers(c):
    print("\n--- 1. SSO Providers ---")
    r = c.post(f"{EP}/providers", json={"provider_name": "Azure AD",
               "provider_type": "saml", "client_id": "azure-client-001"}, headers=H_A)
    t("Create provider", r.status_code, 200)
    pid = r.json()["data"]["id"]
    r = c.post(f"{EP}/providers", json={"provider_name": "Google",
               "provider_type": "oidc", "client_id": "google-client-001"}, headers=H_A)
    t("Create second provider", r.status_code, 200)
    r = c.get(f"{EP}/providers", headers=H_A)
    t("List providers", r.status_code, 200)
    t("Two providers", len(r.json()["data"]), 2)
    r = c.put(f"{EP}/providers/{pid}", json={"is_active": False}, headers=H_A)
    t("Update provider", r.status_code, 200)


def test_sessions(c):
    print("\n--- 2. SSO Sessions ---")
    pid = c.post(f"{EP}/providers", json={"provider_name": "Test",
               "provider_type": "saml", "client_id": "test"}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/sessions", json={"user_id": "user1", "provider_id": pid,
               "sso_session_id": "sso_abc123", "ip_address": "10.0.0.1"}, headers=H_A)
    t("Create session", r.status_code, 200)
    r = c.get(f"{EP}/sessions", headers=H_A)
    t("List sessions", r.status_code, 200)
    t("One session", len(r.json()["data"]), 1)


def test_mfa(c):
    print("\n--- 3. MFA ---")
    r = c.post(f"{EP}/mfa", json={"user_id": "user1", "mfa_type": "totp"}, headers=H_A)
    t("Setup MFA", r.status_code, 200)
    mid = r.json()["data"]["id"]
    r = c.put(f"{EP}/mfa/{mid}/enable", headers=H_A)
    t("Enable MFA", r.status_code, 200)
    r = c.get(f"{EP}/mfa", headers=H_A)
    t("List MFA", r.status_code, 200)
    r = c.put(f"{EP}/mfa/{mid}/disable", headers=H_A)
    t("Disable MFA", r.status_code, 200)


def test_role_mappings(c):
    print("\n--- 4. Role Mappings ---")
    pid = c.post(f"{EP}/providers", json={"provider_name": "Test2",
               "provider_type": "oidc", "client_id": "test2"}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/role-mappings", json={"provider_id": pid,
               "external_role": "admin", "internal_role": "manager"}, headers=H_A)
    t("Create role mapping", r.status_code, 200)
    rid = r.json()["data"]["id"]
    r = c.get(f"{EP}/role-mappings", headers=H_A)
    t("List role mappings", r.status_code, 200)
    t("One mapping", len(r.json()["data"]), 1)
    r = c.delete(f"{EP}/role-mappings/{rid}", headers=H_A)
    t("Delete role mapping", r.status_code, 200)


def test_api_keys(c):
    print("\n--- 5. API Keys ---")
    r = c.post(f"{EP}/api-keys", json={"key_name": "Production Key",
               "permissions": ["read", "write"]}, headers=H_A)
    t("Create API key", r.status_code, 200)
    kid = r.json()["data"]["id"]
    r = c.get(f"{EP}/api-keys", headers=H_A)
    t("List API keys", r.status_code, 200)
    t("One key", len(r.json()["data"]), 1)
    r = c.put(f"{EP}/api-keys/{kid}/revoke", headers=H_A)
    t("Revoke API key", r.status_code, 200)


def test_negative(c):
    print("\n--- 6. Negative Tests ---")
    r = c.post(f"{EP}/providers", json={}, headers=H_A)
    t("Create provider missing fields", r.status_code, 400)
    r = c.post(f"{EP}/mfa", json={}, headers=H_A)
    t("Setup MFA missing fields", r.status_code, 400)
    r = c.post(f"{EP}/role-mappings", json={}, headers=H_A)
    t("Create role mapping missing fields", r.status_code, 400)
    r = c.post(f"{EP}/api-keys", json={}, headers=H_A)
    t("Create API key missing fields", r.status_code, 400)


if __name__ == "__main__":
    print("=" * 60)
    print("P47 IDENTITY & SSO TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_providers(c); test_sessions(c); test_mfa(c)
        test_role_mappings(c); test_api_keys(c); test_negative(c)
    finally:
        c.close(); stop(proc); cleanup()
    print("\n" + "=" * 60)
    print(f"P47 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
