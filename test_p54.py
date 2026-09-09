"""
P54 — Self-Service ERP Builder (End-to-End)
Flow: AI Composer → Builder Project → Edit Config → Custom Entities → Preview
      → Approval Gate → Publish → Use Generated ERP via Dynamic CRUD
      → Tenant Isolation → RBAC → Version 2 → Rollback
No company-specific Python code — everything through platform APIs.
"""
import httpx, subprocess, sys, time, os, json
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
BLD = f"{EP}/builder"
CMP = f"{EP}/composer"

TENANT = "tenant_p54"
TENANT_OTHER = "tenant_p54_other"
TOKEN = create_test_token(TENANT, user_id="owner_p54", email="owner@p54.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
TOKEN_OTHER = create_test_token(TENANT_OTHER, user_id="other_p54", email="other@x.com", roles=["admin"])
H_OTHER = {"Authorization": f"Bearer {TOKEN_OTHER}"}
TOKEN_VIEWER = create_test_token(TENANT, user_id="viewer_p54", email="v@p54.com", roles=["dynamic_viewer"])
H_VIEWER = {"Authorization": f"Bearer {TOKEN_VIEWER}"}

E1, E2, E3 = "site_inspections", "equipment_requests", "warranty_claims"
T1, T2, T3 = f"bld_{E1}", f"bld_{E2}", f"bld_{E3}"

p, fail = 0, 0
results = []


def t(name, got, exp, critical=False):
    global p, fail
    if got == exp:
        p += 1
        results.append(f"  OK   {name}")
    else:
        fail += 1
        tag = "CRITICAL" if critical else "FAIL"
        results.append(f"  {tag}  {name}: got {got!r}, expected {exp!r}")


def log(msg):
    results.append(f"  ---  {msg}")


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


def cleanup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for ecode in [E1, E2, E3]:
            row = db.execute(sa("SELECT id FROM dbp_entities WHERE code=:c"), {"c": ecode}).fetchone()
            if row:
                db.execute(sa("DELETE FROM dbp_fields WHERE entity_id=:e"), {"e": row[0]})
                db.execute(sa("DELETE FROM dbp_relationships WHERE entity_id=:e"), {"e": row[0]})
                db.execute(sa("DELETE FROM dbp_entities WHERE id=:e"), {"e": row[0]})
        for tbl in [T1, T2, T3]:
            try:
                db.execute(sa(f"DROP TABLE IF EXISTS public.{tbl}"))
            except Exception:
                pass
        db.execute(sa(f"DELETE FROM dbp_builder_versions WHERE tenant_id='{TENANT}'"))
        db.execute(sa(f"DELETE FROM dbp_builder_projects WHERE tenant_id='{TENANT}'"))
        db.execute(sa(f"DELETE FROM dbp_composer_sessions WHERE tenant_id='{TENANT}'"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════
# STAGE 1: AI Composer generates starting point (P53)
# ═══════════════════════════════════════════════════════════
def stage_1_compose(c):
    log("STAGE 1: AI Composer (P53) — natural language start")
    r = c.post(f"{CMP}/compose", headers=H, json={
        "input": "\u0639\u0627\u064a\u0632 \u0646\u0638\u0627\u0645 \u0644\u0634\u0631\u0643\u0629 "
                 "\u0645\u0642\u0627\u0648\u0644\u0627\u062a \u0641\u064a\u0647\u0627 \u0645\u0634\u0627\u0631\u064a\u0639 "
                 "\u0648\u0645\u062e\u0627\u0632\u0646 \u0648\u0645\u0634\u062a\u0631\u064a\u0627\u062a "
                 "\u0648\u062d\u0633\u0627\u0628\u0627\u062a \u0648\u0645\u0648\u0627\u0641\u0642\u0627\u062a",
    })
    t("Compose request", r.status_code, 200, critical=True)
    data = r.json()["data"]
    sid = data["session_id"]
    t("Industry detected = construction", data["requirements"]["industry"], "construction")
    t("Composer session in preview status (not executed)", data["validation"]["valid"], True)
    return sid


# ═══════════════════════════════════════════════════════════
# STAGE 2: Builder project from composer session
# ═══════════════════════════════════════════════════════════
def stage_2_create_project(c, sid):
    log("STAGE 2: Create builder project FROM composer session")

    r = c.post(f"{BLD}/projects", headers=H, json={
        "name": "Al-Omran ERP Build",
        "composer_session_id": sid,
    })
    t("Create project from composer", r.status_code, 200, critical=True)
    pid = r.json()["data"]["project_id"]
    draft = r.json()["data"]["draft_config"]

    t("Draft industry prefilled", draft["industry"], "construction")
    mod_codes = [m["code"] for m in draft["modules"] if m["enabled"]]
    t_in = lambda name, val, coll: t(name, val in coll, True)
    t_in("Module procurement enabled", "procurement", mod_codes)
    t_in("Module projects enabled", "projects", mod_codes)
    t("Settings currency prefilled", draft["settings"].get("currency"), "SAR")
    t("No custom entities yet", len(draft["custom_entities"]), 0)

    r = c.get(f"{BLD}/projects/{pid}", headers=H)
    t("Get project", r.status_code, 200)
    t("Status is draft", r.json()["data"]["status"], "draft")
    return pid


# ═══════════════════════════════════════════════════════════
# STAGE 3: Edit configuration
# ═══════════════════════════════════════════════════════════
def stage_3_edit(c, pid):
    log("STAGE 3: Edit configuration (no developer needed)")

    r = c.put(f"{BLD}/projects/{pid}/settings", headers=H,
              json={"branches": 3, "employees": 50})
    t("Update settings (branches=3, employees=50)", r.status_code, 200)

    r = c.get(f"{BLD}/projects/{pid}", headers=H)
    st = r.json()["data"]["draft_config"]["settings"]
    t("Branches saved", st.get("branches"), 3)
    t("Employees saved", st.get("employees"), 50)

    r = c.put(f"{BLD}/projects/{pid}/modules", headers=H, json={
        "modules": [{"code": "bi", "enabled": False}]
    })
    t("Disable BI module", r.status_code, 200)

    r = c.get(f"{BLD}/projects/{pid}", headers=H)
    bi = [m for m in r.json()["data"]["draft_config"]["modules"] if m["code"] == "bi"]
    t("BI disabled in draft", bi[0]["enabled"], False)

    r = c.post(f"{BLD}/projects/{pid}/entities", headers=H, json={
        "entity_code": E1,
        "name_en": "Site Inspections",
        "name_ar": "\u062a\u0641\u062a\u064a\u0634 \u0627\u0644\u0645\u0648\u0627\u0642\u0639",
        "faculty": "operations",
        "fields": [
            {"code": "title", "label_en": "Title", "field_type": "string",
             "is_required": True, "label_ar": "\u0627\u0644\u0639\u0646\u0648\u0627\u0646"},
            {"code": "score", "label_en": "Score", "field_type": "number"},
            {"code": "status", "label_en": "Status", "field_type": "enum",
             "enum_values": ["pass", "fail", "pending"]},
            {"code": "inspection_date", "label_en": "Date", "field_type": "date"},
        ],
    })
    t(f"Add entity '{E1}' with 4 fields", r.status_code, 200, critical=True)

    r = c.post(f"{BLD}/projects/{pid}/entities", headers=H, json={
        "entity_code": E2,
        "name_en": "Equipment Requests",
        "faculty": "operations",
        "fields": [
            {"code": "title", "label_en": "Title", "field_type": "string", "is_required": True},
            {"code": "quantity", "label_en": "Quantity", "field_type": "integer"},
            {"code": "priority", "label_en": "Priority", "field_type": "enum",
             "enum_values": ["low", "normal", "high"]},
        ],
    })
    t(f"Add entity '{E2}' with 3 fields", r.status_code, 200)

    r = c.post(f"{BLD}/projects/{pid}/relationships", headers=H, json={
        "from_entity": E2, "to_entity": E1, "type": "many_to_one"})
    t("Add relationship E2→E1", r.status_code, 200)

    r = c.put(f"{BLD}/projects/{pid}/roles", headers=H, json={
        "inspector": ["read", "create"],
        "site_manager": ["*"],
        "viewer": ["read"],
    })
    t("Set custom roles", r.status_code, 200)

    r = c.post(f"{BLD}/projects/{pid}/workflows", headers=H, json={
        "name": "Inspection Approval", "trigger": f"{E1}_created",
        "steps": ["site_manager"]})
    t("Add workflow", r.status_code, 200)

    r = c.post(f"{BLD}/projects/{pid}/kpis", headers=H, json={
        "name": "Failed Inspections", "metric": "failed_count", "aggregation": "COUNT"})
    t("Add KPI", r.status_code, 200)

    r = c.post(f"{BLD}/projects/{pid}/entities", headers=H, json={
        "entity_code": "Bad Code!", "name_en": "X", "fields": [{"code": "a", "field_type": "string"}]})
    t("Invalid entity code rejected", r.status_code, 400)

    r = c.post(f"{BLD}/projects/{pid}/entities", headers=H, json={
        "entity_code": "badtype_test", "name_en": "X",
        "fields": [{"code": "a", "field_type": "varchar2"}]})
    t("Invalid field type rejected", r.status_code, 400)

    r = c.delete(f"{BLD}/projects/{pid}/entities/badtype_test", headers=H)
    t("Cleanup rejected entity ignored (not added)", r.status_code, 400)


# ═══════════════════════════════════════════════════════════
# STAGE 4: Preview & Validation
# ═══════════════════════════════════════════════════════════
def stage_4_preview(c, pid):
    log("STAGE 4: Configuration Preview")

    r = c.get(f"{BLD}/projects/{pid}/preview", headers=H)
    t("Preview draft", r.status_code, 200)
    d = r.json()["data"]

    t("Validation passes", d["validation"]["valid"], True, critical=True)
    s = d["validation"]["summary"]
    t("Summary: 2 custom entities", s["custom_entities"], 2)
    t("Summary: 7 fields total", s["total_fields"], 7)
    t("Summary: 1 relationship", s["relationships"], 1)
    t("Summary: 3 roles", s["roles"], 3)
    t("Summary: workflows (composer + custom) >= 1", s["workflows"] >= 1, True)
    t_gt_kpis = s["kpis"] >= 6
    t("Summary: KPIs (composer + custom) >= 6", t_gt_kpis, True)
    t("Config included in preview", d["config"]["industry"], "construction")


# ═══════════════════════════════════════════════════════════
# STAGE 5: Approval Gate
# ═══════════════════════════════════════════════════════════
def stage_5_approval_gate(c, pid):
    log("STAGE 5: Approval Gate — nothing executes without explicit approval")

    r = c.post(f"{BLD}/projects/{pid}/publish", headers=H, json={})
    t("Publish without confirmation → 400", r.status_code, 400, critical=True)

    r = c.post(f"{BLD}/projects/{pid}/publish", headers=H, json={"confirmed": False})
    t("Publish confirmed=False → 400", r.status_code, 400)

    r = c.get(f"{BLD}/active", headers=H)
    t("No active config before publish", r.status_code, 404)


# ═══════════════════════════════════════════════════════════
# STAGE 6: Publish v1
# ═══════════════════════════════════════════════════════════
def stage_6_publish(c, pid):
    log("STAGE 6: Publish version 1 (creates real entities)")

    r = c.post(f"{BLD}/projects/{pid}/publish", headers=H, json={
        "confirmed": True,
        "change_summary": "Initial build: inspections + equipment requests",
    })
    t("Publish v1", r.status_code, 200, critical=True)
    d = r.json()["data"]
    t("Version number = 1", d["version_number"], 1)
    t_in_ok = lambda name, val, coll: t(name, val in coll, True)
    t_in_ok("Entity E1 published", E1, d["entities_published"])
    t_in_ok("Entity E2 published", E2, d["entities_published"])

    r = c.get(f"{BLD}/active", headers=H)
    t("Active config exists", r.status_code, 200)
    act = r.json()["data"]
    t("Active version = 1", act["version_number"], 1)
    t("Active config has entities", len(act["config"]["custom_entities"]), 2)

    r = c.get(f"{BLD}/projects/{pid}", headers=H)
    t("Project status = published", r.json()["data"]["status"], "published")


# ═══════════════════════════════════════════════════════════
# STAGE 7: Use the Generated ERP (Dynamic CRUD)
# ═══════════════════════════════════════════════════════════
def stage_7_use_erp(c):
    log("STAGE 7: Use generated ERP — create/query business records")

    rec = {
        "id": "11111111-1111-4111-8111-111111111111",
        "title": "Foundation inspection - Block A",
        "score": 92.5,
        "status": "pass",
        "inspection_date": "2026-02-01",
    }
    r = c.post(f"{EP}/entities/{E1}/records", headers=H, json=rec)
    t(f"Create record in '{E1}'", r.status_code, 200, critical=True)

    rec2 = dict(rec, id="22222222-2222-4222-8222-222222222222",
                title="Steel check - Floor 2", score=48.0, status="fail")
    r = c.post(f"{EP}/entities/{E1}/records", headers=H, json=rec2)
    t("Create second record", r.status_code, 200)

    r = c.post(f"{EP}/entities/{E1}/records", headers=H, json={
        "id": "33333333-3333-4333-8333-333333333333",
        "score": 70, "status": "pass",
    })
    t("Missing required field 'title' → 400", r.status_code, 400)

    r = c.post(f"{EP}/entities/{E1}/records", headers=H, json={
        "id": "44444444-4444-4444-8444-444444444444",
        "title": "Bad enum", "status": "excellent",
    })
    t("Invalid enum value → 400", r.status_code, 400)

    r = c.get(f"{EP}/entities/{E1}/records", headers=H)
    t(f"List records of '{E1}'", r.status_code, 200)
    d = r.json()
    t("Tenant sees own 2 records", d["count"], 2)
    titles = [x["title"] for x in d["data"]]
    t("Record content correct", "Foundation inspection - Block A" in titles, True)

    r = c.get(f"{EP}/entities/{E1}/records?filters=status:eq:fail", headers=H)
    t("Filtered query (status:eq:fail) returns 1", r.status_code == 200 and r.json().get("count") == 1, True)

    r = c.post(f"{EP}/entities/{E2}/records", headers=H, json={
        "id": "55555555-5555-4555-8555-555555555555",
        "title": "Request crane - site B", "quantity": 1, "priority": "high",
    })
    t(f"Create record in '{E2}'", r.status_code, 200)


# ═══════════════════════════════════════════════════════════
# STAGE 8: Tenant isolation on generated ERP
# ═══════════════════════════════════════════════════════════
def stage_8_isolation(c):
    log("STAGE 8: Tenant isolation")

    r = c.get(f"{EP}/entities/{E1}/records", headers=H_OTHER)
    t("Other tenant can reach list endpoint", r.status_code, 200)
    if r.status_code == 200:
        t("Other tenant sees 0 records", r.json()["count"], 0, critical=True)

    r = c.get(f"{BLD}/projects", headers=H_OTHER)
    t("Other tenant has no builder projects", len(r.json()["data"]), 0)

    r = c.get(f"{BLD}/active", headers=H_OTHER)
    t("Other tenant has no active config", r.status_code, 404)


# ═══════════════════════════════════════════════════════════
# STAGE 9: RBAC
# ═══════════════════════════════════════════════════════════
def stage_9_rbac(c):
    log("STAGE 9: RBAC on generated entities")

    r = c.get(f"{EP}/entities/{E1}/records", headers=H_VIEWER)
    t("Viewer CAN read records", r.status_code, 200)

    r = c.post(f"{EP}/entities/{E1}/records", headers=H_VIEWER, json={
        "id": "66666666-6666-4666-8666-666666666666", "title": "nope"})
    t("Viewer CANNOT create records → 403", r.status_code, 403, critical=True)

    r = c.post(f"{BLD}/projects/xxx/publish", headers=H_VIEWER, json={"confirmed": True})
    t("Viewer CANNOT publish → 403", r.status_code, 403)


# ═══════════════════════════════════════════════════════════
# STAGE 10: Version 2 + Rollback to v1
# ═══════════════════════════════════════════════════════════
def stage_10_versions(c, pid):
    log("STAGE 10: Versioning & Rollback")

    r = c.post(f"{BLD}/projects/{pid}/entities", headers=H, json={
        "entity_code": E3, "name_en": "Warranty Claims",
        "fields": [
            {"code": "title", "label_en": "Title", "field_type": "string", "is_required": True},
            {"code": "claim_amount", "label_en": "Amount", "field_type": "number"},
        ]})
    t(f"Draft: add third entity '{E3}'", r.status_code, 200)

    r = c.post(f"{BLD}/projects/{pid}/publish", headers=H, json={
        "confirmed": True, "change_summary": "Add warranty claims"})
    t("Publish v2", r.status_code, 200)
    t("Version number = 2", r.json()["data"]["version_number"], 2)

    r = c.post(f"{EP}/entities/{E3}/records", headers=H, json={
        "id": "77777777-7777-4777-8777-777777777777",
        "title": "Cracks in wall", "claim_amount": 15000})
    t("E3 record created after v2", r.status_code, 200)

    versions = c.get(f"{BLD}/projects/{pid}/versions", headers=H).json()["data"]
    t("Version history has 2 entries", len(versions), 2)
    active = [v for v in versions if v["is_active"]]
    t("Exactly one active version", len(active), 1)
    t("Active is v2", active[0]["version_number"], 2)

    v1 = next(v for v in versions if v["version_number"] == 1)
    r = c.post(f"{BLD}/projects/{pid}/rollback", headers=H, json={"version_id": v1["id"]})
    t("Rollback to v1", r.status_code, 200, critical=True)
    rb = r.json()["data"]
    t("Rollback removed E3", rb["entities_removed"], [E3])
    t("Rollback created new version 3", rb["new_version_number"], 3)

    r = c.post(f"{EP}/entities/{E3}/records", headers=H, json={
        "id": "88888888-8888-4888-8888-888888888888", "title": "post-rollback"})
    t("E3 unusable after rollback → 404", r.status_code, 404, critical=True)

    r = c.get(f"{EP}/entities/{E1}/records", headers=H)
    t("E1 still works after rollback", r.status_code, 200)
    if r.status_code == 200:
        t("E1 data preserved", r.json()["count"], 2, critical=True)

    r = c.get(f"{BLD}/projects/{pid}/versions", headers=H)
    versions = r.json()["data"]
    t("Version audit trail now 3 entries", len(versions), 3)
    active = [v for v in versions if v["is_active"]]
    t("Active is now v3 (v1 config)", active[0]["version_number"], 3)
    t("V3 summary mentions rollback", "Rollback" in (active[0]["change_summary"] or ""), True)

    r = c.get(f"{BLD}/active", headers=H)
    cfg = r.json()["data"]["config"]
    codes = [e["entity_code"] for e in cfg["custom_entities"]]
    t("Active config matches rolled-back state", E3 not in codes and E1 in codes, True)


# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("  P54 SELF-SERVICE ERP BUILDER — END-TO-END")
    print("  Composer → Builder → Publish → Real ERP Usage → Rollback")
    print("=" * 70)

    cleanup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)

    try:
        sid = stage_1_compose(c)
        pid = stage_2_create_project(c, sid)
        stage_3_edit(c, pid)
        stage_4_preview(c, pid)
        stage_5_approval_gate(c, pid)
        stage_6_publish(c, pid)
        stage_7_use_erp(c)
        stage_8_isolation(c)
        stage_9_rbac(c)
        stage_10_versions(c, pid)
    finally:
        c.close()
        stop(proc)

    print("\n" + "\n".join(results))
    print("\n" + "=" * 70)
    print(f"  P54 RESULTS: {p}/{p+fail} PASSED, {fail} FAILED")
    print("=" * 70)

    if fail == 0:
        print("\n  CONCLUSION: Customer built a working ERP without a developer:")
        print("  Arabic request → AI config → edited → approved → published →")
        print("  real records created → isolated per tenant → rolled back safely.")
    else:
        print(f"\n  {fail} gaps found.")

    sys.exit(0 if fail == 0 else 1)
