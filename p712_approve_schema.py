"""
P71.2 Universal Approval Engine — Database Schema
===================================================
Configurable multi-step approval chains. Any module, any industry.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import engine

TABLES = [
    # ─── Approval Chains (templates) ───────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_approve_chains (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        chain_name VARCHAR(200) NOT NULL,
        source_module VARCHAR(50) NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Approval Steps (within a chain) ───────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_approve_steps (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        chain_id VARCHAR(36) NOT NULL,
        step_order INTEGER NOT NULL,
        step_name VARCHAR(200) NOT NULL,
        approver_type VARCHAR(30) NOT NULL,
        approver_value VARCHAR(200),
        min_approvals INTEGER DEFAULT 1,
        is_optional BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Approval Requests (active instances) ──────────
    """
    CREATE TABLE IF NOT EXISTS dbp_approve_requests (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        chain_id VARCHAR(36),
        source_module VARCHAR(50) NOT NULL,
        source_id VARCHAR(36) NOT NULL,
        title VARCHAR(500) NOT NULL,
        description TEXT,
        requested_by VARCHAR(36) NOT NULL,
        current_step INTEGER DEFAULT 1,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE
    )
    """,

    # ─── Approval Actions (individual decisions) ───────
    """
    CREATE TABLE IF NOT EXISTS dbp_approve_actions (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        request_id VARCHAR(36) NOT NULL,
        step_order INTEGER NOT NULL,
        approver_id VARCHAR(36) NOT NULL,
        decision VARCHAR(20) NOT NULL,
        comment TEXT,
        decided_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Approval Log (full audit trail) ───────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_approve_log (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        request_id VARCHAR(36) NOT NULL,
        action VARCHAR(50) NOT NULL,
        actor_id VARCHAR(36) NOT NULL,
        details TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_approve_chains_tenant ON dbp_approve_chains(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_approve_chains_module ON dbp_approve_chains(tenant_id, source_module)",
    "CREATE INDEX IF NOT EXISTS idx_approve_steps_chain ON dbp_approve_steps(chain_id)",
    "CREATE INDEX IF NOT EXISTS idx_approve_requests_tenant ON dbp_approve_requests(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_approve_requests_status ON dbp_approve_requests(tenant_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_approve_requests_source ON dbp_approve_requests(source_module, source_id)",
    "CREATE INDEX IF NOT EXISTS idx_approve_actions_request ON dbp_approve_actions(request_id)",
    "CREATE INDEX IF NOT EXISTS idx_approve_log_request ON dbp_approve_log(request_id)",
]

UNIQUES = [
    "ALTER TABLE dbp_approve_chains ADD CONSTRAINT uq_approve_chain UNIQUE (tenant_id, chain_name)",
]

CHECKS = [
    "ALTER TABLE dbp_approve_steps ADD CONSTRAINT chk_approve_step_type CHECK (approver_type IN ('user','role','manager','self_manager','any_role'))",
    "ALTER TABLE dbp_approve_requests ADD CONSTRAINT chk_approve_request_status CHECK (status IN ('pending','approved','rejected','cancelled','expired'))",
    "ALTER TABLE dbp_approve_actions ADD CONSTRAINT chk_approve_action_decision CHECK (decision IN ('approved','rejected','escalated','delegated'))",
]

DEFAULTS = [
    "ALTER TABLE dbp_approve_chains ALTER COLUMN is_active SET DEFAULT TRUE",
    "ALTER TABLE dbp_approve_steps ALTER COLUMN step_order SET DEFAULT 1",
    "ALTER TABLE dbp_approve_steps ALTER COLUMN min_approvals SET DEFAULT 1",
    "ALTER TABLE dbp_approve_requests ALTER COLUMN current_step SET DEFAULT 1",
    "ALTER TABLE dbp_approve_requests ALTER COLUMN status SET DEFAULT 'pending'",
]

def migrate():
    with engine.begin() as conn:
        created = sum(1 for sql in TABLES if not _exec(conn, sql.strip()))
        idx = sum(1 for sql in INDEXES if not _exec(conn, sql))
        uq = sum(1 for sql in UNIQUES if not _exec(conn, sql))
        chk = sum(1 for sql in CHECKS if not _exec(conn, sql))
        df = sum(1 for sql in DEFAULTS if not _exec(conn, sql))
    print(f"P71.2 Approval Engine Schema: {created} tables, {idx} indexes, {uq} uniques, {chk} checks, {df} defaults")


def _exec(conn, sql):
    try:
        conn.execute(text(sql))
        return False
    except Exception:
        return True


if __name__ == "__main__":
    migrate()
