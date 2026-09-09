"""
EOS Industry Engine — Module Engine
Registers, activates, and queries modules per tenant.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ModuleCategory(str, Enum):
    CORE = "core"
    FINANCIAL = "financial"
    OPERATIONS = "operations"
    COMMERCIAL = "commercial"
    PEOPLE = "people"
    CONSTRUCTION = "construction"
    TRADING = "trading"
    RETAIL = "retail"
    RESTAURANT = "restaurant"
    MANUFACTURING = "manufacturing"
    TOURISM = "tourism"
    INTELLIGENCE = "intelligence"


class ModuleStatus(str, Enum):
    REGISTERED = "registered"
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


@dataclass
class ModuleCapability:
    code: str
    name: str
    description: str = ""


@dataclass
class ModuleDefinition:
    code: str
    name: str
    name_ar: str
    category: ModuleCategory
    icon: str
    description: str = ""
    version: str = "1.0.0"
    capabilities: List[ModuleCapability] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    menu_items: List[Dict[str, Any]] = field(default_factory=list)
    dashboard_widgets: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)


class ModuleEngine:
    """
    Central registry for all modules in the EOS platform.
    Each industry template references modules from this registry.
    """

    def __init__(self):
        self._modules: Dict[str, ModuleDefinition] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register core platform modules."""
        core_modules = [
            ModuleDefinition(
                code="accounting", name="Accounting", name_ar="المحاسبة",
                category=ModuleCategory.FINANCIAL, icon="AccountBookOutlined",
                description="Chart of accounts, journal entries, financial statements",
                capabilities=[
                    ModuleCapability("journal_entries", "Journal Entries"),
                    ModuleCapability("trial_balance", "Trial Balance"),
                    ModuleCapability("income_statement", "Income Statement"),
                    ModuleCapability("balance_sheet", "Balance Sheet"),
                    ModuleCapability("cost_centers", "Cost Centers"),
                ],
                entities=["account", "journal_entry", "journal_line", "cost_center"],
                permissions=["accounting.view", "accounting.create", "accounting.post", "accounting.close"],
                menu_items=[{"label": "Accounting", "labelAr": "المحاسبة", "path": "/accounting", "icon": "AccountBookOutlined"}],
                dashboard_widgets=["financial_summary", "recent_journals", "cash_position"],
            ),
            ModuleDefinition(
                code="inventory", name="Inventory", name_ar="المخزون",
                category=ModuleCategory.OPERATIONS, icon="ShopOutlined",
                description="Items, warehouses, stock movements, valuation",
                capabilities=[
                    ModuleCapability("stock_management", "Stock Management"),
                    ModuleCapability("warehouse_management", "Warehouse Management"),
                    ModuleCapability("stock_movements", "Stock Movements"),
                    ModuleCapability("batch_serial", "Batch/Serial Tracking"),
                    ModuleCapability("stock_valuation", "Stock Valuation"),
                ],
                entities=["item", "warehouse", "stock", "stock_movement", "stock_take"],
                permissions=["inventory.view", "inventory.create", "inventory.adjust", "inventory.transfer"],
                menu_items=[{"label": "Inventory", "labelAr": "المخزون", "path": "/inventory", "icon": "ShopOutlined"}],
                dashboard_widgets=["stock_summary", "low_stock_alerts", "stock_value"],
            ),
            ModuleDefinition(
                code="sales", name="Sales & CRM", name_ar="المبيعات",
                category=ModuleCategory.COMMERCIAL, icon="ShoppingCartOutlined",
                description="Customers, quotations, sales orders, invoices, pipeline",
                capabilities=[
                    ModuleCapability("customers", "Customer Management"),
                    ModuleCapability("quotations", "Quotations"),
                    ModuleCapability("sales_orders", "Sales Orders"),
                    ModuleCapability("invoices", "Invoicing"),
                    ModuleCapability("pipeline", "Sales Pipeline"),
                ],
                entities=["customer", "quotation", "sales_order", "invoice", "lead"],
                permissions=["sales.view", "sales.create", "sales.invoice", "sales.discount"],
                menu_items=[{"label": "Sales", "labelAr": "المبيعات", "path": "/sales", "icon": "ShoppingCartOutlined"}],
                dashboard_widgets=["sales_pipeline", "recent_invoices", "revenue_trend"],
            ),
            ModuleDefinition(
                code="hr", name="Human Resources", name_ar="الموارد البشرية",
                category=ModuleCategory.PEOPLE, icon="TeamOutlined",
                description="Employees, attendance, payroll, leave, recruitment",
                capabilities=[
                    ModuleCapability("employees", "Employee Management"),
                    ModuleCapability("attendance", "Attendance"),
                    ModuleCapability("payroll", "Payroll"),
                    ModuleCapability("leave", "Leave Management"),
                    ModuleCapability("recruitment", "Recruitment"),
                ],
                entities=["employee", "department", "attendance", "payroll_run", "leave_request"],
                permissions=["hr.view", "hr.manage", "hr.payroll", "hr.recruit"],
                menu_items=[{"label": "HR", "labelAr": "الموارد البشرية", "path": "/hr", "icon": "TeamOutlined"}],
                dashboard_widgets=["headcount", "attendance_summary", "payroll_summary"],
            ),
            ModuleDefinition(
                code="procurement", name="Procurement", name_ar="المشتريات",
                category=ModuleCategory.OPERATIONS, icon="ImportOutlined",
                description="Purchase requests, orders, goods receipt, supplier invoices",
                capabilities=[
                    ModuleCapability("purchase_requests", "Purchase Requests"),
                    ModuleCapability("purchase_orders", "Purchase Orders"),
                    ModuleCapability("goods_receipt", "Goods Receipt"),
                    ModuleCapability("supplier_invoices", "Supplier Invoices"),
                ],
                entities=["purchase_request", "purchase_order", "grn", "supplier_invoice"],
                permissions=["procurement.view", "procurement.create", "procurement.approve"],
                menu_items=[{"label": "Procurement", "labelAr": "المشتريات", "path": "/procurement", "icon": "ImportOutlined"}],
                dashboard_widgets=["pending_pos", "procurement_value", "supplier_performance"],
                dependencies=["inventory"],
            ),
            ModuleDefinition(
                code="projects", name="Project Management", name_ar="إدارة المشاريع",
                category=ModuleCategory.OPERATIONS, icon="ProjectOutlined",
                description="Projects, tasks, milestones, time tracking, WBS",
                capabilities=[
                    ModuleCapability("projects", "Project Management"),
                    ModuleCapability("tasks", "Task Management"),
                    ModuleCapability("milestones", "Milestones"),
                    ModuleCapability("time_tracking", "Time Tracking"),
                    ModuleCapability("wbs", "Work Breakdown Structure"),
                ],
                entities=["project", "project_task", "milestone", "time_entry"],
                permissions=["projects.view", "projects.create", "projects.manage"],
                menu_items=[{"label": "Projects", "labelAr": "المشاريع", "path": "/projects", "icon": "ProjectOutlined"}],
                dashboard_widgets=["project_progress", "upcoming_milestones", "resource_utilization"],
            ),
            ModuleDefinition(
                code="documents", name="Document Management", name_ar="المستندات",
                category=ModuleCategory.CORE, icon="FileTextOutlined",
                description="Document storage, versioning, templates, e-signatures",
                capabilities=[
                    ModuleCapability("storage", "Document Storage"),
                    ModuleCapability("versioning", "Version Control"),
                    ModuleCapability("templates", "Document Templates"),
                    ModuleCapability("esignature", "E-Signatures"),
                ],
                entities=["document", "document_version", "document_template"],
                permissions=["documents.view", "documents.upload", "documents.delete"],
                menu_items=[{"label": "Documents", "labelAr": "المستندات", "path": "/documents", "icon": "FileTextOutlined"}],
            ),
            ModuleDefinition(
                code="workflow", name="Workflow & Approvals", name_ar="سير العمل",
                category=ModuleCategory.CORE, icon="SyncOutlined",
                description="Approval workflows, routing, escalation",
                capabilities=[
                    ModuleCapability("approvals", "Approvals"),
                    ModuleCapability("routing", "Routing"),
                    ModuleCapability("escalation", "Escalation"),
                ],
                entities=["workflow_definition", "workflow_instance", "workflow_step"],
                permissions=["workflow.view", "workflow.approve", "workflow.define"],
                menu_items=[{"label": "Workflows", "labelAr": "سير العمل", "path": "/workflows", "icon": "SyncOutlined"}],
                dashboard_widgets=["pending_approvals"],
            ),
            ModuleDefinition(
                code="crm", name="CRM", name_ar="إدارة العلاقات",
                category=ModuleCategory.COMMERCIAL, icon="ContactsOutlined",
                description="Leads, opportunities, contacts, activities",
                capabilities=[
                    ModuleCapability("leads", "Lead Management"),
                    ModuleCapability("opportunities", "Opportunity Tracking"),
                    ModuleCapability("contacts", "Contact Management"),
                    ModuleCapability("activities", "Activity Tracking"),
                ],
                entities=["lead", "opportunity", "contact", "activity"],
                permissions=["crm.view", "crm.create", "crm.manage"],
                menu_items=[{"label": "CRM", "labelAr": "العلاقات", "path": "/crm", "icon": "ContactsOutlined"}],
                dashboard_widgets=["pipeline_value", "leads_by_source", "conversion_rate"],
            ),
            ModuleDefinition(
                code="analytics", name="Analytics & Reporting", name_ar="التقارير",
                category=ModuleCategory.INTELLIGENCE, icon="BarChartOutlined",
                description="Reports, dashboards, data export, BI",
                capabilities=[
                    ModuleCapability("reports", "Standard Reports"),
                    ModuleCapability("custom_reports", "Custom Reports"),
                    ModuleCapability("dashboards", "Dashboards"),
                    ModuleCapability("export", "Data Export"),
                ],
                entities=["report", "dashboard_widget", "report_schedule"],
                permissions=["analytics.view", "analytics.export", "analytics.create"],
                menu_items=[{"label": "Reports", "labelAr": "التقارير", "path": "/analytics", "icon": "BarChartOutlined"}],
            ),
            ModuleDefinition(
                code="treasury", name="Treasury & Banking", name_ar="الخزينة والبنوك",
                category=ModuleCategory.FINANCIAL, icon="BankOutlined",
                description="Bank accounts, cash, payments, collections",
                capabilities=[
                    ModuleCapability("bank_accounts", "Bank Accounts"),
                    ModuleCapability("cash_management", "Cash Management"),
                    ModuleCapability("payments", "Payment Processing"),
                    ModuleCapability("collections", "Collection Management"),
                ],
                entities=["bank_account", "payment", "collection", "bank_reconciliation"],
                permissions=["treasury.view", "treasury.create", "treasury.reconcile"],
                menu_items=[{"label": "Treasury", "labelAr": "الخزينة", "path": "/treasury", "icon": "BankOutlined"}],
                dashboard_widgets=["cash_position", "bank_balances", "payment_schedule"],
                dependencies=["accounting"],
            ),
            ModuleDefinition(
                code="tax", name="Tax Management", name_ar="الضرائب",
                category=ModuleCategory.FINANCIAL, icon="PercentageOutlined",
                description="VAT, WHT, tax returns, compliance",
                capabilities=[
                    ModuleCapability("vat", "VAT Management"),
                    ModuleCapability("wht", "Withholding Tax"),
                    ModuleCapability("returns", "Tax Returns"),
                ],
                entities=["tax_rate", "tax_return", "tax_transaction"],
                permissions=["tax.view", "tax.calculate", "tax.file"],
                dependencies=["accounting"],
            ),
            ModuleDefinition(
                code="fixed_assets", name="Fixed Assets", name_ar="الأصول الثابتة",
                category=ModuleCategory.FINANCIAL, icon="CarOutlined",
                description="Asset register, depreciation, maintenance",
                capabilities=[
                    ModuleCapability("register", "Asset Register"),
                    ModuleCapability("depreciation", "Depreciation"),
                    ModuleCapability("maintenance", "Maintenance"),
                ],
                entities=["fixed_asset", "depreciation_entry", "maintenance_log"],
                permissions=["assets.view", "assets.create", "assets.dispose"],
                dependencies=["accounting"],
            ),
            ModuleDefinition(
                code="tourism", name="Tourism Management", name_ar="إدارة السياحة",
                category=ModuleCategory.TOURISM, icon="CloudOutlined",
                description="Tour packages, bookings, hotels, flights, passengers, visas, guides",
                capabilities=[
                    ModuleCapability("tour_packages", "Tour Packages"),
                    ModuleCapability("bookings", "Booking Management"),
                    ModuleCapability("hotels", "Hotel Management"),
                    ModuleCapability("flights", "Flight Management"),
                    ModuleCapability("passengers", "Passenger Management"),
                    ModuleCapability("visas", "Visa Processing"),
                    ModuleCapability("guides", "Guide Management"),
                    ModuleCapability("transfers", "Transfer Services"),
                ],
                entities=["tour_package", "booking", "hotel", "flight", "passenger", "visa", "guide", "transfer"],
                permissions=["tourism.view", "tourism.create", "tourism.book", "tourism.approve"],
                menu_items=[{"label": "Tourism", "labelAr": "السياحة", "path": "/tourism", "icon": "CloudOutlined"}],
                dashboard_widgets=["total_bookings", "booking_value", "occupancy_rate", "revenue_per_passenger", "visa_success_rate"],
                dependencies=["accounting", "crm"],
            ),
        ]

        for mod in core_modules:
            self._modules[mod.code] = mod

    def register(self, module: ModuleDefinition):
        """Register a new module."""
        self._modules[module.code] = module

    def get(self, code: str) -> Optional[ModuleDefinition]:
        """Get module definition by code."""
        return self._modules.get(code)

    def get_all(self) -> Dict[str, ModuleDefinition]:
        """Get all registered modules."""
        return dict(self._modules)

    def get_by_category(self, category: ModuleCategory) -> List[ModuleDefinition]:
        """Get modules by category."""
        return [m for m in self._modules.values() if m.category == category]

    def has_capability(self, module_code: str, capability: str) -> bool:
        """Check if a module has a specific capability."""
        mod = self._modules.get(module_code)
        if not mod:
            return False
        return any(c.code == capability for c in mod.capabilities)

    def validate_dependencies(self, module_codes: List[str]) -> List[str]:
        """Return list of missing dependencies."""
        missing = []
        codes_set = set(module_codes)
        for code in module_codes:
            mod = self._modules.get(code)
            if mod:
                for dep in mod.dependencies:
                    if dep not in codes_set:
                        missing.append(f"{code} requires {dep}")
        return missing

    def get_menu_for_modules(self, module_codes: List[str]) -> List[Dict[str, Any]]:
        """Build menu from list of active module codes."""
        menu = []
        for code in module_codes:
            mod = self._modules.get(code)
            if mod:
                for item in mod.menu_items:
                    menu.append({**item, "module": code})
        return menu

    def get_dashboard_widgets(self, module_codes: List[str]) -> List[str]:
        """Get all dashboard widget codes for active modules."""
        widgets = []
        for code in module_codes:
            mod = self._modules.get(code)
            if mod:
                widgets.extend(mod.dashboard_widgets)
        return widgets

    def get_permissions(self, module_codes: List[str]) -> List[str]:
        """Get all permissions for active modules."""
        perms = []
        for code in module_codes:
            mod = self._modules.get(code)
            if mod:
                perms.extend(mod.permissions)
        return perms
