"""
P37 SYSTEM INTEGRATION & HEALTH TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
CID_A = "co_p37"
CID_B = "co_p37_b"
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
        for tbl in ("dbp_data_exports", "dbp_data_imports", "dbp_integration_logs", "dbp_system_config"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE id IN ('co_p37','co_p37_b')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p37','tenant_a','CP37A','Company P37 A')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p37_b','tenant_b','CP37B','Company P37 B')"))
        db.commit()
    finally:
        db.close()


def cleanup_final():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ("dbp_data_exports", "dbp_data_imports", "dbp_integration_logs", "dbp_system_config"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE id IN ('co_p37','co_p37_b')"))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    c = httpx.Client(timeout=30)

    print("=" * 60)
    print("P37 SYSTEM INTEGRATION & HEALTH TESTS")
    print("=" * 60)

    setup()
    proc = start()

    try:
        # --- 1. Set Config ---
        print("\n--- 1. Set Config ---")
        r = c.post(f"{BASE}{EP}/system/config",
                   json={"config_key": "currency_default", "config_value": {"code": "USD"},
                         "description": "Default currency", "category": "finance"},
                   headers=H_A)
        t("Set config", r.status_code, 200)
        cfg_id = r.json()["data"]["id"]
        t("Has id", bool(cfg_id), True)

        # --- 2. Get Config ---
        print("\n--- 2. Get Config ---")
        r = c.get(f"{BASE}{EP}/system/config", headers=H_A)
        t("List configs", r.status_code, 200)
        keys = [item["config_key"] for item in r.json()["data"]]
        t("Config found", "currency_default" in keys, True)

        # --- 3. Upsert Config (update existing) ---
        print("\n--- 3. Upsert Config ---")
        r = c.post(f"{BASE}{EP}/system/config",
                   json={"config_key": "currency_default", "config_value": {"code": "EUR"},
                         "description": "Updated currency", "category": "finance"},
                   headers=H_A)
        t("Upsert config", r.status_code, 200)
        cfg_id2 = r.json()["data"]["id"]
        t("Same id on upsert", cfg_id2, cfg_id)

        # --- 4. Verify updated value ---
        print("\n--- 4. Verify Updated Value ---")
        r = c.get(f"{BASE}{EP}/system/config?category=finance", headers=H_A)
        t("List by category", r.status_code, 200)
        matched = [i for i in r.json()["data"] if i["config_key"] == "currency_default"]
        t("Found in category", len(matched), 1)
        if matched:
            t("Value updated", matched[0]["config_value"]["code"], "EUR")

        # --- 5. List Configs ---
        print("\n--- 5. List Configs ---")
        r = c.get(f"{BASE}{EP}/system/config", headers=H_A)
        t("List all configs", r.status_code, 200)
        t("Has configs", len(r.json()["data"]) >= 1, True)

        # --- 6. Delete Config ---
        print("\n--- 6. Delete Config ---")
        r = c.delete(f"{BASE}{EP}/system/config/currency_default", headers=H_A)
        t("Delete config", r.status_code, 200)
        r = c.get(f"{BASE}{EP}/system/config", headers=H_A)
        keys_after = [item["config_key"] for item in r.json()["data"]]
        t("Config deleted", "currency_default" not in keys_after, True)

        # --- 7. Delete Non-existent Config ---
        print("\n--- 7. Delete Non-existent Config ---")
        r = c.delete(f"{BASE}{EP}/system/config/nonexistent", headers=H_A)
        t("404 delete", r.status_code, 404)

        # --- 8. System Health ---
        print("\n--- 8. System Health ---")
        r = c.get(f"{BASE}{EP}/system/health", headers=H_A)
        t("Health check", r.status_code, 200)
        health = r.json()["data"]
        t("Status healthy", health["status"], "healthy")
        t("Version 1.0.0", health["version"], "1.0.0")
        t("Has modules", len(health["modules"]) >= 6, True)

        # --- 9. Health Modules Active ---
        print("\n--- 9. Health Modules Active ---")
        active = [m for m in health["modules"] if m["status"] == "active"]
        t("All 6 active", len(active), 6)

        # --- 10. Create Inbound Log ---
        print("\n--- 10. Create Inbound Log ---")
        r = c.post(f"{BASE}{EP}/integration-logs",
                   json={"integration_type": "edi", "direction": "inbound",
                         "status": "success", "company_id": CID_A,
                         "entity_type": "invoice", "payload_summary": "EDI order received",
                         "duration_ms": 120},
                   headers=H_A)
        t("Create inbound log", r.status_code, 200)
        lid1 = r.json()["data"]["id"]

        # --- 11. Create Outbound Log ---
        print("\n--- 11. Create Outbound Log ---")
        r = c.post(f"{BASE}{EP}/integration-logs",
                   json={"integration_type": "api", "direction": "outbound",
                         "status": "failed", "company_id": CID_A,
                         "entity_type": "payment", "error_message": "Timeout",
                         "duration_ms": 5000},
                   headers=H_A)
        t("Create outbound log", r.status_code, 200)
        lid2 = r.json()["data"]["id"]

        # --- 12. List Integration Logs ---
        print("\n--- 12. List Integration Logs ---")
        r = c.get(f"{BASE}{EP}/integration-logs", headers=H_A)
        t("List logs", r.status_code, 200)
        t("Has 2+ logs", len(r.json()["data"]) >= 2, True)

        # --- 13. Filter Logs by Status ---
        print("\n--- 13. Filter Logs by Status ---")
        r = c.get(f"{BASE}{EP}/integration-logs?status=failed", headers=H_A)
        t("Filter failed", r.status_code, 200)
        statuses = [l["status"] for l in r.json()["data"]]
        t("All failed", all(s == "failed" for s in statuses), True)

        # --- 14. Filter Logs by Integration Type ---
        print("\n--- 14. Filter Logs by Integration Type ---")
        r = c.get(f"{BASE}{EP}/integration-logs?integration_type=edi", headers=H_A)
        t("Filter edi", r.status_code, 200)
        types = [l["integration_type"] for l in r.json()["data"]]
        t("All edi", all(t2 == "edi" for t2 in types), True)

        # --- 15. Create Data Import ---
        print("\n--- 15. Create Data Import ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/data-imports",
                   json={"import_type": "customers", "file_name": "customers.csv",
                         "record_count": 100},
                   headers=H_A)
        t("Create import", r.status_code, 200)
        iid = r.json()["data"]["id"]

        # --- 16. Update Data Import (progress) ---
        print("\n--- 16. Update Data Import ---")
        r = c.put(f"{BASE}{EP}/data-imports/{iid}",
                  json={"success_count": 80, "error_count": 20, "status": "completed"},
                  headers=H_A)
        t("Update import", r.status_code, 200)
        t("Status completed", r.json()["data"]["status"], "completed")
        t("Success 80", r.json()["data"]["success_count"], 80)

        # --- 17. List Data Imports ---
        print("\n--- 17. List Data Imports ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/data-imports", headers=H_A)
        t("List imports", r.status_code, 200)
        t("Has 1+ import", len(r.json()["data"]) >= 1, True)

        # --- 18. Filter Imports by Status ---
        print("\n--- 18. Filter Imports by Status ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/data-imports?status=completed", headers=H_A)
        t("Filter completed imports", r.status_code, 200)
        imp_statuses = [i["status"] for i in r.json()["data"]]
        t("All completed", all(s == "completed" for s in imp_statuses), True)

        # --- 19. Create Data Export ---
        print("\n--- 19. Create Data Export ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/data-exports",
                   json={"export_type": "invoices", "record_count": 500, "file_format": "xlsx"},
                   headers=H_A)
        t("Create export", r.status_code, 200)
        eid = r.json()["data"]["id"]

        # --- 20. Verify Auto expires_at ---
        print("\n--- 20. Verify Auto expires_at ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/data-exports", headers=H_A)
        t("List exports", r.status_code, 200)
        exp_rec = [e for e in r.json()["data"] if e["id"] == eid]
        t("Found export", len(exp_rec), 1)
        if exp_rec:
            t("Has expires_at", exp_rec[0]["expires_at"] is not None, True)

        # --- 21. List Data Exports ---
        print("\n--- 21. List Data Exports ---")
        t("Has 1+ export", len(r.json()["data"]) >= 1, True)

        # --- 22. Filter Exports by Type ---
        print("\n--- 22. Filter Exports by Type ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/data-exports?export_type=invoices", headers=H_A)
        t("Filter invoices exports", r.status_code, 200)
        exp_types = [e["export_type"] for e in r.json()["data"]]
        t("All invoices", all(et == "invoices" for et in exp_types), True)

        # --- 23. Tenant Isolation - Config ---
        print("\n--- 23. Tenant Isolation - Config ---")
        c.post(f"{BASE}{EP}/system/config",
               json={"config_key": "b_secret", "config_value": {"key": "secret"}},
               headers=H_B)
        r = c.get(f"{BASE}{EP}/system/config", headers=H_A)
        keys_a = [item["config_key"] for item in r.json()["data"]]
        t("B config not visible to A", "b_secret" not in keys_a, True)

        # --- 24. Tenant Isolation - Integration Logs ---
        print("\n--- 24. Tenant Isolation - Integration Logs ---")
        c.post(f"{BASE}{EP}/integration-logs",
               json={"integration_type": "edi", "direction": "inbound",
                     "status": "success", "company_id": CID_B},
               headers=H_B)
        r = c.get(f"{BASE}{EP}/integration-logs", headers=H_A)
        for log in r.json()["data"]:
            t("Log tenant isolation", log["tenant_id"], "tenant_a")

        # --- 25. Tenant Isolation - Data Imports ---
        print("\n--- 25. Tenant Isolation - Data Imports ---")
        c.post(f"{BASE}{EP}/companies/{CID_B}/data-imports",
               json={"import_type": "vendors", "file_name": "vendors.csv"},
               headers=H_B)
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/data-imports", headers=H_A)
        for imp in r.json()["data"]:
            t("Import tenant isolation", imp["tenant_id"], "tenant_a")

        # --- 26. Tenant Isolation - Data Exports ---
        print("\n--- 26. Tenant Isolation - Data Exports ---")
        c.post(f"{BASE}{EP}/companies/{CID_B}/data-exports",
               json={"export_type": "payments", "record_count": 100},
               headers=H_B)
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/data-exports", headers=H_A)
        for exp in r.json()["data"]:
            t("Export tenant isolation", exp["tenant_id"], "tenant_a")

        # --- 27. Update Non-existent Import ---
        print("\n--- 27. Update Non-existent Import ---")
        r = c.put(f"{BASE}{EP}/data-imports/nonexistent",
                  json={"status": "completed"}, headers=H_A)
        t("404 update import", r.status_code, 404)

        # --- 28. Missing Required Fields - Log ---
        print("\n--- 28. Missing Required Fields - Log ---")
        r = c.post(f"{BASE}{EP}/integration-logs",
                   json={"integration_type": "edi"},
                   headers=H_A)
        t("Missing fields log", r.status_code, 400)

        # --- 29. Missing Required Fields - Import ---
        print("\n--- 29. Missing Required Fields - Import ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/data-imports",
                   json={"file_name": "test.csv"},
                   headers=H_A)
        t("Missing import_type", r.status_code, 400)

        # --- 30. Missing Required Fields - Export ---
        print("\n--- 30. Missing Required Fields - Export ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/data-exports",
                   json={"export_type": "reports"},
                   headers=H_A)
        t("Missing record_count", r.status_code, 400)

    finally:
        stop(proc)
        cleanup_final()
        c.close()

    print(f"\n{'='*60}")
    print(f"P37 RESULTS: {p}/{p + f} PASSED, {f} FAILED")
    print(f"{'='*60}")

    sys.exit(0 if f == 0 else 1)
