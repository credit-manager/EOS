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

print("=== P71.5 Dynamic Customization Layer Tests ===\n")

# ═══ 1. CUSTOM FIELDS ═══
print("--- Custom Fields ---")
cf1 = api("POST", "/custom/fields", {
    "entity_type": "trading_item", "field_code": f"color_{_rid}",
    "field_label": "Color", "field_type": "select",
    "enum_values": "Red,Blue,Green", "sort_order": 1
}, token)
test("1.1 Custom field created", "_err" not in cf1 and "id" in cf1.get("data", {}))
field_id = cf1["data"]["id"]

cf2 = api("POST", "/custom/fields", {
    "entity_type": "trading_item", "field_code": f"hazard_{_rid}",
    "field_label": "Hazardous", "field_type": "boolean", "sort_order": 2
}, token)
test("1.2 Second field created", "_err" not in cf2)

dup = api("POST", "/custom/fields", {
    "entity_type": "trading_item", "field_code": f"color_{_rid}",
    "field_label": "Dup", "field_type": "text"
}, token)
test("1.3 Duplicate field rejected", "_err" in dup)

bad_type = api("POST", "/custom/fields", {
    "entity_type": "test", "field_code": "x", "field_label": "X", "field_type": "invalid"
}, token)
test("1.4 Invalid field_type rejected", "_err" in bad_type)

fields = api("GET", "/custom/fields?entity_type=trading_item", token=token)
test("1.5 Fields listed", "_err" not in fields and len(fields["data"]) >= 2)

# ═══ 2. FIELD VALUES ═══
print("\n--- Field Values ---")
test_entity = uuid.uuid4().hex[:8]
sv = api("POST", "/custom/fields/values", {
    "entity_type": "trading_item", "entity_id": test_entity,
    "field_id": field_id, "field_value": "Red"
}, token)
test("2.1 Field value set", "_err" not in sv)

sv2 = api("POST", "/custom/fields/values", {
    "entity_type": "trading_item", "entity_id": test_entity,
    "field_id": field_id, "field_value": "Blue"
}, token)
test("2.2 Field value updated (upsert)", "_err" not in sv2)

vals = api("GET", f"/custom/fields/values?entity_type=trading_item&entity_id={test_entity}", token=token)
test("2.3 Field values retrieved", "_err" not in vals and len(vals["data"]) >= 1)
test("2.4 Value is updated", vals["data"][0]["field_value"] == "Blue")

bad_field = api("POST", "/custom/fields/values", {
    "entity_type": "test", "entity_id": "x", "field_id": "nonexistent", "field_value": "v"
}, token)
test("2.5 Bad field_id rejected", "_err" in bad_field)

# ═══ 3. CUSTOM MODULES ═══
print("\n--- Custom Modules ---")
cm = api("POST", "/custom/modules", {
    "module_code": f"fleet_{_rid}",
    "module_name": f"Fleet Management-{_rid}",
    "description": "Track company vehicles",
    "icon": "car",
    "color": "#3498db",
    "fields": [
        {"field_code": "plate_number", "field_label": "Plate Number", "field_type": "text", "is_primary": True},
        {"field_code": "vehicle_type", "field_label": "Vehicle Type", "field_type": "select",
         "enum_values": "Sedan,SUV,Truck,Van"},
        {"field_code": "mileage", "field_label": "Mileage", "field_type": "number"},
        {"field_code": "purchase_date", "field_label": "Purchase Date", "field_type": "date"},
    ]
}, token)
test("3.1 Module created with fields", "_err" not in cm and "id" in cm.get("data", {}))
module_id = cm["data"]["id"]

dup_mod = api("POST", "/custom/modules", {
    "module_code": f"fleet_{_rid}", "module_name": "Dup", "fields": []
}, token)
test("3.2 Duplicate module rejected", "_err" in dup_mod)

modules = api("GET", "/custom/modules", token=token)
test("3.3 Modules listed", "_err" not in modules)
test("3.4 Module has fields", any(m["module_code"] == f"fleet_{_rid}" and len(m["fields"]) == 4 for m in modules["data"]))
test("3.5 Module has record_count", all("record_count" in m for m in modules["data"]))

mod_detail = api("GET", f"/custom/modules/{module_id}", token=token)
test("3.6 Module detail accessible", "_err" not in mod_detail and len(mod_detail["data"]["fields"]) == 4)

# ═══ 4. MODULE RECORDS ═══
print("\n--- Module Records ---")
rec1 = api("POST", f"/custom/modules/{module_id}/records", {
    "record_code": f"VH-{_rid}-001",
    "data": {"plate_number": "ABC-123", "vehicle_type": "SUV", "mileage": 45000, "purchase_date": "2023-06-15"}
}, token)
test("4.1 Record created", "_err" not in rec1 and "id" in rec1.get("data", {}))
rec_id = rec1["data"]["id"]

rec2 = api("POST", f"/custom/modules/{module_id}/records", {
    "record_code": f"VH-{_rid}-002",
    "data": {"plate_number": "XYZ-789", "vehicle_type": "Truck", "mileage": 12000}
}, token)
test("4.2 Second record created", "_err" not in rec2)

recs = api("GET", f"/custom/modules/{module_id}/records", token=token)
test("4.3 Records listed", "_err" not in recs and len(recs["data"]) == 2)
test("4.4 Record has data dict", isinstance(recs["data"][0]["data"], dict))

