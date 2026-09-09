import urllib.request, json

# 1. Login
login_data = json.dumps({"email": "admin@demo.com", "password": "admin123"}).encode()
req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", data=login_data,
                             headers={"Content-Type": "application/json"}, method="POST")
r = urllib.request.urlopen(req, timeout=10)
result = json.loads(r.read())
token = result["data"]["access_token"]
user = result["data"]["user"]
print("=== LOGIN SUCCESS ===")
print(f"  User: {user['first_name']} {user['last_name']}")
print(f"  Email: {user['email']}")
print(f"  Tenant: {user['tenant_id']}")
print(f"  Role: {user['role']}")

headers = {"Authorization": f"Bearer {token}"}

# 2. Dashboard
try:
    req2 = urllib.request.Request("http://127.0.0.1:8000/api/v1/analytics/executive?period=this_month", headers=headers)
    r2 = urllib.request.urlopen(req2, timeout=10)
    dash = json.loads(r2.read())
    print("\n=== EXECUTIVE DASHBOARD ===")
    data = dash.get("data", dash)
    if isinstance(data, dict):
        for k, v in list(data.items())[:10]:
            print(f"  {k}: {v}")
except Exception as e:
    print(f"\n  Dashboard: {e}")

# 3. Sales
try:
    req3 = urllib.request.Request("http://127.0.0.1:8000/api/v1/analytics/sales/summary?period=this_month", headers=headers)
    r3 = urllib.request.urlopen(req3, timeout=10)
    sales = json.loads(r3.read())
    print("\n=== SALES SUMMARY ===")
    data = sales.get("data", sales)
    if isinstance(data, dict):
        for k, v in list(data.items())[:8]:
            print(f"  {k}: {v}")
except Exception as e:
    print(f"\n  Sales: {e}")

# 4. Inventory
try:
    req4 = urllib.request.Request("http://127.0.0.1:8000/api/v1/analytics/inventory", headers=headers)
    r4 = urllib.request.urlopen(req4, timeout=10)
    inv = json.loads(r4.read())
    print("\n=== INVENTORY ===")
    data = inv.get("data", inv)
    if isinstance(data, dict):
        for k, v in list(data.items())[:8]:
            print(f"  {k}: {v}")
except Exception as e:
    print(f"\n  Inventory: {e}")

# 5. Projects
try:
    req5 = urllib.request.Request("http://127.0.0.1:8000/api/v1/analytics/projects", headers=headers)
    r5 = urllib.request.urlopen(req5, timeout=10)
    proj = json.loads(r5.read())
    print("\n=== PROJECTS ===")
    data = proj.get("data", proj)
    if isinstance(data, dict):
        for k, v in list(data.items())[:8]:
            print(f"  {k}: {v}")
except Exception as e:
    print(f"\n  Projects: {e}")

# 6. KPIs
try:
    req6 = urllib.request.Request("http://127.0.0.1:8000/api/v1/analytics/kpis?period=this_month", headers=headers)
    r6 = urllib.request.urlopen(req6, timeout=10)
    kpis = json.loads(r6.read())
    print("\n=== KPIs ===")
    data = kpis.get("data", kpis)
    if isinstance(data, list):
        for kpi in data[:5]:
            print(f"  {kpi.get('name', kpi.get('code', '?'))}: {kpi.get('value', kpi.get('current_value', '?'))}")
    elif isinstance(data, dict):
        for k, v in list(data.items())[:8]:
            print(f"  {k}: {v}")
except Exception as e:
    print(f"\n  KPIs: {e}")

# 7. Alerts
try:
    req7 = urllib.request.Request("http://127.0.0.1:8000/api/v1/analytics/alerts", headers=headers)
    r7 = urllib.request.urlopen(req7, timeout=10)
    alerts = json.loads(r7.read())
    print("\n=== ALERTS ===")
    data = alerts.get("data", alerts)
    if isinstance(data, list):
        print(f"  Count: {len(data)}")
        for a in data[:3]:
            print(f"  - {a.get('alert_name', '?')}: {a.get('metric_name', '?')}")
    elif isinstance(data, dict):
        for k, v in list(data.items())[:5]:
            print(f"  {k}: {v}")
except Exception as e:
    print(f"\n  Alerts: {e}")

print("\n=== DONE ===")
