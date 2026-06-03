-- Quality management tables for Sensei ERP
--
-- This migration adds comprehensive quality management tables extending
-- the base quality tables (inspections, audits, msa_studies, etc.) from
-- 002_domain_tables. New tables cover non-conformances, CAPA actions,
-- inspection plans, gauges, calibration, QMS documents, FMEA, NPI,
-- customer complaints, 8D reports, and more.

-- ── Non-Conformances ──────────────────────────────────────────────────────
-- Extended non-conformance tracking (complements ncr_reports with richer data).
CREATE TABLE IF NOT EXISTS non_conformances (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nc_number           VARCHAR(50) NOT NULL,
    nc_type             VARCHAR(30) NOT NULL DEFAULT 'internal'
                        CHECK (nc_type IN ('internal', 'external', 'supplier', 'customer', 'process')),
    severity            VARCHAR(20) NOT NULL DEFAULT 'minor'
                        CHECK (severity IN ('minor', 'major', 'critical')),
    status              VARCHAR(30) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'under_investigation', 'dispositioned',
                               'in_progress', 'closed', 'rejected')),
    disposition         VARCHAR(30)
                        CHECK (disposition IS NULL OR disposition IN ('use_as_is', 'rework', 'repair', 'scrap', 'return')),
    product_id          UUID REFERENCES products(id) ON DELETE SET NULL,
    work_order_id       UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    detected_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    detected_at         TIMESTAMPTZ,
    description         TEXT NOT NULL DEFAULT '',
    root_cause          TEXT,
    corrective_action   TEXT,
    resolved_at         TIMESTAMPTZ,
    closed_by           UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, nc_number)
);

CREATE INDEX idx_non_conformances_tenant ON non_conformances(tenant_id);
CREATE INDEX idx_non_conformances_status ON non_conformances(tenant_id, status);
CREATE INDEX idx_non_conformances_severity ON non_conformances(tenant_id, severity);
CREATE INDEX idx_non_conformances_product ON non_conformances(product_id);
CREATE INDEX idx_non_conformances_work_order ON non_conformances(work_order_id);
CREATE INDEX idx_non_conformances_detected ON non_conformances(detected_by);

-- ── CAPA Actions ──────────────────────────────────────────────────────────
-- Individual corrective/preventive actions within a CAPA.
CREATE TABLE IF NOT EXISTS capa_actions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    capa_id             UUID NOT NULL REFERENCES capas(id) ON DELETE CASCADE,
    action_type         VARCHAR(30) NOT NULL DEFAULT 'corrective'
                        CHECK (action_type IN ('corrective', 'preventive', 'containment')),
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed', 'verified', 'overdue')),
    description         TEXT NOT NULL DEFAULT '',
    assigned_to         UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date            TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    verified_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at         TIMESTAMPTZ,
    verification_notes  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_capa_actions_capa ON capa_actions(capa_id);
CREATE INDEX idx_capa_actions_tenant ON capa_actions(tenant_id);
CREATE INDEX idx_capa_actions_status ON capa_actions(tenant_id, status);
CREATE INDEX idx_capa_actions_assigned ON capa_actions(assigned_to);

-- ── Inspection Plans ──────────────────────────────────────────────────────
-- Plans defining inspection requirements for products.
CREATE TABLE IF NOT EXISTS inspection_plans (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    plan_number         VARCHAR(50) NOT NULL,
    plan_type           VARCHAR(30) NOT NULL DEFAULT 'in_process'
                        CHECK (plan_type IN ('incoming', 'in_process', 'final', 'fai', 'aql')),
    name                VARCHAR(255) NOT NULL,
    frequency           VARCHAR(50),
    sample_size         INT NOT NULL DEFAULT 1,
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('draft', 'active', 'inactive')),
    description         TEXT,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, plan_number)
);

CREATE INDEX idx_inspection_plans_tenant ON inspection_plans(tenant_id);
CREATE INDEX idx_inspection_plans_product ON inspection_plans(product_id);
CREATE INDEX idx_inspection_plans_status ON inspection_plans(tenant_id, status);

