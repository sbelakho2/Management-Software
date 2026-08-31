-- Country policy versions (sixteenth audit item 65): policy is
-- effective-dated; each site references the version governing it.
CREATE TABLE IF NOT EXISTS country_policy_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    country         VARCHAR(100) NOT NULL,
    revision        BIGINT NOT NULL DEFAULT 1,
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until     TIMESTAMPTZ,
    language        VARCHAR(10) NOT NULL,
    currency        VARCHAR(10) NOT NULL,
    unit_system     VARCHAR(20) NOT NULL DEFAULT 'metric',
    week_start      VARCHAR(10) NOT NULL DEFAULT 'monday',
    holiday_schedule JSONB NOT NULL DEFAULT '[]',
    timezone        VARCHAR(100) NOT NULL DEFAULT 'UTC',
    data_residency  VARCHAR(100),
    retention_days  INT NOT NULL DEFAULT 365,
    employment_data_visibility VARCHAR(30) NOT NULL DEFAULT 'restricted',
    local_document_requirements JSONB NOT NULL DEFAULT '[]',
    approved_by     UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, country, revision)
);
ALTER TABLE country_policy_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE country_policy_versions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON country_policy_versions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Versioned jurisdiction holidays (sixteenth audit item 66): a date is a
-- holiday per jurisdiction with a source + revision — Morocco's calendar
-- is not a forever-static list.
CREATE TABLE IF NOT EXISTS jurisdiction_holidays (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    jurisdiction VARCHAR(100) NOT NULL,
    holiday_date DATE NOT NULL,
    name         VARCHAR(200) NOT NULL,
    source       VARCHAR(100) NOT NULL DEFAULT 'government',
    revision     BIGINT NOT NULL DEFAULT 1,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, jurisdiction, holiday_date, revision)
);
ALTER TABLE jurisdiction_holidays ENABLE ROW LEVEL SECURITY;
ALTER TABLE jurisdiction_holidays FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON jurisdiction_holidays
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
