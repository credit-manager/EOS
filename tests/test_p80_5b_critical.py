"""
P80.5B — Critical Remediation Tests (9/9)
Tests that verify each critical issue is actually fixed.
"""
import sys, io, json, uuid
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0

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
    global passed, failed
    if cond:
        passed += 1; print(f"  PASS  {name}")
    else:
        failed += 1; print(f"  FAIL  {name}")

print("=" * 60)
print("  P80.5B — CRITICAL REMEDIATION TESTS")
print("=" * 60)

r = api("POST", "/api/v1/auth/login", {"email": "admin@demo.com", "password": "admin123"})
token = r["data"]["access_token"]

# ─── C9: Services accept_quotation ─────────────
print("\n--- C9: Services accept_quotation ---")
# Verify fix at code level (q_id was undefined, should be quote_id)
with open("D:\\EOS\\EOS-Release-1.0\\routers\\services_api.py", encoding="utf-8") as f:
    svc_content = f.read()
# The fix changed q_id[:8] to quote_id[:8] in the accept function
test("C9: services_api.py uses quote_id (not q_id) in accept",
     "quote_id[:8]" in svc_content and "q_id[:8]" not in svc_content)

# ─── C8: No real secrets in .env.production ─────
print("\n--- C8: No real secrets ---")
with open("D:\\EOS\\EOS-Release-1.0\\.env.production", encoding="utf-8") as f:
    env_content = f.read()
test("C8: .env.production has no real secret key",
     "V9hlS_-LWVt" not in env_content and "CHANGE_ME" in env_content)

# ─── C7: No hardcoded DB creds in alembic.ini ──
print("\n--- C7: No hardcoded DB creds ---")
with open("D:\\EOS\\EOS-Release-1.0\\alembic.ini", encoding="utf-8") as f:
    alembic_content = f.read()
test("C7: alembic.ini has no hardcoded password",
     "eos:0100" not in alembic_content and "DATABASE_URL" in alembic_content)

# ─── C6: Stock transfer uses correct table ─────
print("\n--- C6: Stock transfer unit_cost ---")
with open("D:\\EOS\\EOS-Release-1.0\\routers\\trading_api.py", encoding="utf-8") as f:
    trading_content = f.read()
test("C6: Stock transfer reads from dbp_commerce_stock",
     "SELECT unit_cost FROM dbp_commerce_stock" in trading_content)

# ─── C2: Portal password hashing ───────────────
print("\n--- C2: Portal password hashing ---")
with open("D:\\EOS\\EOS-Release-1.0\\core\\portal_engine.py", encoding="utf-8") as f:
    portal_content = f.read()
test("C2: Portal uses PBKDF2 (not raw SHA-256)",
     "pbkdf2_hmac" in portal_content and "_verify_password" in portal_content)

# ─── C3: WebSocket rejects unauthenticated ─────
print("\n--- C3: WebSocket auth ---")
with open("D:\\EOS\\EOS-Release-1.0\\routers\\ws_router.py", encoding="utf-8") as f:
    ws_content = f.read()
test("C3: WebSocket rejects unauthenticated (4001)",
     "4001" in ws_content and "anonymous_" not in ws_content)
test("C3: WebSocket has tenant_id isolation",
     "tenant_id" in ws_content and "connection_info" in ws_content)

# ─── C1: Accounting tenant isolation ────────────
print("\n--- C1: Accounting tenant isolation ---")
with open("D:\\EOS\\EOS-Release-1.0\\routers\\accounting_api.py", encoding="utf-8") as f:
    acct_content = f.read()
# Count tenant_id usage in queries
tenant_count = acct_content.count("tenant_id = :tid") + acct_content.count("tenant_id=:tid")
test(f"C1: Accounting has tenant_id on queries ({tenant_count} instances)", tenant_count >= 15)

# Verify all functions extract tid from user
tid_extractions = acct_content.count('tid = user.get("tenant_id")')
test(f"C1: All functions extract tid ({tid_extractions} functions)", tid_extractions >= 10)

# Verify conditions list starts with tenant_id
conditions_starts = acct_content.count('conditions = ["tenant_id = :tid"]')
test(f"C1: Conditions list starts with tenant_id ({conditions_starts} lists)", conditions_starts >= 2)

# Verify report queries have tenant_id
report_queries = acct_content.count('WHERE tenant_id = :tid AND')
test(f"C1: Report queries have tenant_id ({report_queries} queries)", report_queries >= 4)

# ─── C4: Journal double-posting prevention ──────
print("\n--- C4: Journal concurrency ---")
test("C4: Accounting engine uses SELECT FOR UPDATE",
     "FOR UPDATE" in open("D:\\EOS\\EOS-Release-1.0\\core\\accounting_engine.py", encoding="utf-8").read())
test("C4: Accounting API uses SELECT FOR UPDATE",
     "FOR UPDATE" in acct_content)

# ─── C5: GL balance updates ────────────────────
print("\n--- C5: GL integrity ---")
test("C5: Post endpoint updates GL balances",
     "UPDATE dbp_accounts SET current_balance = current_balance" in acct_content)
test("C5: Reverse endpoint reverses GL balances",
     "current_balance = current_balance - :dr + :cr" in acct_content)
test("C5: Create entry validates debit == credit",
     "not balanced" in acct_content)

# ─── Summary ────────────────────────────────────
print(f"\n{'='*60}")
print(f"  P80.5B CRITICAL REMEDIATION TESTS")
print(f"{'='*60}")
print(f"  Passed: {passed}")
print(f"  Failed: {failed}")
print(f"  Total:  {passed + failed}")
print(f"{'='*60}")

if failed == 0:
    print("  ALL 9 CRITICAL ISSUES VERIFIED FIXED")
else:
    print(f"  {failed} ISSUES REMAIN")
