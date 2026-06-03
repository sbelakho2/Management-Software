-- System and cross-cutting tables for Sensei ERP
--
-- This migration adds system-level and cross-cutting tables extending
-- the base attachments, audit_logs, and notifications from earlier
-- migrations. New tables cover notification preferences, data lineage,
-- AI reasoning traces, service state, saved views, sites, escalation
-- policies, notification triggers, knowledge management, and training matrix.

-- ── Notification Preferences ──────────────────────────────────────────────
-- User preferences for notification channels and events.
CREATE TABLE IF NOT EXISTS notification_preferences (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel             VARCHAR(30) NOT NULL DEFAULT 'in_app'
                        CHECK (channel IN ('in_app', 'email', 'sms', 'push', 'webhook')),
    event_type          VARCHAR(100) NOT NULL,
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, channel, event_type)
);

CREATE INDEX idx_notification_prefs_user ON notification_preferences(user_id);
CREATE INDEX idx_notification_prefs_tenant ON notification_preferences(tenant_id);

-- ── Data Lineage Links ────────────────────────────────────────────────────
-- Tracks data flow between entities for traceability.
CREATE TABLE IF NOT EXISTS data_lineage_links (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_entity       VARCHAR(100) NOT NULL,
    source_id           UUID NOT NULL,
    target_entity       VARCHAR(100) NOT NULL,
    target_id           UUID NOT NULL,
    transformation      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_data_lineage_source ON data_lineage_links(source_entity, source_id);
CREATE INDEX idx_data_lineage_target ON data_lineage_links(target_entity, target_id);
CREATE INDEX idx_data_lineage_tenant ON data_lineage_links(tenant_id);

-- ── Reasoning Traces ──────────────────────────────────────────────────────
-- AI agent reasoning traces for audit and debugging.
CREATE TABLE IF NOT EXISTS reasoning_traces (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_type          VARCHAR(100) NOT NULL,
    input               TEXT NOT NULL DEFAULT '',
    output              TEXT NOT NULL DEFAULT '',
    tokens_used         INT NOT NULL DEFAULT 0,
    duration_ms         INT NOT NULL DEFAULT 0,
    model_name          VARCHAR(100),
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reasoning_traces_tenant ON reasoning_traces(tenant_id);
CREATE INDEX idx_reasoning_traces_agent ON reasoning_traces(tenant_id, agent_type);
CREATE INDEX idx_reasoning_traces_created ON reasoning_traces(tenant_id, created_at DESC);

-- ── Service State ─────────────────────────────────────────────────────────
-- Persistent state storage for services (state machines, config, etc.).
CREATE TABLE IF NOT EXISTS service_state (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    service_name        VARCHAR(100) NOT NULL,
    state_key           VARCHAR(255) NOT NULL,
    state_value         JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, service_name, state_key)
);

CREATE INDEX idx_service_state_tenant ON service_state(tenant_id);
CREATE INDEX idx_service_state_service ON service_state(service_name);

-- ── Saved Views ───────────────────────────────────────────────────────────
-- User-customizable views for lists and dashboards.
CREATE TABLE IF NOT EXISTS saved_views (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    entity_type         VARCHAR(100) NOT NULL,
    config              JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_default          BOOLEAN NOT NULL DEFAULT FALSE,
    is_shared           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_saved_views_user ON saved_views(user_id);
CREATE INDEX idx_saved_views_tenant ON saved_views(tenant_id);
CREATE INDEX idx_saved_views_entity ON saved_views(tenant_id, entity_type);

-- ── Sites ─────────────────────────────────────────────────────────────────
-- Physical site/facility locations.
CREATE TABLE IF NOT EXISTS sites (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    site_code           VARCHAR(50) NOT NULL,
    address             TEXT,
    city                VARCHAR(100),
    state               VARCHAR(100),
    postal_code         VARCHAR(20),
    country             VARCHAR(100),
    timezone            VARCHAR(50) NOT NULL DEFAULT 'UTC',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_headquarters     BOOLEAN NOT NULL DEFAULT FALSE,
    contact_phone       VARCHAR(50),
    contact_email       VARCHAR(320),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, site_code)
);

CREATE INDEX idx_sites_tenant ON sites(tenant_id);
CREATE INDEX idx_sites_active ON sites(tenant_id, is_active) WHERE is_active = TRUE;

-- ── Escalation Policies ───────────────────────────────────────────────────
-- Rules for automatic escalation of issues and alerts.
CREATE TABLE IF NOT EXISTS escalation_policies (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    entity_type         VARCHAR(100) NOT NULL,
    rules               JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    description         TEXT,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_escalation_policies_tenant ON escalation_policies(tenant_id);
CREATE INDEX idx_escalation_policies_entity ON escalation_policies(entity_type);
CREATE INDEX idx_escalation_policies_active ON escalation_policies(tenant_id, is_active) WHERE is_active = TRUE;

-- ── Notification Triggers ─────────────────────────────────────────────────
-- Automated notification rules based on events.
CREATE TABLE IF NOT EXISTS notification_triggers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    event_type          VARCHAR(100) NOT NULL,
    entity_type         VARCHAR(100),
    conditions          JSONB NOT NULL DEFAULT '{}'::jsonb,
    actions             JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    description         TEXT,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_notification_triggers_tenant ON notification_triggers(tenant_id);
CREATE INDEX idx_notification_triggers_event ON notification_triggers(event_type);
CREATE INDEX idx_notification_triggers_active ON notification_triggers(tenant_id, is_active) WHERE is_active = TRUE;

-- ── Knowledge Packs ───────────────────────────────────────────────────────
-- Structured knowledge base content for AI and user reference.
CREATE TABLE IF NOT EXISTS knowledge_packs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    category            VARCHAR(100),
    content             JSONB NOT NULL DEFAULT '{}'::jsonb,
    version             VARCHAR(20) NOT NULL DEFAULT '1.0',
    language            VARCHAR(10) NOT NULL DEFAULT 'en',
    tags                TEXT[] NOT NULL DEFAULT '{}',
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'published', 'archived')),
    embedding           vector(384),
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_knowledge_packs_tenant ON knowledge_packs(tenant_id);
CREATE INDEX idx_knowledge_packs_category ON knowledge_packs(tenant_id, category);
CREATE INDEX idx_knowledge_packs_status ON knowledge_packs(tenant_id, status);
CREATE INDEX idx_knowledge_packs_tags ON knowledge_packs USING GIN(tags);

