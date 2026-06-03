-- Production and manufacturing tables for Sensei ERP
--
-- This migration adds production-related tables that extend the base
-- products, bom_items, work_centers, work_orders, and production_orders
-- from earlier migrations. New tables cover routings, stations,
-- work order operations, and production cells.

-- ── Routings ──────────────────────────────────────────────────────────────
-- Manufacturing routings defining the sequence of operations for a product.
CREATE TABLE IF NOT EXISTS routings (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sequence            INT NOT NULL DEFAULT 1,
    work_center_id      UUID NOT NULL REFERENCES work_centers(id) ON DELETE CASCADE,
    operation           VARCHAR(255) NOT NULL,
    operation_code      VARCHAR(50),
    standard_time       DOUBLE PRECISION NOT NULL DEFAULT 0,
    setup_time          DOUBLE PRECISION NOT NULL DEFAULT 0,
    move_time           DOUBLE PRECISION NOT NULL DEFAULT 0,
    queue_time          DOUBLE PRECISION NOT NULL DEFAULT 0,
    description         TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, product_id, sequence)
);

CREATE INDEX idx_routings_tenant ON routings(tenant_id);
CREATE INDEX idx_routings_product ON routings(product_id);
CREATE INDEX idx_routings_work_center ON routings(work_center_id);
CREATE INDEX idx_routings_active ON routings(product_id, is_active) WHERE is_active = TRUE;

-- ── Stations ──────────────────────────────────────────────────────────────
-- Individual workstations within work centers.
CREATE TABLE IF NOT EXISTS stations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    work_center_id      UUID NOT NULL REFERENCES work_centers(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    station_number      VARCHAR(50) NOT NULL,
    station_type        VARCHAR(30) NOT NULL DEFAULT 'manual'
                        CHECK (station_type IN ('manual', 'cnc', 'robotic', 'assembly', 'inspection', 'packaging')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'maintenance', 'retired')),
    description         TEXT,
    equipment_id        UUID REFERENCES equipment(id) ON DELETE SET NULL,
    capacity            DOUBLE PRECISION,
    efficiency          DOUBLE PRECISION DEFAULT 1.0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, station_number)
);

CREATE INDEX idx_stations_tenant ON stations(tenant_id);
CREATE INDEX idx_stations_work_center ON stations(work_center_id);
CREATE INDEX idx_stations_status ON stations(tenant_id, status);
CREATE INDEX idx_stations_active ON stations(work_center_id) WHERE status = 'active';

-- ── Work Order Operations ─────────────────────────────────────────────────
-- Individual operations within a work order, tracking progress per station.
CREATE TABLE IF NOT EXISTS work_order_operations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    work_order_id       UUID NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    sequence            INT NOT NULL DEFAULT 1,
    station_id          UUID NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    operation           VARCHAR(255) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed', 'skipped', 'on_hold')),
    standard_time       DOUBLE PRECISION NOT NULL DEFAULT 0,
    actual_time         DOUBLE PRECISION,
    setup_time          DOUBLE PRECISION NOT NULL DEFAULT 0,
    actual_setup_time   DOUBLE PRECISION,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    operator_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(work_order_id, sequence)
);

CREATE INDEX idx_wo_ops_tenant ON work_order_operations(tenant_id);
CREATE INDEX idx_wo_ops_work_order ON work_order_operations(work_order_id);
CREATE INDEX idx_wo_ops_station ON work_order_operations(station_id);
CREATE INDEX idx_wo_ops_status ON work_order_operations(tenant_id, status);

-- ── Production Cells ──────────────────────────────────────────────────────
-- Groupings of work centers into manufacturing cells (lean manufacturing).
CREATE TABLE IF NOT EXISTS production_cells (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    cell_number         VARCHAR(50) NOT NULL,
    cell_type           VARCHAR(30) NOT NULL DEFAULT 'manufacturing'
                        CHECK (cell_type IN ('manufacturing', 'assembly', 'painting', 'welding', 'inspection', 'packaging')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'reconfiguring')),
    description         TEXT,
    location            VARCHAR(255),
    supervisor_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, cell_number)
);

CREATE INDEX idx_production_cells_tenant ON production_cells(tenant_id);
CREATE INDEX idx_production_cells_status ON production_cells(tenant_id, status);

-- ── Production Cell Work Centers ──────────────────────────────────────────
-- Junction table linking production cells to work centers.
CREATE TABLE IF NOT EXISTS production_cell_work_centers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cell_id             UUID NOT NULL REFERENCES production_cells(id) ON DELETE CASCADE,
    work_center_id      UUID NOT NULL REFERENCES work_centers(id) ON DELETE CASCADE,
    sequence            INT NOT NULL DEFAULT 1,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(cell_id, work_center_id)
);

CREATE INDEX idx_pcwc_cell ON production_cell_work_centers(cell_id);
CREATE INDEX idx_pcwc_work_center ON production_cell_work_centers(work_center_id);
