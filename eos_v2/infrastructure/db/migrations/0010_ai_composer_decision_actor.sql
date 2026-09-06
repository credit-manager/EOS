-- Preserve migration immutability: decision actor is added as a follow-up migration.
ALTER TABLE eos_v2_ai_composer_proposals
    ADD COLUMN IF NOT EXISTS decided_by UUID NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_eos_v2_ai_composer_decided_by'
    ) THEN
        ALTER TABLE eos_v2_ai_composer_proposals
            ADD CONSTRAINT ck_eos_v2_ai_composer_decided_by
            CHECK ((status = 'draft' AND decided_by IS NULL) OR (status <> 'draft' AND decided_by IS NOT NULL));
    END IF;
END $$;
