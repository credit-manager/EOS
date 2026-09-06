-- EOS DBP v2 migration 0005: transactional outbox.
-- Apply only to the dedicated v2 database/schema. Never execute against the legacy database.

CREATE TABLE IF NOT EXISTS eos_v2_outbox_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    event_type VARCHAR(200) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_eos_v2_outbox_tenant_pending
    ON eos_v2_outbox_events (tenant_id, published_at, occurred_at);

CREATE INDEX IF NOT EXISTS ix_eos_v2_outbox_aggregate
    ON eos_v2_outbox_events (tenant_id, aggregate_id);
