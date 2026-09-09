"""
P31 AUDIT & COMPLIANCE TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p31"

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
        for tbl in ("dbp_audit_exports", "dbp_data_access_logs", "dbp_compliance_rules", "dbp_audit_trail"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p31', 'tenant_a', 'CO31', 'Test')"))
        db.commit()
    finally:
        db.close()

def test_audit_trail(c):
    print("\n--- 1. Audit Trail ---")
    r = c.post(f"{EP}/companies/{CID}/audit-exports", headers=H, json={
        "export_type": "full", "from_date": "2025-01-01", "to_date": "2025-12-31"
    })
    t("Create export trigger", r.status_code, 200)

    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    from core.audit_engine import AuditComplianceEngine
    eng = AuditComplianceEngine(db)
    eid1 = eng.log_audit_event("tenant_a", CID, "company", "create",
        actor_id="admin", actor_email="admin@test.com",
        new_values={"name": "Test Co"}, ip_address="127.0.0.1")
    eid2 = eng.log_audit_event("tenant_a", CID, "company", "update",
        actor_id="admin", old_values={"name": "Test Co"}, new_values={"name": "Test Co Updated"})
    db.commit()
    db.close()

    r = c.get(f"{EP}/companies/{CID}/audit-trail", headers=H)
    t("List audit trail", r.status_code, 200)
    t("Has 2 events", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/companies/{CID}/audit-trail?entity_type=company", headers=H)
    t("Filter by entity_type", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/companies/{CID}/audit-trail?actor_id=admin", headers=H)
    t("Filter by actor", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/companies/{CID}/audit-trail/entity/company/{eid1}", headers=H)
    t("Entity history", r.status_code, 200)

def test_access_logs(c):
    print("\n--- 2. Access Logs ---")
    r = c.post(f"{EP}/companies/{CID}/access-logs", headers=H, json={
        "user_id": "admin", "user_email": "admin@test.com",
        "action": "read", "resource_type": "company", "resource_id": "co_p31",
        "access_granted": True, "ip_address": "127.0.0.1"
    })
    t("Log access granted", r.status_code, 200)

    r = c.post(f"{EP}/companies/{CID}/access-logs", headers=H, json={
        "user_id": "hacker", "action": "delete", "resource_type": "company",
        "access_granted": False, "denial_reason": "Insufficient permissions"
    })
    t("Log access denied", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/access-logs", headers=H)
    t("List access logs", r.status_code, 200)
    t("Has 2 logs", len(r.json()["data"]), 2)

def test_compliance_rules(c):
    print("\n--- 3. Compliance Rules ---")
    r = c.post(f"{EP}/companies/{CID}/compliance-rules", headers=H, json={
        "rule_code": "FIN-001", "name": "Account Balance Check",
        "entity_type": "account", "category": "financial",
        "severity": "high", "rule_expression": "balance >= 0"
    })
    t("Create rule", r.status_code, 200)
    rid = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/compliance-rules", headers=H)
    t("List rules", r.status_code, 200)
    t("Has 1 rule", len(r.json()["data"]), 1)

    r = c.put(f"{EP}/compliance-rules/{rid}", headers=H, json={"is_active": False})
    t("Update rule", r.status_code, 200)

def test_compliance_check(c):
    print("\n--- 4. Compliance Check ---")
    r = c.get(f"{EP}/companies/{CID}/compliance-check", headers=H)
    t("Compliance check", r.status_code, 200)
    t("Has audit_events_30d", "audit_events_30d" in r.json()["data"], True)
    t("Has active_rules", "active_rules" in r.json()["data"], True)

def test_audit_exports(c):
    print("\n--- 5. Audit Exports ---")
    r = c.post(f"{EP}/companies/{CID}/audit-exports", headers=H, json={
        "export_type": "audit", "from_date": "2025-01-01", "to_date": "2025-06-30",
        "entity_types": "company,account"
    })
    t("Create export", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/audit-exports", headers=H)
    t("List exports", r.status_code, 200)
    t("Has exports", len(r.json()["data"]) >= 1, True)

def test_tenant_isolation(c):
    print("\n--- 6. Tenant Isolation ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/companies/{CID}/audit-trail", headers=H_B)
    t("Tenant B no audit trail", len(r.json()["data"]), 0)

if __name__ == "__main__":
    print("=" * 60)
    print("P31 AUDIT & COMPLIANCE TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_audit_trail(c)
        test_access_logs(c)
        test_compliance_rules(c)
        test_compliance_check(c)
        test_audit_exports(c)
        test_tenant_isolation(c)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P31 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
