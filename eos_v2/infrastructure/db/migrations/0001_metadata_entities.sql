-- EOS DBP v2 metadata kernel.
-- Apply only to the dedicated v2 database/schema. Never against the legacy EOS database.

CREATE TABLE eos_v2_metadata_entities (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    label VARCHAR(200) NOT NULL DEFAULT '',
    version INTEGER NOT NULL CHECK (version >= 1),
    published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    definition JSONB NOT NULL,
    CONSTRAINT uq_v2_metadata_entity_version UNIQUE (tenant_id, name, version)
);

CREATE INDEX ix_v2_metadata_entities_tenant_id
    ON eos_v2_metadata_entities (tenant_id);
