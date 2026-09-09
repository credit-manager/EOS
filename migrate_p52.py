"""
P52 Migration — Productization & SaaS Launch
Tables: dbp_industry_templates, dbp_module_definitions, dbp_tenant_onboarding
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text

TABLES = {
    "dbp_industry_templates": {
        "columns": [
            ("id", "VARCHAR(36) PRIMARY KEY"),
            ("industry_code", "VARCHAR(50) NOT NULL UNIQUE"),
            ("industry_name", "VARCHAR(200) NOT NULL"),
            ("industry_name_ar", "VARCHAR(200)"),
            ("description", "TEXT"),
            ("default_modules", "JSONB NOT NULL DEFAULT '[]'"),
            ("default_settings", "JSONB NOT NULL DEFAULT '{}'"),
            ("default_accounts", "JSONB NOT NULL DEFAULT '[]'"),
            ("is_active", "BOOLEAN NOT NULL DEFAULT true"),
            ("sort_order", "INTEGER NOT NULL DEFAULT 0"),
            ("created_at", "TIMESTAMP DEFAULT NOW()"),
        ],
        "tenantScoped": False,
    },
    "dbp_module_definitions": {
        "columns": [
            ("id", "VARCHAR(36) PRIMARY KEY"),
            ("module_code", "VARCHAR(50) NOT NULL UNIQUE"),
            ("module_name", "VARCHAR(200) NOT NULL"),
            ("module_name_ar", "VARCHAR(200)"),
            ("description", "TEXT"),
            ("category", "VARCHAR(50) NOT NULL DEFAULT 'core'"),
            ("required_modules", "JSONB NOT NULL DEFAULT '[]'"),
            ("optional_dependencies", "JSONB NOT NULL DEFAULT '[]'"),
            ("default_enabled", "BOOLEAN NOT NULL DEFAULT false"),
            ("sort_order", "INTEGER NOT NULL DEFAULT 0"),
            ("is_active", "BOOLEAN NOT NULL DEFAULT true"),
            ("created_at", "TIMESTAMP DEFAULT NOW()"),
        ],
        "tenantScoped": False,
    },
    "dbp_tenant_onboarding": {
        "columns": [
            ("id", "VARCHAR(36) PRIMARY KEY"),
            ("tenant_id", "VARCHAR(100) NOT NULL"),
            ("company_id", "VARCHAR(36)"),
            ("industry_code", "VARCHAR(50)"),
            ("plan_id", "VARCHAR(36)"),
            ("current_step", "VARCHAR(50) NOT NULL DEFAULT 'industry_selection'"),
            ("status", "VARCHAR(30) NOT NULL DEFAULT 'in_progress'"),
            ("company_name", "VARCHAR(200)"),
            ("company_name_ar", "VARCHAR(200)"),
            ("admin_user_id", "VARCHAR(100)"),
            ("admin_email", "VARCHAR(200)"),
            ("selected_modules", "JSONB NOT NULL DEFAULT '[]'"),
            ("configuration", "JSONB NOT NULL DEFAULT '{}'"),
            ("steps_completed", "JSONB NOT NULL DEFAULT '[]'"),
            ("steps_data", "JSONB NOT NULL DEFAULT '{}'"),
            ("activated_at", "TIMESTAMP"),
            ("created_at", "TIMESTAMP DEFAULT NOW()"),
            ("updated_at", "TIMESTAMP DEFAULT NOW()"),
        ],
        "tenantScoped": True,
        "tenantColumn": "tenant_id",
    },
}

INDICES = {
    "dbp_industry_templates": [
        "CREATE INDEX IF NOT EXISTS idx_industry_code ON dbp_industry_templates(industry_code)",
    ],
    "dbp_module_definitions": [
        "CREATE INDEX IF NOT EXISTS idx_module_code ON dbp_module_definitions(module_code)",
        "CREATE INDEX IF NOT EXISTS idx_module_category ON dbp_module_definitions(category)",
    ],
    "dbp_tenant_onboarding": [
        "CREATE INDEX IF NOT EXISTS idx_onboarding_tenant ON dbp_tenant_onboarding(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_onboarding_status ON dbp_tenant_onboarding(status)",
        "CREATE INDEX IF NOT EXISTS idx_onboarding_step ON dbp_tenant_onboarding(current_step)",
    ],
}

INDUSTRY_SEEDS = [
    {
        "id": "ind-construction", "industry_code": "construction",
        "industry_name": "Construction & Contracting",
        "industry_name_ar": "\u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a \u0648\u0627\u0644\u0628\u0646\u0627\u0621",
        "description": "Building construction, civil engineering, and contracting",
        "default_modules": ["accounting", "finance", "procurement", "inventory", "projects", "hr", "sales", "documents", "workflow"],
        "default_settings": {"base_currency": "SAR", "fiscal_year_start": "01-01", "tax_system": "vat"},
        "default_accounts": [
            {"code": "1000", "name": "Cash", "account_type": "asset"},
            {"code": "1100", "name": "Bank Account", "account_type": "asset"},
            {"code": "1200", "name": "Accounts Receivable", "account_type": "asset"},
            {"code": "1300", "name": "Inventory - Materials", "account_type": "asset"},
            {"code": "2000", "name": "Accounts Payable", "account_type": "liability"},
            {"code": "2100", "name": "Tax Payable", "account_type": "liability"},
            {"code": "3000", "name": "Owner's Equity", "account_type": "equity"},
            {"code": "4000", "name": "Construction Revenue", "account_type": "revenue"},
            {"code": "5000", "name": "Material Costs", "account_type": "expense"},
            {"code": "5100", "name": "Labor Costs", "account_type": "expense"},
            {"code": "5200", "name": "Equipment Costs", "account_type": "expense"},
        ],
    },
    {
        "id": "ind-trading", "industry_code": "trading",
        "industry_name": "Trading & Distribution",
        "industry_name_ar": "\u0627\u0644\u062a\u062c\u0627\u0631\u0629 \u0648\u0627\u0644\u062a\u0648\u0632\u064a\u0639",
        "description": "Wholesale, distribution, and import/export",
        "default_modules": ["accounting", "finance", "procurement", "inventory", "sales", "hr", "documents"],
        "default_settings": {"base_currency": "SAR", "fiscal_year_start": "01-01", "tax_system": "vat"},
        "default_accounts": [
            {"code": "1000", "name": "Cash", "account_type": "asset"},
            {"code": "1100", "name": "Bank Account", "account_type": "asset"},
            {"code": "1200", "name": "Accounts Receivable", "account_type": "asset"},
            {"code": "1300", "name": "Inventory", "account_type": "asset"},
            {"code": "2000", "name": "Accounts Payable", "account_type": "liability"},
            {"code": "3000", "name": "Owner's Equity", "account_type": "equity"},
            {"code": "4000", "name": "Sales Revenue", "account_type": "revenue"},
            {"code": "5000", "name": "Cost of Goods Sold", "account_type": "expense"},
        ],
    },
    {
        "id": "ind-retail", "industry_code": "retail",
        "industry_name": "Retail & E-Commerce",
        "industry_name_ar": "\u0627\u0644\u062a\u062c\u0632\u0626\u0629 \u0648\u0627\u0644\u062a\u062c\u0627\u0631\u0629 \u0627\u0644\u0625\u0644\u0643\u062a\u0631\u0648\u0646\u064a\u0629",
        "description": "Physical stores, online shops, POS",
        "default_modules": ["accounting", "finance", "inventory", "sales", "hr", "documents"],
        "default_settings": {"base_currency": "SAR", "fiscal_year_start": "01-01", "tax_system": "vat"},
        "default_accounts": [
            {"code": "1000", "name": "Cash", "account_type": "asset"},
            {"code": "1100", "name": "Bank Account", "account_type": "asset"},
            {"code": "1300", "name": "Inventory", "account_type": "asset"},
            {"code": "2000", "name": "Accounts Payable", "account_type": "liability"},
            {"code": "3000", "name": "Owner's Equity", "account_type": "equity"},
            {"code": "4000", "name": "Sales Revenue", "account_type": "revenue"},
            {"code": "5000", "name": "Cost of Goods Sold", "account_type": "expense"},
        ],
    },
    {
        "id": "ind-restaurant", "industry_code": "restaurant",
        "industry_name": "Restaurant & Food Service",
        "industry_name_ar": "\u0627\u0644\u0645\u0637\u0639\u0627\u0645 \u0648\u0627\u0644\u062e\u062f\u0645\u0629 \u0627\u0644\u063a\u0630\u0627\u0626\u064a\u0629",
        "description": "Restaurants, cafes, catering, cloud kitchens",
        "default_modules": ["accounting", "finance", "inventory", "sales", "hr", "documents"],
        "default_settings": {"base_currency": "SAR", "fiscal_year_start": "01-01", "tax_system": "vat"},
        "default_accounts": [
            {"code": "1000", "name": "Cash", "account_type": "asset"},
            {"code": "1100", "name": "Bank Account", "account_type": "asset"},
            {"code": "1300", "name": "Inventory - Food", "account_type": "asset"},
            {"code": "2000", "name": "Accounts Payable", "account_type": "liability"},
            {"code": "3000", "name": "Owner's Equity", "account_type": "equity"},
            {"code": "4000", "name": "Food Sales Revenue", "account_type": "revenue"},
            {"code": "5000", "name": "Food Cost", "account_type": "expense"},
            {"code": "5100", "name": "Labor Cost", "account_type": "expense"},
        ],
    },
    {
        "id": "ind-services", "industry_code": "services",
        "industry_name": "Professional Services",
        "industry_name_ar": "\u0627\u0644\u062e\u062f\u0645\u0627\u062a \u0627\u0644\u0645\u0647\u0646\u064a\u0629",
        "description": "Consulting, IT, legal, accounting, marketing",
        "default_modules": ["accounting", "finance", "projects", "hr", "sales", "documents", "workflow"],
        "default_settings": {"base_currency": "SAR", "fiscal_year_start": "01-01", "tax_system": "vat"},
        "default_accounts": [
            {"code": "1000", "name": "Cash", "account_type": "asset"},
            {"code": "1100", "name": "Bank Account", "account_type": "asset"},
            {"code": "1200", "name": "Accounts Receivable", "account_type": "asset"},
            {"code": "2000", "name": "Accounts Payable", "account_type": "liability"},
            {"code": "3000", "name": "Owner's Equity", "account_type": "equity"},
            {"code": "4000", "name": "Service Revenue", "account_type": "revenue"},
            {"code": "5000", "name": "Operating Expenses", "account_type": "expense"},
            {"code": "5100", "name": "Staff Costs", "account_type": "expense"},
        ],
    },
    {
        "id": "ind-manufacturing", "industry_code": "manufacturing",
        "industry_name": "Manufacturing & Production",
        "industry_name_ar": "\u0627\u0644\u062a\u0635\u0646\u064a\u0639 \u0648\u0627\u0644\u0625\u0646\u062a\u0627\u062c",
        "description": "Factory production, assembly, raw materials",
        "default_modules": ["accounting", "finance", "procurement", "inventory", "projects", "hr", "documents", "fixed_assets"],
        "default_settings": {"base_currency": "SAR", "fiscal_year_start": "01-01", "tax_system": "vat"},
        "default_accounts": [
            {"code": "1000", "name": "Cash", "account_type": "asset"},
            {"code": "1100", "name": "Bank Account", "account_type": "asset"},
            {"code": "1300", "name": "Raw Materials", "account_type": "asset"},
            {"code": "1400", "name": "Work in Progress", "account_type": "asset"},
            {"code": "1500", "name": "Finished Goods", "account_type": "asset"},
            {"code": "2000", "name": "Accounts Payable", "account_type": "liability"},
            {"code": "3000", "name": "Owner's Equity", "account_type": "equity"},
            {"code": "4000", "name": "Sales Revenue", "account_type": "revenue"},
            {"code": "5000", "name": "Raw Material Cost", "account_type": "expense"},
            {"code": "5100", "name": "Direct Labor", "account_type": "expense"},
            {"code": "5200", "name": "Manufacturing Overhead", "account_type": "expense"},
        ],
    },
]

MODULE_SEEDS = [
    {"id": "mod-accounting", "module_code": "accounting", "module_name": "Accounting & Journal", "module_name_ar": "\u0627\u0644\u0645\u062d\u0627\u0633\u0628\u0627\u062a \u0648\u0627\u0644\u0642\u064a\u0648\u062f", "description": "Chart of accounts, journal entries, trial balance", "category": "financial", "default_enabled": True, "sort_order": 1},
    {"id": "mod-finance", "module_code": "finance", "module_name": "Finance & Treasury", "module_name_ar": "\u0627\u0644\u0645\u0627\u0644\u064a\u0629 \u0648\u0627\u0644\u062e\u0632\u064a\u0646\u0629", "description": "Bank accounts, payments, budgets", "category": "financial", "default_enabled": True, "sort_order": 2},
    {"id": "mod-procurement", "module_code": "procurement", "module_name": "Procurement & POs", "module_name_ar": "\u0627\u0644\u0645\u0634\u062a\u0631\u064a\u0627\u062a", "description": "Suppliers, purchase requests, POs, GRN", "category": "operations", "sort_order": 3},
    {"id": "mod-inventory", "module_code": "inventory", "module_name": "Inventory & Warehouses", "module_name_ar": "\u0627\u0644\u0645\u062e\u0632\u0646 \u0648\u0627\u0644\u0645\u0633\u062a\u0648\u062f\u0639\u0627\u062a", "description": "Items, warehouses, stock movements", "category": "operations", "sort_order": 4},
    {"id": "mod-sales", "module_code": "sales", "module_name": "Sales & Invoicing", "module_name_ar": "\u0627\u0644\u0645\u0628\u064a\u0639\u0627\u062a \u0648\u0627\u0644\u0641\u0648\u0627\u062a\u064a\u0631", "description": "Customers, quotations, orders, invoices", "category": "operations", "sort_order": 5},
    {"id": "mod-hr", "module_code": "hr", "module_name": "Human Resources", "module_name_ar": "\u0627\u0644\u0645\u0648\u0627\u0631\u062f \u0627\u0644\u0628\u0634\u0631\u064a\u0629", "description": "Employees, leave, attendance, payroll", "category": "people", "sort_order": 6},
    {"id": "mod-projects", "module_code": "projects", "module_name": "Project Management", "module_name_ar": "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0645\u0634\u0627\u0631\u064a\u0639", "description": "Projects, tasks, milestones, time tracking", "category": "operations", "sort_order": 7},
    {"id": "mod-documents", "module_code": "documents", "module_name": "Document Management", "module_name_ar": "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0645\u0633\u062a\u0646\u062f\u0627\u0639\u0627\u062a", "description": "Folders, documents, versions, tags", "category": "core", "sort_order": 8},
    {"id": "mod-workflow", "module_code": "workflow", "module_name": "Workflow & Approvals", "module_name_ar": "\u0623\u0633\u0644\u0648\u0628 \u0627\u0644\u0639\u0645\u0644 \u0648\u0627\u0644\u062a\u0635\u0631\u064a\u062d\u0627\u062a", "description": "Approval workflows, e-signatures", "category": "core", "sort_order": 9},
    {"id": "mod-fixed_assets", "module_code": "fixed_assets", "module_name": "Fixed Assets", "module_name_ar": "\u0627\u0644\u0623\u0635\u0648\u0644 \u0627\u0644\u062b\u0627\u0628\u062a\u0629", "description": "Asset register, depreciation", "category": "financial", "sort_order": 10},
    {"id": "mod-audit", "module_code": "audit", "module_name": "Audit & Compliance", "module_name_ar": "\u0627\u0644\u062a\u062f\u0642\u0642 \u0648\u0627\u0644\u0627\u0645\u062a\u062b\u0627\u0644", "description": "Audit trail, compliance rules", "category": "core", "default_enabled": True, "sort_order": 11},
    {"id": "mod-bi", "module_code": "bi", "module_name": "BI & Reporting", "module_name_ar": "\u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u062a\u062c\u0627\u0631\u064a \u0648\u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631", "description": "Dashboards, reports, analytics", "category": "intelligence", "sort_order": 12},
]


def migrate():
    with engine.begin() as conn:
        for tbl_name, tbl_def in TABLES.items():
            cols = ", ".join(f"{c[0]} {c[1]}" for c in tbl_def["columns"])
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {tbl_name} ({cols})"))
            print(f"  [OK] {tbl_name}")

        for tbl_name, indices in INDICES.items():
            for idx_sql in indices:
                conn.execute(text(idx_sql))
            print(f"  [OK] Indices for {tbl_name}")

        for seed in INDUSTRY_SEEDS:
            existing = conn.execute(text("SELECT id FROM dbp_industry_templates WHERE id=:id"), {"id": seed["id"]}).fetchone()
            if not existing:
                import json as _json
                conn.execute(text(
                    "INSERT INTO dbp_industry_templates "
                    "(id, industry_code, industry_name, industry_name_ar, description, default_modules, default_settings, default_accounts) "
                    "VALUES (:id, :code, :name, :name_ar, :desc, :modules, :settings, :accounts)"
                ), {
                    "id": seed["id"], "code": seed["industry_code"], "name": seed["industry_name"],
                    "name_ar": seed["industry_name_ar"], "desc": seed["description"],
                    "modules": _json.dumps(seed["default_modules"]),
                    "settings": _json.dumps(seed["default_settings"]),
                    "accounts": _json.dumps(seed["default_accounts"]),
                })
        print(f"  [OK] Seeded {len(INDUSTRY_SEEDS)} industry templates")

        for seed in MODULE_SEEDS:
            existing = conn.execute(text("SELECT id FROM dbp_module_definitions WHERE id=:id"), {"id": seed["id"]}).fetchone()
            if not existing:
                import json as _json
                conn.execute(text(
                    "INSERT INTO dbp_module_definitions "
                    "(id, module_code, module_name, module_name_ar, description, category, "
                    "required_modules, optional_dependencies, default_enabled, sort_order) "
                    "VALUES (:id, :code, :name, :name_ar, :desc, :cat, :req, :opt, :def, :sort)"
                ), {
                    "id": seed["id"], "code": seed["module_code"], "name": seed["module_name"],
                    "name_ar": seed["module_name_ar"], "desc": seed["description"],
                    "cat": seed["category"],
                    "req": _json.dumps(seed.get("required_modules", [])),
                    "opt": _json.dumps(seed.get("optional_dependencies", [])),
                    "def": seed.get("default_enabled", False), "sort": seed.get("sort_order", 0),
                })
        print(f"  [OK] Seeded {len(MODULE_SEEDS)} module definitions")


if __name__ == "__main__":
    print("=" * 60)
    print("  P52 MIGRATION — Productization & SaaS Launch")
    print("=" * 60)
    migrate()
    print("  DONE")
