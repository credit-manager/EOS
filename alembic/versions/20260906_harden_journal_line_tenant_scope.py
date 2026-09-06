"""Harden journal-line tenant isolation for existing databases.

Revision ID: 20260906_journal_line_tenant
Revises: 20260905_restore_journal_tables
"""
from alembic import op

revision = "20260906_journal_line_tenant"
down_revision = "20260905_restore_journal_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE dbp_journal_lines
        ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(255)
    """)
    op.execute("""
        UPDATE dbp_journal_lines l
        SET tenant_id = e.tenant_id
        FROM dbp_journal_entries e
        WHERE l.journal_entry_id = e.id
          AND l.tenant_id IS NULL
    """)
    op.execute("""
        ALTER TABLE dbp_journal_lines
        ALTER COLUMN tenant_id SET NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_dbp_journal_lines_tenant_entry
        ON dbp_journal_lines (tenant_id, journal_entry_id)
    """)
    op.execute("ALTER TABLE dbp_journal_lines ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dbp_journal_lines FORCE ROW LEVEL SECURITY")
    op.execute('DROP POLICY IF EXISTS "tenant_isolation_dbp_journal_lines" ON dbp_journal_lines')
    op.execute('''
        CREATE POLICY "tenant_isolation_dbp_journal_lines" ON dbp_journal_lines
        USING (tenant_id::text = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
    ''')


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "tenant_isolation_dbp_journal_lines" ON dbp_journal_lines')
    op.execute("ALTER TABLE dbp_journal_lines NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dbp_journal_lines DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS ix_dbp_journal_lines_tenant_entry")
    op.execute("ALTER TABLE dbp_journal_lines DROP COLUMN IF EXISTS tenant_id")
