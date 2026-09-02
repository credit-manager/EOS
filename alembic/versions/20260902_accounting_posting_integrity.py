"""Enforce journal posting invariants at the PostgreSQL boundary.

Draft journal entries may be assembled over multiple statements. A journal can
only transition to posted when it has at least two lines and aggregate debits
equal aggregate credits. Posted entries and their lines are immutable; callers
must create a reversal entry instead.
"""
from alembic import op

revision = "20260902_accounting_posting_integrity"
down_revision = "20260902_tenant_rls_policies"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE OR REPLACE FUNCTION eos_validate_journal_posting()
    RETURNS trigger AS $$
    DECLARE
        line_count integer;
        total_debit numeric;
        total_credit numeric;
    BEGIN
        IF NEW.status = 'posted' OR NEW.is_posted IS TRUE THEN
            SELECT COUNT(*), COALESCE(SUM(debit), 0), COALESCE(SUM(credit), 0)
              INTO line_count, total_debit, total_credit
            FROM dbp_journal_lines
            WHERE journal_entry_id = NEW.id;

            IF line_count < 2 THEN
                RAISE EXCEPTION 'Posted journal entry must contain at least two lines';
            END IF;

            IF total_debit <> total_credit THEN
                RAISE EXCEPTION
                    'Posted journal entry is not balanced: debit=% credit=%',
                    total_debit, total_credit;
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_eos_validate_journal_posting ON dbp_journal_entries;
    CREATE CONSTRAINT TRIGGER trg_eos_validate_journal_posting
    AFTER INSERT OR UPDATE OF status, is_posted
    ON dbp_journal_entries
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION eos_validate_journal_posting();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION eos_block_posted_journal_line_mutation()
    RETURNS trigger AS $$
    DECLARE
        posted boolean;
    BEGIN
        SELECT (status = 'posted' OR is_posted IS TRUE)
          INTO posted
        FROM dbp_journal_entries
        WHERE id = COALESCE(OLD.journal_entry_id, NEW.journal_entry_id);

        IF COALESCE(posted, FALSE) THEN
            RAISE EXCEPTION 'Posted journal lines are immutable; create a reversal entry';
        END IF;

        RETURN COALESCE(NEW, OLD);
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_eos_block_posted_journal_line_mutation ON dbp_journal_lines;
    CREATE TRIGGER trg_eos_block_posted_journal_line_mutation
    BEFORE UPDATE OR DELETE
    ON dbp_journal_lines
    FOR EACH ROW EXECUTE FUNCTION eos_block_posted_journal_line_mutation();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION eos_block_posted_journal_entry_mutation()
    RETURNS trigger AS $$
    BEGIN
        IF OLD.status = 'posted' OR OLD.is_posted IS TRUE THEN
            RAISE EXCEPTION 'Posted journal entries are immutable; create a reversal entry';
        END IF;
        RETURN COALESCE(NEW, OLD);
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_eos_block_posted_journal_entry_mutation ON dbp_journal_entries;
    CREATE TRIGGER trg_eos_block_posted_journal_entry_mutation
    BEFORE UPDATE OR DELETE
    ON dbp_journal_entries
    FOR EACH ROW EXECUTE FUNCTION eos_block_posted_journal_entry_mutation();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_eos_validate_journal_posting ON dbp_journal_entries")
    op.execute("DROP TRIGGER IF EXISTS trg_eos_block_posted_journal_line_mutation ON dbp_journal_lines")
    op.execute("DROP TRIGGER IF EXISTS trg_eos_block_posted_journal_entry_mutation ON dbp_journal_entries")
    op.execute("DROP FUNCTION IF EXISTS eos_validate_journal_posting()")
    op.execute("DROP FUNCTION IF EXISTS eos_block_posted_journal_line_mutation()")
    op.execute("DROP FUNCTION IF EXISTS eos_block_posted_journal_entry_mutation()")
