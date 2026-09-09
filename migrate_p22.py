"""
P22 Migration — Accounting Engine
  - dbp_accounts (Chart of Accounts)
  - dbp_journal_entries
  - dbp_journal_lines
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_accounts": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "code": "VARCHAR(50) NOT NULL",
        "name_en": "VARCHAR(255) NOT NULL",
        "name_ar": "VARCHAR(255)",
        "account_type": "VARCHAR(30) NOT NULL",
        "parent_id": "VARCHAR(36)",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "is_active": "BOOLEAN DEFAULT true",
        "is_system": "BOOLEAN DEFAULT false",
        "opening_balance": "NUMERIC(18,4) DEFAULT 0",
        "current_balance": "NUMERIC(18,4) DEFAULT 0",
        "description": "TEXT",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_journal_entries": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "fiscal_year_id": "VARCHAR(36)",
        "entry_number": "VARCHAR(50) NOT NULL",
        "entry_date": "DATE NOT NULL",
        "entry_type": "VARCHAR(30) NOT NULL",
        "description": "TEXT",
        "reference": "VARCHAR(200)",
        "status": "VARCHAR(20) DEFAULT 'draft'",
        "total_debit": "NUMERIC(18,4) DEFAULT 0",
        "total_credit": "NUMERIC(18,4) DEFAULT 0",
        "is_posted": "BOOLEAN DEFAULT false",
        "posted_at": "TIMESTAMPTZ",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_journal_lines": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "journal_entry_id": "VARCHAR(36) REFERENCES dbp_journal_entries(id) ON DELETE CASCADE",
        "account_id": "VARCHAR(36) NOT NULL",
        "debit": "NUMERIC(18,4) DEFAULT 0",
        "credit": "NUMERIC(18,4) DEFAULT 0",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "description": "TEXT",
        "cost_center_id": "VARCHAR(36)",
        "line_order": "INTEGER DEFAULT 0",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_accounts": ["tenant_id", "company_id", "parent_id", "account_type", "code"],
    "dbp_journal_entries": ["tenant_id", "company_id", "entry_date", "status", "entry_number"],
    "dbp_journal_lines": ["journal_entry_id", "account_id"],
}

if __name__ == "__main__":
    print("Running P22 migration...")
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
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table}({col})"))
                except Exception:
                    pass
    print("P22 migration complete.")
