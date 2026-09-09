"""
EOS Experience Engine — List/Grid Engine
Search, filters, sorting, saved views, export, bulk actions.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ViewType(str, Enum):
    TABLE = "table"
    GRID = "grid"
    KANBAN = "kanban"
    CALENDAR = "calendar"
    TIMELINE = "timeline"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class BulkAction(str, Enum):
    DELETE = "delete"
    EXPORT = "export"
    STATUS_CHANGE = "status_change"
    ASSIGN = "assign"
    PRINT = "print"
    CUSTOM = "custom"


@dataclass
class ColumnDef:
    code: str
    title: str
    title_ar: str
    field_type: str = "text"
    width: int = 150
    is_sortable: bool = True
    is_filterable: bool = True
    is_searchable: bool = False
    is_visible: bool = True
    is_frozen: bool = False
    align: str = "left"  # left, center, right
    format: str = ""  # e.g. "#,##0.00" for numbers, "DD/MM/YYYY" for dates
    render: str = ""  # Custom render function name
    tooltip: str = ""
    tooltip_ar: str = ""
    color_field: str = ""  # Field to determine row color


@dataclass
class FilterDef:
    code: str
    label: str
    label_ar: str
    field_type: str
    field: str
    operator: FilterOperator = FilterOperator.EQ
    options: List[Dict[str, str]] = field(default_factory=list)
    default_value: Any = None
    is_visible: bool = True
    group: str = ""


@dataclass
class SortConfig:
    field: str
    direction: SortDirection = SortDirection.ASC


@dataclass
class SavedView:
    code: str
    name: str
    name_ar: str
    user_id: str
    columns: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    sort: List[SortConfig] = field(default_factory=list)
    view_type: ViewType = ViewType.TABLE
    page_size: int = 20
    is_default: bool = False
    is_shared: bool = False


@dataclass
class ListConfig:
    """Complete list configuration for an entity."""
    entity: str
    title: str
    title_ar: str
    columns: List[ColumnDef] = field(default_factory=list)
    filters: List[FilterDef] = field(default_factory=list)
    default_sort: List[SortConfig] = field(default_factory=list)
    default_view: ViewType = ViewType.TABLE
    page_size: int = 20
    page_size_options: List[int] = field(default_factory=lambda: [10, 20, 50, 100])
    searchable: bool = True
    search_fields: List[str] = field(default_factory=list)
    bulk_actions: List[BulkAction] = field(default_factory=list)
    export_formats: List[str] = field(default_factory=lambda: ["csv", "excel", "pdf"])
    row_actions: List[str] = field(default_factory=lambda: ["view", "edit", "delete"])
    row_click: str = "view"  # view, edit, none
    empty_state_icon: str = "InboxOutlined"
    empty_state_text: str = "No data"
    empty_state_text_ar: str = "لا توجد بيانات"
    title_field: str = "name"
    subtitle_field: str = ""
    avatar_field: str = ""
    group_by: str = ""
    kanban_field: str = ""  # For kanban view
    calendar_date_field: str = ""  # For calendar view


class ListEngine:
    """
    Generates list/grid configurations for entities.
    Each industry can customize list views per entity.
    """

    def __init__(self):
        self._lists: Dict[str, ListConfig] = {}
        self._views: Dict[str, List[SavedView]] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register core list configurations."""

        # ── Projects List ───────────────────────
        self.register(ListConfig(
            entity="project", title="Projects", title_ar="المشاريع",
            columns=[
                ColumnDef("code", "Code", "الكود", width=100, is_searchable=True),
                ColumnDef("name", "Name", "الاسم", width=250, is_searchable=True),
                ColumnDef("client", "Client", "العميل", width=150),
                ColumnDef("status", "Status", "الحالة", width=120, color_field="status"),
                ColumnDef("start_date", "Start Date", "تاريخ البداية", width=120, format="DD/MM/YYYY"),
                ColumnDef("end_date", "End Date", "تاريخ النهاية", width=120, format="DD/MM/YYYY"),
                ColumnDef("budget", "Budget", "الميزانية", width=150, align="right", format="#,##0"),
                ColumnDef("actual_cost", "Actual Cost", "التكلفة", width=150, align="right", format="#,##0"),
                ColumnDef("progress", "Progress", "التقدم", width=100, render="progress_bar"),
            ],
            filters=[
                FilterDef("status", "Status", "الحالة", "select", "status",
                         options=[{"value": "planning", "label": "Planning"},
                                {"value": "active", "label": "Active"},
                                {"value": "completed", "label": "Completed"}]),
                FilterDef("client", "Client", "العميل", "text", "client"),
            ],
            default_sort=[SortConfig("created_at", SortDirection.DESC)],
            searchable=True, search_fields=["code", "name", "client"],
            bulk_actions=[BulkAction.DELETE, BulkAction.EXPORT],
            title_field="name", subtitle_field="client",
        ))

        # ── Purchase Orders List ────────────────
        self.register(ListConfig(
            entity="purchase_order", title="Purchase Orders", title_ar="أوامر الشراء",
            columns=[
                ColumnDef("po_number", "PO No.", "رقم الأمر", width=120, is_searchable=True),
                ColumnDef("supplier", "Supplier", "المورد", width=180, is_searchable=True),
                ColumnDef("po_date", "Date", "التاريخ", width=120, format="DD/MM/YYYY"),
                ColumnDef("delivery_date", "Delivery", "التسليم", width=120, format="DD/MM/YYYY"),
                ColumnDef("total", "Total", "الإجمالي", width=150, align="right", format="#,##0.00"),
                ColumnDef("status", "Status", "الحالة", width=120, color_field="status"),
                ColumnDef("approved_by", "Approved By", "اعتمد بواسطة", width=150),
            ],
            filters=[
                FilterDef("status", "Status", "الحالة", "select", "status",
                         options=[{"value": "draft", "label": "Draft"},
                                {"value": "pending", "label": "Pending"},
                                {"value": "approved", "label": "Approved"},
                                {"value": "received", "label": "Received"}]),
                FilterDef("supplier", "Supplier", "المورد", "text", "supplier"),
            ],
            default_sort=[SortConfig("po_date", SortDirection.DESC)],
            searchable=True, search_fields=["po_number", "supplier"],
            bulk_actions=[BulkAction.DELETE, BulkAction.EXPORT, BulkAction.PRINT],
        ))

        # ── Stock List ──────────────────────────
        self.register(ListConfig(
            entity="stock", title="Stock Levels", title_ar="مستويات المخزون",
            columns=[
                ColumnDef("item_code", "Code", "كود الصنف", width=120, is_searchable=True),
                ColumnDef("item_name", "Item", "الصنف", width=200, is_searchable=True),
                ColumnDef("warehouse", "Warehouse", "المستودع", width=150),
                ColumnDef("on_hand", "On Hand", "المتوفر", width=100, align="right"),
                ColumnDef("reserved", "Reserved", "محجوز", width=100, align="right"),
                ColumnDef("available", "Available", "المتاح", width=100, align="right"),
                ColumnDef("min_stock", "Min Stock", "الحد الأدنى", width=100, align="right"),
                ColumnDef("reorder", "Reorder", "إعادة طلب", width=80, render="alert_badge"),
                ColumnDef("value", "Value", "القيمة", width=150, align="right", format="#,##0.00"),
            ],
            filters=[
                FilterDef("warehouse", "Warehouse", "المستودع", "select", "warehouse"),
                FilterDef("low_stock", "Low Stock", "تحت الحد الأدنى", "boolean", "low_stock"),
            ],
            default_sort=[SortConfig("item_name", SortDirection.ASC)],
            searchable=True, search_fields=["item_code", "item_name"],
            bulk_actions=[BulkAction.EXPORT],
        ))

        # ── Employees List ──────────────────────
        self.register(ListConfig(
            entity="employee", title="Employees", title_ar="الموظفون",
            columns=[
                ColumnDef("employee_id", "ID", "الرقم", width=100, is_searchable=True),
                ColumnDef("name", "Name", "الاسم", width=200, is_searchable=True),
                ColumnDef("department", "Department", "القسم", width=150),
                ColumnDef("position", "Position", "المنصب", width=150),
                ColumnDef("hire_date", "Hire Date", "تاريخ التعيين", width=120, format="DD/MM/YYYY"),
                ColumnDef("status", "Status", "الحالة", width=100, color_field="status"),
            ],
            filters=[
                FilterDef("department", "Department", "القسم", "select", "department"),
                FilterDef("status", "Status", "الحالة", "select", "status"),
            ],
            default_sort=[SortConfig("name", SortDirection.ASC)],
            searchable=True, search_fields=["employee_id", "name"],
            bulk_actions=[BulkAction.DELETE, BulkAction.EXPORT],
        ))

        # ── Items List ──────────────────────────
        self.register(ListConfig(
            entity="item", title="Items", title_ar="الأصناف",
            columns=[
                ColumnDef("code", "Code", "الكود", width=100, is_searchable=True),
                ColumnDef("name", "Name", "الاسم", width=200, is_searchable=True),
                ColumnDef("item_type", "Type", "النوع", width=120),
                ColumnDef("unit", "Unit", "الوحدة", width=80),
                ColumnDef("cost_price", "Cost Price", "التكلفة", width=120, align="right", format="#,##0.00"),
                ColumnDef("sell_price", "Sell Price", "البيع", width=120, align="right", format="#,##0.00"),
                ColumnDef("stock", "Stock", "المخزون", width=100, align="right"),
                ColumnDef("status", "Status", "الحالة", width=80, color_field="status"),
            ],
            filters=[
                FilterDef("item_type", "Type", "النوع", "select", "item_type",
                         options=[{"value": "product", "label": "Product"},
                                {"value": "service", "label": "Service"},
                                {"value": "raw_material", "label": "Raw Material"}]),
            ],
            default_sort=[SortConfig("name", SortDirection.ASC)],
            searchable=True, search_fields=["code", "name"],
            bulk_actions=[BulkAction.DELETE, BulkAction.EXPORT],
        ))

    def register(self, config: ListConfig):
        """Register a list configuration."""
        self._lists[config.entity] = config

    def get(self, entity: str) -> Optional[ListConfig]:
        """Get list config for an entity."""
        return self._lists.get(entity)

    def get_all(self) -> Dict[str, ListConfig]:
        return dict(self._lists)

    def generate_list_config(self, entity: str, user_id: str = "") -> Dict[str, Any]:
        """
        Generate complete list configuration for frontend rendering.
        """
        config = self._lists.get(entity)
        if not config:
            return {"error": f"No list config for entity '{entity}'"}

        # Get user's saved views
        saved_views = self._views.get(f"{entity}:{user_id}", [])

        return {
            "entity": config.entity,
            "title": config.title,
            "title_ar": config.title_ar,
            "columns": [self._serialize_column(c) for c in config.columns],
            "filters": [self._serialize_filter(f) for f in config.filters],
            "default_sort": [{"field": s.field, "direction": s.direction.value} for s in config.default_sort],
            "default_view": config.default_view.value,
            "page_size": config.page_size,
            "page_size_options": config.page_size_options,
            "searchable": config.searchable,
            "search_fields": config.search_fields,
            "bulk_actions": [a.value for a in config.bulk_actions],
            "export_formats": config.export_formats,
            "row_actions": config.row_actions,
            "row_click": config.row_click,
            "empty_state": {
                "icon": config.empty_state_icon,
                "text": config.empty_state_text_ar,
                "text_en": config.empty_state_text,
            },
            "title_field": config.title_field,
            "subtitle_field": config.subtitle_field,
            "saved_views": [{"code": v.code, "name": v.name_ar, "is_default": v.is_default} for v in saved_views],
        }

    def save_view(self, entity: str, user_id: str, view: SavedView):
        """Save a view for a user."""
        key = f"{entity}:{user_id}"
        if key not in self._views:
            self._views[key] = []
        # Replace existing with same code
        self._views[key] = [v for v in self._views[key] if v.code != view.code]
        self._views[key].append(view)

    def get_views(self, entity: str, user_id: str) -> List[SavedView]:
        """Get user's saved views for an entity."""
        return self._views.get(f"{entity}:{user_id}", [])

    def delete_view(self, entity: str, user_id: str, view_code: str):
        """Delete a saved view."""
        key = f"{entity}:{user_id}"
        if key in self._views:
            self._views[key] = [v for v in self._views[key] if v.code != view_code]

    def _serialize_column(self, col: ColumnDef) -> Dict[str, Any]:
        return {
            "code": col.code, "title": col.title, "title_ar": col.title_ar,
            "type": col.field_type, "width": col.width,
            "sortable": col.is_sortable, "filterable": col.is_filterable,
            "searchable": col.is_searchable, "visible": col.is_visible,
            "frozen": col.is_frozen, "align": col.align,
            "format": col.format, "render": col.render,
        }

    def _serialize_filter(self, f: FilterDef) -> Dict[str, Any]:
        return {
            "code": f.code, "label": f.label, "label_ar": f.label_ar,
            "type": f.field_type, "field": f.field,
            "operator": f.operator.value, "options": f.options,
            "default": f.default_value, "visible": f.is_visible,
        }

    def export_lists(self, entity_codes: List[str] = None) -> List[Dict[str, Any]]:
        """Export list configs for templates."""
        lists = self._lists.values()
        if entity_codes:
            lists = [l for l in lists if l.entity in entity_codes]
        return [{
            "entity": l.entity, "title": l.title, "title_ar": l.title_ar,
            "columns": len(l.columns), "filters": len(l.filters),
        } for l in lists]
