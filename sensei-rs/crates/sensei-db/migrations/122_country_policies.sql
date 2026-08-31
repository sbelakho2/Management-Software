-- Country policy bundles (fifteenth audit item 84): language, currency,
-- units, week/calendar, holiday schedule, timezone, data residency,
-- retention, employment-data visibility and local document requirements —
-- as POLICY OBJECTS, never `if country == ...` code forks. A new country
-- is a policy RECORD, never a code change.
CREATE TABLE IF NOT EXISTS country_policies (
    id                           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    country                      VARCHAR(100) NOT NULL,
    language                     VARCHAR(10) NOT NULL,
    currency                     VARCHAR(10) NOT NULL,
    unit_system                  VARCHAR(20) NOT NULL,
    week_start                   VARCHAR(10) NOT NULL,
    holiday_schedule             JSONB NOT NULL DEFAULT '[]',
    timezone                     VARCHAR(50) NOT NULL,
    data_residency               VARCHAR(10),
    retention_days               INT NOT NULL DEFAULT 365,
    employment_data_visibility   VARCHAR(20) NOT NULL DEFAULT 'restricted',
    local_document_requirements  JSONB NOT NULL DEFAULT '[]',
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, country)
);
ALTER TABLE country_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE country_policies FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON country_policies
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Seed the initial country bundles for every tenant (fail-closed RLS:
-- only INSERTs executed under the tenant's own context are visible).
INSERT INTO country_policies
    (tenant_id, country, language, currency, unit_system, week_start,
     holiday_schedule, timezone, data_residency, retention_days,
     employment_data_visibility, local_document_requirements)
SELECT t.id, v.country, v.language, v.currency, v.unit_system, v.week_start,
       v.holiday_schedule::jsonb, v.timezone, v.data_residency, v.retention_days,
       v.employment_data_visibility, v.local_document_requirements::jsonb
FROM tenants t,
     (VALUES
        ('Morocco', 'fr', 'MAD', 'metric', 'monday',
         '["new_year","throne_day","green_march"]', 'Africa/Casablanca', 'ma', 365,
         'restricted', '["invoice_ar","invoice_fr"]'),
        ('Tunisia', 'fr', 'TND', 'metric', 'monday',
         '["new_year","revolution_day","independence_day"]', 'Africa/Tunis', 'tn', 365,
         'restricted', '["invoice_fr"]')
     ) AS v(country, language, currency, unit_system, week_start,
            holiday_schedule, timezone, data_residency, retention_days,
            employment_data_visibility, local_document_requirements)
WHERE NOT EXISTS (
    SELECT 1 FROM country_policies cp WHERE cp.tenant_id = t.id AND cp.country = v.country
);
