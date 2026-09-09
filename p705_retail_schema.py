"""
P70.5 Retail ERP Professional — Database Migration
====================================================
POS, Cash Management, Loyalty, Promotions, Branch Analytics.
Reuses Trading's items/stock/warehouses/customers tables via shared
`dbp_trading_*` prefix (Retail IS Trading with a POS frontend).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from sqlalchemy import text

TENANT_ID = "f57e6756-b954-4ade-a17b-f2125e4b97c4"

# ═══════════════════════════════════════════════════
# Retail-specific tables (POS, Cash, Loyalty, Promotions)
# Items, Stock, Warehouses, Customers are SHARED from Trading
# ═══════════════════════════════════════════════════

TABLES = [
    # ─────────────────────────────────────────────
    # POS: Registers & Cashiers
    # ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_registers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        register_code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        warehouse_id VARCHAR(36) NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_cashiers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        user_id VARCHAR(36) NOT NULL,
        name VARCHAR(200) NOT NULL,
        pin VARCHAR(20),
        register_id VARCHAR(36),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ─────────────────────────────────────────────
    # POS: Sales (immediate transactions)
    # ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_pos_sales (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        sale_number VARCHAR(50) NOT NULL,
        register_id VARCHAR(36) NOT NULL,
        cashier_id VARCHAR(36) NOT NULL,
        customer_id VARCHAR(36),
        sale_date TIMESTAMPTZ DEFAULT NOW(),
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_rate NUMERIC(5,2) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        discount_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        paid_amount NUMERIC(15,4) DEFAULT 0,
        change_amount NUMERIC(15,4) DEFAULT 0,
        payment_method VARCHAR(30) DEFAULT 'cash',
        loyalty_points_earned INT DEFAULT 0,
        loyalty_points_redeemed INT DEFAULT 0,
        is_return BOOLEAN DEFAULT false,
        return_of VARCHAR(36),
        status VARCHAR(20) DEFAULT 'completed',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_pos_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        sale_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        barcode VARCHAR(100),
        description VARCHAR(500),
        qty NUMERIC(15,4) NOT NULL DEFAULT 1,
        unit_price NUMERIC(15,4) NOT NULL DEFAULT 0,
        cost_price NUMERIC(15,4) DEFAULT 0,
        discount_pct NUMERIC(5,2) DEFAULT 0,
        discount_amount NUMERIC(15,4) DEFAULT 0,
        line_total NUMERIC(15,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ─────────────────────────────────────────────
    # POS: Suspended Sales (hold & recall)
    # ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_suspended_sales (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        register_id VARCHAR(36) NOT NULL,
        cashier_id VARCHAR(36) NOT NULL,
        customer_id VARCHAR(36),
        suspended_at TIMESTAMPTZ DEFAULT NOW(),
        items_json TEXT NOT NULL,
        subtotal NUMERIC(15,4) DEFAULT 0,
        tax_amount NUMERIC(15,4) DEFAULT 0,
        total NUMERIC(15,4) DEFAULT 0,
        notes TEXT,
        status VARCHAR(20) DEFAULT 'suspended',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ─────────────────────────────────────────────
    # Cash Management
    # ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_cash_sessions (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        session_number VARCHAR(50) NOT NULL,
        register_id VARCHAR(36) NOT NULL,
        cashier_id VARCHAR(36) NOT NULL,
        opened_at TIMESTAMPTZ DEFAULT NOW(),
        opening_amount NUMERIC(15,4) DEFAULT 0,
        closed_at TIMESTAMPTZ,
        closing_amount NUMERIC(15,4),
        expected_amount NUMERIC(15,4),
        variance NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'open',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_cash_movements (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        session_id VARCHAR(36) NOT NULL,
        movement_type VARCHAR(30) NOT NULL,
        amount NUMERIC(15,4) NOT NULL,
        reference VARCHAR(200),
        notes TEXT,
        created_by VARCHAR(100),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ─────────────────────────────────────────────
    # Loyalty Program
    # ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_loyalty_tiers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        name VARCHAR(100) NOT NULL,
        min_points INT DEFAULT 0,
        discount_pct NUMERIC(5,2) DEFAULT 0,
        points_multiplier NUMERIC(5,2) DEFAULT 1.0,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_loyalty_accounts (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        customer_id VARCHAR(36) NOT NULL,
        tier_id VARCHAR(36),
        total_points INT DEFAULT 0,
        redeemed_points INT DEFAULT 0,
        available_points INT DEFAULT 0,
        lifetime_spend NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_loyalty_transactions (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        account_id VARCHAR(36) NOT NULL,
        sale_id VARCHAR(36),
        transaction_type VARCHAR(30) NOT NULL,
        points INT NOT NULL DEFAULT 0,
        description TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ─────────────────────────────────────────────
    # Promotions & Offers
    # ─────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_promotions (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        promo_type VARCHAR(30) NOT NULL,
        discount_value NUMERIC(15,4) DEFAULT 0,
        buy_qty INT,
        get_qty INT,
        min_purchase NUMERIC(15,4) DEFAULT 0,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        applies_to VARCHAR(30) DEFAULT 'all',
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_retail_promo_items (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        promo_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
]


# ═══════════════════════════════════════════════════
# CONSTRAINTS
# ═══════════════════════════════════════════════════

CONSTRAINTS = [
    # UNIQUE
    "ALTER TABLE dbp_retail_registers ADD CONSTRAINT uq_retail_reg_code UNIQUE (tenant_id, register_code)",
    "ALTER TABLE dbp_retail_pos_sales ADD CONSTRAINT uq_retail_sale_num UNIQUE (tenant_id, sale_number)",
    "ALTER TABLE dbp_retail_cash_sessions ADD CONSTRAINT uq_retail_sess_num UNIQUE (tenant_id, session_number)",
    "ALTER TABLE dbp_retail_promotions ADD CONSTRAINT uq_retail_promo_name UNIQUE (tenant_id, name)",

    # FK: Registers → Warehouses (reuses Trading's warehouse table)
    "ALTER TABLE dbp_retail_registers ADD CONSTRAINT fk_retail_reg_wh FOREIGN KEY (warehouse_id) REFERENCES dbp_trading_warehouses(id)",

    # FK: Cashiers → Registers
    "ALTER TABLE dbp_retail_cashiers ADD CONSTRAINT fk_retail_cash_reg FOREIGN KEY (register_id) REFERENCES dbp_retail_registers(id)",

    # FK: POS Sales
    "ALTER TABLE dbp_retail_pos_sales ADD CONSTRAINT fk_retail_sale_reg FOREIGN KEY (register_id) REFERENCES dbp_retail_registers(id)",
    "ALTER TABLE dbp_retail_pos_sales ADD CONSTRAINT fk_retail_sale_cashier FOREIGN KEY (cashier_id) REFERENCES dbp_retail_cashiers(id)",
    "ALTER TABLE dbp_retail_pos_sales ADD CONSTRAINT fk_retail_sale_cust FOREIGN KEY (customer_id) REFERENCES dbp_trading_customers(id)",

    # FK: POS Lines
    "ALTER TABLE dbp_retail_pos_lines ADD CONSTRAINT fk_retail_pl_sale FOREIGN KEY (sale_id) REFERENCES dbp_retail_pos_sales(id)",
    "ALTER TABLE dbp_retail_pos_lines ADD CONSTRAINT fk_retail_pl_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",

    # FK: Suspended Sales
    "ALTER TABLE dbp_retail_suspended_sales ADD CONSTRAINT fk_retail_susp_reg FOREIGN KEY (register_id) REFERENCES dbp_retail_registers(id)",
    "ALTER TABLE dbp_retail_suspended_sales ADD CONSTRAINT fk_retail_susp_cashier FOREIGN KEY (cashier_id) REFERENCES dbp_retail_cashiers(id)",

    # FK: Cash Sessions
    "ALTER TABLE dbp_retail_cash_sessions ADD CONSTRAINT fk_retail_cs_reg FOREIGN KEY (register_id) REFERENCES dbp_retail_registers(id)",
    "ALTER TABLE dbp_retail_cash_sessions ADD CONSTRAINT fk_retail_cs_cashier FOREIGN KEY (cashier_id) REFERENCES dbp_retail_cashiers(id)",

    # FK: Cash Movements
    "ALTER TABLE dbp_retail_cash_movements ADD CONSTRAINT fk_retail_cm_session FOREIGN KEY (session_id) REFERENCES dbp_retail_cash_sessions(id)",

    # FK: Loyalty
    "ALTER TABLE dbp_retail_loyalty_accounts ADD CONSTRAINT fk_retail_la_cust FOREIGN KEY (customer_id) REFERENCES dbp_trading_customers(id)",
    "ALTER TABLE dbp_retail_loyalty_accounts ADD CONSTRAINT fk_retail_la_tier FOREIGN KEY (tier_id) REFERENCES dbp_retail_loyalty_tiers(id)",
    "ALTER TABLE dbp_retail_loyalty_transactions ADD CONSTRAINT fk_retail_lt_account FOREIGN KEY (account_id) REFERENCES dbp_retail_loyalty_accounts(id)",
    "ALTER TABLE dbp_retail_loyalty_transactions ADD CONSTRAINT fk_retail_lt_sale FOREIGN KEY (sale_id) REFERENCES dbp_retail_pos_sales(id)",

    # FK: Promotions
    "ALTER TABLE dbp_retail_promo_items ADD CONSTRAINT fk_retail_pi_promo FOREIGN KEY (promo_id) REFERENCES dbp_retail_promotions(id)",
    "ALTER TABLE dbp_retail_promo_items ADD CONSTRAINT fk_retail_pi_item FOREIGN KEY (item_id) REFERENCES dbp_trading_items(id)",

    # CHECK
    "ALTER TABLE dbp_retail_pos_sales ADD CONSTRAINT chk_retail_sale_pay CHECK (payment_method IN ('cash','card','mobile','credit','loyalty'))",
    "ALTER TABLE dbp_retail_pos_sales ADD CONSTRAINT chk_retail_sale_status CHECK (status IN ('completed','voided','suspended'))",
    "ALTER TABLE dbp_retail_cash_sessions ADD CONSTRAINT chk_retail_cs_status CHECK (status IN ('open','closed'))",
    "ALTER TABLE dbp_retail_cash_movements ADD CONSTRAINT chk_retail_cm_type CHECK (movement_type IN ('opening','sale','return','withdrawal','deposit','closing'))",
    "ALTER TABLE dbp_retail_promotions ADD CONSTRAINT chk_retail_promo_type CHECK (promo_type IN ('percentage','fixed','bogo','bundle'))",
]


# ═══════════════════════════════════════════════════
# INDEXES
# ═══════════════════════════════════════════════════

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_retail_reg_tenant ON dbp_retail_registers(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_cashier_tenant ON dbp_retail_cashiers(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_sale_tenant ON dbp_retail_pos_sales(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_sale_date ON dbp_retail_pos_sales(tenant_id, sale_date)",
    "CREATE INDEX IF NOT EXISTS idx_retail_sale_reg ON dbp_retail_pos_sales(register_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_pl_tenant ON dbp_retail_pos_lines(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_susp_tenant ON dbp_retail_suspended_sales(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_cs_tenant ON dbp_retail_cash_sessions(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_cs_reg ON dbp_retail_cash_sessions(register_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_cm_tenant ON dbp_retail_cash_movements(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_cm_session ON dbp_retail_cash_movements(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_la_tenant ON dbp_retail_loyalty_accounts(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_la_cust ON dbp_retail_loyalty_accounts(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_lt_tenant ON dbp_retail_loyalty_transactions(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_lt_account ON dbp_retail_loyalty_transactions(account_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_promo_tenant ON dbp_retail_promotions(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_promo_dates ON dbp_retail_promotions(start_date, end_date)",
    "CREATE INDEX IF NOT EXISTS idx_retail_pi_tenant ON dbp_retail_promo_items(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_pi_promo ON dbp_retail_promo_items(promo_id)",
]


def migrate():
    print("P70.5 Retail Schema Migration")
    print("=" * 50)
    with engine.begin() as conn:
        created = 0
        for i, sql in enumerate(TABLES):
            try:
                conn.execute(text(sql.strip()))
                created += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"  Table {i+1}: {e}")

        conformed = 0
        for sql in CONSTRAINTS:
            try:
                conn.execute(text(sql))
                conformed += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"  FK/CHECK: {e}")

        indexed = 0
        for sql in INDEXES:
            try:
                conn.execute(text(sql))
                indexed += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"  Index: {e}")

        # Seed loyalty tiers
        from core.industry_security import uid, now
        tiers = [
            ("Bronze", 0, 0, 1.0),
            ("Silver", 1000, 5, 1.5),
            ("Gold", 5000, 10, 2.0),
            ("Platinum", 20000, 15, 3.0),
        ]
        seeded = 0
        for name, min_pts, disc, mult in tiers:
            exists = conn.execute(text(
                "SELECT id FROM dbp_retail_loyalty_tiers WHERE tenant_id=:t AND name=:n"
            ), {"t": TENANT_ID, "n": name}).fetchone()
            if not exists:
                conn.execute(text(
                    "INSERT INTO dbp_retail_loyalty_tiers "
                    "(id, tenant_id, name, min_points, discount_pct, points_multiplier) "
                    "VALUES (:id, :t, :n, :mp, :dp, :pm)"
                ), {"id": uid(), "t": TENANT_ID, "n": name,
                    "mp": min_pts, "dp": disc, "pm": mult})
                seeded += 1

    print(f"  Tables created: {created}")
    print(f"  Constraints: {conformed}")
    print(f"  Indexes: {indexed}")
    print(f"  Loyalty tiers seeded: {seeded}")
    print(f"\nRetail schema ready. {created} tables + {conformed} constraints + {indexed} indexes")


if __name__ == "__main__":
    migrate()
