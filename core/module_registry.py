"""
EOS Industry Framework — Module Registry & Industry Templates
Defines modules, their capabilities, and which industries use them.
"""

from typing import Any

# ═══════════════════════════════════════════════════
# Module Registry — every module registers itself
# ═══════════════════════════════════════════════════

MODULE_REGISTRY: dict[str, dict[str, Any]] = {
    # ─── Core Modules ───────────────────────────
    "accounting": {
        "name": "Accounting",
        "name_ar": "المحاسبة",
        "category": "financial",
        "icon": "AccountBookOutlined",
        "description": "Chart of accounts, journal entries, financial statements",
        "capabilities": ["journal_entries", "trial_balance", "income_statement", "balance_sheet"],
        "entities": ["account", "journal_entry", "journal_line"],
        "permissions": ["accounting.view", "accounting.create", "accounting.post"],
        "menu": {"label": "Accounting", "labelAr": "المحاسبة", "path": "/accounting", "icon": "AccountBookOutlined"},
        "dashboard_widgets": ["financial_summary", "recent_journals"],
        "dependencies": [],
    },
    "inventory": {
        "name": "Inventory",
        "name_ar": "المخزون",
        "category": "operations",
        "icon": "ShopOutlined",
        "description": "Items, warehouses, stock movements",
        "capabilities": ["stock_management", "warehouse_management", "stock_movements"],
        "entities": ["item", "warehouse", "stock", "stock_movement"],
        "permissions": ["inventory.view", "inventory.create", "inventory.adjust"],
        "menu": {"label": "Inventory", "labelAr": "المخزون", "path": "/inventory", "icon": "ShopOutlined"},
        "dashboard_widgets": ["stock_summary", "low_stock_alerts"],
        "dependencies": [],
    },
    "sales": {
        "name": "Sales & CRM",
        "name_ar": "المبيعات",
        "category": "commercial",
        "icon": "ShoppingCartOutlined",
        "description": "Customers, quotations, invoices, pipeline",
        "capabilities": ["customers", "quotations", "invoices", "pipeline"],
        "entities": ["customer", "quotation", "invoice", "lead"],
        "permissions": ["sales.view", "sales.create", "sales.invoice"],
        "menu": {"label": "Sales", "labelAr": "المبيعات", "path": "/sales", "icon": "ShoppingCartOutlined"},
        "dashboard_widgets": ["sales_pipeline", "recent_invoices"],
        "dependencies": [],
    },
    "hr": {
        "name": "Human Resources",
        "name_ar": "الموارد البشرية",
        "category": "people",
        "icon": "TeamOutlined",
        "description": "Employees, attendance, payroll, leave",
        "capabilities": ["employees", "attendance", "payroll", "leave"],
        "entities": ["employee", "department", "attendance", "payroll_run"],
        "permissions": ["hr.view", "hr.manage", "hr.payroll"],
        "menu": {"label": "HR", "labelAr": "الموارد البشرية", "path": "/hr", "icon": "TeamOutlined"},
        "dashboard_widgets": ["headcount", "attendance_summary"],
        "dependencies": [],
    },
    "procurement": {
        "name": "Procurement",
        "name_ar": "المشتريات",
        "category": "operations",
        "icon": "ImportOutlined",
        "description": "Purchase requests, orders, goods receipt",
        "capabilities": ["purchase_requests", "purchase_orders", "goods_receipt"],
        "entities": ["purchase_request", "purchase_order", "grn"],
        "permissions": ["procurement.view", "procurement.create", "procurement.approve"],
        "menu": {"label": "Procurement", "labelAr": "المشتريات", "path": "/procurement", "icon": "ImportOutlined"},
        "dashboard_widgets": ["pending_pos", "procurement_value"],
        "dependencies": ["inventory"],
    },
    "projects": {
        "name": "Project Management",
        "name_ar": "إدارة المشاريع",
        "category": "operations",
        "icon": "ProjectOutlined",
        "description": "Projects, tasks, milestones, time tracking",
        "capabilities": ["projects", "tasks", "milestones", "time_tracking"],
        "entities": ["project", "project_task", "milestone"],
        "permissions": ["projects.view", "projects.create", "projects.manage"],
        "menu": {"label": "Projects", "labelAr": "المشاريع", "path": "/projects", "icon": "ProjectOutlined"},
        "dashboard_widgets": ["project_progress", "upcoming_milestones"],
        "dependencies": [],
    },
    "documents": {
        "name": "Document Management",
        "name_ar": "المستندات",
        "category": "core",
        "icon": "FileTextOutlined",
        "description": "Document storage, versioning, tags",
        "capabilities": ["document_storage", "versioning", "tags"],
        "entities": ["document", "document_version"],
        "permissions": ["documents.view", "documents.upload", "documents.delete"],
        "menu": {"label": "Documents", "labelAr": "المستندات", "path": "/documents", "icon": "FileTextOutlined"},
        "dashboard_widgets": [],
        "dependencies": [],
    },
    "workflow": {
        "name": "Workflow & Approvals",
        "name_ar": "سير العمل",
        "category": "core",
        "icon": "SyncOutlined",
        "description": "Approval workflows, routing, notifications",
        "capabilities": ["approvals", "routing", "notifications"],
        "entities": ["workflow_definition", "workflow_instance"],
        "permissions": ["workflow.view", "workflow.approve"],
        "menu": {"label": "Workflows", "labelAr": "سير العمل", "path": "/workflows", "icon": "SyncOutlined"},
        "dashboard_widgets": ["pending_approvals"],
        "dependencies": [],
    },

    # ─── Construction-specific ──────────────────
    "boq": {
        "name": "Bill of Quantities",
        "name_ar": "جدول الكميات",
        "category": "construction",
        "icon": "UnorderedListOutlined",
        "description": "BOQ items, quantities, rates, progress",
        "capabilities": ["boq_items", "quantity_tracking", "progress_tracking"],
        "entities": ["boq_item"],
        "permissions": ["boq.view", "boq.create", "boq.update"],
        "menu": {"label": "BOQ", "labelAr": "جدول الكميات", "path": "/boq", "icon": "UnorderedListOutlined"},
        "dashboard_widgets": ["boq_progress"],
        "dependencies": ["projects"],
    },
    "equipment": {
        "name": "Equipment & Assets",
        "name_ar": "المعدات والأصول",
        "category": "construction",
        "icon": "ToolOutlined",
        "description": "Equipment tracking, maintenance, depreciation",
        "capabilities": ["equipment_tracking", "maintenance", "depreciation"],
        "entities": ["equipment", "maintenance_log"],
        "permissions": ["equipment.view", "equipment.manage"],
        "menu": {"label": "Equipment", "labelAr": "المعدات", "path": "/equipment", "icon": "ToolOutlined"},
        "dashboard_widgets": ["equipment_status"],
        "dependencies": [],
    },

    # ─── Trading-specific ───────────────────────
    "pos": {
        "name": "Point of Sale",
        "name_ar": "نقطة البيع",
        "category": "trading",
        "icon": "CreditCardOutlined",
        "description": "POS terminal, sales transactions, receipts",
        "capabilities": ["pos_terminal", "transactions", "receipts"],
        "entities": ["pos_session", "pos_transaction"],
        "permissions": ["pos.use", "pos.view"],
        "menu": {"label": "POS", "labelAr": "نقطة البيع", "path": "/pos", "icon": "CreditCardOutlined"},
        "dashboard_widgets": ["daily_sales", "top_products"],
        "dependencies": ["sales", "inventory"],
    },

    # ─── Restaurant-specific ────────────────────
    "menu_mgmt": {
        "name": "Menu Management",
        "name_ar": "إدارة القائمة",
        "category": "restaurant",
        "icon": "CoffeeOutlined",
        "description": "Menu items, categories, recipes, pricing",
        "capabilities": ["menu_items", "categories", "recipes"],
        "entities": ["menu_item", "menu_category", "recipe"],
        "permissions": ["menu.view", "menu.create", "menu.update"],
        "menu": {"label": "Menu", "labelAr": "القائمة", "path": "/menu", "icon": "CoffeeOutlined"},
        "dashboard_widgets": ["popular_items", "menu_performance"],
        "dependencies": ["inventory"],
    },
    "kitchen": {
        "name": "Kitchen Management",
        "name_ar": "إدارة المطبخ",
        "category": "restaurant",
        "icon": "FireOutlined",
        "description": "Orders, kitchen display, preparation tracking",
        "capabilities": ["kitchen_orders", "display", "preparation_tracking"],
        "entities": ["kitchen_order"],
        "permissions": ["kitchen.view", "kitchen.manage"],
        "menu": {"label": "Kitchen", "labelAr": "المطبخ", "path": "/kitchen", "icon": "FireOutlined"},
        "dashboard_widgets": ["pending_orders", "avg_prep_time"],
        "dependencies": ["menu_mgmt"],
    },

    # ─── Manufacturing-specific ─────────────────
    "production": {
        "name": "Production Planning",
        "name_ar": "تخطيط الإنتاج",
        "category": "manufacturing",
        "icon": "SettingOutlined",
        "description": "BOM, work orders, production lines",
        "capabilities": ["bom", "work_orders", "production_lines"],
        "entities": ["bom", "work_order", "production_line"],
        "permissions": ["production.view", "production.create", "production.manage"],
        "menu": {"label": "Production", "labelAr": "الإنتاج", "path": "/production", "icon": "SettingOutlined"},
        "dashboard_widgets": ["production_output", "work_order_status"],
        "dependencies": ["inventory"],
    },
    "quality": {
        "name": "Quality Control",
        "name_ar": "مراقبة الجودة",
        "category": "manufacturing",
        "icon": "CheckCircleOutlined",
        "description": "Quality checks, inspections, non-conformance",
        "capabilities": ["quality_checks", "inspections", "non_conformance"],
        "entities": ["quality_check", "inspection"],
        "permissions": ["quality.view", "quality.inspect"],
        "menu": {"label": "Quality", "labelAr": "الجودة", "path": "/quality", "icon": "CheckCircleOutlined"},
        "dashboard_widgets": ["quality_metrics"],
        "dependencies": ["production"],
    },

    # ─── Analytics (cross-industry) ─────────────
    "analytics": {
        "name": "Analytics & Reporting",
        "name_ar": "التقارير",
        "category": "intelligence",
        "icon": "BarChartOutlined",
        "description": "Reports, dashboards, data export",
        "capabilities": ["reports", "dashboards", "export"],
        "entities": ["report", "dashboard_widget"],
        "permissions": ["analytics.view", "analytics.export"],
        "menu": {"label": "Reports", "labelAr": "التقارير", "path": "/analytics", "icon": "BarChartOutlined"},
        "dashboard_widgets": [],
        "dependencies": [],
    },
}


