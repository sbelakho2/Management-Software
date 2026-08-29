-- Document ingestion (item 72): uploaded shop documents (standards,
-- customer requirements, PFMEAs, work instructions, scanned PDFs) go
-- through a HUMAN-APPROVED pipeline before they can become knowledge —
-- OCR output is never automatically authoritative. Each document draft
-- carries source, extraction, and approval state; on approval it becomes
-- a knowledge pack (under_review -> approved by the ingestion gate).
CREATE TABLE IF NOT EXISTS document_ingestions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    source_path     TEXT NOT NULL,
    mime_type       VARCHAR(100),
    -- The extracted raw text (perception layer output).
    raw_text        TEXT NOT NULL DEFAULT '',
    -- Structured elements (paragraphs, tables, key-value pairs) as
    -- extracted by the parsing layer.
    structured      JSONB NOT NULL DEFAULT '[]',
    -- The semantic extraction: candidate knowledge (authority class,
    -- content, effective window) — a HYPOTHESIS until approved.
    candidate       JSONB,
    status          VARCHAR(30) NOT NULL DEFAULT 'extracted'
                    CHECK (status IN ('extracted', 'under_review', 'approved', 'rejected')),
    uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_document_ingestions_tenant
    ON document_ingestions (tenant_id, status);
