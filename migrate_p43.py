"""
P43 Subscription & Licensing Migration
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_subscriptions": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "plan_id": "VARCHAR(36) NOT NULL",
        "status": "VARCHAR(30) DEFAULT 'active'",
        "billing_cycle": "VARCHAR(20) DEFAULT 'monthly'",
        "current_period_start": "TIMESTAMPTZ",
        "current_period_end": "TIMESTAMPTZ",
        "trial_end": "TIMESTAMPTZ",
        "cancelled_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_invoices_saas": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "subscription_id": "VARCHAR(36) NOT NULL",
        "invoice_number": "VARCHAR(50) NOT NULL",
        "amount": "DOUBLE PRECISION NOT NULL",
        "currency": "VARCHAR(10) DEFAULT 'USD'",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "due_date": "TIMESTAMPTZ",
        "paid_at": "TIMESTAMPTZ",
        "line_items": "JSONB",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_payments_saas": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "invoice_id": "VARCHAR(36)",
        "amount": "DOUBLE PRECISION NOT NULL",
        "currency": "VARCHAR(10) DEFAULT 'USD'",
        "payment_method": "VARCHAR(50)",
        "status": "VARCHAR(20) DEFAULT 'pending'",
        "transaction_id": "VARCHAR(200)",
        "paid_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_licenses": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "license_key": "VARCHAR(200) NOT NULL",
        "license_type": "VARCHAR(50) NOT NULL",
        "max_seats": "INT DEFAULT 5",
        "valid_from": "TIMESTAMPTZ",
        "valid_until": "TIMESTAMPTZ",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "features": "JSONB",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_usage_meters": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "meter_name": "VARCHAR(100) NOT NULL",
        "meter_value": "DOUBLE PRECISION DEFAULT 0",
        "unit": "VARCHAR(20)",
        "period_start": "TIMESTAMPTZ",
        "period_end": "TIMESTAMPTZ",
        "overage_rate": "DOUBLE PRECISION DEFAULT 0",
        "recorded_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_subscriptions": ["tenant_id, status", "current_period_end"],
    "dbp_invoices_saas": ["tenant_id, status", "invoice_number"],
    "dbp_payments_saas": ["tenant_id, status", "invoice_id"],
    "dbp_licenses": ["tenant_id, license_key", "status"],
    "dbp_usage_meters": ["tenant_id, meter_name", "period_start"],
}

if __name__ == "__main__":
    print("Running P43 migration...")
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
                col_clean = col.replace(", ", "_")
                idx_name = f"idx_{table}_{col_clean}"
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})"))
                except Exception:
                    pass

    print("P43 migration complete.")
