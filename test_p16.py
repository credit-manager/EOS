"""
P16 DASHBOARD / ANALYTICS TESTS
=================================
Tests analytics engine, aggregations, GROUP BY, KPIs,
dashboards, widgets, tenant isolation, security.
"""
import httpx
import subprocess
import sys
import time
import os
sys.path.insert(0, '.')

from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"

TOKEN_A = create_test_token("tenant_a", user_id="admin", email="admin@test.com",
                             roles=["admin"])
TOKEN_V = create_test_token("tenant_a", user_id="viewer", email="viewer@test.com",
                             roles=["dynamic_viewer"])
TOKEN_B = create_test_token("tenant_b", user_id="admin_b", email="adminb@test.com",
                             roles=["admin"])

HEADERS_A = {"Authorization": f"Bearer {TOKEN_A}"}
HEADERS_V = {"Authorization": f"Bearer {TOKEN_V}"}
HEADERS_B = {"Authorization": f"Bearer {TOKEN_B}"}

passed = 0
failed = 0


def test(name, got, expected):
    global passed, failed
    ok = got == expected
    if not ok:
        failed += 1
        print(f"  FAIL - {name}: got {got!r}, expected {expected!r}")
    else:
        passed += 1


def start_server():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env
    )
    time.sleep(5)
    return proc


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ═══════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════

def setup_entities():
    from database import SessionLocal
    from sqlalchemy import text as sa_text
    from models import DBPEntity, DBPField

    db = SessionLocal()
    try:
        for code in ('p16_orders',):
            db.execute(sa_text(f"DELETE FROM dbp_fields WHERE entity_id IN "
                               f"(SELECT id FROM dbp_entities WHERE code = '{code}')"))
            db.execute(sa_text(f"DELETE FROM dbp_entities WHERE code = '{code}'"))
            db.execute(sa_text(f"DROP TABLE IF EXISTS {code}"))
        db.execute(sa_text("DELETE FROM dbp_dashboard_widgets"))
        db.execute(sa_text("DELETE FROM dbp_dashboards"))
        db.execute(sa_text("DELETE FROM dbp_kpis"))
        db.commit()

        # Physical table with data
        db.execute(sa_text("""
            CREATE TABLE p16_orders (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                customer VARCHAR(255),
                status VARCHAR(50),
                amount NUMERIC,
                quantity INTEGER,
                order_date DATE
            )
        """))

        # Insert test data — tenant_a
        for i in range(10):
            db.execute(sa_text(
                "INSERT INTO p16_orders "
                "(id, tenant_id, customer, status, amount, quantity, order_date) "
                f"VALUES ('ord-{i:03d}', 'tenant_a', 'Customer{i}', "
                f"'{'paid' if i % 3 == 0 else 'pending'}', "
                f"{100 + i * 50}, {i + 1}, '2026-01-15'::date + interval '{i} days')"
            ))

        # tenant_b data
        for i in range(5):
            db.execute(sa_text(
                "INSERT INTO p16_orders "
                "(id, tenant_id, customer, status, amount, quantity, order_date) "
                f"VALUES ('ord-b{i:03d}', 'tenant_b', 'B-Customer{i}', "
                f"'paid', {200 + i * 100}, {i + 1}, '2026-02-01'::date + interval '{i} days')"
            ))
        db.commit()

        # Entity metadata
        emp = DBPEntity(code="p16_orders", name_en="Orders", name_ar="طلبات",
                        faculty="sales", table_mapping="p16_orders")
        db.add(emp)
        db.flush()
        db.add_all([
            DBPField(entity_id=emp.id, code="customer", label_en="Customer",
                     field_type="string"),
            DBPField(entity_id=emp.id, code="status", label_en="Status",
                     field_type="string"),
            DBPField(entity_id=emp.id, code="amount", label_en="Amount",
                     field_type="currency"),
            DBPField(entity_id=emp.id, code="quantity", label_en="Quantity",
                     field_type="number"),
            DBPField(entity_id=emp.id, code="order_date", label_en="Order Date",
                     field_type="date"),
        ])
        db.commit()
        print("  Setup: p16_orders entity + 15 records (10 tenant_a, 5 tenant_b)")
    except Exception as e:
        db.rollback()
        print(f"  Setup error: {e}")
        raise
    finally:
        db.close()


