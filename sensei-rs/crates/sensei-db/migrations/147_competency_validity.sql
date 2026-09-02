-- Competency validity (twentieth audit P0/P1): the projection becomes
-- safety-grade — expiry, revocation and standard revision are first-class,
-- and the evidence link is an enforced FK. A qualification that expired
-- or was revoked can never satisfy a lifecycle gate or coverage query.
ALTER TABLE competency_projection
    ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS valid_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revoked_reason VARCHAR(300),
    ADD COLUMN IF NOT EXISTS standard_revision VARCHAR(200);
CREATE INDEX IF NOT EXISTS idx_competency_valid
    ON competency_projection (tenant_id, valid_until) WHERE revoked_at IS NULL;

-- The projection's evidence must exist and belong to the SAME tenant as
-- the projection (structural integrity: no orphaned projections).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'competency_projection_evidence_fk'
    ) THEN
        ALTER TABLE competency_projection
            ADD CONSTRAINT competency_projection_evidence_fk
            FOREIGN KEY (source_evidence_id)
            REFERENCES skill_qualification_evidence(id)
            ON DELETE RESTRICT;
    END IF;
END $$;

-- Scoped current state: the global skill_qualifications row no longer
-- controls scoped transitions — the per-(site, shift) projection does.
-- Seed the projection's validity from the source evidence timestamp when
-- missing.
UPDATE competency_projection cp
SET valid_from = e.demonstrated_at,
    valid_until = COALESCE(cp.valid_until, e.demonstrated_at + INTERVAL '12 months'),
    standard_revision = COALESCE(cp.standard_revision, e.standard_revision)
FROM skill_qualification_evidence e
WHERE cp.source_evidence_id = e.id
  AND cp.valid_from = cp.valid_from
  AND e.demonstrated_at IS NOT NULL;