-- ── Inspection Characteristics ────────────────────────────────────────────
-- Measurable characteristics within an inspection plan.
CREATE TABLE IF NOT EXISTS inspection_characteristics (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id                 UUID NOT NULL REFERENCES inspection_plans(id) ON DELETE CASCADE,
    sequence                INT NOT NULL DEFAULT 1,
    name                    VARCHAR(255) NOT NULL,
    characteristic_type     VARCHAR(30) NOT NULL DEFAULT 'variable'
                            CHECK (characteristic_type IN ('variable', 'attribute', 'visual')),
    nominal                 DOUBLE PRECISION,
    upper_spec              DOUBLE PRECISION,
    lower_spec              DOUBLE PRECISION,
    unit                    VARCHAR(30),
    criticality             VARCHAR(20) NOT NULL DEFAULT 'major'
                            CHECK (criticality IN ('critical', 'major', 'minor')),
    inspection_method       VARCHAR(100),
    gauge_id                UUID,
    required                BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(plan_id, sequence)
);

CREATE INDEX idx_inspection_chars_plan ON inspection_characteristics(plan_id);
CREATE INDEX idx_inspection_chars_tenant ON inspection_characteristics(tenant_id);

-- ── Inspection Records ────────────────────────────────────────────────────
-- Records of inspections performed against plans.
CREATE TABLE IF NOT EXISTS inspection_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan_id             UUID NOT NULL REFERENCES inspection_plans(id) ON DELETE CASCADE,
    work_order_id       UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    lot_number          VARCHAR(100),
    sample_size         INT NOT NULL DEFAULT 1,
    result              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (result IN ('pending', 'pass', 'fail', 'conditional')),
    inspector_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    inspected_at        TIMESTAMPTZ,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inspection_records_plan ON inspection_records(plan_id);
CREATE INDEX idx_inspection_records_tenant ON inspection_records(tenant_id);
CREATE INDEX idx_inspection_records_result ON inspection_records(tenant_id, result);
CREATE INDEX idx_inspection_records_work_order ON inspection_records(work_order_id);
CREATE INDEX idx_inspection_records_inspector ON inspection_records(inspector_id);

-- ── Inspection Measurements ───────────────────────────────────────────────
-- Individual measurements within an inspection record.
CREATE TABLE IF NOT EXISTS inspection_measurements (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    record_id               UUID NOT NULL REFERENCES inspection_records(id) ON DELETE CASCADE,
    characteristic_id       UUID NOT NULL REFERENCES inspection_characteristics(id) ON DELETE CASCADE,
    measured_value          DOUBLE PRECISION NOT NULL DEFAULT 0,
    pass_fail               BOOLEAN NOT NULL DEFAULT TRUE,
    deviation               DOUBLE PRECISION,
    notes                   TEXT,
    measured_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inspection_measurements_record ON inspection_measurements(record_id);
CREATE INDEX idx_inspection_measurements_char ON inspection_measurements(characteristic_id);
CREATE INDEX idx_inspection_measurements_tenant ON inspection_measurements(tenant_id);

-- ── Gauges ────────────────────────────────────────────────────────────────
-- Measurement instruments and gauges.
CREATE TABLE IF NOT EXISTS gauges (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    gauge_id                VARCHAR(50) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    gauge_type              VARCHAR(30) NOT NULL DEFAULT 'general'
                            CHECK (gauge_type IN ('caliper', 'micrometer', 'height_gauge', 'cmm',
                                   'go_no_go', 'thread_gauge', 'general', 'other')),
    status                  VARCHAR(20) NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'out_of_calibration', 'retired', 'lost')),
    location                VARCHAR(255),
    manufacturer            VARCHAR(255),
    model                   VARCHAR(255),
    serial_number           VARCHAR(255),
    resolution              DOUBLE PRECISION,
    calibration_interval    INT NOT NULL DEFAULT 365,
    calibration_interval_unit VARCHAR(20) NOT NULL DEFAULT 'days'
                            CHECK (calibration_interval_unit IN ('days', 'weeks', 'months')),
    last_calibration_date   TIMESTAMPTZ,
    next_calibration_due    TIMESTAMPTZ,
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, gauge_id)
);

CREATE INDEX idx_gauges_tenant ON gauges(tenant_id);
CREATE INDEX idx_gauges_status ON gauges(tenant_id, status);
CREATE INDEX idx_gauges_calibration_due ON gauges(next_calibration_due) WHERE status = 'active';

-- ── Calibration Events ────────────────────────────────────────────────────
-- Records of gauge calibration activities.
CREATE TABLE IF NOT EXISTS calibration_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    gauge_id            UUID NOT NULL REFERENCES gauges(id) ON DELETE CASCADE,
    calibration_date    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    next_due            TIMESTAMPTZ NOT NULL,
    result              VARCHAR(20) NOT NULL DEFAULT 'pass'
                        CHECK (result IN ('pass', 'fail', 'conditional', 'as_found_pass', 'as_found_fail')),
    performed_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    vendor              VARCHAR(255),
    certificate_number  VARCHAR(100),
    uncertainty         DOUBLE PRECISION,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_calibration_events_gauge ON calibration_events(gauge_id);
