-- Role/role-slot/principal separation (fifteenth audit 40-44): a role
-- slot (electronics_buyer_tangier) owns the work — principals are
-- assigned to slots. When a person leaves, the slot and its history
-- survive; only the assignment ends.
CREATE TABLE IF NOT EXISTS role_slots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role_name       VARCHAR(100) NOT NULL,   -- the role definition
    slot_name       VARCHAR(100) NOT NULL,   -- e.g. Planner_Tangier_A
    scope_site_id   UUID,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, slot_name)
);
CREATE TABLE IF NOT EXISTS principal_assignments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    principal_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    slot_id         UUID NOT NULL REFERENCES role_slots(id) ON DELETE CASCADE,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    UNIQUE (tenant_id, slot_id, principal_id, ended_at)
);
ALTER TABLE role_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_slots FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON role_slots
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
ALTER TABLE principal_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE principal_assignments FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON principal_assignments
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
