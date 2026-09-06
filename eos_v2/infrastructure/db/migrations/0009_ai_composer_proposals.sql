-- EOS DBP v2 AI Composer proposal registry.
-- AI output is persisted as a draft and cannot publish metadata without an explicit approval action.
CREATE TABLE IF NOT EXISTS eos_v2_ai_composer_proposals (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    actor_id UUID NOT NULL,
    prompt VARCHAR(12000) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    changes JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMPTZ NULL,
    CONSTRAINT ck_eos_v2_ai_composer_proposal_status CHECK (status IN ('draft', 'approved', 'rejected')),
    CONSTRAINT ck_eos_v2_ai_composer_decision_time CHECK ((status = 'draft' AND decided_at IS NULL) OR (status <> 'draft' AND decided_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_eos_v2_ai_composer_proposals_tenant
    ON eos_v2_ai_composer_proposals(tenant_id);
CREATE INDEX IF NOT EXISTS ix_eos_v2_ai_composer_proposals_tenant_status
    ON eos_v2_ai_composer_proposals(tenant_id, status);
