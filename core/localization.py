"""
EOS Localization Engine — Language detection, switching, persistence.
P64.1: Language Engine
P64.2: Translation Dictionary
P64.3: RTL/LTR Middleware
P64.4: Business Terminology
P64.5: Date/Number/Currency Formatting
"""

import os
import re
from typing import Optional
from contextvars import ContextVar

# ═══════════════════════════════════════════════
# Context Variables
# ═══════════════════════════════════════════════

current_lang: ContextVar[str] = ContextVar("current_lang", default="en")
current_direction: ContextVar[str] = ContextVar("current_direction", default="ltr")

# Supported languages
SUPPORTED_LANGUAGES = {"ar", "en"}
DEFAULT_LANGUAGE = "en"

# RTL languages
RTL_LANGUAGES = {"ar", "he", "fa", "ur"}


# ═══════════════════════════════════════════════
# Translation Dictionary (P64.2)
# ═══════════════════════════════════════════════

TRANSLATIONS = {
    # ─────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────
    "nav.home": {"en": "Home", "ar": "الرئيسية"},
    "nav.login": {"en": "Login", "ar": "تسجيل الدخول"},
    "nav.signup": {"en": "Sign Up", "ar": "إنشاء حساب"},
    "nav.dashboard": {"en": "Dashboard", "ar": "لوحة التحكم"},
    "nav.marketplace": {"en": "Marketplace", "ar": "السوق"},
    "nav.settings": {"en": "Settings", "ar": "الإعدادات"},
    "nav.logout": {"en": "Logout", "ar": "تسجيل الخروج"},
    "nav.profile": {"en": "Profile", "ar": "الملف الشخصي"},
    "nav.docs": {"en": "Documentation", "ar": "التوثيق"},

    # ─────────────────────────────────────
    # Landing Page
    # ─────────────────────────────────────
    "landing.title": {"en": "EOS Dynamic Business Platform", "ar": "منصة EOS للأعمال الديناميكية"},
    "landing.subtitle": {"en": "Build, Deploy, and Scale your ERP in minutes", "ar": "ابنِ وانشر ووسّع نظام ERP الخاص بك في دقائق"},
    "landing.cta.start": {"en": "Get Started Free", "ar": "ابدأ مجاناً"},
    "landing.cta.demo": {"en": "See Demo", "ar": "شاهد العرض"},
    "landing.feature1.title": {"en": "AI-Powered ERP", "ar": "ERP بالذكاء الاصطناعي"},
    "landing.feature1.desc": {"en": "Describe your business in Arabic or English, our AI builds your ERP", "ar": "صف عملك بالعربي أو الإنجليزي، يبني الذكاء الاصطناعي نظام ERP لك"},
    "landing.feature2.title": {"en": "Multi-Tenant SaaS", "ar": "SaaS متعدد المستأجرين"},
    "landing.feature2.desc": {"en": "Each customer gets isolated data, users, and configurations", "ar": "كل عميل يحصل على بيانات ومستخدمين وإعدادات معزولة"},
    "landing.feature3.title": {"en": "Full Localization", "ar": "دعم كامل للغة العربية"},
    "landing.feature3.desc": {"en": "Arabic RTL, bilingual errors, industry terminology", "ar": "اتجاه عربي RTL، أخطاء ثنائية اللغة، مصطلحات صناعية"},

    # ─────────────────────────────────────
    # Authentication
    # ─────────────────────────────────────
    "auth.login.title": {"en": "Login to Your Account", "ar": "تسجيل الدخول إلى حسابك"},
    "auth.login.email": {"en": "Email Address", "ar": "البريد الإلكتروني"},
    "auth.login.password": {"en": "Password", "ar": "كلمة المرور"},
    "auth.login.submit": {"en": "Login", "ar": "تسجيل الدخول"},
    "auth.login.forgot": {"en": "Forgot Password?", "ar": "نسيت كلمة المرور؟"},
    "auth.login.no_account": {"en": "Don't have an account?", "ar": "ليس لديك حساب؟"},
    "auth.login.signup_link": {"en": "Sign Up", "ar": "سجل الآن"},

    "auth.signup.title": {"en": "Create Your Account", "ar": "إنشاء حسابك"},
    "auth.signup.first_name": {"en": "First Name", "ar": "الاسم الأول"},
    "auth.signup.last_name": {"en": "Last Name", "ar": "اسم العائلة"},
    "auth.signup.email": {"en": "Email Address", "ar": "البريد الإلكتروني"},
    "auth.signup.password": {"en": "Password", "ar": "كلمة المرور"},
    "auth.signup.confirm_password": {"en": "Confirm Password", "ar": "تأكيد كلمة المرور"},
    "auth.signup.submit": {"en": "Create Account", "ar": "إنشاء الحساب"},
    "auth.signup.has_account": {"en": "Already have an account?", "ar": "لديك حساب بالفعل؟"},
    "auth.signup.login_link": {"en": "Login", "ar": "تسجيل الدخول"},

    "auth.verify.title": {"en": "Verify Your Email", "ar": "تحقق من بريدك الإلكتروني"},
    "auth.verify.message": {"en": "We sent a verification code to your email", "ar": "أرسلنا رمز التحقق إلى بريدك الإلكتروني"},
    "auth.verify.code": {"en": "Verification Code", "ar": "رمز التحقق"},
    "auth.verify.submit": {"en": "Verify", "ar": "تحقق"},
    "auth.verify.resend": {"en": "Resend Code", "ar": "إعادة إرسال الرمز"},

    "auth.forgot.title": {"en": "Reset Password", "ar": "إعادة تعيين كلمة المرور"},
    "auth.forgot.submit": {"en": "Send Reset Link", "ar": "إرسال رابط إعادة التعيين"},
    "auth.reset.title": {"en": "New Password", "ar": "كلمة المرور الجديدة"},
    "auth.reset.submit": {"en": "Reset Password", "ar": "إعادة التعيين"},

    # ─────────────────────────────────────
    # AI Composer
    # ─────────────────────────────────────
    "composer.title": {"en": "AI Business Composer", "ar": "مُؤلف الأعمال بالذكاء الاصطناعي"},
    "composer.subtitle": {"en": "Describe your business, we build your ERP", "ar": "صف عملك، نبني نظام ERP لك"},
    "composer.placeholder": {"en": "e.g. I need an ERP for a construction company with project tracking, inventory, and invoicing...", "ar": "مثال: أحتاج نظام ERP لشركة مقاولات مع تتبع المشاريع، المخزون، وإدارة الفواتير..."},
    "composer.submit": {"en": "Generate ERP", "ar": "توليد نظام ERP"},
    "composer.industry": {"en": "Industry", "ar": "القطاع"},
    "composer.modules": {"en": "Modules", "ar": "الوحدات"},
    "composer.generating": {"en": "Generating your ERP...", "ar": "جارٍ توليد نظام ERP لك..."},

    # ─────────────────────────────────────
    # Builder
    # ─────────────────────────────────────
    "builder.title": {"en": "ERP Builder", "ar": "منشئ نظام ERP"},
    "builder.entities": {"en": "Entities", "ar": "الكيانات"},
    "builder.fields": {"en": "Fields", "ar": "الحقول"},
    "builder.relationships": {"en": "Relationships", "ar": "العلاقات"},
    "builder.preview": {"en": "Preview", "ar": "معاينة"},
    "builder.publish": {"en": "Publish", "ar": "نشر"},
    "builder.save_draft": {"en": "Save Draft", "ar": "حفظ كمسودة"},
    "builder.add_entity": {"en": "Add Entity", "ar": "إضافة كيان"},
    "builder.add_field": {"en": "Add Field", "ar": "إضافة حقل"},

    # ─────────────────────────────────────
    # ERP Module Names
    # ─────────────────────────────────────
    "module.accounting": {"en": "Accounting", "ar": "المحاسبة"},
    "module.finance": {"en": "Finance", "ar": "المالية"},
    "module.procurement": {"en": "Procurement", "ar": "المشتريات"},
    "module.inventory": {"en": "Inventory", "ar": "المخزون"},
    "module.sales": {"en": "Sales", "ar": "المبيعات"},
    "module.hr": {"en": "Human Resources", "ar": "الموارد البشرية"},
    "module.projects": {"en": "Projects", "ar": "المشاريع"},
    "module.fixed_assets": {"en": "Fixed Assets", "ar": "الأصول الثابتة"},
    "module.documents": {"en": "Documents", "ar": "المستندات"},
    "module.audit": {"en": "Audit", "ar": "التدقيق"},
    "module.localization": {"en": "Localization", "ar": "التوطين"},

    # ─────────────────────────────────────
    # Business Terminology (P64.4)
    # ─────────────────────────────────────
    "biz.customer": {"en": "Customer", "ar": "العميل"},
    "biz.customers": {"en": "Customers", "ar": "العملاء"},
    "biz.supplier": {"en": "Supplier", "ar": "المورد"},
    "biz.suppliers": {"en": "Suppliers", "ar": "الموردون"},
    "biz.invoice": {"en": "Invoice", "ar": "الفاتورة"},
    "biz.invoices": {"en": "Invoices", "ar": "الفواتير"},
    "biz.purchase": {"en": "Purchase Order", "ar": "طلب الشراء"},
    "biz.purchases": {"en": "Purchases", "ar": "المشتريات"},
    "biz.project": {"en": "Project", "ar": "المشروع"},
    "biz.projects": {"en": "Projects", "ar": "المشاريع"},
    "biz.warehouse": {"en": "Warehouse", "ar": "المخزن"},
    "biz.warehouses": {"en": "Warehouses", "ar": "المخازن"},
    "biz.employee": {"en": "Employee", "ar": "الموظف"},
    "biz.employees": {"en": "Employees", "ar": "الموظفون"},
    "biz.item": {"en": "Item", "ar": "الصنف"},
    "biz.items": {"en": "Items", "ar": "الأصناف"},
    "biz.quotation": {"en": "Quotation", "ar": "عرض السعر"},
    "biz.quotations": {"en": "Quotations", "ar": "عروض الأسعار"},
    "biz.receipt": {"en": "Receipt", "ar": "الإيصال"},
    "biz.receipts": {"en": "Receipts", "ar": "الإيصالات"},
    "biz.payment": {"en": "Payment", "ar": "الدفعة"},
    "biz.payments": {"en": "Payments", "ar": "المدفوعات"},
    "biz.journal": {"en": "Journal Entry", "ar": "القيد اليومي"},
    "biz.journals": {"en": "Journal Entries", "ar": "القيود اليومية"},
    "biz.account": {"en": "Account", "ar": "الحساب"},
    "biz.accounts": {"en": "Accounts", "ar": "الحسابات"},
    "biz.tax": {"en": "Tax", "ar": "الضريبة"},
    "biz.taxes": {"en": "Taxes", "ar": "الضرائب"},
    "biz.report": {"en": "Report", "ar": "التقرير"},
    "biz.reports": {"en": "Reports", "ar": "التقارير"},
    "biz.budget": {"en": "Budget", "ar": "الميزانية"},
    "biz.budgets": {"en": "Budgets", "ar": "الميزانيات"},
    "biz.cost_center": {"en": "Cost Center", "ar": "مركز التكلفة"},
    "biz.cost_centers": {"en": "Cost Centers", "ar": "مراكز التكلفة"},
    "biz.contract": {"en": "Contract", "ar": "العقد"},
    "biz.contracts": {"en": "Contracts", "ar": "العقود"},
    "biz.salary": {"en": "Salary", "ar": "الراتب"},
    "biz.salaries": {"en": "Salaries", "ar": "الرواتب"},
    "biz.attendance": {"en": "Attendance", "ar": "الحضور"},
    "biz.leave": {"en": "Leave", "ar": "الإجازة"},
    "biz.timesheet": {"en": "Timesheet", "ar": "سجل الوقت"},

    # ─────────────────────────────────────
    # Onboarding
    # ─────────────────────────────────────
    "onboard.welcome": {"en": "Welcome to EOS!", "ar": "مرحباً بك في EOS!"},
    "onboard.step1": {"en": "Tell us about your business", "ar": "أخبرنا عن عملك"},
    "onboard.step2": {"en": "Choose your modules", "ar": "اختر الوحدات"},
    "onboard.step3": {"en": "Invite your team", "ar": "ادعُ فريقك"},
    "onboard.step4": {"en": "Start using EOS", "ar": "ابدأ استخدام EOS"},
    "onboard.industry.placeholder": {"en": "e.g. Construction, Trading, Manufacturing...", "ar": "مثال: مقاولات، تجارة، تصنيع..."},
    "onboard.company_name": {"en": "Company Name", "ar": "اسم الشركة"},
    "onboard.company_name_ar": {"en": "Company Name (Arabic)", "ar": "اسم الشركة (عربي)"},

    # ─────────────────────────────────────
    # Marketplace
    # ─────────────────────────────────────
    "market.title": {"en": "Marketplace", "ar": "السوق"},
    "market.install": {"en": "Install", "ar": "تثبيت"},
    "market.uninstall": {"en": "Uninstall", "ar": "إلغاء التثبيت"},
    "market.installed": {"en": "Installed", "ar": "مثبت"},
    "market.free": {"en": "Free", "ar": "مجاني"},
    "market.search": {"en": "Search modules...", "ar": "بحث عن وحدات..."},
    "market.categories": {"en": "Categories", "ar": "الفئات"},
    "market.reviews": {"en": "Reviews", "ar": "التقييمات"},

    # ─────────────────────────────────────
    # Billing
    # ─────────────────────────────────────
    "billing.title": {"en": "Billing & Plans", "ar": "الفواتير والخطط"},
    "billing.plan.free": {"en": "Free Plan", "ar": "الخطة المجانية"},
    "billing.plan.starter": {"en": "Starter", "ar": "المبتدئ"},
    "billing.plan.pro": {"en": "Professional", "ar": "المحترف"},
    "billing.plan.enterprise": {"en": "Enterprise", "ar": "المؤسسات"},
    "billing.current": {"en": "Current Plan", "ar": "الخطة الحالية"},
    "billing.upgrade": {"en": "Upgrade", "ar": "ترقية"},
    "billing.invoice": {"en": "Invoice", "ar": "الفاتورة"},
    "billing.payment_method": {"en": "Payment Method", "ar": "طريقة الدفع"},

    # ─────────────────────────────────────
    # Portal
    # ─────────────────────────────────────
    "portal.title": {"en": "Customer Portal", "ar": "بوابة العميل"},
    "portal.overview": {"en": "Overview", "ar": "نظرة عامة"},
    "portal.tickets": {"en": "Support Tickets", "ar": "تذاكر الدعم"},
    "portal.usage": {"en": "Usage", "ar": "الاستخدام"},
    "portal.documents": {"en": "Documents", "ar": "المستندات"},

    # ─────────────────────────────────────
    # Notifications
    # ─────────────────────────────────────
    "notif.title": {"en": "Notifications", "ar": "الإشعارات"},
    "notif.mark_read": {"en": "Mark as Read", "ar": "تحديد كمقروء"},
    "notif.mark_all_read": {"en": "Mark All as Read", "ar": "تحديد الكل كمقروء"},
    "notif.empty": {"en": "No notifications", "ar": "لا توجد إشعارات"},

    # ─────────────────────────────────────
    # Common Actions
    # ─────────────────────────────────────
    "action.save": {"en": "Save", "ar": "حفظ"},
    "action.cancel": {"en": "Cancel", "ar": "إلغاء"},
    "action.delete": {"en": "Delete", "ar": "حذف"},
    "action.edit": {"en": "Edit", "ar": "تعديل"},
    "action.create": {"en": "Create", "ar": "إنشاء"},
    "action.search": {"en": "Search", "ar": "بحث"},
    "action.filter": {"en": "Filter", "ar": "تصفية"},
    "action.export": {"en": "Export", "ar": "تصدير"},
    "action.import": {"en": "Import", "ar": "استيراد"},
    "action.refresh": {"en": "Refresh", "ar": "تحديث"},
    "action.back": {"en": "Back", "ar": "رجوع"},
    "action.next": {"en": "Next", "ar": "التالي"},
    "action.previous": {"en": "Previous", "ar": "السابق"},
    "action.submit": {"en": "Submit", "ar": "إرسال"},
    "action.confirm": {"en": "Confirm", "ar": "تأكيد"},
    "action.close": {"en": "Close", "ar": "إغلاق"},
    "action.view_all": {"en": "View All", "ar": "عرض الكل"},
    "action.view_details": {"en": "View Details", "ar": "عرض التفاصيل"},

    # ─────────────────────────────────────
    # Status
    # ─────────────────────────────────────
    "status.active": {"en": "Active", "ar": "نشط"},
    "status.inactive": {"en": "Inactive", "ar": "غير نشط"},
    "status.pending": {"en": "Pending", "ar": "قيد الانتظار"},
    "status.approved": {"en": "Approved", "ar": "موافق عليه"},
    "status.rejected": {"en": "Rejected", "ar": "مرفوض"},
    "status.draft": {"en": "Draft", "ar": "مسودة"},
    "status.published": {"en": "Published", "ar": "منشور"},
    "status.paid": {"en": "Paid", "ar": "مدفوع"},
    "status.unpaid": {"en": "Unpaid", "ar": "غير مدفوع"},
    "status.overdue": {"en": "Overdue", "ar": "متأخر"},
    "status.completed": {"en": "Completed", "ar": "مكتمل"},
    "status.cancelled": {"en": "Cancelled", "ar": "ملغي"},

    # ─────────────────────────────────────
    # Error Messages (P64.7)
    # ─────────────────────────────────────
    "error.general": {"en": "An error occurred", "ar": "حدث خطأ"},
    "error.not_found": {"en": "Resource not found", "ar": "المورد غير موجود"},
    "error.unauthorized": {"en": "Unauthorized access", "ar": "وصول غير مصرح به"},
    "error.forbidden": {"en": "Access denied", "ar": "تم رفض الوصول"},
    "error.validation": {"en": "Validation error", "ar": "خطأ في التحقق"},
    "error.duplicate": {"en": "Resource already exists", "ar": "المورد موجود بالفعل"},
    "error.server": {"en": "Internal server error", "ar": "خطأ داخلي في الخادم"},
    "error.network": {"en": "Network error", "ar": "خطأ في الشبكة"},
    "error.timeout": {"en": "Request timed out", "ar": "انتهت مهلة الطلب"},
    "error.email.required": {"en": "Email is required", "ar": "البريد الإلكتروني مطلوب"},
    "error.email.invalid": {"en": "Invalid email address", "ar": "البريد الإلكتروني غير صالح"},
    "error.password.required": {"en": "Password is required", "ar": "كلمة المرور مطلوبة"},
    "error.password.weak": {"en": "Password is too weak", "ar": "كلمة المرور ضعيفة جداً"},
    "error.password.mismatch": {"en": "Passwords do not match", "ar": "كلمتا المرور غير متطابقتين"},
    "error.user.not_found": {"en": "User not found", "ar": "المستخدم غير موجود"},
    "error.user.already_exists": {"en": "User already exists", "ar": "المستخدم موجود بالfastcall"},
    "error.user.deactivated": {"en": "Account has been deactivated", "ar": "تم تعطيل الحساب"},
    "error.email.not_verified": {"en": "Email not verified", "ar": "البريد الإلكتروني غير موثق"},
    "error.token.invalid": {"en": "Invalid or expired token", "ar": "الرمز غير صالح أو منتهي الصلاحية"},
    "error.tenant.not_found": {"en": "Tenant not found", "ar": "المستأجر غير موجود"},
    "error.entity.not_found": {"en": "Entity not found", "ar": "الكيان غير موجود"},
    "error.entity.already_registered": {"en": "Entity already registered", "ar": "الكيان مسجل بالفعل"},
    "error.rate_limit": {"en": "Too many requests", "ar": "طلبات كثيرة جداً"},
    "error.file_too_large": {"en": "File is too large", "ar": "الملف كبير جداً"},

    # ─────────────────────────────────────
    # Tables / CRUD
    # ─────────────────────────────────────
    "table.no_data": {"en": "No data available", "ar": "لا توجد بيانات"},
    "table.loading": {"en": "Loading...", "ar": "جارٍ التحميل..."},
    "table.total": {"en": "Total", "ar": "الإجمالي"},
    "table.rows": {"en": "rows", "ar": "صفوف"},
    "table.page": {"en": "Page", "ar": "صفحة"},
    "table.of": {"en": "of", "ar": "من"},
    "table.add_new": {"en": "Add New", "ar": "إضافة جديد"},
    "table.confirm_delete": {"en": "Are you sure you want to delete this?", "ar": "هل أنت متأكد من الحذف؟"},
    "table.no_results": {"en": "No results found", "ar": "لم يتم العثور على نتائج"},

    # ─────────────────────────────────────
    # Date/Time (P64.5)
    # ─────────────────────────────────────
    "date.today": {"en": "Today", "ar": "اليوم"},
    "date.yesterday": {"en": "Yesterday", "ar": "أمس"},
    "date.tomorrow": {"en": "Tomorrow", "ar": "غداً"},
    "date.monday": {"en": "Monday", "ar": "الاثنين"},
    "date.tuesday": {"en": "Tuesday", "ar": "الثلاثاء"},
    "date.wednesday": {"en": "Wednesday", "ar": "الأربعاء"},
    "date.thursday": {"en": "Thursday", "ar": "الخميس"},
    "date.friday": {"en": "Friday", "ar": "الجمعة"},
    "date.saturday": {"en": "Saturday", "ar": "السبت"},
    "date.sunday": {"en": "Sunday", "ar": "الأحد"},
    "date.january": {"en": "January", "ar": "يناير"},
    "date.february": {"en": "February", "ar": "فبراير"},
    "date.march": {"en": "March", "ar": "مارس"},
    "date.april": {"en": "April", "ar": "أبريل"},
    "date.may": {"en": "May", "ar": "مايو"},
    "date.june": {"en": "June", "ar": "يونيو"},
    "date.july": {"en": "July", "ar": "يوليو"},
    "date.august": {"en": "August", "ar": "أغسطس"},
    "date.september": {"en": "September", "ar": "سبتمبر"},
    "date.october": {"en": "October", "ar": "أكتوبر"},
    "date.november": {"en": "November", "ar": "نوفمبر"},
    "date.december": {"en": "December", "ar": "ديسمبر"},
}


