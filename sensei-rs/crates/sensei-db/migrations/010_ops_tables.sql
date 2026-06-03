-- Operations and lean manufacturing tables for Sensei ERP
--
-- This migration adds operations and lean manufacturing tables extending
-- the base andon_events, kanban_cards, a3_reports, risks, and projects
-- from 002_domain_tables. New tables cover kanban boards/columns, obeya,
-- standard work, KPIs, tasks, and additional project tracking.

-- ── Kanban Boards ─────────────────────────────────────────────────────────
-- Visual management boards for workflow tracking.
CREATE TABLE IF NOT EXISTS kanban_boards (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    board_type          VARCHAR(30) NOT NULL DEFAULT 'task'
                        CHECK (board_type IN ('task', 'production', 'maintenance', 'quality', 'project', 'custom')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'archived')),
    description         TEXT,
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    is_default          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kanban_boards_tenant ON kanban_boards(tenant_id);
CREATE INDEX idx_kanban_boards_status ON kanban_boards(tenant_id, status);
CREATE INDEX idx_kanban_boards_type ON kanban_boards(tenant_id, board_type);

-- ── Kanban Columns ────────────────────────────────────────────────────────
-- Columns/lanes within a kanban board.
CREATE TABLE IF NOT EXISTS kanban_columns (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    board_id            UUID NOT NULL REFERENCES kanban_boards(id) ON DELETE CASCADE,
    name                VARCHAR(100) NOT NULL,
    position            INT NOT NULL DEFAULT 0,
    wip_limit           INT,
    column_type         VARCHAR(20) NOT NULL DEFAULT 'normal'
                        CHECK (column_type IN ('backlog', 'normal', 'done', 'blocked')),
    color               VARCHAR(7),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(board_id, name)
);

CREATE INDEX idx_kanban_columns_board ON kanban_columns(board_id);
CREATE INDEX idx_kanban_columns_position ON kanban_columns(board_id, position);

-- ── Obeya Boards ──────────────────────────────────────────────────────────
-- Obeya (big room) visual management boards.
CREATE TABLE IF NOT EXISTS obeya_boards (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    board_number        VARCHAR(50) NOT NULL,
    type                VARCHAR(30) NOT NULL DEFAULT 'daily_management'
                        CHECK (type IN ('daily_management', 'project', 'strategy', 'safety', 'quality', 'custom')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'archived')),
    description         TEXT,
    location            VARCHAR(255),
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    meeting_cadence     VARCHAR(50),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, board_number)
);

CREATE INDEX idx_obeya_boards_tenant ON obeya_boards(tenant_id);
CREATE INDEX idx_obeya_boards_status ON obeya_boards(tenant_id, status);
CREATE INDEX idx_obeya_boards_type ON obeya_boards(tenant_id, type);

-- ── Obeya Items ───────────────────────────────────────────────────────────
-- Items/cards on obeya boards.
CREATE TABLE IF NOT EXISTS obeya_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    board_id            UUID NOT NULL REFERENCES obeya_boards(id) ON DELETE CASCADE,
    type                VARCHAR(30) NOT NULL DEFAULT 'action'
                        CHECK (type IN ('action', 'metric', 'issue', 'idea', 'decision', 'information')),
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'in_progress', 'completed', 'closed')),
    sqdcp_category      VARCHAR(20)
                        CHECK (sqdcp_category IS NULL OR sqdcp_category IN ('safety', 'quality', 'delivery', 'cost', 'people')),
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date            TIMESTAMPTZ,
    priority            VARCHAR(20) DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    position            INT NOT NULL DEFAULT 0,
    data                JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_obeya_items_board ON obeya_items(board_id);
CREATE INDEX idx_obeya_items_tenant ON obeya_items(tenant_id);
CREATE INDEX idx_obeya_items_status ON obeya_items(tenant_id, status);
CREATE INDEX idx_obeya_items_owner ON obeya_items(owner_id);
CREATE INDEX idx_obeya_items_category ON obeya_items(board_id, sqdcp_category);

