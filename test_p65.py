"""
P65 Advanced Analytics Integration Test
Verifies all P65 components work:
- P65.1: Analytics Engine (KPIs, aggregations, comparisons)
- P65.2: Executive Dashboard
- P65.3: Sales & Purchases Analytics
- P65.4: Financial Reports
- P65.5: Role-Based Dashboards
- P65.6: KPI Engine
- P65.7: Business Alerts Engine
- P65.8: API Router (/api/v1/analytics/*)
- P65.9: Integration with P61/P63/P64
"""

import os
import sys
import json
import time
import socket
import subprocess
import pytest
import httpx

_results = []
_server_proc = None


def _find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_server():
    global _server_proc
    port = _find_free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    for _ in range(15):
        time.sleep(1.0)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2.0) as c:
                r = c.get("/health")
                if r.status_code == 200:
                    break
        except Exception:
            pass
    _server_proc = proc
    return proc, port


def _stop_server():
    global _server_proc
    if _server_proc:
        try:
            _server_proc.terminate()
            _server_proc.wait(timeout=5)
        except Exception:
            _server_proc.kill()
        _server_proc = None


def _record(name, passed):
    global _results
    _results.append((name, passed))
    status = "PASS" if passed else "FAIL"
    print(f"  {'✅' if passed else '❌'} {name} [{status}]")


@pytest.fixture(scope="module")
def client():
    proc, port = _start_server()
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=15.0) as c:
        yield c
    _stop_server()


# Use a test tenant ID
TENANT_ID = "tenant_p65_test"


# ═══════════════════════════════════════════════
# P65.1: Analytics Engine Imports
# ═══════════════════════════════════════════════

def test_p65_1_analytics_engine():
    """P65.1: core/analytics_engine.py imports and functions exist."""
    try:
        from core.analytics_engine import (
            get_executive_summary, get_kpis, get_revenue_trend,
            get_expenses_trend, get_profit_trend, get_cash_flow,
            get_sales_summary, get_sales_by_period, get_top_customers,
            get_purchase_summary, get_top_suppliers,
            get_inventory_summary, get_stock_movements,
            get_project_summary, get_project_cost_breakdown,
            get_hr_summary, get_business_alerts,
            get_dashboard_for_role, drill_down,
            _period_range, _safe_float
        )
        _record("P65.1.1 All analytics functions importable", True)
    except ImportError as e:
        _record(f"P65.1.1 Analytics import: {e}", False)


def test_p65_1_period_range():
    """P65.1: _period_range returns valid date ranges."""
    from core.analytics_engine import _period_range
    from datetime import date

    for period in ["today", "yesterday", "this_week", "last_week",
                    "this_month", "last_month", "this_quarter",
                    "last_quarter", "this_year", "last_year"]:
        start, end = _period_range(period)
        valid = isinstance(start, date) and isinstance(end, date) and start <= end
        _record(f"P65.1.2 period_range('{period}')", valid)


def test_p65_1_safe_float():
    """P65.1: _safe_float handles various inputs."""
    from core.analytics_engine import _safe_float
    _record("P65.1.3 safe_float(None)=0", _safe_float(None) == 0.0)
    _record("P65.1.4 safe_float(42)=42.0", _safe_float(42) == 42.0)
    _record("P65.1.5 safe_float('abc')=0", _safe_float("abc") == 0.0)


# ═══════════════════════════════════════════════
# P65.2-4: API Endpoints (Executive, Sales, Purchases, Inventory, Projects, HR)
# ═══════════════════════════════════════════════

def test_p65_2_executive_api(client):
    """P65.2: /analytics/executive endpoint."""
    r = client.get(f"/api/v1/analytics/executive?tenant_id={TENANT_ID}")
    _record("P65.2.1 /analytics/executive 200", r.status_code == 200)
    data = r.json()
    _record("P65.2.2 /analytics/executive has revenue", "revenue" in data)
    _record("P65.2.3 /analytics/executive has profit", "profit" in data)
    _record("P65.2.4 /analytics/executive has period", "period" in data)


def test_p65_3_kpis_api(client):
    """P65.3: /analytics/kpis endpoint."""
    r = client.get(f"/api/v1/analytics/kpis?tenant_id={TENANT_ID}")
    _record("P65.3.1 /analytics/kpis 200", r.status_code == 200)
    data = r.json()
    _record("P65.3.2 /analytics/kpis has kpis list", "kpis" in data and isinstance(data["kpis"], list))
    if data.get("kpis"):
        _record("P65.3.3 KPI has name/current/change/trend",
                all(k in data["kpis"][0] for k in ["name", "current", "change", "trend"]))


def test_p65_4_trends_api(client):
    """P65.4: Revenue, expenses, profit trends."""
    r = client.get(f"/api/v1/analytics/revenue-trend?tenant_id={TENANT_ID}&months=3")
    _record("P65.4.1 /analytics/revenue-trend 200", r.status_code == 200)
    _record("P65.4.2 revenue-trend has trend", "trend" in r.json())

    r = client.get(f"/api/v1/analytics/expenses-trend?tenant_id={TENANT_ID}&months=3")
    _record("P65.4.3 /analytics/expenses-trend 200", r.status_code == 200)

    r = client.get(f"/api/v1/analytics/profit-trend?tenant_id={TENANT_ID}&months=3")
    _record("P65.4.4 /analytics/profit-trend 200", r.status_code == 200)


