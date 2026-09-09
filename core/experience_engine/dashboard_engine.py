"""
EOS Experience Engine — Dashboard Engine
KPI cards, charts, alerts, targets, drill-down, activity feeds.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class KPIType(str, Enum):
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    COUNT = "count"
    DURATION = "duration"
    RATIO = "ratio"


class ChartType(str, Enum):
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    DONUT = "donut"
    AREA = "area"
    STACKED_BAR = "stacked_bar"
    COMBO = "combo"
    GAUGE = "gauge"
    FUNNEL = "funnel"
    TREEMAP = "treemap"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SUCCESS = "success"


class WidgetSize(str, Enum):
    SMALL = "small"       # 1/4 width
    MEDIUM = "medium"     # 1/2 width
    LARGE = "large"       # 3/4 width
    FULL = "full"         # full width
    DOUBLE = "double"     # 2x height


@dataclass
class KPITarget:
    value: float
    label: str = ""
    color: str = "#52c41a"  # green when met


@dataclass
class KPICard:
    code: str
    title: str
    title_ar: str
    kpi_type: KPIType
    value: Any = 0
    previous_value: Any = None
    change: float = 0.0
    change_label: str = ""
    change_label_ar: str = ""
    icon: str = "ArrowUpOutlined"
    color: str = "#1890ff"
    target: Optional[KPITarget] = None
    sparkline: List[float] = field(default_factory=list)
    drill_down: Optional[str] = None
    size: WidgetSize = WidgetSize.SMALL
    format: str = ""  # e.g. "#,##0.00"
    currency: str = "SAR"
    module: str = ""


@dataclass
class ChartDataset:
    label: str
    label_ar: str
    data: List[float]
    color: str = "#1890ff"
    type: Optional[ChartType] = None  # For combo charts


@dataclass
class ChartWidget:
    code: str
    title: str
    title_ar: str
    chart_type: ChartType
    datasets: List[ChartDataset] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    x_axis_label: str = ""
    y_axis_label: str = ""
    x_axis_label_ar: str = ""
    y_axis_label_ar: str = ""
    size: WidgetSize = WidgetSize.MEDIUM
    module: str = ""
    colors: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    code: str
    title: str
    title_ar: str
    message: str
    message_ar: str
    severity: AlertSeverity
    entity: str = ""
    entity_id: str = ""
    action_url: str = ""
    action_label: str = ""
    action_label_ar: str = ""
    created_at: str = ""
    is_read: bool = False
    module: str = ""


@dataclass
class ActivityItem:
    id: str
    action: str
    action_ar: str
    entity: str
    entity_id: str
    entity_name: str
    user: str
    user_name: str
    timestamp: str
    details: str = ""
    details_ar: str = ""
    icon: str = "FileOutlined"
    color: str = "#1890ff"


@dataclass
class DashboardLayout:
    """Defines the layout grid for a dashboard."""
    rows: List[List[Dict[str, Any]]] = field(default_factory=list)
    # Each row is a list of widgets with their size


@dataclass
class DashboardDefinition:
    code: str
    name: str
    name_ar: str
    description: str = ""
    industry: str = ""
    layout: DashboardLayout = field(default_factory=DashboardLayout)
    kpis: List[KPICard] = field(default_factory=list)
    charts: List[ChartWidget] = field(default_factory=list)
    alerts_config: List[Dict[str, Any]] = field(default_factory=list)
    activity_config: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: int = 300  # seconds
    is_default: bool = False


class DashboardEngine:
    """
    Generates and manages dashboards per industry.
    Each industry template defines its own dashboard with KPIs, charts, and alerts.
    """

    def __init__(self):
        self._dashboards: Dict[str, DashboardDefinition] = {}
        self._kpis: Dict[str, KPICard] = {}
        self._charts: Dict[str, ChartWidget] = {}
        self._alerts: Dict[str, Alert] = {}
        self._activities: List[ActivityItem] = []
        self._register_builtins()

    def _register_builtins(self):
        """Register core and industry dashboards."""

        # ── Core Dashboard ──────────────────────
        core_dashboard = DashboardDefinition(
            code="core_main", name="Main Dashboard", name_ar="الرئيسية",
            industry="core", is_default=True,
            kpis=[
                KPICard("total_revenue", "Revenue", "الإيرادات", KPIType.CURRENCY,
                       color="#52c41a", icon="RiseOutlined", module="accounting"),
                KPICard("total_expenses", "Expenses", "المصروفات", KPIType.CURRENCY,
                       color="#ff4d4f", icon="FallOutlined", module="accounting"),
                KPICard("net_profit", "Net Profit", "صافي الربح", KPIType.CURRENCY,
                       color="#1890ff", icon="DollarOutlined", module="accounting"),
                KPICard("active_projects", "Active Projects", "المشاريع النشطة", KPIType.COUNT,
                       color="#722ed1", icon="ProjectOutlined", module="projects"),
            ],
            charts=[
                ChartWidget("revenue_expense_trend", "Revenue vs Expenses", "الإيرادات مقابل المصروفات",
                           ChartType.LINE, size=WidgetSize.LARGE, module="accounting"),
                ChartWidget("top_products", "Top Products", "المنتجات الأكثر مبيعًا",
                           ChartType.BAR, size=WidgetSize.MEDIUM, module="sales"),
            ],
        )
        self._dashboards["core_main"] = core_dashboard

        # ── Construction Dashboard ──────────────
        construction_dashboard = DashboardDefinition(
            code="construction_main", name="Construction Dashboard", name_ar="لوحة التحكم",
            industry="construction",
            layout=DashboardLayout(rows=[
                [{"widget": "project_portfolio", "size": "full"}],
                [{"widget": "contract_value", "size": "medium"}, {"widget": "actual_cost", "size": "medium"}],
                [{"widget": "gross_profit", "size": "medium"}, {"widget": "project_completion", "size": "medium"}],
                [{"widget": "cost_breakdown", "size": "large"}, {"widget": "overdue_projects", "size": "medium"}],
                [{"widget": "recent_activities", "size": "large"}, {"widget": "alerts", "size": "medium"}],
            ]),
            kpis=[
                KPICard("project_portfolio", "Project Portfolio", "محفظة المشاريع", KPIType.COUNT,
                       icon="ProjectOutlined", color="#1890ff", module="projects"),
                KPICard("contract_value", "Contract Value", "قيمة العقود", KPIType.CURRENCY,
                       icon="FileTextOutlined", color="#52c41a", module="projects"),
                KPICard("actual_cost", "Actual Cost", "التكلفة الفعلية", KPIType.CURRENCY,
                       icon="DollarOutlined", color="#ff4d4f", module="accounting"),
                KPICard("committed_cost", "Committed Cost", "التكاليف الملزمة", KPIType.CURRENCY,
                       icon="LockOutlined", color="#faad14", module="procurement"),
                KPICard("gross_profit", "Gross Profit", "الربح الإجمالي", KPIType.CURRENCY,
                       icon="RiseOutlined", color="#52c41a", module="accounting"),
                KPICard("project_completion", "Project Completion", "نسبة الإنجاز", KPIType.PERCENTAGE,
                       icon="CheckCircleOutlined", color="#13c2c2", module="projects"),
                KPICard("overdue_projects", "Overdue Projects", "مشاريع متأخرة", KPIType.COUNT,
                       icon="WarningOutlined", color="#ff4d4f", module="projects"),
                KPICard("cash_flow", "Cash Flow", "التدفق النقدي", KPIType.CURRENCY,
                       icon="BankOutlined", color="#722ed1", module="treasury"),
            ],
            charts=[
                ChartWidget("cost_breakdown", "Cost Breakdown", "تفصيل التكاليف",
                           ChartType.PIE, size=WidgetSize.LARGE, module="accounting",
                           labels=["Materials", "Labor", "Equipment", "Subcontract", "Overhead"],
                           datasets=[ChartDataset("Cost", "التكلفة", [35, 25, 15, 20, 5],
                                                 color="#1890ff")]),
                ChartWidget("project_progress", "Project Progress", "تقدم المشاريع",
                           ChartType.BAR, size=WidgetSize.LARGE, module="projects"),
                ChartWidget("monthly_revenue", "Monthly Revenue", "الإيرادات الشهرية",
                           ChartType.AREA, size=WidgetSize.LARGE, module="accounting"),
                ChartWidget("equipment_utilization", "Equipment Utilization", "استغلال المعدات",
                           ChartType.GAUGE, size=WidgetSize.MEDIUM, module="projects"),
            ],
        )
        self._dashboards["construction_main"] = construction_dashboard

        # ── Trading Dashboard ───────────────────
        trading_dashboard = DashboardDefinition(
            code="trading_main", name="Trading Dashboard", name_ar="لوحة التحكم",
            industry="trading",
            kpis=[
                KPICard("daily_sales", "Today's Sales", "مبيعات اليوم", KPIType.CURRENCY,
                       icon="ShoppingCartOutlined", color="#52c41a", module="sales"),
                KPICard("monthly_sales", "Monthly Sales", "مبيعات الشهر", KPIType.CURRENCY,
                       icon="RiseOutlined", color="#1890ff", module="sales"),
                KPICard("outstanding_receivables", "Receivables", "المبالغ المستحقة", KPIType.CURRENCY,
                       icon="UserOutlined", color="#faad14", module="accounting"),
                KPICard("low_stock_items", "Low Stock Items", "أصناف تحت الحد الأدنى", KPIType.COUNT,
                       icon="WarningOutlined", color="#ff4d4f", module="inventory"),
                KPICard("gross_margin", "Gross Margin", "هامش الربح", KPIType.PERCENTAGE,
                       icon="PercentageOutlined", color="#52c41a", module="sales"),
                KPICard("pending_orders", "Pending Orders", "الطلبات المعلقة", KPIType.COUNT,
                       icon="ClockCircleOutlined", color="#faad14", module="sales"),
            ],
            charts=[
                ChartWidget("sales_trend", "Sales Trend", "اتجاه المبيعات",
                           ChartType.LINE, size=WidgetSize.LARGE, module="sales"),
                ChartWidget("sales_by_category", "Sales by Category", "المبيعات حسب التصنيف",
                           ChartType.PIE, size=WidgetSize.MEDIUM, module="sales"),
                ChartWidget("top_customers", "Top Customers", "أكبر العملاء",
                           ChartType.BAR, size=WidgetSize.MEDIUM, module="sales"),
            ],
        )
        self._dashboards["trading_main"] = trading_dashboard

        # ── Restaurant Dashboard ────────────────
        restaurant_dashboard = DashboardDefinition(
            code="restaurant_main", name="Restaurant Dashboard", name_ar="لوحة التحكم",
            industry="restaurant",
            kpis=[
                KPICard("daily_sales", "Today's Sales", "مبيعات اليوم", KPIType.CURRENCY,
                       icon="DollarOutlined", color="#52c41a", module="sales"),
                KPICard("orders_count", "Orders", "الطلبات", KPIType.COUNT,
                       icon="ShoppingCartOutlined", color="#1890ff", module="sales"),
                KPICard("avg_ticket", "Average Ticket", "متوسط التذكرة", KPIType.CURRENCY,
                       icon="RiseOutlined", color="#722ed1", module="sales"),
                KPICard("food_cost_pct", "Food Cost %", "نسبة تكلفة الطعام", KPIType.PERCENTAGE,
                       icon="PercentageOutlined", color="#faad14", module="inventory"),
                KPICard("top_item", "Top Item", "ال selling الأعلى", KPIType.COUNT,
                       icon="StarOutlined", color="#52c41a", module="sales"),
                KPICard("kitchen_load", "Kitchen Load", "حِمل المطبخ", KPIType.COUNT,
                       icon="FireOutlined", color="#ff4d4f", module="inventory"),
                KPICard("waste_pct", "Waste %", "نسبة الهدر", KPIType.PERCENTAGE,
                       icon="DeleteOutlined", color="#ff4d4f", module="inventory"),
                KPICard("tables_occupied", "Tables Occupied", "الطاولات المشغولة", KPIType.COUNT,
                       icon="TeamOutlined", color="#13c2c2", module="sales"),
            ],
            charts=[
                ChartWidget("hourly_sales", "Hourly Sales", "المبيعات بالساعة",
                           ChartType.AREA, size=WidgetSize.LARGE, module="sales"),
                ChartWidget("popular_items", "Popular Items", "الأكثر طلبًا",
                           ChartType.BAR, size=WidgetSize.MEDIUM, module="sales"),
                ChartWidget("table_status", "Table Status", "حالة الطاولات",
                           ChartType.DONUT, size=WidgetSize.MEDIUM, module="sales"),
            ],
        )
        self._dashboards["restaurant_main"] = restaurant_dashboard

        # ── Manufacturing Dashboard ─────────────
        manufacturing_dashboard = DashboardDefinition(
            code="manufacturing_main", name="Manufacturing Dashboard", name_ar="لوحة التحكم",
            industry="manufacturing",
            kpis=[
                KPICard("production_today", "Production Today", "إنتاج اليوم", KPIType.COUNT,
                       icon="SettingOutlined", color="#1890ff", module="projects"),
                KPICard("oee", "OEE", "كفاءة المعدات", KPIType.PERCENTAGE,
                       icon="DashboardOutlined", color="#52c41a", module="projects"),
                KPICard("active_orders", "Production Orders", "أوامر الإنتاج", KPIType.COUNT,
                       icon="PlayCircleOutlined", color="#722ed1", module="projects"),
                KPICard("material_shortages", "Material Shortages", "نقص المواد", KPIType.COUNT,
                       icon="WarningOutlined", color="#ff4d4f", module="inventory"),
                KPICard("wip_value", "WIP Value", "قيمة قيد التنفيذ", KPIType.CURRENCY,
                       icon="SyncOutlined", color="#faad14", module="inventory"),
                KPICard("scrap_rate", "Scrap Rate", "نسبة الهالك", KPIType.PERCENTAGE,
                       icon="DeleteOutlined", color="#ff4d4f", module="projects"),
                KPICard("production_cost", "Production Cost", "تكلفة الإنتاج", KPIType.CURRENCY,
                       icon="DollarOutlined", color="#13c2c2", module="accounting"),
            ],
            charts=[
                ChartWidget("production_output", "Production Output", "الإنتاج",
                           ChartType.LINE, size=WidgetSize.LARGE, module="projects"),
                ChartWidget("quality_metrics", "Quality Metrics", "مؤشرات الجودة",
                           ChartType.BAR, size=WidgetSize.MEDIUM, module="projects"),
                ChartWidget("capacity_utilization", "Capacity Utilization", "استغلال الطاقة",
                           ChartType.GAUGE, size=WidgetSize.MEDIUM, module="projects"),
            ],
        )
        self._dashboards["manufacturing_main"] = manufacturing_dashboard

        # ── Services Dashboard ──────────────────
        services_dashboard = DashboardDefinition(
            code="services_main", name="Services Dashboard", name_ar="لوحة التحكم",
            industry="services",
            kpis=[
                KPICard("active_projects", "Active Projects", "المشاريع النشطة", KPIType.COUNT,
                       icon="ProjectOutlined", color="#1890ff", module="projects"),
                KPICard("billable_hours", "Billable Hours", "الساعات الفاتورة", KPIType.DURATION,
                       icon="ClockCircleOutlined", color="#52c41a", module="projects"),
                KPICard("utilization_rate", "Utilization Rate", "نسبة الاستغلال", KPIType.PERCENTAGE,
                       icon="DashboardOutlined", color="#722ed1", module="projects"),
                KPICard("outstanding_invoices", "Outstanding Invoices", "الفواتير المعلقة", KPIType.CURRENCY,
                       icon="FileTextOutlined", color="#faad14", module="sales"),
                KPICard("project_profitability", "Project Profitability", "ربحية المشاريع", KPIType.PERCENTAGE,
                       icon="RiseOutlined", color="#52c41a", module="projects"),
            ],
            charts=[
                ChartWidget("revenue_by_project", "Revenue by Project", "الإيرادات حسب المشروع",
                           ChartType.BAR, size=WidgetSize.LARGE, module="projects"),
                ChartWidget("utilization_trend", "Utilization Trend", "اتجاه الاستغلال",
                           ChartType.LINE, size=WidgetSize.MEDIUM, module="projects"),
            ],
        )
        self._dashboards["services_main"] = services_dashboard

    def register_dashboard(self, dashboard: DashboardDefinition):
        """Register a dashboard definition."""
        self._dashboards[dashboard.code] = dashboard

    def get_dashboard(self, code: str) -> Optional[DashboardDefinition]:
        """Get dashboard by code."""
        return self._dashboards.get(code)

    def get_industry_dashboard(self, industry: str) -> Optional[DashboardDefinition]:
        """Get the default dashboard for an industry."""
        for d in self._dashboards.values():
            if d.industry == industry and d.is_default:
                return d
        # Fallback to industry_main pattern
        return self._dashboards.get(f"{industry}_main")

    def get_all_dashboards(self) -> Dict[str, DashboardDefinition]:
        return dict(self._dashboards)

    def generate_dashboard_data(self, industry: str, db=None) -> Dict[str, Any]:
        """
        Generate complete dashboard data for rendering.
        Returns KPIs, charts, alerts, and activities.
        """
        dashboard = self.get_industry_dashboard(industry)
        if not dashboard:
            dashboard = self._dashboards.get("core_main")
        if not dashboard:
            return {"error": "No dashboard found"}

        return {
            "code": dashboard.code,
            "name": dashboard.name,
            "name_ar": dashboard.name_ar,
            "layout": {
                "rows": [{"widgets": row} for row in dashboard.layout.rows]
            } if dashboard.layout.rows else None,
            "kpis": [self._serialize_kpi(k) for k in dashboard.kpis],
            "charts": [self._serialize_chart(c) for c in dashboard.charts],
            "alerts": [self._serialize_alert(a) for a in self._alerts.values()
                      if a.module in [k.module for k in dashboard.kpis]],
            "activities": [self._serialize_activity(a) for a in self._activities[-20:]],
            "refresh_interval": dashboard.refresh_interval,
        }

    def add_alert(self, alert: Alert):
        """Add an alert."""
        self._alerts[alert.code] = alert

    def add_activity(self, activity: ActivityItem):
        """Add an activity item."""
        self._activities.append(activity)
        if len(self._activities) > 100:
            self._activities = self._activities[-100:]

    def get_alerts(self, industry: str = "", module: str = "") -> List[Alert]:
        """Get alerts filtered by industry/module."""
        alerts = list(self._alerts.values())
        if module:
            alerts = [a for a in alerts if a.module == module]
        return alerts

    def _serialize_kpi(self, kpi: KPICard) -> Dict[str, Any]:
        return {
            "code": kpi.code, "title": kpi.title, "title_ar": kpi.title_ar,
            "type": kpi.kpi_type.value, "value": kpi.value,
            "previous_value": kpi.previous_value,
            "change": kpi.change, "change_label": kpi.change_label,
            "icon": kpi.icon, "color": kpi.color,
            "target": {"value": kpi.target.value, "label": kpi.target.label} if kpi.target else None,
            "sparkline": kpi.sparkline,
            "drill_down": kpi.drill_down,
            "size": kpi.size.value, "format": kpi.format,
            "currency": kpi.currency, "module": kpi.module,
        }

    def _serialize_chart(self, chart: ChartWidget) -> Dict[str, Any]:
        return {
            "code": chart.code, "title": chart.title, "title_ar": chart.title_ar,
            "chart_type": chart.chart_type.value,
            "datasets": [{"label": d.label, "label_ar": d.label_ar, "data": d.data, "color": d.color}
                        for d in chart.datasets],
            "labels": chart.labels,
            "size": chart.size.value, "module": chart.module,
            "colors": chart.colors, "options": chart.options,
        }

    def _serialize_alert(self, alert: Alert) -> Dict[str, Any]:
        return {
            "code": alert.code, "title": alert.title, "title_ar": alert.title_ar,
            "message": alert.message, "message_ar": alert.message_ar,
            "severity": alert.severity.value,
            "entity": alert.entity, "entity_id": alert.entity_id,
            "action_url": alert.action_url,
            "action_label": alert.action_label,
            "created_at": alert.created_at, "is_read": alert.is_read,
        }

    def _serialize_activity(self, activity: ActivityItem) -> Dict[str, Any]:
        return {
            "id": activity.id, "action": activity.action, "action_ar": activity.action_ar,
            "entity": activity.entity, "entity_id": activity.entity_id,
            "entity_name": activity.entity_name,
            "user": activity.user_name, "timestamp": activity.timestamp,
            "icon": activity.icon, "color": activity.color,
        }

    def export_dashboard(self, industry: str) -> Dict[str, Any]:
        """Export dashboard definition for templates."""
        dashboard = self.get_industry_dashboard(industry)
        if not dashboard:
            return {}
        return {
            "code": dashboard.code,
            "name": dashboard.name,
            "name_ar": dashboard.name_ar,
            "kpis": [{"code": k.code, "title": k.title, "title_ar": k.title_ar,
                      "type": k.kpi_type.value, "module": k.module} for k in dashboard.kpis],
            "charts": [{"code": c.code, "title": c.title, "title_ar": c.title_ar,
                        "chart_type": c.chart_type.value, "module": c.module} for c in dashboard.charts],
        }