# ═══════════════════════════════════════════════
# Translation Functions
# ═══════════════════════════════════════════════

def t(key: str, lang: str = None, **kwargs) -> str:
    """
    Translate a key to the specified language.
    Falls back to English if key not found, then returns the key itself.

    Usage:
        t("auth.login.title", lang="ar")  # "تسجيل الدخول إلى حسابك"
        t("biz.invoice")  # Uses current_lang context
    """
    if lang is None:
        lang = current_lang.get(DEFAULT_LANGUAGE)

    translations = TRANSLATIONS.get(key, {})
    result = translations.get(lang) or translations.get(DEFAULT_LANGUAGE) or key

    # Interpolation: {name} → value
    if kwargs:
        for k, v in kwargs.items():
            result = result.replace(f"{{{k}}}", str(v))

    return result


def get_direction(lang: str = None) -> str:
    """Get text direction for language (rtl or ltr)."""
    if lang is None:
        lang = current_lang.get(DEFAULT_LANGUAGE)
    return "rtl" if lang in RTL_LANGUAGES else "ltr"


def get_language_name(lang: str) -> str:
    """Get the native name of a language."""
    names = {"ar": "العربية", "en": "English"}
    return names.get(lang, lang)


def get_supported_languages() -> list:
    """Get list of supported languages with their names."""
    return [
        {"code": lang, "name": get_language_name(lang), "direction": get_direction(lang)}
        for lang in sorted(SUPPORTED_LANGUAGES)
    ]