# ═══════════════════════════════════════════════════════
# TEST SECTIONS
# ═══════════════════════════════════════════════════════

def test_count_aggregation(client):
    """Section 1: COUNT aggregation"""
    print("\n--- 1. COUNT Aggregation ---")

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "COUNT",
    })
    test("COUNT -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Aggregation is COUNT", data["aggregation"], "COUNT")
    test("Count = 10 (tenant_a)", data["results"]["value"], 10.0)


def test_sum_aggregation(client):
    """Section 2: SUM aggregation"""
    print("\n--- 2. SUM Aggregation ---")

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "SUM",
        "column_name": "amount",
    })
    test("SUM -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Aggregation is SUM", data["aggregation"], "SUM")
    test("Sum value > 0", data["results"]["value"] > 0, True)


def test_avg_min_max(client):
    """Section 3: AVG, MIN, MAX"""
    print("\n--- 3. AVG / MIN / MAX ---")

    for agg in ("AVG", "MIN", "MAX"):
        r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
            "entity_code": "p16_orders",
            "aggregation": agg,
            "column_name": "amount",
        })
        test(f"{agg} -> 200", r.status_code, 200)
        test(f"{agg} has value", "value" in r.json()["data"]["results"], True)


def test_group_by(client):
    """Section 4: GROUP BY"""
    print("\n--- 4. GROUP BY ---")

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "COUNT",
        "group_by": "status",
    })
    test("GROUP BY status -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Has results list", isinstance(data["results"], list), True)
    test("Has groups", len(data["results"]) > 0, True)

    groups = {r["group_key"]: r["value"] for r in data["results"]}
    test("Has 'paid' group", "paid" in groups, True)
    test("Has 'pending' group", "pending" in groups, True)
    test("Paid count = 4", groups.get("paid", 0), 4.0)
    test("Pending count = 6", groups.get("pending", 0), 6.0)


def test_filters(client):
    """Section 5: Filtered aggregation"""
    print("\n--- 5. Filters ---")

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "COUNT",
        "filters": [{"field": "status", "op": "eq", "value": "paid"}],
    })
    test("Filter by status -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Paid orders = 4", data["results"]["value"], 4.0)

    # Multiple filters
    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "SUM",
        "column_name": "amount",
        "filters": [
            {"field": "status", "op": "eq", "value": "paid"},
            {"field": "amount", "op": "gt", "value": 200},
        ],
    })
    test("Multi-filter -> 200", r.status_code, 200)
    test("Sum value > 0", r.json()["data"]["results"]["value"] > 0, True)


def test_date_range(client):
    """Section 6: Date range filtering"""
    print("\n--- 6. Date Range ---")

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "COUNT",
        "date_field": "order_date",
        "date_range": "90d",
    })
    test("Date range 90d -> 200", r.status_code, 200)


def test_security_invalid_entity(client):
    """Section 7: Security — invalid entity"""
    print("\n--- 7. Security ---")

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "nonexistent_entity",
        "aggregation": "COUNT",
    })
    test("Invalid entity -> 400", r.status_code, 400)

    # Invalid column
    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "SUM",
        "column_name": "password",
    })
    test("Blocked column -> 400", r.status_code, 400)

    # Invalid aggregation
    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "DROP",
    })
    test("Invalid aggregation -> 400", r.status_code, 400)

    # Invalid filter field
    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "COUNT",
        "filters": [{"field": "tenant_id", "op": "eq", "value": "x"}],
    })
    test("Blocked filter field -> 400", r.status_code, 400)


def test_tenant_isolation(client):
    """Section 8: Tenant isolation"""
    print("\n--- 8. Tenant Isolation ---")

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "COUNT",
    })
    test("Tenant A count = 10", r.json()["data"]["results"]["value"], 10.0)

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_B, json={
        "entity_code": "p16_orders",
        "aggregation": "COUNT",
    })
    test("Tenant B count = 5", r.json()["data"]["results"]["value"], 5.0)


