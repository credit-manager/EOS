"""
P72.2 Core ↔ Commerce Integration Tests
=========================================
Tests the full integration between Commerce Engine and Core Accounting.
"""
import io
import json
import sys
import uuid

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

r = api("POST", "/api/v1/auth/login", {"email": "admin@demo.com", "password": "admin123"})
token = r["data"]["access_token"]
_rid = uuid.uuid4().hex[:6].upper()

print("=== P72.2 Core <-> Commerce Integration Tests ===\n")

# ═══ 1. COMMERCE ENGINE: Items via Trading ═══
print("--- 1. Commerce Engine Items & Stock ---")

item = api("POST", "/trading/items", {
    "name": f"Integration Item {_rid}",
    "unit": "pcs", "category": "Test", "selling_price": 100, "cost_price": 60
}, token)
test("1.1 Item created via Trading API", "_err" not in item and "id" in item.get("data", {}))
item_id = item["data"]["id"]

stock_list = api("GET", "/trading/stock", token=token)
test("1.2 Stock list accessible via Trading", "_err" not in stock_list)

# ═══ 2. CROSS-INDUSTRY ITEM QUERIES ═══
print("\n--- 2. Cross-Industry Item Visibility ---")

rest_items = api("GET", "/restaurant/menu/items", token=token)
test("2.1 Restaurant menu items queryable", "_err" not in rest_items and "data" in rest_items)

mfg_items = api("GET", "/manufacturing/work-centers", token=token)
test("2.2 Manufacturing work centers queryable", "_err" not in mfg_items)

trading_items = api("GET", "/trading/items", token=token)
has_item = any(i.get("id") == item_id for i in trading_items.get("data", []))
test("2.3 New item appears in Trading items list", has_item)

# ═══ 3. CUSTOMER/Supplier Cross-Industry ═══
print("\n--- 3. Cross-Industry Customer/Supplier ---")

customer = api("POST", "/trading/customers", {
    "name": f"INT Customer {_rid}", "email": f"int{_rid}@test.com",
    "phone": "123456", "address": "Test Address"
}, token)
test("3.1 Customer created via Trading", "_err" not in customer and "id" in customer.get("data", {}))
cust_id = customer["data"]["id"]

cust_read = api("GET", f"/trading/customers/{cust_id}", token=token)
test("3.2 Customer readable via Trading", "_err" not in cust_read)

supplier = api("POST", "/trading/suppliers", {
    "name": f"INT Supplier {_rid}", "email": f"sup{_rid}@test.com",
    "phone": "555555", "address": "Supplier Address"
}, token)
test("3.3 Supplier created via Trading", "_err" not in supplier and "id" in supplier.get("data", {}))

# ═══ 4. TRADING SALES ORDER FLOW ═══
print("\n--- 4. Trading Sales Order Flow ---")

order = api("POST", "/trading/sales-orders", {
    "customer_id": cust_id,
    "lines": [{"item_id": item_id, "qty": 10, "unit_price": 100}]
}, token)
test("4.1 Sales order created", "_err" not in order and "id" in order.get("data", {}))
order_id = order["data"]["id"]

# ═══ 5. RETAIL POS FLOW ═══
print("\n--- 5. Retail POS Integration ---")

regs = api("GET", "/retail/registers", token=token)
reg_wh_map = {reg["warehouse_id"]: reg["id"] for reg in regs.get("data", [])}

stock = api("GET", "/trading/stock", token=token)
reg_id = ""
existing_item_id = item_id
for s in stock.get("data", []):
    if s.get("warehouse_id") in reg_wh_map:
        reg_id = reg_wh_map[s["warehouse_id"]]
        existing_item_id = s["item_id"]
        break

cashiers = api("GET", "/retail/cashiers", token=token)
cashier_id = cashiers["data"][0]["id"] if cashiers.get("data") else ""

sale = api("POST", "/retail/pos/sales", {
    "register_id": reg_id,
    "cashier_id": cashier_id,
    "lines": [{"item_id": existing_item_id, "qty": 1, "unit_price": 10}],
    "payment_method": "cash", "paid_amount": 15
}, token)
test("5.1 POS sale created", "_err" not in sale and "id" in sale.get("data", {}))

# ═══ 6. RESTAURANT ORDER FLOW ═══
print("\n--- 6. Restaurant Order Integration ---")

menu_items = api("GET", "/restaurant/menu/items", token=token)
menu_item = menu_items["data"][0]["id"] if menu_items.get("data") else item_id

rest_order = api("POST", "/restaurant/orders", {
    "order_type": "dine_in",
    "lines": [{"menu_item_id": menu_item, "qty": 1, "unit_price": 100}]
}, token)
test("6.1 Restaurant order created", "_err" not in rest_order and "id" in rest_order.get("data", {}))

# ═══ 7. MANUFACTURING ORDER FLOW ═══
print("\n--- 7. Manufacturing Integration ---")

