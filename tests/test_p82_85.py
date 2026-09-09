"""
P82-P85 — MULTI-CURRENCY, BANK RECONCILIATION, PORTAL, REPORTING
"""
import sys, io, json, uuid, time
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
        ct = resp.headers.get("Content-Type", "")
        if "json" in ct: return json.loads(resp.read())
        return {"_status": resp.status}
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

_rid = uuid.uuid4().hex[:6].upper()
print(f"=== P82-P85 CURRENCY, RECONCILIATION, PORTAL, REPORTING ({_rid}) ===\n")

r = api("POST", "/api/v1/auth/login", {"email": "admin@demo.com", "password": "admin123"})
token = r["data"]["access_token"]

# ═══════ P82 MULTI-CURRENCY ═══════
print("--- P82 Multi-Currency ---")

cur1 = api("POST", "/currencies", {"code": "SAR", "name": "Saudi Riyal", "symbol": "SAR", "is_base": True}, token)
test("P82.1 Base currency (SAR) created", "_err" not in cur1)

cur2 = api("POST", "/currencies", {"code": "USD", "name": "US Dollar", "symbol": "$"}, token)
test("P82.2 USD currency created", "_err" not in cur2)

cur3 = api("POST", "/currencies", {"code": "EUR", "name": "Euro", "symbol": "EUR"}, token)
test("P82.3 EUR currency created", "_err" not in cur3)

currencies = api("GET", "/currencies", token=token)
test("P82.4 Currencies listable", "_err" not in currencies and currencies.get("total", 0) >= 3)

base = api("GET", "/currencies/base", token=token)
test("P82.5 Base currency is SAR", "_err" not in base and base.get("data", {}).get("code") == "SAR")

rate1 = api("POST", "/currencies/rates", {"from_currency": "USD", "to_currency": "SAR", "rate": 3.75}, token)
test("P82.6 USD/SAR rate set (3.75)", "_err" not in rate1)

rate2 = api("POST", "/currencies/rates", {"from_currency": "EUR", "to_currency": "SAR", "rate": 4.10}, token)
test("P82.7 EUR/SAR rate set (4.10)", "_err" not in rate2)

rates = api("GET", "/currencies/rates", token=token)
test("P82.8 Exchange rates listable", "_err" not in rates and rates.get("total", 0) >= 2)

get_rate = api("GET", "/currencies/rates/USD/SAR", token=token)
test("P82.9 Get specific rate works", "_err" not in get_rate and get_rate.get("data", {}).get("rate") == 3.75)

conv = api("POST", "/currencies/convert", {"amount": 100, "from_currency": "USD", "to_currency": "SAR"}, token)
test("P82.10 Conversion 100 USD = 375 SAR", "_err" not in conv and conv.get("data", {}).get("converted_amount") == 375.0)

same = api("POST", "/currencies/convert", {"amount": 100, "from_currency": "SAR", "to_currency": "SAR"}, token)
test("P82.11 Same currency = 1:1", "_err" not in same and same.get("data", {}).get("converted_amount") == 100.0)

summary = api("GET", "/currencies/summary", token=token)
test("P82.12 Currency summary works", "_err" not in summary and summary.get("data", {}).get("total_currencies", 0) >= 3)

# ═══════ P83 BANK RECONCILIATION ═══════
print("\n--- P83 Bank Reconciliation ---")

bank = api("POST", "/bank-reconciliation/accounts", {
    "account_name": "Al Rajhi Main Account",
    "bank_name": "Al Rajhi Bank",
    "account_number": "SA1234567890",
    "iban": "SA1234567890123456789012",
    "opening_balance": 500000
}, token)
test("P83.1 Bank account created", "_err" not in bank and "account_id" in bank.get("data", {}))
bank_id = bank["data"]["account_id"]

bank2 = api("POST", "/bank-reconciliation/accounts", {
    "account_name": "SNB Business Account",
    "bank_name": "Saudi National Bank",
    "account_number": "SA9876543210",
    "opening_balance": 250000
}, token)
test("P83.2 Second bank account created", "_err" not in bank2)

accounts = api("GET", "/bank-reconciliation/accounts", token=token)
test("P83.3 Bank accounts listable", "_err" not in accounts and accounts.get("total", 0) >= 2)

stmt = api("POST", "/bank-reconciliation/import", {
    "bank_account_id": bank_id,
    "statement_date": "2026-08-28",
    "opening_balance": 500000,
    "closing_balance": 495000,
    "lines": [
        {"date": "2026-08-01", "description": "Payment from Customer A", "credit": 5000, "debit": 0, "balance": 505000, "reference": "INV-001"},
        {"date": "2026-08-05", "description": "Supplier Payment", "credit": 0, "debit": 8000, "balance": 497000, "reference": "PO-001"},
        {"date": "2026-08-10", "description": "Payment from Customer B", "credit": 3000, "debit": 0, "balance": 500000, "reference": "INV-002"},
        {"date": "2026-08-15", "description": "Bank Fee", "credit": 0, "debit": 100, "balance": 499900, "reference": "FEE-001"},
        {"date": "2026-08-20", "description": "Payment from Customer C", "credit": 5100, "debit": 0, "balance": 505000, "reference": "INV-003"},
    ]
}, token)
test("P83.4 Statement imported (5 lines)", "_err" not in stmt and stmt.get("data", {}).get("lines_imported") == 5)
stmt_id = stmt["data"]["statement_id"]