-- ── Learning Modules ──────────────────────────────────────────────────────
-- Training and educational content modules.
CREATE TABLE IF NOT EXISTS learning_modules (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title               VARCHAR(500) NOT NULL,
    module_code         VARCHAR(50) NOT NULL,
    description         TEXT,
    category            VARCHAR(100),
    content_type        VARCHAR(30) NOT NULL DEFAULT 'document'
                        CHECK (content_type IN ('document', 'video', 'interactive', 'quiz', 'scorm')),
    content             JSONB NOT NULL DEFAULT '{}'::jsonb,
    duration_minutes    INT NOT NULL DEFAULT 0,
    difficulty          VARCHAR(20) NOT NULL DEFAULT 'beginner'
                        CHECK (difficulty IN ('beginner', 'intermediate', 'advanced', 'expert')),
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'published', 'archived')),
    version             VARCHAR(20) NOT NULL DEFAULT '1.0',
    prerequisites       UUID[] NOT NULL DEFAULT '{}',
    tags                TEXT[] NOT NULL DEFAULT '{}',
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, module_code)
);

CREATE INDEX idx_learning_modules_tenant ON learning_modules(tenant_id);
CREATE INDEX idx_learning_modules_category ON learning_modules(tenant_id, category);
CREATE INDEX idx_learning_modules_status ON learning_modules(tenant_id, status);
CREATE INDEX idx_learning_modules_tags ON learning_modules USING GIN(tags);

-- ── Training Matrix ───────────────────────────────────────────────────────
-- Skills matrix tracking required vs. actual training per role/site.
CREATE TABLE IF NOT EXISTS training_matrix (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_id             UUID REFERENCES sites(id) ON DELETE SET NULL,
    role                VARCHAR(100) NOT NULL,
    skill               VARCHAR(255) NOT NULL,
    required_level      INT NOT NULL DEFAULT 1 CHECK (required_level BETWEEN 1 AND 5),
    current_level       INT NOT NULL DEFAULT 0 CHECK (current_level BETWEEN 0 AND 5),
    gap                 INT NOT NULL DEFAULT 0,
    employee_id         UUID REFERENCES employees(id) ON DELETE SET NULL,
    training_program_id UUID REFERENCES training_programs(id) ON DELETE SET NULL,
    due_date            TIMESTAMPTZ,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed', 'overdue')),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_training_matrix_tenant ON training_matrix(tenant_id);
CREATE INDEX idx_training_matrix_site ON training_matrix(site_id);
CREATE INDEX idx_training_matrix_role ON training_matrix(tenant_id, role);
CREATE INDEX idx_training_matrix_employee ON training_matrix(employee_id);
CREATE INDEX idx_training_matrix_status ON training_matrix(tenant_id, status);
CREATE INDEX idx_training_matrix_gap ON training_matrix(tenant_id, gap DESC);
