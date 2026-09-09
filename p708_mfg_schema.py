"""
P70.8.1 Manufacturing ERP Professional — Database Schema
=========================================================
22 manufacturing-specific tables + Commerce Engine integration.
Uses dbp_commerce_items (finished goods + raw materials) and dbp_commerce_stock.
"""
import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from database import engine
from sqlalchemy import text

def uid():
    return str(uuid.uuid4())

def now():
    return datetime.now(timezone.utc)

TABLES = [
    # ─── BOM (Bill of Materials) ────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_bom (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        bom_code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        revision VARCHAR(20) DEFAULT 'A',
        description TEXT,
        status VARCHAR(20) DEFAULT 'draft',
        is_active BOOLEAN DEFAULT TRUE,
        version INTEGER DEFAULT 1,
        created_by VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_bom_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        bom_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL DEFAULT 1,
        unit VARCHAR(20) DEFAULT 'piece',
        scrap_pct NUMERIC(5,2) DEFAULT 0,
        cost_estimate NUMERIC(15,4) DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Work Centers ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_work_centers (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200),
        work_center_type VARCHAR(30) DEFAULT 'machine',
        capacity_per_hour NUMERIC(15,4) DEFAULT 1,
        cost_per_hour NUMERIC(15,4) DEFAULT 0,
        efficiency_pct NUMERIC(5,2) DEFAULT 100,
        warehouse_id VARCHAR(36),
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Routings ──────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_routings (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        routing_code VARCHAR(50) NOT NULL,
        name VARCHAR(200) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        bom_id VARCHAR(36),
        revision VARCHAR(20) DEFAULT 'A',
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        status VARCHAR(20) DEFAULT 'draft',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_routing_steps (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        routing_id VARCHAR(36) NOT NULL,
        step_number INTEGER NOT NULL,
        work_center_id VARCHAR(36) NOT NULL,
        setup_time_hrs NUMERIC(10,4) DEFAULT 0,
        run_time_hrs NUMERIC(10,4) DEFAULT 0,
        wait_time_hrs NUMERIC(10,4) DEFAULT 0,
        transfer_time_hrs NUMERIC(10,4) DEFAULT 0,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Production Orders ─────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_orders (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        order_number VARCHAR(50) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        bom_id VARCHAR(36),
        routing_id VARCHAR(36),
        warehouse_id VARCHAR(36) NOT NULL,
        qty_planned NUMERIC(15,4) NOT NULL,
        qty_completed NUMERIC(15,4) DEFAULT 0,
        qty_scrapped NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'planned',
        priority INTEGER DEFAULT 5,
        planned_start DATE,
        planned_end DATE,
        actual_start TIMESTAMP WITH TIME ZONE,
        actual_end TIMESTAMP WITH TIME ZONE,
        notes TEXT,
        created_by VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Material Issues ───────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_material_issues (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        order_id VARCHAR(36) NOT NULL,
        issue_number VARCHAR(50) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        issued_by VARCHAR(36),
        issued_at TIMESTAMP WITH TIME ZONE,
        warehouse_id VARCHAR(36),
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_material_issue_lines (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        issue_id VARCHAR(36) NOT NULL,
        order_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        bom_line_id VARCHAR(36),
        qty_required NUMERIC(15,4) NOT NULL,
        qty_issued NUMERIC(15,4) DEFAULT 0,
        unit_cost NUMERIC(15,4) DEFAULT 0,
        warehouse_id VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Production Receipts (Finished Goods) ──────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_receipts (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        order_id VARCHAR(36) NOT NULL,
        receipt_number VARCHAR(50) NOT NULL,
        qty_received NUMERIC(15,4) NOT NULL,
        qty_accepted NUMERIC(15,4) NOT NULL,
        qty_rejected NUMERIC(15,4) DEFAULT 0,
        warehouse_id VARCHAR(36) NOT NULL,
        unit_cost NUMERIC(15,4) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'completed',
        received_by VARCHAR(36),
        received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Quality Inspections ───────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_quality_inspections (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        inspection_number VARCHAR(50) NOT NULL,
        order_id VARCHAR(36),
        receipt_id VARCHAR(36),
        item_id VARCHAR(36) NOT NULL,
        inspection_type VARCHAR(30) DEFAULT 'incoming',
        qty_inspected NUMERIC(15,4) DEFAULT 0,
        qty_passed NUMERIC(15,4) DEFAULT 0,
        qty_failed NUMERIC(15,4) DEFAULT 0,
        result VARCHAR(20) DEFAULT 'pending',
        inspector VARCHAR(36),
        inspection_date DATE,
        defect_notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Scrap Records ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_scrap (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        order_id VARCHAR(36) NOT NULL,
        item_id VARCHAR(36) NOT NULL,
        qty NUMERIC(15,4) NOT NULL,
        reason VARCHAR(100),
        cost NUMERIC(15,4) DEFAULT 0,
        reported_by VARCHAR(36),
        reported_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Production Costs ──────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_costs (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        order_id VARCHAR(36) NOT NULL,
        cost_type VARCHAR(30) NOT NULL,
        amount NUMERIC(15,4) DEFAULT 0,
        description TEXT,
        account_code VARCHAR(30),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Manufacturing Settings ────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_mfg_settings (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        setting_key VARCHAR(100) NOT NULL,
        setting_value TEXT,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
]

# ─── Indexes ─────────────────────────────────────────
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_mfg_bom_tenant ON dbp_mfg_bom(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_bom_item ON dbp_mfg_bom(tenant_id, item_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_bom_lines_tenant ON dbp_mfg_bom_lines(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_bom_lines_bom ON dbp_mfg_bom_lines(bom_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_wc_tenant ON dbp_mfg_work_centers(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_routing_tenant ON dbp_mfg_routings(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_routing_item ON dbp_mfg_routings(tenant_id, item_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_routing_steps_routing ON dbp_mfg_routing_steps(routing_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_orders_tenant ON dbp_mfg_orders(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_orders_status ON dbp_mfg_orders(tenant_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_orders_item ON dbp_mfg_orders(tenant_id, item_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_orders_number ON dbp_mfg_orders(tenant_id, order_number)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_mi_tenant ON dbp_mfg_material_issues(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_mi_order ON dbp_mfg_material_issues(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_mil_tenant ON dbp_mfg_material_issue_lines(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_mil_issue ON dbp_mfg_material_issue_lines(issue_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_receipts_tenant ON dbp_mfg_receipts(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_receipts_order ON dbp_mfg_receipts(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_qi_tenant ON dbp_mfg_quality_inspections(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_qi_order ON dbp_mfg_quality_inspections(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_scrap_tenant ON dbp_mfg_scrap(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_scrap_order ON dbp_mfg_scrap(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_costs_tenant ON dbp_mfg_costs(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_costs_order ON dbp_mfg_costs(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_mfg_settings_tenant ON dbp_mfg_settings(tenant_id)",
]

# ─── UNIQUE Constraints ──────────────────────────────
UNIQUES = [
    "ALTER TABLE dbp_mfg_bom ADD CONSTRAINT uq_mfg_bom_code UNIQUE (tenant_id, bom_code)",
    "ALTER TABLE dbp_mfg_work_centers ADD CONSTRAINT uq_mfg_wc_code UNIQUE (tenant_id, code)",
    "ALTER TABLE dbp_mfg_routings ADD CONSTRAINT uq_mfg_routing_code UNIQUE (tenant_id, routing_code)",
    "ALTER TABLE dbp_mfg_orders ADD CONSTRAINT uq_mfg_order_number UNIQUE (tenant_id, order_number)",
    "ALTER TABLE dbp_mfg_material_issues ADD CONSTRAINT uq_mfg_mi_number UNIQUE (tenant_id, issue_number)",
    "ALTER TABLE dbp_mfg_receipts ADD CONSTRAINT uq_mfg_receipt_number UNIQUE (tenant_id, receipt_number)",
    "ALTER TABLE dbp_mfg_quality_inspections ADD CONSTRAINT uq_mfg_qi_number UNIQUE (tenant_id, inspection_number)",
    "ALTER TABLE dbp_mfg_settings ADD CONSTRAINT uq_mfg_setting UNIQUE (tenant_id, setting_key)",
]

# ─── CHECK Constraints ───────────────────────────────
CHECKS = [
    "ALTER TABLE dbp_mfg_bom ADD CONSTRAINT chk_mfg_bom_status CHECK (status IN ('draft','active','inactive','archived'))",
    "ALTER TABLE dbp_mfg_bom_lines ADD CONSTRAINT chk_mfg_bom_line_qty CHECK (qty > 0)",
    "ALTER TABLE dbp_mfg_bom_lines ADD CONSTRAINT chk_mfg_bom_line_scrap CHECK (scrap_pct >= 0 AND scrap_pct <= 100)",
    "ALTER TABLE dbp_mfg_work_centers ADD CONSTRAINT chk_mfg_wc_type CHECK (work_center_type IN ('machine','labor','both'))",
    "ALTER TABLE dbp_mfg_work_centers ADD CONSTRAINT chk_mfg_wc_status CHECK (status IN ('active','inactive','maintenance'))",
    "ALTER TABLE dbp_mfg_work_centers ADD CONSTRAINT chk_mfg_wc_capacity CHECK (capacity_per_hour > 0)",
    "ALTER TABLE dbp_mfg_routings ADD CONSTRAINT chk_mfg_routing_status CHECK (status IN ('draft','active','inactive'))",
    "ALTER TABLE dbp_mfg_routing_steps ADD CONSTRAINT chk_mfg_step_number CHECK (step_number > 0)",
    "ALTER TABLE dbp_mfg_routing_steps ADD CONSTRAINT chk_mfg_step_times CHECK (setup_time_hrs >= 0 AND run_time_hrs >= 0)",
    "ALTER TABLE dbp_mfg_orders ADD CONSTRAINT chk_mfg_order_status CHECK (status IN ('planned','released','in_progress','completed','cancelled'))",
    "ALTER TABLE dbp_mfg_orders ADD CONSTRAINT chk_mfg_order_qty CHECK (qty_planned > 0)",
    "ALTER TABLE dbp_mfg_orders ADD CONSTRAINT chk_mfg_order_priority CHECK (priority >= 1 AND priority <= 10)",
    "ALTER TABLE dbp_mfg_material_issues ADD CONSTRAINT chk_mfg_mi_status CHECK (status IN ('pending','partial','completed','cancelled'))",
    "ALTER TABLE dbp_mfg_material_issue_lines ADD CONSTRAINT chk_mfg_mil_qty CHECK (qty_required > 0)",
    "ALTER TABLE dbp_mfg_receipts ADD CONSTRAINT chk_mfg_receipt_status CHECK (status IN ('pending','completed','cancelled'))",
    "ALTER TABLE dbp_mfg_receipts ADD CONSTRAINT chk_mfg_receipt_qty CHECK (qty_received > 0)",
    "ALTER TABLE dbp_mfg_quality_inspections ADD CONSTRAINT chk_mfg_qi_type CHECK (inspection_type IN ('incoming','in_process','final','random'))",
    "ALTER TABLE dbp_mfg_quality_inspections ADD CONSTRAINT chk_mfg_qi_result CHECK (result IN ('pending','passed','failed','partial'))",
    "ALTER TABLE dbp_mfg_scrap ADD CONSTRAINT chk_mfg_scrap_qty CHECK (qty > 0)",
    "ALTER TABLE dbp_mfg_costs ADD CONSTRAINT chk_mfg_cost_type CHECK (cost_type IN ('material','labor','overhead','setup','scrap','other'))",
]

# ─── DEFAULTS ────────────────────────────────────────
DEFAULTS = [
    "ALTER TABLE dbp_mfg_bom ALTER COLUMN revision SET DEFAULT 'A'",
    "ALTER TABLE dbp_mfg_bom ALTER COLUMN status SET DEFAULT 'draft'",
    "ALTER TABLE dbp_mfg_bom ALTER COLUMN is_active SET DEFAULT TRUE",
    "ALTER TABLE dbp_mfg_bom ALTER COLUMN version SET DEFAULT 1",
    "ALTER TABLE dbp_mfg_work_centers ALTER COLUMN work_center_type SET DEFAULT 'machine'",
    "ALTER TABLE dbp_mfg_work_centers ALTER COLUMN capacity_per_hour SET DEFAULT 1",
    "ALTER TABLE dbp_mfg_work_centers ALTER COLUMN efficiency_pct SET DEFAULT 100",
    "ALTER TABLE dbp_mfg_work_centers ALTER COLUMN status SET DEFAULT 'active'",
    "ALTER TABLE dbp_mfg_orders ALTER COLUMN status SET DEFAULT 'planned'",
    "ALTER TABLE dbp_mfg_orders ALTER COLUMN priority SET DEFAULT 5",
    "ALTER TABLE dbp_mfg_orders ALTER COLUMN qty_completed SET DEFAULT 0",
    "ALTER TABLE dbp_mfg_orders ALTER COLUMN qty_scrapped SET DEFAULT 0",
    "ALTER TABLE dbp_mfg_material_issues ALTER COLUMN status SET DEFAULT 'pending'",
    "ALTER TABLE dbp_mfg_material_issue_lines ALTER COLUMN qty_issued SET DEFAULT 0",
    "ALTER TABLE dbp_mfg_receipts ALTER COLUMN status SET DEFAULT 'completed'",
    "ALTER TABLE dbp_mfg_quality_inspections ALTER COLUMN result SET DEFAULT 'pending'",
]


def migrate():
    with engine.begin() as conn:
        created = 0
        for sql in TABLES:
            try:
                conn.execute(text(sql.strip()))
                created += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"  WARN: {e}")

        idx_created = 0
        for sql in INDEXES:
            try:
                conn.execute(text(sql))
                idx_created += 1
            except Exception:
                pass

        uq_created = 0
        for sql in UNIQUES:
            try:
                conn.execute(text(sql))
                uq_created += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    pass

        chk_created = 0
        for sql in CHECKS:
            try:
                conn.execute(text(sql))
                chk_created += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    pass

        df_created = 0
        for sql in DEFAULTS:
            try:
                conn.execute(text(sql))
                df_created += 1
            except Exception:
                pass

        print(f"P70.8.1 Manufacturing Schema:")
        print(f"  Tables:     {created}/{len(TABLES)}")
        print(f"  Indexes:    {idx_created}/{len(INDEXES)}")
        print(f"  Uniques:    {uq_created}/{len(UNIQUES)}")
        print(f"  Checks:     {chk_created}/{len(CHECKS)}")
        print(f"  Defaults:   {df_created}/{len(DEFAULTS)}")
        print("  DONE")


if __name__ == "__main__":
    migrate()
