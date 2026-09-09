"""
P70.7B Restaurant ERP Hardening — DB Migration
================================================
Adds UNIQUE, CHECK, performance indexes, and default values
to restaurant tables for production-grade data integrity.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

MIGRATIONS = [
    # ═══════════════════════════════════════════════
    # UNIQUE CONSTRAINTS
    # ═══════════════════════════════════════════════
    "ALTER TABLE dbp_restaurant_tables ADD CONSTRAINT uq_rest_tbl_number UNIQUE (tenant_id, table_number)",
    "ALTER TABLE dbp_restaurant_menu_items ADD CONSTRAINT uq_rest_menu_code UNIQUE (tenant_id, item_code)",
    "ALTER TABLE dbp_restaurant_menu_categories ADD CONSTRAINT uq_rest_cat_name UNIQUE (tenant_id, name)",
    "ALTER TABLE dbp_restaurant_modifier_groups ADD CONSTRAINT uq_rest_mg_name UNIQUE (tenant_id, name)",
    "ALTER TABLE dbp_restaurant_kitchen_stations ADD CONSTRAINT uq_rest_ks_code UNIQUE (tenant_id, station_code)",
    "ALTER TABLE dbp_restaurant_waiters ADD CONSTRAINT uq_rest_waiter_name UNIQUE (tenant_id, name)",

    # ═══════════════════════════════════════════════
    # CHECK CONSTRAINTS
    # ═══════════════════════════════════════════════
    "ALTER TABLE dbp_restaurant_tables ADD CONSTRAINT chk_rest_tbl_capacity CHECK (capacity > 0)",
    "ALTER TABLE dbp_restaurant_tables ADD CONSTRAINT chk_rest_tbl_status CHECK (status IN ('available','occupied','reserved','cleaning'))",
    "ALTER TABLE dbp_restaurant_reservations ADD CONSTRAINT chk_rest_res_party CHECK (party_size > 0)",
    "ALTER TABLE dbp_restaurant_reservations ADD CONSTRAINT chk_rest_res_status CHECK (status IN ('confirmed','checked_in','completed','cancelled','no_show'))",
    "ALTER TABLE dbp_restaurant_menu_items ADD CONSTRAINT chk_rest_menu_price CHECK (selling_price >= 0)",
    "ALTER TABLE dbp_restaurant_menu_items ADD CONSTRAINT chk_rest_menu_cost CHECK (cost_price >= 0)",
    "ALTER TABLE dbp_restaurant_menu_items ADD CONSTRAINT chk_rest_menu_prep CHECK (prep_time_minutes >= 0)",
    "ALTER TABLE dbp_restaurant_modifiers ADD CONSTRAINT chk_rest_mod_adj CHECK (price_adjustment >= -10000)",
    "ALTER TABLE dbp_restaurant_orders ADD CONSTRAINT chk_rest_ord_type CHECK (order_type IN ('dine_in','takeaway','delivery'))",
    "ALTER TABLE dbp_restaurant_orders ADD CONSTRAINT chk_rest_ord_status CHECK (status IN ('open','preparing','ready','served','paid','voided'))",
    "ALTER TABLE dbp_restaurant_orders ADD CONSTRAINT chk_rest_ord_kitchen CHECK (kitchen_status IN ('pending','fired','ready','done'))",
    "ALTER TABLE dbp_restaurant_orders ADD CONSTRAINT chk_rest_ord_total CHECK (total >= 0)",
    "ALTER TABLE dbp_restaurant_orders ADD CONSTRAINT chk_rest_ord_guests CHECK (guests_count > 0)",
    "ALTER TABLE dbp_restaurant_order_lines ADD CONSTRAINT chk_rest_ol_qty CHECK (qty > 0)",
    "ALTER TABLE dbp_restaurant_order_lines ADD CONSTRAINT chk_rest_ol_price CHECK (unit_price >= 0)",
    "ALTER TABLE dbp_restaurant_order_lines ADD CONSTRAINT chk_rest_ol_status CHECK (status IN ('pending','fired','started','prepared','served','voided'))",
    "ALTER TABLE dbp_restaurant_kitchen_orders ADD CONSTRAINT chk_rest_ko_status CHECK (status IN ('pending','fired','started','done'))",
    "ALTER TABLE dbp_restaurant_waste ADD CONSTRAINT chk_rest_waste_type CHECK (waste_type IN ('production','expired','spoiled','other'))",
    "ALTER TABLE dbp_restaurant_waste ADD CONSTRAINT chk_rest_waste_status CHECK (status IN ('recorded','verified'))",
    "ALTER TABLE dbp_restaurant_waste_items ADD CONSTRAINT chk_rest_wi_qty CHECK (qty > 0)",
    "ALTER TABLE dbp_restaurant_cash_drawer ADD CONSTRAINT chk_rest_cd_status CHECK (status IN ('open','closed'))",
    "ALTER TABLE dbp_restaurant_cash_drawer ADD CONSTRAINT chk_rest_cd_opening CHECK (opening_amount >= 0)",

    # ═══════════════════════════════════════════════
    # DEFAULT VALUES
    # ═══════════════════════════════════════════════
    "ALTER TABLE dbp_restaurant_orders ALTER COLUMN status SET DEFAULT 'open'",
    "ALTER TABLE dbp_restaurant_orders ALTER COLUMN kitchen_status SET DEFAULT 'pending'",
    "ALTER TABLE dbp_restaurant_orders ALTER COLUMN payment_method SET DEFAULT 'cash'",
    "ALTER TABLE dbp_restaurant_order_lines ALTER COLUMN status SET DEFAULT 'pending'",
    "ALTER TABLE dbp_restaurant_kitchen_orders ALTER COLUMN status SET DEFAULT 'pending'",
    "ALTER TABLE dbp_restaurant_reservations ALTER COLUMN status SET DEFAULT 'confirmed'",
    "ALTER TABLE dbp_restaurant_cash_drawer ALTER COLUMN status SET DEFAULT 'open'",

    # ═══════════════════════════════════════════════
    # PERFORMANCE INDEXES
    # ═══════════════════════════════════════════════
    "CREATE INDEX IF NOT EXISTS idx_rest2_tbl_tenant ON dbp_restaurant_tables(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_res_tenant ON dbp_restaurant_reservations(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_menu_tenant ON dbp_restaurant_menu_items(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_order_tenant ON dbp_restaurant_orders(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_order_created ON dbp_restaurant_orders(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_ol_tenant ON dbp_restaurant_order_lines(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_ko_tenant ON dbp_restaurant_kitchen_orders(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_waste_tenant ON dbp_restaurant_waste(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_cd_tenant ON dbp_restaurant_cash_drawer(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_recipe_tenant ON dbp_restaurant_recipes(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest2_rl_tenant ON dbp_restaurant_recipe_lines(tenant_id)",
]


def migrate():
    print("P70.7B Restaurant Hardening Migration")
    print("=" * 60)
    applied = 0
    skipped = 0
    errors = 0
    with engine.connect() as conn:
        for sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
                applied += 1
            except Exception as e:
                conn.rollback()
                err = str(e).lower()
                if "already exists" in err or "duplicate" in err or "duplicate key" in err:
                    skipped += 1
                else:
                    errors += 1
                    print(f"  WARN: {e}")
    print(f"  Applied: {applied}, Skipped: {skipped}, Errors: {errors}")
    print("  Restaurant hardening complete")


if __name__ == "__main__":
    migrate()
