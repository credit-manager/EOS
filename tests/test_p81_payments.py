"""
P81 — PAYMENT GATEWAY INTEGRATION
==================================
Tests: Gateways, Transactions, Refunds, Payment Links, Bank Transfer, Cash
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
        if "json" in ct:
            return json.loads(resp.read())
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
print(f"=== P81 PAYMENT GATEWAY INTEGRATION ({_rid}) ===\n")

# Login
r = api("POST", "/api/v1/auth/login", {"email": "admin@demo.com", "password": "admin123"})
token = r["data"]["access_token"]

# ═══════ GATEWAYS ═══════
print("--- Gateways ---")

gw1 = api("POST", "/payments/gateways", {
    "gateway_name": "Stripe", "gateway_type": "stripe",
    "config": {"publishable_key": "pk_test_xxx", "secret_key": "sk_test_xxx"}
}, token)
test("81.1 Gateway created", "_err" not in gw1)

gw2 = api("POST", "/payments/gateways", {
    "gateway_name": "Mada", "gateway_type": "mada"
}, token)
test("81.2 Mada gateway created", "_err" not in gw2)

gw_list = api("GET", "/payments/gateways", token=token)
test("81.3 Gateways listable", "_err" not in gw_list and len(gw_list.get("data", [])) >= 2)

# ═══════ TRANSACTIONS ═══════
print("\n--- Transactions ---")

txn1 = api("POST", "/payments/transactions", {
    "amount": 5000, "currency": "SAR", "payment_method": "credit_card",
    "customer_id": "cust-001", "reference_type": "sales_order", "reference_id": "SO-001"
}, token)
test("81.4 Transaction created", "_err" not in txn1 and "transaction_id" in txn1.get("data", {}))
txn_id = txn1["data"]["transaction_id"]

txn2 = api("POST", "/payments/transactions", {
    "amount": 2500, "currency": "SAR", "payment_method": "bank_transfer",
    "customer_id": "cust-002"
}, token)
test("81.5 Second transaction created", "_err" not in txn2)

# Complete transaction
comp = api("POST", f"/payments/transactions/{txn_id}/complete", token=token)
test("81.6 Transaction completed", "_err" not in comp and comp.get("data", {}).get("status") == "completed")

# List transactions
txns = api("GET", "/payments/transactions", token=token)
test("81.7 Transactions listable", "_err" not in txns and txns.get("total", 0) >= 2)

# Get single transaction
txn_detail = api("GET", f"/payments/transactions/{txn_id}", token=token)
test("81.8 Transaction detail works", "_err" not in txn_detail and txn_detail.get("data", {}).get("status") == "completed")

# List by status
completed = api("GET", "/payments/transactions?status=completed", token=token)
test("81.9 Filter by status works", "_err" not in completed)

# ═══════ REFUNDS ═══════
print("\n--- Refunds ---")

refund = api("POST", f"/payments/transactions/{txn_id}/refund", {"amount": 1000}, token)
test("81.10 Refund created", "_err" not in refund and refund.get("data", {}).get("status") == "completed")

# ═══════ PAYMENT LINKS ═══════
print("\n--- Payment Links ---")

link = api("POST", "/payments/links", {
    "amount": 1500, "description": "Invoice INV-2026-001",
    "customer_email": "customer@example.com"
}, token)
test("81.11 Payment link created", "_err" not in link and "payment_url" in link.get("data", {}))

# ═══════ BANK TRANSFER ═══════
print("\n--- Bank Transfer ---")

bt = api("POST", "/payments/bank-transfer", {
    "amount": 8000, "bank_name": "Al Rajhi Bank",
    "account_number": "SA1234567890", "reference": "TRF-2026-001"
}, token)
test("81.12 Bank transfer recorded", "_err" not in bt)

# ═══════ CASH ═══════
print("\n--- Cash Payment ---")

cash = api("POST", "/payments/cash?amount=500", token=token)
test("81.13 Cash payment recorded", "_err" not in cash)

# ═══════ SUMMARY ═══════
print("\n--- Summary ---")

summary = api("GET", "/payments/summary", token=token)
test("81.14 Payment summary works", "_err" not in summary and "total_collected" in summary.get("data", {}))
test("81.15 Summary has net amount", summary.get("data", {}).get("net_amount", 0) > 0)

# ═══════ FAIL TRANSACTION ═══════
print("\n--- Edge Cases ---")

fail_txn = api("POST", "/payments/transactions", {
    "amount": 100, "currency": "SAR", "payment_method": "credit_card"
}, token)
fail_id = fail_txn["data"]["transaction_id"]
fail_result = api("POST", f"/payments/transactions/{fail_id}/fail?reason=insufficient_funds", token=token)
test("81.16 Transaction failure works", "_err" not in fail_result)

# Auth required
no_auth = api("GET", "/payments/transactions")
test("81.17 Auth required", no_auth.get("_err") in [401, 403])

# ═══════ SUMMARY ═══════
print(f"\n{'='*60}")
print("P81 PAYMENT GATEWAY INTEGRATION")
print(f"{'='*60}")
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
print(f"  Total:  {total}")
print(f"{'='*60}")

if failed == 0:
    print("\n=== P81: PASS ===")
else:
    print(f"\n=== {failed} FAILURES ===")
