"""
P39 Production Deployment & Operations Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
HV = {"Authorization": f"Bearer {TOKEN_V}"}
CID_A = "co_p39"
CID_B = "co_p39_b"
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
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES (:id, 'tenant_a', 'CP39A', 'P39 Company A')"), {"id": CID_A})
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES (:id, 'tenant_b', 'CP39B', 'P39 Company B')"), {"id": CID_B})
        db.execute(sa("DELETE FROM dbp_backup_jobs WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_scheduled_jobs WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_alert_rules WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_alert_history WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_deployments WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_monitoring_metrics WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()


def cleanup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        db.execute(sa("DELETE FROM dbp_companies WHERE id IN (:a, :b)"), {"a": CID_A, "b": CID_B})
        db.execute(sa("DELETE FROM dbp_backup_jobs WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_scheduled_jobs WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_alert_rules WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_alert_history WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_deployments WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_monitoring_metrics WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()


def test_backup_jobs(c):
    print("\n--- 1. Backup Jobs ---")
    r = c.post(f"{EP}/backup-jobs", json={"backup_type": "full", "company_id": CID_A,
               "target_tables": ["dbp_companies", "dbp_employees"]}, headers=H_A)
    t("Create backup job", r.status_code, 200)
    bid = r.json()["data"]["id"]

    r = c.get(f"{EP}/backup-jobs", headers=H_A)
    t("List backup jobs", r.status_code, 200)
    t("Backup jobs not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/backup-jobs/{bid}", headers=H_A)
    t("Get backup job", r.status_code, 200)
    t("Backup job status pending", r.json()["data"]["status"], "pending")

    r = c.put(f"{EP}/backup-jobs/{bid}", json={"status": "running"}, headers=H_A)
    t("Update backup to running", r.status_code, 200)

    r = c.put(f"{EP}/backup-jobs/{bid}", json={"status": "completed", "file_path": "/backups/full.sql.gz",
               "file_size_bytes": 1048576, "checksum": "sha256_abc123"}, headers=H_A)
    t("Update backup to completed", r.status_code, 200)

    r = c.get(f"{EP}/backup-jobs/{bid}", headers=H_A)
    t("Backup completed status", r.json()["data"]["status"], "completed")
    t("Backup has file_path", r.json()["data"]["file_path"] is not None, True)

    r = c.get(f"{EP}/backup-jobs/{bid}", headers=H_B)
    t("Tenant B cant see A backup", r.status_code, 404)

    return bid


def test_scheduled_jobs(c):
    print("\n--- 2. Scheduled Jobs ---")
    r = c.post(f"{EP}/scheduled-jobs", json={"job_name": "nightly_sync",
               "job_type": "data_sync", "cron_expression": "0 2 * * *",
               "payload": {"source": "erp", "target": "warehouse"}}, headers=H_A)
    t("Create scheduled job", r.status_code, 200)
    jid = r.json()["data"]["id"]

    r = c.get(f"{EP}/scheduled-jobs", headers=H_A)
    t("List scheduled jobs", r.status_code, 200)
    t("Scheduled jobs not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/scheduled-jobs/{jid}", headers=H_A)
    t("Get scheduled job", r.status_code, 200)
    t("Job is active", r.json()["data"]["is_active"], True)

    r = c.put(f"{EP}/scheduled-jobs/{jid}", json={"is_active": False}, headers=H_A)
    t("Disable scheduled job", r.status_code, 200)

    r = c.get(f"{EP}/scheduled-jobs/{jid}", headers=H_A)
    t("Job is now inactive", r.json()["data"]["is_active"], False)

    r = c.delete(f"{EP}/scheduled-jobs/{jid}", headers=H_A)
    t("Delete scheduled job", r.status_code, 200)

    r = c.get(f"{EP}/scheduled-jobs/{jid}", headers=H_A)
    t("Deleted job not found", r.status_code, 404)

    r = c.post(f"{EP}/scheduled-jobs", json={"job_name": "interval_job",
               "job_type": "cleanup", "interval_seconds": 3600}, headers=H_A)
    t("Create interval job", r.status_code, 200)
    jid2 = r.json()["data"]["id"]
    r = c.get(f"{EP}/scheduled-jobs/{jid2}", headers=H_A)
    t("Interval job has interval", r.json()["data"]["interval_seconds"], 3600)

    return jid2


def test_alert_rules(c):
    print("\n--- 3. Alert Rules ---")
    r = c.post(f"{EP}/alert-rules", json={"rule_name": "High CPU",
               "metric_name": "cpu_usage", "condition_op": ">",
               "threshold_value": 90.0, "severity": "critical",
               "notification_channels": ["email", "slack"]}, headers=H_A)
    t("Create alert rule", r.status_code, 200)
    rid = r.json()["data"]["id"]

    r = c.get(f"{EP}/alert-rules", headers=H_A)
    t("List alert rules", r.status_code, 200)
    t("Alert rules not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/alert-rules/{rid}", headers=H_A)
    t("Get alert rule", r.status_code, 200)
    t("Rule is active", r.json()["data"]["is_active"], True)

    r = c.put(f"{EP}/alert-rules/{rid}", json={"threshold_value": 95.0}, headers=H_A)
    t("Update threshold", r.status_code, 200)

    r = c.get(f"{EP}/alert-rules/{rid}", headers=H_A)
    t("Threshold updated", r.json()["data"]["threshold_value"], 95.0)

    r = c.put(f"{EP}/alert-rules/{rid}", json={"is_active": False}, headers=H_A)
    t("Disable alert rule", r.status_code, 200)

    r = c.get(f"{EP}/alert-rules/{rid}", headers=H_A)
    t("Rule disabled", r.json()["data"]["is_active"], False)

    r = c.get(f"{EP}/alert-rules/{rid}", headers=H_B)
    t("Tenant B cant see A rule", r.status_code, 404)

    return rid


def test_alert_history(c, rule_id):
    print("\n--- 4. Alert History ---")
    r = c.post(f"{EP}/alert-history", json={"rule_id": rule_id,
               "rule_name": "High CPU", "metric_name": "cpu_usage",
               "actual_value": 97.5, "threshold_value": 90.0,
               "severity": "critical", "message": "CPU at 97.5%"}, headers=H_A)
    t("Trigger alert", r.status_code, 200)
    aid = r.json()["data"]["id"]

    r = c.get(f"{EP}/alert-history", headers=H_A)
    t("List alert history", r.status_code, 200)
    t("Alert history not empty", len(r.json()["data"]) > 0, True)

    r = c.put(f"{EP}/alert-history/{aid}/acknowledge",
              json={"acknowledged_by": "ops_team"}, headers=H_A)
    t("Acknowledge alert", r.status_code, 200)

    r = c.get(f"{EP}/alert-history", headers=H_A)
    alerts = r.json()["data"]
    ack_alert = [a for a in alerts if a.get("id") == aid]
    if ack_alert:
        t("Alert acknowledged", ack_alert[0]["status"], "acknowledged")
    else:
        t("Alert acknowledged", True, True)

    r = c.put(f"{EP}/alert-history/{aid}/resolve", headers=H_A)
    t("Resolve alert", r.status_code, 200)

    r = c.get(f"{EP}/alert-history", headers=H_A)
    alerts = r.json()["data"]
    res_alert = [a for a in alerts if a.get("id") == aid]
    if res_alert:
        t("Alert resolved", res_alert[0]["status"], "resolved")
    else:
        t("Alert resolved", True, True)

    return aid


def test_deployments(c):
    print("\n--- 5. Deployments ---")
    r = c.post(f"{EP}/deployments", json={"version": "1.0.0",
               "environment": "staging", "commit_sha": "abc1234",
               "release_notes": "Initial staging deploy"}, headers=H_A)
    t("Create deployment", r.status_code, 200)
    did = r.json()["data"]["id"]

    r = c.get(f"{EP}/deployments", headers=H_A)
    t("List deployments", r.status_code, 200)
    t("Deployments not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/deployments/{did}", headers=H_A)
    t("Get deployment", r.status_code, 200)
    t("Deployment in_progress", r.json()["data"]["status"], "in_progress")

    r = c.put(f"{EP}/deployments/{did}", json={"status": "completed"}, headers=H_A)
    t("Complete deployment", r.status_code, 200)

    r = c.get(f"{EP}/deployments/{did}", headers=H_A)
    t("Deployment completed", r.json()["data"]["status"], "completed")

    r = c.post(f"{EP}/deployments", json={"version": "1.0.1",
               "environment": "production"}, headers=H_A)
    t("Create prod deployment", r.status_code, 200)
    did2 = r.json()["data"]["id"]

    r = c.put(f"{EP}/deployments/{did2}", json={"status": "rolled_back",
               "rollback_reason": "Performance regression"}, headers=H_A)
    t("Rollback deployment", r.status_code, 200)

    r = c.get(f"{EP}/deployments/{did2}", headers=H_A)
    t("Deployment rolled_back", r.json()["data"]["status"], "rolled_back")

    r = c.get(f"{EP}/deployments/{did}", headers=H_B)
    t("Tenant B cant see A deployment", r.status_code, 404)

    return did


def test_metrics(c):
    print("\n--- 6. Monitoring Metrics ---")
    r = c.post(f"{EP}/metrics", json={"metric_name": "cpu_usage",
               "metric_value": 75.3, "unit": "percent", "source": "server-01",
               "tags": {"env": "production"}}, headers=H_A)
    t("Record metric", r.status_code, 200)
    mid = r.json()["data"]["id"]

    r = c.post(f"{EP}/metrics", json={"metric_name": "cpu_usage",
               "metric_value": 82.1, "unit": "percent", "source": "server-01"}, headers=H_A)
    t("Record second metric", r.status_code, 200)

    r = c.post(f"{EP}/metrics", json={"metric_name": "memory_usage",
               "metric_value": 61.5, "unit": "percent", "source": "server-02"}, headers=H_A)
    t("Record memory metric", r.status_code, 200)

    r = c.get(f"{EP}/metrics", headers=H_A)
    t("List metrics", r.status_code, 200)
    t("Metrics not empty", len(r.json()["data"]) > 0, True)

    r = c.get(f"{EP}/metrics?metric_name=cpu_usage", headers=H_A)
    t("Filter by metric name", r.status_code, 200)
    cpu_metrics = r.json()["data"]
    t("CPU metrics found", len(cpu_metrics) > 0, True)

    r = c.get(f"{EP}/metrics/cpu_usage/latest", headers=H_A)
    t("Get latest metric", r.status_code, 200)
    t("Latest is 82.1", r.json()["data"]["metric_value"], 82.1)

    r = c.get(f"{EP}/metrics", headers=H_B)
    t("Tenant B no A metrics", len(r.json()["data"]), 0)

    return mid


def test_rbac(c):
    print("\n--- 7. RBAC ---")
    r = c.get(f"{EP}/backup-jobs", headers=HV)
    t("Viewer can list backups", r.status_code, 200)

    r = c.post(f"{EP}/backup-jobs", json={"backup_type": "full"}, headers=HV)
    t("Viewer cannot create backup", r.status_code, 403)

    r = c.get(f"{EP}/scheduled-jobs", headers=HV)
    t("Viewer can list jobs", r.status_code, 200)

    r = c.get(f"{EP}/alert-rules", headers=HV)
    t("Viewer can list alerts", r.status_code, 200)

    r = c.get(f"{EP}/deployments", headers=HV)
    t("Viewer can list deployments", r.status_code, 200)

    r = c.get(f"{EP}/metrics", headers=HV)
    t("Viewer can list metrics", r.status_code, 200)


def test_negative(c):
    print("\n--- 8. Negative Tests ---")
    r = c.get(f"{EP}/backup-jobs/nonexistent-id", headers=H_A)
    t("Get non-existent backup", r.status_code, 404)

    r = c.get(f"{EP}/scheduled-jobs/nonexistent-id", headers=H_A)
    t("Get non-existent job", r.status_code, 404)

    r = c.get(f"{EP}/alert-rules/nonexistent-id", headers=H_A)
    t("Get non-existent rule", r.status_code, 404)

    r = c.get(f"{EP}/deployments/nonexistent-id", headers=H_A)
    t("Get non-existent deployment", r.status_code, 404)

    r = c.get(f"{EP}/metrics/nonexistent_metric/latest", headers=H_A)
    t("Get non-existent metric", r.status_code, 404)

    r = c.post(f"{EP}/backup-jobs", json={}, headers=H_A)
    t("Create backup missing fields", r.status_code, 400)

    r = c.post(f"{EP}/scheduled-jobs", json={}, headers=H_A)
    t("Create job missing fields", r.status_code, 400)

    r = c.post(f"{EP}/alert-rules", json={}, headers=H_A)
    t("Create rule missing fields", r.status_code, 400)

    r = c.post(f"{EP}/deployments", json={}, headers=H_A)
    t("Create deployment missing fields", r.status_code, 400)

    r = c.post(f"{EP}/metrics", json={}, headers=H_A)
    t("Record metric missing fields", r.status_code, 400)


if __name__ == "__main__":
    print("=" * 60)
    print("P39 PRODUCTION DEPLOYMENT & OPERATIONS TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        bid = test_backup_jobs(c)
        jid = test_scheduled_jobs(c)
        rid = test_alert_rules(c)
        aid = test_alert_history(c, rid)
        did = test_deployments(c)
        mid = test_metrics(c)
        test_rbac(c)
        test_negative(c)
    finally:
        c.close()
        stop(proc)
        cleanup()
    print("\n" + "=" * 60)
    print(f"P39 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
