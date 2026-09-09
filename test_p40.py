"""
P40 Production Validation Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/ops"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
HV = {"Authorization": f"Bearer {TOKEN_V}"}
CID_A = "co_p40"
CID_B = "co_p40_b"
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
        db.execute(sa("DELETE FROM dbp_companies WHERE id IN (:a, :b)"), {"a": CID_A, "b": CID_B})
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES (:id, 'tenant_a', 'CP40A', 'P40 Company A')"), {"id": CID_A})
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES (:id, 'tenant_b', 'CP40B', 'P40 Company B')"), {"id": CID_B})
        for tbl in ['dbp_validation_rules','dbp_validation_results','dbp_health_checks',
                     'dbp_ssl_certificates','dbp_environment_configs','dbp_security_scans']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()


def cleanup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        db.execute(sa("DELETE FROM dbp_companies WHERE id IN (:a, :b)"), {"a": CID_A, "b": CID_B})
        for tbl in ['dbp_validation_rules','dbp_validation_results','dbp_health_checks',
                     'dbp_ssl_certificates','dbp_environment_configs','dbp_security_scans']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()


def test_validation_rules(c):
    print("\n--- 1. Validation Rules ---")
    r = c.post(f"{EP}/validation-rules", json={"rule_name": "DB Connection",
               "rule_type": "infrastructure", "check_command": "pg_isready",
               "expected_value": "ok", "severity": "critical"}, headers=H_A)
    t("Create validation rule", r.status_code, 200)
    rid = r.json()["data"]["id"]

    r = c.get(f"{EP}/validation-rules", headers=H_A)
    t("List rules", r.status_code, 200)
    t("Rules not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/validation-rules/{rid}", headers=H_A)
    t("Get rule", r.status_code, 200)
    t("Rule severity critical", r.json()["data"]["severity"], "critical")

    r = c.put(f"{EP}/validation-rules/{rid}", json={"severity": "warning"}, headers=H_A)
    t("Update rule", r.status_code, 200)

    r = c.get(f"{EP}/validation-rules/{rid}", headers=H_A)
    t("Rule updated", r.json()["data"]["severity"], "warning")

    r = c.get(f"{EP}/validation-rules/{rid}", headers=H_B)
    t("Tenant B cant see A rule", r.status_code, 404)

    return rid


def test_validation_results(c, rule_id):
    print("\n--- 2. Validation Results ---")
    r = c.post(f"{EP}/validation-results", json={"check_type": "infrastructure",
               "status": "pass", "rule_id": rule_id, "rule_name": "DB Connection",
               "actual_value": "ok", "expected_value": "ok",
               "message": "Database responsive", "execution_time_ms": 15}, headers=H_A)
    t("Record result", r.status_code, 200)

    r = c.post(f"{EP}/validation-results", json={"check_type": "security",
               "status": "fail", "rule_name": "SSL Check",
               "actual_value": "expired", "expected_value": "valid",
               "message": "Certificate expired"}, headers=H_A)
    t("Record fail result", r.status_code, 200)

    r = c.get(f"{EP}/validation-results", headers=H_A)
    t("List results", r.status_code, 200)
    t("Results not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/validation-results?status=fail", headers=H_A)
    t("Filter by status", r.status_code, 200)
    t("Fail results found", len(r.json()["data"]) > 0, True)


def test_health_checks(c):
    print("\n--- 3. Health Checks ---")
    r = c.post(f"{EP}/health-checks", json={"check_name": "API Health",
               "check_type": "http", "target": "http://localhost:8000/api/v1/dynamic/system/health"}, headers=H_A)
    t("Create health check", r.status_code, 200)
    hid = r.json()["data"]["id"]

    r = c.get(f"{EP}/health-checks", headers=H_A)
    t("List health checks", r.status_code, 200)
    t("Health checks not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/health-checks/{hid}", headers=H_A)
    t("Get health check", r.status_code, 200)
    t("Check status pending", r.json()["data"]["status"], "pending")

    r = c.put(f"{EP}/health-checks/{hid}", json={"status": "healthy",
               "response_time_ms": 12, "message": "All OK"}, headers=H_A)
    t("Update to healthy", r.status_code, 200)

    r = c.get(f"{EP}/health-checks/{hid}", headers=H_A)
    t("Check is healthy", r.json()["data"]["status"], "healthy")
    t("Response time set", r.json()["data"]["response_time_ms"], 12)

    r = c.put(f"{EP}/health-checks/{hid}", json={"status": "degraded",
               "message": "High latency"}, headers=H_A)
    t("Update to degraded", r.status_code, 200)

    r = c.get(f"{EP}/health-checks/{hid}", headers=H_B)
    t("Tenant B cant see A check", r.status_code, 404)

    return hid


def test_ssl_certificates(c):
    print("\n--- 4. SSL Certificates ---")
    r = c.post(f"{EP}/ssl-certificates", json={"domain": "api.eos-platform.com",
               "issuer": "Let's Encrypt", "serial_number": "ABC123",
               "not_before": "2025-01-01T00:00:00Z", "not_after": "2026-01-01T00:00:00Z",
               "auto_renew": True}, headers=H_A)
    t("Register SSL cert", r.status_code, 200)
    sid = r.json()["data"]["id"]

    r = c.get(f"{EP}/ssl-certificates", headers=H_A)
    t("List SSL certs", r.status_code, 200)
    t("SSL certs not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/ssl-certificates/{sid}", headers=H_A)
    t("Get SSL cert", r.status_code, 200)
    t("Cert domain correct", r.json()["data"]["domain"], "api.eos-platform.com")
    t("Cert auto_renew", r.json()["data"]["auto_renew"], True)

    r = c.put(f"{EP}/ssl-certificates/{sid}", json={"status": "expiring_soon"}, headers=H_A)
    t("Update cert status", r.status_code, 200)

    r = c.get(f"{EP}/ssl-certificates/{sid}", headers=H_A)
    t("Cert status expiring", r.json()["data"]["status"], "expiring_soon")

    r = c.get(f"{EP}/ssl-certificates/{sid}", headers=H_B)
    t("Tenant B cant see A cert", r.status_code, 404)

    return sid


def test_env_configs(c):
    print("\n--- 5. Environment Configs ---")
    r = c.post(f"{EP}/env-configs", json={"environment": "production",
               "config_key": "db_pool_size", "config_value": "20",
               "description": "Database pool size"}, headers=H_A)
    t("Set env config", r.status_code, 200)
    eid = r.json()["data"]["id"]

    r = c.post(f"{EP}/env-configs", json={"environment": "production",
               "config_key": "db_pool_size", "config_value": "30"}, headers=H_A)
    t("Upsert config", r.status_code, 200)

    r = c.get(f"{EP}/env-configs?environment=production", headers=H_A)
    t("List prod configs", r.status_code, 200)
    t("Prod configs not empty", len(r.json()["data"]) > 0, True)

    configs = r.json()["data"]
    pool_cfg = [x for x in configs if x.get("config_key") == "db_pool_size"]
    if pool_cfg:
        t("Upsert updated value", pool_cfg[0]["config_value"], "30")

    r = c.post(f"{EP}/env-configs", json={"environment": "staging",
               "config_key": "debug_mode", "config_value": "true",
               "is_sensitive": False}, headers=H_A)
    t("Set staging config", r.status_code, 200)

    r = c.get(f"{EP}/env-configs?environment=staging", headers=H_A)
    t("List staging configs", r.status_code, 200)
    t("Staging configs found", len(r.json()["data"]) > 0, True)

    r = c.delete(f"{EP}/env-configs/{eid}", headers=H_A)
    t("Delete env config", r.status_code, 200)

    r = c.get(f"{EP}/env-configs", headers=H_B)
    t("Tenant B no A configs", len(r.json()["data"]), 0)


def test_security_scans(c):
    print("\n--- 6. Security Scans ---")
    r = c.post(f"{EP}/security-scans", json={"scan_type": "vulnerability",
               "target": "eos-platform"}, headers=H_A)
    t("Create security scan", r.status_code, 200)
    sid = r.json()["data"]["id"]

    r = c.get(f"{EP}/security-scans", headers=H_A)
    t("List scans", r.status_code, 200)
    t("Scans not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/security-scans/{sid}", headers=H_A)
    t("Get scan", r.status_code, 200)
    t("Scan running", r.json()["data"]["status"], "running")

    r = c.put(f"{EP}/security-scans/{sid}", json={"status": "completed",
               "vulnerabilities_found": 3, "critical_count": 0,
               "high_count": 1, "medium_count": 2, "low_count": 0,
               "report_url": "https://reports.eos.com/scan/123"}, headers=H_A)
    t("Complete scan", r.status_code, 200)

    r = c.get(f"{EP}/security-scans/{sid}", headers=H_A)
    t("Scan completed", r.json()["data"]["status"], "completed")
    t("Vulns found", r.json()["data"]["vulnerabilities_found"], 3)
    t("High count", r.json()["data"]["high_count"], 1)

    r = c.get(f"{EP}/security-scans/{sid}", headers=H_B)
    t("Tenant B cant see A scan", r.status_code, 404)


def test_rbac(c):
    print("\n--- 7. RBAC ---")
    r = c.get(f"{EP}/validation-rules", headers=HV)
    t("Viewer can list rules", r.status_code, 200)
    r = c.post(f"{EP}/validation-rules", json={"rule_name": "x", "rule_type": "x", "check_command": "x"}, headers=HV)
    t("Viewer cannot create rule", r.status_code, 403)
    r = c.get(f"{EP}/health-checks", headers=HV)
    t("Viewer can list health checks", r.status_code, 200)
    r = c.get(f"{EP}/ssl-certificates", headers=HV)
    t("Viewer can list certs", r.status_code, 200)
    r = c.get(f"{EP}/env-configs", headers=HV)
    t("Viewer can list configs", r.status_code, 200)
    r = c.get(f"{EP}/security-scans", headers=HV)
    t("Viewer can list scans", r.status_code, 200)


def test_negative(c):
    print("\n--- 8. Negative Tests ---")
    r = c.get(f"{EP}/validation-rules/nonexistent", headers=H_A)
    t("Get non-existent rule", r.status_code, 404)
    r = c.get(f"{EP}/health-checks/nonexistent", headers=H_A)
    t("Get non-existent health check", r.status_code, 404)
    r = c.get(f"{EP}/ssl-certificates/nonexistent", headers=H_A)
    t("Get non-existent cert", r.status_code, 404)
    r = c.get(f"{EP}/security-scans/nonexistent", headers=H_A)
    t("Get non-existent scan", r.status_code, 404)
    r = c.post(f"{EP}/validation-rules", json={}, headers=H_A)
    t("Create rule missing fields", r.status_code, 400)
    r = c.post(f"{EP}/health-checks", json={}, headers=H_A)
    t("Create health check missing fields", r.status_code, 400)
    r = c.post(f"{EP}/ssl-certificates", json={}, headers=H_A)
    t("Create cert missing fields", r.status_code, 400)
    r = c.post(f"{EP}/security-scans", json={}, headers=H_A)
    t("Create scan missing fields", r.status_code, 400)
    r = c.post(f"{EP}/env-configs", json={}, headers=H_A)
    t("Set config missing fields", r.status_code, 400)
    r = c.delete(f"{EP}/env-configs/nonexistent", headers=H_A)
    t("Delete non-existent config", r.status_code, 404)


if __name__ == "__main__":
    print("=" * 60)
    print("P40 PRODUCTION VALIDATION TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        rid = test_validation_rules(c)
        test_validation_results(c, rid)
        test_health_checks(c)
        test_ssl_certificates(c)
        test_env_configs(c)
        test_security_scans(c)
        test_rbac(c)
        test_negative(c)
    finally:
        c.close()
        stop(proc)
        cleanup()
    print("\n" + "=" * 60)
    print(f"P40 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
