"""Database-enforced integrity controls for the canonical EOS v2 ledger."""
from alembic import op

revision = "20260906_accounting_integrity"
down_revision = "20260906_harden_inventory_tenant_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The historical canonical-schema replay can remove this compatibility
    # object although the production authentication surface still requires it.
    op.execute("""
        CREATE TABLE IF NOT EXISTS dbp_companies (
            id UUID PRIMARY KEY,
            tenant_id VARCHAR(255) NOT NULL,
            code VARCHAR(100) NOT NULL,
            name_en VARCHAR(255) NOT NULL,
            name_ar VARCHAR(255) NOT NULL
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_dbp_companies_tenant_code
        ON dbp_companies (tenant_id, code)
    """)

    # The dedicated V2 ledger is provisioned by the V2 migration runner. Keep
    # the canonical Alembic chain safe when that optional schema is absent.
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('eos_v2_accounts') IS NULL
               OR to_regclass('eos_v2_journal_entries') IS NULL
               OR to_regclass('eos_v2_journal_lines') IS NULL THEN
                RETURN;
            END IF;

            BEGIN
                ALTER TABLE eos_v2_accounts
                    ADD CONSTRAINT uq_eos_v2_accounts_tenant_id_id
                    UNIQUE (tenant_id, id);
            EXCEPTION WHEN duplicate_object THEN NULL;
            END;

            BEGIN
                ALTER TABLE eos_v2_journal_entries
                    ADD CONSTRAINT uq_eos_v2_journal_entries_tenant_id_id
                    UNIQUE (tenant_id, id);
            EXCEPTION WHEN duplicate_object THEN NULL;
            END;

            BEGIN
                ALTER TABLE eos_v2_journal_lines
                    ADD CONSTRAINT fk_eos_v2_lines_tenant_entry
                    FOREIGN KEY (tenant_id, journal_entry_id)
                    REFERENCES eos_v2_journal_entries (tenant_id, id)
                    ON DELETE CASCADE;
            EXCEPTION WHEN duplicate_object THEN NULL;
            END;

            BEGIN
                ALTER TABLE eos_v2_journal_lines
                    ADD CONSTRAINT fk_eos_v2_lines_tenant_account
                    FOREIGN KEY (tenant_id, account_id)
                    REFERENCES eos_v2_accounts (tenant_id, id);
            EXCEPTION WHEN duplicate_object THEN NULL;
            END;

            BEGIN
                ALTER TABLE eos_v2_journal_lines
                    ADD CONSTRAINT ck_eos_v2_journal_lines_exclusive_side
                    CHECK (NOT (debit > 0 AND credit > 0));
            EXCEPTION WHEN duplicate_object THEN NULL;
            END;

            CREATE OR REPLACE FUNCTION eos_v2_assert_journal_balanced()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $fn$
            DECLARE
                debit_total NUMERIC;
                credit_total NUMERIC;
                line_count INTEGER;
            BEGIN
                SELECT COUNT(*), COALESCE(SUM(debit), 0), COALESCE(SUM(credit), 0)
                  INTO line_count, debit_total, credit_total
                  FROM eos_v2_journal_lines
                 WHERE journal_entry_id = NEW.journal_entry_id
                   AND tenant_id = NEW.tenant_id;
                IF line_count < 2 OR debit_total <> credit_total THEN
                    RAISE EXCEPTION 'Journal entry % is invalid: lines=% debit=% credit=%',
                        NEW.journal_entry_id, line_count, debit_total, credit_total;
                END IF;
                RETURN NEW;
            END;
            $fn$;

            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'eos_v2_journal_lines_balanced'
            ) THEN
                CREATE CONSTRAINT TRIGGER eos_v2_journal_lines_balanced
                AFTER INSERT OR UPDATE ON eos_v2_journal_lines
                DEFERRABLE INITIALLY DEFERRED
                FOR EACH ROW EXECUTE FUNCTION eos_v2_assert_journal_balanced();
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS eos_v2_journal_lines_balanced ON eos_v2_journal_lines")
    op.execute("DROP FUNCTION IF EXISTS eos_v2_assert_journal_balanced()")
    op.execute("ALTER TABLE IF EXISTS eos_v2_journal_lines DROP CONSTRAINT IF EXISTS ck_eos_v2_journal_lines_exclusive_side")
    op.execute("ALTER TABLE IF EXISTS eos_v2_journal_lines DROP CONSTRAINT IF EXISTS fk_eos_v2_lines_tenant_account")
    op.execute("ALTER TABLE IF EXISTS eos_v2_journal_lines DROP CONSTRAINT IF EXISTS fk_eos_v2_lines_tenant_entry")
    op.execute("ALTER TABLE IF EXISTS eos_v2_journal_entries DROP CONSTRAINT IF EXISTS uq_eos_v2_journal_entries_tenant_id_id")
    op.execute("ALTER TABLE IF EXISTS eos_v2_accounts DROP CONSTRAINT IF EXISTS uq_eos_v2_accounts_tenant_id_id")
