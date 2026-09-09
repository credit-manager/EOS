"""
EOS Industry Engine — Terminology Engine
Industry-specific labels, translations, and terminology.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TermSet:
    """A set of terminology for a specific concept across languages."""
    code: str
    en: str
    ar: str
    context: str = ""  # Where this term is used


@dataclass
class IndustryTerminology:
    """Complete terminology set for an industry."""
    industry: str
    # Core concepts
    terms: Dict[str, TermSet] = field(default_factory=dict)
    # Entity names
    entity_names: Dict[str, TermSet] = field(default_factory=dict)
    # Status labels
    status_labels: Dict[str, TermSet] = field(default_factory=dict)
    # Action labels
    action_labels: Dict[str, TermSet] = field(default_factory=dict)
    # Menu labels
    menu_labels: Dict[str, TermSet] = field(default_factory=dict)
    # Dashboard labels
    dashboard_labels: Dict[str, TermSet] = field(default_factory=dict)
    # Report names
    report_names: Dict[str, TermSet] = field(default_factory=dict)


class TerminologyEngine:
    """
    Manages industry-specific terminology.
    Each industry template registers its own term set.
    """

    def __init__(self):
        self._terminology: Dict[str, IndustryTerminology] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register core platform terminology."""
        core = IndustryTerminology(
            industry="core",
            terms={
                "company": TermSet("company", "Company", "شركة"),
                "branch": TermSet("branch", "Branch", "فرع"),
                "user": TermSet("user", "User", "مستخدم"),
                "employee": TermSet("employee", "Employee", "موظف"),
                "customer": TermSet("customer", "Customer", "عميل"),
                "supplier": TermSet("supplier", "Supplier", "مورد"),
                "item": TermSet("item", "Item", "صنف"),
                "warehouse": TermSet("warehouse", "Warehouse", "مستودع"),
                "account": TermSet("account", "Account", "حساب"),
                "journal": TermSet("journal", "Journal Entry", "قيد يومي"),
                "invoice": TermSet("invoice", "Invoice", "فاتورة"),
                "payment": TermSet("payment", "Payment", "دفعة"),
                "receipt": TermSet("receipt", "Receipt", "إيصال"),
                "document": TermSet("document", "Document", "مستند"),
                "attachment": TermSet("attachment", "Attachment", "مرفق"),
                "report": TermSet("report", "Report", "تقرير"),
                "dashboard": TermSet("dashboard", "Dashboard", "لوحة التحكم"),
                "settings": TermSet("settings", "Settings", "الإعدادات"),
                "notification": TermSet("notification", "Notification", "إشعار"),
                "approval": TermSet("approval", "Approval", "موافقة"),
                "draft": TermSet("draft", "Draft", "مسودة"),
                "submitted": TermSet("submitted", "Submitted", "مقدّم"),
                "approved": TermSet("approved", "Approved", "مُعتمد"),
                "rejected": TermSet("rejected", "Rejected", "مرفوض"),
                "cancelled": TermSet("cancelled", "Cancelled", "ملغي"),
                "active": TermSet("active", "Active", "نشط"),
                "inactive": TermSet("inactive", "Inactive", "غير نشط"),
            },
            entity_names={
                "account": TermSet("account", "Account", "حساب"),
                "journal_entry": TermSet("journal_entry", "Journal Entry", "قيد يومي"),
                "customer": TermSet("customer", "Customer", "عميل"),
                "supplier": TermSet("supplier", "Supplier", "مورد"),
                "employee": TermSet("employee", "Employee", "موظف"),
                "item": TermSet("item", "Item", "صنف"),
                "warehouse": TermSet("warehouse", "Warehouse", "مستودع"),
                "project": TermSet("project", "Project", "مشروع"),
            },
            action_labels={
                "create": TermSet("create", "Create", "إنشاء"),
                "edit": TermSet("edit", "Edit", "تعديل"),
                "delete": TermSet("delete", "Delete", "حذف"),
                "save": TermSet("save", "Save", "حفظ"),
                "cancel": TermSet("cancel", "Cancel", "إلغاء"),
                "submit": TermSet("submit", "Submit", "تقديم"),
                "approve": TermSet("approve", "Approve", "اعتماد"),
                "reject": TermSet("reject", "Reject", "رفض"),
                "print": TermSet("print", "Print", "طباعة"),
                "export": TermSet("export", "Export", "تصدير"),
                "import": TermSet("import", "Import", "استيراد"),
            },
        )
        self._terminology["core"] = core

        # Construction terminology
        construction = IndustryTerminology(
            industry="construction",
            terms={
                "project": TermSet("project", "Project", "مشروع"),
                "contract": TermSet("contract", "Contract", "عقد"),
                "boq": TermSet("boq", "Bill of Quantities", "جدول الكميات"),
                "boq_item": TermSet("boq_item", "BOQ Item", "بند جدول الكميات"),
                "variation": TermSet("variation", "Variation Order", "أمر تغيير"),
                "subcontractor": TermSet("subcontractor", "Subcontractor", "مقاول باطن"),
                "consultant": TermSet("consultant", "Consultant", "استشاري"),
                "owner": TermSet("owner", "Project Owner", "المالك"),
                "site": TermSet("site", "Project Site", "موقع المشروع"),
                "progress": TermSet("progress", "Progress", "تقدم الأعمال"),
                "progress_cert": TermSet("progress_cert", "Progress Certificate", "شهادة إنجاز"),
                "retention": TermSet("retention", "Retention", "ضمان أداء"),
                "advance": TermSet("advance", "Advance Payment", "دفعة مقدمة"),
                "wbs": TermSet("wbs", "Work Breakdown Structure", "هيكل تفكيك الأعمال"),
                "cost_code": TermSet("cost_code", "Cost Code", "رمز التكلفة"),
                "cost_center": TermSet("cost_center", "Cost Center", "مركز التكلفة"),
                "equipment": TermSet("equipment", "Equipment", "معدات"),
                "fuel": TermSet("fuel", "Fuel", "وقود"),
                "maintenance": TermSet("maintenance", "Maintenance", "صيانة"),
                "site_diary": TermSet("site_diary", "Site Diary", "سجل الموقع"),
                "inspection": TermSet("inspection", "Inspection", "فحص"),
                "ncr": TermSet("ncr", "Non-Conformance Report", "تقرير عدم مطابقة"),
                "rfi": TermSet("rfi", "Request for Information", "طلب معلومات"),
                "submittal": TermSet("submittal", "Submittal", "تقديم"),
                "drawing": TermSet("drawing", "Drawing", "رسم"),
                "daily_report": TermSet("daily_report", "Daily Report", "تقرير يومي"),
                "material_request": TermSet("material_request", "Material Request", "طلب مواد"),
                "material_issue": TermSet("material_issue", "Material Issue", "صرف مواد"),
                "material_return": TermSet("material_return", "Material Return", "إرجاع مواد"),
                "rfq": TermSet("rfq", "Request for Quotation", "طلب عرض سعر"),
                "tender": TermSet("tender", "Tender", "مناقصة"),
                "claim": TermSet("claim", "Claim", "مطالبة"),
                "warranty": TermSet("warranty", "Warranty", "ضمان"),
            },
            entity_names={
                "project": TermSet("project", "Project", "مشروع"),
                "contract": TermSet("contract", "Contract", "عقد"),
                "boq_item": TermSet("boq_item", "BOQ Item", "بند"),
                "purchase_request": TermSet("purchase_request", "Purchase Request", "طلب شراء"),
                "purchase_order": TermSet("purchase_order", "Purchase Order", "أمر شراء"),
                "grn": TermSet("grn", "Goods Receipt", "استلام بضاعة"),
                "equipment": TermSet("equipment", "Equipment", "معدات"),
                "equipment_log": TermSet("equipment_log", "Equipment Log", "سجل تشغيل"),
                "site_diary": TermSet("site_diary", "Site Diary", "سجل موقع"),
                "inspection": TermSet("inspection", "Inspection", "فحص"),
                "variation": TermSet("variation", "Variation", "تغيير"),
                "progress_cert": TermSet("progress_cert", "Progress Certificate", "شهادة إنجاز"),
            },
            status_labels={
                "planning": TermSet("planning", "Planning", "التخطيط"),
                "active": TermSet("active", "Active", "نشط"),
                "on_hold": TermSet("on_hold", "On Hold", "معلق"),
                "completed": TermSet("completed", "Completed", "مكتمل"),
                "cancelled": TermSet("cancelled", "Cancelled", "ملغي"),
                "tendering": TermSet("tendering", "Tendering", "مناقصة"),
                "awarded": TermSet("awarded", "Awarded", "محسوب"),
            },
            menu_labels={
                "projects": TermSet("projects", "Projects & Contracts", "المشاريع والعقود"),
                "boq": TermSet("boq", "Bill of Quantities", "جدول الكميات"),
                "procurement": TermSet("procurement", "Procurement", "المشتريات"),
                "inventory": TermSet("inventory", "Materials & Stock", "المخزون والمواد"),
                "equipment": TermSet("equipment", "Equipment", "المعدات"),
                "site_ops": TermSet("site_ops", "Site Operations", "عمليات الموقع"),
                "finance": TermSet("finance", "Finance", "المالية"),
                "hr": TermSet("hr", "Human Resources", "الموارد البشرية"),
                "documents": TermSet("documents", "Documents", "المستندات"),
                "reports": TermSet("reports", "Reports", "التقارير"),
            },
            dashboard_labels={
                "project_portfolio": TermSet("project_portfolio", "Project Portfolio", "محفظة المشاريع"),
                "contract_value": TermSet("contract_value", "Contract Value", "قيمة العقود"),
                "actual_cost": TermSet("actual_cost", "Actual Cost", "التكلفة الفعلية"),
                "committed_cost": TermSet("committed_cost", "Committed Cost", "التكاليف الملزمة"),
                "gross_profit": TermSet("gross_profit", "Gross Profit", "الربح الإجمالي"),
                "project_completion": TermSet("project_completion", "Project Completion", "نسبة الإنجاز"),
                "overdue_projects": TermSet("overdue_projects", "Overdue Projects", "مشاريع متأخرة"),
                "cash_flow": TermSet("cash_flow", "Cash Flow", "التدفق النقدي"),
            },
        )
        self._terminology["construction"] = construction

        # Trading terminology
        trading = IndustryTerminology(
            industry="trading",
            terms={
                "sales_order": TermSet("sales_order", "Sales Order", "أمر بيع"),
                "delivery": TermSet("delivery", "Delivery Note", " تسليم"),
                "route": TermSet("route", "Route", "مسار"),
                "sales_rep": TermSet("sales_rep", "Sales Representative", "مندوب مبيعات"),
                "price_list": TermSet("price_list", "Price List", "قائمة أسعار"),
                "discount": TermSet("discount", "Discount", "خصم"),
                "credit_limit": TermSet("credit_limit", "Credit Limit", "حد الائتمان"),
                "batch": TermSet("batch", "Batch", "دفعة"),
                "serial": TermSet("serial", "Serial Number", "رقم تسلسلي"),
                "expiry": TermSet("expiry", "Expiry Date", "تاريخ الصلاحية"),
                "grn": TermSet("grn", "Goods Receipt Note", "استلام بضاعة"),
                "supplier_invoice": TermSet("supplier_invoice", "Supplier Invoice", "فاتورة مورد"),
            },
            menu_labels={
                "sales": TermSet("sales", "Sales", "المبيعات"),
                "purchasing": TermSet("purchasing", "Purchasing", "المشتريات"),
                "distribution": TermSet("distribution", "Distribution", "التوزيع"),
                "inventory": TermSet("inventory", "Inventory", "المخزون"),
            },
        )
        self._terminology["trading"] = trading

        # Restaurant terminology
        restaurant = IndustryTerminology(
            industry="restaurant",
            terms={
                "menu": TermSet("menu", "Menu", "قائمة الطعام"),
                "recipe": TermSet("recipe", "Recipe", "وصفة"),
                "ingredient": TermSet("ingredient", "Ingredient", "مكون"),
                "kitchen": TermSet("kitchen", "Kitchen", "المطبخ"),
                "kds": TermSet("kds", "Kitchen Display System", "شاشة المطبخ"),
                "table": TermSet("table", "Table", "طاولة"),
                "reservation": TermSet("reservation", "Reservation", "حجز"),
                "waiter": TermSet("waiter", "Waiter", "جرسور"),
                "order": TermSet("order", "Order", "طلب"),
                "modifier": TermSet("modifier", "Modifier", "تعديل"),
                "combo": TermSet("combo", "Combo Meal", "وجبة مجمعة"),
                "food_cost": TermSet("food_cost", "Food Cost", "تكلفة الطعام"),
                "waste": TermSet("waste", "Waste", "هدر"),
                "shift": TermSet("shift", "Shift", "وردية"),
                "daily_close": TermSet("daily_close", "Daily Closing", "إقفال يومي"),
            },
            menu_labels={
                "menu_mgmt": TermSet("menu_mgmt", "Menu", "القائمة"),
                "kitchen": TermSet("kitchen", "Kitchen", "المطبخ"),
                "orders": TermSet("orders", "Orders", "الطلبات"),
                "tables": TermSet("tables", "Tables", "الطاولات"),
                "inventory": TermSet("inventory", "Kitchen Stock", "مخزون المطبخ"),
            },
        )
        self._terminology["restaurant"] = restaurant

        # Manufacturing terminology
        manufacturing = IndustryTerminology(
            industry="manufacturing",
            terms={
                "bom": TermSet("bom", "Bill of Materials", "قائمة المواد"),
                "routing": TermSet("routing", "Routing", "مسار الإنتاج"),
                "work_center": TermSet("work_center", "Work Center", "مركز العمل"),
                "production_order": TermSet("production_order", "Production Order", "أمر إنتاج"),
                "mrp": TermSet("mrp", "Material Requirements Planning", "تخطيط متطلبات المواد"),
                "wip": TermSet("wip", "Work in Progress", "قيد التنفيذ"),
                "finished_goods": TermSet("finished_goods", "Finished Goods", "منتجات تامة"),
                "raw_materials": TermSet("raw_materials", "Raw Materials", "مواد خام"),
                "scrap": TermSet("scrap", "Scrap", "هالك"),
                "quality": TermSet("quality", "Quality Control", "مراقبة الجودة"),
                "batch": TermSet("batch", "Batch", "دفعة"),
                "oee": TermSet("oee", "Overall Equipment Effectiveness", "كفاءة المعدات الإجمالية"),
                "capacity": TermSet("capacity", "Capacity", "الطاقة الإنتاجية"),
            },
            menu_labels={
                "production": TermSet("production", "Production", "الإنتاج"),
                "quality": TermSet("quality", "Quality Control", "مراقبة الجودة"),
                "bom": TermSet("bom", "BOM", "قائمة المواد"),
            },
        )
        self._terminology["manufacturing"] = manufacturing

    def register(self, terminology: IndustryTerminology):
        """Register industry terminology."""
        self._terminology[terminology.industry] = terminology

    def get(self, industry: str) -> Optional[IndustryTerminology]:
        """Get terminology for an industry."""
        return self._terminology.get(industry)

    def get_term(self, industry: str, term_code: str, lang: str = "ar") -> str:
        """Get a specific term translation."""
        # Check industry-specific first, then fallback to core
        for ind in [industry, "core"]:
            term_set = self._terminology.get(ind)
            if term_set:
                term = term_set.terms.get(term_code)
                if term:
                    return getattr(term, lang, term.en)
        return term_code

    def get_entity_name(self, industry: str, entity_code: str, lang: str = "ar") -> str:
        """Get entity name in industry terminology."""
        for ind in [industry, "core"]:
            term_set = self._terminology.get(ind)
            if term_set:
                term = term_set.entity_names.get(entity_code)
                if term:
                    return getattr(term, lang, term.en)
        return entity_code

    def get_status_label(self, industry: str, status: str, lang: str = "ar") -> str:
        """Get status label in industry terminology."""
        for ind in [industry, "core"]:
            term_set = self._terminology.get(ind)
            if term_set:
                term = term_set.status_labels.get(status)
                if term:
                    return getattr(term, lang, term.en)
        return status

    def get_menu_label(self, industry: str, menu_key: str, lang: str = "ar") -> str:
        """Get menu label in industry terminology."""
        for ind in [industry, "core"]:
            term_set = self._terminology.get(ind)
            if term_set:
                term = term_set.menu_labels.get(menu_key)
                if term:
                    return getattr(term, lang, term.en)
        return menu_key

    def get_dashboard_label(self, industry: str, widget_key: str, lang: str = "ar") -> str:
        """Get dashboard label in industry terminology."""
        for ind in [industry, "core"]:
            term_set = self._terminology.get(ind)
            if term_set:
                term = term_set.dashboard_labels.get(widget_key)
                if term:
                    return getattr(term, lang, term.en)
        return widget_key

    def get_all_industries(self) -> List[str]:
        """Get all registered industries."""
        return list(self._terminology.keys())

    def export_terminology(self, industry: str) -> Dict[str, Any]:
        """Export terminology for a template."""
        term = self._terminology.get(industry)
        if not term:
            return {}
        return {
            "industry": term.industry,
            "terms": {k: {"en": v.en, "ar": v.ar} for k, v in term.terms.items()},
            "entity_names": {k: {"en": v.en, "ar": v.ar} for k, v in term.entity_names.items()},
            "status_labels": {k: {"en": v.en, "ar": v.ar} for k, v in term.status_labels.items()},
            "menu_labels": {k: {"en": v.en, "ar": v.ar} for k, v in term.menu_labels.items()},
            "dashboard_labels": {k: {"en": v.en, "ar": v.ar} for k, v in term.dashboard_labels.items()},
        }
