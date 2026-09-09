"""
P53 Migration — AI Business Composer
Table: dbp_composer_sessions
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text

TABLE = {
    "dbp_composer_sessions": {
        "columns": [
            ("id", "VARCHAR(36) PRIMARY KEY"),
            ("tenant_id", "VARCHAR(100) NOT NULL"),
            ("user_id", "VARCHAR(100) NOT NULL"),
            ("natural_language_input", "TEXT NOT NULL"),
            ("detected_industry", "VARCHAR(50)"),
            ("detected_language", "VARCHAR(10)"),
            ("parsed_requirements", "JSONB NOT NULL DEFAULT '{}'"),
            ("generated_config", "JSONB NOT NULL DEFAULT '{}'"),
            ("status", "VARCHAR(30) NOT NULL DEFAULT 'draft'"),
            ("preview_data", "JSONB NOT NULL DEFAULT '{}'"),
            ("approved_by", "VARCHAR(100)"),
            ("approved_at", "TIMESTAMP"),
            ("activated_at", "TIMESTAMP"),
            ("activation_result", "JSONB NOT NULL DEFAULT '{}'"),
            ("error_message", "TEXT"),
            ("created_at", "TIMESTAMP DEFAULT NOW()"),
            ("updated_at", "TIMESTAMP DEFAULT NOW()"),
        ],
    },
}

INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_composer_tenant ON dbp_composer_sessions(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_composer_status ON dbp_composer_sessions(status)",
]


def migrate():
    with engine.begin() as conn:
        cols = ", ".join(f"{c[0]} {c[1]}" for c in TABLE["dbp_composer_sessions"]["columns"])
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS dbp_composer_sessions ({cols})"))
        print("  [OK] dbp_composer_sessions")
        for idx in INDICES:
            conn.execute(text(idx))
        print("  [OK] Indices")


if __name__ == "__main__":
    print("=" * 60)
    print("  P53 MIGRATION — AI Business Composer")
    print("=" * 60)
    migrate()
    print("  DONE")