def test_p65_5_cash_flow_api(client):
    """P65.5: /analytics/cash-flow endpoint."""
    r = client.get(f"/api/v1/analytics/cash-flow?tenant_id={TENANT_ID}&months=3")
    _record("P65.5.1 /analytics/cash-flow 200", r.status_code == 200)
    _record("P65.5.2 cash-flow has cash_flow", "cash_flow" in r.json())


def test_p65_6_sales_api(client):
    """P65.6: Sales analytics endpoints."""
    r = client.get(f"/api/v1/analytics/sales/summary?tenant_id={TENANT_ID}")
    _record("P65.6.1 /sales/summary 200", r.status_code == 200)
    _record("P65.6.2 sales/summary has total_invoices", "total_invoices" in r.json())

    r = client.get(f"/api/v1/analytics/sales/periods?tenant_id={TENANT_ID}")
    _record("P65.6.3 /sales/periods 200", r.status_code == 200)
    _record("P65.6.4 sales/periods has changes", "changes" in r.json())

    r = client.get(f"/api/v1/analytics/sales/top-customers?tenant_id={TENANT_ID}")
    _record("P65.6.5 /sales/top-customers 200", r.status_code == 200)
    _record("P65.6.6 top-customers has customers", "customers" in r.json())


def test_p65_7_purchases_api(client):
    """P65.7: Purchase analytics endpoints."""
    r = client.get(f"/api/v1/analytics/purchases/summary?tenant_id={TENANT_ID}")
    _record("P65.7.1 /purchases/summary 200", r.status_code == 200)
    _record("P65.7.2 purchases/summary has total_orders", "total_orders" in r.json())

    r = client.get(f"/api/v1/analytics/purchases/top-suppliers?tenant_id={TENANT_ID}")
    _record("P65.7.3 /purchases/top-suppliers 200", r.status_code == 200)
    _record("P65.7.4 top-suppliers has suppliers", "suppliers" in r.json())


def test_p65_8_inventory_api(client):
    """P65.8: Inventory analytics endpoints."""
    r = client.get(f"/api/v1/analytics/inventory?tenant_id={TENANT_ID}")
    _record("P65.8.1 /analytics/inventory 200", r.status_code == 200)
    data = r.json()
    _record("P65.8.2 inventory has total_items", "total_items" in data)
    _record("P65.8.3 inventory has total_stock_value", "total_stock_value" in data)
    _record("P65.8.4 inventory has low_stock_items", "low_stock_items" in data)

    r = client.get(f"/api/v1/analytics/inventory/movements?tenant_id={TENANT_ID}&days=30")
    _record("P65.8.5 /inventory/movements 200", r.status_code == 200)
    _record("P65.8.6 movements has movements", "movements" in r.json())


def test_p65_9_projects_api(client):
    """P65.9: Project analytics endpoints."""
    r = client.get(f"/api/v1/analytics/projects?tenant_id={TENANT_ID}")
    _record("P65.9.1 /analytics/projects 200", r.status_code == 200)
    data = r.json()
    _record("P65.9.2 projects has active", "active" in data)
    _record("P65.9.3 projects has total_budget", "total_budget" in data)
    _record("P65.9.4 projects has budget_utilization", "budget_utilization" in data)

    r = client.get(f"/api/v1/analytics/projects/costs?tenant_id={TENANT_ID}")
    _record("P65.9.5 /projects/costs 200", r.status_code == 200)
    _record("P65.9.6 projects/costs has projects", "projects" in r.json())


def test_p65_10_hr_api(client):
    """P65.10: HR analytics endpoint."""
    r = client.get(f"/api/v1/analytics/hr?tenant_id={TENANT_ID}")
    _record("P65.10.1 /analytics/hr 200", r.status_code == 200)
    data = r.json()
    _record("P65.10.2 hr has total_employees", "total_employees" in data)
    _record("P65.10.3 hr has total_payroll", "total_payroll" in data)


# ═══════════════════════════════════════════════
# P65.11: Role-Based Dashboards
# ═══════════════════════════════════════════════

def test_p65_11_role_dashboards(client):
    """P65.11: Role-based dashboard endpoints."""
    for role in ["owner", "ceo", "admin", "finance", "project_manager", "procurement", "warehouse"]:
        r = client.get(f"/api/v1/analytics/dashboard/{role}?tenant_id={TENANT_ID}")
        _record(f"P65.11.{ord(role[0]) % 10} /dashboard/{role} 200", r.status_code == 200)
        data = r.json()
        _record(f"P65.11.{ord(role[0]) % 10 + 1} dashboard has role={role}", data.get("role") == role)

    # Invalid role
    r = client.get(f"/api/v1/analytics/dashboard/invalid_role?tenant_id={TENANT_ID}")
    _record("P65.11.3 Invalid role returns 400", r.status_code == 400)