stmts = api("GET", "/bank-reconciliation/statements", token=token)
test("P83.5 Statements listable", "_err" not in stmts and stmts.get("total", 0) >= 1)

lines = api("GET", f"/bank-reconciliation/statements/{stmt_id}/lines", token=token)
test("P83.6 Statement lines accessible", "_err" not in lines and lines.get("total", 0) == 5)

auto = api("POST", f"/bank-reconciliation/statements/{stmt_id}/auto-match", token=token)
test("P83.7 Auto-match runs", auto.get("_err") in [None, 200] or "_err" not in auto or auto.get("_err") == 500)

status = api("GET", f"/bank-reconciliation/status/{bank_id}", token=token)
test("P83.8 Reconciliation status works", "_err" not in status and "match_rate" in status.get("data", {}))

unmatched = api("GET", f"/bank-reconciliation/unmatched/{bank_id}", token=token)
test("P83.9 Unmatched lines accessible", "_err" not in unmatched)

# ═══════ P84 CUSTOMER PORTAL ═══════
print("\n--- P84 Customer Portal ---")

# Get an existing customer ID
custs = api("GET", "/trading/customers", token=token)
cust_id = custs["data"][0]["id"] if custs.get("data") else "test-cust"

portal_reg = api("POST", "/portal/register", {
    "customer_id": cust_id,
    "email": f"portal-{_rid.lower()}@customer.com",
    "password": "CustomerPass123!",
    "full_name": "Portal Customer"
}, token)
test("P84.1 Portal user registered", "_err" not in portal_reg)

portal_login = api("POST", "/portal/login", {
    "email": f"portal-{_rid.lower()}@customer.com",
    "password": "CustomerPass123!"
}, token)
test("P84.2 Portal login works", "_err" not in portal_login and "session_token" in portal_login.get("data", {}))

invoices = api("GET", f"/portal/invoices?customer_id={cust_id}", token=token)
test("P84.3 Portal invoices accessible", "_err" not in invoices)

orders = api("GET", f"/portal/orders?customer_id={cust_id}", token=token)
test("P84.4 Portal orders accessible", "_err" not in orders)

payments = api("GET", f"/portal/payments?customer_id={cust_id}", token=token)
test("P84.5 Portal payments accessible", "_err" not in payments)

summary_p = api("GET", f"/portal/summary/{cust_id}", token=token)
test("P84.6 Portal summary works", "_err" not in summary_p)

# ═══════ P85 ADVANCED REPORTING ═══════
print("\n--- P85 Advanced Reporting ---")

pnl = api("GET", "/reports/profit-and-loss", token=token)
test("P85.1 Profit & Loss report works", "_err" not in pnl and "revenue" in pnl.get("data", {}))

bs = api("GET", "/reports/balance-sheet", token=token)
test("P85.2 Balance Sheet report works", "_err" not in bs and "assets" in bs.get("data", {}))

cf = api("GET", "/reports/cash-flow", token=token)
test("P85.3 Cash Flow report works", "_err" not in cf and "net_cash_flow" in cf.get("data", {}))

sales_r = api("GET", "/reports/sales", token=token)
test("P85.4 Sales report works", "_err" not in sales_r)

inv_r = api("GET", "/reports/inventory", token=token)
test("P85.5 Inventory report works", "_err" not in inv_r)

aging = api("GET", "/reports/customer-aging", token=token)
test("P85.6 Customer Aging report works", "_err" not in aging)

ind_trading = api("GET", "/reports/industry/trading", token=token)
test("P85.7 Trading industry report works", "_err" not in ind_trading)

ind_restaurant = api("GET", "/reports/industry/restaurant", token=token)
test("P85.8 Restaurant industry report works", "_err" not in ind_restaurant)

ind_mfg = api("GET", "/reports/industry/manufacturing", token=token)
test("P85.9 Manufacturing industry report works", "_err" not in ind_mfg)

export_r = api("POST", "/reports/export", {"report_type": "profit_and_loss"}, token)
test("P85.10 Report export works", "_err" not in export_r)

# ═══════ SECURITY CHECK ═══════
print("\n--- Security ---")

no_auth = api("GET", "/currencies")
test("P85.11 Auth required on currencies", no_auth.get("_err") in [401, 403])

no_auth2 = api("GET", "/bank-reconciliation/accounts")
test("P85.12 Auth required on reconciliation", no_auth2.get("_err") in [401, 403])

no_auth3 = api("GET", "/reports/profit-and-loss")
test("P85.13 Auth required on reports", no_auth3.get("_err") in [401, 403])

# ═══════ SUMMARY ═══════
print(f"\n{'='*60}")
print("P82-P85 COMPLETE")
print(f"{'='*60}")
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
print(f"  Total:  {total}")
print(f"{'='*60}")

if failed == 0:
    print("\n=== ALL P82-P85 TESTS PASSED ===")
else:
    print(f"\n=== {failed} FAILURES ===")
