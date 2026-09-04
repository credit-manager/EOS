"""
EOS Experience Engine — Report Engine
Financial, operational, and custom reports with PDF/Excel export.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReportCategory(str, Enum):
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    SALES = "sales"
    INVENTORY = "inventory"
    HR = "hr"
    PROJECT = "project"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    HTML = "html"


class ReportFrequency(str, Enum):
    ON_DEMAND = "on_demand"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class ReportColumn:
    code: str
    title: str
    title_ar: str
    field_type: str = "text"
    width: int = 120
    align: str = "left"
    format: str = ""
    is_total: bool = False
    formula: str = ""


@dataclass
class ReportFilter:
    code: str
    label: str
    label_ar: str
    field_type: str
    default_value: Any = None
    options: list[dict[str, str]] = field(default_factory=list)
    is_required: bool = False


@dataclass
class ReportDefinition:
    code: str
    name: str
    name_ar: str
    category: ReportCategory
    description: str = ""
    description_ar: str = ""
    module: str = ""
    columns: list[ReportColumn] = field(default_factory=list)
    filters: list[ReportFilter] = field(default_factory=list)
    group_by: str = ""
    sub_total: bool = True
    grand_total: bool = True
    charts: list[dict[str, Any]] = field(default_factory=list)
    formats: list[ReportFormat] = field(default_factory=lambda: [ReportFormat.PDF, ReportFormat.EXCEL])
    frequency: ReportFrequency = ReportFrequency.ON_DEMAND
    is_system: bool = False  # System reports can't be deleted
    sql_query: str = ""  # For custom reports
    template: str = ""   # PDF template
    sort_by: str = ""
    sort_direction: str = "asc"
    page_size: int = 50
    header_fields: list[str] = field(default_factory=list)  # Fields to show in report header


class ReportEngine:
    """
    Generates and manages reports per industry.
    Each industry template defines its own report set.
    """

    def __init__(self):
        self._reports: dict[str, ReportDefinition] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register core reports."""

        # ── Financial Reports ───────────────────
        self.register(ReportDefinition(
            code="trial_balance", name="Trial Balance", name_ar="ميزان المراجعة",
            category=ReportCategory.FINANCIAL, module="accounting", is_system=True,
            description="Trial balance for a period",
            columns=[
                ReportColumn("account_code", "Account Code", "كود الحساب", width=100),
                ReportColumn("account_name", "Account Name", "اسم الحساب", width=200),
                ReportColumn("debit", "Debit", "المدين", width=150, align="right", format="#,##0.00", is_total=True),
                ReportColumn("credit", "Credit", "الدائن", width=150, align="right", format="#,##0.00", is_total=True),
                ReportColumn("balance", "Balance", "الرصيد", width=150, align="right", format="#,##0.00", is_total=True),
            ],
            filters=[
                ReportFilter("period", "Period", "الفترة", "date_range", is_required=True),
                ReportFilter("account_type", "Account Type", "نوع الحساب", "select",
                           options=[{"value": "all", "label": "All"}, {"value": "asset", "label": "Asset"},
                                  {"value": "liability", "label": "Liability"}]),
            ],
            group_by="account_type",
        ))

        self.register(ReportDefinition(
            code="income_statement", name="Income Statement", name_ar="قائمة الدخل",
            category=ReportCategory.FINANCIAL, module="accounting", is_system=True,
            description="Profit & Loss for a period",
            columns=[
                ReportColumn("category", "Category", "التصنيف", width=250),
                ReportColumn("amount", "Amount", "المبلغ", width=180, align="right", format="#,##0.00", is_total=True),
                ReportColumn("percentage", "Percentage", "النسبة", width=100, align="right", format="#,##0.0%"),
            ],
            filters=[
                ReportFilter("period", "Period", "الفترة", "date_range", is_required=True),
                ReportFilter("comparison", "Comparison", "المقارنة", "select",
                           options=[{"value": "none", "label": "None"},
                                  {"value": "previous_period", "label": "Previous Period"},
                                  {"value": "budget", "label": "Budget"}]),
            ],
        ))

        self.register(ReportDefinition(
            code="balance_sheet", name="Balance Sheet", name_ar="الميزانية العمومية",
            category=ReportCategory.FINANCIAL, module="accounting", is_system=True,
            columns=[
                ReportColumn("item", "Item", "البند", width=300),
                ReportColumn("current", "Current", "الحالي", width=150, align="right", format="#,##0.00"),
                ReportColumn("previous", "Previous", "السابق", width=150, align="right", format="#,##0.00"),
            ],
            filters=[
                ReportFilter("as_of_date", "As of Date", "تاريخ", "date", is_required=True),
            ],
        ))

        # ── Sales Reports ───────────────────────
        self.register(ReportDefinition(
            code="sales_summary", name="Sales Summary", name_ar="ملخص المبيعات",
            category=ReportCategory.SALES, module="sales",
            columns=[
                ReportColumn("period", "Period", "الفترة", width=150),
                ReportColumn("invoice_count", "Invoices", "الفواتير", width=100, align="right", is_total=True),
                ReportColumn("total_sales", "Total Sales", "إجمالي المبيعات", width=150, align="right", format="#,##0.00", is_total=True),
                ReportColumn("returns", "Returns", "المرتجعات", width=120, align="right", format="#,##0.00"),
                ReportColumn("net_sales", "Net Sales", "صافي المبيعات", width=150, align="right", format="#,##0.00", is_total=True),
            ],
            filters=[
                ReportFilter("period", "Period", "الفترة", "date_range", is_required=True),
                ReportFilter("customer", "Customer", "العميل", "reference"),
            ],
            group_by="period",
        ))

        self.register(ReportDefinition(
            code="sales_by_customer", name="Sales by Customer", name_ar="المبيعات حسب العميل",
            category=ReportCategory.SALES, module="sales",
            columns=[
                ReportColumn("customer_name", "Customer", "العميل", width=200, is_total=False),
                ReportColumn("invoice_count", "Invoices", "الفواتير", width=80, align="right"),
                ReportColumn("total_amount", "Total", "الإجمالي", width=150, align="right", format="#,##0.00", is_total=True),
                ReportColumn("percentage", "Share", "النسبة", width=80, align="right", format="#,##0.0%"),
            ],
            filters=[ReportFilter("period", "Period", "الفترة", "date_range", is_required=True)],
            sort_by="total_amount", sort_direction="desc",
        ))

        # ── Inventory Reports ───────────────────
        self.register(ReportDefinition(
            code="stock_valuation", name="Stock Valuation", name_ar="تقييم المخزون",
            category=ReportCategory.INVENTORY, module="inventory",
            columns=[
                ReportColumn("item_code", "Code", "الكود", width=100),
                ReportColumn("item_name", "Item", "الصنف", width=200),
                ReportColumn("warehouse", "Warehouse", "المستودع", width=150),
                ReportColumn("quantity", "Qty", "الكمية", width=100, align="right", is_total=True),
                ReportColumn("unit_cost", "Unit Cost", "التكلفة", width=120, align="right", format="#,##0.00"),
                ReportColumn("total_value", "Value", "القيمة", width=150, align="right", format="#,##0.00", is_total=True),
            ],
            filters=[
                ReportFilter("warehouse", "Warehouse", "المستودع", "reference"),
                ReportFilter("item_type", "Type", "النوع", "select"),
            ],
        ))

        self.register(ReportDefinition(
            code="slow_moving", name="Slow Moving Items", name_ar="أصناف بطيئة الحركة",
            category=ReportCategory.INVENTORY, module="inventory",
            columns=[
                ReportColumn("item_code", "Code", "الكود", width=100),
                ReportColumn("item_name", "Item", "الصنف", width=200),
                ReportColumn("last_sold", "Last Sold", "آخر بيع", width=120, format="DD/MM/YYYY"),
                ReportColumn("days_since", "Days", "الأيام", width=80, align="right"),
                ReportColumn("stock_qty", "Stock", "المخزون", width=100, align="right"),
                ReportColumn("stock_value", "Value", "القيمة", width=120, align="right", format="#,##0.00"),
            ],
            filters=[ReportFilter("days", "Days Since Sale", "أيام منذ آخر بيع", "number", default_value=90)],
        ))

        # ── HR Reports ──────────────────────────
        self.register(ReportDefinition(
            code="employee_list", name="Employee List", name_ar="قائمة الموظفين",
            category=ReportCategory.HR, module="hr",
            columns=[
                ReportColumn("employee_id", "ID", "الرقم", width=80),
                ReportColumn("name", "Name", "الاسم", width=200),
                ReportColumn("department", "Department", "القسم", width=150),
                ReportColumn("position", "Position", "المنصب", width=150),
                ReportColumn("hire_date", "Hire Date", "تاريخ التعيين", width=120, format="DD/MM/YYYY"),
                ReportColumn("status", "Status", "الحالة", width=100),
            ],
            filters=[
                ReportFilter("department", "Department", "القسم", "reference"),
                ReportFilter("status", "Status", "الحالة", "select"),
            ],
        ))

        self.register(ReportDefinition(
            code="attendance_summary", name="Attendance Summary", name_ar="ملخص الحضور",
            category=ReportCategory.HR, module="hr",
            columns=[
                ReportColumn("employee_name", "Employee", "الموظف", width=200),
                ReportColumn("days_present", "Present", "أيام الحضور", width=100, align="right", is_total=True),
                ReportColumn("days_absent", "Absent", "أيام الغياب", width=100, align="right", is_total=True),
                ReportColumn("hours_worked", "Hours", "الساعات", width=100, align="right", is_total=True),
                ReportColumn("overtime", "Overtime", "الساعات الإضافية", width=100, align="right", is_total=True),
            ],
            filters=[
                ReportFilter("period", "Period", "الفترة", "date_range", is_required=True),
                ReportFilter("department", "Department", "القسم", "reference"),
            ],
        ))

        # ── Project Reports ─────────────────────
        self.register(ReportDefinition(
            code="project_status", name="Project Status Report", name_ar="تقرير حالة المشاريع",
            category=ReportCategory.PROJECT, module="projects",
            columns=[
                ReportColumn("project_code", "Code", "الكود", width=100),
                ReportColumn("project_name", "Project", "المشروع", width=200),
                ReportColumn("client", "Client", "العميل", width=150),
                ReportColumn("status", "Status", "الحالة", width=100),
                ReportColumn("budget", "Budget", "الميزانية", width=150, align="right", format="#,##0", is_total=True),
                ReportColumn("actual_cost", "Actual", "الفعلي", width=150, align="right", format="#,##0", is_total=True),
                ReportColumn("variance", "Variance", "الانحراف", width=120, align="right", format="#,##0"),
                ReportColumn("progress", "Progress%", "نسبة الإنجاز", width=100, align="right"),
            ],
            filters=[
                ReportFilter("status", "Status", "الحالة", "select"),
                ReportFilter("client", "Client", "العميل", "reference"),
            ],
        ))

        self.register(ReportDefinition(
            code="project_cost", name="Project Cost Report", name_ar="تقرير تكاليف المشاريع",
            category=ReportCategory.PROJECT, module="projects",
            columns=[
                ReportColumn("project_name", "Project", "المشروع", width=200),
                ReportColumn("materials", "Materials", "المواد", width=150, align="right", format="#,##0", is_total=True),
                ReportColumn("labor", "Labor", "العمالة", width=150, align="right", format="#,##0", is_total=True),
                ReportColumn("equipment", "Equipment", "المعدات", width=150, align="right", format="#,##0", is_total=True),
                ReportColumn("subcontract", "Subcontract", "المقاولون", width=150, align="right", format="#,##0", is_total=True),
                ReportColumn("overhead", "Overhead", "النفقات العامة", width=150, align="right", format="#,##0"),
                ReportColumn("total", "Total", "الإجمالي", width=150, align="right", format="#,##0", is_total=True),
            ],
            filters=[ReportFilter("project", "Project", "المشروع", "reference")],
        ))

    def register(self, report: ReportDefinition):
        """Register a report definition."""
        self._reports[report.code] = report

    def get(self, code: str) -> ReportDefinition | None:
        """Get report by code."""
        return self._reports.get(code)

    def get_by_category(self, category: ReportCategory) -> list[ReportDefinition]:
        """Get reports by category."""
        return [r for r in self._reports.values() if r.category == category]

    def get_by_module(self, module: str) -> list[ReportDefinition]:
        """Get reports by module."""
        return [r for r in self._reports.values() if r.module == module]

    def get_all(self) -> dict[str, ReportDefinition]:
        return dict(self._reports)

    def generate_report_config(self, code: str) -> dict[str, Any]:
        """Generate report configuration for frontend rendering."""
        report = self._reports.get(code)
        if not report:
            return {"error": f"Report '{code}' not found"}

        return {
            "code": report.code,
            "name": report.name,
            "name_ar": report.name_ar,
            "category": report.category.value,
            "description": report.description_ar or report.description,
            "module": report.module,
            "columns": [{
                "code": c.code, "title": c.title_ar or c.title, "title_en": c.title,
                "type": c.field_type, "width": c.width, "align": c.align,
                "format": c.format, "is_total": c.is_total,
            } for c in report.columns],
            "filters": [{
                "code": f.code, "label": f.label_ar or f.label, "label_en": f.label,
                "type": f.field_type, "default": f.default_value,
                "options": f.options, "required": f.is_required,
            } for f in report.filters],
            "group_by": report.group_by,
            "sub_total": report.sub_total,
            "grand_total": report.grand_total,
            "formats": [f.value for f in report.formats],
            "frequency": report.frequency.value,
            "sort_by": report.sort_by,
            "sort_direction": report.sort_direction,
        }

    def get_report_list(self, industry: str = "", module: str = "") -> list[dict[str, Any]]:
        """Get list of available reports, optionally filtered."""
        reports = self._reports.values()
        if module:
            reports = [r for r in reports if r.module == module]

        return [{
            "code": r.code, "name": r.name, "name_ar": r.name_ar,
            "category": r.category.value, "module": r.module,
            "description": r.description_ar or r.description,
            "formats": [f.value for f in r.formats],
        } for r in reports]

    def export_reports(self, module: str = "") -> list[dict[str, Any]]:
        """Export report definitions for templates."""
        return self.get_report_list(module=module)
