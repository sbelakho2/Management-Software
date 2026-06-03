-- Maintenance management tables for Sensei ERP
--
-- This migration adds maintenance-related tables extending the base
-- equipment and pm_schedules tables from 002_domain_tables. New tables
-- cover assets, maintenance work orders, spare parts, downtime tracking,
-- LOTO procedures, tool management, and warranties.

-- ── Assets ────────────────────────────────────────────────────────────────
-- Asset register for all company assets (extends equipment concept).
CREATE TABLE IF NOT EXISTS assets (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    asset_number        VARCHAR(50) NOT NULL,
    description         TEXT,
    asset_type          VARCHAR(30) NOT NULL DEFAULT 'equipment'
                        CHECK (asset_type IN ('equipment', 'vehicle', 'building', 'tool', 'it_equipment', 'other')),
    location            VARCHAR(255),
    department          VARCHAR(100),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'in_storage', 'in_maintenance', 'disposed', 'retired')),
    category            VARCHAR(100),
    manufacturer        VARCHAR(255),
    model               VARCHAR(255),
    serial_number       VARCHAR(255),
    acquisition_date    TIMESTAMPTZ,
    purchase_price      DOUBLE PRECISION,
    current_value       DOUBLE PRECISION,
    useful_life_months  INT,
    residual_value      DOUBLE PRECISION,
    equipment_id        UUID REFERENCES equipment(id) ON DELETE SET NULL,
    parent_id           UUID REFERENCES assets(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, asset_number)
);

CREATE INDEX idx_assets_tenant ON assets(tenant_id);
CREATE INDEX idx_assets_status ON assets(tenant_id, status);
CREATE INDEX idx_assets_type ON assets(tenant_id, asset_type);
CREATE INDEX idx_assets_location ON assets(tenant_id, location);
CREATE INDEX idx_assets_parent ON assets(parent_id);

-- ── Maintenance Work Orders ───────────────────────────────────────────────
-- Work orders specifically for maintenance activities.
CREATE TABLE IF NOT EXISTS maintenance_work_orders (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    mwo_number          VARCHAR(50) NOT NULL,
    asset_id            UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    equipment_id        UUID REFERENCES equipment(id) ON DELETE SET NULL,
    type                VARCHAR(30) NOT NULL DEFAULT 'corrective'
                        CHECK (type IN ('corrective', 'preventive', 'predictive', 'emergency')),
    priority            VARCHAR(20) NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'emergency')),
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'assigned', 'in_progress', 'completed', 'cancelled')),
    description         TEXT NOT NULL DEFAULT '',
    assigned_to         UUID REFERENCES users(id) ON DELETE SET NULL,
    requested_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    scheduled_start     TIMESTAMPTZ,
    scheduled_end       TIMESTAMPTZ,
    actual_start        TIMESTAMPTZ,
    actual_end          TIMESTAMPTZ,
    downtime_hours      DOUBLE PRECISION NOT NULL DEFAULT 0,
    root_cause          TEXT,
    resolution          TEXT,
    parts_used          JSONB NOT NULL DEFAULT '[]'::jsonb,
    labor_hours         DOUBLE PRECISION NOT NULL DEFAULT 0,
    cost                DOUBLE PRECISION NOT NULL DEFAULT 0,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, mwo_number)
);

CREATE INDEX idx_mwo_tenant ON maintenance_work_orders(tenant_id);
CREATE INDEX idx_mwo_asset ON maintenance_work_orders(asset_id);
CREATE INDEX idx_mwo_equipment ON maintenance_work_orders(equipment_id);
CREATE INDEX idx_mwo_status ON maintenance_work_orders(tenant_id, status);
CREATE INDEX idx_mwo_priority ON maintenance_work_orders(tenant_id, priority);
CREATE INDEX idx_mwo_assigned ON maintenance_work_orders(assigned_to);
CREATE INDEX idx_mwo_scheduled ON maintenance_work_orders(tenant_id, scheduled_start);

-- ── Spare Parts ───────────────────────────────────────────────────────────
-- Spare parts inventory for maintenance.
CREATE TABLE IF NOT EXISTS spare_parts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    part_number         VARCHAR(100) NOT NULL,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    quantity_on_hand    DOUBLE PRECISION NOT NULL DEFAULT 0,
    quantity_reserved   DOUBLE PRECISION NOT NULL DEFAULT 0,
    reorder_point       DOUBLE PRECISION NOT NULL DEFAULT 0,
    reorder_quantity    DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_cost           DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_of_measure     VARCHAR(20) NOT NULL DEFAULT 'pcs',
    supplier_id         UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    lead_time_days      INT,
    location            VARCHAR(255),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, part_number)
);

