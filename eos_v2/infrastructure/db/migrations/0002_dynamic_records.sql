-- EOS DBP v2 migration 0002: dynamic records.
-- Apply only to the dedicated v2 database/schema. Never execute against the legacy database.

CREATE TABLE IF NOT EXISTS eos_v2_dynamic_records (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    entity_id UUID NOT NULL,
    entity_version INTEGER NOT NULL CHECK (entity_version >= 1),
    data JSONB NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1 CHECK (row_version >= 1),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_eos_v2_record_tenant_id UNIQUE (tenant_id, id)
);

CREATE INDEX IF NOT EXISTS ix_eos_v2_dynamic_records_tenant_entity
    ON eos_v2_dynamic_records (tenant_id, entity_id);

CREATE INDEX IF NOT EXISTS ix_eos_v2_dynamic_records_tenant_entity_version
    ON eos_v2_dynamic_records (tenant_id, entity_id, entity_version);
