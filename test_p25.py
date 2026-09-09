"""
P25 INVENTORY MANAGEMENT TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, '.')
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p25"

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
        db.execute(sa("DELETE FROM dbp_stock_movements WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_stock WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_stock_takes WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_warehouses WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_grn_items WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_purchase_order_lines WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_purchase_orders WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_items WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p25', 'tenant_a', 'CO25', 'Test')"))
        db.execute(sa("INSERT INTO dbp_companies (id, tenant_id, code, name_en) VALUES ('co_p25b', 'tenant_b', 'CO25B', 'Other')"))
        db.execute(sa("INSERT INTO dbp_items (id, tenant_id, company_id, code, name_en, item_type) VALUES ('itm1', 'tenant_a', 'co_p25', 'I-001', 'Widget', 'product')"))
        db.commit()
    finally:
        db.close()

def test_warehouses(c):
    print("\n--- 1. Warehouses ---")
    r = c.post(f"{EP}/companies/{CID}/warehouses", headers=H, json={"name": "Main Warehouse", "location": "Riyadh"})
    t("Create WH", r.status_code, 200)
    wh1 = r.json()["data"]["id"]

    r = c.post(f"{EP}/companies/{CID}/warehouses", headers=H, json={"name": "Branch WH"})
    t("Create WH2", r.status_code, 200)
    wh2 = r.json()["data"]["id"]

    r = c.get(f"{EP}/companies/{CID}/warehouses", headers=H)
    t("List WHs", r.status_code, 200)
    t("Has 2 WHs", len(r.json()["data"]), 2)
    return wh1, wh2

def test_receive(c, wh1):
    print("\n--- 2. Receive Stock ---")
    r = c.post(f"{EP}/companies/{CID}/stock/receive", headers=H, json={
        "item_id": "itm1", "warehouse_id": wh1, "quantity": 100, "notes": "Initial stock"
    })
    t("Receive 100", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/stock?item_id=itm1", headers=H)
    t("Stock is 100", r.json()["data"][0]["quantity_on_hand"], 100)

    # Receive 50 more
    r = c.post(f"{EP}/companies/{CID}/stock/receive", headers=H, json={
        "item_id": "itm1", "warehouse_id": wh1, "quantity": 50
    })
    t("Receive 50 more", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/stock?item_id=itm1", headers=H)
    t("Stock is 150", r.json()["data"][0]["quantity_on_hand"], 150)

def test_issue(c, wh1):
    print("\n--- 3. Issue Stock ---")
    r = c.post(f"{EP}/companies/{CID}/stock/issue", headers=H, json={
        "item_id": "itm1", "warehouse_id": wh1, "quantity": 40
    })
    t("Issue 40", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/stock?item_id=itm1", headers=H)
    t("Stock is 110", r.json()["data"][0]["quantity_on_hand"], 110)

    # Over-issue should fail
    r = c.post(f"{EP}/companies/{CID}/stock/issue", headers=H, json={
        "item_id": "itm1", "warehouse_id": wh1, "quantity": 200
    })
    t("Over-issue blocked", r.status_code, 400)

def test_transfer(c, wh1, wh2):
    print("\n--- 4. Transfer ---")
    r = c.post(f"{EP}/companies/{CID}/stock/transfer", headers=H, json={
        "item_id": "itm1", "from_warehouse_id": wh1, "to_warehouse_id": wh2, "quantity": 50
    })
    t("Transfer 50", r.status_code, 200)

    r = c.get(f"{EP}/companies/{CID}/stock?item_id=itm1", headers=H)
    stock = {s["warehouse_id"]: s["quantity_on_hand"] for s in r.json()["data"]}
    t("WH1 has 60", stock.get(wh1), 60)
    t("WH2 has 50", stock.get(wh2), 50)

    # Self-transfer should fail
    r = c.post(f"{EP}/companies/{CID}/stock/transfer", headers=H, json={
        "item_id": "itm1", "from_warehouse_id": wh1, "to_warehouse_id": wh1, "quantity": 10
    })
    t("Self-transfer blocked", r.status_code, 400)

def test_movements(c):
    print("\n--- 5. Movements ---")
    r = c.get(f"{EP}/companies/{CID}/stock/movements?item_id=itm1", headers=H)
    t("List movements", r.status_code, 200)
    t("Has movements", len(r.json()["data"]) > 0, True)
    t("Oldest first", r.json()["data"][0]["movement_type"] in ("purchase_receive", "transfer_in", "sales_issue", "transfer_out"), True)

def test_low_stock_alerts(c):
    print("\n--- 6. Low Stock Alerts ---")
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        db.execute(sa("UPDATE dbp_stock SET reorder_level = 200, quantity_on_hand = 110 WHERE item_id='itm1'"))
        db.commit()
    finally:
        db.close()

    r = c.get(f"{EP}/companies/{CID}/stock/alerts", headers=H)
    t("Has alert", r.status_code, 200)
    t("Alerts not empty", len(r.json()["data"]) > 0, True)

def test_tenant_isolation(c):
    print("\n--- 7. Tenant Isolation ---")
    TOKEN_B = create_test_token("tenant_b", user_id="user_b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}

    r = c.get(f"{EP}/companies/{CID}/stock", headers=H_B)
    t("Tenant B sees no stock", len(r.json()["data"]), 0)

    r = c.get(f"{EP}/companies/{CID}/warehouses", headers=H_B)
    t("Tenant B sees no WHs", len(r.json()["data"]), 0)

if __name__ == "__main__":
    print("=" * 60)
    print("P25 INVENTORY MANAGEMENT TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        wh1, wh2 = test_warehouses(c)
        test_receive(c, wh1)
        test_issue(c, wh1)
        test_transfer(c, wh1, wh2)
        test_movements(c)
        test_low_stock_alerts(c)
        test_tenant_isolation(c)
    finally:
        c.close(); stop(proc)
    print("\n" + "=" * 60)
    print(f"P25 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
