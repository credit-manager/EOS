"""
P54 Migration — Self-Service ERP Builder
Tables: dbp_builder_projects, dbp_builder_versions
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from database import engine
from sqlalchemy import text

TABLES = {
    "dbp_builder_projects": [
        ("id", "VARCHAR(36) PRIMARY KEY"),
        ("tenant_id", "VARCHAR(100) NOT NULL"),
        ("name", "VARCHAR(200) NOT NULL"),
        ("source_composer_session_id", "VARCHAR(36)"),
        ("status", "VARCHAR(30) NOT NULL DEFAULT 'draft'"),
        ("draft_config", "JSONB NOT NULL DEFAULT '{}'"),
        ("published_version_id", "VARCHAR(36)"),
        ("created_at", "TIMESTAMP DEFAULT NOW()"),
        ("updated_at", "TIMESTAMP DEFAULT NOW()"),
    ],
    "dbp_builder_versions": [
        ("id", "VARCHAR(36) PRIMARY KEY"),
        ("tenant_id", "VARCHAR(100) NOT NULL"),
        ("project_id", "VARCHAR(36) NOT NULL"),
        ("version_number", "INTEGER NOT NULL"),
        ("config", "JSONB NOT NULL"),
        ("change_summary", "TEXT"),
        ("published_by", "VARCHAR(100)"),
        ("published_at", "TIMESTAMP DEFAULT NOW()"),
        ("is_active", "BOOLEAN NOT NULL DEFAULT false"),
    ],
}

INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_bproj_tenant ON dbp_builder_projects(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_bproj_status ON dbp_builder_projects(status)",
    "CREATE INDEX IF NOT EXISTS idx_bver_project ON dbp_builder_versions(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_bver_tenant ON dbp_builder_versions(tenant_id)",
]


def migrate():
    with engine.begin() as conn:
        for tbl, cols in TABLES.items():
            col_sql = ", ".join(f"{c[0]} {c[1]}" for c in cols)
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {tbl} ({col_sql})"))
            print(f"  [OK] {tbl}")
        for idx in INDICES:
            conn.execute(text(idx))
        print("  [OK] Indices")


if __name__ == "__main__":
    print("=" * 60)
    print("  P54 MIGRATION — Self-Service ERP Builder")
    print("=" * 60)
    migrate()
    print("  DONE")