upd = api("PUT", f"/custom/modules/{module_id}/records/{rec_id}", {
    "record_code": f"VH-{_rid}-001",
    "data": {"plate_number": "ABC-123", "vehicle_type": "SUV", "mileage": 50000}
}, token)
test("4.5 Record updated", "_err" not in upd)

rec_detail = api("GET", f"/custom/modules/{module_id}/records", token=token)
updated_rec = next(r for r in rec_detail["data"] if r["id"] == rec_id)
test("4.6 Mileage updated to 50000", updated_rec["data"]["mileage"] == 50000)

del_rec = api("DELETE", f"/custom/modules/{module_id}/records/{rec_id}", token=token)
test("4.7 Record soft-deleted", "_err" not in del_rec)

recs_after = api("GET", f"/custom/modules/{module_id}/records", token=token)
test("4.8 Deleted record hidden", len(recs_after["data"]) == 1)

# ═══ 5. WORKFLOWS ═══
print("\n--- Workflows ---")
wf = api("POST", "/custom/workflows", {
    "workflow_name": f"Fleet Approval-{_rid}",
    "entity_type": "fleet_vehicle",
    "description": "Vehicle purchase approval",
    "steps": [
        {"step_order": 1, "step_name": "Manager Review", "action_type": "approve",
         "next_step_on_success": 2, "next_step_on_failure": None},
        {"step_order": 2, "step_name": "Finance Review", "action_type": "approve",
         "next_step_on_success": None, "next_step_on_failure": None},
    ]
}, token)
test("5.1 Workflow created", "_err" not in wf and "id" in wf.get("data", {}))
wf_id = wf["data"]["id"]

wfs = api("GET", "/custom/workflows", token=token)
test("5.2 Workflows listed", "_err" not in wfs)

wf_detail = api("GET", f"/custom/workflows/{wf_id}", token=token)
test("5.3 Workflow has steps", "_err" not in wf_detail and len(wf_detail["data"]["steps"]) == 2)
test("5.4 Running instances = 0", wf_detail["data"]["running_instances"] == 0)

# ═══ 6. WORKFLOW EXECUTION ═══
print("\n--- Workflow Execution ---")
start = api("POST", "/custom/workflows/start", {
    "workflow_id": wf_id,
    "entity_type": "fleet_vehicle",
    "entity_id": uuid.uuid4().hex[:8]
}, token)
test("6.1 Workflow started", "_err" not in start and "instance_id" in start.get("data", {}))
inst_id = start["data"]["instance_id"]

inst = api("GET", f"/custom/workflows/instances/{inst_id}", token=token)
test("6.2 Instance at step 1", inst["data"]["current_step"] == 1)
test("6.3 Instance running", inst["data"]["status"] == "running")

step1 = api("POST", f"/custom/workflows/instances/{inst_id}/step", {
    "action": "approve", "comment": "Manager approved"
}, token)
test("6.4 Step 1 approved", "_err" not in step1 and step1["data"]["next_step"] == 2)

inst2 = api("GET", f"/custom/workflows/instances/{inst_id}", token=token)
test("6.5 Advanced to step 2", inst2["data"]["current_step"] == 2)

step2 = api("POST", f"/custom/workflows/instances/{inst_id}/step", {
    "action": "approve", "comment": "Finance approved"
}, token)
test("6.6 Step 2 approved", "_err" not in step2)

inst3 = api("GET", f"/custom/workflows/instances/{inst_id}", token=token)
test("6.7 Workflow completed", inst3["data"]["status"] == "completed")
test("6.8 Completed timestamp set", inst3["data"]["completed_at"] is not None)
test("6.9 Log has entries", len(inst3["data"]["log"]) >= 2)

# Reject scenario
start2 = api("POST", "/custom/workflows/start", {
    "workflow_id": wf_id, "entity_type": "fleet_vehicle", "entity_id": uuid.uuid4().hex[:8]
}, token)
inst_id2 = start2["data"]["instance_id"]
step_reject = api("POST", f"/custom/workflows/instances/{inst_id2}/step", {
    "action": "reject", "comment": "Over budget"
}, token)
test("6.10 Rejection handled", "_err" not in step_reject)

# Can't decide on non-running
bad_step = api("POST", f"/custom/workflows/instances/{inst_id}/step", {"action": "approve"}, token)
test("6.11 Can't step on completed", "_err" in bad_step)

# Delete workflow
del_wf = api("DELETE", f"/custom/workflows/{wf_id}", token=token)
test("6.12 Workflow deleted", "_err" not in del_wf)

# ═══ 7. STATS ═══
print("\n--- Stats ---")
stats = api("GET", "/custom/stats", token=token)
test("7.1 Stats accessible", "_err" not in stats)
test("7.2 Has custom_fields", "custom_fields" in stats["data"])
test("7.3 Has custom_modules", "custom_modules" in stats["data"])
test("7.4 Has workflows", "workflows" in stats["data"])

# ═══ 8. CLEANUP / DELETE ═══
print("\n--- Cleanup ---")
del_field = api("DELETE", f"/custom/fields/{field_id}", token=token)
test("8.1 Field deleted", "_err" not in del_field)

del_module = api("DELETE", f"/custom/modules/{module_id}", token=token)
test("8.2 Module deleted", "_err" not in del_module)

del_gone = api("GET", f"/custom/modules/{module_id}", token=token)
test("8.3 Deleted module gone", "_err" in del_gone)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P71.5 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
