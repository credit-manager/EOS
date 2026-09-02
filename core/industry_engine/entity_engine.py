"""
EOS Industry Engine — Entity/Metadata Engine
Defines entities, fields, and relationships per industry.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
    min_value: float | None = None
    max_value: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    custom_rule: str | None = None  # Name of custom validation rule


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
    options: list[dict[str, str]] = field(default_factory=list)  # For SELECT
    reference_entity: str | None = None  # For REFERENCE type
    formula: str | None = None           # For FORMULA type
    validation: FieldValidation = field(default_factory=FieldValidation)
    is_visible: bool = True
    is_editable: bool = True
    is_searchable: bool = False
    is_filterable: bool = False
    is_sortable: bool = False
    display_order: int = 0
    group: str = "general"
    width: int | None = None  # Column width in pixels


@dataclass
class EntityRelationship:
    name: str
    type: str  # one_to_one, one_to_many, many_to_many
    target_entity: str
    foreign_key: str | None = None
    join_table: str | None = None


@dataclass
class EntityDefinition:
    code: str
    name: str
    name_ar: str
    description: str = ""
    icon: str = "AppstoreOutlined"
    module: str = ""  # Which module this entity belongs to
    fields: list[FieldDefinition] = field(default_factory=list)
    relationships: list[EntityRelationship] = field(default_factory=list)
    is_core: bool = False  # Core entities can't be deleted
    is_searchable: bool = True
    default_view: str = "list"  # list, grid, kanban, calendar
    default_sort: str = "-created_at"
    page_size: int = 20
    permissions: dict[str, str] = field(default_factory=dict)  # action -> permission code
    actions: list[dict[str, Any]] = field(default_factory=list)  # Custom actions


class EntityEngine:
    """
    Manages entity definitions per industry.
    Each industry template registers its entities with this engine.
    """

    def __init__(self):
        self._entities: dict[str, EntityDefinition] = {}
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
            # Tourism Entities
            EntityDefinition(
                code="tour_package", name="Tour Package", name_ar="باقة سياحية",
                module="tourism", icon="CloudOutlined",
                fields=[
                    FieldDefinition("code", "Code", "الكود", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("name", "Name", "الاسم", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("description", "Description", "الوصف", FieldType.TEXTAREA, display_order=3),
                    FieldDefinition("destination", "Destination", "الوجهة", FieldType.TEXT, is_searchable=True, display_order=4),
                    FieldDefinition("duration_days", "Duration (Days)", "المدة (أيام)", FieldType.INTEGER, display_order=5),
                    FieldDefinition("price", "Price", "السعر", FieldType.CURRENCY, display_order=6),
                    FieldDefinition("currency", "Currency", "العملة", FieldType.SELECT, options=[{"value": "USD", "label": "USD"}, {"value": "EUR", "label": "EUR"}, {"value": "SAR", "label": "SAR"}, {"value": "EGP", "label": "EGP"}], display_order=7),
                    FieldDefinition("includes", "Includes", "يتضمن", FieldType.TEXTAREA, display_order=8),
                    FieldDefinition("is_active", "Active", "نشط", FieldType.BOOLEAN, default_value=True, display_order=9),
                ],
            ),
            EntityDefinition(
                code="booking", name="Booking", name_ar="حجز",
                module="tourism", icon="BookOutlined",
                fields=[
                    FieldDefinition("booking_number", "Booking Number", "رقم الحجز", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("customer_id", "Customer", "العميل", FieldType.REFERENCE, reference_entity="customer", validation=FieldValidation(required=True), display_order=2),
                    FieldDefinition("tour_package_id", "Tour Package", "الباقة السياحية", FieldType.REFERENCE, reference_entity="tour_package", display_order=3),
                    FieldDefinition("booking_date", "Booking Date", "تاريخ الحجز", FieldType.DATE, display_order=4),
                    FieldDefinition("travel_date", "Travel Date", "تاريخ السفر", FieldType.DATE, display_order=5),
                    FieldDefinition("passengers_count", "Passengers", "عدد المسافرين", FieldType.INTEGER, display_order=6),
                    FieldDefinition("total_amount", "Total Amount", "الإجمالي", FieldType.CURRENCY, display_order=7),
                    FieldDefinition("status", "Status", "الحالة", FieldType.SELECT, options=[{"value": "pending", "label": "Pending"}, {"value": "confirmed", "label": "Confirmed"}, {"value": "cancelled", "label": "Cancelled"}, {"value": "completed", "label": "Completed"}], display_order=8),
                    FieldDefinition("payment_status", "Payment Status", "حالة الدفع", FieldType.SELECT, options=[{"value": "unpaid", "label": "Unpaid"}, {"value": "partial", "label": "Partial"}, {"value": "paid", "label": "Paid"}], display_order=9),
                ],
            ),
            EntityDefinition(
                code="hotel", name="Hotel", name_ar="فندق",
                module="tourism", icon="HomeOutlined",
                fields=[
                    FieldDefinition("code", "Code", "الكود", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("name", "Name", "الاسم", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("star_rating", "Star Rating", "التصنيف", FieldType.SELECT, options=[{"value": "3", "label": "3 Stars"}, {"value": "4", "label": "4 Stars"}, {"value": "5", "label": "5 Stars"}], display_order=3),
                    FieldDefinition("location", "Location", "الموقع", FieldType.TEXT, display_order=4),
                    FieldDefinition("contact_email", "Email", "البريد", FieldType.EMAIL, display_order=5),
                    FieldDefinition("contact_phone", "Phone", "الهاتف", FieldType.PHONE, display_order=6),
                    FieldDefinition("room_types", "Room Types", "أنواع الغرف", FieldType.JSON, display_order=7),
                    FieldDefinition("is_contracted", "Contracted", "متعاقدين", FieldType.BOOLEAN, default_value=False, display_order=8),
                ],
            ),
            EntityDefinition(
                code="flight", name="Flight", name_ar="رحلة طيران",
                module="tourism", icon="RocketOutlined",
                fields=[
                    FieldDefinition("flight_number", "Flight Number", "رقم الرحلة", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("airline", "Airline", "الخطوط الجوية", FieldType.TEXT, display_order=2),
                    FieldDefinition("departure_from", "Departure From", "من", FieldType.TEXT, display_order=3),
                    FieldDefinition("arrival_to", "Arrival To", "إلى", FieldType.TEXT, display_order=4),
                    FieldDefinition("departure_time", "Departure Time", "وقت المغادرة", FieldType.DATETIME, display_order=5),
                    FieldDefinition("arrival_time", "Arrival Time", "وقت الوصول", FieldType.DATETIME, display_order=6),
                    FieldDefinition("available_seats", "Available Seats", "المقاعد المتاحة", FieldType.INTEGER, display_order=7),
                    FieldDefinition("class_type", "Class", "الفئة", FieldType.SELECT, options=[{"value": "economy", "label": "Economy"}, {"value": "business", "label": "Business"}, {"value": "first", "label": "First Class"}], display_order=8),
                ],
            ),
            EntityDefinition(
                code="passenger", name="Passenger", name_ar="مسافر",
                module="tourism", icon="UserOutlined",
                fields=[
                    FieldDefinition("passport_number", "Passport Number", "رقم الجواز", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("full_name", "Full Name", "الاسم الكامل", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("nationality", "Nationality", "الجنسية", FieldType.TEXT, display_order=3),
                    FieldDefinition("date_of_birth", "Date of Birth", "تاريخ الميلاد", FieldType.DATE, display_order=4),
                    FieldDefinition("gender", "Gender", "النوع", FieldType.SELECT, options=[{"value": "male", "label": "Male"}, {"value": "female", "label": "Female"}], display_order=5),
                    FieldDefinition("passport_expiry", "Passport Expiry", "انتهاء الجواز", FieldType.DATE, display_order=6),
                    FieldDefinition("phone", "Phone", "الهاتف", FieldType.PHONE, display_order=7),
                    FieldDefinition("email", "Email", "البريد", FieldType.EMAIL, display_order=8),
                ],
            ),
            EntityDefinition(
                code="visa", name="Visa", name_ar="تأشيرة",
                module="tourism", icon="SafetyCertificateOutlined",
                fields=[
                    FieldDefinition("visa_number", "Visa Number", "رقم التأشيرة", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("passenger_id", "Passenger", "المسافر", FieldType.REFERENCE, reference_entity="passenger", validation=FieldValidation(required=True), display_order=2),
                    FieldDefinition("visa_type", "Visa Type", "نوع التأشيرة", FieldType.SELECT, options=[{"value": "tourist", "label": "Tourist"}, {"value": "work", "label": "Work"}, {"value": "umrah", "label": "Umrah"}, {"value": "hajj", "label": "Hajj"}], display_order=3),
                    FieldDefinition("destination_country", "Destination Country", "الدولة", FieldType.TEXT, display_order=4),
                    FieldDefinition("application_date", "Application Date", "تاريخ التقديم", FieldType.DATE, display_order=5),
                    FieldDefinition("issue_date", "Issue Date", "تاريخ الإصدار", FieldType.DATE, display_order=6),
                    FieldDefinition("expiry_date", "Expiry Date", "تاريخ الانتهاء", FieldType.DATE, display_order=7),
                    FieldDefinition("status", "Status", "الحالة", FieldType.SELECT, options=[{"value": "pending", "label": "Pending"}, {"value": "approved", "label": "Approved"}, {"value": "rejected", "label": "Rejected"}, {"value": "expired", "label": "Expired"}], display_order=8),
                ],
            ),
            EntityDefinition(
                code="guide", name="Tour Guide", name_ar="مرشد سياحي",
                module="tourism", icon="UsergroupAddOutlined",
                fields=[
                    FieldDefinition("guide_id", "Guide ID", "رقم المرشد", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("name", "Name", "الاسم", FieldType.TEXT, validation=FieldValidation(required=True), is_searchable=True, display_order=2),
                    FieldDefinition("languages", "Languages", "اللغات", FieldType.MULTI_SELECT, options=[{"value": "arabic", "label": "Arabic"}, {"value": "english", "label": "English"}, {"value": "french", "label": "French"}, {"value": "german", "label": "German"}, {"value": "spanish", "label": "Spanish"}], display_order=3),
                    FieldDefinition("specialization", "Specialization", "التخصص", FieldType.TEXT, display_order=4),
                    FieldDefinition("license_number", "License Number", "رقم الترخيص", FieldType.TEXT, display_order=5),
                    FieldDefinition("phone", "Phone", "الهاتف", FieldType.PHONE, display_order=6),
                    FieldDefinition("daily_rate", "Daily Rate", "الأجر اليومي", FieldType.CURRENCY, display_order=7),
                    FieldDefinition("is_available", "Available", "متاح", FieldType.BOOLEAN, default_value=True, display_order=8),
                ],
            ),
            EntityDefinition(
                code="transfer", name="Transfer", name_ar="انتقال",
                module="tourism", icon="CarOutlined",
                fields=[
                    FieldDefinition("transfer_number", "Transfer Number", "رقم الانتقال", FieldType.TEXT, is_searchable=True, display_order=1),
                    FieldDefinition("booking_id", "Booking", "الحجز", FieldType.REFERENCE, reference_entity="booking", display_order=2),
                    FieldDefinition("transfer_type", "Type", "النوع", FieldType.SELECT, options=[{"value": "airport_pickup", "label": "Airport Pickup"}, {"value": "airport_dropoff", "label": "Airport Dropoff"}, {"value": "hotel_transfer", "label": "Hotel Transfer"}, {"value": "excursion", "label": "Excursion"}], display_order=3),
                    FieldDefinition("pickup_location", "Pickup Location", "مكان الاستقبال", FieldType.TEXT, display_order=4),
                    FieldDefinition("dropoff_location", "Dropoff Location", "مكان التوصيل", FieldType.TEXT, display_order=5),
                    FieldDefinition("pickup_time", "Pickup Time", "وقت الاستقبال", FieldType.DATETIME, display_order=6),
                    FieldDefinition("vehicle_type", "Vehicle Type", "نوع السيارة", FieldType.TEXT, display_order=7),
                    FieldDefinition("driver_name", "Driver Name", "اسم السائق", FieldType.TEXT, display_order=8),
                    FieldDefinition("status", "Status", "الحالة", FieldType.SELECT, options=[{"value": "scheduled", "label": "Scheduled"}, {"value": "in_progress", "label": "In Progress"}, {"value": "completed", "label": "Completed"}, {"value": "cancelled", "label": "Cancelled"}], display_order=9),
                ],
            ),
        ]

        for entity in core_entities:
            self._entities[entity.code] = entity

    def register(self, entity: EntityDefinition):
        """Register a new entity."""
        self._entities[entity.code] = entity

    def get(self, code: str) -> EntityDefinition | None:
        """Get entity definition by code."""
        return self._entities.get(code)

    def get_all(self) -> dict[str, EntityDefinition]:
        """Get all registered entities."""
        return dict(self._entities)

    def get_by_module(self, module_code: str) -> list[EntityDefinition]:
        """Get entities for a specific module."""
        return [e for e in self._entities.values() if e.module == module_code]

    def get_fields(self, entity_code: str) -> list[FieldDefinition]:
        """Get fields for an entity, sorted by display_order."""
        entity = self._entities.get(entity_code)
        if not entity:
            return []
        return sorted(entity.fields, key=lambda f: f.display_order)

    def get_searchable_fields(self, entity_code: str) -> list[FieldDefinition]:
        """Get searchable fields for an entity."""
        return [f for f in self.get_fields(entity_code) if f.is_searchable]

    def get_filterable_fields(self, entity_code: str) -> list[FieldDefinition]:
        """Get filterable fields for an entity."""
        return [f for f in self.get_fields(entity_code) if f.is_filterable]

    def validate_entity_data(self, entity_code: str, data: dict[str, Any]) -> list[str]:
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

    def build_entity_schema(self, entity_code: str) -> dict[str, Any]:
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
