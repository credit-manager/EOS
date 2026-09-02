import io
import json
import sys

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

print("=== P71.4 Cross-Industry Analytics Tests ===\n")

# ═══ 1. OVERVIEW ═══
print("--- Overview ---")
ov = api("GET", "/analytics/overview", token=token)
test("1.1 Overview accessible", "_err" not in ov)
test("1.2 Has industries breakdown", "industries" in ov.get("data", {}))
test("1.3 Has total_users", "total_users" in ov["data"])
test("1.4 Has active_industries", "active_industries" in ov["data"])
test("1.5 Industries has trading", "trading" in ov["data"]["industries"])
test("1.6 Industries has retail", "retail" in ov["data"]["industries"])
test("1.7 Industries has restaurant", "restaurant" in ov["data"]["industries"])
test("1.8 Industries has construction", "construction" in ov["data"]["industries"])
test("1.9 Industries has manufacturing", "manufacturing" in ov["data"]["industries"])
test("1.10 Industries has services", "services" in ov["data"]["industries"])

# ═══ 2. BY INDUSTRY ═══
print("\n--- By Industry ---")
bi = api("GET", "/analytics/by-industry", token=token)
test("2.1 By-industry accessible", "_err" not in bi)
test("2.2 Returns list", isinstance(bi.get("data", []), list))

# ═══ 3. ALERTS ═══
print("\n--- Alerts ---")
alerts = api("GET", "/analytics/alerts", token=token)
test("3.1 Alerts accessible", "_err" not in alerts)
test("3.2 Returns list", isinstance(alerts.get("data", []), list))
test("3.3 Each alert has type", all("type" in a for a in alerts["data"]) if alerts["data"] else True)

# ═══ 4. INVENTORY SUMMARY ═══
print("\n--- Inventory Summary ---")
inv = api("GET", "/analytics/inventory-summary", token=token)
test("4.1 Inventory summary accessible", "_err" not in inv)
test("4.2 Has items count", "items" in inv["data"])
test("4.3 Has total_stock", "total_stock" in inv["data"])
test("4.4 Has total_value", "total_value" in inv["data"])
test("4.5 Has low_stock_items", "low_stock_items" in inv["data"])
test("4.6 Has warehouses", "warehouses" in inv["data"])

# ═══ 5. HR SUMMARY ═══
print("\n--- HR Summary ---")
hr = api("GET", "/analytics/hr-summary", token=token)
test("5.1 HR summary accessible", "_err" not in hr)
test("5.2 Has employees", "employees" in hr["data"])
test("5.3 Has departments", "departments" in hr["data"])

# ═══ 6. ACCOUNTING SUMMARY ═══
print("\n--- Accounting Summary ---")
acct = api("GET", "/analytics/accounting-summary", token=token)
test("6.1 Accounting summary accessible", "_err" not in acct)
test("6.2 Has journals count", "journals" in acct["data"])
test("6.3 Has accounts count", "accounts" in acct["data"])
test("6.4 Has total_debit", "total_debit" in acct["data"])
test("6.5 Has total_credit", "total_credit" in acct["data"])
test("6.6 Has balanced flag", "balanced" in acct["data"])

# ═══ 7. UNAUTH ═══
print("\n--- Unauthorized ---")
no_auth = api("GET", "/analytics/overview")
test("7.1 Unauthorized rejected", "_err" in no_auth and no_auth["_err"] == 401)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P71.4 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