CREATE INDEX idx_calibration_events_tenant ON calibration_events(tenant_id);
CREATE INDEX idx_calibration_events_date ON calibration_events(calibration_date DESC);

-- ── MSA Measurements ──────────────────────────────────────────────────────
-- Individual measurements within an MSA study.
CREATE TABLE IF NOT EXISTS msa_measurements (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    study_id            UUID NOT NULL REFERENCES msa_studies(id) ON DELETE CASCADE,
    operator_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    part_number         INT NOT NULL,
    trial_number        INT NOT NULL,
    measured_value      DOUBLE PRECISION NOT NULL,
    notes               TEXT,
    measured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_msa_measurements_study ON msa_measurements(study_id);
CREATE INDEX idx_msa_measurements_tenant ON msa_measurements(tenant_id);
CREATE INDEX idx_msa_measurements_operator ON msa_measurements(operator_id);

-- ── MSA Results ───────────────────────────────────────────────────────────
-- Computed results from MSA studies.
CREATE TABLE IF NOT EXISTS msa_results (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    study_id            UUID NOT NULL REFERENCES msa_studies(id) ON DELETE CASCADE,
    grr_percent         DOUBLE PRECISION NOT NULL DEFAULT 0,
    grr_contribution    DOUBLE PRECISION NOT NULL DEFAULT 0,
    ndc                 INT NOT NULL DEFAULT 0,
    repeatability       DOUBLE PRECISION NOT NULL DEFAULT 0,
    reproducibility     DOUBLE PRECISION NOT NULL DEFAULT 0,
    part_variation      DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_variation     DOUBLE PRECISION NOT NULL DEFAULT 0,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(study_id)
);

CREATE INDEX idx_msa_results_study ON msa_results(study_id);
CREATE INDEX idx_msa_results_tenant ON msa_results(tenant_id);

-- ── QMS Documents ─────────────────────────────────────────────────────────
-- Quality Management System controlled documents.
CREATE TABLE IF NOT EXISTS qms_documents (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_number     VARCHAR(50) NOT NULL,
    title               VARCHAR(500) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'under_review', 'approved', 'published', 'obsolete')),
    category            VARCHAR(50) NOT NULL DEFAULT 'procedure'
                        CHECK (category IN ('policy', 'procedure', 'work_instruction', 'form',
                               'standard', 'manual', 'record', 'other')),
    version             VARCHAR(20) NOT NULL DEFAULT '1.0',
    effective_date      TIMESTAMPTZ,
    review_date         TIMESTAMPTZ,
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, document_number)
);

CREATE INDEX idx_qms_documents_tenant ON qms_documents(tenant_id);
CREATE INDEX idx_qms_documents_status ON qms_documents(tenant_id, status);
CREATE INDEX idx_qms_documents_category ON qms_documents(tenant_id, category);
CREATE INDEX idx_qms_documents_owner ON qms_documents(owner_id);

-- ── Quality Audits ────────────────────────────────────────────────────────
-- Extended quality audit tracking (complements the base audits table).
CREATE TABLE IF NOT EXISTS quality_audits (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    audit_number        VARCHAR(50) NOT NULL,
    audit_type          VARCHAR(30) NOT NULL DEFAULT 'internal'
                        CHECK (audit_type IN ('internal', 'external', 'supplier', 'regulatory', 'process', 'product')),
    status              VARCHAR(30) NOT NULL DEFAULT 'planned'
                        CHECK (status IN ('planned', 'scheduled', 'in_progress', 'completed', 'closed', 'cancelled')),
    scheduled_date      TIMESTAMPTZ,
    completed_date      TIMESTAMPTZ,
    auditor_id          UUID REFERENCES users(id) ON DELETE SET NULL,
    scope               TEXT NOT NULL DEFAULT '',
    findings_summary    TEXT,
    score               DOUBLE PRECISION,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, audit_number)
);

CREATE INDEX idx_quality_audits_tenant ON quality_audits(tenant_id);
CREATE INDEX idx_quality_audits_status ON quality_audits(tenant_id, status);
CREATE INDEX idx_quality_audits_type ON quality_audits(tenant_id, audit_type);
CREATE INDEX idx_quality_audits_auditor ON quality_audits(auditor_id);

