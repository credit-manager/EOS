import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from database import engine
from sqlalchemy import text

tables = [
    ("dbp_projects", """
    CREATE TABLE IF NOT EXISTS dbp_projects (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, code TEXT NOT NULL,
        name TEXT NOT NULL, status TEXT DEFAULT 'planning', start_date DATE,
        end_date DATE, budget NUMERIC(18,2) DEFAULT 0, actual_cost NUMERIC(18,2) DEFAULT 0,
        progress NUMERIC(5,2) DEFAULT 0, client_name TEXT DEFAULT '', description TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_projects_idx", "CREATE INDEX IF NOT EXISTS idx_projects_tenant ON dbp_projects(tenant_id)"),

    ("dbp_construction_boq", """
    CREATE TABLE IF NOT EXISTS dbp_construction_boq (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL, item_number TEXT NOT NULL,
        description TEXT DEFAULT '', unit TEXT DEFAULT 'ea', quantity NUMERIC(18,4) DEFAULT 0,
        unit_price NUMERIC(18,4) DEFAULT 0, amount NUMERIC(18,2) DEFAULT 0,
        completed_qty NUMERIC(18,4) DEFAULT 0, completed_amount NUMERIC(18,2) DEFAULT 0,
        status TEXT DEFAULT 'pending', created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_boq_idx", "CREATE INDEX IF NOT EXISTS idx_boq_project ON dbp_construction_boq(project_id)"),

    ("dbp_construction_pr", """
    CREATE TABLE IF NOT EXISTS dbp_construction_pr (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, pr_number TEXT NOT NULL,
        project_id TEXT DEFAULT '', description TEXT DEFAULT '', status TEXT DEFAULT 'draft',
        total_amount NUMERIC(18,2) DEFAULT 0, requested_by TEXT DEFAULT '',
        items_json TEXT DEFAULT '[]', created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_pr_idx", "CREATE INDEX IF NOT EXISTS idx_pr_tenant ON dbp_construction_pr(tenant_id)"),

    ("dbp_construction_po", """
    CREATE TABLE IF NOT EXISTS dbp_construction_po (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, po_number TEXT NOT NULL,
        supplier_name TEXT DEFAULT '', project_id TEXT DEFAULT '', status TEXT DEFAULT 'draft',
        total_amount NUMERIC(18,2) DEFAULT 0, po_date DATE, delivery_date DATE,
        items_json TEXT DEFAULT '[]', created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_po_idx", "CREATE INDEX IF NOT EXISTS idx_po_tenant ON dbp_construction_po(tenant_id)"),

    ("dbp_construction_stock", """
    CREATE TABLE IF NOT EXISTS dbp_construction_stock (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, item_code TEXT NOT NULL,
        item_name TEXT DEFAULT '', warehouse_id TEXT DEFAULT 'default',
        on_hand NUMERIC(18,4) DEFAULT 0, reserved NUMERIC(18,4) DEFAULT 0,
        min_stock NUMERIC(18,4) DEFAULT 0, unit_cost NUMERIC(18,4) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_stock_idx", "CREATE INDEX IF NOT EXISTS idx_stock_tenant ON dbp_construction_stock(tenant_id)"),

    ("dbp_construction_warehouses", """
    CREATE TABLE IF NOT EXISTS dbp_construction_warehouses (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, code TEXT NOT NULL,
        name TEXT NOT NULL, address TEXT DEFAULT '', created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),

    ("dbp_construction_equipment", """
    CREATE TABLE IF NOT EXISTS dbp_construction_equipment (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, code TEXT NOT NULL,
        name TEXT NOT NULL, type TEXT DEFAULT '', status TEXT DEFAULT 'available',
        project_id TEXT, hourly_rate NUMERIC(18,2) DEFAULT 0,
        total_hours NUMERIC(18,2) DEFAULT 0, total_fuel NUMERIC(18,2) DEFAULT 0,
        total_maintenance NUMERIC(18,2) DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_equipment_idx", "CREATE INDEX IF NOT EXISTS idx_equipment_tenant ON dbp_construction_equipment(tenant_id)"),

    ("dbp_construction_site_diary", """
    CREATE TABLE IF NOT EXISTS dbp_construction_site_diary (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
        diary_date DATE NOT NULL, weather TEXT DEFAULT '', manpower_count INTEGER DEFAULT 0,
        equipment_list TEXT DEFAULT '', work_progress TEXT DEFAULT '',
        notes TEXT DEFAULT '', created_by TEXT DEFAULT '', created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_site_diary_idx", "CREATE INDEX IF NOT EXISTS idx_diary_project ON dbp_construction_site_diary(project_id)"),

    ("dbp_construction_inspections", """
    CREATE TABLE IF NOT EXISTS dbp_construction_inspections (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
        inspection_date DATE NOT NULL, type TEXT DEFAULT '', result TEXT DEFAULT '',
        inspector TEXT DEFAULT '', notes TEXT DEFAULT '', created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_inspections_idx", "CREATE INDEX IF NOT EXISTS idx_inspections_project ON dbp_construction_inspections(project_id)"),

    ("dbp_construction_rfi", """
    CREATE TABLE IF NOT EXISTS dbp_construction_rfi (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
        rfi_number TEXT NOT NULL, subject TEXT DEFAULT '', description TEXT DEFAULT '',
        status TEXT DEFAULT 'open', response TEXT DEFAULT '', sent_date DATE,
        response_date DATE, created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_rfi_idx", "CREATE INDEX IF NOT EXISTS idx_rfi_project ON dbp_construction_rfi(project_id)"),

    ("dbp_construction_subcontractors", """
    CREATE TABLE IF NOT EXISTS dbp_construction_subcontractors (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, name TEXT NOT NULL,
        trade TEXT DEFAULT '', contact_person TEXT DEFAULT '', phone TEXT DEFAULT '',
        email TEXT DEFAULT '', total_contracts NUMERIC(18,2) DEFAULT 0,
        total_paid NUMERIC(18,2) DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_subcontractors_idx", "CREATE INDEX IF NOT EXISTS idx_sub_tenant ON dbp_construction_subcontractors(tenant_id)"),

    ("dbp_construction_variations", """
    CREATE TABLE IF NOT EXISTS dbp_construction_variations (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
        var_number TEXT NOT NULL, title TEXT DEFAULT '', description TEXT DEFAULT '',
        amount NUMERIC(18,2) DEFAULT 0, status TEXT DEFAULT 'draft',
        approved_date DATE, created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_construction_variations_idx", "CREATE INDEX IF NOT EXISTS idx_var_project ON dbp_construction_variations(project_id)"),

    ("dbp_journal_entries", """
    CREATE TABLE IF NOT EXISTS dbp_journal_entries (
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, company_id TEXT DEFAULT '',
        entry_number TEXT NOT NULL, entry_date DATE, description TEXT DEFAULT '',
        total_debit NUMERIC(18,2) DEFAULT 0, total_credit NUMERIC(18,2) DEFAULT 0,
        status TEXT DEFAULT 'draft', source_type TEXT DEFAULT '', source_id TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_journal_entries_idx", "CREATE INDEX IF NOT EXISTS idx_je_tenant ON dbp_journal_entries(tenant_id)"),

    ("dbp_journal_lines", """
    CREATE TABLE IF NOT EXISTS dbp_journal_lines (
        id TEXT PRIMARY KEY, journal_id TEXT NOT NULL, account_code TEXT NOT NULL,
        description TEXT DEFAULT '', debit NUMERIC(18,2) DEFAULT 0,
        credit NUMERIC(18,2) DEFAULT 0, cost_center TEXT DEFAULT '',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )"""),
    ("dbp_journal_lines_idx", "CREATE INDEX IF NOT EXISTS idx_jl_journal ON dbp_journal_lines(journal_id)"),
]

with engine.connect() as conn:
    for name, sql in tables:
        try:
            conn.execute(text(sql))
            conn.commit()
            print(f"  OK: {name}")
        except Exception as e:
            err = str(e)[:60]
            if "already exists" in err:
                print(f"  EXISTS: {name}")
            else:
                print(f"  ERROR: {name} - {err}")
            conn.rollback()

    # Final count
    result = conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND (tablename LIKE 'dbp_construction_%' OR tablename LIKE 'dbp_journal_%' OR tablename = 'dbp_projects') ORDER BY tablename"
    )).fetchall()
    print(f"\nTotal construction tables: {len(result)}")
    for t in result:
        print(f"  {t[0]}")
