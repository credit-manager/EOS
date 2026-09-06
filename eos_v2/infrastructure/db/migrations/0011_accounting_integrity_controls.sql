-- EOS DBP v2 migration 0011: database-enforced accounting integrity.
-- Tenant ownership is part of every ledger foreign-key reference.

CREATE UNIQUE INDEX IF NOT EXISTS uq_eos_v2_accounts_tenant_id_id
    ON eos_v2_accounts (tenant_id, id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_eos_v2_journal_entries_tenant_id_id
    ON eos_v2_journal_entries (tenant_id, id);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_eos_v2_lines_tenant_entry') THEN
        ALTER TABLE eos_v2_journal_lines
            ADD CONSTRAINT fk_eos_v2_lines_tenant_entry
            FOREIGN KEY (tenant_id, journal_entry_id)
            REFERENCES eos_v2_journal_entries (tenant_id, id)
            ON DELETE CASCADE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_eos_v2_lines_tenant_account') THEN
        ALTER TABLE eos_v2_journal_lines
            ADD CONSTRAINT fk_eos_v2_lines_tenant_account
            FOREIGN KEY (tenant_id, account_id)
            REFERENCES eos_v2_accounts (tenant_id, id);
    END IF;
END $$;

CREATE OR REPLACE FUNCTION eos_v2_assert_journal_balanced()
RETURNS trigger
LANGUAGE plpgsql
AS $$
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
$$;

DROP TRIGGER IF EXISTS eos_v2_journal_lines_balanced ON eos_v2_journal_lines;
CREATE CONSTRAINT TRIGGER eos_v2_journal_lines_balanced
AFTER INSERT OR UPDATE ON eos_v2_journal_lines
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION eos_v2_assert_journal_balanced();

CREATE OR REPLACE FUNCTION eos_v2_prevent_posted_entry_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.posted THEN
        RAISE EXCEPTION 'Posted journal entries are immutable';
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS eos_v2_posted_entry_immutable ON eos_v2_journal_entries;
CREATE TRIGGER eos_v2_posted_entry_immutable
BEFORE UPDATE OR DELETE ON eos_v2_journal_entries
FOR EACH ROW EXECUTE FUNCTION eos_v2_prevent_posted_entry_mutation();

CREATE OR REPLACE FUNCTION eos_v2_prevent_posted_line_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    is_posted BOOLEAN;
BEGIN
    SELECT posted INTO is_posted
      FROM eos_v2_journal_entries
     WHERE id = OLD.journal_entry_id
       AND tenant_id = OLD.tenant_id;
    IF COALESCE(is_posted, FALSE) THEN
        RAISE EXCEPTION 'Lines of posted journal entries are immutable';
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS eos_v2_posted_line_immutable ON eos_v2_journal_lines;
CREATE TRIGGER eos_v2_posted_line_immutable
BEFORE UPDATE OR DELETE ON eos_v2_journal_lines
FOR EACH ROW EXECUTE FUNCTION eos_v2_prevent_posted_line_mutation();
