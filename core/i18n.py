"""
EOS Internationalization Engine — P64
Arabic/English + RTL + Locale-aware formatting.

Usage:
    from core.i18n import t, get_locale, set_locale, format_date, format_number, format_currency

    # In API endpoints:
    msg = t("errors.not_found", locale="ar")
    # → "العثور على العنصر"

    # Formatting:
    format_date(datetime.now(), locale="ar")  # → "٢٦ أغسطس ٢٠٢٦"
    format_number(1250000, locale="ar")       # → "١٬٢٥٠٬٠٠٠"
    format_currency(1250000, "SAR", locale="ar")  # → "١٬٢٥٠٬٠٠٠٫٥٠ ر.س"
"""

import json
import os
from contextvars import ContextVar
from datetime import datetime
from decimal import Decimal
from typing import Any

# ═══════════════════════════════════════════════
# Context Variables
# ═══════════════════════════════════════════════

_locale_var: ContextVar[str] = ContextVar("locale", default="en")

# ═══════════════════════════════════════════════
# Translation Data
# ═══════════════════════════════════════════════

_translations: dict[str, dict] = {}

SUPPORTED_LOCALES = ["en", "ar"]
DEFAULT_LOCALE = "en"

# RTL locales
RTL_LOCALES = ["ar", "he", "fa", "ur"]


def _load_translations():
    """Load translation files from locales/ directory."""
    global _translations
    locales_dir = os.path.join(os.path.dirname(__file__), "..", "locales")

    for locale in SUPPORTED_LOCALES:
        filepath = os.path.join(locales_dir, f"{locale}.json")
        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8") as f:
                _translations[locale] = json.load(f)
        else:
            _translations[locale] = {}


# Load on import
_load_translations()


# ═══════════════════════════════════════════════
# Translation Function
# ═══════════════════════════════════════════════

def t(key: str, locale: str | None = None, **kwargs) -> str:
    """
    Translate a key to the target locale.

    Args:
        dot-separated key, e.g. "errors.not_found" or "business.invoice"
        locale: target locale (default: current context locale)
        **kwargs: format arguments for string interpolation

    Returns:
        Translated string, or key itself if not found.

    Examples:
        t("errors.not_found", locale="ar")
        t("ui.welcome", locale="en", name="Ahmed")
    """
    if locale is None:
        locale = get_locale()

    translations = _translations.get(locale, {})

    # Navigate dot-separated path
    parts = key.split(".")
    result = translations
    for part in parts:
        if isinstance(result, dict):
            result = result.get(part)
        else:
            result = None
            break

    if result is None:
        # Fallback to English
        if locale != "en":
            return t(key, locale="en", **kwargs)
        return key

    # String interpolation
    if kwargs and isinstance(result, str):
        try:
            result = result.format(**kwargs)
        except (KeyError, IndexError):
            pass

    return result


def get_locale() -> str:
    """Get current locale from context."""
    return _locale_var.get(DEFAULT_LOCALE)


def set_locale(locale: str):
    """Set locale for current context."""
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE
    _locale_var.set(locale)


def is_rtl(locale: str | None = None) -> bool:
    """Check if locale is right-to-left."""
    if locale is None:
        locale = get_locale()
    return locale in RTL_LOCALES


def get_direction(locale: str | None = None) -> str:
    """Get text direction for locale."""
    return "rtl" if is_rtl(locale) else "ltr"


# ═══════════════════════════════════════════════
# Formatting — Dates
# ═══════════════════════════════════════════════

# Arabic month names
_AR_MONTHS = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
    5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
    9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
}

_AR_DAYS = {
    0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء",
    3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد"
}

_EN_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

# Arabic-Indic digits
_ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _to_arabic_digits(text: str) -> str:
    """Convert Western digits to Arabic-Indic."""
    return text.translate(_ARABIC_DIGITS)


def format_date(dt: datetime, locale: str | None = None, fmt: str | None = None) -> str:
    """
    Format date for locale.

    Arabic: ٢٦ أغسطس ٢٠٢٦
    English: August 26, 2026
    """
    if locale is None:
        locale = get_locale()

    if dt is None:
        return ""

    if locale == "ar":
        if fmt == "short":
            return _to_arabic_digits(f"{dt.day}/{dt.month}/{dt.year}")
        month = _AR_MONTHS.get(dt.month, "")
        return _to_arabic_digits(f"{dt.day} {month} {dt.year}")
    else:
        if fmt == "short":
            return f"{dt.month}/{dt.day}/{dt.year}"
        month = _EN_MONTHS.get(dt.month, "")
        return f"{month} {dt.day}, {dt.year}"


