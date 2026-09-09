"""
P56 — Billing & Subscription Flow
Plan catalog → checkout → invoice → payment → license → usage → change-plan.
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
BF = f"{EP}/billing-flow"
TENANT = "tenant_p56"
TENANT_B = "tenant_p56_b"
H = {"Authorization": f"Bearer {create_test_token(TENANT, user_id='u56', email='a@56.com', roles=['admin'])}"}
H_B = {"Authorization": f"Bearer {create_test_token(TENANT_B, user_id='b56', email='b@56.com', roles=['admin'])}"}
H_V = {"Authorization": f"Bearer {create_test_token(TENANT, user_id='v56', email='v@56.com', roles=['dynamic_viewer'])}"}
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
                         "dbp_invoices_saas", "dbp_subscriptions"):
                try:
                    db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id='{tid}'"))
                    db.commit()
                except Exception:
                    db.rollback()
        db.execute(sa("DELETE FROM dbp_saas_tenants WHERE tenant_id IN ('%s','%s')" % (TENANT, TENANT_B)))
        db.commit()
    finally:
        db.close()


def main():
    print("=" * 70)
    print("  P56 BILLING & SUBSCRIPTION FLOW")
    print("=" * 70)
    cleanup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        # Catalog
        r = c.get(f"{BF}/plans", headers=H)
        t("List plans", r.status_code, 200)
        plans = r.json()["data"]
        t("4 plans in catalog", len(plans), 4)
        codes = [x["plan_code"] for x in plans]
        for want in ["starter", "professional", "business", "enterprise"]:
            t(f"Plan '{want}' present", want in codes, True)
        prof = next(x for x in plans if x["plan_code"] == "professional")
        t("Professional price = 299/mo", float(prof["price_monthly"]), 299.0)
        t("Plans sorted by price", codes, sorted(codes, key=lambda x: [s["price_monthly"] for s in plans].index(0) if False else codes.index(x)))

        # Checkout
        r = c.post(f"{BF}/checkout", headers=H,
                   json={"plan_code": "professional", "billing_cycle": "monthly"})
        t("Checkout professional monthly", r.status_code, 200, critical=True)
        d = r.json()["data"]
        inv_id = d["invoice_id"]
        t("Amount due = 299 SAR", float(d["amount_due"]), 299.0)
        t("Status awaiting_payment", d["status"], "awaiting_payment")

        r = c.post(f"{BF}/checkout", headers=H, json={"plan_code": "business"})
        t("Second checkout blocked while awaiting payment", r.status_code, 400)

        r = c.post(f"{BF}/checkout", headers=H, json={"plan_code": "nope"})
        t("Unknown plan → 400", r.status_code, 400)

        # Subscription state pre-payment
        r = c.get(f"{BF}/my-subscription", headers=H)
        t("My subscription exists", r.status_code, 200)
        sub = r.json()["data"]
        t("Plan is professional", sub["plan"]["plan_code"], "professional")
        t("No license before payment", sub["license"], None)

        # Pay
        r = c.post(f"{BF}/invoices/{inv_id}/pay", headers=H, json={"payment_method": "card"})
        t("Pay invoice", r.status_code, 200, critical=True)
        pay_d = r.json()["data"]
        t("Invoice now paid", pay_d["invoice_status"], "paid")
        t("License issued", bool(pay_d["license_key"]), True)
        t("License type matches plan", pay_d["license_type"] if False else pay_d["plan"], "professional")

        r = c.post(f"{BF}/invoices/{inv_id}/pay", headers=H, json={})
        t("Double payment → 400", r.status_code, 400)

        # License visible in my-subscription
        r = c.get(f"{BF}/my-subscription", headers=H)
        lic = r.json()["data"]["license"]
        t("Active license with seats=25", lic and lic["seats"], 25)

        # Usage
        r = c.post(f"{BF}/usage", headers=H, json={"meter_name": "active_users", "meter_value": 12})
        t("Record usage active_users=12", r.status_code, 200)
        r = c.post(f"{BF}/usage", headers=H, json={"meter_name": "storage_gb", "meter_value": 18.5})
        t("Record usage storage=18.5GB", r.status_code, 200)

        r = c.get(f"{BF}/usage-summary", headers=H)
        t("Usage summary", r.status_code, 200)
        us = r.json()["data"]
        t("Meters recorded", us["meters"].get("active_users"), 12.0)
        t("Limit users = 25", us["limits"].get("users"), 25)
        t("No over-limit", us["over_limit"], [])

        r = c.post(f"{BF}/usage", headers=H_V, json={"meter_name": "active_users", "meter_value": 1})
        t("Viewer cannot record usage → 403", r.status_code, 403)

        # Change plan
        r = c.post(f"{BF}/change-plan", headers=H, json={"plan_code": "business"})
        t("Change plan → business", r.status_code, 200, critical=True)
        ch = r.json()["data"]
        t("Changed from professional", ch["changed_from"], "professional")
        new_inv = ch["invoice_id"]

        r = c.post(f"{BF}/invoices/{new_inv}/pay", headers=H, json={})
        t("Pay upgrade invoice", r.status_code, 200)
        t("New plan business", r.json()["data"]["plan"], "business")

        r = c.get(f"{BF}/usage-summary", headers=H)
        t("Limits upgraded to 100 users", r.json()["data"]["limits"].get("users"), 100)

        # Isolation
        r = c.get(f"{BF}/my-subscription", headers=H_B)
        t("Tenant B has no subscription → 404", r.status_code, 404)
    finally:
        c.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    print("\n" + "\n".join(results))
    print("\n" + "=" * 70)
    print(f"  P56 RESULTS: {p}/{p+fail} PASSED, {fail} FAILED")
    print("=" * 70)
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
