"""
P70.8.5 Manufacturing ERP Hardening
=====================================
DB constraints + API security hardening.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

HARDENING = [
    # ─── DB Hardening ──────────────────────────────────
    # Indexes for performance
    "CREATE INDEX IF NOT EXISTS idx_mfg_bom_active ON dbp_mfg_bom(tenant_id, is_active)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_orders_date ON dbp_mfg_orders(tenant_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_mi_status ON dbp_mfg_material_issues(tenant_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_qi_status ON dbp_mfg_quality_inspections(tenant_id, result)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_scrap_date ON dbp_mfg_scrap(tenant_id, reported_at DESC)",

    # Extra CHECK constraints
    "ALTER TABLE dbp_mfg_bom ADD CONSTRAINT chk_mfg_bom_revision CHECK (length(revision) > 0 AND length(revision) <= 10)",
    "ALTER TABLE dbp_mfg_bom_lines ADD CONSTRAINT chk_mfg_bom_line_unit CHECK (length(unit) > 0)",
    "ALTER TABLE dbp_mfg_work_centers ADD CONSTRAINT chk_mfg_wc_cost CHECK (cost_per_hour >= 0)",
    "ALTER TABLE dbp_mfg_routing_steps ADD CONSTRAINT chk_mfg_step_times_total CHECK (setup_time_hrs + run_time_hrs + wait_time_hrs + transfer_time_hrs >= 0)",
    "ALTER TABLE dbp_mfg_orders ADD CONSTRAINT chk_mfg_order_dates CHECK (planned_end IS NULL OR planned_start IS NULL OR planned_end >= planned_start)",
    "ALTER TABLE dbp_mfg_receipts ADD CONSTRAINT chk_mfg_receipt_accepted CHECK (qty_accepted >= 0 AND qty_accepted <= qty_received)",
    "ALTER TABLE dbp_mfg_receipts ADD CONSTRAINT chk_mfg_receipt_rejected CHECK (qty_rejected >= 0)",

    # Extra defaults
    "ALTER TABLE dbp_mfg_routing_steps ALTER COLUMN setup_time_hrs SET DEFAULT 0",
    "ALTER TABLE dbp_mfg_routing_steps ALTER COLUMN run_time_hrs SET DEFAULT 0",
    "ALTER TABLE dbp_mfg_routing_steps ALTER COLUMN wait_time_hrs SET DEFAULT 0",
    "ALTER TABLE dbp_mfg_routing_steps ALTER COLUMN transfer_time_hrs SET DEFAULT 0",
]

def harden():
    applied = 0
    skipped = 0
    errors = 0
    with engine.begin() as conn:
        for sql in HARDENING:
            try:
                conn.execute(text(sql))
                applied += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    skipped += 1
                else:
                    errors += 1
                    print(f"  WARN: {e}")

    print(f"P70.8.5 Manufacturing Hardening:")
    print(f"  Applied:  {applied}")
    print(f"  Skipped:  {skipped} (already exist)")
    print(f"  Errors:   {errors}")
    print(f"  Total:    {len(HARDENING)} statements")
    print("  DONE")


if __name__ == "__main__":
    harden()
