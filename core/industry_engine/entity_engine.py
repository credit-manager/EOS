"""
EOS Industry Engine — Entity/Metadata Engine
Defines entities, fields, and relationships per industry.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class FieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    FILE = "file"
    IMAGE = "image"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    RATING = "rating"
    JSON = "json"
    REFERENCE = "reference"  # FK to another entity
    FORMULA = "formula"      # Calculated field


class FieldCategory(str, Enum):
    BASIC = "basic"
    FINANCIAL = "financial"
    DATE_TIME = "date_time"
    RELATION = "relation"
    CUSTOM = "custom"


@dataclass
class FieldValidation:
    required: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    custom_rule: Optional[str] = None  # Name of custom validation rule


@dataclass
class FieldDefinition:
    code: str
    name: str
    name_ar: str
    field_type: FieldType
    category: FieldCategory = FieldCategory.BASIC
    description: str = ""
    placeholder: str = ""
    placeholder_ar: str = ""
    default_value: Any = None
    options: List[Dict[str, str]] = field(default_factory=list)  # For SELECT
    reference_entity: Optional[str] = None  # For REFERENCE type
    formula: Optional[str] = None           # For FORMULA type
    validation: FieldValidation = field(default_factory=FieldValidation)
    is_visible: bool = True
    is_editable: bool = True
    is_searchable: bool = False
    is_filterable: bool = False
    is_sortable: bool = False
    display_order: int = 0
    group: str = "general"
    width: Optional[int] = None  # Column width in pixels


@dataclass
class EntityRelationship:
    name: str
    type: str  # one_to_one, one_to_many, many_to_many
    target_entity: str
    foreign_key: Optional[str] = None
    join_table: Optional[str] = None


@dataclass
class EntityDefinition:
    code: str
    name: str
    name_ar: str
    description: str = ""
    icon: str = "AppstoreOutlined"
    module: str = ""  # Which module this entity belongs to
    fields: List[FieldDefinition] = field(default_factory=list)
    relationships: List[EntityRelationship] = field(default_factory=list)
    is_core: bool = False  # Core entities can't be deleted
    is_searchable: bool = True
    default_view: str = "list"  # list, grid, kanban, calendar
    default_sort: str = "-created_at"
    page_size: int = 20
    permissions: Dict[str, str] = field(default_factory=dict)  # action -> permission code
    actions: List[Dict[str, Any]] = field(default_factory=list)  # Custom actions


class EntityEngine:
    """
    Manages entity definitions per industry.
    Each industry template registers its entities with this engine.
    """

    def __init__(self):
        self._entities: Dict[str, EntityDefinition] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register core platform entities."""
        core_entities = [
            EntityDefinition(
                code="account", name="Account", name_ar="حساب",
                module="accounting", icon="AccountBookOutlined", is_core=True,
                fields=[
                    FieldDefinition("code", "Code", "الكود", FieldType.TEXT, validation=FieldValidation(required=True, max_length=20), is_searchable=True, display_order=1),
                    FieldDefinition("name_en", "Name (EN)", "الاسم (إنجليزي)", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("name_ar", "Name (AR)", "الاسم (عربي)", FieldType.TEXT, is_searchable=True, display_order=3),
                    FieldDefinition("account_type", "Type", "النوع", FieldType.SELECT, options=[{"value": "asset", "label": "Asset"}, {"value": "liability", "label": "Liability"}, {"value": "equity", "label": "Equity"}, {"value": "revenue", "label": "Revenue"}, {"value": "expense", "label": "Expense"}], validation=FieldValidation(required=True), display_order=4),
                    FieldDefinition("parent_id", "Parent", "الأب", FieldType.REFERENCE, reference_entity="account", display_order=5),
                    FieldDefinition("is_active", "Active", "نشط", FieldType.BOOLEAN, default_value=True, display_order=6),
                ],
            ),
            EntityDefinition(
                code="journal_entry", name="Journal Entry", name_ar="قيد يومي",
                module="accounting", icon="FileTextOutlined", is_core=True,
                fields=[
                    FieldDefinition("entry_number", "Entry Number", "رقم القيد", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("entry_date", "Date", "التاريخ", FieldType.DATE, validation=FieldValidation(required=True), display_order=2),
                    FieldDefinition("description", "Description", "الوصف", FieldType.TEXTAREA, display_order=3),
                    FieldDefinition("total_debit", "Total Debit", "إجمالي المدين", FieldType.CURRENCY, is_editable=False, display_order=4),
                    FieldDefinition("total_credit", "Total Credit", "إجمالي الدائن", FieldType.CURRENCY, is_editable=False, display_order=5),
                    FieldDefinition("status", "Status", "الحالة", FieldType.SELECT, options=[{"value": "draft", "label": "Draft"}, {"value": "posted", "label": "Posted"}, {"value": "voided", "label": "Voided"}], display_order=6),
                ],
            ),
            EntityDefinition(
                code="customer", name="Customer", name_ar="عميل",
                module="sales", icon="UserOutlined",
                fields=[
                    FieldDefinition("code", "Code", "الكود", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("name", "Name", "الاسم", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("email", "Email", "البريد", FieldType.EMAIL, display_order=3),
                    FieldDefinition("phone", "Phone", "الهاتف", FieldType.PHONE, display_order=4),
                    FieldDefinition("address", "Address", "العنوان", FieldType.TEXTAREA, display_order=5),
                    FieldDefinition("credit_limit", "Credit Limit", "حد الائتمان", FieldType.CURRENCY, display_order=6),
                    FieldDefinition("payment_terms", "Payment Terms", "شروط الدفع", FieldType.SELECT, options=[{"value": "net30", "label": "Net 30"}, {"value": "net60", "label": "Net 60"}, {"value": "cod", "label": "COD"}], display_order=7),
                ],
            ),
            EntityDefinition(
                code="supplier", name="Supplier", name_ar="مورد",
                module="procurement", icon="TeamOutlined",
                fields=[
                    FieldDefinition("code", "Code", "الكود", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("name", "Name", "الاسم", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("email", "Email", "البريد", FieldType.EMAIL, display_order=3),
                    FieldDefinition("phone", "Phone", "الهاتف", FieldType.PHONE, display_order=4),
                    FieldDefinition("address", "Address", "العنوان", FieldType.TEXTAREA, display_order=5),
                    FieldDefinition("payment_terms", "Payment Terms", "شروط الدفع", FieldType.SELECT, options=[{"value": "net30", "label": "Net 30"}, {"value": "net60", "label": "Net 60"}], display_order=6),
                ],
            ),
            EntityDefinition(
                code="employee", name="Employee", name_ar="موظف",
                module="hr", icon="UserOutlined",
                fields=[
                    FieldDefinition("employee_id", "Employee ID", "رقم الموظف", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("first_name", "First Name", "الاسم", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("last_name", "Last Name", "اللقب", FieldType.TEXT, is_searchable=True, display_order=3),
                    FieldDefinition("email", "Email", "البريد", FieldType.EMAIL, display_order=4),
                    FieldDefinition("department", "Department", "القسم", FieldType.SELECT, display_order=5),
                    FieldDefinition("position", "Position", "المنصب", FieldType.TEXT, display_order=6),
                    FieldDefinition("hire_date", "Hire Date", "تاريخ التعيين", FieldType.DATE, display_order=7),
                    FieldDefinition("salary", "Salary", "الراتب", FieldType.CURRENCY, display_order=8),
                ],
            ),
            EntityDefinition(
                code="item", name="Item", name_ar="صنف",
                module="inventory", icon="TagOutlined",
                fields=[
                    FieldDefinition("code", "Code", "الكود", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("name", "Name", "الاسم", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("item_type", "Type", "النوع", FieldType.SELECT, options=[{"value": "product", "label": "Product"}, {"value": "service", "label": "Service"}, {"value": "raw_material", "label": "Raw Material"}, {"value": "consumable", "label": "Consumable"}], display_order=3),
                    FieldDefinition("unit", "Unit", "الوحدة", FieldType.SELECT, options=[{"value": "ea", "label": "Each"}, {"value": "kg", "label": "Kg"}, {"value": "m", "label": "Meter"}, {"value": "sqm", "label": "Sq Meter"}, {"value": "cbm", "label": "Cu Meter"}, {"value": "l", "label": "Liter"}, {"value": "box", "label": "Box"}], display_order=4),
                    FieldDefinition("cost_price", "Cost Price", "سعر التكلفة", FieldType.CURRENCY, display_order=5),
                    FieldDefinition("sell_price", "Sell Price", "سعر البيع", FieldType.CURRENCY, display_order=6),
                    FieldDefinition("min_stock", "Min Stock", "الحد الأدنى", FieldType.DECIMAL, display_order=7),
                    FieldDefinition("is_active", "Active", "نشط", FieldType.BOOLEAN, default_value=True, display_order=8),
                ],
            ),
            EntityDefinition(
                code="warehouse", name="Warehouse", name_ar="مستودع",
                module="inventory", icon="HomeOutlined",
                fields=[
                    FieldDefinition("code", "Code", "الكود", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("name", "Name", "الاسم", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("address", "Address", "العنوان", FieldType.TEXTAREA, display_order=3),
                    FieldDefinition("manager", "Manager", "المدير", FieldType.REFERENCE, reference_entity="employee", display_order=4),
                    FieldDefinition("is_active", "Active", "نشط", FieldType.BOOLEAN, default_value=True, display_order=5),
                ],
            ),
            EntityDefinition(
                code="project", name="Project", name_ar="مشروع",
                module="projects", icon="ProjectOutlined",
                fields=[
                    FieldDefinition("code", "Code", "الكود", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("name", "Name", "الاسم", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("description", "Description", "الوصف", FieldType.TEXTAREA, display_order=3),
                    FieldDefinition("status", "Status", "الحالة", FieldType.SELECT, options=[{"value": "planning", "label": "Planning"}, {"value": "active", "label": "Active"}, {"value": "on_hold", "label": "On Hold"}, {"value": "completed", "label": "Completed"}, {"value": "cancelled", "label": "Cancelled"}], display_order=4),
                    FieldDefinition("start_date", "Start Date", "تاريخ البداية", FieldType.DATE, display_order=5),
                    FieldDefinition("end_date", "End Date", "تاريخ النهاية", FieldType.DATE, display_order=6),
                    FieldDefinition("budget", "Budget", "الميزانية", FieldType.CURRENCY, display_order=7),
                    FieldDefinition("actual_cost", "Actual Cost", "التكلفة الفعلية", FieldType.CURRENCY, is_editable=False, display_order=8),
                    FieldDefinition("progress", "Progress %", "نسبة التقدم", FieldType.PERCENTAGE, display_order=9),
                ],
            ),
        ]

        for entity in core_entities:
            self._entities[entity.code] = entity

    def register(self, entity: EntityDefinition):
        """Register a new entity."""
        self._entities[entity.code] = entity

    def get(self, code: str) -> Optional[EntityDefinition]:
        """Get entity definition by code."""
        return self._entities.get(code)

    def get_all(self) -> Dict[str, EntityDefinition]:
        """Get all registered entities."""
        return dict(self._entities)

    def get_by_module(self, module_code: str) -> List[EntityDefinition]:
        """Get entities for a specific module."""
        return [e for e in self._entities.values() if e.module == module_code]

    def get_fields(self, entity_code: str) -> List[FieldDefinition]:
        """Get fields for an entity, sorted by display_order."""
        entity = self._entities.get(entity_code)
        if not entity:
            return []
        return sorted(entity.fields, key=lambda f: f.display_order)

    def get_searchable_fields(self, entity_code: str) -> List[FieldDefinition]:
        """Get searchable fields for an entity."""
        return [f for f in self.get_fields(entity_code) if f.is_searchable]

    def get_filterable_fields(self, entity_code: str) -> List[FieldDefinition]:
        """Get filterable fields for an entity."""
        return [f for f in self.get_fields(entity_code) if f.is_filterable]

    def validate_entity_data(self, entity_code: str, data: Dict[str, Any]) -> List[str]:
        """Validate data against entity field definitions. Returns list of errors."""
        errors = []
        entity = self._entities.get(entity_code)
        if not entity:
            return [f"Unknown entity: {entity_code}"]

        for field_def in entity.fields:
            value = data.get(field_def.code)

            # Required check
            if field_def.validation.required and (value is None or value == ""):
                errors.append(f"{field_def.name_ar} ({field_def.name}) is required")

            if value is None:
                continue

            # Type-specific validation
            if field_def.field_type == FieldType.INTEGER:
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append(f"{field_def.name} must be an integer")

            elif field_def.field_type == FieldType.DECIMAL:
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append(f"{field_def.name} must be a number")

            elif field_def.field_type == FieldType.CURRENCY:
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append(f"{field_def.name} must be a valid amount")

            # Min/Max validation
            if field_def.validation.min_value is not None:
                try:
                    if float(value) < field_def.validation.min_value:
                        errors.append(f"{field_def.name} must be >= {field_def.validation.min_value}")
                except (ValueError, TypeError):
                    pass

            if field_def.validation.max_value is not None:
                try:
                    if float(value) > field_def.validation.max_value:
                        errors.append(f"{field_def.name} must be <= {field_def.validation.max_value}")
                except (ValueError, TypeError):
                    pass

            # Select validation
            if field_def.field_type == FieldType.SELECT and field_def.options:
                valid_values = [o["value"] for o in field_def.options]
                if value not in valid_values:
                    errors.append(f"{field_def.name} must be one of: {', '.join(valid_values)}")

        return errors

    def build_entity_schema(self, entity_code: str) -> Dict[str, Any]:
        """Build JSON schema for an entity (for forms/validation)."""
        entity = self._entities.get(entity_code)
        if not entity:
            return {}

        properties = {}
        required = []

        for f in entity.fields:
            prop = {"type": f.field_type.value, "title": f.name}
            if f.default_value is not None:
                prop["default"] = f.default_value
            if f.options:
                prop["enum"] = [o["value"] for o in f.options]
            if f.validation.min_length:
                prop["minLength"] = f.validation.min_length
            if f.validation.max_length:
                prop["maxLength"] = f.validation.max_length
            if f.validation.min_value is not None:
                prop["minimum"] = f.validation.min_value
            if f.validation.max_value is not None:
                prop["maximum"] = f.validation.max_value
            properties[f.code] = prop
            if f.validation.required:
                required.append(f.code)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }
