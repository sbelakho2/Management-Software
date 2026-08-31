-- Lessons (fifteenth audit 46-47/A19): explicit lesson objects with a
-- context signature and an APPLICABILITY rule — cross-site transfer is
-- an experiment with local verification, never blind replication.
CREATE TABLE IF NOT EXISTS lessons (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lesson_id         VARCHAR(100) NOT NULL,
    title             VARCHAR(300) NOT NULL,
    source_problem_id UUID,
    context_signature JSONB NOT NULL DEFAULT '{}',  -- {machine_family, paste_family, process, part_family}
    hypothesis        TEXT,
    countermeasure    TEXT NOT NULL,
    observed_result   JSONB NOT NULL DEFAULT '{}',
    confidence        DOUBLE PRECISION,
    applicability     JSONB NOT NULL DEFAULT '{}',   -- {machine_families[], processes[], min_evidence, verified_locally}
    status            VARCHAR(20) NOT NULL DEFAULT 'proposed'
                      CHECK (status IN ('proposed','verified','adopted','rejected','archived')),
    origin_site_id    UUID,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, lesson_id)
);
CREATE INDEX IF NOT EXISTS idx_lessons_signature ON lessons USING GIN (context_signature);
CREATE INDEX IF NOT EXISTS idx_lessons_applicability ON lessons USING GIN (applicability);
ALTER TABLE lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE lessons FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON lessons
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
