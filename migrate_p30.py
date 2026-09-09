"""
P30 Migration — Document Management
  - dbp_doc_folders
  - dbp_documents
  - dbp_document_versions
  - dbp_document_tags
"""
from sqlalchemy import text
from database import engine

TABLES = {
    "dbp_doc_folders": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "name": "VARCHAR(255) NOT NULL",
        "parent_id": "VARCHAR(36)",
        "description": "TEXT",
        "created_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_documents": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "company_id": "VARCHAR(36) NOT NULL",
        "folder_id": "VARCHAR(36)",
        "title": "VARCHAR(500) NOT NULL",
        "description": "TEXT",
        "doc_type": "VARCHAR(50)",
        "file_name": "VARCHAR(500)",
        "file_size": "BIGINT DEFAULT 0",
        "mime_type": "VARCHAR(100)",
        "reference_type": "VARCHAR(50)",
        "reference_id": "VARCHAR(36)",
        "status": "VARCHAR(20) DEFAULT 'active'",
        "access_level": "VARCHAR(20) DEFAULT 'private'",
        "created_by": "VARCHAR(100)",
        "updated_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_document_versions": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "document_id": "VARCHAR(36) NOT NULL",
        "version_number": "INT NOT NULL",
        "file_name": "VARCHAR(500)",
        "file_size": "BIGINT DEFAULT 0",
        "change_notes": "TEXT",
        "uploaded_by": "VARCHAR(100)",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
    "dbp_document_tags": {
        "id": "VARCHAR(36) PRIMARY KEY",
        "tenant_id": "VARCHAR(36) NOT NULL",
        "document_id": "VARCHAR(36) NOT NULL",
        "tag": "VARCHAR(100) NOT NULL",
        "created_at": "TIMESTAMPTZ DEFAULT NOW()",
    },
}

INDEXES = {
    "dbp_doc_folders": ["tenant_id", "company_id", "parent_id"],
    "dbp_documents": ["tenant_id", "company_id", "folder_id", "doc_type", "status", "reference_type", "reference_id"],
    "dbp_document_versions": ["document_id"],
    "dbp_document_tags": ["document_id", "tag"],
}

if __name__ == "__main__":
    print("Running P30 migration...")
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
    print("P30 migration complete.")