def test_dashboard_crud(client):
    """Section 9: Dashboard CRUD"""
    print("\n--- 9. Dashboard CRUD ---")

    # Create
    r = client.post(f"{EP}/dashboards", headers=HEADERS_A, json={
        "code": "sales_overview",
        "name_en": "Sales Overview",
        "name_ar": "نظرة عامة على المبيعات",
        "description": "Main sales dashboard",
    })
    test("Create dashboard -> 200", r.status_code, 200)
    dash_id = r.json()["data"]["id"]

    # List
    r = client.get(f"{EP}/dashboards", headers=HEADERS_A)
    test("List dashboards -> 200", r.status_code, 200)
    test("Has dashboard", len(r.json()["data"]) > 0, True)

    # Get (empty widgets)
    r = client.get(f"{EP}/dashboards/{dash_id}", headers=HEADERS_A)
    test("Get dashboard -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Dashboard code", data["dashboard"]["code"], "sales_overview")
    test("Has widgets list", isinstance(data["widgets"], list), True)

    # Duplicate code
    r = client.post(f"{EP}/dashboards", headers=HEADERS_A, json={
        "code": "sales_overview", "name_en": "Dup",
    })
    test("Duplicate code -> 400", r.status_code, 400)

    return dash_id


def test_widget_crud(client, dash_id):
    """Section 10: Widget CRUD"""
    print("\n--- 10. Widget CRUD ---")

    # Add KPI widget
    r = client.post(f"{EP}/dashboards/{dash_id}/widgets", headers=HEADERS_A, json={
        "code": "total_orders",
        "widget_type": "kpi",
        "title": "Total Orders",
        "entity_code": "p16_orders",
        "query_config": {"aggregation": "COUNT"},
    })
    test("Create KPI widget -> 200", r.status_code, 200)
    kpi_widget_id = r.json()["data"]["id"]

    # Add bar chart widget
    r = client.post(f"{EP}/dashboards/{dash_id}/widgets", headers=HEADERS_A, json={
        "code": "orders_by_status",
        "widget_type": "bar_chart",
        "title": "Orders by Status",
        "entity_code": "p16_orders",
        "query_config": {
            "aggregation": "COUNT",
            "group_by": "status",
        },
    })
    test("Create bar chart widget -> 200", r.status_code, 200)

    # Add SUM widget
    r = client.post(f"{EP}/dashboards/{dash_id}/widgets", headers=HEADERS_A, json={
        "code": "total_revenue",
        "widget_type": "kpi",
        "title": "Total Revenue",
        "entity_code": "p16_orders",
        "query_config": {"aggregation": "SUM", "column_name": "amount"},
    })
    test("Create SUM widget -> 200", r.status_code, 200)

    # List widgets
    r = client.get(f"{EP}/dashboards/{dash_id}/widgets", headers=HEADERS_A)
    test("List widgets -> 200", r.status_code, 200)
    test("Has 3 widgets", len(r.json()["data"]), 3)

    # Get dashboard with widget data
    r = client.get(f"{EP}/dashboards/{dash_id}", headers=HEADERS_A)
    test("Get dashboard -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Dashboard has widgets", len(data["widgets"]), 3)

    # First widget has data
    w0 = data["widgets"][0]
    test("Widget has data", "data" in w0, True)
    test("Widget has widget_type", "widget_type" in w0, True)

    return kpi_widget_id


def test_dashboard_execution(client, dash_id):
    """Section 11: Dashboard execution with data"""
    print("\n--- 11. Dashboard Execution ---")

    r = client.get(f"{EP}/dashboards/{dash_id}", headers=HEADERS_A)
    test("Execute dashboard -> 200", r.status_code, 200)
    data = r.json()["data"]

    for w in data["widgets"]:
        test(f"Widget '{w['code']}' has data", "data" in w, True)
        if w["widget_type"] == "kpi":
            test(f"KPI '{w['code']}' has value",
                 "value" in w["data"].get("results", {}), True)