# ═══════════════════════════════════════════════════
# Industry Templates — which modules each industry uses
# ═══════════════════════════════════════════════════

INDUSTRY_TEMPLATES: dict[str, dict[str, Any]] = {
    "construction": {
        "name": "Construction & Contracting",
        "name_ar": "مقاولات وإنشاءات",
        "description": "Projects, BOQ, Procurement, Equipment, Materials",
        "base_modules": [
            "accounting", "inventory", "hr", "documents", "workflow", "analytics",
            "projects", "procurement", "boq", "equipment",
        ],
        "optional_modules": ["sales"],
        "default_settings": {
            "base_currency": "SAR",
            "fiscal_year_start": "01-01",
            "tax_system": "vat",
        },
    },
    "trading": {
        "name": "Trading & Distribution",
        "name_ar": "تجارة وتوزيع",
        "description": "Sales, Purchasing, Inventory, POS, Distribution",
        "base_modules": [
            "accounting", "inventory", "hr", "documents", "workflow", "analytics",
            "sales", "procurement", "pos",
        ],
        "optional_modules": ["projects"],
        "default_settings": {
            "base_currency": "SAR",
            "fiscal_year_start": "01-01",
            "tax_system": "vat",
        },
    },
    "retail": {
        "name": "Retail & E-Commerce",
        "name_ar": "تجزئة وإلكتروني",
        "description": "POS, Products, Customers, Inventory",
        "base_modules": [
            "accounting", "inventory", "hr", "documents", "analytics",
            "sales", "pos",
        ],
        "optional_modules": ["workflow", "projects"],
        "default_settings": {
            "base_currency": "SAR",
            "fiscal_year_start": "01-01",
            "tax_system": "vat",
        },
    },
    "restaurant": {
        "name": "Restaurant & Food Service",
        "name_ar": "مطعم وסעدة",
        "description": "Menu, Kitchen, Orders, Inventory, Staff",
        "base_modules": [
            "accounting", "inventory", "hr", "documents", "analytics",
            "sales", "menu_mgmt", "kitchen",
        ],
        "optional_modules": ["workflow", "procurement"],
        "default_settings": {
            "base_currency": "SAR",
            "fiscal_year_start": "01-01",
            "tax_system": "vat",
        },
    },
    "manufacturing": {
        "name": "Manufacturing & Production",
        "name_ar": "تصنيع وإنتاج",
        "description": "BOM, Work Orders, Production, Quality, Inventory",
        "base_modules": [
            "accounting", "inventory", "hr", "documents", "workflow", "analytics",
            "production", "quality", "procurement",
        ],
        "optional_modules": ["sales", "projects"],
        "default_settings": {
            "base_currency": "SAR",
            "fiscal_year_start": "01-01",
            "tax_system": "vat",
        },
    },
    "services": {
        "name": "Professional Services",
        "name_ar": "خدمات مهنية",
        "description": "Projects, Time Tracking, Invoicing, Clients",
        "base_modules": [
            "accounting", "hr", "documents", "workflow", "analytics",
            "projects", "sales",
        ],
        "optional_modules": ["inventory"],
        "default_settings": {
            "base_currency": "SAR",
            "fiscal_year_start": "01-01",
            "tax_system": "vat",
        },
    },
}


