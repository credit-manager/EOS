"""
P35 BUSINESS INTELLIGENCE & REPORTING TESTS
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
CID_A = "co_p35"
CID_B = "co_p35_b"
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
        for tbl in ("dbp_scheduled_reports", "dbp_report_runs", "dbp_report_templates",
                     "dbp_audit_trail", "dbp_payments"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
        db.execute(sa("DELETE FROM dbp_companies WHERE id IN ('co_p35','co_p35_b')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p35','tenant_a','CP35A','Company P35 A')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p35_b','tenant_b','CP35B','Company P35 B')"))
        db.commit()
    finally:
        db.close()


def seed_data(c):
    from database import SessionLocal
    from sqlalchemy import text as sa
    import json
    db = SessionLocal()
    try:
        for i in range(3):
            db.execute(sa(
                "INSERT INTO dbp_audit_trail (id, tenant_id, company_id, entity_type, entity_id, "
                "action, actor_id, actor_email, old_values, new_values, created_at) "
                "VALUES (gen_random_uuid(), 'tenant_a', :cid, 'test_entity', :eid, 'create', 'admin', 'admin@test.com', NULL, NULL, NOW())"
            ), {"cid": CID_A, "eid": f"entity-{i}"})
        db.execute(sa(
            "INSERT INTO dbp_payments (id, tenant_id, company_id, payment_number, "
            "payment_type, payment_date, amount, currency_code, exchange_rate, "
            "bank_account_id, payee_name, payee_type, reference, description, "
            "cost_center_id, created_by) "
            "VALUES (gen_random_uuid(), 'tenant_a', :cid, 'PAY-TEST-001', "
            "'receipt', '2026-01-01', 500, 'USD', 1, NULL, 'Alice', 'customer', NULL, NULL, NULL, 'admin')"
        ), {"cid": CID_A})
        db.commit()
    finally:
        db.close()


def cleanup_final():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ("dbp_scheduled_reports", "dbp_report_runs", "dbp_report_templates",
                     "dbp_audit_trail", "dbp_payments"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE id IN ('co_p35','co_p35_b')"))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    c = httpx.Client(timeout=30)

    print("=" * 60)
    print("P35 BUSINESS INTELLIGENCE & REPORTING TESTS")
    print("=" * 60)

    setup()
    proc = start()

    try:
        seed_data(c)

        # --- 1. Create Template ---
        print("\n--- 1. Create Template ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/report-templates",
                   json={"name": "Audit Report", "report_type": "table", "data_source": "audit_trail", "description": "desc"},
                   headers=H_A)
        t("Create template", r.status_code, 200)
        tpl_id = r.json()["data"]["id"]
        t("Has id", bool(tpl_id), True)

        # --- 2. List Templates ---
        print("\n--- 2. List Templates ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/report-templates", headers=H_A)
        t("List templates", r.status_code, 200)
        t("Has 1+", len(r.json()["data"]) >= 1, True)

        # --- 3. Get Template ---
        print("\n--- 3. Get Template ---")
        r = c.get(f"{BASE}{EP}/report-templates/{tpl_id}", headers=H_A)
        t("Get template", r.status_code, 200)
        t("Name correct", r.json()["data"]["name"], "Audit Report")

        # --- 4. Update Template ---
        print("\n--- 4. Update Template ---")
        r = c.put(f"{BASE}{EP}/report-templates/{tpl_id}",
                  json={"name": "Audit Report v2"},
                  headers=H_A)
        t("Update template", r.status_code, 200)
        t("Name updated", r.json()["data"]["name"], "Audit Report v2")

        # --- 5. Run Audit Report ---
        print("\n--- 5. Run Audit Report ---")
        r = c.post(f"{BASE}{EP}/report-templates/{tpl_id}/run",
                   json={"format": "json"},
                   headers=H_A)
        t("Run report", r.status_code, 200)
        run_id_a = r.json()["data"]["run_id"]
        t("Has run_id", bool(run_id_a), True)

        # --- 6. Get Run Detail ---
        print("\n--- 6. Get Run Detail ---")
        r = c.get(f"{BASE}{EP}/report-runs/{run_id_a}", headers=H_A)
        t("Get run", r.status_code, 200)
        run_detail = r.json()["data"]
        t("Status completed", run_detail["status"], "completed")

        # --- 7. Result Data Populated ---
        print("\n--- 7. Result Data Populated ---")
        t("Result count >= 0", run_detail["result_count"] >= 0, True)
        t("Result data not None", run_detail["result_data"] is not None, True)

        # --- 8. List Runs ---
        print("\n--- 8. List Runs ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/report-runs", headers=H_A)
        t("List runs", r.status_code, 200)
        t("Has 1+ runs", len(r.json()["data"]) >= 1, True)

        # --- 9. List Runs Filtered ---
        print("\n--- 9. List Runs Filtered ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/report-runs?template_id={tpl_id}", headers=H_A)
        t("Filter runs", r.status_code, 200)

        # --- 10. Payments Template ---
        print("\n--- 10. Create Payments Template ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/report-templates",
                   json={"name": "Pay Report", "report_type": "table", "data_source": "payments"},
                   headers=H_A)
        t("Create payments template", r.status_code, 200)
        tpl_pay = r.json()["data"]["id"]

        # --- 11. Run Payments Report ---
        print("\n--- 11. Run Payments Report ---")
        r = c.post(f"{BASE}{EP}/report-templates/{tpl_pay}/run",
                   json={"parameters": {"currency_code": "USD"}},
                   headers=H_A)
        t("Run payments", r.status_code, 200)
        run_id_p = r.json()["data"]["run_id"]

        # --- 12. Payment Run Completed ---
        print("\n--- 12. Payment Run Completed ---")
        r = c.get(f"{BASE}{EP}/report-runs/{run_id_p}", headers=H_A)
        t("Payment completed", r.json()["data"]["status"], "completed")

        # --- 13. Scheduled Report ---
        print("\n--- 13. Create Scheduled Report ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/scheduled-reports",
                   json={"template_id": tpl_id, "name": "Daily Audit",
                         "schedule_cron": "0 8 * * *", "recipients": "admin@example.com", "format": "csv"},
                   headers=H_A)
        t("Create scheduled", r.status_code, 200)
        sched_id = r.json()["data"]["id"]

        # --- 14. List Scheduled ---
        print("\n--- 14. List Scheduled ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/scheduled-reports", headers=H_A)
        t("List scheduled", r.status_code, 200)
        t("Has 1 scheduled", len(r.json()["data"]) >= 1, True)

        # --- 15. Toggle OFF ---
        print("\n--- 15. Toggle Scheduled OFF ---")
        r = c.post(f"{BASE}{EP}/scheduled-reports/{sched_id}/toggle",
                   json={"is_active": False},
                   headers=H_A)
        t("Toggle OFF", r.status_code, 200)
        t("Is inactive", r.json()["data"]["is_active"], False)

        # --- 16. Toggle ON ---
        print("\n--- 16. Toggle Scheduled ON ---")
        r = c.post(f"{BASE}{EP}/scheduled-reports/{sched_id}/toggle",
                   json={"is_active": True},
                   headers=H_A)
        t("Toggle ON", r.status_code, 200)
        t("Is active", r.json()["data"]["is_active"], True)

        # --- 17. Tenant Isolation - Templates ---
        print("\n--- 17. Tenant Isolation - Templates ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_B}/report-templates",
                   json={"name": "B Template", "report_type": "table", "data_source": "audit_trail"},
                   headers=H_B)
        t("Create B template", r.status_code, 200)
        tpl_b = r.json()["data"]["id"]

        r = c.get(f"{BASE}{EP}/companies/{CID_A}/report-templates", headers=H_A)
        names = [t_["name"] for t_ in r.json()["data"]]
        t("B not visible to A", "B Template" not in names, True)

        # --- 18. Tenant Isolation - Runs ---
        print("\n--- 18. Tenant Isolation - Runs ---")
        r = c.post(f"{BASE}{EP}/report-templates/{tpl_b}/run",
                   json={"format": "csv"},
                   headers=H_B)
        t("B run report", r.status_code, 200)

        r = c.get(f"{BASE}{EP}/companies/{CID_A}/report-runs", headers=H_A)
        for run in r.json()["data"]:
            t("Run tenant isolation", run["tenant_id"], "tenant_a")

        # --- 19. Tenant Isolation - Scheduled ---
        print("\n--- 19. Tenant Isolation - Scheduled ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_B}/scheduled-reports",
                   json={"template_id": tpl_b, "name": "B Scheduled",
                         "schedule_cron": "0 9 * * *", "recipients": "b@example.com"},
                   headers=H_B)
        t("Create B scheduled", r.status_code, 200)

        r = c.get(f"{BASE}{EP}/companies/{CID_A}/scheduled-reports", headers=H_A)
        names = [s["name"] for s in r.json()["data"]]
        t("B scheduled not visible to A", "B Scheduled" not in names, True)

        # --- 20. 404 Missing Template ---
        print("\n--- 20. 404 Missing Template ---")
        r = c.get(f"{BASE}{EP}/report-templates/nonexistent", headers=H_A)
        t("404 template", r.status_code, 404)

        # --- 21. 404 Missing Run ---
        print("\n--- 21. 404 Missing Run ---")
        r = c.get(f"{BASE}{EP}/report-runs/nonexistent", headers=H_A)
        t("404 run", r.status_code, 404)

        # --- 22. Filtered Report ---
        print("\n--- 22. Filtered Report ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/report-templates",
                   json={"name": "Filtered Audit", "report_type": "table",
                         "data_source": "audit_trail", "filters": {"entity_type": "test_entity"}},
                   headers=H_A)
        t("Create filtered template", r.status_code, 200)
        tpl_filt = r.json()["data"]["id"]

        r = c.post(f"{BASE}{EP}/report-templates/{tpl_filt}/run", json={}, headers=H_A)
        t("Run filtered", r.status_code, 200)
        run_filt = r.json()["data"]["run_id"]

        r = c.get(f"{BASE}{EP}/report-runs/{run_filt}", headers=H_A)
        t("Filtered completed", r.json()["data"]["status"], "completed")

        # --- 23. Invoices Report ---
        print("\n--- 23. Invoices Report ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/report-templates",
                   json={"name": "Inv Report", "report_type": "table", "data_source": "invoices"},
                   headers=H_A)
        t("Create inv template", r.status_code, 200)
        tpl_inv = r.json()["data"]["id"]

        r = c.post(f"{BASE}{EP}/report-templates/{tpl_inv}/run", json={"format": "json"}, headers=H_A)
        t("Run inv report", r.status_code, 200)
        r = c.get(f"{BASE}{EP}/report-runs/{r.json()['data']['run_id']}", headers=H_A)
        t("Inv completed", r.json()["data"]["status"], "completed")

        # --- 24. Public Template ---
        print("\n--- 24. Public Template ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/report-templates",
                   json={"name": "Public Tpl", "report_type": "summary",
                         "data_source": "employees", "is_public": True},
                   headers=H_A)
        t("Create public", r.status_code, 200)
        tpl_pub = r.json()["data"]["id"]
        r = c.get(f"{BASE}{EP}/report-templates/{tpl_pub}", headers=H_A)
        t("Is public", r.json()["data"]["is_public"], True)

        # --- 25. List by report_type ---
        print("\n--- 25. List by report_type ---")
        r = c.get(f"{BASE}{EP}/companies/{CID_A}/report-templates?report_type=summary", headers=H_A)
        t("Filter by type", r.status_code, 200)
        types = [t_["report_type"] for t_ in r.json()["data"]]
        t("Has summary", "summary" in types, True)

        # --- 26. Missing Required Fields ---
        print("\n--- 26. Missing Required Fields ---")
        r = c.post(f"{BASE}{EP}/companies/{CID_A}/report-templates",
                   json={"name": "Bad Template"},
                   headers=H_A)
        t("Missing fields", r.status_code, 400)

        # --- 27. Update Columns ---
        print("\n--- 27. Update Columns ---")
        r = c.put(f"{BASE}{EP}/report-templates/{tpl_id}",
                  json={"columns": [{"field": "event_type", "label": "Event"}]},
                  headers=H_A)
        t("Update columns", r.status_code, 200)
        t("Has columns", r.json()["data"]["columns"] is not None, True)

    finally:
        stop(proc)
        cleanup_final()
        c.close()

    print(f"\n{'='*60}")
    print(f"P35 RESULTS: {p}/{p + f} PASSED, {f} FAILED")
    print(f"{'='*60}")

    sys.exit(0 if f == 0 else 1)
