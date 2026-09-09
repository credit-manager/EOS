"""
P23 Migration — Finance & Treasury
  - dbp_bank_accounts
  - dbp_payments
  - dbp_exchange_rates
  - dbp_budgets
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_bank_accounts": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "account_name": "VARCHAR(255) NOT NULL",
        "bank_name": "VARCHAR(255)",
        "account_number": "VARCHAR(100)",
        "iban": "VARCHAR(50)",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "gl_account_id": "VARCHAR(36)",
        "current_balance": "NUMERIC(18,4) DEFAULT 0",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_payments": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "payment_number": "VARCHAR(50) NOT NULL",
        "payment_type": "VARCHAR(20) NOT NULL",
        "payment_date": "DATE NOT NULL",
        "amount": "NUMERIC(18,4) NOT NULL",
        "currency_code": "VARCHAR(10) DEFAULT 'SAR'",
        "exchange_rate": "NUMERIC(18,6) DEFAULT 1",
        "bank_account_id": "VARCHAR(36) REFERENCES dbp_bank_accounts(id)",
        "payee_name": "VARCHAR(255)",
        "payee_type": "VARCHAR(30)",
        "reference": "VARCHAR(200)",
        "description": "TEXT",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "journal_entry_id": "VARCHAR(36)",
        "cost_center_id": "VARCHAR(36)",
        "created_by": "VARCHAR(100)",
        "approved_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_exchange_rates": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36)",
        "from_currency": "VARCHAR(10) NOT NULL",
        "to_currency": "VARCHAR(10) NOT NULL",
        "rate": "NUMERIC(18,6) NOT NULL",
        "rate_date": "DATE NOT NULL",
        "source": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_budgets": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "account_id": "VARCHAR(36)",
        "cost_center_id": "VARCHAR(36)",
        "fiscal_year_id": "VARCHAR(36)",
        "period": "VARCHAR(20)",
        "budget_amount": "NUMERIC(18,4) DEFAULT 0",
        "actual_amount": "NUMERIC(18,4) DEFAULT 0",
        "variance": "NUMERIC(18,4) DEFAULT 0",
        "is_active": "BOOLEAN DEFAULT true",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_bank_accounts": ["tenant_id", "company_id"],
    "dbp_payments": ["tenant_id", "company_id", "payment_type", "status", "payment_date"],
    "dbp_exchange_rates": ["from_currency", "to_currency", "rate_date"],
    "dbp_budgets": ["tenant_id", "company_id", "fiscal_year_id"],
}

if __name__ == "__main__":
    print("Running P23 migration...")
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
    print("P23 migration complete.")
