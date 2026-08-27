-- Immutable production event ledger: derived counters (quantity produced,
-- scrap, yield, OEE, completion) come from these events, never from
-- mutable rows edited after the fact.
CREATE TABLE IF NOT EXISTS production_events (
    id          UUID PRIMARY KEY,
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type  VARCHAR(30) NOT NULL
                CHECK (event_type IN ('produced', 'scrapped', 'reworked', 'completed', 'short_closed')),
    operation   VARCHAR(100),
    work_order_id UUID,
    product_id  UUID,
    good_qty    BIGINT NOT NULL DEFAULT 0,
    scrap_qty   BIGINT NOT NULL DEFAULT 0,
    rework_qty  BIGINT NOT NULL DEFAULT 0,
    reason_code VARCHAR(100),
    operator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    machine_id  UUID,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_production_events_tenant_wo
    ON production_events (tenant_id, work_order_id);
CREATE INDEX IF NOT EXISTS idx_production_events_tenant_time
    ON production_events (tenant_id, occurred_at DESC);