# ═══════════════════════════════════════════════
# Formatting (P64.5)
# ═══════════════════════════════════════════════

# Arabic-Indic digits
_ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# Eastern Arabic digits
_EASTERN_ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# Currency symbols
CURRENCY_SYMBOLS = {
    "SAR": {"en": "SAR", "ar": "ر.س"},
    "USD": {"en": "USD", "ar": "دولار"},
    "EUR": {"en": "EUR", "ar": "يورو"},
    "AED": {"en": "AED", "ar": "د.إ"},
    "EGP": {"en": "EGP", "ar": "ج.م"},
    "KWD": {"en": "KWD", "ar": "د.ك"},
    "BHD": {"en": "BHD", "ar": "د.ب"},
    "QAR": {"en": "QAR", "ar": "ر.ق"},
    "OMR": {"en": "OMR", "ar": "ر.ع"},
    "JOD": {"en": "JOD", "ar": "د.أ"},
}


def format_number(value, lang: str = None, decimals: int = 2) -> str:
    """
    Format a number with locale-appropriate separators.
    Arabic: ١٬٢٥٠٬٠٠٠٫٥٠
    English: 1,250,000.50
    """
    if lang is None:
        lang = current_lang.get(DEFAULT_LANGUAGE)

    if value is None:
        return "-"

    try:
        value = float(value)
    except (ValueError, TypeError):
        return str(value)

    if lang == "ar":
        # Arabic: comma = ٬  decimal = ٫
        formatted = f"{value:,.{decimals}f}"
        formatted = formatted.replace(",", "٬").replace(".", "٫")
    else:
        formatted = f"{value:,.{decimals}f}"

    return formatted


