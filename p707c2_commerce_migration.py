"""
P70.7C.2 — Commerce Engine Table Migration
============================================
Safe, reversible migration: rename dbp_trading_* → dbp_commerce_*
with backward-compatible views.

Strategy:
  1. ALTER TABLE RENAME (preserves data, constraints, indexes)
  2. CREATE VIEW dbp_trading_* → SELECT * FROM dbp_commerce_*
  3. Update Retail FKs to reference new table names
  4. Update Python code references

Reversal:
  - Drop views
  - ALTER TABLE RENAME back
"""
import sys
sys.path.insert(0, r"D:\EOS\Eos final")
from database import engine
from sqlalchemy import text

# ═══════════════════════════════════════════════════
# TABLES TO MIGRATE (commerce-generic only)
# ═══════════════════════════════════════════════════
MIGRATIONS = [
    # (old_name, new_name)
    ("dbp_trading_items",      "dbp_commerce_items"),
    ("dbp_trading_stock",      "dbp_commerce_stock"),
    ("dbp_trading_warehouses", "dbp_commerce_warehouses"),
    ("dbp_trading_customers",  "dbp_commerce_customers"),
    ("dbp_trading_suppliers",  "dbp_commerce_suppliers"),
]

def migrate():
    print("P70.7C.2 — Commerce Engine Table Migration")
    print("=" * 60)

    with engine.begin() as conn:
        # ═══ Step 1: Rename tables ═══
        print("\n[1/4] Renaming tables...")
        for old, new in MIGRATIONS:
            try:
                # Check if old table exists
                exists = conn.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                    "WHERE table_name=:name)"
                ), {"name": old}).fetchone()[0]
                if not exists:
                    print(f"  SKIP: {old} does not exist")
                    continue

                # Check if new table already exists
                new_exists = conn.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                    "WHERE table_name=:name)"
                ), {"name": new}).fetchone()[0]
                if new_exists:
                    print(f"  SKIP: {new} already exists")
                    continue

                conn.execute(text(f"ALTER TABLE {old} RENAME TO {new}"))
                print(f"  OK: {old} → {new}")
            except Exception as e:
                print(f"  ERROR: {old}: {e}")

        # ═══ Step 2: Create backward-compatible views ═══
        print("\n[2/4] Creating backward-compatible views...")
        for old, new in MIGRATIONS:
            try:
                view_exists = conn.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.views "
                    "WHERE table_name=:name)"
                ), {"name": old}).fetchone()[0]
                if view_exists:
                    print(f"  SKIP: view {old} already exists")
                    continue
                conn.execute(text(f"CREATE OR REPLACE VIEW {old} AS SELECT * FROM {new}"))
                print(f"  OK: view {old} → {new}")
            except Exception as e:
                print(f"  ERROR: view {old}: {e}")

        # ═══ Step 3: Fix Retail FKs ═══
        print("\n[3/4] Fixing Retail FK constraints...")
        # Drop old FKs that point to the old table names (which are now views)
        # and recreate them pointing to the actual tables
        FK_FIXES = [
            # (constraint_name, alter_statement)
            ("fk_retail_reg_wh",
             "ALTER TABLE dbp_retail_registers DROP CONSTRAINT IF EXISTS fk_retail_reg_wh; "
             "ALTER TABLE dbp_retail_registers ADD CONSTRAINT fk_retail_reg_wh "
             "FOREIGN KEY (warehouse_id) REFERENCES dbp_commerce_warehouses(id)"),
            ("fk_retail_sale_cust",
             "ALTER TABLE dbp_retail_pos_sales DROP CONSTRAINT IF EXISTS fk_retail_sale_cust; "
             "ALTER TABLE dbp_retail_pos_sales ADD CONSTRAINT fk_retail_sale_cust "
             "FOREIGN KEY (customer_id) REFERENCES dbp_commerce_customers(id)"),
            ("fk_retail_pl_item",
             "ALTER TABLE dbp_retail_pos_lines DROP CONSTRAINT IF EXISTS fk_retail_pl_item; "
             "ALTER TABLE dbp_retail_pos_lines ADD CONSTRAINT fk_retail_pl_item "
             "FOREIGN KEY (item_id) REFERENCES dbp_commerce_items(id)"),
            ("fk_retail_la_cust",
             "ALTER TABLE dbp_retail_loyalty_accounts DROP CONSTRAINT IF EXISTS fk_retail_la_cust; "
             "ALTER TABLE dbp_retail_loyalty_accounts ADD CONSTRAINT fk_retail_la_cust "
             "FOREIGN KEY (customer_id) REFERENCES dbp_commerce_customers(id)"),
            ("fk_retail_pi_item",
             "ALTER TABLE dbp_retail_promo_items DROP CONSTRAINT IF EXISTS fk_retail_pi_item; "
             "ALTER TABLE dbp_retail_promo_items ADD CONSTRAINT fk_retail_pi_item "
             "FOREIGN KEY (item_id) REFERENCES dbp_commerce_items(id)"),
        ]
        for name, sql in FK_FIXES:
            try:
                conn.execute(text(sql))
                print(f"  OK: {name}")
            except Exception as e:
                print(f"  WARN: {name}: {e}")

        # ═══ Step 4: Verify ═══
        print("\n[4/4] Verifying migration...")
        for old, new in MIGRATIONS:
            new_count = conn.execute(text(f"SELECT COUNT(*) FROM {new}")).fetchone()[0]
            try:
                view_count = conn.execute(text(f"SELECT COUNT(*) FROM {old}")).fetchone()[0]
                match = "✓" if new_count == view_count else "✗ MISMATCH"
                print(f"  {new}: {new_count} rows | view {old}: {view_count} rows {match}")
            except Exception as e:
                print(f"  {new}: {new_count} rows | view {old}: ERROR {e}")

    print("\nMigration complete!")
    print("Old views provide backward compatibility — no code breakage.")

if __name__ == "__main__":
    migrate()
