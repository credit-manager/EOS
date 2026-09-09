"""Enforce database-level invariants for the general ledger.

Revision ID: 20260909_finalize_tenant_rls_accounting
Revises: 20260909_finalize_tenant_rls
"""
from __future__ import annotations

from alembic import op

revision = "20260909_finalize_tenant_rls_accounting"
down_revision = "20260909_finalize_tenant_rls"
branch_labels = None
depends_on = None


_INSERT_UPDATE_LINE_FUNCTION = """
CREATE OR REPLACE FUNCTION public.eos_validate_journal_line()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_tenant_id text;
    v_status text;
    v_account_tenant text;
BEGIN
    SELECT tenant_id::text, status
      INTO v_tenant_id, v_status
      FROM public.dbp_journal_entries
     WHERE id = NEW.journal_entry_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Journal entry % does not exist', NEW.journal_entry_id;
    END IF;

    IF v_status <> 'draft' THEN
        RAISE EXCEPTION 'Journal lines can only be changed while the entry is draft';
    END IF;

    SELECT tenant_id::text
      INTO v_account_tenant
      FROM public.dbp_accounts
     WHERE id = NEW.account_id;

    IF NOT FOUND OR v_account_tenant <> v_tenant_id THEN
        RAISE EXCEPTION 'Journal line account does not belong to the journal tenant';
    END IF;

    IF NEW.debit < 0 OR NEW.credit < 0 THEN
        RAISE EXCEPTION 'Journal debit and credit must be non-negative';
    END IF;

    IF NEW.debit = 0 AND NEW.credit = 0 THEN
        RAISE EXCEPTION 'Journal line must contain a debit or credit amount';
    END IF;

    IF NEW.debit > 0 AND NEW.credit > 0 THEN
        RAISE EXCEPTION 'Journal line cannot contain both debit and credit';
    END IF;

    RETURN NEW;
END;
$$;
"""

_DELETE_LINE_FUNCTION = """
CREATE OR REPLACE FUNCTION public.eos_validate_journal_line_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_status text;
BEGIN
    SELECT status INTO v_status
      FROM public.dbp_journal_entries
     WHERE id = OLD.journal_entry_id;

    IF v_status IS NULL THEN
        RAISE EXCEPTION 'Journal entry % does not exist', OLD.journal_entry_id;
    END IF;

    IF v_status <> 'draft' THEN
        RAISE EXCEPTION 'Journal lines can only be deleted while the entry is draft';
    END IF;

    RETURN OLD;
END;
$$;
"""

_ENTRY_FUNCTION = """
CREATE OR REPLACE FUNCTION public.eos_validate_journal_entry()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_line_count integer;
    v_debit numeric(20,4);
    v_credit numeric(20,4);
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.id <> OLD.id OR NEW.tenant_id <> OLD.tenant_id OR NEW.company_id <> OLD.company_id
           OR NEW.entry_number <> OLD.entry_number THEN
            RAISE EXCEPTION 'Journal identity fields are immutable';
        END IF;

        IF OLD.status IN ('posted', 'reversed') THEN
            IF NOT (OLD.status = 'posted' AND NEW.status = 'reversed') THEN
                RAISE EXCEPTION 'Posted or reversed journal entries are immutable';
            END IF;
            IF NEW.total_debit <> OLD.total_debit OR NEW.total_credit <> OLD.total_credit
               OR NEW.entry_date <> OLD.entry_date OR NEW.entry_type <> OLD.entry_type
               OR COALESCE(NEW.description, '') <> COALESCE(OLD.description, '')
               OR COALESCE(NEW.reference, '') <> COALESCE(OLD.reference, '')
               OR NEW.company_id <> OLD.company_id THEN
                RAISE EXCEPTION 'Only the status transition posted -> reversed is allowed';
            END IF;
            NEW.is_posted := false;
        END IF;
    END IF;

    IF NEW.total_debit < 0 OR NEW.total_credit < 0 THEN
        RAISE EXCEPTION 'Journal totals must be non-negative';
    END IF;

    IF NEW.status = 'reversed' THEN
        IF NEW.is_posted IS DISTINCT FROM false THEN
            NEW.is_posted := false;
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.status = 'posted' OR NEW.is_posted THEN
        SELECT COUNT(*), COALESCE(SUM(debit), 0), COALESCE(SUM(credit), 0)
          INTO v_line_count, v_debit, v_credit
          FROM public.dbp_journal_lines
         WHERE journal_entry_id = NEW.id;

        IF v_line_count < 2 THEN
            RAISE EXCEPTION 'A posted journal entry requires at least two lines';
        END IF;
        IF v_debit <> v_credit THEN
            RAISE EXCEPTION 'Posted journal entry must be balanced: debit %, credit %', v_debit, v_credit;
        END IF;
        IF NEW.total_debit <> v_debit OR NEW.total_credit <> v_credit THEN
            RAISE EXCEPTION 'Journal header totals do not match journal lines';
        END IF;
        IF NEW.status <> 'posted' OR NEW.is_posted IS DISTINCT FROM true THEN
            RAISE EXCEPTION 'Posted journal status and is_posted flag must agree';
        END IF;
        IF NEW.posted_at IS NULL THEN
            RAISE EXCEPTION 'Posted journal entry requires posted_at';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;
"""

