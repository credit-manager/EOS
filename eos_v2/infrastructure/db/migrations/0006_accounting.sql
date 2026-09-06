-- EOS DBP v2 migration 0006: double-entry accounting kernel.
-- Apply only to the dedicated v2 database/schema. Never execute against the legacy database.

CREATE TABLE IF NOT EXISTS eos_v2_accounts (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    account_type VARCHAR(30) NOT NULL CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_eos_v2_account_code UNIQUE (tenant_id, code)
);

CREATE INDEX IF NOT EXISTS ix_eos_v2_accounts_tenant
    ON eos_v2_accounts (tenant_id);

CREATE TABLE IF NOT EXISTS eos_v2_journal_entries (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    entry_date DATE NOT NULL,
    currency VARCHAR(3) NOT NULL,
    description VARCHAR(500) NOT NULL,
    posted BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT ck_eos_v2_journal_currency CHECK (currency = upper(currency) AND length(currency) = 3)
);

CREATE INDEX IF NOT EXISTS ix_eos_v2_journal_entries_tenant_date
    ON eos_v2_journal_entries (tenant_id, entry_date);

CREATE TABLE IF NOT EXISTS eos_v2_journal_lines (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    journal_entry_id UUID NOT NULL REFERENCES eos_v2_journal_entries(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES eos_v2_accounts(id),
    debit NUMERIC(20,6) NOT NULL DEFAULT 0 CHECK (debit >= 0),
    credit NUMERIC(20,6) NOT NULL DEFAULT 0 CHECK (credit >= 0),
    CONSTRAINT ck_eos_v2_journal_line_side CHECK ((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0))
);

CREATE INDEX IF NOT EXISTS ix_eos_v2_journal_lines_tenant_entry
    ON eos_v2_journal_lines (tenant_id, journal_entry_id);
