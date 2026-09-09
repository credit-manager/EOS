"""
P58 — SaaS Experience (The Flagship E2E)
Arabic description → AI → customize → plan → pay → launch gate → live ERP.
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
EXP = f"{EP}/experience"
TENANT = "tenant_p58"
TENANT_B = "tenant_p58_b"
H = {"Authorization": f"Bearer {create_test_token(TENANT, user_id='u58', email='a@58.com', roles=['admin'])}"}
H_B = {"Authorization": f"Bearer {create_test_token(TENANT_B, user_id='b58', email='b@58.com', roles=['admin'])}"}
H_V = {"Authorization": f"Bearer {create_test_token(TENANT, user_id='v58', email='v@58.com', roles=['dynamic_viewer'])}"}
p, fail = 0, 0
results = []


def t(name, got, exp, critical=False):
    global p, fail
    if got == exp:
        p += 1
        results.append(f"  OK   {name}")
    else:
        fail += 1
        results.append(f"  {'CRITICAL' if critical else 'FAIL'}  {name}: got {got!r}, expected {exp!r}")


def start():
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(5)
    return proc


def cleanup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        all_bld = set()
        for tid in (TENANT, TENANT_B):
            all_bld |= {r[0] for r in db.execute(sa(
                "SELECT DISTINCT table_mapping FROM dbp_entities "
                "WHERE tenant_id=:t AND table_mapping LIKE 'bld_%'"), {"t": tid}).fetchall()}
            rows = db.execute(sa("SELECT id FROM dbp_entities WHERE tenant_id=:t AND is_system=false"),
                               {"t": tid}).fetchall()
            for (eid,) in rows:
                db.execute(sa("DELETE FROM dbp_fields WHERE entity_id=:e"), {"e": eid})
                db.execute(sa("DELETE FROM dbp_relationships WHERE entity_id=:e"), {"e": eid})
                db.execute(sa("DELETE FROM dbp_entities WHERE id=:e"), {"e": eid})
        db.commit()
        for tbl in sorted(all_bld):
            try:
                db.execute(sa(f"DROP TABLE IF EXISTS public.{tbl}"))
                db.commit()
            except Exception:
                db.rollback()
        for tid in (TENANT, TENANT_B):
            for tbl in ("dbp_usage_meters", "dbp_licenses", "dbp_payments_saas",
                         "dbp_invoices_saas", "dbp_subscriptions",
                         "dbp_saas_journeys", "dbp_builder_versions",
                         "dbp_builder_projects", "dbp_composer_sessions"):
                try:
                    db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id='{tid}'"))
                    db.commit()
                except Exception:
                    db.rollback()
    finally:
        db.close()


def main():
    print("=" * 70)
    print("  P58 SAAS EXPERIENCE — FLAGSHIP END-TO-END")
    print("=" * 70)
    cleanup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        AR_DESC = ("\u0645\u0637\u0639\u0645 \u0641\u0627\u062e\u0631 \u0641\u064a \u0627\u0644\u0631\u064a\u0627\u0636 "
                   "\u0628\u0647 4 \u0641\u0631\u0648\u0639\u060c \u0646\u062d\u062a\u0627\u062c "
                   "\u0644\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0645\u062e\u0632\u0646 "
                   "\u0648\u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a \u0648\u0627\u0644\u0645\u0648\u0627\u0635\u0641\u064a\u0646")

        # STEP 1 — Start journey with Arabic description
        r = c.post(f"{EXP}/journeys", headers=H, json={
            "business_description": AR_DESC,
            "company_name": "Restaurant Al-Fakher",
            "admin_email": "owner@fakher.sa"})
        t("Start journey (Arabic)", r.status_code, 200, critical=True)
        d = r.json()["data"]
        jid = d["journey_id"]
        t("Industry detected = restaurant", d["detected_industry"], "restaurant")
        t("Language detected = ar", d["detected_language"], "ar")
        t("Status drafted", d["status"], "drafted")
        t("Inventory module proposed", "inventory" in d["modules"], True)
        t("Summary counts present", d["summary"]["enabled_modules"] >= 3, True)

        r = c.post(f"{EXP}/journeys", headers=H, json={"business_description": ""})
        t("Empty description → 400", r.status_code, 400)

        # STEP 2 — Customize
        r = c.put(f"{EXP}/journeys/{jid}/customize", headers=H, json={
            "settings": {"branches": 4, "employees": 60},
            "disable_modules": ["bi"]})
        t("Customize settings + disable BI", r.status_code, 200, critical=True)
        t("Status customized", r.json()["data"]["status"], "customized")

        r = c.put(f"{EXP}/journeys/{jid}/customize", headers=H, json={
            "add_entities": [{
                "entity_code": "menu_items",
                "name_en": "Menu Items",
                "name_ar": "\u0623\u0635\u0646\u0627\u0641 \u0627\u0644\u0642\u0627\u0626\u0645\u0629",
                "fields": [
                    {"code": "item_name", "label_en": "Name", "field_type": "string", "is_required": True},
                    {"code": "price", "field_type": "number"},
                    {"code": "category", "field_type": "enum",
                     "enum_values": ["appetizer", "main", "dessert", "drink"]}]}]})
        t("Add custom entity menu_items", r.status_code, 200)

        r = c.get(f"{EXP}/journeys/{jid}/preview", headers=H)
        t("Preview journey", r.status_code, 200)
        pv = r.json()["data"]
        t("Preview shows custom entity", "menu_items" in pv["config_summary"]["custom_entities"], True)
        t("BI disabled in preview", "bi" not in pv["config_summary"]["modules_enabled"], True)
        t("Validation valid", pv["validation"]["valid"], True)

        # STEP 3 — Choose plan
        r = c.post(f"{EXP}/journeys/{jid}/select-plan", headers=H,
                   json={"plan_code": "starter"})
        t("Select starter plan", r.status_code, 200, critical=True)
        sp = r.json()["data"]
        t("Amount due = 99 SAR", float(sp["amount_due"]), 99.0)
        inv_id = sp["invoice_id"]

        r = c.post(f"{EXP}/journeys/{jid}/select-plan", headers=H,
                   json={"plan_code": "nope"})
        t("Invalid plan → 400", r.status_code, 400)

        # STEP 4 gates — cannot launch before pay; cannot launch unconfirmed
        r = c.post(f"{EXP}/journeys/{jid}/launch", headers=H, json={"confirmed": True})
        t("Launch before payment → 400", r.status_code, 400, critical=True)

        r = c.post(f"{EXP}/journeys/{jid}/pay", headers=H, json={})
        t("Pay invoice", r.status_code, 200, critical=True)
        t("License issued at pay", bool(r.json()["data"]["license_key"]), True)
        t("Journey paid", r.json()["data"]["status"], "paid")

        r = c.put(f"{EXP}/journeys/{jid}/customize", headers=H,
                  json={"settings": {"branches": 9}})
        t("Customize after payment blocked → 400", r.status_code, 400)

        # STEP 5 — Launch approval gate
        r = c.post(f"{EXP}/journeys/{jid}/launch", headers=H, json={})
        t("Launch without confirm → 400", r.status_code, 400, critical=True)

        r = c.post(f"{EXP}/journeys/{jid}/launch", headers=H, json={"confirmed": True})
        t("LAUNCH — ERP is ready", r.status_code, 200, critical=True)
        ln = r.json()["data"]
        t("Status erp_ready", ln["status"], "erp_ready")
        t("menu_items published live", "menu_items" in ln["entities_published"], True)
        t("Version 1 published", ln["version_number"], 1)

        # USE the generated ERP via standard CRUD
        rec = {"id": "99999999-9999-4999-8999-999999999999",
               "item_name": "\u0643\u0634\u0631\u064a \u0644\u062d\u0645",
               "price": 28.0, "category": "main"}
        r = c.post(f"{EP}/entities/menu_items/records", headers=H, json=rec)
        t("Create record in generated ERP", r.status_code, 200, critical=True)

        r = c.get(f"{EP}/entities/menu_items/records", headers=H)
        t("Query generated ERP returns 1 record",
          r.status_code == 200 and r.json().get("count") == 1, True)

        # Journey final state
        r = c.get(f"{EXP}/journeys/{jid}", headers=H)
        j = r.json()["data"]
        t("Progress 100%", j["progress_percent"], 100)
        t("No steps remaining", len(j["steps_remaining"]), 0)
        t("License key stored", bool(j["license_key"]), True)

        # Isolation & RBAC
        r = c.get(f"{EXP}/journeys/{jid}", headers=H_B)
        t("Other tenant cannot see journey → 404", r.status_code, 404)

        r = c.post(f"{EXP}/journeys/{jid}/launch", headers=H_V, json={"confirmed": True})
        t("Viewer cannot relaunch → 403", r.status_code, 403)

        r = c.get(f"{EXP}/journeys", headers=H)
        t("List journeys has ours", any(x["id"] == jid for x in r.json()["data"]), True)
    finally:
        c.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    print("\n" + "\n".join(results))
    print("\n" + "=" * 70)
    print(f"  P58 RESULTS: {p}/{p+fail} PASSED, {fail} FAILED")
    print("=" * 70)
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
