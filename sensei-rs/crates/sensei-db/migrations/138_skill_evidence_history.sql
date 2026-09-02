-- Append-only evidence history (eighteenth audit item P1-9):
-- skill_qualifications is UNIQUE (tenant_id, principal_id, skill_id), so a
-- qualification on Shift B would OVERWRITE the Shift A anchor and
-- multi-shift qualification could not be represented. Every recorded
-- qualification appends ONE immutable row here — the exact standard
-- revision, the assessor identity and the evidence object from the
-- qualification, plus the demonstration site/shift context — so the
-- full demonstration history survives qualification updates forever.
CREATE TABLE IF NOT EXISTS skill_qualification_evidence (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id              UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    principal_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id               UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    standard_revision      VARCHAR(200) NOT NULL,
    demonstrated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    demonstration_site_id  UUID REFERENCES sites(id) ON DELETE SET NULL,
    demonstration_shift_id UUID REFERENCES shifts(id) ON DELETE SET NULL,
    assessor_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    evidence               JSONB NOT NULL DEFAULT '[]',
    prior_competence       JSONB,
    recorded_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_skill_qual_evidence_history
    ON skill_qualification_evidence (tenant_id, principal_id, skill_id, demonstrated_at);
ALTER TABLE skill_qualification_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_qualification_evidence FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON skill_qualification_evidence
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
