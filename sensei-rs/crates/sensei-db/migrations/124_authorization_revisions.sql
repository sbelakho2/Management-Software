-- Authorization snapshots (fifteenth audit 24/A5): every execution
-- carries the policy/relationship/principal revision it was authorized
-- under; a revocation bumps the revision and invalidates caches.
CREATE TABLE IF NOT EXISTS authorization_revisions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    policy_revision     BIGINT NOT NULL DEFAULT 1,
    relationship_revision BIGINT NOT NULL DEFAULT 1,
    principal_revision  BIGINT NOT NULL DEFAULT 1,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id)
);
ALTER TABLE authorization_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE authorization_revisions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON authorization_revisions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Seed for tenants existing at migration time.
INSERT INTO authorization_revisions (tenant_id, policy_revision, relationship_revision, principal_revision)
SELECT id, 1, 1, 1 FROM tenants
ON CONFLICT (tenant_id) DO NOTHING;
