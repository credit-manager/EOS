"""
P43 Subscription & Licensing Tests
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic/billing"
TOKEN_A = create_test_token("tenant_a", user_id="admin_a", email="admin_a@test.com", roles=["admin"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="admin_b@test.com", roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com", roles=["dynamic_viewer"])
H_A = {"Authorization": f"Bearer {TOKEN_A}"}
H_B = {"Authorization": f"Bearer {TOKEN_B}"}
HV = {"Authorization": f"Bearer {TOKEN_V}"}
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
        for tbl in ['dbp_subscriptions', 'dbp_invoices_saas', 'dbp_payments_saas',
                     'dbp_licenses', 'dbp_usage_meters']:
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.commit()
    finally:
        db.close()


def cleanup():
    setup()


def test_subscriptions(c):
    print("\n--- 1. Subscriptions ---")
    r = c.post(f"{EP}/subscription", json={"plan_id": "enterprise",
               "billing_cycle": "monthly"}, headers=H_A)
    t("Create subscription", r.status_code, 200)
    sid = r.json()["data"]["id"]

    r = c.get(f"{EP}/subscription", headers=H_A)
    t("Get subscription", r.status_code, 200)
    t("Plan correct", r.json()["data"]["plan_id"], "enterprise")

    r = c.get(f"{EP}/subscription", headers=H_B)
    t("Tenant B no subscription", r.status_code, 404)

    r = c.get(f"{EP}/subscriptions", headers=H_A)
    t("List subscriptions", r.status_code, 200)
    t("One subscription", len(r.json()["data"]), 1)


def test_invoices(c):
    print("\n--- 2. Invoices ---")
    sub = c.get(f"{EP}/subscription", headers=H_A).json()["data"]
    r = c.post(f"{EP}/invoices", json={"subscription_id": sub["id"],
               "invoice_number": "INV-001", "amount": 99.99,
               "line_items": [{"desc": "Enterprise Plan", "amount": 99.99}]},
               headers=H_A)
    t("Create invoice", r.status_code, 200)
    inv_id = r.json()["data"]["id"]

    r = c.post(f"{EP}/invoices", json={"subscription_id": sub["id"],
               "invoice_number": "INV-002", "amount": 199.99}, headers=H_A)
    t("Create second invoice", r.status_code, 200)

    r = c.get(f"{EP}/invoices", headers=H_A)
    t("List invoices", r.status_code, 200)
    t("Two invoices", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/invoices/{inv_id}", headers=H_A)
    t("Get invoice", r.status_code, 200)
    t("Amount correct", r.json()["data"]["amount"], 99.99)

    r = c.put(f"{EP}/invoices/{inv_id}", json={"status": "paid"}, headers=H_A)
    t("Mark invoice paid", r.status_code, 200)

    r = c.get(f"{EP}/invoices/{inv_id}", headers=H_A)
    t("Invoice is paid", r.json()["data"]["status"], "paid")
    t("Paid at set", r.json()["data"]["paid_at"] is not None, True)

    r = c.get(f"{EP}/invoices", headers=H_B)
    t("Tenant B no A invoices", len(r.json()["data"]), 0)


def test_payments(c):
    print("\n--- 3. Payments ---")
    r = c.post(f"{EP}/payments", json={"amount": 99.99,
               "payment_method": "credit_card",
               "transaction_id": "txn_abc123"}, headers=H_A)
    t("Create payment", r.status_code, 200)
    pid = r.json()["data"]["id"]

    r = c.post(f"{EP}/payments", json={"amount": 199.99,
               "payment_method": "bank_transfer"}, headers=H_A)
    t("Create second payment", r.status_code, 200)

    r = c.get(f"{EP}/payments", headers=H_A)
    t("List payments", r.status_code, 200)
    t("Two payments", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/payments", headers=H_B)
    t("Tenant B no A payments", len(r.json()["data"]), 0)


def test_licenses(c):
    print("\n--- 4. Licenses ---")
    r = c.post(f"{EP}/licenses", json={"license_key": "LIC-PRO-001",
               "license_type": "professional", "max_seats": 25,
               "features": ["api_access", "advanced_reporting", "sso"]},
               headers=H_A)
    t("Create license", r.status_code, 200)
    lid = r.json()["data"]["id"]

    r = c.post(f"{EP}/licenses", json={"license_key": "LIC-STD-001",
               "license_type": "standard", "max_seats": 10}, headers=H_A)
    t("Create second license", r.status_code, 200)

    r = c.get(f"{EP}/licenses", headers=H_A)
    t("List licenses", r.status_code, 200)
    t("Two licenses", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/licenses/{lid}", headers=H_A)
    t("Get license", r.status_code, 200)
    t("License type correct", r.json()["data"]["license_type"], "professional")

    r = c.put(f"{EP}/licenses/{lid}", json={"max_seats": 50}, headers=H_A)
    t("Update license seats", r.status_code, 200)

    r = c.get(f"{EP}/licenses/{lid}", headers=H_A)
    t("Seats updated", r.json()["data"]["max_seats"], 50)

    r = c.get(f"{EP}/licenses", headers=H_B)
    t("Tenant B no A licenses", len(r.json()["data"]), 0)


def test_usage(c):
    print("\n--- 5. Usage Meters ---")
    r = c.post(f"{EP}/usage", json={"meter_name": "api_calls",
               "meter_value": 15000, "unit": "requests"}, headers=H_A)
    t("Record usage", r.status_code, 200)
    uid = r.json()["data"]["id"]

    r = c.post(f"{EP}/usage", json={"meter_name": "storage_gb",
               "meter_value": 45.5, "unit": "GB",
               "overage_rate": 0.10}, headers=H_A)
    t("Record storage usage", r.status_code, 200)

    r = c.get(f"{EP}/usage", headers=H_A)
    t("List usage", r.status_code, 200)
    t("Two usage records", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/usage?meter_name=api_calls", headers=H_A)
    t("Filter by meter name", r.status_code, 200)
    t("One API call record", len(r.json()["data"]), 1)

    r = c.get(f"{EP}/usage", headers=H_B)
    t("Tenant B no A usage", len(r.json()["data"]), 0)


def test_rbac(c):
    print("\n--- 6. RBAC ---")
    r = c.get(f"{EP}/subscription", headers=HV)
    t("Viewer can read subscription", r.status_code, 200)
    r = c.post(f"{EP}/subscription", json={"plan_id": "test"}, headers=HV)
    t("Viewer cannot create subscription", r.status_code, 403)
    r = c.get(f"{EP}/invoices", headers=HV)
    t("Viewer can list invoices", r.status_code, 200)
    r = c.get(f"{EP}/licenses", headers=HV)
    t("Viewer can list licenses", r.status_code, 200)
    r = c.get(f"{EP}/usage", headers=HV)
    t("Viewer can list usage", r.status_code, 200)


def test_negative(c):
    print("\n--- 7. Negative Tests ---")
    r = c.post(f"{EP}/subscription", json={}, headers=H_A)
    t("Create subscription missing plan_id", r.status_code, 400)
    r = c.post(f"{EP}/invoices", json={}, headers=H_A)
    t("Create invoice missing fields", r.status_code, 400)
    r = c.post(f"{EP}/payments", json={}, headers=H_A)
    t("Create payment missing amount", r.status_code, 400)
    r = c.post(f"{EP}/licenses", json={}, headers=H_A)
    t("Create license missing fields", r.status_code, 400)
    r = c.post(f"{EP}/usage", json={}, headers=H_A)
    t("Record usage missing fields", r.status_code, 400)
    r = c.get(f"{EP}/invoices/nonexistent", headers=H_A)
    t("Get non-existent invoice", r.status_code, 404)
    r = c.get(f"{EP}/licenses/nonexistent", headers=H_A)
    t("Get non-existent license", r.status_code, 404)


if __name__ == "__main__":
    print("=" * 60)
    print("P43 SUBSCRIPTION & LICENSING TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        test_subscriptions(c)
        test_invoices(c)
        test_payments(c)
        test_licenses(c)
        test_usage(c)
        test_rbac(c)
        test_negative(c)
    finally:
        c.close()
        stop(proc)
        cleanup()
    print("\n" + "=" * 60)
    print(f"P43 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
