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

print("=== P70.9 Services ERP Tests ===\n")

# ═══ 1. CRM: CLIENTS ═══
print("--- CRM: Clients ---")
client = api("POST", "/services/clients", {
    "client_code": f"CLI-{_rid}", "name": f"Acme Corp-{_rid}",
    "industry": "technology", "email": f"info@acme-{_rid}.com",
    "phone": "+966501234567", "credit_limit": 100000
}, token)
test("1.1 Client created", "_err" not in client and "id" in client.get("data", {}))
client_id = client["data"]["id"]

clients = api("GET", "/services/clients", token=token)
test("1.2 Clients listable", "_err" not in clients)

detail = api("GET", f"/services/clients/{client_id}", token=token)
test("1.3 Client detail", "_err" not in detail and detail["data"]["name"].startswith("Acme"))

# ═══ 2. CRM: LEADS ═══
print("\n--- CRM: Leads ---")
lead = api("POST", "/services/leads", {
    "company_name": f"TechStart-{_rid}", "contact_name": "Ahmed",
    "email": f"ahmed@techstart-{_rid}.com", "source": "website", "estimated_value": 50000
}, token)
test("2.1 Lead created", "_err" not in lead and "id" in lead.get("data", {}))
lead_id = lead["data"]["id"]

leads = api("GET", "/services/leads", token=token)
test("2.2 Leads listable", "_err" not in leads)

convert = api("PUT", f"/services/leads/{lead_id}/convert", token=token)
test("2.3 Lead converted", "_err" not in convert and "client_id" in convert.get("data", {}))

# ═══ 3. CRM: OPPORTUNITIES ═══
print("\n--- CRM: Opportunities ---")
opp = api("POST", "/services/opportunities", {
    "client_id": client_id, "name": f"Enterprise Deal-{_rid}",
    "stage": "qualification", "probability": 60, "expected_value": 200000
}, token)
test("3.1 Opportunity created", "_err" not in opp and "id" in opp.get("data", {}))
opp_id = opp["data"]["id"]

opps = api("GET", "/services/opportunities", token=token)
test("3.2 Opportunities listable", "_err" not in opps)

stage = api("PUT", f"/services/opportunities/{opp_id}/stage?stage=proposal", token=token)
test("3.3 Stage updated", "_err" not in stage)

# Invalid stage
bad_stage = api("PUT", f"/services/opportunities/{opp_id}/stage?stage=invalid", token=token)
test("3.4 Invalid stage rejected", "_err" in bad_stage)

# ═══ 4. QUOTATIONS ═══
print("\n--- Quotations ---")
quote = api("POST", "/services/quotations", {
    "client_id": client_id, "opportunity_id": opp_id,
    "title": f"Project Quote-{_rid}", "valid_until": "2026-12-31",
    "lines": [
        {"description": "Web Development", "quantity": 100, "unit_price": 150},
        {"description": "UI/UX Design", "quantity": 50, "unit_price": 120},
    ]
}, token)
test("4.1 Quotation created", "_err" not in quote and "id" in quote.get("data", {}))
quote_id = quote["data"]["id"]
test("4.2 Grand total includes tax", quote["data"]["grand_total"] > 0)

quotes = api("GET", "/services/quotations", token=token)
test("4.3 Quotations listable", "_err" not in quotes)

# ═══ 5. CONTRACTS ═══
print("\n--- Contracts ---")
contract = api("POST", "/services/contracts", {
    "client_id": client_id, "title": f"Service Contract-{_rid}",
    "contract_type": "time_material", "value": 120000,
    "start_date": "2026-09-01", "end_date": "2027-08-31"
}, token)
test("5.1 Contract created", "_err" not in contract and "id" in contract.get("data", {}))
contract_id = contract["data"]["id"]

contracts = api("GET", "/services/contracts", token=token)
test("5.2 Contracts listable", "_err" not in contracts)

