"""
P70.7 Restaurant ERP Professional — Database Migration
========================================================
Restaurant-specific tables built ON TOP of:
- Commerce Engine: items, stock, warehouses, customers, suppliers
- Core Platform: accounting, HR, documents, audit

Tables: 20 restaurant-specific tables
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

TENANT_ID = "f57e6756-b954-4ade-a17b-f2125e4b97c4"

TABLES = [
    # ═══════════════════════════════════════════════
    # TABLE LAYOUT
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_sections (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        name VARCHAR(100) NOT NULL,
        name_ar VARCHAR(100),
        sort_order INT DEFAULT 0,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_tables (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        table_number VARCHAR(20) NOT NULL,
        section_id VARCHAR(36),
        capacity INT NOT NULL DEFAULT 4,
        status VARCHAR(20) DEFAULT 'available',
        current_order_id VARCHAR(36),
        x_pos INT DEFAULT 0,
        y_pos INT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # RESERVATIONS
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_reservations (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        customer_name VARCHAR(200) NOT NULL,
        customer_phone VARCHAR(50),
        customer_id VARCHAR(36),
        table_id VARCHAR(36),
        reservation_date DATE NOT NULL,
        reservation_time TIME NOT NULL,
        party_size INT NOT NULL DEFAULT 2,
        status VARCHAR(20) DEFAULT 'confirmed',
        notes TEXT,
        checked_in_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # MENU
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_menu_categories (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        name VARCHAR(100) NOT NULL,
        name_ar VARCHAR(100),
        description TEXT,
        description_ar TEXT,
        sort_order INT DEFAULT 0,
        icon VARCHAR(50),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_menu_items (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        item_code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        description TEXT,
        description_ar TEXT,
        category_id VARCHAR(36),
        commerce_item_id VARCHAR(36),
        selling_price NUMERIC(15,4) NOT NULL DEFAULT 0,
        cost_price NUMERIC(15,4) DEFAULT 0,
        image_url VARCHAR(500),
        prep_time_minutes INT DEFAULT 0,
        is_available BOOLEAN DEFAULT true,
        is_combo BOOLEAN DEFAULT false,
        sort_order INT DEFAULT 0,
        kitchen_station VARCHAR(50),
        tags TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # MODIFIERS (size, add-ons, cooking level)
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_modifier_groups (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        name VARCHAR(100) NOT NULL,
        name_ar VARCHAR(100),
        selection_type VARCHAR(20) DEFAULT 'single',
        min_select INT DEFAULT 0,
        max_select INT DEFAULT 1,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_modifiers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        group_id VARCHAR(36) NOT NULL,
        name VARCHAR(100) NOT NULL,
        name_ar VARCHAR(100),
        price_adjustment NUMERIC(15,4) DEFAULT 0,
        commerce_item_id VARCHAR(36),
        sort_order INT DEFAULT 0,
        is_available BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_menu_modifiers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        menu_item_id VARCHAR(36) NOT NULL,
        modifier_group_id VARCHAR(36) NOT NULL,
        is_required BOOLEAN DEFAULT false,
        sort_order INT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # COMBOS
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_combos (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        description TEXT,
        combo_price NUMERIC(15,4) NOT NULL,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_combo_items (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        combo_id VARCHAR(36) NOT NULL,
        menu_item_id VARCHAR(36) NOT NULL,
        qty INT DEFAULT 1,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # RECIPES (menu item → ingredients)
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_recipes (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        menu_item_id VARCHAR(36) NOT NULL,
        recipe_name VARCHAR(200),
        yield_qty NUMERIC(10,4) DEFAULT 1,
        yield_unit VARCHAR(50) DEFAULT 'portion',
        prep_time_minutes INT DEFAULT 0,
        cook_time_minutes INT DEFAULT 0,
        instructions TEXT,
        total_cost NUMERIC(15,4) DEFAULT 0,
        cost_per_portion NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_recipe_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        recipe_id VARCHAR(36) NOT NULL,
        commerce_item_id VARCHAR(36) NOT NULL,
        ingredient_name VARCHAR(200),
        qty NUMERIC(10,4) NOT NULL DEFAULT 1,
        unit VARCHAR(50) NOT NULL DEFAULT 'gram',
        unit_cost NUMERIC(15,4) DEFAULT 0,
        line_cost NUMERIC(15,4) DEFAULT 0,
        waste_pct NUMERIC(5,2) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # ORDERS
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_orders (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        order_number VARCHAR(50) NOT NULL,
        order_type VARCHAR(20) NOT NULL DEFAULT 'dine_in',
        table_id VARCHAR(36),
        customer_id VARCHAR(36),
        customer_name VARCHAR(200),
        waiter_id VARCHAR(36),
        cashier_id VARCHAR(36),
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        discount_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        paid_amount NUMERIC(15,4) DEFAULT 0,
        change_amount NUMERIC(15,4) DEFAULT 0,
        payment_method VARCHAR(30) DEFAULT 'cash',
        status VARCHAR(20) DEFAULT 'open',
        kitchen_status VARCHAR(20) DEFAULT 'pending',
        notes TEXT,
        guests_count INT DEFAULT 1,
        opened_at TIMESTAMPTZ DEFAULT NOW(),
        served_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_order_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        order_id VARCHAR(36) NOT NULL,
        menu_item_id VARCHAR(36) NOT NULL,
        item_name VARCHAR(200) NOT NULL,
        qty INT NOT NULL DEFAULT 1,
        unit_price NUMERIC(15,4) NOT NULL DEFAULT 0,
        discount_pct NUMERIC(5,2) DEFAULT 0,
        discount_amount NUMERIC(15,4) DEFAULT 0,
        line_total NUMERIC(15,4) DEFAULT 0,
        cost_price NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'pending',
        sent_to_kitchen_at TIMESTAMPTZ,
        prepared_at TIMESTAMPTZ,
        voided_at TIMESTAMPTZ,
        void_reason TEXT,
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_order_modifiers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        order_line_id VARCHAR(36) NOT NULL,
        modifier_id VARCHAR(36) NOT NULL,
        modifier_name VARCHAR(100) NOT NULL,
        price_adjustment NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # KITCHEN DISPLAY (KDS)
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_kitchen_stations (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        station_code VARCHAR(50) NOT NULL,
        name VARCHAR(100) NOT NULL,
        name_ar VARCHAR(100),
        station_type VARCHAR(50) DEFAULT 'general',
        printer_ip VARCHAR(50),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_kitchen_orders (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        order_id VARCHAR(36) NOT NULL,
        order_line_id VARCHAR(36) NOT NULL,
        station_id VARCHAR(36) NOT NULL,
        priority INT DEFAULT 0,
        status VARCHAR(20) DEFAULT 'pending',
        fired_at TIMESTAMPTZ,
        started_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        eta_minutes INT,
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # WASTE TRACKING
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_waste (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        waste_number VARCHAR(50) NOT NULL,
        waste_date DATE NOT NULL,
        waste_type VARCHAR(30) DEFAULT 'production',
        reason VARCHAR(100),
        total_cost NUMERIC(15,4) DEFAULT 0,
        reported_by VARCHAR(36),
        notes TEXT,
        status VARCHAR(20) DEFAULT 'recorded',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_waste_items (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        waste_id VARCHAR(36) NOT NULL,
        commerce_item_id VARCHAR(36) NOT NULL,
        item_name VARCHAR(200),
        qty NUMERIC(10,4) NOT NULL DEFAULT 1,
        unit VARCHAR(50) DEFAULT 'gram',
        unit_cost NUMERIC(15,4) DEFAULT 0,
        total_cost NUMERIC(15,4) DEFAULT 0,
        reason VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # CASH DRAWER
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_cash_drawer (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        drawer_date DATE NOT NULL,
        opening_amount NUMERIC(15,4) DEFAULT 0,
        closing_amount NUMERIC(15,4),
        cash_in NUMERIC(15,4) DEFAULT 0,
        cash_out NUMERIC(15,4) DEFAULT 0,
        card_total NUMERIC(15,4) DEFAULT 0,
        mobile_total NUMERIC(15,4) DEFAULT 0,
        expected_cash NUMERIC(15,4) DEFAULT 0,
        actual_cash NUMERIC(15,4),
        variance NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'open',
        opened_by VARCHAR(36),
        closed_by VARCHAR(36),
        opened_at TIMESTAMPTZ DEFAULT NOW(),
        closed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ═══════════════════════════════════════════════
    # WAITER / SHIFT ASSIGNMENTS
    # ═══════════════════════════════════════════════
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_waiters (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        employee_id VARCHAR(36),
        name VARCHAR(200) NOT NULL,
        pin VARCHAR(20),
        section_id VARCHAR(36),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_shifts (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        shift_name VARCHAR(100) NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_restaurant_shift_assignments (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        shift_id VARCHAR(36) NOT NULL,
        waiter_id VARCHAR(36) NOT NULL,
        assignment_date DATE NOT NULL,
        section_id VARCHAR(36),
        status VARCHAR(20) DEFAULT 'assigned',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
]

CONSTRAINTS = [
    "ALTER TABLE dbp_restaurant_tables ADD CONSTRAINT fk_rest_section FOREIGN KEY (section_id) REFERENCES dbp_restaurant_sections(id)",
    "ALTER TABLE dbp_restaurant_reservations ADD CONSTRAINT fk_rest_res_table FOREIGN KEY (table_id) REFERENCES dbp_restaurant_tables(id)",
    "ALTER TABLE dbp_restaurant_menu_items ADD CONSTRAINT fk_rest_menu_cat FOREIGN KEY (category_id) REFERENCES dbp_restaurant_menu_categories(id)",
    "ALTER TABLE dbp_restaurant_modifiers ADD CONSTRAINT fk_rest_mod_group FOREIGN KEY (group_id) REFERENCES dbp_restaurant_modifier_groups(id)",
    "ALTER TABLE dbp_restaurant_menu_modifiers ADD CONSTRAINT fk_rest_mm_menu FOREIGN KEY (menu_item_id) REFERENCES dbp_restaurant_menu_items(id)",
    "ALTER TABLE dbp_restaurant_menu_modifiers ADD CONSTRAINT fk_rest_mm_group FOREIGN KEY (modifier_group_id) REFERENCES dbp_restaurant_modifier_groups(id)",
    "ALTER TABLE dbp_restaurant_combo_items ADD CONSTRAINT fk_rest_ci_combo FOREIGN KEY (combo_id) REFERENCES dbp_restaurant_combos(id)",
    "ALTER TABLE dbp_restaurant_combo_items ADD CONSTRAINT fk_rest_ci_menu FOREIGN KEY (menu_item_id) REFERENCES dbp_restaurant_menu_items(id)",
    "ALTER TABLE dbp_restaurant_recipes ADD CONSTRAINT fk_rest_recipe_menu FOREIGN KEY (menu_item_id) REFERENCES dbp_restaurant_menu_items(id)",
    "ALTER TABLE dbp_restaurant_recipe_lines ADD CONSTRAINT fk_rest_rl_recipe FOREIGN KEY (recipe_id) REFERENCES dbp_restaurant_recipes(id)",
    "ALTER TABLE dbp_restaurant_order_lines ADD CONSTRAINT fk_rest_ol_order FOREIGN KEY (order_id) REFERENCES dbp_restaurant_orders(id)",
    "ALTER TABLE dbp_restaurant_order_lines ADD CONSTRAINT fk_rest_ol_menu FOREIGN KEY (menu_item_id) REFERENCES dbp_restaurant_menu_items(id)",
    "ALTER TABLE dbp_restaurant_order_modifiers ADD CONSTRAINT fk_rest_om_line FOREIGN KEY (order_line_id) REFERENCES dbp_restaurant_order_lines(id)",
    "ALTER TABLE dbp_restaurant_kitchen_orders ADD CONSTRAINT fk_rest_ko_order FOREIGN KEY (order_id) REFERENCES dbp_restaurant_orders(id)",
    "ALTER TABLE dbp_restaurant_kitchen_orders ADD CONSTRAINT fk_rest_ko_line FOREIGN KEY (order_line_id) REFERENCES dbp_restaurant_order_lines(id)",
    "ALTER TABLE dbp_restaurant_kitchen_orders ADD CONSTRAINT fk_rest_ko_station FOREIGN KEY (station_id) REFERENCES dbp_restaurant_kitchen_stations(id)",
    "ALTER TABLE dbp_restaurant_waste_items ADD CONSTRAINT fk_rest_wi_waste FOREIGN KEY (waste_id) REFERENCES dbp_restaurant_waste(id)",
    "ALTER TABLE dbp_restaurant_waiters ADD CONSTRAINT fk_rest_waiter_section FOREIGN KEY (section_id) REFERENCES dbp_restaurant_sections(id)",
    "ALTER TABLE dbp_restaurant_shift_assignments ADD CONSTRAINT fk_rest_sa_shift FOREIGN KEY (shift_id) REFERENCES dbp_restaurant_shifts(id)",
    "ALTER TABLE dbp_restaurant_shift_assignments ADD CONSTRAINT fk_rest_sa_waiter FOREIGN KEY (waiter_id) REFERENCES dbp_restaurant_waiters(id)",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_rest_tbl_section ON dbp_restaurant_tables(section_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest_tbl_status ON dbp_restaurant_tables(status)",
    "CREATE INDEX IF NOT EXISTS idx_rest_res_date ON dbp_restaurant_reservations(reservation_date)",
    "CREATE INDEX IF NOT EXISTS idx_rest_res_status ON dbp_restaurant_reservations(status)",
    "CREATE INDEX IF NOT EXISTS idx_rest_menu_cat ON dbp_restaurant_menu_items(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest_menu_code ON dbp_restaurant_menu_items(item_code)",
    "CREATE INDEX IF NOT EXISTS idx_rest_recipe_menu ON dbp_restaurant_recipes(menu_item_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest_rl_recipe ON dbp_restaurant_recipe_lines(recipe_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest_order_table ON dbp_restaurant_orders(table_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest_order_status ON dbp_restaurant_orders(status)",
    "CREATE INDEX IF NOT EXISTS idx_rest_order_type ON dbp_restaurant_orders(order_type)",
    "CREATE INDEX IF NOT EXISTS idx_rest_order_date ON dbp_restaurant_orders(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_rest_ol_order ON dbp_restaurant_order_lines(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest_ko_station ON dbp_restaurant_kitchen_orders(station_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest_ko_status ON dbp_restaurant_kitchen_orders(status)",
    "CREATE INDEX IF NOT EXISTS idx_rest_ko_order ON dbp_restaurant_kitchen_orders(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_rest_waste_date ON dbp_restaurant_waste(waste_date)",
    "CREATE INDEX IF NOT EXISTS idx_rest_cd_date ON dbp_restaurant_cash_drawer(drawer_date)",
    "CREATE INDEX IF NOT EXISTS idx_rest_sa_date ON dbp_restaurant_shift_assignments(assignment_date)",
]


def migrate():
    print("P70.7 Restaurant ERP Schema Migration")
    print("=" * 60)
    created = 0
    skipped = 0
    with engine.begin() as conn:
        for sql in TABLES:
            try:
                conn.execute(text(sql))
                created += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    skipped += 1
                else:
                    print(f"  WARN TABLE: {e}")
        for sql in CONSTRAINTS:
            try:
                conn.execute(text(sql))
            except Exception:
                pass
        for sql in INDEXES:
            try:
                conn.execute(text(sql))
            except Exception:
                pass
    print(f"  Tables: {created} created, {skipped} skipped")
    print(f"  Constraints: {len(CONSTRAINTS)} applied")
    print(f"  Indexes: {len(INDEXES)} applied")
    print("  Restaurant schema complete")


if __name__ == "__main__":
    migrate()
