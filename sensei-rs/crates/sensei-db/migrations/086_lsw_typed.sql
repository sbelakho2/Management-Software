-- LSW typed relational persistence (item 12): standards, audits and
-- occurrences become relational with the standard->audit->occurrence
-- relationships enforced by the database.
CREATE TABLE IF NOT EXISTS lsw_standards (
    id              UUID PRIMARY KEY,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    area            VARCHAR(100) NOT NULL,
    layer           INT NOT NULL DEFAULT 1,
    revision        INT NOT NULL DEFAULT 1,
    frequency       VARCHAR(30) NOT NULL DEFAULT 'daily'
                    CHECK (frequency IN ('daily', 'weekly', 'monthly', 'quarterly')),
    checklist_items JSONB NOT NULL DEFAULT '[]',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      UUID NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lsw_occurrences (
    id                UUID PRIMARY KEY,
    standard_id       UUID NOT NULL REFERENCES lsw_standards(id) ON DELETE CASCADE,
    tenant_id         UUID NOT NULL,
    checklist_revision INT NOT NULL,
    due_at            TIMESTAMPTZ NOT NULL,
    assigned_leader   UUID NOT NULL,
    area              VARCHAR(100) NOT NULL DEFAULT '',
    layer             INT NOT NULL DEFAULT 1,
    status            VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                      CHECK (status IN ('scheduled', 'in_progress', 'completed')),
    scheduled_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at        TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_lsw_occurrences_standard
    ON lsw_occurrences (tenant_id, standard_id, due_at);

CREATE TABLE IF NOT EXISTS lsw_audits (
    id               UUID PRIMARY KEY,
    standard_id      UUID NOT NULL REFERENCES lsw_standards(id) ON DELETE CASCADE,
    occurrence_id    UUID REFERENCES lsw_occurrences(id) ON DELETE SET NULL,
    -- One audit per occurrence: a single request can never create two
    -- audits for the same execution (item 13).
    CONSTRAINT lsw_audits_occurrence_once UNIQUE (occurrence_id, tenant_id),
    tenant_id        UUID NOT NULL,
    auditor_id       UUID NOT NULL,
    leader_id        UUID,
    area             VARCHAR(100) NOT NULL DEFAULT '',
    layer            INT NOT NULL DEFAULT 1,
    results          JSONB NOT NULL DEFAULT '[]',
    compliance_rate  DOUBLE PRECISION NOT NULL DEFAULT 0,
    notes            TEXT,
    audited_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_lsw_audits_standard
    ON lsw_audits (tenant_id, standard_id, audited_at);