-- ── First Article Inspections ─────────────────────────────────────────────
-- FAI records for new or changed products.
CREATE TABLE IF NOT EXISTS first_article_inspections (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    fai_number          VARCHAR(50) NOT NULL,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    work_order_id       UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'planned'
                        CHECK (status IN ('planned', 'in_progress', 'completed', 'failed')),
    performed_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    performed_at        TIMESTAMPTZ,
    result              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (result IN ('pending', 'pass', 'fail', 'conditional')),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, fai_number)
);

CREATE INDEX idx_fai_tenant ON first_article_inspections(tenant_id);
CREATE INDEX idx_fai_product ON first_article_inspections(product_id);
CREATE INDEX idx_fai_status ON first_article_inspections(tenant_id, status);

-- ── Self Inspections ──────────────────────────────────────────────────────
-- Operator self-inspection records.
CREATE TABLE IF NOT EXISTS self_inspections (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    work_order_id       UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    operator_id         UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    inspected_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    result              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (result IN ('pending', 'pass', 'fail', 'conditional')),
    characteristics     JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_self_inspections_tenant ON self_inspections(tenant_id);
CREATE INDEX idx_self_inspections_product ON self_inspections(product_id);
CREATE INDEX idx_self_inspections_work_order ON self_inspections(work_order_id);
CREATE INDEX idx_self_inspections_operator ON self_inspections(operator_id);

-- ── Customer Complaints ───────────────────────────────────────────────────
-- Customer complaint tracking and resolution.
CREATE TABLE IF NOT EXISTS customer_complaints (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    complaint_number    VARCHAR(50) NOT NULL,
    account_id          UUID REFERENCES accounts(id) ON DELETE SET NULL,
    contact_id          UUID REFERENCES contacts(id) ON DELETE SET NULL,
    status              VARCHAR(30) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'acknowledged', 'investigating', 'action_defined',
                               'in_progress', 'resolved', 'closed')),
    severity            VARCHAR(20) NOT NULL DEFAULT 'minor'
                        CHECK (severity IN ('minor', 'major', 'critical')),
    complaint_type      VARCHAR(30) NOT NULL DEFAULT 'quality'
                        CHECK (complaint_type IN ('quality', 'delivery', 'service', 'documentation', 'packaging', 'other')),
    product_id          UUID REFERENCES products(id) ON DELETE SET NULL,
    description         TEXT NOT NULL DEFAULT '',
    resolution          TEXT,
    received_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ,
    resolved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, complaint_number)
);

CREATE INDEX idx_customer_complaints_tenant ON customer_complaints(tenant_id);
CREATE INDEX idx_customer_complaints_status ON customer_complaints(tenant_id, status);
CREATE INDEX idx_customer_complaints_account ON customer_complaints(account_id);
CREATE INDEX idx_customer_complaints_severity ON customer_complaints(tenant_id, severity);

-- ── 8D Reports ────────────────────────────────────────────────────────────
-- Eight Disciplines problem-solving reports linked to complaints.
CREATE TABLE IF NOT EXISTS eight_d_reports (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    report_number       VARCHAR(50) NOT NULL,
    complaint_id        UUID NOT NULL REFERENCES customer_complaints(id) ON DELETE CASCADE,
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'in_progress', 'completed', 'closed')),
    d1_team             JSONB NOT NULL DEFAULT '{}'::jsonb,
    d2_problem          TEXT,
    d3_interim          TEXT,
    d4_root_cause       TEXT,
    d5_corrective       TEXT,
    d6_implement        TEXT,
    d7_preventive       TEXT,
    d8_closure          JSONB NOT NULL DEFAULT '{}'::jsonb,
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date            TIMESTAMPTZ,
    closed_at           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, report_number)
);

CREATE INDEX idx_eight_d_reports_tenant ON eight_d_reports(tenant_id);
CREATE INDEX idx_eight_d_reports_complaint ON eight_d_reports(complaint_id);
CREATE INDEX idx_eight_d_reports_status ON eight_d_reports(tenant_id, status);

-- ── Management Reviews ────────────────────────────────────────────────────
-- QMS management review records.
CREATE TABLE IF NOT EXISTS management_reviews (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    review_number       VARCHAR(50) NOT NULL,
    review_date         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status              VARCHAR(20) NOT NULL DEFAULT 'planned'
                        CHECK (status IN ('planned', 'in_progress', 'completed')),
    scope               TEXT NOT NULL DEFAULT '',
    findings            TEXT,
    actions             TEXT,
    next_review_date    TIMESTAMPTZ,
    chairperson_id      UUID REFERENCES users(id) ON DELETE SET NULL,
    participants        UUID[],
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, review_number)
);

