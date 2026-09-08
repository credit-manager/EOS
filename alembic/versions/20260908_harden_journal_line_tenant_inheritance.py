"""Enforce journal-line tenant ownership from journal entries and accounts.

Journal lines are children of both journal entries and accounts. The tenant is
therefore derived from those authoritative parents rather than being supplied
independently by every caller. This closes the accounting integrity gap exposed
by the commercial-cycle regression when the tenant_id column became NOT NULL.

Revision ID: 20260908_harden_journal_line_tenant_inheritance
Revises: 20260906_harden_inventory_tenant_scope
"""

from alembic import op

revision = "20260908_harden_journal_line_tenant_inheritance"
down_revision = "20260906_harden_inventory_tenant_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION eos_journal_line_set_tenant_id()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            entry_tenant text;
            account_tenant text;
        BEGIN
            SELECT tenant_id::text
              INTO entry_tenant
              FROM dbp_journal_entries
             WHERE id = NEW.journal_entry_id;

            IF entry_tenant IS NULL THEN
                RAISE EXCEPTION 'journal entry tenant context is required for journal-line writes';
            END IF;

            SELECT tenant_id::text
              INTO account_tenant
              FROM dbp_accounts
             WHERE id = NEW.account_id;

            IF account_tenant IS NULL THEN
                RAISE EXCEPTION 'account tenant context is required for journal-line writes';
            END IF;

            IF account_tenant <> entry_tenant THEN
                RAISE EXCEPTION 'journal line account does not belong to journal entry tenant';
            END IF;

            NEW.tenant_id := entry_tenant;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_dbp_journal_lines_tenant_id ON dbp_journal_lines")
    op.execute(
        """
        CREATE TRIGGER trg_dbp_journal_lines_tenant_id
        BEFORE INSERT OR UPDATE OF journal_entry_id, account_id, tenant_id
        ON dbp_journal_lines
        FOR EACH ROW
        EXECUTE FUNCTION eos_journal_line_set_tenant_id()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_dbp_journal_lines_tenant_id ON dbp_journal_lines")
    op.execute("DROP FUNCTION IF EXISTS eos_journal_line_set_tenant_id()")
