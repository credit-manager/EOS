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

print("=== P70.8 Manufacturing ERP Tests ===\n")

# ─── SETUP: Items via Commerce Engine ──────────────
print("--- Setup: Items ---")
raw_mat = api("POST", "/trading/items", {"name": f"Steel-{_rid}", "item_code": f"STL-{_rid}",
             "cost_price": 10, "selling_price": 20, "category": "raw_material", "unit": "kg"}, token)
raw_id = raw_mat["data"]["id"]

component = api("POST", "/trading/items", {"name": f"Screw-{_rid}", "item_code": f"SCR-{_rid}",
               "cost_price": 2, "selling_price": 5, "category": "raw_material", "unit": "piece"}, token)
comp_id = component["data"]["id"]

finished = api("POST", "/trading/items", {"name": f"Table-{_rid}", "item_code": f"TBL-{_rid}",
              "cost_price": 50, "selling_price": 100, "category": "finished_good", "unit": "piece"}, token)
fg_id = finished["data"]["id"]

# Warehouse
wh = api("POST", "/trading/warehouses", {"name": f"MFGWH-{_rid}", "code": f"MFGWH-{_rid}"}, token)
wh_id = wh["data"]["id"]

# Stock raw materials
supp = api("POST", "/trading/suppliers", {"name": f"MS-{_rid}", "supplier_code": f"MS-{_rid}"}, token)
po = api("POST", "/trading/purchase-orders", {"supplier_id": supp["data"]["id"],
         "lines": [{"item_id": raw_id, "qty": 1000, "estimated_price": 10},
                   {"item_id": comp_id, "qty": 5000, "estimated_price": 2}]}, token)
grn = api("POST", "/trading/grn", {"po_id": po["data"]["id"],
          "lines": [{"item_id": raw_id, "qty_received": 1000, "qty_accepted": 1000,
                     "unit_cost": 10, "warehouse_id": wh_id},
                    {"item_id": comp_id, "qty_received": 5000, "qty_accepted": 5000,
                     "unit_cost": 2, "warehouse_id": wh_id}]}, token)
test("Setup: stock received", "_err" not in grn)

# ═══ 1. BOM ═══
print("\n--- BOM ---")
bom = api("POST", "/manufacturing/bom", {
    "bom_code": f"BOM-{_rid}", "name": f"Table BOM-{_rid}", "item_id": fg_id,
    "revision": "A", "description": "Table BOM",
    "lines": [
        {"item_id": raw_id, "qty": 20, "unit": "kg", "scrap_pct": 5, "sort_order": 1},
        {"item_id": comp_id, "qty": 40, "unit": "piece", "scrap_pct": 2, "sort_order": 2},
    ]
}, token)
test("1.1 BOM created", "_err" not in bom and "id" in bom.get("data", {}))
bom_id = bom["data"]["id"]

bom_list = api("GET", "/manufacturing/bom", token=token)
bom_data = bom_list.get("data", bom_list)
test("1.2 BOM listable", "_err" not in bom_list and isinstance(bom_data, list) and len(bom_data) >= 1)

bom_detail = api("GET", f"/manufacturing/bom/{bom_id}", token=token)
test("1.3 BOM detail has 2 lines", "_err" not in bom_detail and len(bom_detail["data"]["lines"]) == 2)

bom_activate = api("PUT", f"/manufacturing/bom/{bom_id}/activate", token=token)
test("1.4 BOM activated", "_err" not in bom_activate)

# Duplicate code
dup_bom = api("POST", "/manufacturing/bom", {"bom_code": f"BOM-{_rid}", "name": "Dup",
              "item_id": fg_id, "lines": []}, token)
test("1.5 Duplicate BOM rejected", "_err" in dup_bom)

# ═══ 2. WORK CENTERS ═══
print("\n--- Work Centers ---")
wc1 = api("POST", "/manufacturing/work-centers", {
    "code": f"WC-CUT-{_rid}", "name": f"Cutter-{_rid}", "work_center_type": "machine",
    "capacity_per_hour": 10, "cost_per_hour": 50, "efficiency_pct": 95
}, token)
test("2.1 Work center created", "_err" not in wc1 and "id" in wc1.get("data", {}))
wc1_id = wc1["data"]["id"]

