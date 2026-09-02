"""
EOS Industry Engine — Tourism Pack
Complete tourism industry template with entities, workflows, and accounting mappings.
"""

from typing import Any

# Entity definitions for tourism industry
TOURISM_ENTITIES = {
    "tour_package": {
        "code": "tour_package",
        "name": "Tour Package",
        "name_ar": "باقة سياحية",
        "module": "tourism",
        "fields": [
            {"code": "code", "name": "Code", "name_ar": "الكود", "type": "text", "required": True},
            {"code": "name_en", "name": "Name (EN)", "name_ar": "الاسم (إنجليزي)", "type": "text", "required": True},
            {"code": "name_ar", "name": "Name (AR)", "name_ar": "الاسم (عربي)", "type": "text", "required": True},
            {"code": "destination", "name": "Destination", "name_ar": "الوجهة", "type": "text"},
            {"code": "duration_days", "name": "Duration (Days)", "name_ar": "المدة (أيام)", "type": "integer"},
            {"code": "base_price", "name": "Base Price", "name_ar": "السعر الأساسي", "type": "currency"},
            {"code": "min_pax", "name": "Minimum Pax", "name_ar": "الحد الأدنى", "type": "integer"},
            {"code": "max_pax", "name": "Maximum Pax", "name_ar": "الحد الأقصى", "type": "integer"},
            {"code": "includes", "name": "Includes", "name_ar": "يتضمن", "type": "textarea"},
            {"code": "excludes", "name": "Excludes", "name_ar": "لا يتضمن", "type": "textarea"},
            {"code": "status", "name": "Status", "name_ar": "الحالة", "type": "select", 
             "options": [{"value": "active", "label": "Active"}, {"value": "inactive", "label": "Inactive"}]},
        ]
    },
    "booking": {
        "code": "booking",
        "name": "Booking",
        "name_ar": "حجز",
        "module": "tourism",
        "fields": [
            {"code": "booking_number", "name": "Booking Number", "name_ar": "رقم الحجز", "type": "text", "required": True},
            {"code": "customer_id", "name": "Customer", "name_ar": "العميل", "type": "reference", "ref_entity": "customer"},
            {"code": "tour_package_id", "name": "Tour Package", "name_ar": "الباقة السياحية", "type": "reference", "ref_entity": "tour_package"},
            {"code": "travel_date", "name": "Travel Date", "name_ar": "تاريخ السفر", "type": "date", "required": True},
            {"code": "return_date", "name": "Return Date", "name_ar": "تاريخ العودة", "type": "date"},
            {"code": "pax_count", "name": "Number of Pax", "name_ar": "عدد الأشخاص", "type": "integer"},
            {"code": "total_amount", "name": "Total Amount", "name_ar": "المبلغ الإجمالي", "type": "currency"},
            {"code": "paid_amount", "name": "Paid Amount", "name_ar": "المبلغ المدفوع", "type": "currency"},
            {"code": "status", "name": "Status", "name_ar": "الحالة", "type": "select",
             "options": [{"value": "pending", "label": "Pending"}, {"value": "confirmed", "label": "Confirmed"}, 
                        {"value": "cancelled", "label": "Cancelled"}, {"value": "completed", "label": "Completed"}]},
        ]
    },
    "hotel": {
        "code": "hotel",
        "name": "Hotel",
        "name_ar": "فندق",
        "module": "tourism",
        "fields": [
            {"code": "code", "name": "Code", "name_ar": "الكود", "type": "text"},
            {"code": "name_en", "name": "Name (EN)", "name_ar": "الاسم (إنجليزي)", "type": "text", "required": True},
            {"code": "name_ar", "name": "Name (AR)", "name_ar": "الاسم (عربي)", "type": "text"},
            {"code": "city", "name": "City", "name_ar": "المدينة", "type": "text"},
            {"code": "country", "name": "Country", "name_ar": "الدولة", "type": "text"},
            {"code": "star_rating", "name": "Star Rating", "name_ar": "التصنيف", "type": "select",
             "options": [{"value": "3", "label": "3 Stars"}, {"value": "4", "label": "4 Stars"}, {"value": "5", "label": "5 Stars"}]},
            {"code": "contact_email", "name": "Email", "name_ar": "البريد", "type": "email"},
            {"code": "contact_phone", "name": "Phone", "name_ar": "الهاتف", "type": "phone"},
        ]
    },
    "flight": {
        "code": "flight",
        "name": "Flight",
        "name_ar": "رحلة طيران",
        "module": "tourism",
        "fields": [
            {"code": "flight_number", "name": "Flight Number", "name_ar": "رقم الرحلة", "type": "text"},
            {"code": "airline", "name": "Airline", "name_ar": "الخطوط الجوية", "type": "text"},
            {"code": "departure_airport", "name": "Departure Airport", "name_ar": "مطار المغادرة", "type": "text"},
            {"code": "arrival_airport", "name": "Arrival Airport", "name_ar": "مطار الوصول", "type": "text"},
            {"code": "departure_time", "name": "Departure Time", "name_ar": "وقت المغادرة", "type": "datetime"},
            {"code": "arrival_time", "name": "Arrival Time", "name_ar": "وقت الوصول", "type": "datetime"},
            {"code": "class", "name": "Class", "name_ar": "الدرجة", "type": "select",
             "options": [{"value": "economy", "label": "Economy"}, {"value": "business", "label": "Business"}, {"value": "first", "label": "First"}]},
        ]
    },
    "passenger": {
        "code": "passenger",
        "name": "Passenger",
        "name_ar": "مسافر",
        "module": "tourism",
        "fields": [
            {"code": "first_name", "name": "First Name", "name_ar": "الاسم", "type": "text", "required": True},
            {"code": "last_name", "name": "Last Name", "name_ar": "اللقب", "type": "text", "required": True},
            {"code": "passport_number", "name": "Passport Number", "name_ar": "رقم الجواز", "type": "text"},
            {"code": "passport_expiry", "name": "Passport Expiry", "name_ar": "تاريخ انتهاء الجواز", "type": "date"},
            {"code": "nationality", "name": "Nationality", "name_ar": "الجنسية", "type": "text"},
            {"code": "date_of_birth", "name": "Date of Birth", "name_ar": "تاريخ الميلاد", "type": "date"},
            {"code": "gender", "name": "Gender", "name_ar": "الجنس", "type": "select",
             "options": [{"value": "M", "label": "Male"}, {"value": "F", "label": "Female"}]},
        ]
    },
    "visa": {
        "code": "visa",
        "name": "Visa",
        "name_ar": "تأشيرة",
        "module": "tourism",
        "fields": [
            {"code": "passenger_id", "name": "Passenger", "name_ar": "المسافر", "type": "reference", "ref_entity": "passenger"},
            {"code": "visa_type", "name": "Visa Type", "name_ar": "نوع التأشيرة", "type": "select",
             "options": [{"value": "tourist", "label": "Tourist"}, {"value": "business", "label": "Business"}, 
                        {"value": "umrah", "label": "Umrah"}, {"value": "hajj", "label": "Hajj"}]},
            {"code": "destination_country", "name": "Destination Country", "name_ar": "دولة الوجهة", "type": "text"},
            {"code": "application_date", "name": "Application Date", "name_ar": "تاريخ التقديم", "type": "date"},
            {"code": "status", "name": "Status", "name_ar": "الحالة", "type": "select",
             "options": [{"value": "pending", "label": "Pending"}, {"value": "approved", "label": "Approved"}, 
                        {"value": "rejected", "label": "Rejected"}]},
        ]
    },
    "guide": {
        "code": "guide",
        "name": "Tour Guide",
        "name_ar": "مرشد سياحي",
        "module": "tourism",
        "fields": [
            {"code": "employee_id", "name": "Employee ID", "name_ar": "رقم الموظف", "type": "reference", "ref_entity": "employee"},
            {"code": "languages", "name": "Languages", "name_ar": "اللغات", "type": "multi_select"},
            {"code": "specialization", "name": "Specialization", "name_ar": "التخصص", "type": "text"},
            {"code": "license_number", "name": "License Number", "name_ar": "رقم الترخيص", "type": "text"},
            {"code": "rating", "name": "Rating", "name_ar": "التقييم", "type": "number"},
        ]
    },
    "transfer": {
        "code": "transfer",
        "name": "Transfer",
        "name_ar": "انتقال",
        "module": "tourism",
        "fields": [
            {"code": "booking_id", "name": "Booking", "name_ar": "الحجز", "type": "reference", "ref_entity": "booking"},
            {"code": "pickup_location", "name": "Pickup Location", "name_ar": "مكان الاستلام", "type": "text"},
            {"code": "dropoff_location", "name": "Dropoff Location", "name_ar": "مكان التوصيل", "type": "text"},
            {"code": "pickup_time", "name": "Pickup Time", "name_ar": "وقت الاستلام", "type": "datetime"},
            {"code": "vehicle_type", "name": "Vehicle Type", "name_ar": "نوع السيارة", "type": "select"},
            {"code": "driver_name", "name": "Driver Name", "name_ar": "اسم السائق", "type": "text"},
            {"code": "status", "name": "Status", "name_ar": "الحالة", "type": "select",
             "options": [{"value": "scheduled", "label": "Scheduled"}, {"value": "completed", "label": "Completed"}, 
                        {"value": "cancelled", "label": "Cancelled"}]},
        ]
    },
}

