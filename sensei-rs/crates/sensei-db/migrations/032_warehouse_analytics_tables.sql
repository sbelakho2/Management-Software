-- Warehouse operations summary tables.
--
-- Back the warehouse KPI queries in the analytics worker
-- (storage utilization, picking accuracy, order cycle time,
-- dock-to-stock time, inventory accuracy).

CREATE TABLE IF NOT EXISTS warehouse_storage_locations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    location_code   VARCHAR(50) NOT NULL,
    utilization_pct DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, location_code)
);

CREATE TABLE IF NOT EXISTS warehouse_pick_events (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    status      VARCHAR(20) NOT NULL DEFAULT 'correct'
                CHECK (status IN ('correct', 'incorrect', 'missing')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS warehouse_orders (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS warehouse_receipts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    putaway_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS warehouse_cycle_counts (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    count_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_qty  DOUBLE PRECISION NOT NULL DEFAULT 0,
    counted_qty   DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wh_pick_events_date ON warehouse_pick_events (tenant_id, event_date);
CREATE INDEX IF NOT EXISTS idx_wh_orders_completed ON warehouse_orders (tenant_id, completed_at);
CREATE INDEX IF NOT EXISTS idx_wh_receipts_received ON warehouse_receipts (tenant_id, received_at);
CREATE INDEX IF NOT EXISTS idx_wh_cycle_counts_date ON warehouse_cycle_counts (tenant_id, count_date);