-- ── Standard Works ────────────────────────────────────────────────────────
-- Standardized work instructions and procedures.
CREATE TABLE IF NOT EXISTS standard_works (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_number     VARCHAR(50) NOT NULL,
    title               VARCHAR(500) NOT NULL,
    product_id          UUID REFERENCES products(id) ON DELETE SET NULL,
    work_center_id      UUID REFERENCES work_centers(id) ON DELETE SET NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'active', 'under_review', 'obsolete')),
    version             VARCHAR(20) NOT NULL DEFAULT '1.0',
    description         TEXT,
    steps               JSONB NOT NULL DEFAULT '[]'::jsonb,
    cycle_time          DOUBLE PRECISION,
    takt_time           DOUBLE PRECISION,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    effective_date      TIMESTAMPTZ,
    review_date         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, document_number)
);

CREATE INDEX idx_standard_works_tenant ON standard_works(tenant_id);
CREATE INDEX idx_standard_works_product ON standard_works(product_id);
CREATE INDEX idx_standard_works_work_center ON standard_works(work_center_id);
CREATE INDEX idx_standard_works_status ON standard_works(tenant_id, status);

-- ── KPI Definitions ───────────────────────────────────────────────────────
-- Key Performance Indicator definitions.
CREATE TABLE IF NOT EXISTS kpi_definitions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    kpi_code            VARCHAR(50) NOT NULL,
    category            VARCHAR(50) NOT NULL DEFAULT 'operational'
                        CHECK (category IN ('safety', 'quality', 'delivery', 'cost', 'people',
                               'operational', 'financial', 'environmental', 'custom')),
    unit                VARCHAR(30) NOT NULL DEFAULT 'percentage',
    target              DOUBLE PRECISION NOT NULL DEFAULT 0,
    threshold           DOUBLE PRECISION NOT NULL DEFAULT 0,
    frequency           VARCHAR(20) NOT NULL DEFAULT 'monthly'
                        CHECK (frequency IN ('hourly', 'daily', 'weekly', 'monthly', 'quarterly', 'annual')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive')),
    description         TEXT,
    formula             TEXT,
    data_source         VARCHAR(100),
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, kpi_code)
);

CREATE INDEX idx_kpi_definitions_tenant ON kpi_definitions(tenant_id);
CREATE INDEX idx_kpi_definitions_category ON kpi_definitions(tenant_id, category);
CREATE INDEX idx_kpi_definitions_status ON kpi_definitions(tenant_id, status);

-- ── KPI Values ────────────────────────────────────────────────────────────
-- KPI measurement values over time.
CREATE TABLE IF NOT EXISTS kpi_values (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    kpi_id              UUID NOT NULL REFERENCES kpi_definitions(id) ON DELETE CASCADE,
    value               DOUBLE PRECISION NOT NULL,
    target              DOUBLE PRECISION,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source              VARCHAR(100),
    notes               TEXT,
    recorded_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kpi_values_kpi ON kpi_values(kpi_id);
CREATE INDEX idx_kpi_values_tenant ON kpi_values(tenant_id);
CREATE INDEX idx_kpi_values_timestamp ON kpi_values(kpi_id, timestamp DESC);

-- ── Tasks ─────────────────────────────────────────────────────────────────
-- General-purpose task tracking across all domains.
CREATE TABLE IF NOT EXISTS tasks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    task_number         VARCHAR(50) NOT NULL,
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'in_progress', 'completed', 'cancelled', 'on_hold')),
    priority            VARCHAR(20) NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    task_type           VARCHAR(30) NOT NULL DEFAULT 'task'
                        CHECK (task_type IN ('task', 'action_item', 'follow_up', 'review', 'approval')),
    assignee_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    reporter_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date            TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    related_entity_type VARCHAR(50),
    related_entity_id   UUID,
    tags                TEXT[] NOT NULL DEFAULT '{}',
    estimated_hours     DOUBLE PRECISION,
    actual_hours        DOUBLE PRECISION,
    parent_task_id      UUID REFERENCES tasks(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, task_number)
);

CREATE INDEX idx_tasks_tenant ON tasks(tenant_id);
CREATE INDEX idx_tasks_status ON tasks(tenant_id, status);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX idx_tasks_reporter ON tasks(reporter_id);
CREATE INDEX idx_tasks_due ON tasks(tenant_id, due_date);
CREATE INDEX idx_tasks_entity ON tasks(related_entity_type, related_entity_id);
CREATE INDEX idx_tasks_parent ON tasks(parent_task_id);
CREATE INDEX idx_tasks_tags ON tasks USING GIN(tags);
