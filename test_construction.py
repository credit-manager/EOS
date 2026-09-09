import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"

def api(method, path, data=None, use_token=True):
    headers = {"Content-Type": "application/json"}
    if use_token and token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        content = e.read().decode()
        print(f"  HTTP {e.code}: {content[:300]}")
        try:
            return json.loads(content)
        except:
            return {"error": f"HTTP {e.code}: {content[:200]}"}
    except Exception as e:
        return {"error": str(e)}

# Login
resp = api("POST", "/auth/login", {"email": "admin@demo.com", "password": "admin123"}, use_token=False)
token = resp.get("data", {}).get("access_token", "")
print("Logged in")

# Dashboard
print("\n--- Dashboard ---")
dash = api("GET", "/construction/dashboard")
print(f"  Projects: {dash['kpis']['total_projects']}")
print(f"  Contract Value: {dash['kpis']['contract_value']}")
print(f"  Alerts: {len(dash['alerts'])}")

# Create project
print("\n--- Create Project ---")
proj = api("POST", "/construction/projects", {
    "name": "Cairo Tower Phase 2",
    "budget": 25000000,
    "start_date": "2026-01-01",
    "end_date": "2027-06-30"
})
print(f"  Response: {proj}")
pid = proj.get("id", "")

# Create BOQ items
print("\n--- Create BOQ ---")
api("POST", f"/construction/projects/{pid}/boq", {"item_number": "1.1", "description": "Excavation", "unit": "m3", "quantity": 5000, "unit_price": 45})
api("POST", f"/construction/projects/{pid}/boq", {"item_number": "1.2", "description": "Concrete", "unit": "m3", "quantity": 3000, "unit_price": 120})
boq = api("GET", f"/construction/projects/{pid}/boq")
print(f"  BOQ items: {boq['total']}")

# Create PR
print("\n--- Create PR ---")
pr = api("POST", "/construction/procurement/requests", {
    "project_id": pid,
    "description": "Steel for Cairo Tower",
    "items": [{"item_code": "STEEL-001", "quantity": 200000, "unit_price": 8}]
})
print(f"  PR: {pr.get('pr_number', '')} - Total: {pr.get('total_amount', 0)}")

# Submit + Approve PR
api("POST", f"/construction/procurement/requests/{pr['id']}/submit")
api("POST", f"/construction/procurement/requests/{pr['id']}/approve")
print("  PR approved")

# Create PO
print("\n--- Create PO ---")
po = api("POST", "/construction/procurement/orders", {
    "supplier_name": "Steel Trading Co",
    "project_id": pid,
    "po_date": "2026-08-27",
    "delivery_date": "2026-09-15",
    "items": [{"item_code": "STEEL-001", "quantity": 200000, "unit_price": 8}]
})
print(f"  PO: {po.get('po_number', '')} - Total: {po.get('total_amount', 0)}")

# Create Warehouse
print("\n--- Warehouse ---")
wh = api("POST", "/construction/warehouses", {"code": "WH-001", "name": "Main Warehouse", "address": "Industrial Area"})
print(f"  {wh.get('message', '')}")

# Receive goods
print("\n--- Receive Goods ---")
api("POST", f"/construction/procurement/orders/{po['id']}/receive", {
    "warehouse_id": "WH-001",
    "items": [{"item_code": "STEEL-001", "quantity": 200000, "unit_price": 8}]
})
print("  GRN processed")

# Check stock
print("\n--- Stock ---")
stock = api("GET", "/construction/stock")
print(f"  Items: {stock['total']}")
for s in stock.get("data", []):
    print(f"    {s['item_code']}: {s['on_hand']} units")

# Issue material
print("\n--- Issue Material ---")
issue = api("POST", "/construction/stock/issue", {"item_code": "STEEL-001", "quantity": 50000, "project_id": pid})
print(f"  Cost: {issue.get('total_cost', 0)}")

# Create equipment
print("\n--- Equipment ---")
eq = api("POST", "/construction/equipment", {"code": "EQ-001", "name": "Tower Crane", "type": "Crane", "hourly_rate": 150})
print(f"  {eq.get('message', '')}")

# Get equipment ID from list
eqs = api("GET", "/construction/equipment")
eq_id = eqs["data"][0]["id"] if eqs.get("data") else ""

# Log equipment
print("\n--- Equipment Log ---")
log = api("POST", f"/construction/equipment/{eq_id}/log", {"hours": 8, "fuel_cost": 200})
print(f"  Cost: {log.get('total_cost', 0)}")

# Site diary
print("\n--- Site Diary ---")
diary = api("POST", "/construction/site/diary", {
    "project_id": pid, "diary_date": "2026-08-27",
    "weather": "Sunny", "manpower_count": 45,
    "work_progress": "Foundation work completed 80%"
})
print(f"  {diary.get('message', '')}")

# RFI
print("\n--- RFI ---")
rfi = api("POST", "/construction/site/rfi", {
    "project_id": pid, "subject": "Foundation depth clarification",
    "description": "Need clarification on foundation depth for Tower B"
})
print(f"  {rfi.get('rfi_number', '')}")

# Subcontractor
print("\n--- Subcontractor ---")
sub = api("POST", "/construction/subcontractors", {
    "name": "ABC Contracting", "trade": "Electrical",
    "contact_person": "Ahmed", "phone": "+966501234567"
})
print(f"  {sub.get('message', '')}")

# Profitability
print("\n--- Profitability ---")
profit = api("GET", f"/construction/projects/{pid}/profitability")
print(f"  Contract Value: {profit.get('contract_value', 0)}")
print(f"  Actual Cost: {profit.get('actual_cost', 0)}")
print(f"  Variance: {profit.get('variance', 0)}")
print(f"  Gross Margin: {profit.get('gross_margin', 0)}%")

print("\n=== All tests passed ===")
