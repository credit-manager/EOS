-- EOS DBP v2 industry pack installation registry.
-- Records are tenant-scoped and make pack installation retries idempotent.
CREATE TABLE IF NOT EXISTS eos_v2_industry_pack_installations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    pack_key VARCHAR(100) NOT NULL,
    pack_version VARCHAR(50) NOT NULL,
    entity_ids JSONB NOT NULL,
    installed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_v2_industry_pack_installation UNIQUE (tenant_id, pack_key, pack_version)
);
CREATE INDEX IF NOT EXISTS ix_eos_v2_industry_pack_installations_tenant
    ON eos_v2_industry_pack_installations(tenant_id);
