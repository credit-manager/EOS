"""Database-enforced integrity controls for the canonical EOS v2 ledger."""
from alembic import op
import sqlalchemy as sa

revision = "20260906_accounting_integrity"
down_revision = "20260906_harden_inventory_tenant_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite uniqueness makes tenant ownership part of every ledger reference.
    op.create_unique_constraint(
        "uq_eos_v2_accounts_tenant_id_id", "eos_v2_accounts", ["tenant_id", "id"]
    )
    op.create_unique_constraint(
        "uq_eos_v2_journal_entries_tenant_id_id", "eos_v2_journal_entries", ["tenant_id", "id"]
    )
    op.create_foreign_key(
        "fk_eos_v2_lines_tenant_entry",
        "eos_v2_journal_lines",
        "eos_v2_journal_entries",
        ["tenant_id", "journal_entry_id"],
        ["tenant_id", "id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_eos_v2_lines_tenant_account",
        "eos_v2_journal_lines",
        "eos_v2_accounts",
        ["tenant_id", "account_id"],
        ["tenant_id", "id"],
    )
    op.create_check_constraint(
        "ck_eos_v2_journal_lines_exclusive_side",
        "eos_v2_journal_lines",
        "NOT (debit > 0 AND credit > 0)",
    )
    op.create_check_constraint(
        "ck_eos_v2_journal_entries_nonnegative_totals",
        "eos_v2_journal_entries",
        "total_debit >= 0 AND total_credit >= 0",
    )
    # A deferred constraint trigger makes the database the final authority for
    # double-entry balance, while allowing all lines to be inserted in one tx.
    op.execute("""
        CREATE OR REPLACE FUNCTION eos_v2_assert_journal_balanced()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            debit_total NUMERIC;
            credit_total NUMERIC;
        BEGIN
            SELECT COALESCE(SUM(debit), 0), COALESCE(SUM(credit), 0)
              INTO debit_total, credit_total
              FROM eos_v2_journal_lines
             WHERE journal_entry_id = NEW.journal_entry_id
               AND tenant_id = NEW.tenant_id;
            IF debit_total <> credit_total THEN
                RAISE EXCEPTION 'Journal entry % is not balanced: debit=% credit=%',
                    NEW.journal_entry_id, debit_total, credit_total;
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER eos_v2_journal_lines_balanced
        AFTER INSERT OR UPDATE OR DELETE ON eos_v2_journal_lines
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION eos_v2_assert_journal_balanced()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS eos_v2_journal_lines_balanced ON eos_v2_journal_lines")
    op.execute("DROP FUNCTION IF EXISTS eos_v2_assert_journal_balanced()")
    op.drop_constraint("ck_eos_v2_journal_entries_nonnegative_totals", "eos_v2_journal_entries", type_="check")
    op.drop_constraint("ck_eos_v2_journal_lines_exclusive_side", "eos_v2_journal_lines", type_="check")
    op.drop_constraint("fk_eos_v2_lines_tenant_account", "eos_v2_journal_lines", type_="foreignkey")
    op.drop_constraint("fk_eos_v2_lines_tenant_entry", "eos_v2_journal_lines", type_="foreignkey")
    op.drop_constraint("uq_eos_v2_journal_entries_tenant_id_id", "eos_v2_journal_entries", type_="unique")
    op.drop_constraint("uq_eos_v2_accounts_tenant_id_id", "eos_v2_accounts", type_="unique")