_ACCOUNT_DELETE_FUNCTION = """
CREATE OR REPLACE FUNCTION public.eos_prevent_account_delete_if_referenced()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM public.dbp_journal_lines
         WHERE account_id = OLD.id
         LIMIT 1
    ) THEN
        RAISE EXCEPTION 'Account % cannot be deleted because it is referenced by journal lines', OLD.id;
    END IF;
    RETURN OLD;
END;
$$;
"""


def upgrade() -> None:
    op.execute(_INSERT_UPDATE_LINE_FUNCTION)
    op.execute(_DELETE_LINE_FUNCTION)
    op.execute(_ENTRY_FUNCTION)
    op.execute(_ACCOUNT_DELETE_FUNCTION)

    op.execute("DROP TRIGGER IF EXISTS trg_eos_validate_journal_line ON public.dbp_journal_lines")
    op.execute(
        "CREATE TRIGGER trg_eos_validate_journal_line "
        "BEFORE INSERT OR UPDATE ON public.dbp_journal_lines "
        "FOR EACH ROW EXECUTE FUNCTION public.eos_validate_journal_line()"
    )

    op.execute("DROP TRIGGER IF EXISTS trg_eos_validate_journal_line_delete ON public.dbp_journal_lines")
    op.execute(
        "CREATE TRIGGER trg_eos_validate_journal_line_delete "
        "BEFORE DELETE ON public.dbp_journal_lines "
        "FOR EACH ROW EXECUTE FUNCTION public.eos_validate_journal_line_delete()"
    )

    op.execute("DROP TRIGGER IF EXISTS trg_eos_validate_journal_entry ON public.dbp_journal_entries")
    op.execute(
        "CREATE TRIGGER trg_eos_validate_journal_entry "
        "BEFORE INSERT OR UPDATE ON public.dbp_journal_entries "
        "FOR EACH ROW EXECUTE FUNCTION public.eos_validate_journal_entry()"
    )

    op.execute("DROP TRIGGER IF EXISTS trg_eos_prevent_account_delete_if_referenced ON public.dbp_accounts")
    op.execute(
        "CREATE TRIGGER trg_eos_prevent_account_delete_if_referenced "
        "BEFORE DELETE ON public.dbp_accounts "
        "FOR EACH ROW EXECUTE FUNCTION public.eos_prevent_account_delete_if_referenced()"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dbp_journal_lines_entry_account "
        "ON public.dbp_journal_lines (journal_entry_id, account_id)"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_eos_prevent_account_delete_if_referenced ON public.dbp_accounts")
    op.execute("DROP TRIGGER IF EXISTS trg_eos_validate_journal_entry ON public.dbp_journal_entries")
    op.execute("DROP TRIGGER IF EXISTS trg_eos_validate_journal_line_delete ON public.dbp_journal_lines")
    op.execute("DROP TRIGGER IF EXISTS trg_eos_validate_journal_line ON public.dbp_journal_lines")
    op.execute("DROP FUNCTION IF EXISTS public.eos_prevent_account_delete_if_referenced()")
    op.execute("DROP FUNCTION IF EXISTS public.eos_validate_journal_entry()")
    op.execute("DROP FUNCTION IF EXISTS public.eos_validate_journal_line_delete()")
    op.execute("DROP FUNCTION IF EXISTS public.eos_validate_journal_line()")
    op.execute("DROP INDEX IF EXISTS public.ix_dbp_journal_lines_entry_account")
