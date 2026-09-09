"""
P57 — Customer Portal
One-stop overview aggregating all tenant state + support tickets.
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
POR = f"{EP}/portal"
TENANT = "tenant_p57"
TENANT_B = "tenant_p57_b"
H = {"Authorization": f"Bearer {create_test_token(TENANT, user_id='u57', email='a@57.com', roles=['admin'])}"}
H_B = {"Authorization": f"Bearer {create_test_token(TENANT_B, user_id='b57', email='b@57.com', roles=['admin'])}"}
H_V = {"Authorization": f"Bearer {create_test_token(TENANT, user_id='v57', email='v@57.com', roles=['dynamic_viewer'])}"}
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
            for tbl in ("dbp_usage_meters", "dbp_licenses", "dbp_payments_saas",
                         "dbp_invoices_saas", "dbp_subscriptions",
                         "dbp_tenant_installations", "dbp_builder_versions",
                         "dbp_builder_projects", "dbp_support_tickets",
                         "dbp_tenant_notifications", "dbp_companies"):
                try:
                    db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id='{tid}'"))
                    db.commit()
                except Exception:
                    db.rollback()
    finally:
        db.close()


def main():
    print("=" * 70)
    print("  P57 CUSTOMER PORTAL")
    print("=" * 70)
    cleanup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        # Seed tenant state through real platform APIs
        r = c.post(f"{EP}/companies", headers=H, json={
            "code": "P57CO", "name_en": "Portal Test Co", "base_currency": "SAR"})
        t("Setup: create company", r.status_code, 200)

        r = c.post(f"{EP}/billing-flow/checkout", headers=H,
                   json={"plan_code": "professional"})
        inv_id = r.json()["data"]["invoice_id"]
        c.post(f"{EP}/billing-flow/invoices/{inv_id}/pay", headers=H, json={})
        results.append("  ---  Setup: subscription active (paid)")

        c.post(f"{EP}/marketplace/install", headers=H, json={"item_code": "pack_services"})
        results.append("  ---  Setup: marketplace pack installed")

        r = c.post(f"{EP}/builder/projects", headers=H, json={"name": "Portal Co Build"})
        pid = r.json()["data"]["project_id"]
        results.append("  ---  Setup: builder project created")

        c.post(f"{EP}/tenant-lifecycle/notifications", headers=H, json={
            "notification_type": "system", "title": "Welcome to EOS"})
        results.append("  ---  Setup: notification created")

        # Overview — the core of P57
        r = c.get(f"{POR}/overview", headers=H)
        t("Get overview", r.status_code, 200, critical=True)
        ov = r.json()["data"]

        expected_sections = ["company", "onboarding", "subscription", "usage",
                             "marketplace", "erp_builder", "notifications", "support"]
        for s in expected_sections:
            t(f"Section '{s}' present", s in ov, True)

        t("Company name correct", ov["company"]["data"]["name_en"], "Portal Test Co")
        t("Subscription plan professional", ov["subscription"]["data"]["plan_code"], "professional")
        t("Open amount = 0 (all paid)", float(ov["subscription"]["data"]["open_amount"] or 0), 0.0)
        t("License seats visible", ov["subscription"]["data"]["license_seats"], 25)
        t("Marketplace count = 1", ov["marketplace"]["data"]["count"], 1)
        t("Marketplace item listed", "pack_services" in ov["marketplace"]["data"]["items"], True)
        t("Builder projects = 1 draft", ov["erp_builder"]["data"]["projects_total"], 1)
        t("Onboarding not started", ov["onboarding"]["data"]["status"], "not_started")
        t("No section errored", all(ov[s]["error"] is None for s in expected_sections), True)

        # Support tickets
        r = c.post(f"{POR}/support/tickets", headers=H, json={
            "subject": "Need help with invoice export",
            "message": "How do I export invoices to Excel?",
            "priority": "normal"})
        t("Create ticket", r.status_code, 200)
        tk = r.json()["data"]
        t("Ticket number assigned", bool(tk["ticket_number"]), True)

        r = c.post(f"{POR}/support/tickets", headers=H, json={
            "subject": "Urgent: cannot login", "priority": "urgent"})
        t("Create urgent ticket", r.status_code, 200)

        r = c.post(f"{POR}/support/tickets", headers=H, json={"subject": ""})
        t("Empty subject → 400", r.status_code, 400)

        r = c.post(f"{POR}/support/tickets", headers=H, json={
            "subject": "x", "priority": "asap"})
        t("Invalid priority → 400", r.status_code, 400)

        r = c.get(f"{POR}/support/tickets", headers=H)
        t("List tickets = 2", len(r.json()["data"]), 2)

        r = c.put(f"{POR}/support/tickets/{tk['ticket_id']}/close", headers=H)
        t("Close first ticket", r.status_code, 200)

        r = c.get(f"{POR}/support/tickets?status=open", headers=H)
        t("Only 1 open ticket remains", len(r.json()["data"]), 1)

        r = c.put(f"{POR}/support/tickets/{tk['ticket_id']}/close", headers=H)
        t("Re-close → 400", r.status_code, 400)

        # Overview reflects support + notifications
        r = c.get(f"{POR}/overview", headers=H)
        ov = r.json()["data"]
        t("Overview shows 2 tickets total", ov["support"]["data"]["tickets_total"], 2)
        t("Overview shows 1 open", ov["support"]["data"]["open"], 1)
        t("Unread notifications >= 1", ov["notifications"]["data"]["unread"], 1)

        # Isolation
        r = c.get(f"{POR}/overview", headers=H_B)
        ovb = r.json()["data"]
        t("Tenant B no company", ovb["company"]["data"], None)
        t("Tenant B no subscription", ovb["subscription"]["data"]["status"], "no_subscription")
        t("Tenant B marketplace empty", ovb["marketplace"]["data"]["count"], 0)
        t("Tenant B zero tickets", ovb["support"]["data"]["tickets_total"], 0)

        # RBAC
        r = c.get(f"{POR}/overview", headers=H_V)
        t("Viewer can read overview", r.status_code, 200)
        r = c.post(f"{POR}/support/tickets", headers=H_V, json={"subject": "hi"})
        t("Viewer cannot create ticket → 403", r.status_code, 403)
    finally:
        c.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    print("\n" + "\n".join(results))
    print("\n" + "=" * 70)
    print(f"  P57 RESULTS: {p}/{p+fail} PASSED, {fail} FAILED")
    print("=" * 70)
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
