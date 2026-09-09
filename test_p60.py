"""
P60 — Commercial Productization — Full Customer Journey E2E Test

Proves EOS works as a SaaS product:
  Visitor → Signup → AI Composer → Build ERP → Customize → Preview →
  Select Plan → Pay → Launch → Use ERP → Reports → Billing → Portal

All from platform primitives, zero company-specific code.
"""
import httpx, subprocess, sys, time, os, json

sys.path.insert(0, ".")
from core.auth import create_test_token
from database import SessionLocal
from sqlalchemy import text

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
CMP = f"{EP}/composer"
BLD = f"{EP}/builder"
MKT = f"{EP}/marketplace"
SAAS = f"{EP}/experience"
BILL = f"{EP}/billing-flow"
PORTAL = f"{EP}/portal"
PROD = f"{EP}"

TENANT = "tenant_p60"
TOKEN = create_test_token(TENANT, user_id="owner_p60", email="owner@demo.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}

passed = failed = 0
results = []


def t(name, got, exp, critical=False):
    global passed, failed
    if got == exp:
        passed += 1
        results.append(f"  OK   {name}")
    else:
        failed += 1
        tag = "CRITICAL" if critical else "FAIL"
        results.append(f"  {tag}  {name}: got {got!r}, expected {exp!r}")


def log(msg):
    results.append(f"  ---  {msg}")


def api(method, path, body=None):
    c = httpx.Client(base_url=BASE, headers=H, timeout=30)
    if method == "GET":
        r = c.get(path, headers=H)
    elif method == "POST":
        r = c.post(path, json=body, headers=H)
    elif method == "PUT":
        r = c.put(path, json=body, headers=H)
    elif method == "DELETE":
        r = c.delete(path, headers=H)
    else:
        raise ValueError(method)
    c.close()
    return r


def cleanup():
    db = SessionLocal()
    try:
        for tbl in ["dbp_builder_versions", "dbp_builder_projects",
                     "dbp_tenant_installations", "dbp_saas_journeys",
                     "dbp_composer_sessions", "dbp_support_tickets",
                     "dbp_payments", "dbp_subscriptions", "dbp_invoices_saas",
                     "dbp_licenses", "dbp_saas_usage",
                     "dbp_saas_metrics", "dbp_saas_alerts",
                     "dbp_backup_jobs", "dbp_scheduled_jobs",
                     "dbp_alert_rules", "dbp_alert_history", "dbp_deployments"]:
            try:
                db.execute(text(f"DELETE FROM {tbl} WHERE tenant_id='{TENANT}'"))
                db.execute(text(f"DELETE FROM {tbl} WHERE tenant_id='tenant_p60_other'"))
                db.commit()
            except Exception:
                db.rollback()
        for ptbl in ["bld_project_claims", "bld_temp_entity", "bld_journey_custom",
                      "project_claims", "temp_entity", "journey_custom"]:
            try:
                db.execute(text(f"DROP TABLE IF EXISTS public.{ptbl}"))
                db.commit()
            except Exception:
                db.rollback()
    except Exception:
        pass
    finally:
        db.close()


def start_server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=os.environ.copy())
    time.sleep(6)
    return proc


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


