-- Corporate federation membership (sixteenth audit item 1): the explicit
-- federation graph — a tenant may receive lessons ONLY from tenants it is
-- federated with. Target selection is authorization, not caller input.
CREATE TABLE IF NOT EXISTS federation_memberships (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    peer_tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    relationship    VARCHAR(30) NOT NULL DEFAULT 'corporate_group'
                    CHECK (relationship IN ('corporate_group', 'sister_site', 'parent')),
    capabilities    JSONB NOT NULL DEFAULT '[]',  -- ['lesson_transfer', 'analytics_share']
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, peer_tenant_id)
);
ALTER TABLE federation_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE federation_memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON federation_memberships
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Offers are NEVER written into the target's tables: the target sees an
-- offer and explicitly imports it into its own proposed state (proper
-- yokoten semantics).
CREATE TABLE IF NOT EXISTS corporate_lesson_offers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    offer_tenant_id UUID NOT NULL,      -- the tenant that OFFERED the lesson
    lesson_id       UUID NOT NULL,
    lesson_title    VARCHAR(300) NOT NULL,
    countermeasure  TEXT NOT NULL,
    context_signature JSONB NOT NULL DEFAULT '{}',
    applicability   JSONB NOT NULL DEFAULT '{}',
    status          VARCHAR(20) NOT NULL DEFAULT 'offered'
                    CHECK (status IN ('offered', 'imported', 'declined')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, offer_tenant_id, lesson_id)
);
ALTER TABLE corporate_lesson_offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE corporate_lesson_offers FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON corporate_lesson_offers
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