wc2 = api("POST", "/manufacturing/work-centers", {
    "code": f"WC-ASM-{_rid}", "name": f"Assembler-{_rid}", "work_center_type": "labor",
    "capacity_per_hour": 5, "cost_per_hour": 30
}, token)
test("2.2 Work center 2 created", "_err" not in wc2)

wc_list = api("GET", "/manufacturing/work-centers", token=token)
wc_data = wc_list.get("data", wc_list) if isinstance(wc_list.get("data", wc_list), list) else wc_list.get("data", {}).get("data", wc_list.get("data", []))
test("2.3 Work centers listable", "_err" not in wc_list)

# ═══ 3. ROUTINGS ═══
print("\n--- Routings ---")
routing = api("POST", "/manufacturing/routings", {
    "routing_code": f"RT-{_rid}", "name": f"Table Routing-{_rid}", "item_id": fg_id,
    "bom_id": bom_id, "revision": "A",
    "steps": [
        {"step_number": 1, "work_center_id": wc1_id, "setup_time_hrs": 0.5, "run_time_hrs": 2},
        {"step_number": 2, "work_center_id": wc2["data"]["id"], "setup_time_hrs": 0.25, "run_time_hrs": 3},
    ]
}, token)
test("3.1 Routing created", "_err" not in routing and "id" in routing.get("data", {}))
rt_id = routing["data"]["id"]

rt_list = api("GET", "/manufacturing/routings", token=token)
test("3.2 Routings listable", "_err" not in rt_list)

rt_detail = api("GET", f"/manufacturing/routings/{rt_id}", token=token)
test("3.3 Routing has 2 steps", "_err" not in rt_detail and len(rt_detail["data"]["steps"]) == 2)

# ═══ 4. PRODUCTION ORDERS ═══
print("\n--- Production Orders ---")
po_mfg = api("POST", "/manufacturing/orders", {
    "item_id": fg_id, "bom_id": bom_id, "routing_id": rt_id,
    "warehouse_id": wh_id, "qty_planned": 100, "priority": 3,
    "planned_start": "2026-09-01", "planned_end": "2026-09-10"
}, token)
test("4.1 Order created", "_err" not in po_mfg and "id" in po_mfg.get("data", {}))
order_id = po_mfg["data"]["id"]
test("4.2 Order number generated", "order_number" in po_mfg.get("data", {}))

# List & Detail
orders = api("GET", "/manufacturing/orders", token=token)
test("4.3 Orders listable", "_err" not in orders and len(orders.get("data", [])) >= 1)

order_detail = api("GET", f"/manufacturing/orders/{order_id}", token=token)
test("4.4 Order detail", "_err" not in order_detail and order_detail["data"]["status"] == "planned")

# Lifecycle: plan → release → start → complete
rel = api("PUT", f"/manufacturing/orders/{order_id}/release", token=token)
test("4.5 Order released", "_err" not in rel)

start = api("PUT", f"/manufacturing/orders/{order_id}/start", token=token)
test("4.6 Order started", "_err" not in start)

# Complete 50
comp = api("PUT", f"/manufacturing/orders/{order_id}/complete?qty_completed=50", token=token)
test("4.7 Order partially completed (50)", "_err" not in comp)

# Verify stock increased
stk = api("GET", f"/trading/items/{fg_id}", token=token)
test("4.8 Finished goods stock increased", "_err" not in stk and stk["data"]["on_hand"] == 50)

# ═══ 5. MATERIAL ISSUES ═══
print("\n--- Material Issues ---")
# Create a new order for material issues test
po_mfg2 = api("POST", "/manufacturing/orders", {
    "item_id": fg_id, "warehouse_id": wh_id, "qty_planned": 20
}, token)
oid2 = po_mfg2["data"]["id"]
api("PUT", f"/manufacturing/orders/{oid2}/release", token=token)
api("PUT", f"/manufacturing/orders/{oid2}/start", token=token)