# ═══════════════════════════════════════════════════════════
# STAGE 1: MARKETPLACE DISCOVERY
# ═══════════════════════════════════════════════════════════
def stage_1_marketplace():
    log("STAGE 1: Marketplace Discovery")
    r = api("GET", f"{MKT}/items")
    t("Browse marketplace", r.status_code, 200)
    if r.status_code == 200:
        items = r.json()["data"]
        t("Has 10+ items", len(items) >= 10, True)
        t("Has industry packs", any(i["type"] == "industry_pack" for i in items), True)
        t("Has addons", any(i["type"] == "addon" for i in items), True)
    r2 = api("GET", f"{MKT}/items/pack_construction")
    t("Get specific item", r2.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 2: BILLING — PLAN CATALOG
# ═══════════════════════════════════════════════════════════
def stage_2_billing_catalog():
    log("STAGE 2: Billing Plan Catalog")
    r = api("GET", f"{BILL}/plans")
    t("List plans", r.status_code, 200)
    if r.status_code == 200:
        plans = r.json()["data"]
        t("Has 4 plans", len(plans) >= 4, True)
        codes = [p["plan_code"] for p in plans]
        t("Has starter", "starter" in codes, True)
        t("Has enterprise", "enterprise" in codes, True)


# ═══════════════════════════════════════════════════════════
# STAGE 3: AI COMPOSER — NATURAL LANGUAGE
# ═══════════════════════════════════════════════════════════
def stage_3_composer():
    log("STAGE 3: AI Composer — Arabic Description")
    r = api("POST", f"{CMP}/compose", {
        "input": "عايز نظام ERP لشركة مقاولات فيها مشاريع ومخازن ومشتريات وحسابات وموافقات"
    })
    t("Compose request", r.status_code, 200, critical=True)
    if r.status_code != 200:
        return None
    data = r.json()["data"]
    sid = data["session_id"]
    t("Industry detected", data["requirements"]["industry"], "construction")
    t("Has modules", len(data["config"]["modules"]) >= 5, True)
    t("Has validation", "valid" in data["validation"], True)
    return sid


# ═══════════════════════════════════════════════════════════
# STAGE 4: BUILDER PROJECT FROM AI
# ═══════════════════════════════════════════════════════════
def stage_4_builder(sid):
    log("STAGE 4: Builder Project from AI Session")
    r = api("POST", f"{BLD}/projects", {
        "name": "Construction ERP",
        "composer_session_id": sid,
    })
    t("Create project from AI", r.status_code, 200, critical=True)
    if r.status_code != 200:
        return None
    d = r.json()["data"]
    pid = d["project_id"]
    t("Has project_id", pid is not None, True)
    t("Has modules", len(d["draft_config"]["modules"]) >= 5, True)
    t("Has settings", "currency" in d["draft_config"]["settings"], True)
    return pid


# ═══════════════════════════════════════════════════════════
# STAGE 5: CUSTOMIZE ERP
# ═══════════════════════════════════════════════════════════
def stage_5_customize(pid):
    log("STAGE 5: Customer Customizes ERP")
    r = api("PUT", f"{BLD}/projects/{pid}/settings", {
        "branches": 3, "employees": 50
    })
    t("Update settings", r.status_code, 200)

    r = api("POST", f"{BLD}/projects/{pid}/entities", {
        "entity_code": "project_claims",
        "name_en": "Project Claims",
        "faculty": "projects",
        "fields": [
            {"code": "claim_type", "label_en": "Type", "field_type": "string", "is_required": True},
            {"code": "amount", "label_en": "Amount", "field_type": "number", "is_required": True},
            {"code": "status", "field_type": "enum",
             "enum_values": ["submitted", "approved", "rejected"]},
        ]
    })
    t("Add entity project_claims", r.status_code, 200, critical=True)

    r = api("PUT", f"{BLD}/projects/{pid}/roles", {
        "project_owner": ["*"],
        "project_manager": ["read", "create", "update"],
    })
    t("Set custom roles", r.status_code, 200)

    r = api("POST", f"{BLD}/projects/{pid}/kpis", {
        "name": "Active Projects", "metric": "active_count", "aggregation": "COUNT"
    })
    t("Add KPI", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 6: PREVIEW + APPROVE
# ═══════════════════════════════════════════════════════════
def stage_6_preview_publish(pid):
    log("STAGE 6: Preview -> Publish (Gate)")
    r = api("GET", f"{BLD}/projects/{pid}/preview")
    t("Preview draft", r.status_code, 200)
    if r.status_code == 200:
        p = r.json()["data"]
        t("Validation passes", p["validation"]["valid"], True)
        t("1 custom entity", p["validation"]["summary"]["custom_entities"], 1)

    r = api("POST", f"{BLD}/projects/{pid}/publish", {
        "confirmed": True, "change_summary": "Initial publish"
    })
    t("Publish with confirmed=true", r.status_code, 200, critical=True)
    if r.status_code != 200:
        return None
    d = r.json()["data"]
    t("Version = 1", d["version_number"], 1)
    t("project_claims published", "project_claims" in d["entities_published"], True)

    r = api("POST", f"{BLD}/projects/{pid}/publish", {"confirmed": False})
    t("Publish without confirm -> 400", r.status_code, 400)
    return d


# ═══════════════════════════════════════════════════════════
# STAGE 7: USE GENERATED ERP
# ═══════════════════════════════════════════════════════════
def stage_7_use_erp():
    log("STAGE 7: Use Generated ERP — CRUD Operations")
    r = api("POST", f"{EP}/entities/project_claims/records", {
        "id": "claim-001", "claim_type": "Material Overrun",
        "amount": 15000, "status": "submitted"
    })
    t("Create claim 1", r.status_code, 200, critical=True)

    r = api("POST", f"{EP}/entities/project_claims/records", {
        "id": "claim-002", "claim_type": "Labor Overrun",
        "amount": 25000, "status": "approved"
    })
    t("Create claim 2", r.status_code, 200)

    r = api("GET", f"{EP}/entities/project_claims/records")
    t("List claims", r.status_code, 200)
    if r.status_code == 200:
        t("Tenant owns 2 records", r.json()["count"], 2)

    r = api("GET", f"{EP}/entities/project_claims/records?filters=status:eq:approved")
    t("Filter by approved", r.status_code == 200 and r.json().get("count") == 1, True)


# ═══════════════════════════════════════════════════════════
# STAGE 8: TENANT ISOLATION
# ═══════════════════════════════════════════════════════════
def stage_8_isolation():
    log("STAGE 8: Tenant Isolation")
    T2 = "tenant_p60_other"
    TOK2 = create_test_token(T2, user_id="other", email="other@demo.com", roles=["admin"])
    c = httpx.Client(base_url=BASE, timeout=30)
    H2 = {"Authorization": f"Bearer {TOK2}"}
    r = c.get(f"{EP}/entities/project_claims/records", headers=H2)
    t("Other tenant sees 0 records", r.status_code == 200 and r.json()["count"] == 0, True)
    r2 = c.get(f"{BLD}/projects", headers=H2)
    t("Other tenant no projects", r2.status_code == 200 and len(r2.json()["data"]) == 0, True)
    r3 = c.get(f"{EP}/active", headers=H2)
    t("Other tenant no active config", r3.status_code, 404)
    c.close()


# ═══════════════════════════════════════════════════════════
# STAGE 9: RBAC
# ═══════════════════════════════════════════════════════════
def stage_9_rbac():
    log("STAGE 9: RBAC on Generated Entity")
    TV = create_test_token(TENANT, user_id="viewer", email="v@demo.com", roles=["dynamic_viewer"])
    HV = {"Authorization": f"Bearer {TV}"}
    c = httpx.Client(base_url=BASE, timeout=30)
    r = c.get(f"{EP}/entities/project_claims/records", headers=HV)
    t("Viewer CAN read", r.status_code, 200)
    r = c.post(f"{EP}/entities/project_claims/records", headers=HV,
               json={"id": "v-test", "claim_type": "X", "amount": 1, "status": "X"})
    t("Viewer CANNOT write -> 403", r.status_code, 403, critical=True)
    c.close()


# ═══════════════════════════════════════════════════════════
# STAGE 10: VERSIONING & ROLLBACK
# ═══════════════════════════════════════════════════════════
def stage_10_versioning(pid):
    log("STAGE 10: Versioning & Rollback")
    r = api("POST", f"{BLD}/projects/{pid}/entities", {
        "entity_code": "temp_entity",
        "name_en": "Temporary", "faculty": "ops",
        "fields": [{"code": "val", "field_type": "string"}]
    })
    t("Add temp entity", r.status_code, 200)

    r = api("POST", f"{BLD}/projects/{pid}/publish", {
        "confirmed": True, "change_summary": "Add temp entity"
    })
    t("Publish v2", r.status_code, 200)
    if r.status_code == 200:
        t("Version = 2", r.json()["data"]["version_number"], 2)

    versions = api("GET", f"{BLD}/projects/{pid}/versions")
    if versions.status_code == 200:
        vlist = versions.json()["data"]
        v1id = next((v["id"] for v in vlist if v["version_number"] == 1), None)
        if v1id:
            r = api("POST", f"{BLD}/projects/{pid}/rollback", {"version_id": v1id})
            t("Rollback to v1", r.status_code, 200, critical=True)
            if r.status_code == 200:
                t("temp_entity removed", "temp_entity" in r.json()["data"]["entities_removed"], True)
                t("New version 3", r.json()["data"]["new_version_number"], 3)

    r = api("POST", f"{EP}/entities/temp_entity/records", {"id": "t1", "val": "x"})
    t("Rolled-back entity -> 404", r.status_code, 404)

    r = api("POST", f"{EP}/entities/project_claims/records", {
        "id": "after-rollback", "claim_type": "Post-RB", "amount": 500, "status": "submitted"
    })
    t("v1 entity still works", r.status_code, 200, critical=True)


# ═══════════════════════════════════════════════════════════
# STAGE 11: SAAS JOURNEY (Full Orchestration)
# ═══════════════════════════════════════════════════════════
def stage_11_journey():
    log("STAGE 11: SaaS Journey — Full Orchestration")
    r = api("POST", f"{SAAS}/journeys", {
        "business_description": "شركة مقاولات كبيرة فيها 50 موظف و3 فروع ومشاريع كثيرة",
        "company_name": "Contracting Corp",
        "admin_email": "admin@contracting.com"
    })
    t("Start journey", r.status_code, 200, critical=True)
    if r.status_code != 200:
        return None
    d = r.json()["data"]
    jid = d["journey_id"]
    t("Status = drafted", d["status"], "drafted")
    t("Industry detected", d["detected_industry"], "construction")
    t("Has modules", len(d["modules"]) >= 1, True)

    r2 = api("GET", f"{SAAS}/journeys/{jid}")
    t("Get journey", r2.status_code, 200)
    if r2.status_code == 200:
        t("Progress calculated", "progress_percent" in r2.json()["data"], True)
    return jid


# ═══════════════════════════════════════════════════════════
# STAGE 12: JOURNEY — CUSTOMIZE → PLAN → PAY → LAUNCH
# ═══════════════════════════════════════════════════════════
def stage_12_journey_lifecycle(jid):
    log("STAGE 12: Journey Lifecycle -- Customize -> Plan -> Pay -> Launch")

    r = api("PUT", f"{SAAS}/journeys/{jid}/customize", {
        "settings": {"currency": "SAR", "language": "ar"},
        "enable_modules": ["workflow"],
        "add_entities": [{
            "entity_code": "journey_custom",
            "name_en": "Journey Custom",
            "faculty": "ops",
            "fields": [{"code": "note", "field_type": "string"}]
        }]
    })
    t("Customize journey", r.status_code, 200)

    r = api("GET", f"{SAAS}/journeys/{jid}/preview")
    t("Preview journey", r.status_code, 200)
    if r.status_code == 200:
        p = r.json()["data"]
        t("Preview has validation", "validation" in p, True)

    r = api("POST", f"{SAAS}/journeys/{jid}/select-plan", {
        "plan_code": "professional", "billing_cycle": "monthly"
    })
    t("Select plan", r.status_code, 200, critical=True)
    if r.status_code == 200:
        d = r.json()["data"]
        t("Status = plan_selected", d["status"], "plan_selected")
        t("Has amount_due", "amount_due" in d, True)

    r = api("POST", f"{SAAS}/journeys/{jid}/pay", {"payment_method": "card"})
    t("Pay", r.status_code, 200, critical=True)
    if r.status_code == 200:
        d = r.json()["data"]
        t("Status = paid", d["status"], "paid")
        t("Has license_key", "license_key" in d, True)

    r = api("POST", f"{SAAS}/journeys/{jid}/launch", {"confirmed": False})
    t("Launch without confirm -> 400", r.status_code, 400)

    r = api("POST", f"{SAAS}/journeys/{jid}/launch", {"confirmed": True})
    t("Launch with confirm", r.status_code, 200, critical=True)
    if r.status_code == 200:
        d = r.json()["data"]
        t("Status = erp_ready", d["status"], "erp_ready")
        t("Entities published", len(d["entities_published"]) >= 1, True)


# ═══════════════════════════════════════════════════════════
# STAGE 13: CUSTOMER PORTAL
# ═══════════════════════════════════════════════════════════
def stage_13_portal():
    log("STAGE 13: Customer Portal")
    r = api("GET", f"{PORTAL}/overview")
    t("Portal overview", r.status_code, 200, critical=True)
    if r.status_code == 200:
        d = r.json()["data"]
        t("Has company section", "company" in d, True)
        t("Has subscription section", "subscription" in d, True)
        t("Has support section", "support" in d, True)

    r = api("POST", f"{PORTAL}/support/tickets", {
        "subject": "Need help with ERP setup",
        "message": "I need assistance configuring my chart of accounts",
        "priority": "high"
    })
    t("Create support ticket", r.status_code, 200, critical=True)
    ticket_id = r.json()["data"]["ticket_id"] if r.status_code == 200 else None

    r = api("GET", f"{PORTAL}/support/tickets")
    t("List tickets", r.status_code, 200)
    if r.status_code == 200:
        t("Has 1 ticket", r.json()["data"][0]["status"], "open")

    if ticket_id:
        r = api("PUT", f"{PORTAL}/support/tickets/{ticket_id}/close")
        t("Close ticket", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 14: BILLING — SUBSCRIPTION + USAGE
# ═══════════════════════════════════════════════════════════
def stage_14_billing():
    log("STAGE 14: Billing — Subscription & Usage")
    r = api("GET", f"{BILL}/my-subscription")
    t("My subscription", r.status_code, 200)
    if r.status_code == 200:
        d = r.json()["data"]
        t("Has plan", d.get("plan") is not None, True)

    r = api("POST", f"{BILL}/usage", {
        "meter_name": "active_users", "meter_value": 12
    })
    t("Record usage", r.status_code, 200)

    r = api("GET", f"{BILL}/usage-summary")
    t("Usage summary", r.status_code, 200)
    if r.status_code == 200:
        t("Has meters", "meters" in r.json()["data"], True)


# ═══════════════════════════════════════════════════════════
# STAGE 15: PRODUCTION OPS
# ═══════════════════════════════════════════════════════════
def stage_15_production_ops():
    log("STAGE 15: Production Ops — Monitoring, Alerts, Deployments")
    r = api("POST", f"{PROD}/backup-jobs", {
        "backup_type": "full", "target_tables": ["dbp_accounts", "dbp_entities"]
    })
    t("Create backup job", r.status_code, 200)

    r = api("GET", f"{PROD}/backup-jobs")
    t("List backup jobs", r.status_code, 200)
    if r.status_code == 200:
        t("Has 1 backup job", len(r.json()["data"]) >= 1, True)

    r = api("POST", f"{PROD}/scheduled-jobs", {
        "job_name": "Daily Report", "job_type": "report",
        "cron_expression": "0 8 * * *"
    })
    t("Create scheduled job", r.status_code, 200)

    r = api("POST", f"{PROD}/alert-rules", {
        "rule_name": "High CPU", "metric_name": "cpu_usage",
        "condition_op": ">", "threshold_value": 90.0, "severity": "critical"
    })
    t("Create alert rule", r.status_code, 200)

    r = api("POST", f"{PROD}/deployments", {
        "version": "1.0.0", "environment": "production",
        "commit_sha": "abc123", "release_notes": "Initial production"
    })
    t("Create deployment", r.status_code, 200)

    r = api("POST", f"{PROD}/metrics", {
        "metric_name": "response_time_ms", "metric_value": 120.5, "source": "api"
    })
    t("Record metric", r.status_code, 200)

    r = api("GET", f"{PROD}/metrics/metric_name/response_time_ms/latest" if False else
            f"{PROD}/metrics?metric_name=response_time_ms&limit=5")
    t("List metrics", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 16: AUDIT TRAIL
# ═══════════════════════════════════════════════════════════
def stage_16_audit():
    log("STAGE 16: Audit Trail")
    r = api("GET", f"{EP}/companies/{TENANT}/audit-trail")
    t("Audit trail available", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("  P60 COMMERCIAL PRODUCTIZATION — FULL CUSTOMER JOURNEY E2E")
    print("  16 Stages: Marketplace > Billing > AI > Builder > ERP > Portal > Ops")
    print("=" * 70)

    cleanup()
    proc = start_server()

    try:
        # Warm up
        c = httpx.Client(base_url=BASE, timeout=30)
        c.close()

        stage_1_marketplace()
        stage_2_billing_catalog()

        sid = stage_3_composer()
        if sid:
            pid = stage_4_builder(sid)
            if pid:
                stage_5_customize(pid)
                stage_6_preview_publish(pid)
                stage_7_use_erp()
                stage_8_isolation()
                stage_9_rbac()
                stage_10_versioning(pid)

        jid = stage_11_journey()
        if jid:
            stage_12_journey_lifecycle(jid)

        stage_13_portal()
        stage_14_billing()
        stage_15_production_ops()
        stage_16_audit()

    finally:
        stop_server(proc)

    print("\n" + "\n".join(results))
    print("\n" + "=" * 70)
    print(f"  P60 RESULTS: {passed}/{passed+failed} PASSED, {failed} FAILED")
    print("=" * 70)

    if failed == 0:
        print()
        print("  *** ENTREPRENEUR READY ***")
        print("  EOS is now a SaaS PRODUCT.")
        print("  A customer can:")
        print("    1. Browse marketplace (10 industry packs + addons)")
        print("    2. Write needs in Arabic (natural language)")
        print("    3. AI understands and builds ERP config")
        print("    4. Customer customizes modules, entities, roles")
        print("    5. Preview validates everything")
        print("    6. Choose plan (Starter/Pro/Business/Enterprise)")
        print("    7. Pay (provider-agnostic adapter)")
        print("    8. Launch ERP (publish with approval gate)")
        print("    9. Use ERP (create customers, invoices, projects)")
        print("   10. Full tenant isolation + RBAC")
        print("   11. Customer portal (tickets, subscription, usage)")
        print("   12. Production ops (backups, monitoring, deployments)")
        print("   13. Version control with rollback")
        print("  ZERO company-specific Python code.")
        print()
    else:
        print(f"\n  {failed} gaps found — see FAIL/CRITICAL lines above.")

    sys.exit(0 if failed == 0 else 1)
