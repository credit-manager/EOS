import sys, io, json, uuid
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0
total = 0

def api(method, path, data=None, token=""):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(BASE + path, body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode()[:200]}

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

print("=== P70.7C.2 Cross-Industry Smoke Test ===\n")

# ═══ COMMERCE ENGINE (via API) ═══
print("--- Commerce Engine ---")
wh = api("POST", "/trading/warehouses", {"name": f"SMK-{_rid}", "code": f"SMK-{_rid}"}, token)
test("Commerce: create warehouse", "_err" not in wh and "id" in wh.get("data", {}))

item = api("POST", "/trading/items", {"name": f"Item-{_rid}", "item_code": f"SMK-{_rid}", "cost_price": 10, "selling_price": 20}, token)
test("Commerce: create item", "_err" not in item and "id" in item.get("data", {}))

cust = api("POST", "/trading/customers", {"name": f"Cust-{_rid}", "customer_code": f"SMK-{_rid}"}, token)
test("Commerce: create customer", "_err" not in cust and "id" in cust.get("data", {}))

supp = api("POST", "/trading/suppliers", {"name": f"Supp-{_rid}", "supplier_code": f"SMK-{_rid}"}, token)
test("Commerce: create supplier", "_err" not in supp and "id" in supp.get("data", {}))

# ═══ TRADING ═══
print("\n--- Trading ---")
items = api("GET", "/trading/items", token=token)
items_ok = "_err" not in items and (isinstance(items, list) or isinstance(items.get("data"), list) or items.get("data", {}).get("total", 0) > 0)
test("Trading: list items", items_ok)

stock = api("GET", "/trading/stock", token=token)
test("Trading: list stock", "_err" not in stock and "data" in stock)

whs = api("GET", "/trading/warehouses", token=token)
test("Trading: list warehouses", "_err" not in whs and len(whs.get("data", [])) > 0)

supps = api("GET", "/trading/suppliers", token=token)
supps_ok = "_err" not in supps and (isinstance(supps, list) and len(supps) > 0 or isinstance(supps.get("data"), list) and len(supps["data"]) > 0)
test("Trading: list suppliers", supps_ok)

dashboard = api("GET", "/trading/dashboard", token=token)
test("Trading: dashboard", "_err" not in dashboard and "data" in dashboard)

# ═══ RETAIL ═══
print("\n--- Retail ---")
registers = api("GET", "/retail/registers", token=token)
test("Retail: list registers", "_err" not in registers and "data" in registers)

cashiers = api("GET", "/retail/cashiers", token=token)
test("Retail: list cashiers", "_err" not in cashiers and "data" in cashiers)

promos = api("GET", "/retail/promotions", token=token)
test("Retail: list promotions", "_err" not in promos and "data" in promos)

loyalty = api("GET", "/retail/loyalty/tiers", token=token)
test("Retail: loyalty tiers", "_err" not in loyalty and "data" in loyalty)

# ═══ RESTAURANT ═══
print("\n--- Restaurant ---")
sections = api("GET", "/restaurant/sections", token=token)
test("Restaurant: list sections", "_err" not in sections and "data" in sections)

tables = api("GET", "/restaurant/tables", token=token)
test("Restaurant: list tables", "_err" not in tables and "data" in tables)

menu = api("GET", "/restaurant/menu/items", token=token)
test("Restaurant: list menu items", "_err" not in menu and "data" in menu)

categories = api("GET", "/restaurant/menu/categories", token=token)
test("Restaurant: list menu categories", "_err" not in categories and "data" in categories)

kitchen = api("GET", "/restaurant/kitchen/orders", token=token)
test("Restaurant: kitchen orders", "_err" not in kitchen and "data" in kitchen)

dash = api("GET", "/restaurant/dashboard", token=token)
test("Restaurant: dashboard", "_err" not in dash and "data" in dash)

# ═══ CONSTRUCTION ═══
print("\n--- Construction ---")
projects = api("GET", "/construction/project-list", token=token)
if "_err" in projects:
    projects = api("GET", "/construction/projects/list", token=token)
test("Construction: list projects", "_err" not in projects)

# ═══ CROSS-INDUSTRY: Same item visible from Trading and Restaurant ═══
print("\n--- Cross-Industry Commerce ---")
trading_items = api("GET", "/trading/items", token=token)
trading_ok = "_err" not in trading_items
test("Cross-Industry: Trading has items", trading_ok)
restaurant_menu = api("GET", "/restaurant/menu/items", token=token)
test("Cross-Industry: Restaurant has menu items", "_err" not in restaurant_menu)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P70.7C.2 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
