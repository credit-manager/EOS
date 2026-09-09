"""
P74.7 Database Cleanup Script
Drops test-only and unused tables from the database.
Run with: python db_cleanup.py [--dry-run]
"""
import sys
import psycopg2

DRY_RUN = "--dry-run" in sys.argv

TEST_TABLES = [
    "evt_test_table", "evt_test_table2", "sec_test_table",
    "sv_empty_table", "test_products", "p14_departments",
    "p14_employees", "p14_salary_records", "p15_emp_tbl",
    "p16_orders", "p18_products", "bld_journey_custom",
    "bld_project_claims", "bld_temp_entity",
]

UNUSED_APP_TABLES = [
    "dbp_analytics_alerts", "dbp_analytics_dashboards", "dbp_analytics_widgets",
    "dbp_construction_inspections", "dbp_construction_variations",
    "dbp_data_pipelines", "dbp_mfg_settings", "dbp_notify_channels",
    "dbp_retail_promo_items", "dbp_stock_takes",
    "dbp_trading_price_list_items", "dbp_trading_purchase_return_lines",
    "dbp_trading_purchase_returns", "dbp_trading_rfq_lines",
    "dbp_trading_rfqs", "dbp_trading_sales_return_lines",
    "dbp_trading_sales_returns", "dbp_trading_salesmen",
    "dbp_trading_supplier_quotation_lines", "dbp_trading_supplier_quotations",
    "dbp_trading_territories", "dbp_webhook_logs",
]

ALL_TABLES = TEST_TABLES + UNUSED_APP_TABLES

conn = psycopg2.connect('postgresql://eos:0100@127.0.0.1:5432/eos_main')
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
existing = {r[0] for r in cur.fetchall()}

dropped = 0
skipped = 0
not_found = 0

for table in ALL_TABLES:
    if table in existing:
        if DRY_RUN:
            print(f"  [DRY-RUN] Would drop: {table}")
            dropped += 1
        else:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"  Dropped: {table}")
                dropped += 1
            except Exception as e:
                print(f"  Error dropping {table}: {e}")
                skipped += 1
    else:
        not_found += 1

if not DRY_RUN:
    conn.commit()

conn.close()

print(f"\nSummary:")
print(f"  {'Would drop' if DRY_RUN else 'Dropped'}: {dropped}")
print(f"  Skipped (errors): {skipped}")
print(f"  Not found: {not_found}")
print(f"  Mode: {'DRY-RUN' if DRY_RUN else 'LIVE'}")
