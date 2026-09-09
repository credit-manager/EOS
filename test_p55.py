"""
P55 — Marketplace
Catalog browse → install pack/addon → per-tenant isolation → uninstall.
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
MKT = f"{EP}/marketplace"
TENANT = "tenant_p55"
TENANT_B = "tenant_p55_b"
H = {"Authorization": f"Bearer {create_test_token(TENANT, user_id='u55', email='a@55.com', roles=['admin'])}"}
H_B = {"Authorization": f"Bearer {create_test_token(TENANT_B, user_id='b55', email='b@55.com', roles=['admin'])}"}
H_V = {"Authorization": f"Bearer {create_test_token(TENANT, user_id='v55', email='v@55.com', roles=['dynamic_viewer'])}"}
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
        for tid in (TENANT, TENANT_B):
            db.execute(sa(f"DELETE FROM dbp_tenant_installations WHERE tenant_id='{tid}'"))
            for tbl in ("dbp_entities",):
                rows = db.execute(sa(f"SELECT id FROM {tbl} WHERE tenant_id='{tid}'")).fetchall()
                for r in rows:
                    db.execute(sa("DELETE FROM dbp_fields WHERE entity_id=:e"), {"e": r[0]})
                    db.execute(sa("DELETE FROM dbp_relationships WHERE entity_id=:e"), {"e": r[0]})
                    db.execute(sa(f"DELETE FROM {tbl} WHERE id=:e"), {"e": r[0]})
            for tbl in ("payroll_adjustments", "crm_leads"):
                db.execute(sa(f"DROP TABLE IF EXISTS public.{tbl}"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def main():
    print("=" * 70)
    print("  P55 MARKETPLACE")
    print("=" * 70)
    cleanup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        # 1. Catalog
        r = c.get(f"{MKT}/items", headers=H)
        t("List catalog", r.status_code, 200)
        items = r.json()["data"]
        t("Catalog has 10 items", len(items), 10)

        types = {i["item_type"] for i in items}
        t("Has industry_pack type", "industry_pack" in types, True)
        t("Has addon type", "addon" in types, True)

        r = c.get(f"{MKT}/items?item_type=industry_pack", headers=H)
        t("Filter industry packs = 6", len(r.json()["data"]), 6)

        r = c.get(f"{MKT}/items?featured=true", headers=H)
        t("Featured >= 3", len(r.json()["data"]) >= 3, True)

        r = c.get(f"{MKT}/items?search=\u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a", headers=H)
        t("Arabic search finds construction", any(i["item_code"] == "pack_construction" for i in r.json()["data"]), True)

        r = c.get(f"{MKT}/items/pack_construction", headers=H)
        t("Get construction details", r.status_code, 200)
        d = r.json()["data"]
        t("Payload has modules", len(d["payload"].get("modules", [])) >= 8, True)
        t("Construction is free", d["is_free"], True)

        r = c.get(f"{MKT}/items/addon_payroll_plus", headers=H)
        t("Payroll addon priced", float(r.json()["data"]["price_monthly"]) > 0, True)

        r = c.get(f"{MKT}/items/nope_404", headers=H)
        t("Unknown item → 404", r.status_code, 404)

        # 2. Install
        r = c.post(f"{MKT}/install", headers=H, json={"item_code": "pack_construction"})
        t("Install construction pack", r.status_code, 200, critical=True)
        applied = r.json()["data"]["applied"]
        t("Applied 9 modules", len(applied["modules"]), 9)

        r = c.post(f"{MKT}/install", headers=H, json={"item_code": "pack_construction"})
        t("Double install → 400", r.status_code, 400)

        r = c.post(f"{MKT}/install", headers=H, json={"item_code": "addon_crm_lite"})
        t("Install CRM addon", r.status_code, 200)
        t("CRM has entity payload", r.json()["data"]["applied"]["entities"], 1)

        r = c.post(f"{MKT}/install", headers=H, json={})
        t("Missing item_code → 400", r.status_code, 400)

        # 3. Isolation
        r = c.get(f"{MKT}/installed", headers=H_B)
        t("Tenant B sees 0 installs", len(r.json()["data"]), 0)

        r = c.post(f"{MKT}/install", headers=H_B, json={"item_code": "pack_retail"})
        t("Tenant B installs retail", r.status_code, 200)

        r = c.get(f"{MKT}/installed", headers=H)
        codes = [x["item_code"] for x in r.json()["data"]]
        t("Tenant A list unchanged (2)", len(codes), 2)
        t("No bleed of retail to A", "pack_retail" not in codes, True)

        # 4. RBAC
        r = c.get(f"{MKT}/installed", headers=H_V)
        t("Viewer can view installed", r.status_code, 200)
        r = c.post(f"{MKT}/install", headers=H_V, json={"item_code": "pack_trading"})
        t("Viewer cannot install → 403", r.status_code, 403)

        # 5. Uninstall
        r = c.post(f"{MKT}/uninstall", headers=H, json={"item_code": "addon_crm_lite"})
        t("Uninstall CRM", r.status_code, 200)

        r = c.get(f"{MKT}/installed", headers=H)
        t("A now has 1 installed", len(r.json()["data"]), 1)

        r = c.get(f"{MKT}/installed?include_removed=true", headers=H)
        removed = [x for x in r.json()["data"] if x["status"] == "removed"]
        t("Removed record kept for audit",
          len(removed) == 1 and bool(removed[0]["removed_at"]), True)

        r = c.post(f"{MKT}/uninstall", headers=H, json={"item_code": "addon_crm_lite"})
        t("Uninstall again → 400", r.status_code, 400)
    finally:
        c.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    print("\n" + "\n".join(results))
    print("\n" + "=" * 70)
    print(f"  P55 RESULTS: {p}/{p+fail} PASSED, {fail} FAILED")
    print("=" * 70)
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
