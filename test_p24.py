"""
P24 PROCUREMENT & PURCHASE ORDERS TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p24"

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
        db.execute(sa("DELETE FROM dbp_grn_items WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_purchase_order_lines WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_purchase_orders WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_purchase_requests WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_suppliers WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_items WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_items WHERE tenant_id='tenant_b'"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id='tenant_a'"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id='tenant_b'"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p24', 'tenant_a', 'CO_P24', 'Test Co')"))
        db.commit()
    finally:
        db.close()

def test_items(c):
    print("\n--- 1. Items ---")
    r = c.post(f"{EP}/companies/{CID}/items", headers=H, json={"code": "ITM-001", "name_en": "Laptop", "item_type": "product", "category": "IT"})
    t("Create item", r.status_code, 200)
    item_id = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/items", headers=H)
    t("List items", r.status_code, 200)
    t("Has 1 item", len(r.json()["data"]), 1)
    return item_id

def test_suppliers(c):
    print("\n--- 2. Suppliers ---")
    r = c.post(f"{EP}/companies/{CID}/suppliers", headers=H, json={"name": "TechSupplier Co.", "email": "info@tech.com", "phone": "+966500000"})
    t("Create supplier", r.status_code, 200)
    sid = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/suppliers", headers=H)
    t("List suppliers", r.status_code, 200)
    t("Has 1 supplier", len(r.json()["data"]), 1)
    return sid

def test_purchase_requests(c):
    print("\n--- 3. Purchase Requests ---")
    r = c.post(f"{EP}/companies/{CID}/purchase-requests", headers=H, json={
        "request_date": "2025-06-15", "description": "IT equipment", "priority": "high"
    })
    t("Create PR", r.status_code, 200)
    prid = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/purchase-requests", headers=H)
    t("List PRs", r.status_code, 200)
    t("Has PR", len(r.json()["data"]) >= 1, True)
    return prid

def test_purchase_orders(c, supplier_id, item_id):
    print("\n--- 4. Purchase Orders ---")
    r = c.post(f"{EP}/companies/{CID}/purchase-orders", headers=H, json={
        "supplier_id": supplier_id, "order_date": "2025-06-15",
        "lines": [{"item_id": item_id, "description": "5x Laptops", "quantity": 5, "unit_price": 3000, "tax_rate": 15}]
    })
    t("Create PO", r.status_code, 200)
    po_id = r.json()["data"]["id"]

    # Get PO details
    r = c.get(f"{EP}/purchase-orders/{po_id}", headers=H)
    t("Get PO", r.status_code, 200)
    t("PO has line", len(r.json()["data"]["lines"]), 1)
    t("PO total 15000", r.json()["data"]["total_amount"], 15000)

    # Submit then approve
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    db.execute(sa("UPDATE dbp_purchase_orders SET status='submitted' WHERE id = :id"), {"id": po_id})
    db.commit(); db.close()

    r = c.post(f"{EP}/purchase-orders/{po_id}/approve", headers=H)
    t("Approve PO", r.status_code, 200)

    # Re-approve should fail
    r = c.post(f"{EP}/purchase-orders/{po_id}/approve", headers=H)
    t("Re-approve blocked", r.status_code, 400)
    return po_id

def test_grn(c, po_id):
    print("\n--- 5. Goods Receiving ---")
    r = c.get(f"{EP}/purchase-orders/{po_id}", headers=H)
    line_id = r.json()["data"]["lines"][0]["id"]

    # Receive 3
    r = c.post(f"{EP}/purchase-orders/{po_id}/receive", headers=H, json={
        "line_id": line_id, "quantity": 3, "received_date": "2025-06-20"
    })
    t("Receive 3", r.status_code, 200)
    t("Status partially", r.json()["data"]["new_status"], "partially_received")

    # Receive 2 more
    r = c.post(f"{EP}/purchase-orders/{po_id}/receive", headers=H, json={
        "line_id": line_id, "quantity": 2, "received_date": "2025-06-22"
    })
    t("Receive 2", r.status_code, 200)
    t("Status received", r.json()["data"]["new_status"], "received")

    # Over-receive should fail
    r = c.post(f"{EP}/purchase-orders/{po_id}/receive", headers=H, json={
        "line_id": line_id, "quantity": 1, "received_date": "2025-06-23"
    })
    t("Over-receive blocked", r.status_code, 400)

def test_tenant_isolation(c):
    print("\n--- 6. Tenant Isolation ---")
    # Create a different tenant
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_other', 'tenant_b', 'CO_B', 'Other')"))
        db.commit()
    except:
        db.rollback()
    finally:
        db.close()

    TOKEN_B = create_test_token("tenant_b", user_id="user_b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}

    # tenant_b should NOT see tenant_a items
    r = c.get(f"{EP}/companies/{CID}/items", headers=H_B)
    t("Tenant B empty items", len(r.json()["data"]), 0)

    # tenant_b should see its own
    r = c.post(f"{EP}/companies/co_other/items", headers=H_B, json={"code": "X1", "name_en": "Widget", "item_type": "product"})
    t("Tenant B create item", r.status_code, 200)

    r = c.get(f"{EP}/companies/co_other/items", headers=H_B)
    t("Tenant B has 1", len(r.json()["data"]), 1)

if __name__ == "__main__":
    print("=" * 60)
    print("P24 PROCUREMENT & PURCHASE ORDERS TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        item_id = test_items(c)
        supplier_id = test_suppliers(c)
        test_purchase_requests(c)
        po_id = test_purchase_orders(c, supplier_id, item_id)
        test_grn(c, po_id)
        test_tenant_isolation(c)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P24 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
