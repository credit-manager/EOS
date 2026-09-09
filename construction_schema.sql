-- EOS Construction ERP Professional — Database Schema
-- Adds construction-specific tables on top of P69 base.

-- ═══════════════════════════════════════════════════
-- 1. PROJECTS (enhanced)
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_projects (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'planning',
    start_date DATE,
    end_date DATE,
    budget NUMERIC(18,2) DEFAULT 0,
    actual_cost NUMERIC(18,2) DEFAULT 0,
    progress NUMERIC(5,2) DEFAULT 0,
    client_name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_projects_tenant ON dbp_projects(tenant_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON dbp_projects(tenant_id, status);

-- ═══════════════════════════════════════════════════
-- 2. BOQ — Bill of Quantities
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_boq (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    item_number TEXT NOT NULL,
    description TEXT DEFAULT '',
    unit TEXT DEFAULT 'ea',
    quantity NUMERIC(18,4) DEFAULT 0,
    unit_price NUMERIC(18,4) DEFAULT 0,
    amount NUMERIC(18,2) DEFAULT 0,
    completed_qty NUMERIC(18,4) DEFAULT 0,
    completed_amount NUMERIC(18,2) DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_boq_project ON dbp_construction_boq(project_id);

-- ═══════════════════════════════════════════════════
-- 3. PURCHASE REQUESTS
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_pr (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    pr_number TEXT NOT NULL,
    project_id TEXT DEFAULT '',
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    total_amount NUMERIC(18,2) DEFAULT 0,
    requested_by TEXT DEFAULT '',
    items_json TEXT DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pr_tenant ON dbp_construction_pr(tenant_id);

-- ═══════════════════════════════════════════════════
-- 4. PURCHASE ORDERS
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_po (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    po_number TEXT NOT NULL,
    supplier_name TEXT DEFAULT '',
    project_id TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    total_amount NUMERIC(18,2) DEFAULT 0,
    po_date DATE,
    delivery_date DATE,
    items_json TEXT DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_po_tenant ON dbp_construction_po(tenant_id);

-- ═══════════════════════════════════════════════════
-- 5. STOCK — Materials & Inventory
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_stock (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    item_code TEXT NOT NULL,
    item_name TEXT DEFAULT '',
    warehouse_id TEXT DEFAULT 'default',
    on_hand NUMERIC(18,4) DEFAULT 0,
    reserved NUMERIC(18,4) DEFAULT 0,
    min_stock NUMERIC(18,4) DEFAULT 0,
    unit_cost NUMERIC(18,4) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stock_tenant ON dbp_construction_stock(tenant_id);

-- ═══════════════════════════════════════════════════
-- 6. WAREHOUSES
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_warehouses (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    address TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════
-- 7. EQUIPMENT
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_equipment (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT DEFAULT '',
    status TEXT DEFAULT 'available',
    project_id TEXT,
    hourly_rate NUMERIC(18,2) DEFAULT 0,
    total_hours NUMERIC(18,2) DEFAULT 0,
    total_fuel NUMERIC(18,2) DEFAULT 0,
    total_maintenance NUMERIC(18,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_equipment_tenant ON dbp_construction_equipment(tenant_id);

-- ═══════════════════════════════════════════════════
-- 8. SITE DIARY
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_site_diary (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    diary_date DATE NOT NULL,
    weather TEXT DEFAULT '',
    manpower_count INTEGER DEFAULT 0,
    equipment_list TEXT DEFAULT '',
    work_progress TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_by TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_diary_project ON dbp_construction_site_diary(project_id);

-- ═══════════════════════════════════════════════════
-- 9. INSPECTIONS
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_inspections (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    inspection_date DATE NOT NULL,
    type TEXT DEFAULT '',
    result TEXT DEFAULT '',
    inspector TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_inspections_project ON dbp_construction_inspections(project_id);

-- ═══════════════════════════════════════════════════
-- 10. RFIs — Request for Information
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_rfi (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    rfi_number TEXT NOT NULL,
    subject TEXT DEFAULT '',
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'open',
    response TEXT DEFAULT '',
    sent_date DATE,
    response_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rfi_project ON dbp_construction_rfi(project_id);

-- ═══════════════════════════════════════════════════
-- 11. SUBCONTRACTORS
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_subcontractors (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    trade TEXT DEFAULT '',
    contact_person TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    total_contracts NUMERIC(18,2) DEFAULT 0,
    total_paid NUMERIC(18,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sub_tenant ON dbp_construction_subcontractors(tenant_id);

-- ═══════════════════════════════════════════════════
-- 12. VARIATION ORDERS
-- ═══════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dbp_construction_variations (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    var_number TEXT NOT NULL,
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    amount NUMERIC(18,2) DEFAULT 0,
    status TEXT DEFAULT 'draft',
    approved_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_var_project ON dbp_construction_variations(project_id);