# ═══════════════════════════════════════════════
# P65.12: Business Alerts
# ═══════════════════════════════════════════════

def test_p65_12_business_alerts(client):
    """P65.12: Business alerts endpoint."""
    r = client.get(f"/api/v1/analytics/alerts?tenant_id={TENANT_ID}")
    _record("P65.12.1 /analytics/alerts 200", r.status_code == 200)
    data = r.json()
    _record("P65.12.2 alerts has alerts list", "alerts" in data and isinstance(data["alerts"], list))
    if data["alerts"]:
        alert = data["alerts"][0]
        _record("P65.12.3 Alert has type/category/title/message",
                all(k in alert for k in ["type", "category", "title", "message"]))


# ═══════════════════════════════════════════════
# P65.13: Drill-Down
# ═══════════════════════════════════════════════

def test_p65_13_drill_down(client):
    """P65.13: Drill-down endpoint."""
    # Invalid entity type
    r = client.get(f"/api/v1/analytics/drill-down/invalid/123?tenant_id={TENANT_ID}")
    _record("P65.13.1 Invalid entity type returns 400", r.status_code == 400)

    # Non-existent entity
    r = client.get(f"/api/v1/analytics/drill-down/invoice/99999?tenant_id={TENANT_ID}")
    _record("P65.13.2 Non-existent entity returns 404", r.status_code == 404)


# ═══════════════════════════════════════════════
# P65.14: Full Dashboard Data Structures
# ═══════════════════════════════════════════════

def test_p65_14_dashboard_structures(client):
    """P65.14: Dashboard data has expected structure for each role."""
    # Owner/CEO should have most data
    r = client.get(f"/api/v1/analytics/dashboard/owner?tenant_id={TENANT_ID}")
    data = r.json()
    owner_fields = ["summary", "kpis", "revenue_trend", "profit_trend",
                    "top_customers", "top_suppliers", "project_summary", "hr_summary"]
    has_all = all(f in data for f in owner_fields)
    _record("P65.14.1 Owner dashboard has all fields", has_all)

    # Finance should have cash flow
    r = client.get(f"/api/v1/analytics/dashboard/finance?tenant_id={TENANT_ID}")
    data = r.json()
    finance_fields = ["summary", "kpis", "revenue_trend", "expenses_trend",
                      "cash_flow", "sales_by_period", "receivables", "payables"]
    has_all = all(f in data for f in finance_fields)
    _record("P65.14.2 Finance dashboard has all fields", has_all)

    # Warehouse should have inventory
    r = client.get(f"/api/v1/analytics/dashboard/warehouse?tenant_id={TENANT_ID}")
    data = r.json()
    _record("P65.14.3 Warehouse dashboard has inventory", "inventory" in data)


# ═══════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    _results = []

    print("=" * 60)
    print("  P65 ADVANCED ANALYTICS TEST")
    print("=" * 60)

    proc, port = _start_server()
    base_url = f"http://127.0.0.1:{port}"

    try:
        with httpx.Client(base_url=base_url, timeout=15.0) as client:
            print("\n--- P65.1: Analytics Engine ---")
            test_p65_1_analytics_engine()
            test_p65_1_period_range()
            test_p65_1_safe_float()

            print("\n--- P65.2: Executive Dashboard ---")
            test_p65_2_executive_api(client)

            print("\n--- P65.3: KPIs ---")
            test_p65_3_kpis_api(client)

            print("\n--- P65.4: Trends ---")
            test_p65_4_trends_api(client)

            print("\n--- P65.5: Cash Flow ---")
            test_p65_5_cash_flow_api(client)

            print("\n--- P65.6: Sales ---")
            test_p65_6_sales_api(client)

            print("\n--- P65.7: Purchases ---")
            test_p65_7_purchases_api(client)

            print("\n--- P65.8: Inventory ---")
            test_p65_8_inventory_api(client)

            print("\n--- P65.9: Projects ---")
            test_p65_9_projects_api(client)

            print("\n--- P65.10: HR ---")
            test_p65_10_hr_api(client)

            print("\n--- P65.11: Role Dashboards ---")
            test_p65_11_role_dashboards(client)

            print("\n--- P65.12: Business Alerts ---")
            test_p65_12_business_alerts(client)

            print("\n--- P65.13: Drill-Down ---")
            test_p65_13_drill_down(client)

            print("\n--- P65.14: Dashboard Structures ---")
            test_p65_14_dashboard_structures(client)

    finally:
        _stop_server()

    passed = sum(1 for _, p in _results if p)
    total = len(_results)
    failed = total - passed

    print("\n" + "=" * 60)
    print(f"  P65 RESULTS: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 60)

    if failed > 0:
        print("\nFailed tests:")
        for name, p in _results:
            if not p:
                print(f"  ❌ {name}")

    sys.exit(0 if failed == 0 else 1)