-- Integration architecture corrections (eleventh audit):
--
-- 1. SALES QUOTES are a SEPARATE domain from supplier quotes. The
--    canonical `quotes` table is supplier responses to purchasing RFQs
--    (supplier_id NOT NULL). Customer sales quotations get their own
--    table — the CRM-v2 import and the sales pipeline target THIS table,
--    never the supplier-quote table.
-- 2. RFQ line items are a normalized child table (the base rfqs table has
--    no line_items column).
-- 3. The integration entity map gains source-version semantics: the
--    bridge must distinguish same-event replay, newer version, stale
--    version, and same-version-changed-payload instead of lying
--    "updated=true".
-- 4. An immutable integration INBOX (the audit's envelope architecture):
--    source connectors write envelopes; the importer consumes them.
-- 5. A reconciliation queue for unresolved references (imported sales
--    order lines whose product SKU is not yet mapped).
-- 6. Source checkpoints (watermarks) for incremental synchronization.
-- 7. Dead-letter for quarantined records.

-- ── Sales quotes (customer quotations) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS sales_quotes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    quote_number    VARCHAR(50) NOT NULL,
    customer_id     UUID NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    customer_name   VARCHAR(255) NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'submitted', 'approved', 'rejected',
                                      'converted', 'expired')),
    line_items      JSONB NOT NULL DEFAULT '[]',
    total_amount    NUMERIC(19,4) NOT NULL DEFAULT 0,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    valid_until     TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, quote_number)
);
CREATE INDEX IF NOT EXISTS idx_sales_quotes_tenant
    ON sales_quotes (tenant_id, status);

-- ── RFQ line items ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rfq_line_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rfq_id          UUID NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
    product_id      UUID REFERENCES products(id) ON DELETE SET NULL,
    part_number     VARCHAR(100) NOT NULL,
    quantity        BIGINT NOT NULL,
    unit_of_measure VARCHAR(20) NOT NULL DEFAULT 'pcs',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, rfq_id, part_number)
);
CREATE INDEX IF NOT EXISTS idx_rfq_line_items_rfq
    ON rfq_line_items (tenant_id, rfq_id);

-- ── Integration source-version semantics (item 4) ───────────────────────
ALTER TABLE integration_entity_map
    ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS source_version   VARCHAR(100),
    ADD COLUMN IF NOT EXISTS mapper_version   INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS schema_version   INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS last_applied_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_seen_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS tombstoned       BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS tombstoned_at    TIMESTAMPTZ;

-- ── Immutable integration inbox (envelope architecture) ─────────────────
CREATE TABLE IF NOT EXISTS integration_inbox (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_system     VARCHAR(50) NOT NULL,
    source_entity     VARCHAR(50) NOT NULL,
    source_id         VARCHAR(100) NOT NULL,
    source_version    VARCHAR(100),
    source_updated_at TIMESTAMPTZ,
    source_event_id   VARCHAR(100),
    extraction_run_id VARCHAR(100),
    schema_version    INT NOT NULL DEFAULT 1,
    mapper_version    INT NOT NULL DEFAULT 1,
    payload_hash      VARCHAR(64) NOT NULL,
    raw_payload       JSONB NOT NULL,
    received_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at      TIMESTAMPTZ,
    status            VARCHAR(30) NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'applied', 'duplicate', 'stale',
                                        'conflict', 'quarantined', 'dead')),
    error             TEXT,
    UNIQUE (tenant_id, source_system, source_entity, source_id, source_event_id)
);

-- ── Reconciliation queue (unresolved references) ────────────────────────
CREATE TABLE IF NOT EXISTS integration_reconciliation (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_system   VARCHAR(50) NOT NULL,
    source_entity   VARCHAR(50) NOT NULL,
    source_id       VARCHAR(100) NOT NULL,
    reference_kind  VARCHAR(50) NOT NULL,   -- 'product_sku', 'account_id', ...
    reference_value VARCHAR(255) NOT NULL,
    context         JSONB NOT NULL DEFAULT '{}',
    status          VARCHAR(30) NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'resolved', 'ignored')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    UNIQUE (tenant_id, source_system, source_entity, source_id, reference_kind, reference_value)
);

-- ── Source checkpoints (incremental sync watermark) ─────────────────────
CREATE TABLE IF NOT EXISTS integration_checkpoints (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_system   VARCHAR(50) NOT NULL,
    source_table    VARCHAR(100) NOT NULL,
    watermark       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_run_id     VARCHAR(100),
    last_run_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, source_system, source_table)
);

-- ── Dead letter (quarantined records) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS integration_dead_letter (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_system   VARCHAR(50) NOT NULL,
    source_entity   VARCHAR(50) NOT NULL,
    source_id       VARCHAR(100) NOT NULL,
    payload_hash    VARCHAR(64),
    error           TEXT NOT NULL,
    error_kind      VARCHAR(50) NOT NULL,  -- validation | dependency | conflict | transient
    attempts        INT NOT NULL DEFAULT 1,
    quarantined_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, source_system, source_entity, source_id, payload_hash)
);

-- ── Fail-closed RLS for EVERY tenant-owned table (item 26): the
--    invariant is chain-wide, not table-by-table. Every table that HAS a
--    tenant_id column gets ENABLE + FORCE RLS and the tenant_isolation
--    policy. Tables without a tenant_id column (dedupe/system tables) are
--    intentionally exempt. The CI RLS audit (db-contract gate) enforces
--    the same invariant for the whole chain — a future migration that
--    creates a tenant-owned table without isolation fails the gate. ──
DO $$
DECLARE t text;
BEGIN
    FOR t IN
        SELECT c.relname::text
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND EXISTS (
              SELECT 1 FROM information_schema.columns col
              WHERE col.table_schema = 'public'
                AND col.table_name = c.relname
                AND col.column_name = 'tenant_id'
          )
          AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity)
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        -- 070 already created this policy on some tables; the definition
        -- is identical, so drop-and-recreate is idempotent.
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', t);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I USING (tenant_id = current_setting(''app.tenant_id'', true)::uuid)',
            t
        );
    END LOOP;
END $$;
