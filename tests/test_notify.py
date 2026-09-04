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

print("=== P71.1 Notification Engine Tests ===\n")

# ═══ 1. TEMPLATES ═══
print("--- Templates ---")
tmpl = api("POST", "/notifications/templates", {
    "template_code": f"INV-OVERDUE-{_rid}",
    "name": "Invoice Overdue",
    "channel": "in_app",
    "subject": "Invoice {{invoice_number}} is overdue",
    "body": "Invoice {{invoice_number}} for {{client_name}} is overdue by {{days}} days. Amount: ${{amount}}",
    "variables": ["invoice_number", "client_name", "days", "amount"]
}, token)
test("1.1 Template created", "_err" not in tmpl and "id" in tmpl.get("data", {}))
tmpl_id = tmpl["data"]["id"]

tmpls = api("GET", "/notifications/templates", token=token)
test("1.2 Templates listable", "_err" not in tmpls)

# Duplicate
dup = api("POST", "/notifications/templates", {
    "template_code": f"INV-OVERDUE-{_rid}", "name": "Dup", "body": "test"
}, token)
test("1.3 Duplicate rejected", "_err" in dup)

# ═══ 2. RULES ═══
print("\n--- Rules ---")
rule = api("POST", "/notifications/rules", {
    "rule_name": f"invoice-overdue-{_rid}",
    "event_type": "invoice.overdue",
    "source_module": "invoices",
    "channel": "in_app",
    "recipient_type": "all",
    "template_id": tmpl_id,
    "priority": 3
}, token)
test("2.1 Rule created", "_err" not in rule and "id" in rule.get("data", {}))
rule_id = rule["data"]["id"]

rules = api("GET", "/notifications/rules", token=token)
test("2.2 Rules listable", "_err" not in rules)

toggle = api("PUT", f"/notifications/rules/{rule_id}/toggle", token=token)
test("2.3 Rule toggled", "_err" not in toggle and "is_active" in toggle.get("data", {}))

# Toggle back
api("PUT", f"/notifications/rules/{rule_id}/toggle", token=token)

# Invalid channel
bad_rule = api("POST", "/notifications/rules", {
    "rule_name": f"bad-{_rid}", "event_type": "test", "channel": "telepathy",
    "recipient_type": "all"
}, token)
test("2.4 Invalid channel rejected", "_err" in bad_rule)

# ═══ 3. FIRE EVENT ═══
print("\n--- Fire Event ---")
fire = api("POST", "/notifications/events/fire", {
    "event_type": "invoice.overdue",
    "source_module": "invoices",
    "source_id": uuid.uuid4().hex[:8],
    "payload": {"invoice_number": "INV-001", "client_name": "Acme Corp", "days": 15, "amount": 5000}
}, token)
test("3.1 Event fired", "_err" not in fire and "delivered" in fire.get("data", {}))
test("3.2 Rules matched", fire["data"]["rules_matched"] >= 1)
test("3.3 Notifications delivered", fire["data"]["delivered"] >= 1)

# ═══ 4. INBOX ═══
print("\n--- Inbox ---")
inbox = api("GET", "/notifications/inbox", token=token)
test("4.1 Inbox accessible", "_err" not in inbox)
test("4.2 Notification received", len(inbox.get("data", [])) >= 1)

count = api("GET", "/notifications/inbox/count", token=token)
test("4.3 Unread count", "_err" not in count and count["data"]["unread"] >= 1)

# Mark read
notif_id = inbox["data"][0]["id"]
mark = api("PUT", f"/notifications/inbox/{notif_id}/read", token=token)
test("4.4 Marked as read", "_err" not in mark)

count2 = api("GET", "/notifications/inbox/count", token=token)
test("4.5 Unread decreased", count2["data"]["unread"] < count["data"]["unread"])

# Read all
read_all = api("PUT", "/notifications/inbox/read-all", token=token)
test("4.6 Read all", "_err" not in read_all)

count3 = api("GET", "/notifications/inbox/count", token=token)
test("4.7 Unread is 0", count3["data"]["unread"] == 0)

# ═══ 5. PREFERENCES ═══
print("\n--- Preferences ---")
pref = api("POST", "/notifications/preferences", {
    "category": "approval", "in_app": True, "email": True
}, token)
test("5.1 Preference set", "_err" not in pref)

prefs = api("GET", "/notifications/preferences", token=token)
test("5.2 Preferences listable", "_err" not in prefs)

# ═══ 6. STATS ═══
print("\n--- Stats ---")
stats = api("GET", "/notifications/stats", token=token)
test("6.1 Stats accessible", "_err" not in stats)
test("6.2 Events today tracked", "events_today" in stats.get("data", {}))
test("6.3 Active rules tracked", "rules_active" in stats.get("data", {}))

# ═══ 7. CROSS-INDUSTRY: Fire from Trading ═══
print("\n--- Cross-Industry Events ---")
fire2 = api("POST", "/notifications/events/fire", {
    "event_type": "order.approved",
    "source_module": "trading",
    "source_id": uuid.uuid4().hex[:8],
    "payload": {"order_number": "SO-001", "total": 25000}
}, token)
test("7.1 Trading event fired", "_err" not in fire2)

fire3 = api("POST", "/notifications/events/fire", {
    "event_type": "project.milestone",
    "source_module": "services",
    "source_id": uuid.uuid4().hex[:8],
    "payload": {"project": "ERP Implementation", "milestone": "Phase 1"}
}, token)
test("7.2 Services event fired", "_err" not in fire3)

fire4 = api("POST", "/notifications/events/fire", {
    "event_type": "production.completed",
    "source_module": "manufacturing",
    "source_id": uuid.uuid4().hex[:8],
    "payload": {"order_number": "MO-001", "qty": 100}
}, token)
test("7.3 Manufacturing event fired", "_err" not in fire4)

# ═══ 8. MULTIPLE RULES ═══
print("\n--- Multiple Rules ---")
api("POST", "/notifications/rules", {
    "rule_name": f"order-approved-email-{_rid}",
    "event_type": "order.approved",
    "channel": "email",
    "recipient_type": "all"
}, token)

fire5 = api("POST", "/notifications/events/fire", {
    "event_type": "order.approved",
    "source_module": "trading",
    "payload": {"order_number": "SO-002"}
}, token)
test("8.1 Multiple rules matched", fire5["data"]["rules_matched"] >= 2)

# ═══ 9. NO RULE = NO NOTIFICATION ═══
print("\n--- No Rule Scenario ---")
fire6 = api("POST", "/notifications/events/fire", {
    "event_type": "random.unknown.event",
    "source_module": "test",
    "payload": {}
}, token)
test("9.1 No rules matched for unknown event", fire6["data"]["rules_matched"] == 0)
test("9.2 Nothing delivered", fire6["data"]["delivered"] == 0)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P71.1 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