def format_currency(value, currency: str = "SAR", lang: str = None) -> str:
    """
    Format a currency value.
    Arabic: ١٬٢٥٠٬٠٠٠٫٥٠ ر.س
    English: SAR 1,250,000.50
    """
    if lang is None:
        lang = current_lang.get(DEFAULT_LANGUAGE)

    if value is None:
        return "-"

    formatted_number = format_number(value, lang=lang, decimals=2)
    symbols = CURRENCY_SYMBOLS.get(currency, {"en": currency, "ar": currency})
    symbol = symbols.get(lang, currency)

    if lang == "ar":
        return f"{formatted_number} {symbol}"
    else:
        return f"{symbol} {formatted_number}"


def format_percentage(value, lang: str = None, decimals: int = 1) -> str:
    """
    Format a percentage.
    Arabic: ٨٥٫٥٪
    English: 85.5%
    """
    if lang is None:
        lang = current_lang.get(DEFAULT_LANGUAGE)

    if value is None:
        return "-"

    formatted = format_number(value, lang=lang, decimals=decimals)
    return f"{formatted}٪" if lang == "ar" else f"{formatted}%"


def format_date(date_obj, lang: str = None, format_type: str = "medium") -> str:
    """
    Format a date.
    Arabic: ٢٦ أغسطس ٢٠٢٦
    English: Aug 26, 2026
    """
    if lang is None:
        lang = current_lang.get(DEFAULT_LANGUAGE)

    if date_obj is None:
        return "-"

    months_en = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    months_ar = [
        "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
    ]

    try:
        day = date_obj.day
        month = date_obj.month - 1
        year = date_obj.year

        if lang == "ar":
            day_ar = format_number(day, lang="ar", decimals=0)
            year_ar = format_number(year, lang="ar", decimals=0)
            if format_type == "short":
                return f"{day_ar}/{format_number(date_obj.month, lang='ar', decimals=0)}/{year_ar}"
            return f"{day_ar} {months_ar[month]} {year_ar}"
        else:
            if format_type == "short":
                return f"{date_obj.month}/{day}/{year}"
            return f"{months_en[month]} {day}, {year}"
    except Exception:
        return str(date_obj)


# ═══════════════════════════════════════════════
# Language Detection
# ═══════════════════════════════════════════════

def detect_language(accept_language: str = None, user_preference: str = None) -> str:
    """
    Detect language from Accept-Language header or user preference.
    Priority: user_preference > Accept-Language > default
    """
    if user_preference and user_preference in SUPPORTED_LANGUAGES:
        return user_preference

    if accept_language:
        # Parse Accept-Language header: ar,en;q=0.9,en-US;q=0.8
        for lang_part in accept_language.split(","):
            lang_code = lang_part.strip().split(";")[0].strip().lower()
            # Normalize: ar-SA → ar, en-US → en
            base = lang_code.split("-")[0]
            if base in SUPPORTED_LANGUAGES:
                return base

    return DEFAULT_LANGUAGE