CREATE INDEX idx_spare_parts_tenant ON spare_parts(tenant_id);
CREATE INDEX idx_spare_parts_supplier ON spare_parts(supplier_id);
CREATE INDEX idx_spare_parts_active ON spare_parts(tenant_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_spare_parts_reorder ON spare_parts(tenant_id)
    WHERE is_active = TRUE AND quantity_on_hand <= reorder_point;

-- ── Downtime Events ───────────────────────────────────────────────────────
-- Equipment/asset downtime tracking.
CREATE TABLE IF NOT EXISTS downtime_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_id            UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    equipment_id        UUID REFERENCES equipment(id) ON DELETE SET NULL,
    start_time          TIMESTAMPTZ NOT NULL,
    end_time            TIMESTAMPTZ,
    reason              TEXT NOT NULL DEFAULT '',
    category            VARCHAR(30) NOT NULL DEFAULT 'unplanned'
                        CHECK (category IN ('planned', 'unplanned', 'changeover', 'break', 'meeting', 'no_demand', 'other')),
    duration_minutes    DOUBLE PRECISION NOT NULL DEFAULT 0,
    work_order_id       UUID REFERENCES maintenance_work_orders(id) ON DELETE SET NULL,
    reported_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_downtime_events_tenant ON downtime_events(tenant_id);
CREATE INDEX idx_downtime_events_asset ON downtime_events(asset_id);
CREATE INDEX idx_downtime_events_start ON downtime_events(start_time DESC);
CREATE INDEX idx_downtime_events_category ON downtime_events(tenant_id, category);

-- ── LOTO Procedures ──────────────────────────────────────────────────────
-- Lockout/Tagout procedures for equipment safety.
CREATE TABLE IF NOT EXISTS loto_procedures (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_id            UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    procedure_number    VARCHAR(50) NOT NULL,
    title               VARCHAR(500) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'active', 'obsolete')),
    steps               JSONB NOT NULL DEFAULT '[]'::jsonb,
    authorized_workers  UUID[] NOT NULL DEFAULT '{}',
    energy_sources      TEXT,
    required_ppe        TEXT,
    review_date         TIMESTAMPTZ,
    approved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, procedure_number)
);

CREATE INDEX idx_loto_procedures_tenant ON loto_procedures(tenant_id);
CREATE INDEX idx_loto_procedures_asset ON loto_procedures(asset_id);
CREATE INDEX idx_loto_procedures_status ON loto_procedures(tenant_id, status);

-- ── Tool Items ────────────────────────────────────────────────────────────
-- Tool crib inventory management.
CREATE TABLE IF NOT EXISTS tool_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    part_number         VARCHAR(100),
    tool_number         VARCHAR(50) NOT NULL,
    description         TEXT,
    quantity            INT NOT NULL DEFAULT 1,
    quantity_available  INT NOT NULL DEFAULT 1,
    status              VARCHAR(20) NOT NULL DEFAULT 'available'
                        CHECK (status IN ('available', 'in_use', 'calibration', 'maintenance', 'retired')),
    location            VARCHAR(255),
    tool_type           VARCHAR(50),
    calibration_due     TIMESTAMPTZ,
    calibration_interval INT NOT NULL DEFAULT 365,
    last_calibration    TIMESTAMPTZ,
    checked_out_to      UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, tool_number)
);

CREATE INDEX idx_tool_items_tenant ON tool_items(tenant_id);
CREATE INDEX idx_tool_items_status ON tool_items(tenant_id, status);
CREATE INDEX idx_tool_items_calibration ON tool_items(calibration_due) WHERE status = 'available';

-- ── Asset Warranties ──────────────────────────────────────────────────────
-- Warranty tracking for assets.
CREATE TABLE IF NOT EXISTS asset_warranties (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_id            UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    vendor              VARCHAR(255) NOT NULL,
    warranty_number     VARCHAR(100),
    start_date          TIMESTAMPTZ NOT NULL,
    end_date            TIMESTAMPTZ NOT NULL,
    terms               TEXT,
    coverage_type       VARCHAR(50),
    contact_info        TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_asset_warranties_tenant ON asset_warranties(tenant_id);
CREATE INDEX idx_asset_warranties_asset ON asset_warranties(asset_id);
CREATE INDEX idx_asset_warranties_active ON asset_warranties(asset_id) WHERE is_active = TRUE;
CREATE INDEX idx_asset_warranties_expiry ON asset_warranties(end_date) WHERE is_active = TRUE;
