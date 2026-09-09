"""
P32 MULTI-CURRENCY & LOCALIZATION TESTS
"""
import httpx, subprocess, sys, time, os
sys.path.insert(0, ".")
from core.auth import create_test_token

BASE = "http://127.0.0.1:8000"
EP = "/api/v1/dynamic"
TOKEN = create_test_token("tenant_a", user_id="admin", email="admin@test.com", roles=["admin"])
H = {"Authorization": f"Bearer {TOKEN}"}
p, f = 0, 0
CID = "co_p32"


def t(name, got, exp):
    global p, f
    if got == exp:
        p += 1
    else:
        f += 1
        print(f"  FAIL - {name}: got {got!r}, expected {exp!r}")


def start():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
    time.sleep(5)
    return proc


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def setup():
    from database import SessionLocal
    from sqlalchemy import text as sa
    db = SessionLocal()
    try:
        for tbl in ("dbp_translations", "dbp_tenant_locales"):
            db.execute(sa(f"DELETE FROM {tbl} WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa("DELETE FROM dbp_companies WHERE tenant_id IN ('tenant_a','tenant_b')"))
        db.execute(sa(
            "INSERT INTO dbp_companies (id, tenant_id, code, name_en) "
            "VALUES ('co_p32', 'tenant_a', 'CO32', 'Test')"
        ))
        db.commit()
    finally:
        db.close()


def test_create_locale(c):
    print("\n--- 1. Create Locale ---")
    r = c.post(f"{EP}/locales", headers=H, json={
        "locale_code": "en_US", "language_code": "en",
        "country_code": "US", "currency_code": "USD",
        "date_format": "MM/DD/YYYY", "is_default": True})
    t("Create en_US", r.status_code, 200)
    lid1 = r.json()["data"]["id"]

    r = c.post(f"{EP}/locales", headers=H, json={
        "locale_code": "ar_SA", "language_code": "ar",
        "country_code": "SA", "currency_code": "SAR",
        "rtl": True})
    t("Create ar_SA", r.status_code, 200)
    lid2 = r.json()["data"]["id"]
    return lid1, lid2


def test_list_locales(c, lid1, lid2):
    print("\n--- 2. List Locales ---")
    r = c.get(f"{EP}/locales", headers=H)
    t("List locales", r.status_code, 200)
    t("Has 2 locales", len(r.json()["data"]), 2)


def test_set_default(c, lid1, lid2):
    print("\n--- 3. Set Default Locale ---")
    r = c.post(f"{EP}/locales/{lid2}/default", headers=H)
    t("Set default ar_SA", r.status_code, 200)

    r = c.get(f"{EP}/locales", headers=H)
    defaults = [l for l in r.json()["data"] if l["is_default"]]
    t("Only 1 default", len(defaults), 1)
    t("Default is ar_SA", defaults[0]["locale_code"], "ar_SA")


def test_get_default(c):
    print("\n--- 4. Get Default Locale ---")
    r = c.get(f"{EP}/locales", headers=H)
    defaults = [l for l in r.json()["data"] if l["is_default"]]
    t("Has default", len(defaults) >= 1, True)


def test_add_translation(c, lid1):
    print("\n--- 5. Add Translation ---")
    r = c.post(f"{EP}/locales/{lid1}/translations", headers=H, json={
        "key": "greeting", "value": "Hello", "context": "general"})
    t("Add greeting", r.status_code, 200)
    tid = r.json()["data"]["id"]

    r = c.post(f"{EP}/locales/{lid1}/translations", headers=H, json={
        "key": "farewell", "value": "Goodbye"})
    t("Add farewell", r.status_code, 200)
    return tid


def test_get_single_translation(c, lid1):
    print("\n--- 6. Get Single Translation ---")
    r = c.get(f"{EP}/locales/{lid1}/translate/greeting", headers=H)
    t("Get greeting", r.status_code, 200)
    t("Value is Hello", r.json()["data"]["value"], "Hello")

    r = c.get(f"{EP}/locales/{lid1}/translate/nonexistent", headers=H)
    t("Missing key 404", r.status_code, 404)


def test_get_all_translations(c, lid1):
    print("\n--- 7. Get All Translations ---")
    r = c.get(f"{EP}/locales/{lid1}/translations", headers=H)
    t("Get translations", r.status_code, 200)
    data = r.json()["data"]
    t("Has greeting", "greeting" in data, True)
    t("Has farewell", "farewell" in data, True)
    t("Count 2", len(data), 2)


def test_get_translations_by_context(c, lid1):
    print("\n--- 8. Get Translations by Context ---")
    r = c.get(f"{EP}/locales/{lid1}/translations?context=general", headers=H)
    t("Filter by context", r.status_code, 200)
    data = r.json()["data"]
    t("Has greeting", "greeting" in data, True)
    t("No farewell", "farewell" not in data, True)


def test_upsert_translation(c, lid1):
    print("\n--- 9. Upsert Translation ---")
    r = c.post(f"{EP}/locales/{lid1}/translations", headers=H, json={
        "key": "greeting", "value": "Hi there"})
    t("Upsert greeting", r.status_code, 200)

    r = c.get(f"{EP}/locales/{lid1}/translate/greeting", headers=H)
    t("Updated value", r.json()["data"]["value"], "Hi there")

    r = c.get(f"{EP}/locales/{lid1}/translations", headers=H)
    t("Still 2 keys", len(r.json()["data"]), 2)


def test_format_currency(c):
    print("\n--- 10. Format Currency ---")
    r = c.post(f"{EP}/format-currency", headers=H, json={
        "amount": 1234.56, "currency_code": "SAR", "locale_code": "en_US"})
    t("Format SAR", r.status_code, 200)
    t("Formatted value", r.json()["data"]["formatted"], "1,234.56 SAR")

    r = c.post(f"{EP}/format-currency", headers=H, json={
        "amount": 1234.56, "currency_code": "SAR", "locale_code": "ar_SA"})
    t("Format SAR ar_SA", r.status_code, 200)


def test_format_date(c):
    print("\n--- 11. Format Date ---")
    r = c.post(f"{EP}/format-date", headers=H, json={
        "date_str": "2025-06-15", "locale_code": "en_US"})
    t("Format date en_US", r.status_code, 200)
    t("Formatted MM/DD/YYYY", r.json()["data"]["formatted"], "06/15/2025")

    r = c.post(f"{EP}/format-date", headers=H, json={
        "date_str": "2025-06-15", "locale_code": "ar_SA"})
    t("Format date default", r.status_code, 200)


def test_list_countries(c):
    print("\n--- 12. List Countries ---")
    r = c.get(f"{EP}/countries", headers=H)
    t("List countries", r.status_code, 200)
    t("Has 10 countries", len(r.json()["data"]), 10)


def test_get_country(c):
    print("\n--- 13. Get Country ---")
    r = c.get(f"{EP}/countries", headers=H)
    sa = [co for co in r.json()["data"] if co["code"] == "SA"]
    t("SA exists", len(sa), 1)
    t("SA currency SAR", sa[0]["currency_code"], "SAR")
    t("SA phone +966", sa[0]["phone_code"], "+966")

    us = [co for co in r.json()["data"] if co["code"] == "US"]
    t("US exists", len(us), 1)
    t("US currency USD", us[0]["currency_code"], "USD")


def test_create_locale_arabic(c):
    print("\n--- 14. Arabic Locale RTL ---")
    r = c.get(f"{EP}/locales", headers=H)
    ar = [l for l in r.json()["data"] if l["locale_code"] == "ar_SA"]
    t("ar_SA RTL flag", ar[0]["rtl"], True)
    t("ar_SA currency SAR", ar[0]["currency_code"], "SAR")


def test_tenant_isolation_locales(c):
    print("\n--- 15. Tenant Isolation - Locales ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/locales", headers=H_B)
    t("Tenant B no locales", len(r.json()["data"]), 0)


def test_tenant_isolation_translations(c):
    print("\n--- 16. Tenant Isolation - Translations ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}

    r = c.post(f"{EP}/locales", headers=H_B, json={
        "locale_code": "en_US", "language_code": "en"})
    t("Tenant B create locale", r.status_code, 200)
    lid_b = r.json()["data"]["id"]

    r = c.get(f"{EP}/locales/{lid_b}/translations", headers=H)
    t("Tenant A cannot see B translations", r.status_code, 404)


def test_missing_required_fields(c):
    print("\n--- 17. Missing Required Fields ---")
    r = c.post(f"{EP}/locales", headers=H, json={})
    t("Missing locale_code", r.status_code, 400)

    r = c.post(f"{EP}/format-currency", headers=H, json={"amount": 100})
    t("Missing currency_code", r.status_code, 400)

    r = c.post(f"{EP}/format-date", headers=H, json={})
    t("Missing date_str", r.status_code, 400)


def test_format_currency_large(c):
    print("\n--- 18. Format Currency Large Amount ---")
    r = c.post(f"{EP}/format-currency", headers=H, json={
        "amount": 1234567.89, "currency_code": "USD", "locale_code": "en_US"})
    t("Large amount", r.status_code, 200)
    t("Formatted large", r.json()["data"]["formatted"], "1,234,567.89 USD")


def test_format_currency_zero(c):
    print("\n--- 19. Format Currency Zero ---")
    r = c.post(f"{EP}/format-currency", headers=H, json={
        "amount": 0, "currency_code": "SAR", "locale_code": "en_US"})
    t("Zero amount", r.status_code, 200)
    t("Formatted zero", r.json()["data"]["formatted"], "0 SAR")


def test_countries_global(c):
    print("\n--- 20. Countries are Global ---")
    TOKEN_B = create_test_token("tenant_b", user_id="b", email="b@test.com", roles=["admin"])
    H_B = {"Authorization": f"Bearer {TOKEN_B}"}
    r = c.get(f"{EP}/countries", headers=H_B)
    t("Tenant B sees countries", r.status_code, 200)
    t("Tenant B sees 10", len(r.json()["data"]), 10)


def test_add_arabic_translation(c, lid_ar):
    print("\n--- 21. Arabic Translation ---")
    r = c.post(f"{EP}/locales/{lid_ar}/translations", headers=H, json={
        "key": "greeting", "value": "\u0645\u0631\u062d\u0628\u0627"})
    t("Add Arabic greeting", r.status_code, 200)

    r = c.get(f"{EP}/locales/{lid_ar}/translate/greeting", headers=H)
    t("Arabic value", r.json()["data"]["value"], "\u0645\u0631\u062d\u0628\u0627")


def test_format_currency_negative(c):
    print("\n--- 22. Format Currency Negative ---")
    r = c.post(f"{EP}/format-currency", headers=H, json={
        "amount": -500.25, "currency_code": "EUR", "locale_code": "en_US"})
    t("Negative amount", r.status_code, 200)
    t("Formatted negative", r.json()["data"]["formatted"], "-500.25 EUR")


def test_format_date_iso_with_time(c):
    print("\n--- 23. Format Date ISO with Time ---")
    r = c.post(f"{EP}/format-date", headers=H, json={
        "date_str": "2025-12-25T10:30:00", "locale_code": "en_US"})
    t("ISO with time", r.status_code, 200)
    t("Extracted date only", r.json()["data"]["formatted"], "12/25/2025")


def test_get_locale_not_found(c):
    print("\n--- 24. Locale Not Found ---")
    r = c.get(f"{EP}/locales/nonexistent/translations", headers=H)
    t("Bad locale ID", r.status_code, 404)


def test_set_default_not_found(c):
    print("\n--- 25. Set Default Not Found ---")
    r = c.post(f"{EP}/locales/nonexistent/default", headers=H)
    t("Set default bad ID", r.status_code, 404)


def test_multiple_countries(c):
    print("\n--- 26. Multiple Countries Data ---")
    r = c.get(f"{EP}/countries", headers=H)
    codes = {co["code"] for co in r.json()["data"]}
    for expected in ("KW", "BH", "QA", "OM", "JO"):
        t(f"Country {expected} present", expected in codes, True)


def test_locale_fields(c, lid1):
    print("\n--- 27. Locale Fields ---")
    r = c.get(f"{EP}/locales", headers=H)
    en = [l for l in r.json()["data"] if l["locale_code"] == "en_US"]
    t("date_format", en[0]["date_format"], "MM/DD/YYYY")
    t("currency_code", en[0]["currency_code"], "USD")
    t("country_code", en[0]["country_code"], "US")


if __name__ == "__main__":
    print("=" * 60)
    print("P32 MULTI-CURRENCY & LOCALIZATION TESTS")
    print("=" * 60)
    setup()
    proc = start()
    c = httpx.Client(base_url=BASE, timeout=30)
    try:
        lid1, lid2 = test_create_locale(c)
        test_list_locales(c, lid1, lid2)
        test_set_default(c, lid1, lid2)
        test_get_default(c)
        tid = test_add_translation(c, lid1)
        test_get_single_translation(c, lid1)
        test_get_all_translations(c, lid1)
        test_get_translations_by_context(c, lid1)
        test_upsert_translation(c, lid1)
        test_format_currency(c)
        test_format_date(c)
        test_list_countries(c)
        test_get_country(c)
        test_create_locale_arabic(c)
        test_tenant_isolation_locales(c)
        test_tenant_isolation_translations(c)
        test_missing_required_fields(c)
        test_format_currency_large(c)
        test_format_currency_zero(c)
        test_countries_global(c)
        test_add_arabic_translation(c, lid2)
        test_format_currency_negative(c)
        test_format_date_iso_with_time(c)
        test_get_locale_not_found(c)
        test_set_default_not_found(c)
        test_multiple_countries(c)
        test_locale_fields(c, lid1)
    finally:
        c.close()
        stop(proc)
    print("\n" + "=" * 60)
    print(f"P32 RESULTS: {p}/{p+f} PASSED, {f} FAILED")
    print("=" * 60)
    sys.exit(0 if f == 0 else 1)
