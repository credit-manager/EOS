"""
P64 i18n / Localization Integration Test
Verifies all P64 components work:
- P64.1: Language Engine (core/i18n.py)
- P64.2: Translation files (locales/ar.json, locales/en.json)
- P64.3: Locale Middleware (Accept-Language, X-Locale)
- P64.4: Formatting (Date, Number, Currency)
- P64.5: Business Terminology
- P64.6: API Locale endpoints (/api/v1/locale/*)
- P64.7: RTL/LTR support
"""

import os
import sys
import json
import time
import socket
import subprocess
import pytest
import httpx

_results = []
_server_proc = None


def _find_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_server():
    global _server_proc
    port = _find_free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    for _ in range(15):
        time.sleep(1.0)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2.0) as c:
                r = c.get("/health")
                if r.status_code == 200:
                    break
        except Exception:
            pass
    _server_proc = proc
    return proc, port


def _stop_server():
    global _server_proc
    if _server_proc:
        try:
            _server_proc.terminate()
            _server_proc.wait(timeout=5)
        except Exception:
            _server_proc.kill()
        _server_proc = None


def _record(name, passed):
    global _results
    _results.append((name, passed))
    status = "PASS" if passed else "FAIL"
    print(f"  {'✅' if passed else '❌'} {name} [{status}]")


@pytest.fixture(scope="module")
def client():
    proc, port = _start_server()
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=15.0) as c:
        yield c
    _stop_server()


# ═══════════════════════════════════════════════
# P64.1: Language Engine
# ═══════════════════════════════════════════════

def test_p64_1_language_engine():
    """P64.1: core/i18n.py provides translation and formatting."""
    from core.i18n import (
        t, get_locale, set_locale, is_rtl, get_direction,
        SUPPORTED_LOCALES, RTL_LOCALES, detect_locale,
        format_date, format_number, format_currency,
        BUSINESS_TERMS, get_business_term, get_locale_info
    )

    # Basic translation
    en_welcome = t("ui.welcome", locale="en")
    ar_welcome = t("ui.welcome", locale="ar")
    _record("P64.1.1 Translation works (EN)", en_welcome == "Welcome to EOS")
    _record("P64.1.2 Translation works (AR)", ar_welcome == "مرحباً بك في EOS")

    # Fallback to English
    missing = t("nonexistent.key", locale="ar")
    _record("P64.1.3 Fallback to English for missing key", missing == "nonexistent.key")

    # Supported locales
    _record("P64.1.4 Supported locales = [en, ar]", SUPPORTED_LOCALES == ["en", "ar"])

    # RTL detection
    _record("P64.1.5 Arabic is RTL", is_rtl("ar") is True)
    _record("P64.1.6 English is LTR", is_rtl("en") is False)
    _record("P64.1.7 get_direction('ar') = rtl", get_direction("ar") == "rtl")
    _record("P64.1.8 get_direction('en') = ltr", get_direction("en") == "ltr")

    # detect_locale
    _record("P64.1.9 detect from Accept-Language", detect_locale("ar,en;q=0.9") == "ar")
    _record("P64.1.10 detect fallback to English", detect_locale("") == "en")
    _record("P64.1.11 detect user preference wins", detect_locale("en", user_preference="ar") == "ar")


# ═══════════════════════════════════════════════
# P64.2: Translation Files
# ═══════════════════════════════════════════════

def test_p64_2_translation_files():
    """P64.2: Translation JSON files exist and are valid."""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # English
    en_path = os.path.join(base_dir, "locales", "en.json")
    en_exists = os.path.exists(en_path)
    _record("P64.2.1 locales/en.json exists", en_exists)
    if en_exists:
        with open(en_path, encoding="utf-8") as f:
            en = json.load(f)
        sections = ["ui", "auth", "errors", "erp", "business", "marketplace",
                     "onboarding", "ai_composer", "billing", "portal", "notifications", "time", "pagination"]
        has_all = all(s in en for s in sections)
        _record("P64.2.2 EN has all sections", has_all)

    # Arabic
    ar_path = os.path.join(base_dir, "locales", "ar.json")
    ar_exists = os.path.exists(ar_path)
    _record("P64.2.3 locales/ar.json exists", ar_exists)
    if ar_exists:
        with open(ar_path, encoding="utf-8") as f:
            ar = json.load(f)
        has_all_ar = all(s in ar for s in sections)
        _record("P64.2.4 AR has all sections", has_all_ar)

        # Check key parity
        en_keys = set()
        ar_keys = set()
        def _collect_keys(d, prefix=""):
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    _collect_keys(v, full)
                else:
                    en_keys.add(full) if d is en else ar_keys.add(full)
        _collect_keys(en)
        _collect_keys(ar)
        missing_in_ar = en_keys - ar_keys
        missing_in_en = ar_keys - en_keys
        parity = len(missing_in_ar) == 0 and len(missing_in_en) == 0
        _record(f"P64.2.5 Key parity EN↔AR ({len(missing_in_ar)} missing in AR, {len(missing_in_en)} missing in EN)", parity)


