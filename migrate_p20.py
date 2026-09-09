"""
P20 Migration — Validation Rules
"""
from sqlalchemy import text
from database import engine

TABLE = "dbp_validation_rules"

COLUMNS = {
    "id":              "VARCHAR(36) PRIMARY KEY",
    "tenant_id":       "VARCHAR(36)",
    "entity_id":       "VARCHAR(36) NOT NULL",
    "field_code":      "VARCHAR(100)",
    "rule_type":       "VARCHAR(50) NOT NULL",
    "rule_config":     "JSONB DEFAULT '{}'",
    "name_en":         "VARCHAR(255)",
    "name_ar":         "VARCHAR(255)",
    "severity":        "VARCHAR(20) DEFAULT 'error'",
    "is_active":       "BOOLEAN DEFAULT true",
    "condition_config":"JSONB",
    "created_at":      "TIMESTAMPTZ DEFAULT NOW()",
}

INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_entity ON {TABLE}(entity_id);",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_field ON {TABLE}(field_code);",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_type ON {TABLE}(rule_type);",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_tenant ON {TABLE}(tenant_id);",
]

if __name__ == "__main__":
    print("Running P20 migration...")
    with engine.begin() as conn:
        exists = conn.execute(text(
            f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='{TABLE}')"
        )).scalar()

        if not exists:
            col_defs = ", ".join(f"{c} {t}" for c, t in COLUMNS.items())
            conn.execute(text(f"CREATE TABLE {TABLE} ({col_defs})"))
            print(f"  [OK] {TABLE}")
        else:
            existing = {r[0] for r in conn.execute(text(
                f"SELECT column_name FROM information_schema.columns WHERE table_name='{TABLE}'"
            )).fetchall()}
            for col, typ in COLUMNS.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {TABLE} ADD COLUMN {col} {typ}"))
                    print(f"  [OK] Added {col}")

        for idx_sql in INDEXES:
            try:
                conn.execute(text(idx_sql))
            except Exception:
                pass

    print("P20 migration complete.")
