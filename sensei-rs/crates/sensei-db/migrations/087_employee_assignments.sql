-- Employee active assignment (item 17): the agent context must resolve
-- the caller's distributed plant scope at request time — site, value
-- stream, work center and shift — instead of filling None for everybody.
CREATE TABLE IF NOT EXISTS employee_assignments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    site_id         UUID REFERENCES sites(id) ON DELETE SET NULL,
    value_stream_id UUID REFERENCES value_streams(id) ON DELETE SET NULL,
    work_center_id  UUID REFERENCES work_centers(id) ON DELETE SET NULL,
    shift_id        UUID REFERENCES shifts(id) ON DELETE SET NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, site_id, value_stream_id, work_center_id, shift_id)
);
CREATE INDEX IF NOT EXISTS idx_employee_assignments_user
    ON employee_assignments (tenant_id, user_id) WHERE is_active = TRUE;
