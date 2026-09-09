"""
P46 Compliance & Policy Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/compliance"
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
        for tbl in ['dbp_compliance_policies', 'dbp_compliance_checks',
                     'dbp_compliance_violations', 'dbp_compliance_audit_log',
                     'dbp_compliance_frameworks']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()


def cleanup():
    setup()


def test_policies(c):
    print("\n--- 1. Compliance Policies ---")
    r = c.post(f"{EP}/policies", json={"policy_name": "Data Retention",
               "policy_type": "data_governance", "rules_config": {"retention_days": 365},
               "severity": "high"}, headers=H_A)
    t("Create policy", r.status_code, 200)
    pid = r.json()["data"]["id"]
    r = c.post(f"{EP}/policies", json={"policy_name": "Access Control",
               "policy_type": "security", "rules_config": {"min_role": "manager"}}, headers=H_A)
    t("Create second policy", r.status_code, 200)
    r = c.get(f"{EP}/policies", headers=H_A)
    t("List policies", r.status_code, 200)
    t("Two policies", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/policies/{pid}", headers=H_A)
    t("Get policy", r.status_code, 200)
    t("Name correct", r.json()["data"]["policy_name"], "Data Retention")
    r = c.put(f"{EP}/policies/{pid}", json={"severity": "critical"}, headers=H_A)
    t("Update policy", r.status_code, 200)
    r = c.delete(f"{EP}/policies/{pid}", headers=H_A)
    t("Delete policy", r.status_code, 200)
    r = c.get(f"{EP}/policies", headers=H_B)
    t("Tenant B no A policies", len(r.json()["data"]), 0)


def test_checks(c):
    print("\n--- 2. Compliance Checks ---")
    pid = c.post(f"{EP}/policies", json={"policy_name": "Test",
               "policy_type": "test", "rules_config": {}}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/checks", json={"policy_id": pid, "check_name": "Retention Check",
               "check_type": "automated", "target_entity": "companies"}, headers=H_A)
    t("Create check", r.status_code, 200)
    cid = r.json()["data"]["id"]
    r = c.put(f"{EP}/checks/{cid}/run", json={"status": "passed",
               "result_detail": {"records_checked": 500}}, headers=H_A)
    t("Run check", r.status_code, 200)
    r = c.get(f"{EP}/checks", headers=H_A)
    t("List checks", r.status_code, 200)
    t("One check", len(r.json()["data"]), 1)


def test_violations(c):
    print("\n--- 3. Violations ---")
    pid = c.post(f"{EP}/policies", json={"policy_name": "Test",
               "policy_type": "test", "rules_config": {}}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/violations", json={"policy_id": pid,
               "violation_type": "expired_data", "severity": "high",
               "entity_type": "companies", "description": "Data older than 365 days"}, headers=H_A)
    t("Create violation", r.status_code, 200)
    vid = r.json()["data"]["id"]
    r = c.get(f"{EP}/violations", headers=H_A)
    t("List violations", r.status_code, 200)
    t("One violation", len(r.json()["data"]), 1)
    r = c.put(f"{EP}/violations/{vid}/resolve", headers=H_A)
    t("Resolve violation", r.status_code, 200)
    r = c.get(f"{EP}/violations", headers=H_B)
    t("Tenant B no A violations", len(r.json()["data"]), 0)


def test_audit_log(c):
    print("\n--- 4. Audit Log ---")
    r = c.post(f"{EP}/audit-log", json={"action": "policy_created",
               "entity_type": "policy", "details": {"name": "test"}}, headers=H_A)
    t("Log action", r.status_code, 200)
    r = c.get(f"{EP}/audit-log", headers=H_A)
    t("List audit log", r.status_code, 200)
    t("One entry", len(r.json()["data"]), 1)


def test_frameworks(c):
    print("\n--- 5. Frameworks ---")
    r = c.post(f"{EP}/frameworks", json={"framework_name": "SOC 2",
               "framework_type": "security", "version": "2024",
               "requirements": ["access_control", "encryption", "monitoring"]}, headers=H_A)
    t("Create framework", r.status_code, 200)
    r = c.get(f"{EP}/frameworks", headers=H_A)
    t("List frameworks", r.status_code, 200)
    t("One framework", len(r.json()["data"]), 1)
    r = c.get(f"{EP}/frameworks", headers=H_B)
    t("Tenant B no A frameworks", len(r.json()["data"]), 0)


def test_negative(c):
    print("\n--- 6. Negative Tests ---")
    r = c.post(f"{EP}/policies", json={}, headers=H_A)
    t("Create policy missing fields", r.status_code, 400)
    r = c.post(f"{EP}/checks", json={}, headers=H_A)
    t("Create check missing fields", r.status_code, 400)
    r = c.post(f"{EP}/violations", json={}, headers=H_A)
    t("Create violation missing fields", r.status_code, 400)
    r = c.get(f"{EP}/policies/nonexistent", headers=H_A)
    t("Get non-existent policy", r.status_code, 404)


if __name__ == "__main__":
    print("=" * 60)
    print("P46 COMPLIANCE & POLICY TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_policies(c)
        test_checks(c)
        test_violations(c)
        test_audit_log(c)
        test_frameworks(c)
        test_negative(c)
    finally:
        c.close(); stop(proc); cleanup()
    print("\n" + "=" * 60)
    print(f"P46 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
