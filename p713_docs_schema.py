"""
P71.3 Universal Document Manager — Database Schema
====================================================
File metadata, folders, versions, and cross-module linking.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import engine

TABLES = [
    # ─── Folders ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_doc_folders (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        parent_id VARCHAR(36),
        folder_name VARCHAR(200) NOT NULL,
        description TEXT,
        source_module VARCHAR(50),
        created_by VARCHAR(36) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Files ─────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_doc_files (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        folder_id VARCHAR(36),
        file_name VARCHAR(500) NOT NULL,
        original_name VARCHAR(500) NOT NULL,
        mime_type VARCHAR(100),
        file_size BIGINT DEFAULT 0,
        storage_path VARCHAR(1000),
        description TEXT,
        tags TEXT,
        source_module VARCHAR(50),
        source_id VARCHAR(36),
        uploaded_by VARCHAR(36) NOT NULL,
        is_archived BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Versions ──────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_doc_versions (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        file_id VARCHAR(36) NOT NULL,
        version_number INTEGER NOT NULL,
        file_name VARCHAR(500) NOT NULL,
        storage_path VARCHAR(1000),
        file_size BIGINT DEFAULT 0,
        uploaded_by VARCHAR(36) NOT NULL,
        change_notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Shares ────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_doc_shares (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        file_id VARCHAR(36) NOT NULL,
        shared_with_type VARCHAR(30) NOT NULL,
        shared_with_value VARCHAR(200) NOT NULL,
        permission VARCHAR(20) DEFAULT 'view',
        shared_by VARCHAR(36) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Activity Log ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_doc_log (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        file_id VARCHAR(36),
        action VARCHAR(50) NOT NULL,
        actor_id VARCHAR(36) NOT NULL,
        details TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_doc_folders_tenant ON dbp_doc_folders(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_doc_folders_parent ON dbp_doc_folders(parent_id)",
    "CREATE INDEX IF NOT EXISTS idx_doc_folders_module ON dbp_doc_folders(source_module)",
    "CREATE INDEX IF NOT EXISTS idx_doc_files_tenant ON dbp_doc_files(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_doc_files_folder ON dbp_doc_files(folder_id)",
    "CREATE INDEX IF NOT EXISTS idx_doc_files_source ON dbp_doc_files(source_module, source_id)",
    "CREATE INDEX IF NOT EXISTS idx_doc_files_tags ON dbp_doc_files USING GIN (to_tsvector('english', COALESCE(tags, '')))",
    "CREATE INDEX IF NOT EXISTS idx_doc_versions_file ON dbp_doc_versions(file_id)",
    "CREATE INDEX IF NOT EXISTS idx_doc_shares_file ON dbp_doc_shares(file_id)",
    "CREATE INDEX IF NOT EXISTS idx_doc_log_file ON dbp_doc_log(file_id)",
]

CHECKS = [
    "ALTER TABLE dbp_doc_shares ADD CONSTRAINT chk_doc_share_type CHECK (shared_with_type IN ('user','role','group','all'))",
    "ALTER TABLE dbp_doc_shares ADD CONSTRAINT chk_doc_share_perm CHECK (permission IN ('view','edit','admin'))",
]


def migrate():
    with engine.begin() as conn:
        created = sum(1 for sql in TABLES if not _exec(conn, sql.strip()))
        idx = 0
        for sql in INDEXES:
            try:
                conn.execute(text(sql))
            except Exception:
                idx += 1
        chk = sum(1 for sql in CHECKS if not _exec(conn, sql))
    print(f"P71.3 Document Manager Schema: {created} tables, {idx} skipped indexes, {chk} skipped checks")


def _exec(conn, sql):
    try:
        conn.execute(text(sql))
        return False
    except Exception:
        return True


if __name__ == "__main__":
    migrate()
