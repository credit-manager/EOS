"""
P32 Migration - Multi-Currency & Localization
  - dbp_tenant_locales
  - dbp_translations
  - dbp_countries (seeded)
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_tenant_locales": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "locale_code": "VARCHAR(10) NOT NULL",
        "language_code": "VARCHAR(10) NOT NULL",
        "country_code": "VARCHAR(5)",
        "currency_code": "VARCHAR(10)",
        "date_format": "VARCHAR(20) DEFAULT 'YYYY-MM-DD'",
        "time_format": "VARCHAR(10) DEFAULT '24h'",
        "number_decimal_separator": "VARCHAR(1) DEFAULT '.'",
        "number_group_separator": "VARCHAR(1) DEFAULT ','",
        "rtl": "BOOLEAN DEFAULT false",
        "is_default": "BOOLEAN DEFAULT false",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_translations": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36)",
        "locale_code": "VARCHAR(10) NOT NULL",
        "key": "VARCHAR(255) NOT NULL",
        "value": "TEXT NOT NULL",
        "context": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_countries": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "code": "VARCHAR(5) NOT NULL",
        "name_en": "VARCHAR(255)",
        "name_ar": "VARCHAR(255)",
        "currency_code": "VARCHAR(10)",
        "phone_code": "VARCHAR(10)",
        "is_active": "BOOLEAN DEFAULT true",
    },
}

INDEXES = {
    "dbp_tenant_locales": ["tenant_id"],
    "dbp_translations": ["locale_code", "key"],
    "dbp_countries": ["code"],
}

COUNTRIES = [
    ("SA", "Saudi Arabia", "\u0627\u0644\u0645\u0645\u0644\u0643\u0629 \u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0627\u0644\u0633\u0639\u0648\u062f\u064a\u0629", "SAR", "+966"),
    ("US", "United States", "\u0627\u0644\u0648\u0644\u0627\u064a\u0627\u062a \u0627\u0644\u0645\u062a\u062d\u062f\u0629 \u0627\u0644\u0623\u0645\u0631\u064a\u0643\u064a\u0629", "USD", "+1"),
    ("GB", "United Kingdom", "\u0627\u0644\u0645\u0645\u0644\u0643\u0629 \u0627\u0644\u0645\u062a\u062d\u062f\u0629 \u0627\u0644\u0628\u0631\u064a\u0637\u0627\u0646\u064a\u0629 \u0627\u0644\u0643\u0628\u064a\u0631\u0629", "GBP", "+44"),
    ("AE", "United Arab Emirates", "\u0627\u0644\u0625\u0645\u0627\u0631\u0627\u062a \u0627\u0644\u0639\u0631\u0628\u064a\u0629 \u0627\u0644\u0645\u062a\u062d\u062f\u0629", "AED", "+971"),
    ("EG", "Egypt", "\u0645\u0635\u0631", "EGP", "+20"),
    ("KW", "Kuwait", "\u0627\u0644\u0643\u0648\u064a\u062a", "KWD", "+965"),
    ("BH", "Bahrain", "\u0627\u0644\u0628\u062d\u0631\u064a\u0646", "BHD", "+973"),
    ("QA", "Qatar", "\u0642\u0637\u0631", "QAR", "+974"),
    ("OM", "Oman", "\u0639\u064f\u0645\u0627\u0646", "OMR", "+968"),
    ("JO", "Jordan", "\u0627\u0644\u0623\u0631\u062f\u0646", "JOD", "+962"),
]

if __name__ == "__main__":
    print("Running P32 migration...")
    with engine.begin() as conn:
        for table, cols in TABLES.items():
            exists = conn.execute(text(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='{table}')"
            )).scalar()
            if not exists:
                col_defs = ", ".join(f"{c} {t}" for c, t in cols.items())
                conn.execute(text(f"CREATE TABLE {table} ({col_defs})"))
                print(f"  [OK] {table}")
            else:
                existing = {r[0] for r in conn.execute(text(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'"
                )).fetchall()}
                for col, typ in cols.items():
                    if col not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typ}"))
                        print(f"  [OK] Added {col} to {table}")

        for table, cols in INDEXES.items():
            for col in cols:
                idx_name = f"idx_{table}_{col}"
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})"))
                except Exception:
                    pass

        existing_count = conn.execute(text("SELECT COUNT(*) FROM dbp_countries")).scalar() or 0
        if existing_count == 0:
            import uuid
            for code, name_en, name_ar, currency_code, phone_code in COUNTRIES:
                cid = str(uuid.uuid4())
                conn.execute(text(
                    "INSERT INTO dbp_countries (id, code, name_en, name_ar, currency_code, phone_code, is_active) "
                    "VALUES (:id,:code,:name_en,:name_ar,:cc,:pc,true)"
                ), {"id": cid, "code": code, "name_en": name_en, "name_ar": name_ar,
                    "cc": currency_code, "pc": phone_code})
            print(f"  [OK] Seeded {len(COUNTRIES)} countries")
        else:
            print(f"  [SKIP] dbp_countries already has {existing_count} rows")

    print("P32 migration complete.")
