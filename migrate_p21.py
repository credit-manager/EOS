"""
P21 Migration — ERP Foundation Tables
  - dbp_companies (tenant root)
  - dbp_branches
  - dbp_departments
  - dbp_fiscal_years
  - dbp_currencies
  - dbp_cost_centers
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_companies": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "code": "VARCHAR(50) NOT NULL",
        "name_en": "VARCHAR(255) NOT NULL",
        "name_ar": "VARCHAR(255)",
        "legal_name": "VARCHAR(255)",
        "tax_number": "VARCHAR(100)",
        "commercial_registration": "VARCHAR(100)",
        "address": "TEXT",
        "city": "VARCHAR(100)",
        "country": "VARCHAR(50)",
        "phone": "VARCHAR(50)",
        "email": "VARCHAR(200)",
        "website": "VARCHAR(200)",
        "base_currency": "VARCHAR(10) DEFAULT 'SAR'",
        "fiscal_year_start_month": "INTEGER DEFAULT 1",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_branches": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) REFERENCES dbp_companies(id) ON DELETE CASCADE",
        "code": "VARCHAR(50) NOT NULL",
        "name_en": "VARCHAR(255) NOT NULL",
        "name_ar": "VARCHAR(255)",
        "address": "TEXT",
        "city": "VARCHAR(100)",
        "country": "VARCHAR(50)",
        "phone": "VARCHAR(50)",
        "is_headquarters": "BOOLEAN DEFAULT false",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_departments": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) REFERENCES dbp_companies(id) ON DELETE CASCADE",
        "parent_id": "VARCHAR(36) REFERENCES dbp_departments(id) ON DELETE SET NULL",
        "branch_id": "VARCHAR(36) REFERENCES dbp_branches(id) ON DELETE SET NULL",
        "code": "VARCHAR(50) NOT NULL",
        "name_en": "VARCHAR(255) NOT NULL",
        "name_ar": "VARCHAR(255)",
        "cost_center_id": "VARCHAR(36)",
        "manager_id": "VARCHAR(100)",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_fiscal_years": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) REFERENCES dbp_companies(id) ON DELETE CASCADE",
        "code": "VARCHAR(20) NOT NULL",
        "name": "VARCHAR(100) NOT NULL",
        "start_date": "DATE NOT NULL",
        "end_date": "DATE NOT NULL",
        "is_closed": "BOOLEAN DEFAULT false",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_currencies": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36)",
        "code": "VARCHAR(10) NOT NULL",
        "name_en": "VARCHAR(100) NOT NULL",
        "name_ar": "VARCHAR(100)",
        "symbol": "VARCHAR(10)",
        "decimal_places": "INTEGER DEFAULT 2",
        "is_base": "BOOLEAN DEFAULT false",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_cost_centers": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) REFERENCES dbp_companies(id) ON DELETE CASCADE",
        "code": "VARCHAR(50) NOT NULL",
        "name_en": "VARCHAR(255) NOT NULL",
        "name_ar": "VARCHAR(255)",
        "parent_id": "VARCHAR(36) REFERENCES dbp_cost_centers(id) ON DELETE SET NULL",
        "budget_amount": "NUMERIC(18,4) DEFAULT 0",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_companies": ["tenant_id", "code"],
    "dbp_branches": ["tenant_id", "company_id"],
    "dbp_departments": ["tenant_id", "company_id", "parent_id", "branch_id"],
    "dbp_fiscal_years": ["tenant_id", "company_id"],
    "dbp_currencies": ["tenant_id", "code"],
    "dbp_cost_centers": ["tenant_id", "company_id", "parent_id"],
}

if __name__ == "__main__":
    print("Running P21 migration...")
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
                try:
                    conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table}({col})"
                    ))
                except Exception:
                    pass

        # Seed default currencies
        existing_curr = conn.execute(text("SELECT code FROM dbp_currencies LIMIT 1")).fetchone()
        if not existing_curr:
            defaults = [
                ("SAR", "Saudi Riyal", "ريال", "﷼", 2, True),
                ("USD", "US Dollar", "دولار", "$", 2, False),
                ("EUR", "Euro", "يورو", "€", 2, False),
                ("GBP", "British Pound", "جنيه", "£", 2, False),
                ("AED", "UAE Dirham", "درهم", "د.إ", 2, False),
            ]
            for code, name_en, name_ar, sym, dec, is_base in defaults:
                conn.execute(text(
                    "INSERT INTO dbp_currencies (id, code, name_en, name_ar, symbol, decimal_places, is_base) "
                    "VALUES (:id, :code, :ne, :na, :sym, :dec, :base)"
                ), {"id": f"curr_{code.lower()}", "code": code, "ne": name_en,
                    "na": name_ar, "sym": sym, "dec": dec, "base": is_base})
            print("  [OK] Seeded 5 default currencies")

    print("P21 migration complete.")