# Tourism workflows
TOURISM_WORKFLOWS = [
    {
        "name": "Booking Confirmation",
        "trigger": "booking_created",
        "steps": ["sales_agent", "operations_manager"],
    },
    {
        "name": "Visa Application Approval",
        "trigger": "visa_submitted",
        "steps": ["visa_officer", "operations_manager"],
    },
    {
        "name": "Tour Package Approval",
        "trigger": "tour_package_created",
        "steps": ["product_manager", "finance_manager"],
    },
]

# Tourism accounting mappings
TOURISM_ACCOUNTING = {
    "mappings": [
        {
            "code": "BOOKING_PAYMENT",
            "event": "booking_payment_received",
            "debit_account": "1100",  # Cash/Bank
            "credit_account": "4100",  # Tourism Revenue
            "description": "Booking payment {booking_number}",
        },
        {
            "code": "SUPPLIER_PAYMENT",
            "event": "hotel_supplier_payment",
            "debit_account": "5100",  # Hotel Cost
            "credit_account": "2100",  # Accounts Payable
            "description": "Hotel payment {hotel_name}",
        },
        {
            "code": "COMMISSION_INCOME",
            "event": "commission_received",
            "debit_account": "1100",  # Cash/Bank
            "credit_account": "4200",  # Commission Income
            "description": "Commission from {supplier}",
        },
    ],
    "account_patterns": {
        "tourism_revenue": "4100",
        "hotel_cost": "5100",
        "flight_cost": "5110",
        "commission_income": "4200",
        "visa_fees": "5120",
    }
}

# Tourism KPIs
TOURISM_KPIS = [
    {"name": "Total Bookings", "metric": "booking_count", "aggregation": "COUNT"},
    {"name": "Booking Value", "metric": "booking_value", "aggregation": "SUM"},
    {"name": "Occupancy Rate", "metric": "occupancy_rate", "aggregation": "AVG"},
    {"name": "Revenue per Pax", "metric": "revenue_per_pax", "aggregation": "AVG"},
    {"name": "Visa Success Rate", "metric": "visa_approval_rate", "aggregation": "PERCENTAGE"},
]

def get_tourism_pack() -> dict[str, Any]:
    """Return complete tourism industry pack."""
    return {
        "industry": "tourism",
        "entities": TOURISM_ENTITIES,
        "workflows": TOURISM_WORKFLOWS,
        "accounting": TOURISM_ACCOUNTING,
        "kpis": TOURISM_KPIS,
    }
