"""
P26 SALES & INVOICING TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p26"

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
        for t_name in ("dbp_sales_invoice_lines", "dbp_sales_invoices",
                       "dbp_sales_order_lines", "dbp_sales_orders",
                       "dbp_sales_quotation_lines", "dbp_sales_quotations",
                       "dbp_customers"):
            db.execute(sa(f"DELETE FROM {t_name} WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id='tenant_a'"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p26', 'tenant_a', 'CO26', 'Test')"))
        db.commit()
    finally:
        db.close()

def test_customers(c):
    print("\n--- 1. Customers ---")
    r = c.post(f"{EP}/companies/{CID}/customers", headers=H, json={"name": "Customer A", "email": "a@test.com", "credit_limit": 50000})
    t("Create customer", r.status_code, 200)
    cid = r.json()["data"]["id"]
    r = c.get(f"{EP}/companies/{CID}/customers", headers=H)
    t("List customers", r.status_code, 200)
    t("Has 1 customer", len(r.json()["data"]), 1)
    return cid

def test_quotations(c, cust_id):
    print("\n--- 2. Quotations ---")
    r = c.post(f"{EP}/companies/{CID}/quotations", headers=H, json={
        "customer_id": cust_id, "quote_date": "2025-06-15",
        "lines": [{"description": "Service A", "quantity": 10, "unit_price": 100, "tax_rate": 15}]
    })
    t("Create quote", r.status_code, 200)
    qid = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/quotations", headers=H)
    t("List quotes", r.status_code, 200)
    t("Has 1 quote", len(r.json()["data"]), 1)

    # Convert to order
    r = c.post(f"{EP}/quotations/{qid}/convert", headers=H)
    t("Convert quote", r.status_code, 200)
    oid = r.json()["data"]["order_id"]

    # Re-convert should fail
    r = c.post(f"{EP}/quotations/{qid}/convert", headers=H)
    t("Re-convert blocked", r.status_code, 400)
    return oid

def test_sales_orders(c, cust_id, so_id):
    print("\n--- 3. Sales Orders ---")
    r = c.post(f"{EP}/companies/{CID}/sales-orders", headers=H, json={
        "customer_id": cust_id, "order_date": "2025-06-16",
        "lines": [{"description": "Product X", "quantity": 5, "unit_price": 200}]
    })
    t("Create SO", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/sales-orders", headers=H)
    t("List SOs", r.status_code, 200)
    t("Has 2 SOs", len(r.json()["data"]), 2)

    r = c.get(f"{EP}/sales-orders/{so_id}", headers=H)
    t("Get SO detail", r.status_code, 200)
    t("SO has lines", len(r.json()["data"]["lines"]) > 0, True)

def test_invoices(c, cust_id):
    print("\n--- 4. Invoices ---")
    r = c.post(f"{EP}/companies/{CID}/invoices", headers=H, json={
        "customer_id": cust_id, "invoice_date": "2025-06-20",
        "lines": [{"description": "Service B", "quantity": 20, "unit_price": 50, "tax_rate": 15}],
        "due_date": "2025-07-20"
    })
    t("Create invoice", r.status_code, 200)
    iid = r.json()["data"]["id"]

    r = c.get(f"{EP}/invoices/{iid}", headers=H)
    t("Get invoice", r.status_code, 200)
    t("Invoice total 1000", r.json()["data"]["total_amount"], 1000)
    t("Invoice paid 0", r.json()["data"]["paid_amount"], 0)

    # Record partial payment (total=1000+150tax=1150)
    r = c.post(f"{EP}/invoices/{iid}/payments", headers=H, json={"amount": 500, "payment_date": "2025-06-25"})
    t("Partial payment", r.status_code, 200)
    t("Status partial", r.json()["data"]["status"], "partial")

    # Record remaining (1150 - 500 = 650)
    r = c.post(f"{EP}/invoices/{iid}/payments", headers=H, json={"amount": 650, "payment_date": "2025-06-28"})
    t("Full payment", r.status_code, 200)
    t("Status paid", r.json()["data"]["status"], "paid")

    # Over-payment should fail
    r = c.post(f"{EP}/invoices/{iid}/payments", headers=H, json={"amount": 1})
    t("Over-payment blocked", r.status_code, 400)

    r = c.get(f"{EP}/companies/{CID}/invoices", headers=H)
    t("List invoices", r.status_code, 200)
    t("Has 1 invoice", len(r.json()["data"]), 1)

def test_tenant_isolation(c):
    print("\n--- 5. Tenant Isolation ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/companies/{CID}/customers", headers=H_B)
    t("Tenant B no customers", len(r.json()["data"]), 0)
    r = c.get(f"{EP}/companies/{CID}/invoices", headers=H_B)
    t("Tenant B no invoices", len(r.json()["data"]), 0)

if __name__ == "__main__":
    print("=" * 60)
    print("P26 SALES & INVOICING TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        cust_id = test_customers(c)
        so_id = test_quotations(c, cust_id)
        test_sales_orders(c, cust_id, so_id)
        test_invoices(c, cust_id)
        test_tenant_isolation(c)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P26 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
