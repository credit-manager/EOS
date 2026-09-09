"""
P71.5 Dynamic Customization Layer — Database Schema
=====================================================
Custom fields, modules, and workflows for no-code extension.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import engine

TABLES = [
    # ─── Custom Fields ─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_custom_fields (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        entity_type VARCHAR(100) NOT NULL,
        field_code VARCHAR(100) NOT NULL,
        field_label VARCHAR(200) NOT NULL,
        field_type VARCHAR(50) NOT NULL,
        is_required BOOLEAN DEFAULT FALSE,
        default_value TEXT,
        enum_values TEXT,
        sort_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Custom Field Values ───────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_custom_field_values (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        entity_type VARCHAR(100) NOT NULL,
        entity_id VARCHAR(36) NOT NULL,
        field_id VARCHAR(36) NOT NULL,
        field_value TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Custom Modules ────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_custom_modules (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        module_code VARCHAR(100) NOT NULL,
        module_name VARCHAR(200) NOT NULL,
        description TEXT,
        icon VARCHAR(50),
        color VARCHAR(20),
        is_active BOOLEAN DEFAULT TRUE,
        config JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Custom Module Fields ──────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_custom_module_fields (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        module_id VARCHAR(36) NOT NULL,
        field_code VARCHAR(100) NOT NULL,
        field_label VARCHAR(200) NOT NULL,
        field_type VARCHAR(50) NOT NULL,
        is_required BOOLEAN DEFAULT FALSE,
        is_primary BOOLEAN DEFAULT FALSE,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Custom Module Records ─────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_custom_module_records (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        module_id VARCHAR(36) NOT NULL,
        record_code VARCHAR(100),
        data JSONB NOT NULL DEFAULT '{}',
        status VARCHAR(30) DEFAULT 'active',
        created_by VARCHAR(36),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Custom Workflows ──────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_custom_workflows (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        workflow_name VARCHAR(200) NOT NULL,
        entity_type VARCHAR(100) NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Workflow Steps ────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_workflow_steps (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        workflow_id VARCHAR(36) NOT NULL,
        step_order INTEGER NOT NULL,
        step_name VARCHAR(200) NOT NULL,
        action_type VARCHAR(50) NOT NULL,
        action_config JSONB,
        next_step_on_success INTEGER,
        next_step_on_failure INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,

    # ─── Workflow Instances ────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_workflow_instances (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        workflow_id VARCHAR(36) NOT NULL,
        entity_type VARCHAR(100) NOT NULL,
        entity_id VARCHAR(36) NOT NULL,
        current_step INTEGER DEFAULT 1,
        status VARCHAR(30) DEFAULT 'running',
        started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE
    )
    """,

    # ─── Workflow Log ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS dbp_workflow_log (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(36) NOT NULL,
        instance_id VARCHAR(36) NOT NULL,
        step_order INTEGER NOT NULL,
        action VARCHAR(50) NOT NULL,
        result VARCHAR(30) NOT NULL,
        actor_id VARCHAR(36),
        details TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """,
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_cf_tenant_entity ON dbp_custom_fields(tenant_id, entity_type)",
    "CREATE INDEX IF NOT EXISTS idx_cfv_entity ON dbp_custom_field_values(entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_cfv_field ON dbp_custom_field_values(field_id)",
    "CREATE INDEX IF NOT EXISTS idx_cm_tenant ON dbp_custom_modules(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_cmf_module ON dbp_custom_module_fields(module_id)",
    "CREATE INDEX IF NOT EXISTS idx_cmr_module ON dbp_custom_module_records(module_id)",
    "CREATE INDEX IF NOT EXISTS idx_cw_tenant ON dbp_custom_workflows(tenant_id)",
    "CREATE INDEX IF NOT EXISTS idx_ws_workflow ON dbp_workflow_steps(workflow_id)",
    "CREATE INDEX IF NOT EXISTS idx_wi_entity ON dbp_workflow_instances(entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_wl_instance ON dbp_workflow_log(instance_id)",
]

UNIQUES = [
    "ALTER TABLE dbp_custom_fields ADD CONSTRAINT uq_custom_field UNIQUE (tenant_id, entity_type, field_code)",
    "ALTER TABLE dbp_custom_modules ADD CONSTRAINT uq_custom_module UNIQUE (tenant_id, module_code)",
]

CHECKS = [
    "ALTER TABLE dbp_custom_fields ADD CONSTRAINT chk_cf_field_type CHECK (field_type IN ('text','number','date','boolean','select','multiselect','email','phone','url','currency','textarea'))",
    "ALTER TABLE dbp_workflow_instances ADD CONSTRAINT chk_wi_status CHECK (status IN ('running','completed','failed','cancelled','paused'))",
    "ALTER TABLE dbp_custom_module_records ADD CONSTRAINT chk_cmr_status CHECK (status IN ('active','archived','deleted'))",
]


def migrate():
    with engine.begin() as conn:
        created = sum(1 for sql in TABLES if not _exec(conn, sql.strip()))
        idx = sum(1 for sql in INDEXES if not _exec(conn, sql))
        uq = sum(1 for sql in UNIQUES if not _exec(conn, sql))
        chk = sum(1 for sql in CHECKS if not _exec(conn, sql))
    print(f"P71.5 Customization Schema: {created} tables, {idx} indexes, {uq} uniques, {chk} checks")


def _exec(conn, sql):
    try:
        conn.execute(text(sql))
        return False
    except Exception:
        return True


if __name__ == "__main__":
    migrate()
