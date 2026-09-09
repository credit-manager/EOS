-- EOS DBP v2 migration 0012: commercial audit trail for sensitive business actions.

CREATE TABLE IF NOT EXISTS eos_v2_audit_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    actor_id UUID,
    action VARCHAR(80) NOT NULL,
    resource_type VARCHAR(80) NOT NULL,
    resource_id VARCHAR(100),
    request_id VARCHAR(100),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_eos_v2_audit_tenant_created
    ON eos_v2_audit_events (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_eos_v2_audit_resource
    ON eos_v2_audit_events (tenant_id, resource_type, resource_id);

ALTER TABLE eos_v2_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE eos_v2_audit_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS eos_v2_audit_tenant_isolation ON eos_v2_audit_events;
CREATE POLICY eos_v2_audit_tenant_isolation ON eos_v2_audit_events
USING (tenant_id::text = current_setting('app.tenant_id', true))
WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
