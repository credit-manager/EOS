"""
P50 Platform Maturity Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/platform"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
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
        for tbl in ['dbp_certification_scores', 'dbp_maturity_metrics',
                     'dbp_upgrade_history', 'dbp_platform_health']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_platform_features WHERE feature_name LIKE 'test_%'"))
        db.commit()
    finally:
        db.close()

def cleanup(): setup()


def test_certifications(c):
    print("\n--- 1. Certifications ---")
    r = c.post(f"{EP}/certifications", json={"certification_level": "Gold",
               "total_score": 850, "max_score": 1000, "status": "certified"}, headers=H_A)
    t("Create certification", r.status_code, 200)
    sid = r.json()["data"]["id"]
    r = c.get(f"{EP}/certifications", headers=H_A)
    t("List certifications", r.status_code, 200)
    t("One certification", len(r.json()["data"]), 1)
    r = c.get(f"{EP}/certifications/{sid}", headers=H_A)
    t("Get certification", r.status_code, 200)
    t("Level correct", r.json()["data"]["certification_level"], "Gold")
    r = c.get(f"{EP}/certifications", headers=H_B)
    t("Tenant B no A certifications", len(r.json()["data"]), 0)


def test_metrics(c):
    print("\n--- 2. Maturity Metrics ---")
    r = c.post(f"{EP}/metrics", json={"metric_category": "performance",
               "metric_name": "api_response_time", "metric_value": 45.2,
               "target_value": 100.0}, headers=H_A)
    t("Record metric", r.status_code, 200)
    r = c.post(f"{EP}/metrics", json={"metric_category": "security",
               "metric_name": "vulnerability_count", "metric_value": 0}, headers=H_A)
    t("Record second metric", r.status_code, 200)
    r = c.get(f"{EP}/metrics", headers=H_A)
    t("List metrics", r.status_code, 200)
    t("Two metrics", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/metrics?metric_category=performance", headers=H_A)
    t("Filter by category", r.status_code, 200)
    t("One performance metric", len(r.json()["data"]), 1)


def test_features(c):
    print("\n--- 3. Platform Features ---")
    r = c.post(f"{EP}/features", json={"feature_name": "test_dynamic_crud",
               "feature_category": "core", "version_added": "1.0.0",
               "is_stable": True}, headers=H_A)
    t("Register feature", r.status_code, 200)
    fid = r.json()["data"]["id"]
    r = c.post(f"{EP}/features", json={"feature_name": "test_ai_analytics",
               "feature_category": "analytics", "version_added": "2.0.0"}, headers=H_A)
    t("Register second feature", r.status_code, 200)
    r = c.get(f"{EP}/features", headers=H_A)
    t("List features", r.status_code, 200)
    t("Two features", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/features?feature_category=core", headers=H_A)
    t("Filter by category", r.status_code, 200)
    r = c.put(f"{EP}/features/{fid}", json={"is_stable": True}, headers=H_A)
    t("Update feature", r.status_code, 200)


def test_upgrades(c):
    print("\n--- 4. Upgrade History ---")
    r = c.post(f"{EP}/upgrades", json={"from_version": "1.0.0",
               "to_version": "2.0.0", "upgrade_type": "major",
               "notes": "Added P39-P50 features"}, headers=H_A)
    t("Record upgrade", r.status_code, 200)
    r = c.get(f"{EP}/upgrades", headers=H_A)
    t("List upgrades", r.status_code, 200)
    t("One upgrade", len(r.json()["data"]), 1)
    r = c.get(f"{EP}/upgrades", headers=H_B)
    t("Tenant B no A upgrades", len(r.json()["data"]), 0)


def test_health(c):
    print("\n--- 5. Platform Health ---")
    r = c.post(f"{EP}/health", json={"component_name": "database",
               "health_score": 98.5, "status": "healthy"}, headers=H_A)
    t("Record health", r.status_code, 200)
    r = c.post(f"{EP}/health", json={"component_name": "api_server",
               "health_score": 95.0, "status": "healthy"}, headers=H_A)
    t("Record second health", r.status_code, 200)
    r = c.get(f"{EP}/health", headers=H_A)
    t("List health", r.status_code, 200)
    t("Two health records", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/health?component_name=database", headers=H_A)
    t("Filter by component", r.status_code, 200)
    t("One database health", len(r.json()["data"]), 1)


def test_negative(c):
    print("\n--- 6. Negative Tests ---")
    r = c.post(f"{EP}/certifications", json={}, headers=H_A)
    t("Create cert missing fields", r.status_code, 400)
    r = c.post(f"{EP}/metrics", json={}, headers=H_A)
    t("Record metric missing fields", r.status_code, 400)
    r = c.post(f"{EP}/features", json={}, headers=H_A)
    t("Register feature missing fields", r.status_code, 400)
    r = c.get(f"{EP}/certifications/nonexistent", headers=H_A)
    t("Get non-existent cert", r.status_code, 404)


if __name__ == "__main__":
    print("=" * 60)
    print("P50 PLATFORM MATURITY TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_certifications(c); test_metrics(c); test_features(c)
        test_upgrades(c); test_health(c); test_negative(c)
    finally:
        c.close(); stop(proc); cleanup()
    print("\n" + "=" * 60)
    print(f"P50 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