CREATE INDEX idx_management_reviews_tenant ON management_reviews(tenant_id);
CREATE INDEX idx_management_reviews_status ON management_reviews(tenant_id, status);
CREATE INDEX idx_management_reviews_date ON management_reviews(tenant_id, review_date DESC);

-- ── Process Capability Studies ────────────────────────────────────────────
-- Statistical process capability (Cp, Cpk) studies.
CREATE TABLE IF NOT EXISTS process_capability_studies (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    characteristic      VARCHAR(255) NOT NULL,
    cp                  DOUBLE PRECISION NOT NULL DEFAULT 0,
    cpk                 DOUBLE PRECISION NOT NULL DEFAULT 0,
    pp                  DOUBLE PRECISION NOT NULL DEFAULT 0,
    ppk                 DOUBLE PRECISION NOT NULL DEFAULT 0,
    sample_size         INT NOT NULL DEFAULT 0,
    mean                DOUBLE PRECISION NOT NULL DEFAULT 0,
    stddev              DOUBLE PRECISION NOT NULL DEFAULT 0,
    usl                 DOUBLE PRECISION,
    lsl                 DOUBLE PRECISION,
    target              DOUBLE PRECISION,
    performed_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    performed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_process_capability_tenant ON process_capability_studies(tenant_id);
CREATE INDEX idx_process_capability_product ON process_capability_studies(product_id);

-- ── Control Plans ─────────────────────────────────────────────────────────
-- Production control plans defining inspection and monitoring requirements.
CREATE TABLE IF NOT EXISTS control_plans (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    plan_number         VARCHAR(50) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'active', 'inactive')),
    version             VARCHAR(20) NOT NULL DEFAULT '1.0',
    characteristics     JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, plan_number)
);

CREATE INDEX idx_control_plans_tenant ON control_plans(tenant_id);
CREATE INDEX idx_control_plans_product ON control_plans(product_id);
CREATE INDEX idx_control_plans_status ON control_plans(tenant_id, status);

-- ── PFMEA Lite ────────────────────────────────────────────────────────────
-- Lightweight Process Failure Mode and Effects Analysis.
CREATE TABLE IF NOT EXISTS pfmea_lite (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    process_step        VARCHAR(255) NOT NULL,
    failure_mode        VARCHAR(500) NOT NULL,
    effect              TEXT NOT NULL DEFAULT '',
    severity            INT NOT NULL DEFAULT 1 CHECK (severity BETWEEN 1 AND 10),
    occurrence          INT NOT NULL DEFAULT 1 CHECK (occurrence BETWEEN 1 AND 10),
    detection           INT NOT NULL DEFAULT 1 CHECK (detection BETWEEN 1 AND 10),
    rpn                 INT NOT NULL DEFAULT 1,
    recommended_action  TEXT,
    responsible         UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date            TIMESTAMPTZ,
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'in_progress', 'completed', 'closed')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pfmea_tenant ON pfmea_lite(tenant_id);
CREATE INDEX idx_pfmea_product ON pfmea_lite(product_id);
CREATE INDEX idx_pfmea_rpn ON pfmea_lite(tenant_id, rpn DESC);

-- ── NPI Projects ──────────────────────────────────────────────────────────
-- New Product Introduction projects.
CREATE TABLE IF NOT EXISTS npi_projects (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_number      VARCHAR(50) NOT NULL,
    name                VARCHAR(500) NOT NULL,
    status              VARCHAR(30) NOT NULL DEFAULT 'intake'
                        CHECK (status IN ('intake', 'dfm', 'prototype', 'pilot', 'sop', 'completed', 'cancelled')),
    product_id          UUID REFERENCES products(id) ON DELETE SET NULL,
    stage               VARCHAR(30) NOT NULL DEFAULT 'intake'
                        CHECK (stage IN ('intake', 'dfm', 'prototype', 'pilot', 'sop')),
    target_launch       TIMESTAMPTZ,
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    description         TEXT,
    budget              DOUBLE PRECISION,
    actual_cost         DOUBLE PRECISION,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, project_number)
);

CREATE INDEX idx_npi_projects_tenant ON npi_projects(tenant_id);
CREATE INDEX idx_npi_projects_status ON npi_projects(tenant_id, status);
CREATE INDEX idx_npi_projects_product ON npi_projects(product_id);
CREATE INDEX idx_npi_projects_owner ON npi_projects(owner_id);