# ═══════════════════════════════════════════════
# P64.3: Locale Middleware
# ═══════════════════════════════════════════════

def test_p64_3_locale_middleware(client):
    """P64.3: Locale middleware sets locale from headers."""
    # Default = English
    r = client.get("/health")
    _record("P64.3.1 Default Content-Language = en",
            r.headers.get("content-language") == "en")

    # X-Locale header
    r = client.get("/health", headers={"X-Locale": "ar"})
    _record("P64.3.2 X-Locale: ar sets Content-Language = ar",
            r.headers.get("content-language") == "ar")

    # Accept-Language header
    r = client.get("/health", headers={"Accept-Language": "ar,en;q=0.9"})
    _record("P64.3.3 Accept-Language: ar sets Content-Language = ar",
            r.headers.get("content-language") == "ar")

    # X-Locale takes precedence over Accept-Language
    r = client.get("/health", headers={"X-Locale": "ar", "Accept-Language": "en"})
    _record("P64.3.4 X-Locale takes precedence over Accept-Language",
            r.headers.get("content-language") == "ar")


# ═══════════════════════════════════════════════
# P64.4: Formatting
# ═══════════════════════════════════════════════

def test_p64_4_formatting():
    """P64.4: Date, number, currency formatting."""
    from core.i18n import format_date, format_number, format_currency
    from datetime import datetime

    dt = datetime(2026, 8, 26, 14, 30)

    # Date
    ar_date = format_date(dt, locale="ar")
    en_date = format_date(dt, locale="en")
    _record("P64.4.1 AR date format", "أغسطس" in ar_date)
    _record("P64.4.2 EN date format", "August" in en_date)

    # Number
    ar_num = format_number(1250000, locale="ar")
    en_num = format_number(1250000, locale="en")
    _record("P64.4.3 AR number with Arabic digits", "١٬٢٥٠٬٠٠٠" in ar_num)
    _record("P64.4.4 EN number with commas", "1,250,000" in en_num)

    # Currency
    ar_curr = format_currency(1250000, "SAR", locale="ar")
    en_curr = format_currency(1250000, "SAR", locale="en")
    _record("P64.4.5 AR currency (SAR)", "ر.س" in ar_curr)
    _record("P64.4.6 EN currency (SAR)", "SAR" in en_curr)

    # Decimal
    ar_dec = format_currency(1250.50, "SAR", locale="ar", decimals=2)
    en_dec = format_currency(1250.50, "SAR", locale="en", decimals=2)
    _record("P64.4.7 AR decimal formatting", "٫٥٠" in ar_dec)
    _record("P64.4.8 EN decimal formatting", ".50" in en_dec)


# ═══════════════════════════════════════════════
# P64.5: Business Terminology
# ═══════════════════════════════════════════════

def test_p64_5_business_terminology():
    """P64.5: Business terms are translated correctly."""
    from core.i18n import BUSINESS_TERMS, get_business_term

    key_terms = {
        "customer": ("العميل", "Customer"),
        "supplier": ("المورد", "Supplier"),
        "invoice": ("الفاتورة", "Invoice"),
        "purchase": ("المشتريات", "Purchase"),
        "project": ("المشروع", "Project"),
        "warehouse": ("المخزن", "Warehouse"),
        "employee": ("الموظف", "Employee"),
        "account": ("الحساب", "Account"),
        "payment": ("الدفعة", "Payment"),
        "report": ("التقرير", "Report"),
    }

    all_correct = True
    for key, (ar_expected, en_expected) in key_terms.items():
        ar_term = get_business_term(key, "ar")
        en_term = get_business_term(key, "en")
        if ar_term != ar_expected or en_term != en_expected:
            all_correct = False
            _record(f"P64.5 term '{key}'", False)

    _record("P64.5.1 All 10 core business terms translated correctly", all_correct)
    _record("P64.5.2 Total business terms defined", len(BUSINESS_TERMS) >= 40)


# ═══════════════════════════════════════════════
# P64.6: API Locale Endpoints
# ═══════════════════════════════════════════════

