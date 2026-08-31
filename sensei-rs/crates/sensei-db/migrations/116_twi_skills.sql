-- TWI skill/job model (fifteenth audit 37-39): JobStandard with steps
-- (action, key points, REASONS, hazards, checks) and a real skill graph
-- per principal with demonstrated evidence, recency and expiry.
CREATE TABLE IF NOT EXISTS job_standards (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    standard_id VARCHAR(100) NOT NULL,
    revision    BIGINT NOT NULL DEFAULT 1,
    process     VARCHAR(100) NOT NULL,
    title       VARCHAR(200) NOT NULL,
    steps       JSONB NOT NULL DEFAULT '[]',  -- JobStep[] {action, key_points, reasons, hazards, checks}
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, standard_id, revision)
);
CREATE TABLE IF NOT EXISTS skills (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    skill_id     VARCHAR(100) NOT NULL,
    name         VARCHAR(200) NOT NULL,
    process      VARCHAR(100),
    standard_id  VARCHAR(100),
    critical     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, skill_id)
);
CREATE TABLE IF NOT EXISTS skill_qualifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    principal_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id        UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    level           VARCHAR(20) NOT NULL DEFAULT 'unexposed'
                    CHECK (level IN ('unexposed','learning','supervised','independent','trainer')),
    demonstrated_at TIMESTAMPTZ,
    evidence        JSONB NOT NULL DEFAULT '[]',
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, principal_id, skill_id)
);
ALTER TABLE job_standards ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_standards FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON job_standards
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON skills
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
ALTER TABLE skill_qualifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_qualifications FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON skill_qualifications
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
