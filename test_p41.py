"""
P41 SaaS Control Plane Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/saas"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
HV = {"Authorization": f"Bearer {TOKEN_V}"}
p, f = 0, 0


def t(name, got, exp):
    global p, f
    if got == exp:
        p += 1
    else:
        f += 1
        print(f"  FAIL - {name}: got {got!r}, expected {exp!r}")


def start():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(5)
    return proc


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def setup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ['dbp_saas_tenants', 'dbp_saas_plans', 'dbp_saas_features',
                     'dbp_saas_tenant_features', 'dbp_saas_usage']:
            db.execute(sa(f"DELETE FROM {tbl}"))
        db.commit()
    finally:
        db.close()


def cleanup():
    setup()


def test_tenants(c):
    print("\n--- 1. SaaS Tenants ---")
    r = c.post(f"{EP}/tenants", json={"tenant_id": "tenant_a", "name": "Acme Corp",
               "slug": "acme", "max_users": 50, "max_companies": 5}, headers=H_A)
    t("Create tenant", r.status_code, 200)

    r = c.post(f"{EP}/tenants", json={"tenant_id": "tenant_b", "name": "Beta Inc",
               "slug": "beta"}, headers=H_A)
    t("Create second tenant", r.status_code, 200)

    r = c.get(f"{EP}/tenants", headers=H_A)
    t("List tenants", r.status_code, 200)
    t("Two tenants", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/tenants/tenant_a", headers=H_A)
    t("Get tenant A", r.status_code, 200)
    t("Tenant name correct", r.json()["data"]["name"], "Acme Corp")

    r = c.put(f"{EP}/tenants/tenant_a", json={"name": "Acme Corporation"}, headers=H_A)
    t("Update tenant", r.status_code, 200)

    r = c.get(f"{EP}/tenants/tenant_a", headers=H_A)
    t("Updated name", r.json()["data"]["name"], "Acme Corporation")

    r = c.put(f"{EP}/tenants/tenant_a", json={"status": "suspended"}, headers=H_A)
    t("Suspend tenant", r.status_code, 200)

    r = c.get(f"{EP}/tenants/tenant_a", headers=H_A)
    t("Tenant suspended", r.json()["data"]["status"], "suspended")

    r = c.put(f"{EP}/tenants/tenant_a", json={"status": "active"}, headers=H_A)
    t("Reactivate tenant", r.status_code, 200)


def test_plans(c):
    print("\n--- 2. SaaS Plans ---")
    r = c.post(f"{EP}/plans", json={"plan_name": "Starter", "plan_code": "starter",
               "price_monthly": 29.99, "price_yearly": 299.99,
               "max_users": 5, "max_companies": 1, "max_storage_gb": 2}, headers=H_A)
    t("Create starter plan", r.status_code, 200)
    pid1 = r.json()["data"]["id"]

    r = c.post(f"{EP}/plans", json={"plan_name": "Enterprise", "plan_code": "enterprise",
               "price_monthly": 199.99, "price_yearly": 1999.99,
               "max_users": 100, "max_companies": 10, "max_storage_gb": 100,
               "features": ["api_access", "custom_branding", "sso"]}, headers=H_A)
    t("Create enterprise plan", r.status_code, 200)
    pid2 = r.json()["data"]["id"]

    r = c.get(f"{EP}/plans", headers=H_A)
    t("List plans", r.status_code, 200)
    t("Two plans", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/plans/{pid1}", headers=H_A)
    t("Get starter plan", r.status_code, 200)
    t("Starter price", r.json()["data"]["price_monthly"], 29.99)

    r = c.put(f"{EP}/plans/{pid1}", json={"price_monthly": 39.99}, headers=H_A)
    t("Update plan price", r.status_code, 200)

    r = c.get(f"{EP}/plans/{pid1}", headers=H_A)
    t("Updated price", r.json()["data"]["price_monthly"], 39.99)

    r = c.get(f"{EP}/plans/{pid1}", headers=H_B)
    t("Tenant B cant see A plan", r.status_code, 404)

    return pid1, pid2


def test_features(c):
    print("\n--- 3. SaaS Features ---")
    r = c.post(f"{EP}/features", json={"feature_name": "API Access",
               "feature_code": "api_access", "category": "integration",
               "description": "Full API access"}, headers=H_A)
    t("Create feature 1", r.status_code, 200)
    fid1 = r.json()["data"]["id"]

    r = c.post(f"{EP}/features", json={"feature_name": "Custom Branding",
               "feature_code": "custom_branding", "category": "ui",
               "is_default": True}, headers=H_A)
    t("Create feature 2", r.status_code, 200)
    fid2 = r.json()["data"]["id"]

    r = c.post(f"{EP}/features", json={"feature_name": "SSO",
               "feature_code": "sso", "category": "security"}, headers=H_A)
    t("Create feature 3", r.status_code, 200)
    fid3 = r.json()["data"]["id"]

    r = c.get(f"{EP}/features", headers=H_A)
    t("List features", r.status_code, 200)
    t("Three features", len(r.json()["data"]), 3)

    r = c.get(f"{EP}/features?category=security", headers=H_A)
    t("Filter by category", r.status_code, 200)
    t("Security features", len(r.json()["data"]), 1)

    r = c.get(f"{EP}/features/{fid1}", headers=H_A)
    t("Get feature", r.status_code, 200)
    t("Feature name", r.json()["data"]["feature_name"], "API Access")

    return fid1, fid2, fid3


def test_tenant_features(c, fid1, fid2, fid3):
    print("\n--- 4. Tenant Features ---")
    r = c.post(f"{EP}/tenants/tenant_a/features", json={"feature_id": fid1}, headers=H_A)
    t("Enable api_access for A", r.status_code, 200)

    r = c.post(f"{EP}/tenants/tenant_a/features", json={"feature_id": fid2,
               "config": {"logo_url": "https://acme.com/logo.png"}}, headers=H_A)
    t("Enable custom_branding for A", r.status_code, 200)

    r = c.get(f"{EP}/tenants/tenant_a/features", headers=H_A)
    t("List tenant A features", r.status_code, 200)
    t("Two enabled features", len(r.json()["data"]), 2)

    r = c.delete(f"{EP}/tenants/tenant_a/features/{fid1}", headers=H_A)
    t("Disable api_access for A", r.status_code, 200)

    r = c.get(f"{EP}/tenants/tenant_a/features", headers=H_A)
    enabled = [x for x in r.json()["data"] if x.get("is_enabled")]
    t("One feature remains enabled", len(enabled), 1)

    r = c.post(f"{EP}/tenants/tenant_b/features", json={"feature_id": fid3}, headers=H_A)
    t("Enable SSO for B", r.status_code, 200)

    r = c.get(f"{EP}/tenants/tenant_b/features", headers=H_A)
    t("B has one feature", len(r.json()["data"]), 1)


def test_usage(c):
    print("\n--- 5. Usage Tracking ---")
    r = c.post(f"{EP}/usage", json={"tenant_id": "tenant_a",
               "usage_type": "api_calls", "usage_value": 1500}, headers=H_A)
    t("Record API usage", r.status_code, 200)

    r = c.post(f"{EP}/usage", json={"tenant_id": "tenant_a",
               "usage_type": "api_calls", "usage_value": 2300}, headers=H_A)
    t("Record more API usage", r.status_code, 200)

    r = c.post(f"{EP}/usage", json={"tenant_id": "tenant_a",
               "usage_type": "storage_gb", "usage_value": 3.5}, headers=H_A)
    t("Record storage usage", r.status_code, 200)

    r = c.get(f"{EP}/usage", headers=H_A)
    t("List usage", r.status_code, 200)
    t("Three usage records", len(r.json()["data"]), 3)

    r = c.get(f"{EP}/usage?usage_type=api_calls", headers=H_A)
    t("Filter API calls", r.status_code, 200)
    t("Two API call records", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/usage/summary?usage_type=api_calls", headers=H_A)
    t("Usage summary", r.status_code, 200)
    t("Total API calls", r.json()["data"]["total"], 3800)

    r = c.post(f"{EP}/usage", json={"tenant_id": "tenant_b",
               "usage_type": "api_calls", "usage_value": 500}, headers=H_A)
    t("Record B usage", r.status_code, 200)

    r = c.get(f"{EP}/usage", headers=H_B)
    t("B sees own usage only", len(r.json()["data"]), 1)


def test_rbac(c):
    print("\n--- 6. RBAC ---")
    r = c.get(f"{EP}/tenants", headers=HV)
    t("Viewer can list tenants", r.status_code, 200)
    r = c.post(f"{EP}/tenants", json={"tenant_id": "x", "name": "x", "slug": "x"}, headers=HV)
    t("Viewer cannot create tenant", r.status_code, 403)
    r = c.get(f"{EP}/plans", headers=HV)
    t("Viewer can list plans", r.status_code, 200)
    r = c.get(f"{EP}/features", headers=HV)
    t("Viewer can list features", r.status_code, 200)
    r = c.get(f"{EP}/usage", headers=HV)
    t("Viewer can list usage", r.status_code, 200)


def test_negative(c):
    print("\n--- 7. Negative Tests ---")
    r = c.get(f"{EP}/tenants/nonexistent", headers=H_A)
    t("Get non-existent tenant", r.status_code, 404)
    r = c.get(f"{EP}/plans/nonexistent", headers=H_A)
    t("Get non-existent plan", r.status_code, 404)
    r = c.get(f"{EP}/features/nonexistent", headers=H_A)
    t("Get non-existent feature", r.status_code, 404)
    r = c.post(f"{EP}/tenants", json={}, headers=H_A)
    t("Create tenant missing fields", r.status_code, 400)
    r = c.post(f"{EP}/plans", json={}, headers=H_A)
    t("Create plan missing fields", r.status_code, 400)
    r = c.post(f"{EP}/features", json={}, headers=H_A)
    t("Create feature missing fields", r.status_code, 400)
    r = c.post(f"{EP}/usage", json={}, headers=H_A)
    t("Record usage missing fields", r.status_code, 400)


if __name__ == "__main__":
    print("=" * 60)
    print("P41 SAAS CONTROL PLANE TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_tenants(c)
        pid1, pid2 = test_plans(c)
        fid1, fid2, fid3 = test_features(c)
        test_tenant_features(c, fid1, fid2, fid3)
        test_usage(c)
        test_rbac(c)
        test_negative(c)
    finally:
        c.close()
        stop(proc)
        cleanup()
    print("\n" + "=" * 60)
    print(f"P41 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
