"""
P74.9 Two-Factor Authentication — Tests
"""
import sys, io, json, uuid, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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

print(f"=== P74.9 TWO-FACTOR AUTHENTICATION ({_rid}) ===\n")

# ═══ 2FA STATUS (initially disabled) ═══
print("--- 2FA Status ---")
status = api("GET", "/api/v1/auth/2fa/status", token=token)
test("2FA status endpoint works", "_err" not in status)
test("2FA initially disabled", status.get("data", {}).get("enabled") == False)

# ═══ ENABLE 2FA ═══
print("\n--- Enable 2FA ---")
enable = api("POST", "/api/v1/auth/2fa/enable", {"method": "totp"}, token)
test("2FA enable works", "_err" not in enable and "secret" in enable.get("data", {}))
test("Recovery codes returned", len(enable.get("data", {}).get("recovery_codes", [])) == 8)
test("Provisioning URI returned", enable.get("data", {}).get("provisioning_uri") is not None)

# ═══ 2FA STATUS (after enable) ═══
print("\n--- 2FA Status (after enable) ---")
status2 = api("GET", "/api/v1/auth/2fa/status", token=token)
test("2FA now enabled", status2.get("data", {}).get("enabled") == True)
test("2FA method is totp", status2.get("data", {}).get("method") == "totp")
test("Recovery codes remaining: 8", status2.get("data", {}).get("recovery_codes_remaining") == 8)

# ═══ VERIFY 2FA (invalid code) ═══
print("\n--- 2FA Verify (invalid) ---")
bad = api("POST", "/api/v1/auth/2fa/verify", {"code": "000000"}, token)
test("Invalid TOTP code rejected", bad.get("_err") == 401)

# ═══ 2FA ATTEMPTS ═══
print("\n--- 2FA Attempts ---")
attempts = api("GET", "/api/v1/auth/2fa/attempts", token=token)
test("Attempts endpoint works", "_err" not in attempts)
test("Failed attempt logged", attempts.get("data", {}).get("count", 0) >= 1)

# ═══ RECOVERY CODE (invalid) ═══
print("\n--- Recovery Code (invalid) ---")
bad_rec = api("POST", "/api/v1/auth/2fa/verify-recovery", {"code": "00000000"}, token)
test("Invalid recovery code rejected", bad_rec.get("_err") == 401)

# ═══ DISABLE 2FA ═══
print("\n--- Disable 2FA ---")
disable = api("POST", "/api/v1/auth/2fa/disable", token=token)
test("2FA disable works", "_err" not in disable)

status3 = api("GET", "/api/v1/auth/2fa/status", token=token)
test("2FA disabled after disable", status3.get("data", {}).get("enabled") == False)

# ═══ RE-ENABLE AND TEST RECOVERY ═══
print("\n--- Re-enable + Recovery Code ---")
enable2 = api("POST", "/api/v1/auth/2fa/enable", {"method": "totp"}, token)
recovery_code = enable2["data"]["recovery_codes"][0]
rec = api("POST", "/api/v1/auth/2fa/verify-recovery", {"code": recovery_code}, token)
test("Valid recovery code accepted", "_err" not in rec)

status4 = api("GET", "/api/v1/auth/2fa/status", token=token)
test("Recovery codes remaining: 7", status4.get("data", {}).get("recovery_codes_remaining") == 7)

# ═══ CLEANUP ═══
api("POST", "/api/v1/auth/2fa/disable", token=token)

# ═══ RESULTS ═══
print(f"\n{'='*60}")
print(f"P74.9 2FA Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL 2FA TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
