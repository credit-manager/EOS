"""
P45 Analytics & Pipelines Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/analytics"
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
        for tbl in ['dbp_analytics_dashboards', 'dbp_data_pipelines', 'dbp_analytics_alerts']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_analytics_widgets WHERE dashboard_id NOT IN (SELECT id FROM dbp_analytics_dashboards)"))
        db.execute(sa("DELETE FROM dbp_pipeline_runs WHERE pipeline_id NOT IN (SELECT id FROM dbp_data_pipelines)"))
        db.commit()
    finally:
        db.close()

def cleanup():
    setup()


def test_dashboards(c):
    print("\n--- 1. Dashboards ---")
    r = c.post(f"{EP}/dashboards", json={"dashboard_name": "Sales Overview",
               "dashboard_type": "sales", "layout_config": {"columns": 2}}, headers=H_A)
    t("Create dashboard", r.status_code, 200)
    did = r.json()["data"]["id"]
    r = c.post(f"{EP}/dashboards", json={"dashboard_name": "Finance Overview",
               "dashboard_type": "finance"}, headers=H_A)
    t("Create second dashboard", r.status_code, 200)
    r = c.get(f"{EP}/dashboards", headers=H_A)
    t("List dashboards", r.status_code, 200)
    t("Two dashboards", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/dashboards/{did}", headers=H_A)
    t("Get dashboard", r.status_code, 200)
    t("Name correct", r.json()["data"]["dashboard_name"], "Sales Overview")
    r = c.get(f"{EP}/dashboards", headers=H_B)
    t("Tenant B no A dashboards", len(r.json()["data"]), 0)
    r = c.delete(f"{EP}/dashboards/{did}", headers=H_A)
    t("Delete dashboard", r.status_code, 200)
    r = c.get(f"{EP}/dashboards/{did}", headers=H_A)
    t("Deleted dashboard 404", r.status_code, 404)


def test_widgets(c):
    print("\n--- 2. Widgets ---")
    did = c.post(f"{EP}/dashboards", json={"dashboard_name": "Test",
               "dashboard_type": "test"}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/dashboards/{did}/widgets", json={"widget_type": "line_chart",
               "title": "Revenue Trend", "config": {"series": ["revenue"]},
               "position_x": 0, "position_y": 0, "width": 6, "height": 4}, headers=H_A)
    t("Create widget", r.status_code, 200)
    wid = r.json()["data"]["id"]
    r = c.get(f"{EP}/dashboards/{did}/widgets", headers=H_A)
    t("List widgets", r.status_code, 200)
    t("One widget", len(r.json()["data"]), 1)
    r = c.delete(f"{EP}/widgets/{wid}", headers=H_A)
    t("Delete widget", r.status_code, 200)


def test_pipelines(c):
    print("\n--- 3. Pipelines ---")
    r = c.post(f"{EP}/pipelines", json={"pipeline_name": "Sales Sync",
               "source_type": "api", "target_type": "database",
               "schedule": "0 */6 * * *"}, headers=H_A)
    t("Create pipeline", r.status_code, 200)
    pid = r.json()["data"]["id"]
    r = c.post(f"{EP}/pipelines", json={"pipeline_name": "Finance Export",
               "source_type": "database", "target_type": "csv"}, headers=H_A)
    t("Create second pipeline", r.status_code, 200)
    r = c.get(f"{EP}/pipelines", headers=H_A)
    t("List pipelines", r.status_code, 200)
    t("Two pipelines", len(r.json()["data"]), 2)
    r = c.get(f"{EP}/pipelines/{pid}", headers=H_A)
    t("Get pipeline", r.status_code, 200)
    r = c.put(f"{EP}/pipelines/{pid}", json={"schedule": "0 */12 * * *"}, headers=H_A)
    t("Update pipeline", r.status_code, 200)
    r = c.get(f"{EP}/pipelines", headers=H_B)
    t("Tenant B no A pipelines", len(r.json()["data"]), 0)


def test_pipeline_runs(c):
    print("\n--- 4. Pipeline Runs ---")
    pid = c.post(f"{EP}/pipelines", json={"pipeline_name": "Test Pipeline",
               "source_type": "api", "target_type": "db"}, headers=H_A).json()["data"]["id"]
    r = c.post(f"{EP}/pipeline-runs", json={"pipeline_id": pid}, headers=H_A)
    t("Create run", r.status_code, 200)
    rid = r.json()["data"]["id"]
    r = c.put(f"{EP}/pipeline-runs/{rid}", json={"records_processed": 1500,
               "records_failed": 3}, headers=H_A)
    t("Complete run", r.status_code, 200)
    r = c.get(f"{EP}/pipeline-runs?pipeline_id={pid}", headers=H_A)
    t("List runs", r.status_code, 200)
    t("One run", len(r.json()["data"]), 1)


def test_alerts(c):
    print("\n--- 5. Analytics Alerts ---")
    r = c.post(f"{EP}/alerts", json={"alert_name": "High Error Rate",
               "metric_name": "error_rate", "condition": "greater_than",
               "threshold_value": 5.0, "notification_channels": ["email"]}, headers=H_A)
    t("Create alert", r.status_code, 200)
    aid = r.json()["data"]["id"]
    r = c.get(f"{EP}/alerts", headers=H_A)
    t("List alerts", r.status_code, 200)
    t("One alert", len(r.json()["data"]), 1)
    r = c.put(f"{EP}/alerts/{aid}/trigger", headers=H_A)
    t("Trigger alert", r.status_code, 200)
    r = c.delete(f"{EP}/alerts/{aid}", headers=H_A)
    t("Delete alert", r.status_code, 200)
    r = c.get(f"{EP}/alerts", headers=H_B)
    t("Tenant B no A alerts", len(r.json()["data"]), 0)


def test_negative(c):
    print("\n--- 6. Negative Tests ---")
    r = c.post(f"{EP}/dashboards", json={}, headers=H_A)
    t("Create dashboard missing fields", r.status_code, 400)
    r = c.post(f"{EP}/pipelines", json={}, headers=H_A)
    t("Create pipeline missing fields", r.status_code, 400)
    r = c.post(f"{EP}/alerts", json={}, headers=H_A)
    t("Create alert missing fields", r.status_code, 400)
    r = c.get(f"{EP}/dashboards/nonexistent", headers=H_A)
    t("Get non-existent dashboard", r.status_code, 404)


if __name__ == "__main__":
    print("=" * 60)
    print("P45 ANALYTICS & PIPELINES TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_dashboards(c)
        test_widgets(c)
        test_pipelines(c)
        test_pipeline_runs(c)
        test_alerts(c)
        test_negative(c)
    finally:
        c.close(); stop(proc); cleanup()
    print("\n" + "=" * 60)
    print(f"P45 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
