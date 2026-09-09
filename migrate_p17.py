"""
P17 Workflow & Approval — Migration
"""
from sqlalchemy import text
from database import engine


def migrate_p17():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_workflow_definitions (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                code VARCHAR(100) NOT NULL,
                name_en VARCHAR(255) NOT NULL,
                name_ar VARCHAR(255),
                description TEXT,
                entity_code VARCHAR(100) NOT NULL,
                is_active BOOLEAN DEFAULT false,
                is_published BOOLEAN DEFAULT false,
                sla_hours INTEGER,
                escalation_hours INTEGER,
                config JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            )
        """))
        print("  [OK] dbp_workflow_definitions")

        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_wfdef_code "
            "ON dbp_workflow_definitions(code)"
        ))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_workflow_states (
                id VARCHAR(36) PRIMARY KEY,
                workflow_id VARCHAR(36) NOT NULL REFERENCES dbp_workflow_definitions(id) ON DELETE CASCADE,
                code VARCHAR(100) NOT NULL,
                name_en VARCHAR(255) NOT NULL,
                name_ar VARCHAR(255),
                state_type VARCHAR(20) NOT NULL DEFAULT 'pending',
                is_initial BOOLEAN DEFAULT false,
                is_final BOOLEAN DEFAULT false,
                allowed_roles JSONB DEFAULT '[]',
                config JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("  [OK] dbp_workflow_states")

        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_wfstate_workflow "
            "ON dbp_workflow_states(workflow_id)"
        ))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_workflow_transitions (
                id VARCHAR(36) PRIMARY KEY,
                workflow_id VARCHAR(36) NOT NULL REFERENCES dbp_workflow_definitions(id) ON DELETE CASCADE,
                code VARCHAR(100) NOT NULL,
                name_en VARCHAR(255) NOT NULL,
                from_state_id VARCHAR(36) NOT NULL REFERENCES dbp_workflow_states(id) ON DELETE CASCADE,
                to_state_id VARCHAR(36) NOT NULL REFERENCES dbp_workflow_states(id) ON DELETE CASCADE,
                action VARCHAR(50) NOT NULL DEFAULT 'approve',
                required_roles JSONB DEFAULT '[]',
                conditions JSONB DEFAULT '[]',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("  [OK] dbp_workflow_transitions")

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_workflow_instances (
                id VARCHAR(36) PRIMARY KEY,
                tenant_id VARCHAR(36),
                workflow_id VARCHAR(36) NOT NULL REFERENCES dbp_workflow_definitions(id) ON DELETE CASCADE,
                entity_code VARCHAR(100) NOT NULL,
                record_id VARCHAR(36) NOT NULL,
                current_state_id VARCHAR(36) REFERENCES dbp_workflow_states(id) ON DELETE SET NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                initiated_by VARCHAR(100) NOT NULL,
                priority INTEGER DEFAULT 0,
                due_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                wf_metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            )
        """))
        print("  [OK] dbp_workflow_instances")

        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_wfinst_tenant "
            "ON dbp_workflow_instances(tenant_id)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_wfinst_record "
            "ON dbp_workflow_instances(entity_code, record_id)"
        ))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dbp_workflow_actions (
                id VARCHAR(36) PRIMARY KEY,
                instance_id VARCHAR(36) NOT NULL REFERENCES dbp_workflow_instances(id) ON DELETE CASCADE,
                transition_id VARCHAR(36) REFERENCES dbp_workflow_transitions(id) ON DELETE SET NULL,
                action VARCHAR(50) NOT NULL,
                from_state VARCHAR(100),
                to_state VARCHAR(100),
                performed_by VARCHAR(100) NOT NULL,
                comment TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        print("  [OK] dbp_workflow_actions")

        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_wfact_instance "
            "ON dbp_workflow_actions(instance_id)"
        ))

    print("\nP17 migration complete.")


if __name__ == "__main__":
    print("Running P17 migration...")
    migrate_p17()