def format_datetime(dt: datetime, locale: str | None = None) -> str:
    """Format datetime for locale."""
    if locale is None:
        locale = get_locale()
    if dt is None:
        return ""
    date_part = format_date(dt, locale)
    time_part = f"{dt.hour:02d}:{dt.minute:02d}"
    if locale == "ar":
        return _to_arabic_digits(f"{date_part} {time_part}")
    return f"{date_part} {time_part}"


# ═══════════════════════════════════════════════
# Formatting — Numbers
# ═══════════════════════════════════════════════

def format_number(value, locale: str | None = None, decimals: int = 0) -> str:
    """
    Format number for locale.

    Arabic: ١٬٢٥٠٬٠٠٠
    English: 1,250,000
    """
    if locale is None:
        locale = get_locale()

    if value is None:
        return ""

    if isinstance(value, (int, float, Decimal)):
        if decimals > 0:
            num = f"{value:,.{decimals}f}"
        else:
            num = f"{int(round(value)):,}"
    else:
        num = str(value)

    if locale == "ar":
        # Replace Western separators with Arabic
        num = num.replace(",", "٬").replace(".", "٫")
        num = _to_arabic_digits(num)
    return num


# ═══════════════════════════════════════════════
# Formatting — Currency
# ═══════════════════════════════════════════════

_CURRENCY_SYMBOLS = {
    "SAR": {"ar": "ر.س", "en": "SAR"},
    "USD": {"ar": "دولار", "en": "$"},
    "EUR": {"ar": "يورو", "en": "€"},
    "GBP": {"ar": "جنيه", "en": "£"},
    "AED": {"ar": "د.إ", "en": "AED"},
    "EGP": {"ar": "ج.م", "en": "E£"},
    "KWD": {"ar": "د.ك", "en": "KWD"},
    "QAR": {"ar": "ر.ق", "en": "QAR"},
    "BHD": {"ar": "د.ب", "en": "BD"},
    "OMR": {"ar": "ر.ع", "en": "OMR"},
}


def format_currency(value, currency: str = "SAR", locale: str | None = None, decimals: int = 2) -> str:
    """
    Format currency for locale.

    Arabic: ١٬٢٥٠٬٠٠٠٫٥٠ ر.س
    English: SAR 1,250,000.50
    """
    if locale is None:
        locale = get_locale()

    if value is None:
        return ""

    num_part = format_number(value, locale, decimals)
    symbols = _CURRENCY_SYMBOLS.get(currency, {"ar": currency, "en": currency})
    symbol = symbols.get(locale, currency)

    if locale == "ar":
        return f"{num_part} {symbol}"
    else:
        return f"{symbol} {num_part}"


# ═══════════════════════════════════════════════
# Business Terminology
# ═══════════════════════════════════════════════

