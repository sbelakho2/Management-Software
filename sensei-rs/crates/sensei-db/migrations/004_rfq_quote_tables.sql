-- RFQ and quoting tables for Sensei ERP
--
-- This migration adds detailed RFQ and quoting tables that extend the
-- base rfqs and quotes tables from 002_domain_tables. New tables provide
-- line items, versioning, supplier quotes, and qualification tracking.

-- Enable pgvector extension for embedding columns
CREATE EXTENSION IF NOT EXISTS vector;

-- ── RFQ Line Items ────────────────────────────────────────────────────────
-- Individual line items within a Request for Quote.
CREATE TABLE IF NOT EXISTS rfq_line_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rfq_id              UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
    line_number         INT NOT NULL,
    part_number         VARCHAR(100),
    description         TEXT NOT NULL DEFAULT '',
    quantity            DOUBLE PRECISION NOT NULL DEFAULT 1,
    unit_of_measure     VARCHAR(20) NOT NULL DEFAULT 'pcs',
    target_price        DOUBLE PRECISION,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(rfq_id, line_number)
);

CREATE INDEX idx_rfq_line_items_rfq ON rfq_line_items(rfq_id);
CREATE INDEX idx_rfq_line_items_tenant ON rfq_line_items(tenant_id);

-- ── Quote Versions ────────────────────────────────────────────────────────
-- Version history for quotes, tracking changes through negotiation.
CREATE TABLE IF NOT EXISTS quote_versions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    quote_id            UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    version_number      INT NOT NULL DEFAULT 1,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'submitted', 'approved', 'rejected')),
    subtotal            DOUBLE PRECISION NOT NULL DEFAULT 0,
    tax                 DOUBLE PRECISION NOT NULL DEFAULT 0,
    total               DOUBLE PRECISION NOT NULL DEFAULT 0,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(quote_id, version_number)
);

CREATE INDEX idx_quote_versions_quote ON quote_versions(quote_id);
CREATE INDEX idx_quote_versions_tenant ON quote_versions(tenant_id);

-- ── Quote Line Items ──────────────────────────────────────────────────────
-- Individual line items within a quote version.
CREATE TABLE IF NOT EXISTS quote_line_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    quote_id            UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    version_id          UUID NOT NULL REFERENCES quote_versions(id) ON DELETE CASCADE,
    line_number         INT NOT NULL,
    product_id          UUID REFERENCES products(id) ON DELETE SET NULL,
    description         TEXT NOT NULL DEFAULT '',
    quantity            DOUBLE PRECISION NOT NULL DEFAULT 1,
    unit_price          DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_cost           DOUBLE PRECISION NOT NULL DEFAULT 0,
    extended_price      DOUBLE PRECISION NOT NULL DEFAULT 0,
    extended_cost       DOUBLE PRECISION NOT NULL DEFAULT 0,
    lead_time_days      INT,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(version_id, line_number)
);

CREATE INDEX idx_quote_line_items_quote ON quote_line_items(quote_id);
CREATE INDEX idx_quote_line_items_version ON quote_line_items(version_id);
CREATE INDEX idx_quote_line_items_product ON quote_line_items(product_id);
CREATE INDEX idx_quote_line_items_tenant ON quote_line_items(tenant_id);

-- ── Supplier Quotes ───────────────────────────────────────────────────────
-- Quotes received from suppliers in response to RFQs.
CREATE TABLE IF NOT EXISTS supplier_quotes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    supplier_id         UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    rfq_id              UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
    quote_number        VARCHAR(50) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'submitted'
                        CHECK (status IN ('submitted', 'under_review', 'accepted', 'rejected', 'expired')),
    subtotal            DOUBLE PRECISION NOT NULL DEFAULT 0,
    tax                 DOUBLE PRECISION NOT NULL DEFAULT 0,
    total               DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    lead_time_days      INT,
    payment_terms       VARCHAR(100),
    valid_until         TIMESTAMPTZ,
    notes               TEXT,
    embedding           vector(384),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, quote_number)
);

CREATE INDEX idx_supplier_quotes_tenant ON supplier_quotes(tenant_id);
CREATE INDEX idx_supplier_quotes_supplier ON supplier_quotes(supplier_id);
CREATE INDEX idx_supplier_quotes_rfq ON supplier_quotes(rfq_id);
CREATE INDEX idx_supplier_quotes_status ON supplier_quotes(tenant_id, status);

-- ── Qualifications ────────────────────────────────────────────────────────
-- Supplier qualification assessments linked to RFQs.
CREATE TABLE IF NOT EXISTS qualifications (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rfq_id              UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
    supplier_id         UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'approved', 'rejected', 'expired')),
    overall_score       DOUBLE PRECISION NOT NULL DEFAULT 0,
    technical_score     DOUBLE PRECISION NOT NULL DEFAULT 0,
    quality_score       DOUBLE PRECISION NOT NULL DEFAULT 0,
    delivery_score      DOUBLE PRECISION NOT NULL DEFAULT 0,
    cost_score          DOUBLE PRECISION NOT NULL DEFAULT 0,
    notes               TEXT,
    assessed_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    assessed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, rfq_id, supplier_id)
);

CREATE INDEX idx_qualifications_rfq ON qualifications(rfq_id);
CREATE INDEX idx_qualifications_supplier ON qualifications(supplier_id);
CREATE INDEX idx_qualifications_tenant ON qualifications(tenant_id);
CREATE INDEX idx_qualifications_status ON qualifications(tenant_id, status);