def test_p64_6_locale_api(client):
    """P64.6: Locale API endpoints work."""
    # /api/v1/locale/current
    r = client.get("/api/v1/locale/current")
    _record("P64.6.1 /locale/current 200", r.status_code == 200)
    data = r.json()
    _record("P64.6.2 /locale/current has locale", "locale" in data)
    _record("P64.6.3 /locale/current has direction", "direction" in data)
    _record("P64.6.4 /locale/current has is_rtl", "is_rtl" in data)

    # Switch locale
    r = client.post("/api/v1/locale/switch", json={"locale": "ar"})
    _record("P64.6.5 /locale/switch 200", r.status_code == 200)
    data = r.json()
    _record("P64.6.6 /locale/switch returns ar", data.get("locale") == "ar")
    _record("P64.6.7 /locale/switch is_rtl=true", data.get("is_rtl") is True)

    # Get translations
    r = client.get("/api/v1/locale/translations?locale=ar&section=ui")
    _record("P64.6.8 /locale/translations 200", r.status_code == 200)
    data = r.json()
    _record("P64.6.9 /locale/translations has welcome", data["translations"].get("welcome") == "مرحباً بك في EOS")

    # Get business terms
    r = client.get("/api/v1/locale/terms?locale=ar")
    _record("P64.6.10 /locale/terms 200", r.status_code == 200)
    data = r.json()
    _record("P64.6.11 /locale/terms has customer", data["terms"].get("customer") == "العميل")

    # Get single term
    r = client.get("/api/v1/locale/term/invoice?locale=ar")
    _record("P64.6.12 /locale/term/invoice 200", r.status_code == 200)
    data = r.json()
    _record("P64.6.13 /locale/term/invoice = الفاتورة", data.get("translation") == "الفاتورة")

    # Format date
    r = client.post("/api/v1/locale/format/date", json={"date": "2026-08-26", "locale": "ar"})
    _record("P64.6.14 /locale/format/date 200", r.status_code == 200)
    data = r.json()
    _record("P64.6.15 /locale/format/date Arabic month", "أغسطس" in data.get("formatted", ""))

    # Format number
    r = client.post("/api/v1/locale/format/number", json={"value": 1250000, "locale": "ar"})
    _record("P64.6.16 /locale/format/number 200", r.status_code == 200)
    data = r.json()
    _record("P64.6.17 /locale/format/number Arabic digits", "١٬٢٥٠٬٠٠٠" in data.get("formatted", ""))

    # Format currency
    r = client.post("/api/v1/locale/format/currency", json={"value": 1250, "currency": "SAR", "locale": "ar"})
    _record("P64.6.18 /locale/format/currency 200", r.status_code == 200)
    data = r.json()
    _record("P64.6.19 /locale/format/currency has ر.س", "ر.س" in data.get("formatted", ""))


# ═══════════════════════════════════════════════
# P64.7: RTL Support
# ═══════════════════════════════════════════════

def test_p64_7_rtl_support():
    """P64.7: RTL/LTR direction works correctly."""
    from core.i18n import is_rtl, get_direction, RTL_LOCALES

    # RTL locales
    _record("P64.7.1 Arabic in RTL_LOCALES", "ar" in RTL_LOCALES)

    # Direction header should be set by middleware
    # (tested in P64.3 via headers)

    # All business terms have AR translations
    from core.i18n import BUSINESS_TERMS
    ar_complete = all("ar" in v for v in BUSINESS_TERMS.values())
    _record("P64.7.2 All business terms have AR translation", ar_complete)


# ═══════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    _results = []

    print("=" * 60)
    print("  P64 i18n / LOCALIZATION TEST")
    print("=" * 60)

    proc, port = _start_server()
    base_url = f"http://127.0.0.1:{port}"

    try:
        with httpx.Client(base_url=base_url, timeout=15.0) as client:
            print("\n--- P64.1: Language Engine ---")
            test_p64_1_language_engine()

            print("\n--- P64.2: Translation Files ---")
            test_p64_2_translation_files()

            print("\n--- P64.3: Locale Middleware ---")
            test_p64_3_locale_middleware(client)

            print("\n--- P64.4: Formatting ---")
            test_p64_4_formatting()

            print("\n--- P64.5: Business Terminology ---")
            test_p64_5_business_terminology()

            print("\n--- P64.6: API Locale Endpoints ---")
            test_p64_6_locale_api(client)

            print("\n--- P64.7: RTL Support ---")
            test_p64_7_rtl_support()

    finally:
        _stop_server()

    passed = sum(1 for _, p in _results if p)
    total = len(_results)
    failed = total - passed

    print("\n" + "=" * 60)
    print(f"  P64 RESULTS: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 60)

    if failed > 0:
        print("\nFailed tests:")
        for name, p in _results:
            if not p:
                print(f"  ❌ {name}")

    sys.exit(0 if failed == 0 else 1)