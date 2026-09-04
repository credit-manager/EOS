"""Tenant-safe accounting references.

Prevents a journal line from referencing an account or journal entry belonging
to a different tenant, including writes made outside the API layer.
"""
from alembic import op

revision = "20260901_tenant_safe_accounting"
down_revision = "20260902_accounting_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE OR REPLACE FUNCTION eos_validate_journal_line_tenant()
    RETURNS trigger AS $$
    DECLARE
        journal_tenant text;
        journal_company text;
        account_tenant text;
        account_company text;
    BEGIN
        SELECT tenant_id, company_id INTO journal_tenant, journal_company
        FROM dbp_journal_entries WHERE id = NEW.journal_entry_id;
        IF journal_tenant IS NULL THEN
            RAISE EXCEPTION 'Journal entry does not exist: %', NEW.journal_entry_id;
        END IF;

        SELECT tenant_id, company_id INTO account_tenant, account_company
        FROM dbp_accounts WHERE id = NEW.account_id;
        IF account_tenant IS NULL THEN
            RAISE EXCEPTION 'Account does not exist: %', NEW.account_id;
        END IF;

        IF journal_tenant <> account_tenant OR journal_company <> account_company THEN
            RAISE EXCEPTION 'Cross-tenant/company accounting reference denied';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_eos_journal_line_tenant
    BEFORE INSERT OR UPDATE OF journal_entry_id, account_id
    ON dbp_journal_lines
    FOR EACH ROW EXECUTE FUNCTION eos_validate_journal_line_tenant();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION eos_validate_journal_entry_tenant()
    RETURNS trigger AS $$
    DECLARE line_tenant text;
    DECLARE line_company text;
    BEGIN
        IF OLD.tenant_id IS DISTINCT FROM NEW.tenant_id
           OR OLD.company_id IS DISTINCT FROM NEW.company_id THEN
            SELECT je.tenant_id, je.company_id INTO line_tenant, line_company
            FROM dbp_journal_lines jl
            JOIN dbp_journal_entries je ON je.id = jl.journal_entry_id
            WHERE jl.journal_entry_id = NEW.id LIMIT 1;
            IF line_tenant IS NOT NULL AND
               (line_tenant IS DISTINCT FROM NEW.tenant_id OR line_company IS DISTINCT FROM NEW.company_id) THEN
                RAISE EXCEPTION 'Cannot move journal entry across tenants/companies';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_eos_journal_entry_tenant
    BEFORE UPDATE OF tenant_id, company_id
    ON dbp_journal_entries
    FOR EACH ROW EXECUTE FUNCTION eos_validate_journal_entry_tenant();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_eos_journal_line_tenant ON dbp_journal_lines")
    op.execute("DROP TRIGGER IF EXISTS trg_eos_journal_entry_tenant ON dbp_journal_entries")
    op.execute("DROP FUNCTION IF EXISTS eos_validate_journal_line_tenant()")
    op.execute("DROP FUNCTION IF EXISTS eos_validate_journal_entry_tenant()")
