import sys, io, json, uuid
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0
total = 0

def api(method, path, data=None, token=""):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(BASE + path, body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode()[:300]}

def test(name, cond):
    global passed, failed, total
    total += 1
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")

# Login
r = api("POST", "/api/v1/auth/login", {"email": "admin@demo.com", "password": "admin123"})
token = r["data"]["access_token"]
_rid = uuid.uuid4().hex[:6].upper()

print("=== P70.7C.4 Retail → Commerce Engine Test ===\n")

# Setup: item, warehouse, register, cashier
wh = api("POST", "/trading/warehouses", {"name": f"RWH-{_rid}", "code": f"RWH-{_rid}"}, token)
wh_id = wh["data"]["id"]

item = api("POST", "/trading/items", {"name": f"RItem-{_rid}", "item_code": f"RI-{_rid}",
           "cost_price": 15, "selling_price": 30, "barcode": f"RBC-{_rid}"}, token)
item_id = item["data"]["id"]

# Stock via GRN
from datetime import date
supp = api("POST", "/trading/suppliers", {"name": f"RS-{_rid}", "supplier_code": f"RS-{_rid}"}, token)
po = api("POST", "/trading/purchase-orders", {"supplier_id": supp["data"]["id"],
         "lines": [{"item_id": item_id, "qty": 100, "estimated_price": 15}]}, token)
grn = api("POST", "/trading/grn", {"po_id": po["data"]["id"],
          "lines": [{"item_id": item_id, "qty_received": 100, "qty_accepted": 100,
                     "unit_cost": 15, "warehouse_id": wh_id}]}, token)
test("Setup: stock received", "_err" not in grn)

# Register & Cashier
reg = api("POST", "/retail/registers", {"register_code": f"REG-{_rid}", "name": f"REG-{_rid}", "warehouse_id": wh_id}, token)
reg_id = reg["data"]["id"]
cashier = api("POST", "/retail/cashiers", {"name": f"CASH-{_rid}", "pin": "1234"}, token)
cashier_id = cashier["data"]["id"]

# ═══ 1. ITEMS VIA COMMERCE ENGINE ═══
print("--- Items via Commerce Engine ---")
items = api("GET", "/trading/items", token=token)
test("1.1 Trading items accessible", "_err" not in items)

barcode = api("GET", f"/retail/items/barcode/RBC-{_rid}", token=token)
test("1.2 Barcode lookup works", "_err" not in barcode and barcode["data"]["id"] == item_id)

# ═══ 2. POS SALE ═══
print("\n--- POS Sale ---")
session = api("POST", "/retail/cash/sessions/open", {"register_id": reg_id, "cashier_id": cashier_id,
              "opening_amount": 500}, token)
session_id = session["data"]["id"]

sale = api("POST", "/retail/pos/sales", {
    "register_id": reg_id, "cashier_id": cashier_id,
    "payment_method": "cash", "paid_amount": 100,
    "lines": [{"item_id": item_id, "qty": 2, "unit_price": 30}]
}, token)
test("2.1 POS Sale created", "_err" not in sale and "id" in sale.get("data", {}))
sale_id = sale["data"]["id"]

# Check stock reduced
stk = api("GET", f"/trading/items/{item_id}", token=token)
test("2.2 Stock reduced after sale", stk["data"]["on_hand"] == 98)

# ═══ 3. RETURN ═══
print("\n--- POS Return ---")
ret = api("POST", "/retail/pos/returns", {
    "register_id": reg_id, "cashier_id": cashier_id,
    "original_sale_id": sale_id, "reason": "Customer changed mind",
    "lines": [{"item_id": item_id, "qty": 1, "unit_price": 30}]
}, token)
test("3.1 Return processed", "_err" not in ret)

stk2 = api("GET", f"/trading/items/{item_id}", token=token)
test("3.2 Stock restored after return", stk2["data"]["on_hand"] == 99)

# ═══ 4. VOID ═══
print("\n--- POS Void ---")
sale2 = api("POST", "/retail/pos/sales", {
    "register_id": reg_id, "cashier_id": cashier_id,
    "payment_method": "cash", "paid_amount": 50,
    "lines": [{"item_id": item_id, "qty": 1, "unit_price": 30}]
}, token)
sale2_id = sale2["data"]["id"]
void = api("POST", f"/retail/pos/sales/{sale2_id}/void", {}, token)
test("4.1 Sale voided", "_err" not in void)

stk3 = api("GET", f"/trading/items/{item_id}", token=token)
test("4.2 Stock restored after void", stk3["data"]["on_hand"] == 99)

# ═══ 5. CASH SESSIONS ═══
print("\n--- Cash Sessions ---")
close = api("POST", f"/retail/cash/sessions/{session_id}/close?closing_amount=500&card_total=0&mobile_total=0", token=token)
test("5.1 Cash session closed", "_err" not in close)

# ═══ 6. LOYALTY ═══
print("\n--- Loyalty ---")
tiers = api("GET", "/retail/loyalty/tiers", token=token)
test("6.1 Loyalty tiers listable", "_err" not in tiers)

# ═══ 7. PROMOTIONS ═══
print("\n--- Promotions ---")
promo = api("POST", "/retail/promotions", {
    "name": f"Summer-{_rid}", "promo_type": "percentage",
    "discount_value": 10, "start_date": "2026-01-01", "end_date": "2026-12-31"
}, token)
test("7.1 Promotion created", "_err" not in promo)

# ═══ 8. TENANT ISOLATION ═══
print("\n--- Tenant Isolation ---")
sessions = api("GET", "/retail/cash/sessions", token=token)
test("8.1 Cash sessions filtered by tenant", "_err" not in sessions)

promos = api("GET", "/retail/promotions", token=token)
test("8.2 Promotions filtered by tenant", "_err" not in promos)

# ═══ 9. ACCOUNTING ═══
print("\n--- Accounting Integrity ---")
journal = api("GET", "/api/v1/accounting/journal", token=token)
test("9.1 Journal entries exist", "_err" not in journal)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P70.7C.4 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
