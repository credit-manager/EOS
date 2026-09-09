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

r = api("POST", "/api/v1/auth/login", {"email": "admin@demo.com", "password": "admin123"})
token = r["data"]["access_token"]
_rid = uuid.uuid4().hex[:6].upper()

print("=== P71.2 Universal Approval Engine Tests ===\n")

# ═══ 1. CHAINS ═══
print("--- Approval Chains ---")
chain = api("POST", "/approvals/chains", {
    "chain_name": f"PO Approval-{_rid}",
    "source_module": "trading",
    "description": "Purchase order approval chain",
    "steps": [
        {"step_order": 1, "step_name": "Manager Review", "approver_type": "user", "min_approvals": 1},
        {"step_order": 2, "step_name": "Finance Director", "approver_type": "user", "min_approvals": 1},
    ]
}, token)
test("1.1 Chain created", "_err" not in chain and "id" in chain.get("data", {}))
chain_id = chain["data"]["id"]

dup = api("POST", "/approvals/chains", {
    "chain_name": f"PO Approval-{_rid}", "source_module": "trading",
    "steps": [{"step_order": 1, "step_name": "Review", "approver_type": "user"}]
}, token)
test("1.2 Duplicate rejected", "_err" in dup)

chains = api("GET", "/approvals/chains", token=token)
test("1.3 Chains listable", "_err" not in chains)

chains_mod = api("GET", "/approvals/chains?source_module=trading", token=token)
test("1.4 Chains filterable by module", "_err" not in chains_mod and len(chains_mod["data"]) >= 1)

steps = api("GET", f"/approvals/chains/{chain_id}/steps", token=token)
test("1.5 Chain steps returned", "_err" not in steps and len(steps["data"]) == 2)
test("1.6 Steps ordered correctly", steps["data"][0]["step_order"] == 1)

bad_chain = api("POST", "/approvals/chains", {
    "chain_name": f"Bad-{_rid}", "source_module": "test",
    "steps": [{"step_order": 1, "step_name": "X", "approver_type": "wizard"}]
}, token)
test("1.7 Invalid approver_type rejected", "_err" in bad_chain)

# ═══ 2. CREATE REQUESTS ═══
print("\n--- Approval Requests ---")
req1 = api("POST", "/approvals/requests", {
    "chain_id": chain_id,
    "source_module": "trading",
    "source_id": uuid.uuid4().hex[:8],
    "title": f"PO-001-{_rid} — Office Supplies",
    "description": "Annual office supply order"
}, token)
test("2.1 Request created", "_err" not in req1 and "id" in req1.get("data", {}))
req_id = req1["data"]["id"]

req2 = api("POST", "/approvals/requests", {
    "chain_id": chain_id,
    "source_module": "trading",
    "source_id": uuid.uuid4().hex[:8],
    "title": f"PO-002-{_rid} — IT Equipment",
}, token)
test("2.2 Second request created", "_err" not in req2)

reqs = api("GET", "/approvals/requests", token=token)
test("2.3 Requests listable", "_err" not in reqs)

reqs_pending = api("GET", "/approvals/requests?status=pending", token=token)
test("2.4 Filterable by status", "_err" not in reqs_pending)

reqs_mod = api("GET", "/approvals/requests?source_module=trading", token=token)
test("2.5 Filterable by module", "_err" not in reqs_mod)

detail = api("GET", f"/approvals/requests/{req_id}", token=token)
test("2.6 Request detail accessible", "_err" not in detail)
test("2.7 Detail has chain steps", "chain_steps" in detail.get("data", {}))
test("2.8 Detail has empty actions", len(detail["data"]["actions"]) == 0)

# ═══ 3. DECISIONS ═══
print("\n--- Decisions ---")
dec1 = api("POST", f"/approvals/requests/{req_id}/decide", {
    "decision": "approved", "comment": "Looks good"
}, token)
test("3.1 Step 1 approved", "_err" not in dec1 and dec1["data"]["decision"] == "approved")

detail2 = api("GET", f"/approvals/requests/{req_id}", token=token)
test("3.2 Advanced to step 2", detail2["data"]["current_step"] == 2)
test("3.3 Still pending", detail2["data"]["status"] == "pending")

dec2 = api("POST", f"/approvals/requests/{req_id}/decide", {
    "decision": "approved", "comment": "Finance approved"
}, token)
test("3.4 Step 2 approved", "_err" not in dec2)

detail3 = api("GET", f"/approvals/requests/{req_id}", token=token)
test("3.5 Fully approved", detail3["data"]["status"] == "approved")
test("3.6 Completed timestamp set", detail3["data"]["completed_at"] is not None)

# Reject a request
req2_id = req2["data"]["id"]
dec3 = api("POST", f"/approvals/requests/{req2_id}/decide", {
    "decision": "rejected", "comment": "Over budget"
}, token)
test("3.7 Request rejected", "_err" not in dec3)

