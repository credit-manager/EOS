"""
P32 Localization Engine
"""
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


class LocalizationEngine:
    def __init__(self, db: Session):
        self.db = db

    def create_locale(self, tenant_id, locale_code, language_code, **kw):
        lid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_tenant_locales "
            "(id, tenant_id, locale_code, language_code, country_code, currency_code, "
            "date_format, time_format, number_decimal_separator, number_group_separator, "
            "rtl, is_default) "
            "VALUES (:id,:tid,:lc,:lang,:cc,:curr,:df,:tf,:nds,:ngs,:rtl,:isd)"
        ), {
            "id": lid, "tid": tenant_id, "lc": locale_code, "lang": language_code,
            "cc": kw.get("country_code"), "curr": kw.get("currency_code"),
            "df": kw.get("date_format", "YYYY-MM-DD"), "tf": kw.get("time_format", "24h"),
            "nds": kw.get("number_decimal_separator", "."),
            "ngs": kw.get("number_group_separator", ","),
            "rtl": kw.get("rtl", False), "isd": kw.get("is_default", False),
        })
        self.db.flush()
        return lid

    def list_locales(self, tenant_id):
        rows = self.db.execute(text(
            "SELECT id, tenant_id, locale_code, language_code, country_code, currency_code, "
            "date_format, time_format, number_decimal_separator, number_group_separator, "
            "rtl, is_default, created_at "
            "FROM dbp_tenant_locales WHERE tenant_id = :tid ORDER BY is_default DESC, locale_code"
        ), {"tid": tenant_id}).fetchall()
        return [{"id": r[0], "tenant_id": r[1], "locale_code": r[2],
                "language_code": r[3], "country_code": r[4], "currency_code": r[5],
                "date_format": r[6], "time_format": r[7],
                "number_decimal_separator": r[8], "number_group_separator": r[9],
                "rtl": bool(r[10]), "is_default": bool(r[11]),
                "created_at": r[12].isoformat() if r[12] else None} for r in rows]

    def get_default_locale(self, tenant_id):
        row = self.db.execute(text(
            "SELECT id, tenant_id, locale_code, language_code, country_code, currency_code, "
            "date_format, time_format, number_decimal_separator, number_group_separator, "
            "rtl, is_default, created_at "
            "FROM dbp_tenant_locales WHERE tenant_id = :tid AND is_default = true LIMIT 1"
        ), {"tid": tenant_id}).fetchone()
        if not row:
            return None
        return {"id": row[0], "tenant_id": row[1], "locale_code": row[2],
                "language_code": row[3], "country_code": row[4], "currency_code": row[5],
                "date_format": row[6], "time_format": row[7],
                "number_decimal_separator": row[8], "number_group_separator": row[9],
                "rtl": bool(row[10]), "is_default": bool(row[11]),
                "created_at": row[12].isoformat() if row[12] else None}

    def set_default_locale(self, locale_id, tenant_id):
        row = self.db.execute(text(
            "SELECT id FROM dbp_tenant_locales WHERE id = :lid AND tenant_id = :tid"
        ), {"lid": locale_id, "tid": tenant_id}).fetchone()
        if not row:
            return {"success": False, "error": "Locale not found"}
        self.db.execute(text(
            "UPDATE dbp_tenant_locales SET is_default = false WHERE tenant_id = :tid"
        ), {"tid": tenant_id})
        self.db.execute(text(
            "UPDATE dbp_tenant_locales SET is_default = true WHERE id = :lid"
        ), {"lid": locale_id})
        self.db.flush()
        return {"success": True}

    def add_translation(self, locale_code, key, value, tenant_id=None, context=None):
        existing = self.db.execute(text(
            "SELECT id FROM dbp_translations WHERE locale_code = :lc AND key = :k "
            "AND tenant_id IS NOT DISTINCT FROM :tid"
        ), {"lc": locale_code, "k": key, "tid": tenant_id}).fetchone()
        if existing:
            self.db.execute(text(
                "UPDATE dbp_translations SET value = :v, context = :ctx WHERE id = :id"
            ), {"v": value, "ctx": context, "id": existing[0]})
            self.db.flush()
            return existing[0]
        tid = str(uuid.uuid4())
        self.db.execute(text(
            "INSERT INTO dbp_translations (id, tenant_id, locale_code, key, value, context) "
            "VALUES (:id,:tid,:lc,:k,:v,:ctx)"
        ), {"id": tid, "tid": tenant_id, "lc": locale_code,
            "k": key, "v": value, "ctx": context})
        self.db.flush()
        return tid

    def get_translation(self, locale_code, key, tenant_id=None):
        row = self.db.execute(text(
            "SELECT value FROM dbp_translations WHERE locale_code = :lc AND key = :k "
            "AND tenant_id IS NOT DISTINCT FROM :tid LIMIT 1"
        ), {"lc": locale_code, "k": key, "tid": tenant_id}).fetchone()
        return row[0] if row else None

    def get_translations(self, locale_code, tenant_id=None, context=None):
        conditions = ["locale_code = :lc", "tenant_id IS NOT DISTINCT FROM :tid"]
        params = {"lc": locale_code, "tid": tenant_id}
        if context:
            conditions.append("context = :ctx")
            params["ctx"] = context
        where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT key, value FROM dbp_translations WHERE {where}"
        ), params).fetchall()
        return {r[0]: r[1] for r in rows}

    def format_currency(self, amount, currency_code, locale_code=None, tenant_id=None):
        if locale_code is None and tenant_id:
            default = self.get_default_locale(tenant_id)
            if default:
                locale_code = default["locale_code"]
        dec_sep = "."
        grp_sep = ","
        if locale_code and tenant_id:
            loc = self.db.execute(text(
                "SELECT number_decimal_separator, number_group_separator "
                "FROM dbp_tenant_locales WHERE locale_code = :lc AND tenant_id = :tid LIMIT 1"
            ), {"lc": locale_code, "tid": tenant_id}).fetchone()
            if loc:
                dec_sep = loc[0] or "."
                grp_sep = loc[1] or ","
        amount = float(amount)
        negative = amount < 0
        amount = abs(amount)
        int_part = int(amount)
        dec_part = round(amount - int_part, 2)
        int_str = ""
        s = str(int_part)
        for i, ch in enumerate(reversed(s)):
            if i > 0 and i % 3 == 0:
                int_str = grp_sep + int_str
            int_str = ch + int_str
        if dec_part > 0:
            dec_str = f"{dec_sep}{round(dec_part * 100):02d}"
        else:
            dec_str = ""
        result = f"{'-' if negative else ''}{int_str}{dec_str} {currency_code}"
        return result

    def format_date(self, date_str, locale_code=None, tenant_id=None):
        fmt = "YYYY-MM-DD"
        if locale_code and tenant_id:
            loc = self.db.execute(text(
                "SELECT date_format FROM dbp_tenant_locales "
                "WHERE locale_code = :lc AND tenant_id = :tid LIMIT 1"
            ), {"lc": locale_code, "tid": tenant_id}).fetchone()
            if loc:
                fmt = loc[0] or "YYYY-MM-DD"
        try:
            if "T" in str(date_str):
                dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return str(date_str)
        result = fmt
        result = result.replace("YYYY", f"{dt.year:04d}")
        result = result.replace("MM", f"{dt.month:02d}")
        result = result.replace("DD", f"{dt.day:02d}")
        return result

    def list_countries(self, is_active=True):
        conditions = []
        params = {}
        if is_active is not None:
            conditions.append("is_active = :active")
            params["active"] = is_active
        where = "1=1"
        if conditions:
            where = " AND ".join(conditions)
        rows = self.db.execute(text(
            f"SELECT id, code, name_en, name_ar, currency_code, phone_code, is_active "
            f"FROM dbp_countries WHERE {where} ORDER BY name_en"
        ), params).fetchall()
        return [{"id": r[0], "code": r[1], "name_en": r[2], "name_ar": r[3],
                "currency_code": r[4], "phone_code": r[5],
                "is_active": bool(r[6])} for r in rows]

    def get_country(self, code):
        row = self.db.execute(text(
            "SELECT id, code, name_en, name_ar, currency_code, phone_code, is_active "
            "FROM dbp_countries WHERE code = :code"
        ), {"code": code}).fetchone()
        if not row:
            return None
        return {"id": row[0], "code": row[1], "name_en": row[2], "name_ar": row[3],
                "currency_code": row[4], "phone_code": row[5],
                "is_active": bool(row[6])}
