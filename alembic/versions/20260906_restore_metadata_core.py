"""Restore the metadata tables required by the dynamic ERP builder.

The application models and BuilderEngine depend on these tables, but a clean
migration chain previously did not create them. Keep the metadata model
available before the platform attempts to publish custom ERP entities.
"""
from alembic import op

revision = "20260906_restore_metadata_core"
down_revision = "20260906_harden_journal_line_tenant_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_entities (
            id VARCHAR(36) PRIMARY KEY,
            tenant_id VARCHAR(36),
            code VARCHAR(100) NOT NULL,
            name_en VARCHAR(255) NOT NULL,
            name_ar VARCHAR(255),
            faculty VARCHAR(50) NOT NULL,
            table_mapping VARCHAR(100),
            is_system BOOLEAN NOT NULL DEFAULT FALSE,
            metadata_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_dbp_entities_tenant_code
        ON dbp_entities (tenant_id, code)
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_dbp_entities_global_code
        ON dbp_entities (code) WHERE tenant_id IS NULL
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_entities_tenant_id ON dbp_entities (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_entities_code ON dbp_entities (code)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_fields (
            id VARCHAR(36) PRIMARY KEY,
            entity_id VARCHAR(36) NOT NULL REFERENCES dbp_entities(id) ON DELETE CASCADE,
            code VARCHAR(100) NOT NULL,
            label_en VARCHAR(255),
            label_ar VARCHAR(255),
            field_type VARCHAR(50) NOT NULL,
            is_required BOOLEAN NOT NULL DEFAULT FALSE,
            ui_config JSONB NOT NULL DEFAULT '{}'::jsonb,
            enum_values JSONB NOT NULL DEFAULT '[]'::jsonb,
            is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
            writable_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
            visible_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
            validation_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_dbp_fields_entity_code UNIQUE (entity_id, code)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_fields_entity_id ON dbp_fields (entity_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_relationships (
            id VARCHAR(36) PRIMARY KEY,
            entity_id VARCHAR(36) NOT NULL REFERENCES dbp_entities(id) ON DELETE CASCADE,
            code VARCHAR(100) NOT NULL,
            target_entity_code VARCHAR(100) NOT NULL,
            relationship_type VARCHAR(20) NOT NULL DEFAULT 'one_to_many',
            source_column VARCHAR(100) NOT NULL,
            target_column VARCHAR(100) NOT NULL DEFAULT 'id',
            lookup_field VARCHAR(100) DEFAULT 'name_en',
            is_required BOOLEAN NOT NULL DEFAULT FALSE,
            tenant_scope BOOLEAN NOT NULL DEFAULT TRUE,
            on_delete VARCHAR(20) DEFAULT 'restrict',
            junction_table VARCHAR(100) DEFAULT '',
            junction_source_col VARCHAR(100) DEFAULT '',
            junction_target_col VARCHAR(100) DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_dbp_relationships_entity_code UNIQUE (entity_id, code)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_relationships_entity_id ON dbp_relationships (entity_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_entity_versions (
            id VARCHAR(36) PRIMARY KEY,
            entity_id VARCHAR(36) NOT NULL REFERENCES dbp_entities(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            schema_snapshot JSONB NOT NULL,
            change_type VARCHAR(50) NOT NULL,
            changed_by VARCHAR(100) NOT NULL,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            change_summary TEXT,
            CONSTRAINT uq_dbp_entity_versions_entity_version UNIQUE (entity_id, version_number)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_entity_versions_entity_id ON dbp_entity_versions (entity_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_row_rules (
            id VARCHAR(36) PRIMARY KEY,
            entity_id VARCHAR(36) NOT NULL REFERENCES dbp_entities(id) ON DELETE CASCADE,
            filter_column VARCHAR(100) NOT NULL,
            filter_type VARCHAR(20) NOT NULL DEFAULT 'equals',
            filter_value VARCHAR(500),
            allowed_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
            priority INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dbp_row_rules_entity_id ON dbp_row_rules (entity_id)")

    op.execute("ALTER TABLE dbp_entities ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dbp_entities FORCE ROW LEVEL SECURITY")
    op.execute('DROP POLICY IF EXISTS "tenant_isolation_dbp_entities" ON dbp_entities')
    op.execute('''
        CREATE POLICY "tenant_isolation_dbp_entities" ON dbp_entities
        USING (tenant_id::text = current_setting('app.tenant_id', true) OR tenant_id IS NULL)
        WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true) OR tenant_id IS NULL)
    ''')


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "tenant_isolation_dbp_entities" ON dbp_entities')
    op.execute("ALTER TABLE dbp_entities NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dbp_entities DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TABLE IF EXISTS dbp_row_rules")
    op.execute("DROP TABLE IF EXISTS dbp_entity_versions")
    op.execute("DROP TABLE IF EXISTS dbp_relationships")
    op.execute("DROP TABLE IF EXISTS dbp_fields")
    op.execute("DROP TABLE IF EXISTS dbp_entities")