# ═══ 6. PROJECTS ═══
print("\n--- Projects ---")
project = api("POST", "/services/projects", {
    "name": f"ERP Implementation-{_rid}", "client_id": client_id,
    "contract_id": contract_id, "project_type": "time_material",
    "budget": 80000, "start_date": "2026-09-01", "end_date": "2027-02-28"
}, token)
test("6.1 Project created", "_err" not in project and "id" in project.get("data", {}))
project_id = project["data"]["id"]

projects = api("GET", "/services/projects", token=token)
test("6.2 Projects listable", "_err" not in projects)

status = api("PUT", f"/services/projects/{project_id}/status?status=active", token=token)
test("6.3 Project activated", "_err" not in status)

# ═══ 7. TASKS ═══
print("\n--- Tasks ---")
task1 = api("POST", "/services/tasks", {
    "project_id": project_id, "name": "Requirements Gathering",
    "estimated_hours": 40, "task_type": "task"
}, token)
test("7.1 Task 1 created", "_err" not in task1 and "id" in task1.get("data", {}))

task2 = api("POST", "/services/tasks", {
    "project_id": project_id, "name": "System Design",
    "estimated_hours": 60, "task_type": "task"
}, token)
test("7.2 Task 2 created", "_err" not in task2)

tasks = api("GET", f"/services/tasks/{project_id}", token=token)
test("7.3 Tasks listable", "_err" not in tasks and len(tasks.get("data", [])) >= 2)

task_status = api("PUT", f"/services/tasks/{task1['data']['id']}/status?status=in_progress", token=token)
test("7.4 Task status updated", "_err" not in task_status)

# ═══ 8. MILESTONES ═══
print("\n--- Milestones ---")
ms = api("POST", "/services/milestones", {
    "project_id": project_id, "name": "Phase 1 Complete",
    "due_date": "2026-10-31", "amount": 30000
}, token)
test("8.1 Milestone created", "_err" not in ms and "id" in ms.get("data", {}))

milestones = api("GET", f"/services/milestones/{project_id}", token=token)
test("8.2 Milestones listable", "_err" not in milestones)

# ═══ 9. SKILLS ═══
print("\n--- Skills ---")
skill = api("POST", "/services/skills?name=Python&category=Development", token=token)
test("9.1 Skill created", "_err" not in skill and "id" in skill.get("data", {}))

skills = api("GET", "/services/skills", token=token)
test("9.2 Skills listable", "_err" not in skills)

# ═══ 10. ALLOCATIONS ═══
print("\n--- Resource Allocations ---")
emp_id = uuid.uuid4().hex[:8]
alloc = api("POST", "/services/allocations", {
    "employee_id": emp_id,
    "project_id": project_id, "allocation_pct": 80,
    "start_date": "2026-09-01", "end_date": "2026-12-31"
}, token)
test("10.1 Allocation created", "_err" not in alloc and "id" in alloc.get("data", {}))

allocs = api("GET", "/services/allocations", token=token)
test("10.2 Allocations listable", "_err" not in allocs)

# ═══ 11. TIMESHEETS ═══
print("\n--- Timesheets ---")
ts = api("POST", "/services/timesheets", {
    "employee_id": emp_id, "week_start": "2026-09-01", "week_end": "2026-09-07",
    "lines": [
        {"project_id": project_id, "work_date": "2026-09-01", "hours": 8, "billable": True, "description": "Requirements"},
        {"project_id": project_id, "work_date": "2026-09-02", "hours": 6, "billable": True, "description": "Design"},
        {"project_id": project_id, "work_date": "2026-09-03", "hours": 4, "billable": False, "description": "Internal meeting"},
    ]
}, token)
test("11.1 Timesheet created", "_err" not in ts and "id" in ts.get("data", {}))
ts_id = ts["data"]["id"]
test("11.2 Total hours calculated", ts["data"]["total_hours"] == 18)

ts_submit = api("PUT", f"/services/timesheets/{ts_id}/submit", token=token)
test("11.3 Timesheet submitted", "_err" not in ts_submit)

ts_approve = api("PUT", f"/services/timesheets/{ts_id}/approve", token=token)
test("11.4 Timesheet approved", "_err" not in ts_approve)

