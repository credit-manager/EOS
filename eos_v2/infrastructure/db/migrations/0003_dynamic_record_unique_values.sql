-- EOS DBP v2 migration 0003: transactional uniqueness registry.
-- Apply only to the dedicated v2 database/schema. Never execute against the legacy database.

CREATE TABLE IF NOT EXISTS eos_v2_dynamic_record_unique_values (
    tenant_id UUID NOT NULL,
    entity_id UUID NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    value_key VARCHAR(2048) NOT NULL,
    record_id UUID NOT NULL,
    CONSTRAINT pk_eos_v2_record_unique_value
        PRIMARY KEY (tenant_id, entity_id, field_name, value_key),
    CONSTRAINT fk_eos_v2_unique_value_record
        FOREIGN KEY (tenant_id, record_id)
        REFERENCES eos_v2_dynamic_records (tenant_id, id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_eos_v2_record_unique_value_record
    ON eos_v2_dynamic_record_unique_values (tenant_id, record_id);

CREATE INDEX IF NOT EXISTS ix_eos_v2_record_unique_value_entity
    ON eos_v2_dynamic_record_unique_values (tenant_id, entity_id, field_name);
