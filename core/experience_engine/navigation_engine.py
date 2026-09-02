"""
EOS Experience Engine — Navigation Engine
Sidebar, favorites, recent items, role-based visibility.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NavItemType(str, Enum):
    SECTION = "section"
    ITEM = "item"
    DIVIDER = "divider"
    BADGE = "badge"


class NavVisibility(str, Enum):
    ALWAYS = "always"
    AUTHENTICATED = "authenticated"
    ROLE_BASED = "role_based"
    INDUSTRY = "industry"
    FEATURE_FLAG = "feature_flag"


@dataclass
class NavItem:
    code: str
    label: str
    label_ar: str
    icon: str = "AppstoreOutlined"
    path: str = ""
    nav_type: NavItemType = NavItemType.ITEM
    visibility: NavVisibility = NavVisibility.ALWAYS
    visible_roles: list[str] = field(default_factory=list)
    visible_industries: list[str] = field(default_factory=list)
    required_features: list[str] = field(default_factory=list)
    badge: str | None = None  # e.g. "5" or "new"
    badge_color: str = "#ff4d4f"
    parent: str = ""  # Parent section code
    order: int = 0
    children: list['NavItem'] = field(default_factory=list)
    is_external: bool = False
    tooltip: str = ""
    tooltip_ar: str = ""


@dataclass
class NavigationSection:
    code: str
    label: str
    label_ar: str
    icon: str
    items: list[NavItem] = field(default_factory=list)
    order: int = 0
    is_collapsible: bool = True
    is_default_open: bool = True


@dataclass
class NavigationConfig:
    """Complete navigation configuration for an industry."""
    industry: str
    sections: list[NavigationSection] = field(default_factory=list)
    quick_actions: list[NavItem] = field(default_factory=list)
    favorites_enabled: bool = True
    recent_enabled: bool = True
    search_enabled: bool = True
    max_recent: int = 10


@dataclass
class UserFavorite:
    user_id: str
    item_code: str
    order: int = 0


@dataclass
class RecentItem:
    user_id: str
    item_code: str
    entity: str
    entity_id: str
    entity_name: str
    timestamp: str
    module: str = ""


class NavigationEngine:
    """
    Generates and manages navigation per industry.
    Handles sidebar, favorites, recent items, and role-based visibility.
    """

    def __init__(self):
        self._configs: dict[str, NavigationConfig] = {}
        self._favorites: dict[str, list[UserFavorite]] = {}
        self._recent: dict[str, list[RecentItem]] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register navigation configs for each industry."""

        # ── Construction Navigation ─────────────
        construction_nav = NavigationConfig(
            industry="construction",
            sections=[
                NavigationSection("main", "Main", "الرئيسية", "HomeOutlined", order=0, items=[
                    NavItem("dashboard", "Dashboard", "لوحة التحكم", "DashboardOutlined", "/construction", order=0),
                ]),
                NavigationSection("projects", "Projects & Works", "الأعمال والمشاريع", "ProjectOutlined", order=1, items=[
                    NavItem("projects_list", "Projects", "المشاريع", "ProjectOutlined", "/construction?tab=projects", order=0),
                    NavItem("contracts", "Contracts", "العقود", "FileTextOutlined", "/construction?tab=contracts", order=1),
                    NavItem("boq", "Bill of Quantities", "جدول الكميات", "UnorderedListOutlined", "/construction?tab=boq", order=2),
                    NavItem("variations", "Variations", "تغييرات", "SwapOutlined", "/construction?tab=variations", order=3),
                    NavItem("progress", "Progress", "تقدم الأعمال", "LineChartOutlined", "/construction?tab=progress", order=4),
                    NavItem("site_diary", "Site Diary", "سجل الموقع", "BookOutlined", "/construction?tab=site-diary", order=5),
                    NavItem("inspections", "Inspections", "فحص", "CheckCircleOutlined", "/construction?tab=inspections", order=6),
                ]),
                NavigationSection("procurement", "Procurement", "المشتريات", "ImportOutlined", order=2, items=[
                    NavItem("purchase_requests", "Purchase Requests", "طلبات الشراء", "FileAddOutlined", "/construction?tab=pr", order=0),
                    NavItem("rfq", "RFQ", "طلب عرض س שקל", "QuestionCircleOutlined", "/construction?tab=rfq", order=1),
                    NavItem("purchase_orders", "Purchase Orders", "أوامر الشراء", "ShoppingCartOutlined", "/construction?tab=po", order=2),
                    NavItem("grn", "Goods Receipt", "استلام بضاعة", "InboxOutlined", "/construction?tab=grn", order=3),
                ]),
                NavigationSection("inventory", "Materials & Stock", "المخزون والمواد", "ShopOutlined", order=3, items=[
                    NavItem("items", "Materials", "المواد", "TagsOutlined", "/construction?tab=items", order=0),
                    NavItem("warehouses", "Warehouses", "المخازن", "HomeOutlined", "/construction?tab=warehouses", order=1),
                    NavItem("stock", "Stock Levels", "مستويات المخزون", "DatabaseOutlined", "/construction?tab=stock", order=2),
                    NavItem("material_issue", "Material Issue", "صرف مواد", "OutboxOutlined", "/construction?tab=issue", order=3),
                    NavItem("material_return", "Material Return", "إرجاع مواد", "RollbackOutlined", "/construction?tab=return", order=4),
                    NavItem("transfers", "Transfers", "نقل", "SwapOutlined", "/construction?tab=transfers", order=5),
                ]),
                NavigationSection("equipment", "Equipment", "المعدات", "ToolOutlined", order=4, items=[
                    NavItem("equipment_list", "Equipment List", "قائمة المعدات", "ToolOutlined", "/construction?tab=equipment", order=0),
                    NavItem("equipment_logs", "Operation Logs", "سجلات التشغيل", "HistoryOutlined", "/construction?tab=equip-logs", order=1),
                    NavItem("fuel", "Fuel", "وقود", "CarOutlined", "/construction?tab=fuel", order=2),
                    NavItem("maintenance", "Maintenance", "صيانة", "SettingOutlined", "/construction?tab=maintenance", order=3),
                ]),
                NavigationSection("finance", "Finance", "المالية", "AccountBookOutlined", order=5, items=[
                    NavItem("accounting", "Accounting", "المحاسبة", "AccountBookOutlined", "/accounting", order=0),
                    NavItem("treasury", "Treasury", "الخزينة", "BankOutlined", "/treasury", order=1),
                    NavItem("receivables", "Receivables", "المبالغ المستحقة", "RiseOutlined", "/construction?tab=receivables", order=2),
                    NavItem("payables", "Payables", "المبالغ الدائنة", "FallOutlined", "/construction?tab=payables", order=3),
                    NavItem("cost_tracking", "Cost Tracking", "تتبع التكاليف", "FundOutlined", "/construction?tab=costs", order=4),
                ]),
                NavigationSection("hr", "Human Resources", "الموارد البشرية", "TeamOutlined", order=6, items=[
                    NavItem("employees", "Employees", "الموظفون", "TeamOutlined", "/hr", order=0),
                    NavItem("attendance", "Attendance", "الحضور", "ClockCircleOutlined", "/hr?tab=attendance", order=1),
                    NavItem("payroll", "Payroll", "الرواتب", "WalletOutlined", "/hr?tab=payroll", order=2),
                ]),
                NavigationSection("docs", "Documents & Reports", "المستندات والتقارير", "FileTextOutlined", order=7, items=[
                    NavItem("documents", "Documents", "المستندات", "FolderOutlined", "/documents", order=0),
                    NavItem("reports", "Reports", "التقارير", "BarChartOutlined", "/analytics", order=1),
                    NavItem("drawings", "Drawings", "رسومات", "BuildOutlined", "/construction?tab=drawings", order=2),
                ]),
                NavigationSection("admin", "Administration", "الإدارة", "SettingOutlined", order=8, items=[
                    NavItem("settings", "Settings", "الإعدادات", "SettingOutlined", "/settings", order=0),
                    NavItem("control", "EOS Control", "التحكم", "CrownOutlined", "/control", order=1,
                           visible_roles=["platform_owner", "tenant_admin"]),
                ]),
            ],
            quick_actions=[
                NavItem("new_project", "New Project", "مشروع جديد", "PlusCircleOutlined", "/construction?tab=projects&action=new"),
                NavItem("new_pr", "New Purchase Request", "طلب شراء جديد", "PlusCircleOutlined", "/construction?tab=pr&action=new"),
                NavItem("new_issue", "Material Issue", "صرف مواد", "PlusCircleOutlined", "/construction?tab=issue&action=new"),
            ],
        )
        self._configs["construction"] = construction_nav

        # ── Trading Navigation ──────────────────
        trading_nav = NavigationConfig(
            industry="trading",
            sections=[
                NavigationSection("main", "Main", "الرئيسية", "HomeOutlined", order=0, items=[
                    NavItem("dashboard", "Dashboard", "لوحة التحكم", "DashboardOutlined", "/dashboard", order=0),
                ]),
                NavigationSection("sales", "Sales", "المبيعات", "ShoppingCartOutlined", order=1, items=[
                    NavItem("quotations", "Quotations", "عروض الأسعار", "FileTextOutlined", "/sales?tab=quotations", order=0),
                    NavItem("sales_orders", "Sales Orders", "أوامر البيع", "ShoppingCartOutlined", "/sales?tab=orders", order=1),
                    NavItem("delivery", "Delivery Notes", "سندات التسليم", "CarOutlined", "/sales?tab=delivery", order=2),
                    NavItem("invoices", "Invoices", "الفواتير", "FileTextOutlined", "/sales?tab=invoices", order=3),
                    NavItem("customers", "Customers", "العملاء", "UserOutlined", "/sales?tab=customers", order=4),
                    NavItem("returns", "Returns", "المرتجعات", "RollbackOutlined", "/sales?tab=returns", order=5),
                ]),
                NavigationSection("purchasing", "Purchasing", "المشتريات", "ImportOutlined", order=2, items=[
                    NavItem("suppliers", "Suppliers", "الموردون", "TeamOutlined", "/sales?tab=suppliers", order=0),
                    NavItem("rfq", "RFQ", "طلب عرض سعر", "QuestionCircleOutlined", "/inventory?tab=rfq", order=1),
                    NavItem("purchase_orders", "Purchase Orders", "أوامر الشراء", "ShoppingCartOutlined", "/inventory?tab=purchases", order=2),
                    NavItem("grn", "Goods Receipt", "استلام بضاعة", "InboxOutlined", "/inventory?tab=grn", order=3),
                    NavItem("supplier_invoices", "Supplier Invoices", "فواتير الموردين", "FileTextOutlined", "/inventory?tab=supplier-inv", order=4),
                ]),
                NavigationSection("distribution", "Distribution", "التوزيع", "CarOutlined", order=3, items=[
                    NavItem("routes", "Routes", "المسارات", "AimOutlined", "/sales?tab=routes", order=0),
                    NavItem("sales_reps", "Sales Reps", "مندوبي المبيعات", "UserOutlined", "/sales?tab=reps", order=1),
                    NavItem("price_lists", "Price Lists", "قوائم الأسعار", "DollarOutlined", "/sales?tab=prices", order=2),
                ]),
                NavigationSection("inventory", "Inventory", "المخزون", "ShopOutlined", order=4, items=[
                    NavItem("items", "Products", "المنتجات", "TagsOutlined", "/inventory", order=0),
                    NavItem("warehouses", "Warehouses", "المخازن", "HomeOutlined", "/inventory?tab=warehouses", order=1),
                    NavItem("stock", "Stock", "المخزون", "DatabaseOutlined", "/inventory?tab=stock", order=2),
                    NavItem("transfers", "Transfers", "النقل", "SwapOutlined", "/inventory?tab=transfers", order=3),
                    NavItem("stock_take", "Stock Take", "جرد المخزون", "FileSearchOutlined", "/inventory?tab=stocktake", order=4),
                ]),
                NavigationSection("finance", "Finance", "المالية", "AccountBookOutlined", order=5, items=[
                    NavItem("accounting", "Accounting", "المحاسبة", "AccountBookOutlined", "/accounting", order=0),
                    NavItem("treasury", "Treasury", "الخزينة", "BankOutlined", "/treasury", order=1),
                ]),
                NavigationSection("hr", "HR", "الموارد البشرية", "TeamOutlined", order=6, items=[
                    NavItem("employees", "Employees", "الموظفون", "TeamOutlined", "/hr", order=0),
                ]),
                NavigationSection("admin", "Admin", "الإدارة", "SettingOutlined", order=7, items=[
                    NavItem("settings", "Settings", "الإعدادات", "SettingOutlined", "/settings", order=0),
                    NavItem("reports", "Reports", "التقارير", "BarChartOutlined", "/analytics", order=1),
                ]),
            ],
        )
        self._configs["trading"] = trading_nav

        # ── Restaurant Navigation ───────────────
        restaurant_nav = NavigationConfig(
            industry="restaurant",
            sections=[
                NavigationSection("main", "Main", "الرئيسية", "HomeOutlined", order=0, items=[
                    NavItem("dashboard", "Dashboard", "لوحة التحكم", "DashboardOutlined", "/dashboard", order=0),
                ]),
                NavigationSection("operations", "Operations", "العمليات", "CoffeeOutlined", order=1, items=[
                    NavItem("menu", "Menu", "القائمة", "CoffeeOutlined", "/sales?tab=menu", order=0),
                    NavItem("orders", "Orders", "الطلبات", "ShoppingCartOutlined", "/sales?tab=orders", order=1),
                    NavItem("kitchen", "Kitchen", "المطبخ", "FireOutlined", "/sales?tab=kitchen", order=2),
                    NavItem("tables", "Tables", "الطاولات", "AppstoreOutlined", "/sales?tab=tables", order=3),
                    NavItem("reservations", "Reservations", "الحجوزات", "CalendarOutlined", "/sales?tab=reservations", order=4),
                ]),
                NavigationSection("inventory", "Kitchen Stock", "مخزون المطبخ", "ShopOutlined", order=2, items=[
                    NavItem("ingredients", "Ingredients", "المكونات", "TagsOutlined", "/inventory", order=0),
                    NavItem("recipes", "Recipes", "الوصفات", "BookOutlined", "/inventory?tab=recipes", order=1),
                    NavItem("stock", "Stock Levels", "مستويات المخزون", "DatabaseOutlined", "/inventory?tab=stock", order=2),
                    NavItem("waste", "Waste Tracking", "تتبع الهدر", "DeleteOutlined", "/inventory?tab=waste", order=3),
                ]),
                NavigationSection("finance", "Finance", "المالية", "AccountBookOutlined", order=3, items=[
                    NavItem("accounting", "Accounting", "المحاسبة", "AccountBookOutlined", "/accounting", order=0),
                    NavItem("daily_close", "Daily Closing", "إقفال يومي", "LockOutlined", "/sales?tab=daily-close", order=1),
                    NavItem("food_cost", "Food Cost", "تكلفة الطعام", "CalculatorOutlined", "/sales?tab=food-cost", order=2),
                ]),
                NavigationSection("hr", "Staff", "الموظفون", "TeamOutlined", order=4, items=[
                    NavItem("employees", "Staff", "الموظفون", "TeamOutlined", "/hr", order=0),
                    NavItem("shifts", "Shifts", "الورديات", "ClockCircleOutlined", "/hr?tab=shifts", order=1),
                ]),
                NavigationSection("admin", "Admin", "الإدارة", "SettingOutlined", order=5, items=[
                    NavItem("settings", "Settings", "الإعدادات", "SettingOutlined", "/settings", order=0),
                    NavItem("reports", "Reports", "التقارير", "BarChartOutlined", "/analytics", order=1),
                ]),
            ],
        )
        self._configs["restaurant"] = restaurant_nav

        # ── Manufacturing Navigation ────────────
        manufacturing_nav = NavigationConfig(
            industry="manufacturing",
            sections=[
                NavigationSection("main", "Main", "الرئيسية", "HomeOutlined", order=0, items=[
                    NavItem("dashboard", "Dashboard", "لوحة التحكم", "DashboardOutlined", "/dashboard", order=0),
                ]),
                NavigationSection("planning", "Planning", "التخطيط", "AimOutlined", order=1, items=[
                    NavItem("demand", "Demand Planning", "تخطيط الطلب", "LineChartOutlined", "/projects?tab=demand", order=0),
                    NavItem("mrp", "MRP", "تخطيط متطلبات المواد", "SyncOutlined", "/projects?tab=mrp", order=1),
                    NavItem("production_orders", "Production Orders", "أوامر الإنتاج", "PlayCircleOutlined", "/projects?tab=prod-orders", order=2),
                ]),
                NavigationSection("production", "Production", "الإنتاج", "SettingOutlined", order=2, items=[
                    NavItem("bom", "BOM", "قائمة المواد", "ApartmentOutlined", "/projects?tab=bom", order=0),
                    NavItem("routing", "Routing", "مسار الإnung", "BranchesOutlined", "/projects?tab=routing", order=1),
                    NavItem("work_centers", "Work Centers", "مراكز العمل", "BankOutlined", "/projects?tab=work-centers", order=2),
                    NavItem("wip", "WIP", "قيد التنفيذ", "SyncOutlined", "/projects?tab=wip", order=3),
                    NavItem("finished_goods", "Finished Goods", "المنتجات التامة", "CheckCircleOutlined", "/projects?tab=finished", order=4),
                ]),
                NavigationSection("quality", "Quality", "الجودة", "CheckCircleOutlined", order=3, items=[
                    NavItem("inspections", "Inspections", "الفحص", "SearchOutlined", "/projects?tab=inspections", order=0),
                    NavItem("ncr", "NCR", "تقرير عدم مطابقة", "WarningOutlined", "/projects?tab=ncr", order=1),
                    NavItem("scrap", "Scrap", "هالك", "DeleteOutlined", "/projects?tab=scrap", order=2),
                ]),
                NavigationSection("inventory", "Inventory", "المخزون", "ShopOutlined", order=4, items=[
                    NavItem("raw_materials", "Raw Materials", "مواد خام", "TagsOutlined", "/inventory", order=0),
                    NavItem("warehouses", "Warehouses", "المخازن", "HomeOutlined", "/inventory?tab=warehouses", order=1),
                    NavItem("stock", "Stock", "المخزون", "DatabaseOutlined", "/inventory?tab=stock", order=2),
                ]),
                NavigationSection("maintenance", "Maintenance", "الصيانة", "ToolOutlined", order=5, items=[
                    NavItem("equipment", "Equipment", "المعدات", "ToolOutlined", "/inventory?tab=equipment", order=0),
                    NavItem("maintenance_plans", "Maintenance Plans", "خطط الصيانة", "CalendarOutlined", "/projects?tab=maintenance", order=1),
                ]),
                NavigationSection("finance", "Finance", "المالية", "AccountBookOutlined", order=6, items=[
                    NavItem("accounting", "Accounting", "المحاسبة", "AccountBookOutlined", "/accounting", order=0),
                    NavItem("production_cost", "Production Cost", "تكلفة الإنتاج", "DollarOutlined", "/projects?tab=prod-cost", order=1),
                ]),
                NavigationSection("admin", "Admin", "الإدارة", "SettingOutlined", order=7, items=[
                    NavItem("settings", "Settings", "الإعدادات", "SettingOutlined", "/settings", order=0),
                    NavItem("reports", "Reports", "التقارير", "BarChartOutlined", "/analytics", order=1),
                ]),
            ],
        )
        self._configs["manufacturing"] = manufacturing_nav

        # ── Services Navigation ─────────────────
        services_nav = NavigationConfig(
            industry="services",
            sections=[
                NavigationSection("main", "Main", "الرئيسية", "HomeOutlined", order=0, items=[
                    NavItem("dashboard", "Dashboard", "لوحة التحكم", "DashboardOutlined", "/dashboard", order=0),
                ]),
                NavigationSection("projects", "Projects", "المشاريع", "ProjectOutlined", order=1, items=[
                    NavItem("projects_list", "Projects", "المشاريع", "ProjectOutlined", "/projects", order=0),
                    NavItem("tasks", "Tasks", "المهام", "CheckSquareOutlined", "/projects?tab=tasks", order=1),
                    NavItem("timesheets", "Timesheets", "جدول الوق", "ClockCircleOutlined", "/projects?tab=timesheets", order=2),
                    NavItem("milestones", "Milestones", "المعالم", "FlagOutlined", "/projects?tab=milestones", order=3),
                ]),
                NavigationSection("sales", "Sales", "المبيعات", "ShoppingCartOutlined", order=2, items=[
                    NavItem("clients", "Clients", "العملاء", "UserOutlined", "/sales?tab=customers", order=0),
                    NavItem("proposals", "Proposals", "العروض", "FileTextOutlined", "/sales?tab=quotations", order=1),
                    NavItem("invoices", "Invoices", "الفواتير", "FileTextOutlined", "/sales?tab=invoices", order=2),
                ]),
                NavigationSection("finance", "Finance", "المالية", "AccountBookOutlined", order=3, items=[
                    NavItem("accounting", "Accounting", "المحاسبة", "AccountBookOutlined", "/accounting", order=0),
                    NavItem("expenses", "Expenses", "المصروفات", "RiseOutlined", "/sales?tab=expenses", order=1),
                ]),
                NavigationSection("hr", "HR", "الموارد البشرية", "TeamOutlined", order=4, items=[
                    NavItem("employees", "Team", "الفريق", "TeamOutlined", "/hr", order=0),
                ]),
                NavigationSection("admin", "Admin", "الإدارة", "SettingOutlined", order=5, items=[
                    NavItem("settings", "Settings", "الإعدادات", "SettingOutlined", "/settings", order=0),
                    NavItem("reports", "Reports", "التقارير", "BarChartOutlined", "/analytics", order=1),
                ]),
            ],
        )
        self._configs["services"] = services_nav

    def register_config(self, config: NavigationConfig):
        """Register navigation config for an industry."""
        self._configs[config.industry] = config

    def get_config(self, industry: str) -> NavigationConfig | None:
        """Get navigation config for an industry."""
        return self._configs.get(industry)

    def get_menu(self, industry: str, user_role: str = "", features: list[str] | None = None) -> list[dict[str, Any]]:
        """
        Get filtered menu for a user based on industry, role, and features.
        Returns list of sections with items.
        """
        config = self._configs.get(industry)
        if not config:
            config = self._configs.get("construction")  # fallback
        if not config:
            return []

        result = []
        for section in sorted(config.sections, key=lambda s: s.order):
            section_items = []
            for item in sorted(section.items, key=lambda i: i.order):
                # Check visibility
                if not self._is_visible(item, user_role, features or []):
                    continue
                section_items.append({
                    "code": item.code,
                    "label": item.label_ar,
                    "label_en": item.label,
                    "icon": item.icon,
                    "path": item.path,
                    "badge": item.badge,
                })

            if section_items:
                result.append({
                    "code": section.code,
                    "label": section.label_ar,
                    "label_en": section.label,
                    "icon": section.icon,
                    "items": section_items,
                    "is_collapsible": section.is_collapsible,
                    "is_default_open": section.is_default_open,
                })

        return result

    def get_flat_menu(self, industry: str, user_role: str = "", features: list[str] | None = None) -> list[dict[str, Any]]:
        """Get flat menu list (for sidebar)."""
        sections = self.get_menu(industry, user_role, features)
        flat = []
        for section in sections:
            for item in section["items"]:
                flat.append({**item, "section": section["code"]})
        return flat

    def _is_visible(self, item: NavItem, user_role: str, features: list[str]) -> bool:
        """Check if a nav item should be visible."""
        if item.visibility == NavVisibility.ALWAYS:
            return True
        if item.visibility == NavVisibility.ROLE_BASED:
            if item.visible_roles and user_role not in item.visible_roles:
                return False
        if item.visibility == NavVisibility.FEATURE_FLAG:
            if item.required_features:
                if not all(f in features for f in item.required_features):
                    return False
        return True

    def add_favorite(self, user_id: str, item_code: str):
        """Add item to user's favorites."""
        if user_id not in self._favorites:
            self._favorites[user_id] = []
        existing = [f for f in self._favorites[user_id] if f.item_code == item_code]
        if not existing:
            self._favorites[user_id].append(UserFavorite(user_id, item_code, order=0))

    def remove_favorite(self, user_id: str, item_code: str):
        """Remove item from user's favorites."""
        if user_id in self._favorites:
            self._favorites[user_id] = [f for f in self._favorites[user_id] if f.item_code != item_code]

    def get_favorites(self, user_id: str) -> list[str]:
        """Get user's favorite item codes."""
        return [f.item_code for f in self._favorites.get(user_id, [])]

    def add_recent(self, user_id: str, item_code: str, entity: str, entity_id: str,
                   entity_name: str, module: str = ""):
        """Add item to user's recent list."""
        if user_id not in self._recent:
            self._recent[user_id] = []

        # Remove existing entry for same entity
        self._recent[user_id] = [
            r for r in self._recent[user_id]
            if not (r.entity == entity and r.entity_id == entity_id)
        ]

        # Add to front
        self._recent[user_id].insert(0, RecentItem(
            user_id=user_id, item_code=item_code, entity=entity,
            entity_id=entity_id, entity_name=entity_name,
            timestamp="now", module=module,
        ))

        # Trim to max
        config = self._configs.get("construction")  # default
        max_recent = config.max_recent if config else 10
        self._recent[user_id] = self._recent[user_id][:max_recent]

    def get_recent(self, user_id: str) -> list[dict[str, Any]]:
        """Get user's recent items."""
        return [{
            "item_code": r.item_code, "entity": r.entity,
            "entity_id": r.entity_id, "entity_name": r.entity_name,
            "timestamp": r.timestamp, "module": r.module,
        } for r in self._recent.get(user_id, [])]

    def get_quick_actions(self, industry: str) -> list[dict[str, Any]]:
        """Get quick action buttons for an industry."""
        config = self._configs.get(industry)
        if not config:
            return []
        return [{
            "code": a.code, "label": a.label_ar, "label_en": a.label,
            "icon": a.icon, "path": a.path,
        } for a in config.quick_actions]

    def export_navigation(self, industry: str) -> dict[str, Any]:
        """Export navigation config for templates."""
        config = self._configs.get(industry)
        if not config:
            return {}
        return {
            "industry": config.industry,
            "sections": [{
                "code": s.code, "label": s.label, "label_ar": s.label_ar,
                "items": [{"code": i.code, "label": i.label, "label_ar": i.label_ar,
                          "icon": i.icon, "path": i.path} for i in s.items],
            } for s in config.sections],
        }