# Can't approve again
bad_approve = api("PUT", f"/services/timesheets/{ts_id}/approve", token=token)
test("11.5 Double approve rejected", "_err" in bad_approve)

tsheets = api("GET", "/services/timesheets", token=token)
test("11.6 Timesheets listable", "_err" not in tsheets)

# ═══ 12. EXPENSES ═══
print("\n--- Expenses ---")
exp = api("POST", "/services/expenses", {
    "employee_id": emp_id, "project_id": project_id,
    "category": "travel", "amount": 500, "expense_date": "2026-09-02",
    "description": "Flight to client site"
}, token)
test("12.1 Expense created", "_err" not in exp and "id" in exp.get("data", {}))
exp_id = exp["data"]["id"]

exp_approve = api("PUT", f"/services/expenses/{exp_id}/approve", token=token)
test("12.2 Expense approved", "_err" not in exp_approve)

exps = api("GET", "/services/expenses", token=token)
test("12.3 Expenses listable", "_err" not in exps)

# ═══ 13. INVOICES ═══
print("\n--- Service Invoices ---")
inv = api("POST", "/services/invoices", {
    "client_id": client_id, "project_id": project_id,
    "invoice_type": "time_material", "due_date": "2026-10-15",
    "lines": [
        {"description": "Web Development - 100 hrs", "quantity": 100, "unit_price": 150},
        {"description": "UI/UX Design - 50 hrs", "quantity": 50, "unit_price": 120},
        {"description": "Travel Expenses", "quantity": 1, "unit_price": 500},
    ]
}, token)
test("13.1 Invoice created", "_err" not in inv and "id" in inv.get("data", {}))
inv_id = inv["data"]["id"]
test("13.2 Invoice total > 0", inv["data"]["total"] > 0)

inv_send = api("PUT", f"/services/invoices/{inv_id}/send", token=token)
test("13.3 Invoice sent", "_err" not in inv_send)

inv_pay = api("PUT", f"/services/invoices/{inv_id}/pay?amount=10000", token=token)
test("13.4 Partial payment", "_err" not in inv_pay and inv_pay["data"]["status"] == "sent")

inv_pay2 = api("PUT", f"/services/invoices/{inv_id}/pay?amount=20000", token=token)
test("13.5 Full payment", "_err" not in inv_pay2 and inv_pay2["data"]["status"] == "paid")

invs = api("GET", "/services/invoices", token=token)
test("13.6 Invoices listable", "_err" not in invs)

# ═══ 14. PROFITABILITY ═══
print("\n--- Profitability ---")
prof = api("GET", f"/services/profitability/{project_id}", token=token)
test("14.1 Profitability calculated", "_err" not in prof and "revenue" in prof.get("data", {}))

# ═══ 15. DASHBOARD ═══
print("\n--- Dashboard ---")
dash = api("GET", "/services/dashboard", token=token)
test("15.1 Dashboard accessible", "_err" not in dash)
d = dash.get("data", {})
test("15.2 CRM stats", "crm" in d and "active_clients" in d["crm"])
test("15.3 Project stats", "projects" in d and "active" in d["projects"])
test("15.4 Invoicing stats", "invoicing" in d and "outstanding" in d["invoicing"])

# ═══ 16. TENANT ISOLATION ═══
print("\n--- Tenant Isolation ---")
c = api("GET", "/services/clients", token=token)
test("16.1 Clients filtered", "_err" not in c)
p = api("GET", "/services/projects", token=token)
test("16.2 Projects filtered", "_err" not in p)

# ═══ 17. ACCOUNTING ═══
print("\n--- Accounting ---")
journal = api("GET", "/api/v1/accounting/journal", token=token)
test("17.1 Journal entries exist", "_err" not in journal)

# ═══ RESULTS ═══
print(f"\n{'='*50}")
print(f"P70.9 Results: {passed} passed, {failed} failed, {total} total")
if failed == 0:
    print("=== ALL TESTS PASSED ===")
else:
    print(f"=== {failed} TESTS FAILED ===")
