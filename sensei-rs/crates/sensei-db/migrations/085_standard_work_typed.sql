-- Standard work: typed relational persistence (item 12). Controlled
-- documents live in their own tables with the version relationship
-- enforced by the database — never only in generic EntityStore JSON.
CREATE TABLE IF NOT EXISTS standard_work_documents (
    id                 UUID PRIMARY KEY,
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title              VARCHAR(255) NOT NULL,
    document_number    VARCHAR(100) NOT NULL DEFAULT '',
    area               VARCHAR(100) NOT NULL DEFAULT '',
    process            VARCHAR(100) NOT NULL DEFAULT '',
    current_version    INT NOT NULL DEFAULT 1,
    status             VARCHAR(30) NOT NULL DEFAULT 'draft'
                       CHECK (status IN ('draft', 'under_review', 'published',
                                         'effective', 'superseded', 'archived', 'rejected')),
    steps              JSONB NOT NULL DEFAULT '[]',
    required_skills    JSONB NOT NULL DEFAULT '[]',
    cycle_time_seconds INT,
    takt_time_seconds  INT,
    quality_checks     JSONB NOT NULL DEFAULT '[]',
    safety_notes       JSONB NOT NULL DEFAULT '[]',
    tools_required     JSONB NOT NULL DEFAULT '[]',
    materials_required JSONB NOT NULL DEFAULT '[]',
    attachments        JSONB NOT NULL DEFAULT '[]',
    approved_by        UUID,
    approved_at        TIMESTAMPTZ,
    -- Item 15: validity window + supersession lineage.
    effective_from     TIMESTAMPTZ,
    effective_to       TIMESTAMPTZ,
    supersedes         UUID REFERENCES standard_work_documents(id) ON DELETE SET NULL,
    version            BIGINT NOT NULL DEFAULT 1,
    created_by         UUID NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, document_number)
);
CREATE INDEX IF NOT EXISTS idx_sw_documents_tenant
    ON standard_work_documents (tenant_id, area);

CREATE TABLE IF NOT EXISTS standard_work_versions (
    id             UUID PRIMARY KEY,
    document_id    UUID NOT NULL REFERENCES standard_work_documents(id) ON DELETE CASCADE,
    tenant_id      UUID NOT NULL,
    version_number INT NOT NULL,
    snapshot       JSONB NOT NULL,
    change_notes   TEXT,
    created_by     UUID NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, version_number)
);
CREATE INDEX IF NOT EXISTS idx_sw_versions_document
    ON standard_work_versions (document_id, version_number);
