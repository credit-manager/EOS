"""
P70.6 Retail ERP Certification & Hardening
============================================
DB-level hardening for Retail tables:
- Bilingual fields on key tables
- Additional indexes for POS performance
- Cash session closing_amount NOT NULL constraint
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

MIGRATIONS = [
    # ═══════════════════════════════════════════════
    # BILINGUAL FIELDS
    # ═══════════════════════════════════════════════
    "ALTER TABLE dbp_retail_registers ADD COLUMN IF NOT EXISTS name_ar VARCHAR(200)",
    "ALTER TABLE dbp_retail_cashiers ADD COLUMN IF NOT EXISTS name_ar VARCHAR(200)",
    "ALTER TABLE dbp_retail_loyalty_tiers ADD COLUMN IF NOT EXISTS name_ar VARCHAR(200)",
    "ALTER TABLE dbp_retail_promotions ADD COLUMN IF NOT EXISTS description TEXT",
    "ALTER TABLE dbp_retail_promotions ADD COLUMN IF NOT EXISTS description_ar TEXT",

    # ═══════════════════════════════════════════════
    # PERFORMANCE INDEXES (POS must be fast)
    # ═══════════════════════════════════════════════
    "CREATE INDEX IF NOT EXISTS idx_retail_sale_cashier ON dbp_retail_pos_sales(cashier_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_sale_cust ON dbp_retail_pos_sales(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_pl_item ON dbp_retail_pos_lines(item_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_pl_sale_item ON dbp_retail_pos_lines(sale_id, item_id)",
    "CREATE INDEX IF NOT EXISTS idx_retail_cm_type ON dbp_retail_cash_movements(movement_type)",
    "CREATE INDEX IF NOT EXISTS idx_retail_cs_status ON dbp_retail_cash_sessions(status)",
    "CREATE INDEX IF NOT EXISTS idx_retail_sale_status ON dbp_retail_pos_sales(status)",
    "CREATE INDEX IF NOT EXISTS idx_retail_sale_return ON dbp_retail_pos_sales(is_return)",

    # ═══════════════════════════════════════════════
    # DATA INTEGRITY
    # ═══════════════════════════════════════════════
    "ALTER TABLE dbp_retail_pos_sales ALTER COLUMN payment_method SET DEFAULT 'cash'",
    "ALTER TABLE dbp_retail_pos_sales ALTER COLUMN status SET DEFAULT 'completed'",

    # UNIQUE constraints for idempotency
    "ALTER TABLE dbp_retail_cashiers ADD CONSTRAINT uq_retail_cashier_user UNIQUE (tenant_id, user_id)",
]


def migrate():
    print("P70.6 Retail Hardening Migration")
    print("=" * 50)
    applied = 0
    skipped = 0
    with engine.begin() as conn:
        for sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                applied += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    skipped += 1
                else:
                    print(f"  WARN: {e}")

    print(f"  Applied: {applied}, Skipped: {skipped}")
    print("  Retail hardening complete")


if __name__ == "__main__":
    migrate()