detail4 = api("GET", f"/approvals/requests/{req2_id}", token=token)
test("3.8 Status is rejected", detail4["data"]["status"] == "rejected")

# Can't decide on non-pending
dec_bad = api("POST", f"/approvals/requests/{req_id}/decide", {
    "decision": "approved"
}, token)
test("3.9 Can't decide on approved request", "_err" in dec_bad)

dec_bad2 = api("POST", f"/approvals/requests/{req2_id}/decide", {
    "decision": "approved"
}, token)
test("3.10 Can't decide on rejected request", "_err" in dec_bad2)

# ═══ 4. CANCEL ═══
print("\n--- Cancel ---")
req3 = api("POST", "/approvals/requests", {
    "chain_id": chain_id,
    "source_module": "trading",
    "source_id": uuid.uuid4().hex[:8],
    "title": f"PO-003-{_rid} — Cancelled"
}, token)
req3_id = req3["data"]["id"]
cancel = api("POST", f"/approvals/requests/{req3_id}/cancel", token=token)
test("4.1 Request cancelled", "_err" not in cancel)

detail5 = api("GET", f"/approvals/requests/{req3_id}", token=token)
test("4.2 Status is cancelled", detail5["data"]["status"] == "cancelled")

cancel_bad = api("POST", f"/approvals/requests/{req3_id}/cancel", token=token)
test("4.3 Can't cancel non-pending", "_err" in cancel_bad)

# ═══ 5. AUDIT LOG ═══
print("\n--- Audit Log ---")
log = api("GET", f"/approvals/log/{req_id}", token=token)
test("5.1 Log accessible", "_err" not in log)
test("5.2 Log has entries", len(log["data"]) >= 2)
test("5.3 Log has creation entry", any("created" in e["action"] for e in log["data"]))
test("5.4 Log has approval entries", any("approved" in e["action"] for e in log["data"]))

# ═══ 6. PENDING ═══
print("\n--- Pending ---")
pending = api("GET", "/approvals/pending", token=token)
test("6.1 Pending listable", "_err" not in pending)

# ═══ 7. STATS ═══
print("\n--- Stats ---")
stats = api("GET", "/approvals/stats", token=token)
test("7.1 Stats accessible", "_err" not in stats)
test("7.2 Has pending count", "pending" in stats["data"])
test("7.3 Has approved count", "approved" in stats["data"])
test("7.4 Approved >= 1", stats["data"]["approved"] >= 1)

# ═══ 8. INVALID DECISION ═══
print("\n--- Invalid Inputs ---")
req4 = api("POST", "/approvals/requests", {
    "chain_id": chain_id, "source_module": "test", "source_id": "x", "title": "T"
}, token)
bad_dec = api("POST", f"/approvals/requests/{req4['data']['id']}/decide", {
    "decision": "maybe"
}, token)
test("8.1 Invalid decision rejected", "_err" in bad_dec)

not_found = api("GET", "/approvals/requests/nonexistent", token=token)
test("8.2 Not found for bad ID", "_err" in not_found)

# ═══ 9. NO-CHAIN QUICK REQUEST ═══
print("\n--- No-Chain Request ---")
req5 = api("POST", "/approvals/requests", {
    "source_module": "retail",
    "source_id": uuid.uuid4().hex[:8],
    "title": f"Quick Approval-{_rid}"
}, token)
test("9.1 No-chain request created", "_err" not in req5)

detail6 = api("GET", f"/approvals/requests/{req5['data']['id']}", token=token)
test("9.2 No-chain detail shows no steps", len(detail6["data"]["chain_steps"]) == 0)

# ═══ 10. CROSS-INDUSTRY ═══
print("\n--- Cross-Industry ---")
rest_chain = api("POST", "/approvals/chains", {
    "chain_name": f"Menu Change-{_rid}",
    "source_module": "restaurant",
    "steps": [{"step_order": 1, "step_name": "Chef Review", "approver_type": "user"}]
}, token)
test("10.1 Restaurant chain created", "_err" not in rest_chain)

mfg_chain = api("POST", "/approvals/chains", {
    "chain_name": f"BOM Approval-{_rid}",
    "source_module": "manufacturing",
    "steps": [{"step_order": 1, "step_name": "Engineering", "approver_type": "user"}]
}, token)
test("10.2 Manufacturing chain created", "_err" not in mfg_chain)

svc_chain = api("POST", "/approvals/chains", {
    "chain_name": f"Project Go-Live-{_rid}",
    "source_module": "services",
    "steps": [{"step_order": 1, "step_name": "PM Review", "approver_type": "user"}]
}, token)
test("10.3 Services chain created", "_err" not in svc_chain)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P71.2 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