def get_module(module_code: str) -> dict[str, Any]:
    """Get module definition from registry."""
    return MODULE_REGISTRY.get(module_code, {})


def get_industry_modules(industry_code: str) -> list[str]:
    """Get list of module codes for an industry."""
    template = INDUSTRY_TEMPLATES.get(industry_code, {})
    return template.get("base_modules", []) + template.get("optional_modules", [])


def get_industry_template(industry_code: str) -> dict[str, Any]:
    """Get full industry template."""
    return INDUSTRY_TEMPLATES.get(industry_code, {})


def get_all_modules() -> dict[str, dict[str, Any]]:
    """Get all registered modules."""
    return MODULE_REGISTRY


def get_all_industries() -> dict[str, dict[str, Any]]:
    """Get all industry templates."""
    return INDUSTRY_TEMPLATES


def build_sidebar_menu(modules: list[str]) -> list[dict[str, Any]]:
    """Build sidebar menu from list of enabled module codes."""
    menu = []
    for code in modules:
        mod = MODULE_REGISTRY.get(code)
        if mod and "menu" in mod:
            item = {
                "key": mod["menu"]["path"],
                "icon": mod["menu"]["icon"],
                "label": mod["menu"]["labelAr"],
                "module": code,
            }
            menu.append(item)
    return menu


def build_dashboard_widgets(modules: list[str]) -> list[str]:
    """Build list of dashboard widget codes from enabled modules."""
    widgets = []
    for code in modules:
        mod = MODULE_REGISTRY.get(code)
        if mod:
            widgets.extend(mod.get("dashboard_widgets", []))
    return widgets
