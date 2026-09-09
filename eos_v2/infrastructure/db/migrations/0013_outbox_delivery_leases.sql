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

-- Outbox payloads can contain business data, so the delivery table must obey
-- the same database-level tenant boundary as the rest of the v2 platform.
ALTER TABLE eos_v2_outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE eos_v2_outbox_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS eos_v2_outbox_tenant_isolation ON eos_v2_outbox_events;
CREATE POLICY eos_v2_outbox_tenant_isolation ON eos_v2_outbox_events
USING (tenant_id::text = current_setting('app.tenant_id', true))
WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
