-- Episode memory (fifteenth audit 12/14): historical operational
-- episodes — an NCR resolved, an andon with a countermeasure, a standard
-- changed. Associative retrieval walks the links (supplier, machine,
-- process, material, part family, operator) to find related episodes.
CREATE TABLE IF NOT EXISTS episodes (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    episode_type VARCHAR(50) NOT NULL,  -- ncr | andon | standard_change | customer_complaint | supplier_issue
    title        VARCHAR(300) NOT NULL,
    description  TEXT,
    status       VARCHAR(30) NOT NULL DEFAULT 'open',
    outcome      TEXT,
    confidence   DOUBLE PRECISION,
    links        JSONB NOT NULL DEFAULT '[]',  -- [{kind: supplier|machine|process|material|part_family|operator|work_center, id, label}]
    source_entity_type VARCHAR(50),
    source_entity_id   UUID,
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_episodes_tenant ON episodes (tenant_id, episode_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_links ON episodes USING GIN (links);
ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodes FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON episodes
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
