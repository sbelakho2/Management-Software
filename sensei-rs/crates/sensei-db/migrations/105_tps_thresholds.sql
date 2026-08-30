-- Contextual TPS thresholds (item 45): classifiers stay deterministic,
-- but their thresholds are versioned FACTORY KNOWLEDGE — per product
-- family, per site policy — instead of universal constants baked into
-- code. The derive endpoint reads the tenant's overrides; absent rows
-- fall back to the documented defaults.
CREATE TABLE IF NOT EXISTS tps_thresholds (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_family_id  UUID REFERENCES product_families(id) ON DELETE CASCADE,
    signal_key         VARCHAR(100) NOT NULL, -- andon_recurrence_count,
                                              -- cycle_miss_ratio,
                                              -- queue_growth_count,
                                              -- supplier_variability_stddev,
                                              -- workaround_count
    threshold_value    DOUBLE PRECISION NOT NULL,
    window_days        INT NOT NULL DEFAULT 30,
    source             VARCHAR(100) NOT NULL DEFAULT 'site_policy',
    note               TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, product_family_id, signal_key)
);

ALTER TABLE tps_thresholds ENABLE ROW LEVEL SECURITY;
ALTER TABLE tps_thresholds FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tps_thresholds
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
