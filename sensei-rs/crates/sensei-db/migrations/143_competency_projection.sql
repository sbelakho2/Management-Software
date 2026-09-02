-- Nineteenth audit item P1: multi-shift competency from evidence. The
-- CURRENT-STATE competency projection, keyed by
-- (tenant, principal, skill, site, shift): ONE row per site/shift scope a
-- principal has demonstrated a skill on. skill_qualifications keeps only
-- ONE current level (UNIQUE (tenant, principal, skill)) whose shift_id is
-- permanently anchored to the FIRST demonstration, and
-- skill_qualification_evidence is the append-only history — neither can
-- answer "who is independently qualified on SHIFT B". Every recorded
-- qualification upserts the matching projection row here (source_evidence_id
-- links to the immutable evidence row), so coverage filters on STRUCTURAL
-- site/shift columns instead of the single first-shift anchor.
--
-- site_id is NULLABLE (vs. a strict site anchor): a demonstration recorded
-- without a shift and without an anchored site carries no structural site;
-- its scope resolves at query time from the principal's active role-slot
-- assignment (sixteenth audit item 38 semantics preserved for shift-less
-- records). The functional unique index below COALESCEs the nullable key
-- components so the "any site / any shift" bucket is a SINGLE row — plain
-- UNIQUE treats NULLs as distinct and would let repeated shift-less
-- demonstrations grow the projection instead of upserting it.
CREATE TABLE IF NOT EXISTS competency_projection (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    principal_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id           UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    site_id            UUID REFERENCES sites(id) ON DELETE CASCADE,
    shift_id           UUID REFERENCES shifts(id) ON DELETE CASCADE,
    level              VARCHAR(20) NOT NULL
                       CHECK (level IN ('unexposed','learning','supervised','independent','trainer')),
    source_evidence_id UUID NOT NULL,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, principal_id, skill_id, site_id, shift_id)
);
-- The "any site / any shift" bucket: one row per (tenant, principal,
-- skill) even when site_id/shift_id are NULL (NULLs are distinct under
-- plain UNIQUE). The upsert's ON CONFLICT target uses the SAME
-- COALESCE expressions so the arbiter inference resolves to this index.
CREATE UNIQUE INDEX IF NOT EXISTS uq_competency_projection_scope
    ON competency_projection (
        tenant_id,
        principal_id,
        skill_id,
        COALESCE(site_id, '00000000-0000-0000-0000-000000000000'),
        COALESCE(shift_id, '00000000-0000-0000-0000-000000000000')
    );
-- Coverage joins on (tenant_id, skill_id) — the structural scope filter
-- reads the projection per skill.
CREATE INDEX IF NOT EXISTS idx_competency_projection_skill
    ON competency_projection (tenant_id, skill_id);
ALTER TABLE competency_projection ENABLE ROW LEVEL SECURITY;
ALTER TABLE competency_projection FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON competency_projection
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