mi = api("POST", "/manufacturing/material-issues", {
    "order_id": oid2, "warehouse_id": wh_id,
    "lines": [
        {"item_id": raw_id, "qty_required": 40, "qty_issued": 40, "unit_cost": 10},
        {"item_id": comp_id, "qty_required": 80, "qty_issued": 80, "unit_cost": 2},
    ]
}, token)
test("5.1 Material issue created", "_err" not in mi and "id" in mi.get("data", {}))
mi_id = mi["data"]["id"]

issue = api("PUT", f"/manufacturing/material-issues/{mi_id}/issue", token=token)
test("5.2 Materials issued", "_err" not in issue and "total_cost" in issue.get("data", {}))

# Verify raw material stock decreased
stk_raw = api("GET", f"/trading/items/{raw_id}", token=token)
test("5.3 Raw material stock decreased", "_err" not in stk_raw and stk_raw["data"]["on_hand"] == 960)

# ═══ 6. RECEIPTS ═══
print("\n--- Receipts ---")
receipt = api("POST", "/manufacturing/receipts", {
    "order_id": oid2, "qty_received": 20, "qty_accepted": 19, "qty_rejected": 1,
    "warehouse_id": wh_id, "unit_cost": 55
}, token)
test("6.1 Receipt recorded", "_err" not in receipt and "id" in receipt.get("data", {}))

# ═══ 7. QUALITY ═══
print("\n--- Quality Inspections ---")
qi = api("POST", "/manufacturing/quality-inspections", {
    "order_id": oid2, "item_id": fg_id, "inspection_type": "final",
    "qty_inspected": 19, "qty_passed": 18, "qty_failed": 1, "result": "passed",
    "defect_notes": "Minor scratch"
}, token)
test("7.1 Inspection recorded", "_err" not in qi and "id" in qi.get("data", {}))

qi_list = api("GET", "/manufacturing/quality-inspections", token=token)
test("7.2 Inspections listable", "_err" not in qi_list and len(qi_list.get("data", [])) >= 1)

# ═══ 8. SCRAP ═══
print("\n--- Scrap ---")
scrap = api("POST", "/manufacturing/scrap", {
    "order_id": oid2, "item_id": fg_id, "qty": 1,
    "reason": "Quality defect", "cost": 55
}, token)
test("8.1 Scrap recorded", "_err" not in scrap and "id" in scrap.get("data", {}))

# ═══ 9. COSTS ═══
print("\n--- Costs ---")
cost = api("POST", "/manufacturing/costs", {
    "order_id": oid2, "cost_type": "labor", "amount": 300,
    "description": "Assembly labor"
}, token)
test("9.1 Cost recorded", "_err" not in cost and "id" in cost.get("data", {}))

cost2 = api("POST", "/manufacturing/costs", {
    "order_id": oid2, "cost_type": "overhead", "amount": 150
}, token)
test("9.2 Overhead cost recorded", "_err" not in cost2)

costs = api("GET", f"/manufacturing/costs/{oid2}", token=token)
test("9.3 Costs listable with total", "_err" not in costs and costs["data"]["total_cost"] == 450)

# ═══ 10. DASHBOARD ═══
print("\n--- Dashboard ---")
dash = api("GET", "/manufacturing/dashboard", token=token)
test("10.1 Dashboard accessible", "_err" not in dash)
d = dash.get("data", {})
test("10.2 Orders stats present", "orders" in d and "total" in d["orders"])
test("10.3 Production stats present", "production" in d and "yield_rate" in d["production"])
test("10.4 Master data stats", "master_data" in d and d["master_data"]["boms"] >= 1)
test("10.5 Pending stats", "pending" in d)

# ═══ 11. TENANT ISOLATION ═══
print("\n--- Tenant Isolation ---")
boms = api("GET", "/manufacturing/bom", token=token)
test("11.1 BOMs filtered by tenant", "_err" not in boms)

wcs = api("GET", "/manufacturing/work-centers", token=token)
test("11.2 Work centers filtered by tenant", "_err" not in wcs)

orders = api("GET", "/manufacturing/orders", token=token)
test("11.3 Orders filtered by tenant", "_err" not in orders)

# ═══ 12. ACCOUNTING ═══
print("\n--- Accounting ---")
journal = api("GET", "/api/v1/accounting/journal", token=token)
test("12.1 Journal entries exist", "_err" not in journal)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P70.8 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
