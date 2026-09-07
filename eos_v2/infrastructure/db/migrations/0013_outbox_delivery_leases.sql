-- EOS DBP v2 migration 0013: leased outbox claims for crash-safe retries.
-- Delivery remains at-least-once. Consumers MUST deduplicate by event id.

ALTER TABLE eos_v2_outbox_events
    ADD COLUMN IF NOT EXISTS claim_token UUID NULL,
    ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS delivery_attempts INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS ix_eos_v2_outbox_claims
    ON eos_v2_outbox_events (tenant_id, published_at, claimed_at, occurred_at);

ALTER TABLE eos_v2_outbox_events
    DROP CONSTRAINT IF EXISTS eos_v2_outbox_delivery_attempts_nonnegative;
ALTER TABLE eos_v2_outbox_events
    ADD CONSTRAINT eos_v2_outbox_delivery_attempts_nonnegative
    CHECK (delivery_attempts >= 0);
