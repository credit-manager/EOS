"""
P73.17-20 SECURITY, TENANT ISOLATION, ACCOUNTING, CROSS-INDUSTRY E2E
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

print(f"=== P73.17-20 SECURITY & E2E ({_rid}) ===\n")

# ═══ P73.17 TENANT ISOLATION ═══
print("--- P73.17 Tenant Isolation ---")

items = api("GET", "/trading/items", token=token)
if items.get("data"):
    tenants = {i.get("tenant_id") for i in items["data"]}
    test("P73.17 Items single-tenant", len(tenants) == 1)

customers = api("GET", "/trading/customers", token=token)
if customers.get("data"):
    tenants = {c.get("tenant_id") for c in customers["data"]}
    test("P73.17 Customers single-tenant", len(tenants) == 1)

suppliers = api("GET", "/trading/suppliers", token=token)
if suppliers.get("data"):
    tenants = {s.get("tenant_id") for s in suppliers["data"]}
    test("P73.17 Suppliers single-tenant", len(tenants) == 1)

# Stock isolation
stock = api("GET", "/trading/stock", token=token)
if stock.get("data"):
    tenants = {s.get("tenant_id", "unknown") for s in stock["data"]}
    test("P73.17 Stock single-tenant", len(tenants) <= 1)

# ═══ P73.18 ACCOUNTING E2E ═══
print("\n--- P73.18 Accounting E2E ---")

import base64

import psycopg2

payload = token.split('.')[1]
if len(payload) % 4: payload += '=' * (4 - len(payload) % 4)
decoded = json.loads(base64.urlsafe_b64decode(payload))
tenant_id = decoded['tenant_id']

conn = psycopg2.connect('postgresql://eos:0100@127.0.0.1:5432/eos_main')
cur = conn.cursor()
cur.execute("SELECT id FROM dbp_companies WHERE tenant_id=%s LIMIT 1", (tenant_id,))
comp_id = cur.fetchone()[0]
conn.close()

# Create JE
je = api("POST", f"/api/v1/dynamic/companies/{comp_id}/journal-entries", {
    "entry_date": "2026-08-28", "entry_type": "standard",
    "description": f"Production test {_rid}"
}, token)
test("P73.18 Journal entry created", "_err" not in je)

# List JEs
je_list = api("GET", f"/api/v1/dynamic/companies/{comp_id}/journal-entries", token=token)
test("P73.18 Journal entries listed", "_err" not in je_list and "data" in je_list)

# Accounts
accounts = api("GET", f"/api/v1/dynamic/companies/{comp_id}/accounts", token=token)
test("P73.18 Chart of accounts accessible", "_err" not in accounts)

# ═══ P73.19 CROSS-INDUSTRY E2E ═══
print("\n--- P73.19 Cross-Industry E2E ---")

# Create item via trading
item = api("POST", "/trading/items", {
    "name": f"E2E Item {_rid}",
    "unit": "pcs", "category": "E2E", "selling_price": 100, "cost_price": 60
}, token)
test("P73.19 Item created (Trading)", "_err" not in item and "id" in item.get("data", {}))
item_id = item["data"]["id"]

# Verify visible in all industries
trading = api("GET", f"/trading/items/{item_id}", token=token)
test("P73.19 Item in Trading", "_err" not in trading)

retail = api("GET", f"/retail/items/barcode/{item['data'].get('item_code', 'X')}", token=token)
# May not find by barcode — that's OK, just verify query works
test("P73.19 Retail item query works", "_err" not in retail or retail.get("_err") == 404)

rest_menu = api("GET", "/restaurant/menu/items", token=token)
test("P73.19 Restaurant menu queryable", "_err" not in rest_menu)

mfg_wc = api("GET", "/manufacturing/work-centers", token=token)
test("P73.19 Manufacturing work centers", "_err" not in mfg_wc)

svc_dash = api("GET", "/services/dashboard", token=token)
test("P73.19 Services dashboard", "_err" not in svc_dash)

# Analytics covers all industries
analytics = api("GET", "/analytics/overview", token=token)
industries = analytics.get("data", {}).get("industries", {})
test("P73.19 Analytics covers 6 industries", len(industries) == 6)

# ═══ P73.20 E2E FLOW ═══
print("\n--- P73.20 E2E Business Flow ---")

# Full flow: Create customer → Create item → Create SO → Fire notification
cust = api("POST", "/trading/customers", {
    "name": f"E2E Customer {_rid}", "email": f"e2e{_rid}@test.com"
}, token)
test("P73.20 Customer created", "_err" not in cust and "id" in cust.get("data", {}))
cust_id = cust["data"]["id"]

so = api("POST", "/trading/sales-orders", {
    "customer_id": cust_id,
    "lines": [{"item_id": item_id, "qty": 5, "unit_price": 100}]
}, token)
test("P73.20 Sales order created", "_err" not in so and "id" in so.get("data", {}))

if "_err" not in so:
    order_id = so["data"]["id"]
    fire = api("POST", "/notifications/events/fire", {
        "event_type": "order.created",
        "source_module": "trading",
        "source_id": order_id,
        "payload": {"total": 500}
    }, token)
    test("P73.20 Notification fired", "_err" not in fire and "event_id" in fire.get("data", {}))

    # Create approval chain and request
    chain = api("POST", "/approvals/chains", {
        "chain_name": f"E2E Approval-{_rid}",
        "source_module": "trading",
        "steps": [{"step_order": 1, "step_name": "Manager", "approver_type": "user"}]
    }, token)
    test("P73.20 Approval chain created", "_err" not in chain)

    if "_err" not in chain:
        req = api("POST", "/approvals/requests", {
            "chain_id": chain["data"]["id"],
            "source_module": "trading",
            "source_id": order_id,
            "title": f"E2E Approval-{_rid}"
        }, token)
        test("P73.20 Approval request created", "_err" not in req)

# Dashboard shows everything
dash = api("GET", "/trading/dashboard", token=token)
test("P73.20 Trading dashboard works", "_err" not in dash and "data" in dash)

# ═══ RESULTS ═══
print(f"\n{'='*60}")
print(f"P73.17-20 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