BUSINESS_TERMS = {
    # Core ERP
    "customer": {"ar": "العميل", "en": "Customer"},
    "supplier": {"ar": "المورد", "en": "Supplier"},
    "invoice": {"ar": "الفاتورة", "en": "Invoice"},
    "purchase": {"ar": "المشتريات", "en": "Purchase"},
    "sales": {"ar": "المبيعات", "en": "Sales"},
    "project": {"ar": "المشروع", "en": "Project"},
    "warehouse": {"ar": "المخزن", "en": "Warehouse"},
    "employee": {"ar": "الموظف", "en": "Employee"},
    "account": {"ar": "الحساب", "en": "Account"},
    "journal": {"ar": "دفتر اليومية", "en": "Journal"},
    "ledger": {"ar": "دفتر الأستاذ", "en": "Ledger"},
    "payment": {"ar": "الدفعة", "en": "Payment"},
    "receipt": {"ar": "الإيصال", "en": "Receipt"},
    "quotation": {"ar": "عرض السعر", "en": "Quotation"},
    "delivery": {"ar": "التوصيل", "en": "Delivery"},
    "return": {"ar": "المرتجع", "en": "Return"},
    "stock": {"ar": "المخزون", "en": "Stock"},
    "inventory": {"ar": "جرد المخزون", "en": "Inventory"},
    "expense": {"ar": "المصروف", "en": "Expense"},
    "revenue": {"ar": "الإيراد", "en": "Revenue"},
    "profit": {"ar": "الربح", "en": "Profit"},
    "loss": {"ar": "الخسارة", "en": "Loss"},
    "tax": {"ar": "الضريبة", "en": "Tax"},
    "discount": {"ar": "الخصم", "en": "Discount"},
    "total": {"ar": "الإجمالي", "en": "Total"},
    "subtotal": {"ar": "المجموع الفرعي", "en": "Subtotal"},
    "balance": {"ar": "الرصيد", "en": "Balance"},
    "debit": {"ar": "الدين", "en": "Debit"},
    "credit": {"ar": "الائتمان", "en": "Credit"},
    "asset": {"ar": "الأصل", "en": "Asset"},
    "liability": {"ar": "الالتزام", "en": "Liability"},
    "equity": {"ar": "حقوق الملكية", "en": "Equity"},
    "bank": {"ar": "البنك", "en": "Bank"},
    "cash": {"ar": "النقد", "en": "Cash"},
    "payroll": {"ar": "الرواتب", "en": "Payroll"},
    "hr": {"ar": "الموارد البشرية", "en": "Human Resources"},
    "contract": {"ar": "العقد", "en": "Contract"},
    "order": {"ar": "الطلب", "en": "Order"},
    "item": {"ar": "العنصر", "en": "Item"},
    "product": {"ar": "المنتج", "en": "Product"},
    "service": {"ar": "الخدمة", "en": "Service"},
    "report": {"ar": "التقرير", "en": "Report"},
    "dashboard": {"ar": "لوحة التحكم", "en": "Dashboard"},
    "settings": {"ar": "الإعدادات", "en": "Settings"},
    "users": {"ar": "المستخدمين", "en": "Users"},
    "roles": {"ar": "الأدوار", "en": "Roles"},
    "permissions": {"ar": "الصلاحيات", "en": "Permissions"},
    "audit": {"ar": "سجل المراجعة", "en": "Audit Log"},
    "backup": {"ar": "النسخ الاحتياطي", "en": "Backup"},
    "subscription": {"ar": "الاشتراك", "en": "Subscription"},
    "plan": {"ar": "الخطة", "en": "Plan"},
    "marketplace": {"ar": "السوق", "en": "Marketplace"},
    "template": {"ar": "القالب", "en": "Template"},
    "workflow": {"ar": "سير العمل", "en": "Workflow"},
    "notification": {"ar": "الإشعار", "en": "Notification"},
    "company": {"ar": "الشركة", "en": "Company"},
    "branch": {"ar": "الفرع", "en": "Branch"},
    "department": {"ar": "القسم", "en": "Department"},
    "cost_center": {"ar": "مركز التكلفة", "en": "Cost Center"},
}


def get_business_term(term: str, locale: str | None = None) -> str:
    """Get business term translation."""
    if locale is None:
        locale = get_locale()
    terms = BUSINESS_TERMS.get(term, {})
    return terms.get(locale, term)


# ═══════════════════════════════════════════════
# Locale Helper for API
# ═══════════════════════════════════════════════

def detect_locale(accept_language: str | None = None, user_preference: str | None = None) -> str:
    """
    Detect best locale from:
    1. User preference (highest priority)
    2. Accept-Language header
    3. Default (English)
    """
    if user_preference and user_preference in SUPPORTED_LOCALES:
        return user_preference

    if accept_language:
        # Parse Accept-Language: "ar,en;q=0.9"
        for lang_part in accept_language.split(","):
            lang = lang_part.strip().split(";")[0].strip()[:2]
            if lang in SUPPORTED_LOCALES:
                return lang

    return DEFAULT_LOCALE


def get_locale_info(locale: str | None = None) -> dict[str, Any]:
    """Get full locale information."""
    if locale is None:
        locale = get_locale()
    return {
        "locale": locale,
        "direction": get_direction(locale),
        "is_rtl": is_rtl(locale),
        "language_name": "العربية" if locale == "ar" else "English",
        "supported": SUPPORTED_LOCALES,
    }