"""
P70.3A Hardening Migration — Phase 1: Tenant Isolation + DB Integrity
Adds tenant_id to BOQ, foreign keys, unique constraints, CHECK constraints,
updated_at trigger, audit log table, and bilingual fields.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from database import engine
from sqlalchemy import text

MIGRATION = """
-- ============================================================
-- H1: TENANT ISOLATION — Add tenant_id to BOQ
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'dbp_construction_boq' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE dbp_construction_boq ADD COLUMN tenant_id TEXT DEFAULT '';
        RAISE NOTICE 'Added tenant_id to dbp_construction_boq';
    ELSE
        RAISE NOTICE 'tenant_id already exists on dbp_construction_boq';
    END IF;
END $$;

-- Migrate: set tenant_id from parent project
UPDATE dbp_construction_boq b
SET tenant_id = p.tenant_id
FROM dbp_projects p
WHERE b.project_id = p.id AND (b.tenant_id IS NULL OR b.tenant_id = '');

-- Make tenant_id NOT NULL after migration
ALTER TABLE dbp_construction_boq ALTER COLUMN tenant_id SET NOT NULL;

-- Index for tenant isolation
CREATE INDEX IF NOT EXISTS idx_boq_tenant ON dbp_construction_boq(tenant_id);

-- ============================================================
-- H3: FOREIGN KEY CONSTRAINTS
-- ============================================================
DO $$
BEGIN
    -- BOQ -> Projects
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_boq_project') THEN
        ALTER TABLE dbp_construction_boq
            ADD CONSTRAINT fk_boq_project FOREIGN KEY (project_id)
            REFERENCES dbp_projects(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added FK: boq -> projects';
    END IF;

    -- PR -> Projects (allow empty project_id)
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_pr_project') THEN
        ALTER TABLE dbp_construction_pr
            ADD CONSTRAINT fk_pr_project FOREIGN KEY (project_id)
            REFERENCES dbp_projects(id) ON DELETE SET NULL;
        RAISE NOTICE 'Added FK: pr -> projects';
    END IF;

    -- PO -> Projects (allow empty project_id)
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_po_project') THEN
        ALTER TABLE dbp_construction_po
            ADD CONSTRAINT fk_po_project FOREIGN KEY (project_id)
            REFERENCES dbp_projects(id) ON DELETE SET NULL;
        RAISE NOTICE 'Added FK: po -> projects';
    END IF;

    -- Site Diary -> Projects
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_diary_project') THEN
        ALTER TABLE dbp_construction_site_diary
            ADD CONSTRAINT fk_diary_project FOREIGN KEY (project_id)
            REFERENCES dbp_projects(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added FK: diary -> projects';
    END IF;

    -- Inspections -> Projects
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_insp_project') THEN
        ALTER TABLE dbp_construction_inspections
            ADD CONSTRAINT fk_insp_project FOREIGN KEY (project_id)
            REFERENCES dbp_projects(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added FK: inspections -> projects';
    END IF;

    -- RFI -> Projects
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_rfi_project') THEN
        ALTER TABLE dbp_construction_rfi
            ADD CONSTRAINT fk_rfi_project FOREIGN KEY (project_id)
            REFERENCES dbp_projects(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added FK: rfi -> projects';
    END IF;

    -- Variations -> Projects
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_var_project') THEN
        ALTER TABLE dbp_construction_variations
            ADD CONSTRAINT fk_var_project FOREIGN KEY (project_id)
            REFERENCES dbp_projects(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added FK: variations -> projects';
    END IF;

    -- Equipment -> Projects (nullable)
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_eq_project') THEN
        ALTER TABLE dbp_construction_equipment
            ADD CONSTRAINT fk_eq_project FOREIGN KEY (project_id)
            REFERENCES dbp_projects(id) ON DELETE SET NULL;
        RAISE NOTICE 'Added FK: equipment -> projects';
    END IF;
END $$;

-- ============================================================
-- H3: UNIQUE CONSTRAINTS (per tenant)
-- ============================================================
DO $$
BEGIN
    -- Project code per tenant
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_project_tenant_code') THEN
        ALTER TABLE dbp_projects
            ADD CONSTRAINT uq_project_tenant_code UNIQUE (tenant_id, code);
        RAISE NOTICE 'Added UNIQUE: project (tenant_id, code)';
    END IF;

    -- PR number per tenant
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_pr_tenant_number') THEN
        ALTER TABLE dbp_construction_pr
            ADD CONSTRAINT uq_pr_tenant_number UNIQUE (tenant_id, pr_number);
        RAISE NOTICE 'Added UNIQUE: pr (tenant_id, pr_number)';
    END IF;

    -- PO number per tenant
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_po_tenant_number') THEN
        ALTER TABLE dbp_construction_po
            ADD CONSTRAINT uq_po_tenant_number UNIQUE (tenant_id, po_number);
        RAISE NOTICE 'Added UNIQUE: po (tenant_id, po_number)';
    END IF;

    -- Equipment code per tenant
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_eq_tenant_code') THEN
        ALTER TABLE dbp_construction_equipment
            ADD CONSTRAINT uq_eq_tenant_code UNIQUE (tenant_id, code);
        RAISE NOTICE 'Added UNIQUE: equipment (tenant_id, code)';
    END IF;

    -- Warehouse code per tenant
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_wh_tenant_code') THEN
        ALTER TABLE dbp_construction_warehouses
            ADD CONSTRAINT uq_wh_tenant_code UNIQUE (tenant_id, code);
        RAISE NOTICE 'Added UNIQUE: warehouse (tenant_id, code)';
    END IF;

    -- RFI number per tenant
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_rfi_tenant_number') THEN
        ALTER TABLE dbp_construction_rfi
            ADD CONSTRAINT uq_rfi_tenant_number UNIQUE (tenant_id, rfi_number);
        RAISE NOTICE 'Added UNIQUE: rfi (tenant_id, rfi_number)';
    END IF;

    -- Variation number per tenant
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_var_tenant_number') THEN
        ALTER TABLE dbp_construction_variations
            ADD CONSTRAINT uq_var_tenant_number UNIQUE (tenant_id, var_number);
        RAISE NOTICE 'Added UNIQUE: variation (tenant_id, var_number)';
    END IF;
END $$;

-- ============================================================
-- H3: CHECK CONSTRAINTS
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_project_budget') THEN
        ALTER TABLE dbp_projects ADD CONSTRAINT chk_project_budget CHECK (budget >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_project_actual') THEN
        ALTER TABLE dbp_projects ADD CONSTRAINT chk_project_actual CHECK (actual_cost >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_stock_onhand') THEN
        ALTER TABLE dbp_construction_stock ADD CONSTRAINT chk_stock_onhand CHECK (on_hand >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_stock_reserved') THEN
        ALTER TABLE dbp_construction_stock ADD CONSTRAINT chk_stock_reserved CHECK (reserved >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_stock_reserved_le_onhand') THEN
        ALTER TABLE dbp_construction_stock ADD CONSTRAINT chk_stock_reserved_le_onhand CHECK (reserved <= on_hand);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_boq_qty') THEN
        ALTER TABLE dbp_construction_boq ADD CONSTRAINT chk_boq_qty CHECK (quantity >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_boq_price') THEN
        ALTER TABLE dbp_construction_boq ADD CONSTRAINT chk_boq_price CHECK (unit_price >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_boq_completed') THEN
        ALTER TABLE dbp_construction_boq ADD CONSTRAINT chk_boq_completed CHECK (completed_qty >= 0);
    END IF;
    RAISE NOTICE 'CHECK constraints applied';
END $$;

-- ============================================================
-- UPDATED_AT TRIGGER
-- ============================================================
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$
BEGIN
    -- Projects
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_projects_updated') THEN
        CREATE TRIGGER trg_projects_updated
            BEFORE UPDATE ON dbp_projects
            FOR EACH ROW EXECUTE FUNCTION update_modified_column();
    END IF;
    -- PR
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_pr_updated') THEN
        CREATE TRIGGER trg_pr_updated
            BEFORE UPDATE ON dbp_construction_pr
            FOR EACH ROW EXECUTE FUNCTION update_modified_column();
    END IF;
    -- PO
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_po_updated') THEN
        CREATE TRIGGER trg_po_updated
            BEFORE UPDATE ON dbp_construction_po
            FOR EACH ROW EXECUTE FUNCTION update_modified_column();
    END IF;
    RAISE NOTICE 'updated_at triggers created';
END $$;

-- ============================================================
-- H5: AUDIT TRAIL TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS dbp_construction_audit (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    old_values JSONB DEFAULT '{}',
    new_values JSONB DEFAULT '{}',
    ip_address TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON dbp_construction_audit(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON dbp_construction_audit(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON dbp_construction_audit(created_at);

-- ============================================================
-- H6: BILINGUAL FIELDS
-- ============================================================
DO $$
BEGIN
    -- Projects
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='dbp_projects' AND column_name='name_ar') THEN
        ALTER TABLE dbp_projects ADD COLUMN name_ar TEXT DEFAULT '';
        ALTER TABLE dbp_projects ADD COLUMN description_ar TEXT DEFAULT '';
    END IF;
    -- BOQ
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='dbp_construction_boq' AND column_name='description_ar') THEN
        ALTER TABLE dbp_construction_boq ADD COLUMN description_ar TEXT DEFAULT '';
    END IF;
    -- PR
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='dbp_construction_pr' AND column_name='description_ar') THEN
        ALTER TABLE dbp_construction_pr ADD COLUMN description_ar TEXT DEFAULT '';
    END IF;
    -- PO
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='dbp_construction_po' AND column_name='description_ar') THEN
        ALTER TABLE dbp_construction_po ADD COLUMN description_ar TEXT DEFAULT '';
    END IF;
    -- Equipment
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='dbp_construction_equipment' AND column_name='name_ar') THEN
        ALTER TABLE dbp_construction_equipment ADD COLUMN name_ar TEXT DEFAULT '';
        ALTER TABLE dbp_construction_equipment ADD COLUMN type_ar TEXT DEFAULT '';
    END IF;
    -- Warehouses
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='dbp_construction_warehouses' AND column_name='name_ar') THEN
        ALTER TABLE dbp_construction_warehouses ADD COLUMN name_ar TEXT DEFAULT '';
    END IF;
    -- Subcontractors
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='dbp_construction_subcontractors' AND column_name='name_ar') THEN
        ALTER TABLE dbp_construction_subcontractors ADD COLUMN name_ar TEXT DEFAULT '';
        ALTER TABLE dbp_construction_subcontractors ADD COLUMN trade_ar TEXT DEFAULT '';
    END IF;
    RAISE NOTICE 'Bilingual fields added';
END $$;

-- ============================================================
-- MISSING INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_wh_tenant ON dbp_construction_warehouses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_diary_tenant ON dbp_construction_site_diary(tenant_id);
CREATE INDEX IF NOT EXISTS idx_insp_tenant ON dbp_construction_inspections(tenant_id);
CREATE INDEX IF NOT EXISTS idx_rfi_tenant ON dbp_construction_rfi(tenant_id);
CREATE INDEX IF NOT EXISTS idx_var_tenant ON dbp_construction_variations(tenant_id);
"""

with engine.connect() as conn:
    try:
        conn.execute(text(MIGRATION))
        conn.commit()
        print("Migration completed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