mfg_order = api("POST", "/manufacturing/orders", {
    "item_id": item_id, "qty_planned": 10, "warehouse_id": "WH-001",
    "priority": 5
}, token)
test("7.1 Manufacturing order created", "_err" not in mfg_order and "id" in mfg_order.get("data", {}))

# ═══ 8. ACCOUNTING JOURNAL ENTRIES ═══
print("\n--- 8. Accounting Integration ---")

import base64

payload = token.split('.')[1]
if len(payload) % 4: payload += '=' * (4 - len(payload) % 4)
decoded = json.loads(base64.urlsafe_b64decode(payload))
tenant_id = decoded['tenant_id']

import psycopg2

conn = psycopg2.connect('postgresql://eos:0100@127.0.0.1:5432/eos_main')
cur = conn.cursor()
cur.execute("SELECT id FROM dbp_companies WHERE tenant_id=%s LIMIT 1", (tenant_id,))
comp_row = cur.fetchone()
comp_id = comp_row[0] if comp_row else ""
conn.close()

journal = api("POST", f"/api/v1/dynamic/companies/{comp_id}/journal-entries", {
    "entry_date": "2026-08-28", "entry_type": "standard",
    "description": f"Integration test {_rid}",
}, token)
test("8.1 Journal entry posted via Accounting", "_err" not in journal)

# ═══ 9. ANALYTICS CROSS-INDUSTRY ═══
print("\n--- 9. Analytics Cross-Industry ---")

overview = api("GET", "/analytics/overview", token=token)
test("9.1 Analytics overview accessible", "_err" not in overview)
has_industries = overview.get("data", {}).get("industries", {})
test("9.2 All 6 industries in analytics", len(has_industries) == 6)

# ═══ 10. NOTIFICATION INTEGRATION ═══
print("\n--- 10. Notification Integration ---")

fire = api("POST", "/notifications/events/fire", {
    "event_type": "order.confirmed",
    "source_module": "trading",
    "source_id": order_id,
    "payload": {"order_number": f"SO-{_rid}", "total": 1000}
}, token)
test("10.1 Event fired successfully", "_err" not in fire and "event_id" in fire.get("data", {}))

# ═══ 11. APPROVAL INTEGRATION ═══
print("\n--- 11. Approval Integration ---")

chain = api("POST", "/approvals/chains", {
    "chain_name": f"Sales Approval-{_rid}",
    "source_module": "trading",
    "steps": [{"step_order": 1, "step_name": "Manager", "approver_type": "user"}]
}, token)
test("11.1 Approval chain created for trading", "_err" not in chain)

# ═══ 12. DOCUMENT INTEGRATION ═══
print("\n--- 12. Document Integration ---")

folder = api("POST", "/docs/folders", {
    "folder_name": f"Sales Orders-{_rid}",
    "source_module": "trading"
}, token)
test("12.1 Document folder for trading", "_err" not in folder)

doc = api("POST", "/docs/files", {
    "file_name": f"SO-{_rid}.pdf",
    "folder_id": folder["data"]["id"],
    "mime_type": "application/pdf",
    "file_size": 50000,
    "source_module": "trading",
    "source_id": order_id
}, token)
test("12.2 Document linked to order", "_err" not in doc)

# ═══ 13. CUSTOMIZATION INTEGRATION ═══
print("\n--- 13. Customization Integration ---")

field = api("POST", "/custom/fields", {
    "entity_type": "trading_order",
    "field_code": f"priority_{_rid}",
    "field_label": "Priority",
    "field_type": "select",
    "enum_values": "Low,Medium,High,Critical"
}, token)
test("13.1 Custom field on trading orders", "_err" not in field)

# ═══ 14. TRADING DASHBOARD ═══
print("\n--- 14. Trading Dashboard ---")

dash = api("GET", "/trading/dashboard", token=token)
test("14.1 Trading dashboard accessible", "_err" not in dash)
test("14.2 Dashboard has stock data", "stock" in dash.get("data", {}))

# ═══ 15. RETAIL DASHBOARD ═══
print("\n--- 15. Retail Dashboard ---")

ret_dash = api("GET", "/retail/dashboard", token=token)
test("15.1 Retail dashboard accessible", "_err" not in ret_dash)

# ═══ 16. RESTAURANT DASHBOARD ═══
print("\n--- 16. Restaurant Dashboard ---")

rest_dash = api("GET", "/restaurant/dashboard", token=token)
test("16.1 Restaurant dashboard accessible", "_err" not in rest_dash)

# ═══ 17. MANUFACTURING DASHBOARD ═══
print("\n--- 17. Manufacturing Dashboard ---")

mfg_dash = api("GET", "/manufacturing/dashboard", token=token)
test("17.1 Manufacturing dashboard accessible", "_err" not in mfg_dash)

# ═══ 18. SERVICES DASHBOARD ═══
print("\n--- 18. Services Dashboard ---")

svc_dash = api("GET", "/services/dashboard", token=token)
test("18.1 Services dashboard accessible", "_err" not in svc_dash)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P72.2 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
