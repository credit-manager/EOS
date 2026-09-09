"""
P18 Migration — Data Jobs
"""
from sqlalchemy import text
from database import engine

TABLE = "dbp_data_jobs"

COLUMNS = {
    "id":          "VARCHAR(36) PRIMARY KEY",
    "tenant_id":   "VARCHAR(36)",
    "code":        "VARCHAR(100) NOT NULL",
    "name_en":     "VARCHAR(255) NOT NULL",
    "name_ar":     "VARCHAR(255)",
    "job_type":    "VARCHAR(50) NOT NULL",
    "entity_code": "VARCHAR(100)",
    "status":      "VARCHAR(30) NOT NULL DEFAULT 'pending'",
    "priority":    "INTEGER DEFAULT 0",
    "config":      "JSONB DEFAULT '{}'",
    "result":      "JSONB DEFAULT '{}'",
    "progress":    "INTEGER DEFAULT 0",
    "error_message": "TEXT",
    "started_at":  "TIMESTAMPTZ",
    "completed_at":"TIMESTAMPTZ",
    "scheduled_at":"TIMESTAMPTZ",
    "created_by":  "VARCHAR(100)",
    "created_at":  "TIMESTAMPTZ DEFAULT NOW()",
    "updated_at":  "TIMESTAMPTZ",
}

INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_tenant ON {TABLE}(tenant_id);",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_status ON {TABLE}(status);",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_type ON {TABLE}(job_type);",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_entity ON {TABLE}(entity_code);",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_scheduled ON {TABLE}(scheduled_at) WHERE scheduled_at IS NOT NULL;",
]

if __name__ == "__main__":
    print("Running P18 migration...")
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

    print("P18 migration complete.")