def test_kpi_crud(client):
    """Section 12: KPI CRUD + Execution"""
    print("\n--- 12. KPI CRUD ---")

    # Create
    r = client.post(f"{EP}/kpis", headers=HEADERS_A, json={
        "code": "total_paid",
        "name_en": "Total Paid Orders",
        "entity_code": "p16_orders",
        "aggregation": "COUNT",
        "filters": [{"field": "status", "op": "eq", "value": "paid"}],
    })
    test("Create KPI -> 200", r.status_code, 200)
    kpi_id = r.json()["data"]["id"]

    # Execute
    r = client.get(f"{EP}/kpis/{kpi_id}/execute", headers=HEADERS_A)
    test("Execute KPI -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("KPI value = 4", data["results"]["value"], 4.0)
    test("KPI format_type", data["format_type"], "number")

    # List
    r = client.get(f"{EP}/kpis", headers=HEADERS_A)
    test("List KPIs -> 200", r.status_code, 200)
    test("Has KPI", len(r.json()["data"]) > 0, True)

    # SUM KPI
    r = client.post(f"{EP}/kpis", headers=HEADERS_A, json={
        "code": "avg_order",
        "name_en": "Average Order Value",
        "entity_code": "p16_orders",
        "aggregation": "AVG",
        "column_name": "amount",
    })
    test("Create AVG KPI -> 200", r.status_code, 200)
    avg_id = r.json()["data"]["id"]

    r = client.get(f"{EP}/kpis/{avg_id}/execute", headers=HEADERS_A)
    test("Execute AVG KPI -> 200", r.status_code, 200)
    test("AVG has value", r.json()["data"]["results"]["value"] > 0, True)

    # Invalid aggregation
    r = client.post(f"{EP}/kpis", headers=HEADERS_A, json={
        "code": "bad", "name_en": "Bad", "entity_code": "p16_orders",
        "aggregation": "INVALID",
    })
    test("Invalid KPI aggregation -> 400", r.status_code, 400)

    return kpi_id


def test_delete_cascade(client, dash_id):
    """Section 13: Delete cascade"""
    print("\n--- 13. Delete Cascade ---")

    # Delete dashboard should cascade widgets
    r = client.delete(f"{EP}/dashboards/{dash_id}", headers=HEADERS_A)
    test("Delete dashboard -> 200", r.status_code, 200)

    # Verify gone
    r = client.get(f"{EP}/dashboards/{dash_id}", headers=HEADERS_A)
    test("Deleted dashboard -> 404", r.status_code, 404)


def test_rbac(client):
    """Section 14: RBAC"""
    print("\n--- 14. RBAC ---")

    # Viewer can read
    r = client.get(f"{EP}/dashboards", headers=HEADERS_V)
    test("Viewer list dashboards -> 200", r.status_code, 200)

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_V, json={
        "entity_code": "p16_orders", "aggregation": "COUNT",
    })
    test("Viewer aggregate -> 200", r.status_code, 200)

    # No auth
    r = client.post(f"{EP}/analytics/aggregate", json={
        "entity_code": "p16_orders", "aggregation": "COUNT",
    })
    test("No auth -> 401", r.status_code, 401)


def test_group_by_with_filter(client):
    """Section 15: GROUP BY + filters combined"""
    print("\n--- 15. GROUP BY + Filters ---")

    r = client.post(f"{EP}/analytics/aggregate", headers=HEADERS_A, json={
        "entity_code": "p16_orders",
        "aggregation": "SUM",
        "column_name": "amount",
        "group_by": "status",
        "filters": [{"field": "amount", "op": "gt", "value": 150}],
    })
    test("GROUP BY + filter -> 200", r.status_code, 200)
    data = r.json()["data"]
    test("Has grouped results", isinstance(data["results"], list), True)

    for r_item in data["results"]:
        test(f"Group '{r_item['group_key']}' has value",
             r_item["value"] > 0, True)


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("P16 DASHBOARD / ANALYTICS TESTS")
    print("=" * 60)

    print("\nSetup: Creating test entities...")
    setup_entities()

    print("Starting server...")
    proc = start_server()
    client = httpx.Client(base_url=BASE, timeout=30)

    try:
        test_count_aggregation(client)
        test_sum_aggregation(client)
        test_avg_min_max(client)
        test_group_by(client)
        test_filters(client)
        test_date_range(client)
        test_security_invalid_entity(client)
        test_tenant_isolation(client)
        dash_id = test_dashboard_crud(client)
        kpi_widget_id = test_widget_crud(client, dash_id)
        test_dashboard_execution(client, dash_id)
        test_kpi_crud(client)
        test_delete_cascade(client, dash_id)
        test_rbac(client)
        test_group_by_with_filter(client)
    finally:
        client.close()
        stop_server(proc)

    print("\n" + "=" * 60)
    print(f"P16 RESULTS: {passed}/{passed + failed} PASSED, {failed} FAILED")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
