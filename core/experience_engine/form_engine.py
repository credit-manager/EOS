"""
EOS Experience Engine — Form Engine
Dynamic form generation from entity definitions.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class FormLayout(str, Enum):
    SINGLE_COLUMN = "single"
    TWO_COLUMN = "two_column"
    THREE_COLUMN = "three_column"
    STEPPER = "stepper"
    TABS = "tabs"


class SectionType(str, Enum):
    GROUP = "group"
    COLLAPSIBLE = "collapsible"
    TAB = "tab"
    DIVIDER = "divider"


@dataclass
class FormFieldConfig:
    """Extended field config for forms."""
    code: str
    label: str
    label_ar: str
    field_type: str  # maps to FieldType
    required: bool = False
    placeholder: str = ""
    placeholder_ar: str = ""
    help_text: str = ""
    help_text_ar: str = ""
    default_value: Any = None
    options: List[Dict[str, str]] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=dict)
    depends_on: str = ""  # Field this depends on
    visible_when: Dict[str, Any] = field(default_factory=dict)  # Conditional visibility
    editable_when: Dict[str, Any] = field(default_factory=dict)  # Conditional editability
    formula: str = ""  # Calculated field formula
    width: str = "full"  # full, half, third
    group: str = "general"
    icon: str = ""
    prefix: str = ""
    suffix: str = ""


@dataclass
class FormSection:
    code: str
    title: str
    title_ar: str
    section_type: SectionType = SectionType.GROUP
    fields: List[FormFieldConfig] = field(default_factory=list)
    columns: int = 2
    is_collapsed: bool = False
    depends_on: str = ""
    visible_when: Dict[str, Any] = field(default_factory=dict)
    order: int = 0


@dataclass
class FormAction:
    code: str
    label: str
    label_ar: str
    action_type: str  # submit, cancel, draft, print, custom
    icon: str = ""
    color: str = ""
    confirmation: str = ""
    confirmation_ar: str = ""
    url: str = ""


@dataclass
class FormDefinition:
    code: str
    name: str
    name_ar: str
    entity: str
    layout: FormLayout = FormLayout.SINGLE_COLUMN
    sections: List[FormSection] = field(default_factory=list)
    actions: List[FormAction] = field(default_factory=list)
    title_field: str = ""  # Field to use as form title
    subtitle_field: str = ""
    readonly: bool = False
    autosave: bool = False
    validation_mode: str = "on_submit"  # on_submit, on_change
    submit_url: str = ""
    success_message: str = ""
    success_message_ar: str = ""


class FormEngine:
    """
    Generates forms from entity definitions and form configs.
    Each industry can override forms for its entities.
    """

    def __init__(self):
        self._forms: Dict[str, FormDefinition] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Register core forms."""
        # Generic CRUD form
        self.register(FormDefinition(
            code="generic_create", name="Create Record", name_ar="إنشاء سجل",
            entity="*",
            sections=[FormSection("general", "General", "عام", fields=[], order=0)],
            actions=[
                FormAction("submit", "Save", "حفظ", "submit", icon="SaveOutlined", color="#1890ff"),
                FormAction("cancel", "Cancel", "إلغاء", "cancel", icon="CloseOutlined"),
            ],
            autosave=True,
            success_message="Record saved successfully",
            success_message_ar="تم الحفظ بنجاح",
        ))

        # Purchase Order Form
        self.register(FormDefinition(
            code="purchase_order_form", name="Purchase Order", name_ar="أمر شراء",
            entity="purchase_order",
            layout=FormLayout.TWO_COLUMN,
            sections=[
                FormSection("header", "Order Details", "تفاصيل الأمر", fields=[
                    FormFieldConfig("po_number", "PO Number", "رقم الأمر", "text", required=True, width="half"),
                    FormFieldConfig("po_date", "Date", "التاريخ", "date", required=True, width="half"),
                    FormFieldConfig("supplier", "Supplier", "المورد", "reference", required=True, width="half",
                                   depends_on=""),
                    FormFieldConfig("payment_terms", "Payment Terms", "شروط الدفع", "select", width="half",
                                   options=[{"value": "net30", "label": "Net 30"}, {"value": "net60", "label": "Net 60"}]),
                    FormFieldConfig("delivery_date", "Delivery Date", "تاريخ التسليم", "date", width="half"),
                    FormFieldConfig("delivery_address", "Delivery Address", "عنوان التسليم", "textarea", width="half"),
                    FormFieldConfig("notes", "Notes", "ملاحظات", "textarea", width="full"),
                ], order=0),
                FormSection("items", "Items", "الأصناف", fields=[], order=1),
                FormSection("totals", "Totals", "الإجماليات", fields=[
                    FormFieldConfig("subtotal", "Subtotal", "المجموع", "currency", width="third"),
                    FormFieldConfig("discount", "Discount", "الخصم", "currency", width="third"),
                    FormFieldConfig("tax", "Tax", "الضريبة", "currency", width="third"),
                    FormFieldConfig("total", "Total", "الإجمالي", "currency", width="third"),
                ], order=2),
            ],
            actions=[
                FormAction("submit", "Submit for Approval", "تقديم للموافقة", "submit", icon="SendOutlined", color="#1890ff"),
                FormAction("draft", "Save as Draft", "حفظ كمسودة", "custom", icon="SaveOutlined"),
                FormAction("cancel", "Cancel", "إلغاء", "cancel", icon="CloseOutlined"),
            ],
        ))

        # Project Form
        self.register(FormDefinition(
            code="project_form", name="Project", name_ar="مشروع",
            entity="project",
            layout=FormLayout.TWO_COLUMN,
            sections=[
                FormSection("basic", "Project Info", "بيانات المشروع", fields=[
                    FormFieldConfig("code", "Project Code", "كود المشروع", "text", required=True, width="half"),
                    FormFieldConfig("name", "Project Name", "اسم المشروع", "text", required=True, width="half"),
                    FormFieldConfig("client", "Client", "العميل", "reference", required=True, width="half"),
                    FormFieldConfig("contract_type", "Contract Type", "نوع العقد", "select", width="half",
                                   options=[{"value": "lump_sum", "label": "Lump Sum"},
                                          {"value": "cost_plus", "label": "Cost Plus"},
                                          {"value": "unit_price", "label": "Unit Price"}]),
                    FormFieldConfig("start_date", "Start Date", "تاريخ البداية", "date", required=True, width="half"),
                    FormFieldConfig("end_date", "End Date", "تاريخ النهاية", "date", width="half"),
                    FormFieldConfig("budget", "Budget", "الميزانية", "currency", required=True, width="half"),
                    FormFieldConfig("description", "Description", "الوصف", "textarea", width="full"),
                ], order=0),
                FormSection("location", "Location", "الموقع", fields=[
                    FormFieldConfig("address", "Address", "العنوان", "textarea", width="full"),
                    FormFieldConfig("city", "City", "المدينة", "text", width="half"),
                    FormFieldConfig("country", "Country", "الدولة", "text", width="half"),
                ], order=1),
            ],
            actions=[
                FormAction("submit", "Create Project", "إنشاء مشروع", "submit", icon="PlusOutlined", color="#52c41a"),
                FormAction("cancel", "Cancel", "إلغاء", "cancel", icon="CloseOutlined"),
            ],
        ))

        # BOQ Item Form
        self.register(FormDefinition(
            code="boq_item_form", name="BOQ Item", name_ar="بند جدول الكميات",
            entity="boq_item",
            layout=FormLayout.SINGLE_COLUMN,
            sections=[
                FormSection("details", "Item Details", "تفاصيل البند", fields=[
                    FormFieldConfig("item_number", "Item No.", "رقم البند", "text", required=True, width="third"),
                    FormFieldConfig("description", "Description", "الوصف", "textarea", required=True, width="full"),
                    FormFieldConfig("unit", "Unit", "الوحدة", "select", required=True, width="third",
                                   options=[{"value": "m3", "label": "m³"}, {"value": "m2", "label": "m²"},
                                          {"value": "m", "label": "m"}, {"value": "kg", "label": "Kg"},
                                          {"value": "ea", "label": "Each"}, {"value": "ls", "label": "L.S."}]),
                    FormFieldConfig("quantity", "Quantity", "الكمية", "decimal", required=True, width="third"),
                    FormFieldConfig("unit_price", "Unit Price", "سعر الوحدة", "currency", required=True, width="third"),
                    FormFieldConfig("amount", "Amount", "المبلغ", "currency", formula="quantity * unit_price", width="third"),
                ], order=0),
            ],
            actions=[
                FormAction("submit", "Save", "حفظ", "submit", icon="SaveOutlined", color="#1890ff"),
                FormAction("cancel", "Cancel", "إلغاء", "cancel", icon="CloseOutlined"),
            ],
        ))

    def register(self, form: FormDefinition):
        """Register a form definition."""
        self._forms[form.code] = form

    def get(self, code: str) -> Optional[FormDefinition]:
        """Get form by code."""
        return self._forms.get(code)

    def get_for_entity(self, entity_code: str) -> Optional[FormDefinition]:
        """Get form for an entity."""
        for form in self._forms.values():
            if form.entity == entity_code:
                return form
        return self._forms.get("generic_create")

    def get_all(self) -> Dict[str, FormDefinition]:
        return dict(self._forms)

    def generate_form(self, form_code: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate complete form JSON for frontend rendering.
        """
        form = self._forms.get(form_code)
        if not form:
            return {"error": f"Form '{form_code}' not found"}

        return {
            "code": form.code,
            "name": form.name,
            "name_ar": form.name_ar,
            "entity": form.entity,
            "layout": form.layout.value,
            "readonly": form.readonly,
            "autosave": form.autosave,
            "validation_mode": form.validation_mode,
            "sections": [self._serialize_section(s, data or {}) for s in
                        sorted(form.sections, key=lambda s: s.order)],
            "actions": [self._serialize_action(a) for a in form.actions],
            "data": data or {},
        }

    def generate_from_entity(self, entity_code: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate form from entity definition (auto-generate sections/fields)."""
        # This would use the Entity Engine to auto-generate forms
        # For now, return a basic structure
        return {
            "code": f"{entity_code}_form",
            "name": entity_code.replace("_", " ").title(),
            "entity": entity_code,
            "layout": "single",
            "sections": [{
                "code": "general",
                "title": "General",
                "title_ar": "عام",
                "fields": [],  # Would be populated from Entity Engine
            }],
            "data": data or {},
        }

    def validate_form(self, form_code: str, data: Dict[str, Any]) -> List[str]:
        """Validate form data against form definition."""
        form = self._forms.get(form_code)
        if not form:
            return [f"Form '{form_code}' not found"]

        errors = []
        for section in form.sections:
            for field in section.fields:
                value = data.get(field.code)
                if field.required and (value is None or value == ""):
                    errors.append(f"{field.label_ar} ({field.label}) is required")
                if field.validation:
                    # Type-specific validation
                    if field.field_type == "decimal" or field.field_type == "currency":
                        if value is not None:
                            try:
                                float(value)
                            except (ValueError, TypeError):
                                errors.append(f"{field.label} must be a number")

        return errors

    def calculate_fields(self, form_code: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate formula fields."""
        form = self._forms.get(form_code)
        if not form:
            return {}

        results = {}
        for section in form.sections:
            for field in section.fields:
                if field.formula:
                    try:
                        # Simple formula evaluation
                        result = self._eval_formula(field.formula, data)
                        results[field.code] = result
                    except Exception:
                        results[field.code] = 0

        return results

    def _eval_formula(self, formula: str, data: Dict[str, Any]) -> Any:
        """Simple formula evaluation."""
        # Replace field references with values
        expr = formula
        for key, value in data.items():
            if isinstance(value, (int, float)):
                expr = expr.replace(key, str(value))
        try:
            return eval(expr)  # Simple eval for basic formulas
        except Exception:
            return 0

    def _serialize_section(self, section: FormSection, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "code": section.code,
            "title": section.title,
            "title_ar": section.title_ar,
            "type": section.section_type.value,
            "columns": section.columns,
            "is_collapsed": section.is_collapsed,
            "fields": [self._serialize_field(f, data) for f in section.fields],
        }

    def _serialize_field(self, field: FormFieldConfig, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "code": field.code,
            "label": field.label,
            "label_ar": field.label_ar,
            "type": field.field_type,
            "required": field.required,
            "placeholder": field.placeholder_ar or field.placeholder,
            "help_text": field.help_text_ar or field.help_text,
            "value": data.get(field.code, field.default_value),
            "options": field.options,
            "validation": field.validation,
            "depends_on": field.depends_on,
            "visible_when": field.visible_when,
            "editable_when": field.editable_when,
            "formula": field.formula,
            "width": field.width,
            "icon": field.icon,
            "prefix": field.prefix,
            "suffix": field.suffix,
        }

    def _serialize_action(self, action: FormAction) -> Dict[str, Any]:
        return {
            "code": action.code,
            "label": action.label_ar or action.label,
            "label_en": action.label,
            "type": action.action_type,
            "icon": action.icon,
            "color": action.color,
            "confirmation": action.confirmation_ar or action.confirmation,
        }

    def export_forms(self, entity_codes: List[str] = None) -> List[Dict[str, Any]]:
        """Export forms for templates."""
        forms = self._forms.values()
        if entity_codes:
            forms = [f for f in forms if f.entity in entity_codes or f.entity == "*"]
        return [{
            "code": f.code, "name": f.name, "name_ar": f.name_ar,
            "entity": f.entity, "layout": f.layout.value,
        } for f in forms]
