-- Domain tables for Sensei ERP
--
-- This migration adds all business-domain tables that depend on the
-- foundational schema (tenants, users, roles) from 001_initial_schema.
-- Tables are organized by business domain in alphabetical order.

-- ── Quality Domain ────────────────────────────────────────────────────────

-- Inspections: quality checks on products, processes, or incoming materials.
CREATE TABLE IF NOT EXISTS inspections (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    inspection_number   VARCHAR(50) NOT NULL,
    inspection_type     VARCHAR(50) NOT NULL
                        CHECK (inspection_type IN ('incoming', 'in_process', 'final', 'fai', 'self', 'aql')),
    product_id          UUID,
    work_order_id       UUID,
    result              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (result IN ('pending', 'pass', 'fail', 'conditional')),
    inspector_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    status              VARCHAR(30) NOT NULL DEFAULT 'planned'
                        CHECK (status IN ('planned', 'in_progress', 'completed', 'cancelled')),
    notes               TEXT,
    inspected_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, inspection_number)
);

CREATE INDEX idx_inspections_tenant ON inspections(tenant_id);
CREATE INDEX idx_inspections_status ON inspections(tenant_id, status);
CREATE INDEX idx_inspections_product ON inspections(tenant_id, product_id);
CREATE INDEX idx_inspections_result ON inspections(tenant_id, result);

-- Audits: quality management system audits (internal, external, supplier, etc.).
CREATE TABLE IF NOT EXISTS audits (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    audit_number        VARCHAR(50) NOT NULL,
    audit_type          VARCHAR(30) NOT NULL
                        CHECK (audit_type IN ('internal', 'external', 'supplier', 'regulatory', 'certification', 'layered', 'process', 'product', 'system')),
    status              VARCHAR(30) NOT NULL DEFAULT 'planned'
                        CHECK (status IN ('planned', 'scheduled', 'in_progress', 'completed', 'closed', 'cancelled')),
    title               VARCHAR(500) NOT NULL,
    scope               TEXT NOT NULL DEFAULT '',
    area                VARCHAR(255) NOT NULL DEFAULT '',
    lead_auditor_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    scheduled_date      TIMESTAMPTZ,
    start_date          TIMESTAMPTZ,
    completion_date     TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, audit_number)
);

CREATE INDEX idx_audits_tenant ON audits(tenant_id);
CREATE INDEX idx_audits_status ON audits(tenant_id, status);
CREATE INDEX idx_audits_type ON audits(tenant_id, audit_type);
CREATE INDEX idx_audits_scheduled ON audits(tenant_id, scheduled_date);

-- Audit findings: non-conformances or observations identified during audits.
CREATE TABLE IF NOT EXISTS audit_findings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    audit_id                UUID NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    finding_number          VARCHAR(50) NOT NULL,
    severity                VARCHAR(20) NOT NULL
                            CHECK (severity IN ('observation', 'minor', 'major', 'critical')),
    status                  VARCHAR(30) NOT NULL DEFAULT 'open'
                            CHECK (status IN ('open', 'accepted', 'in_progress', 'implemented', 'verified', 'closed', 'waived')),
    description             TEXT NOT NULL,
    clause                  VARCHAR(255),
    area                    VARCHAR(255),
    implementation_notes    TEXT,
    verified_by             UUID REFERENCES users(id) ON DELETE SET NULL,
    verification_notes      TEXT,
    due_date                TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, finding_number)
);

CREATE INDEX idx_audit_findings_audit ON audit_findings(audit_id);
CREATE INDEX idx_audit_findings_status ON audit_findings(tenant_id, status);
CREATE INDEX idx_audit_findings_severity ON audit_findings(tenant_id, severity);

-- Suppliers: companies that provide materials, components, or services.
CREATE TABLE IF NOT EXISTS suppliers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    supplier_number     VARCHAR(50) NOT NULL,
    name                VARCHAR(255) NOT NULL,
    tier                VARCHAR(20),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'on_hold', 'disqualified')),
    email               VARCHAR(320),
    phone               VARCHAR(50),
    address             TEXT,
    website             VARCHAR(500),
    certifications      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, supplier_number)
);

CREATE INDEX idx_suppliers_tenant ON suppliers(tenant_id);
CREATE INDEX idx_suppliers_status ON suppliers(tenant_id, status);
CREATE INDEX idx_suppliers_tier ON suppliers(tenant_id, tier);

-- Supplier scorecards: periodic evaluation of supplier performance.
CREATE TABLE IF NOT EXISTS supplier_scorecards (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    supplier_id             UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    period_key              VARCHAR(20) NOT NULL,
    quality_score           DOUBLE PRECISION NOT NULL DEFAULT 0,
    delivery_score          DOUBLE PRECISION NOT NULL DEFAULT 0,
    cost_score              DOUBLE PRECISION NOT NULL DEFAULT 0,
    responsiveness_score    DOUBLE PRECISION NOT NULL DEFAULT 0,
    overall_score           DOUBLE PRECISION NOT NULL DEFAULT 0,
    tier                    VARCHAR(20) NOT NULL,
    ppm_rate                DOUBLE PRECISION,
    otd_percentage          DOUBLE PRECISION,
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, supplier_id, period_key)
);

CREATE INDEX idx_supplier_scorecards_supplier ON supplier_scorecards(supplier_id);
CREATE INDEX idx_supplier_scorecards_period ON supplier_scorecards(tenant_id, period_key);

-- SCARs (Supplier Corrective Action Requests): issued to suppliers for quality issues.
CREATE TABLE IF NOT EXISTS scars (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    scar_number             VARCHAR(50) NOT NULL,
    supplier_id             UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    title                   VARCHAR(500) NOT NULL,
    description             TEXT NOT NULL DEFAULT '',
    status                  VARCHAR(30) NOT NULL DEFAULT 'open'
                            CHECK (status IN ('open', 'sent_to_supplier', 'containment_in_progress',
                                   'root_cause_analysis', 'corrective_action_defined',
                                   'verification_in_progress', 'closed', 'rejected')),
    severity                VARCHAR(20) NOT NULL DEFAULT 'minor'
                            CHECK (severity IN ('observation', 'minor', 'major', 'critical')),
    containment_action      TEXT,
    root_cause              TEXT,
    corrective_action       TEXT,
    verification_notes      TEXT,
    owner_id                UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date                TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, scar_number)
);

CREATE INDEX idx_scars_tenant ON scars(tenant_id);
CREATE INDEX idx_scars_supplier ON scars(supplier_id);
CREATE INDEX idx_scars_status ON scars(tenant_id, status);

-- NPI risks: risks identified during New Product Introduction process.
CREATE TABLE IF NOT EXISTS npi_risks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    risk_number         VARCHAR(50) NOT NULL,
    title               VARCHAR(500) NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    category            VARCHAR(50) NOT NULL
                        CHECK (category IN ('design_complexity', 'process_capability', 'supplier_capability',
                               'technology_maturity', 'resource_availability', 'regulatory_compliance',
                               'schedule_risk', 'cost_risk', 'quality_risk', 'safety_risk',
                               'environmental_risk', 'market_risk', 'technical_risk', 'other')),
    phase               VARCHAR(30) NOT NULL
                        CHECK (phase IN ('intake', 'dfm', 'prototype', 'pilot', 'sop')),
    project_id          UUID,
    initial_severity    INT NOT NULL DEFAULT 1 CHECK (initial_severity BETWEEN 1 AND 10),
    initial_occurrence  INT NOT NULL DEFAULT 1 CHECK (initial_occurrence BETWEEN 1 AND 10),
    initial_detection   INT NOT NULL DEFAULT 1 CHECK (initial_detection BETWEEN 1 AND 10),
    current_severity    INT NOT NULL DEFAULT 1 CHECK (current_severity BETWEEN 1 AND 10),
    current_occurrence  INT NOT NULL DEFAULT 1 CHECK (current_occurrence BETWEEN 1 AND 10),
    current_detection   INT NOT NULL DEFAULT 1 CHECK (current_detection BETWEEN 1 AND 10),
    target_severity     INT NOT NULL DEFAULT 1 CHECK (target_severity BETWEEN 1 AND 10),
    target_occurrence   INT NOT NULL DEFAULT 1 CHECK (target_occurrence BETWEEN 1 AND 10),
    target_detection    INT NOT NULL DEFAULT 1 CHECK (target_detection BETWEEN 1 AND 10),
    is_closed           BOOLEAN NOT NULL DEFAULT FALSE,
    has_occurred        BOOLEAN NOT NULL DEFAULT FALSE,
    occurred_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, risk_number)
);

CREATE INDEX idx_npi_risks_tenant ON npi_risks(tenant_id);
CREATE INDEX idx_npi_risks_phase ON npi_risks(tenant_id, phase);
CREATE INDEX idx_npi_risks_category ON npi_risks(tenant_id, category);

-- MSA studies: Measurement Systems Analysis (Gauge R&R, linearity, bias, etc.).
CREATE TABLE IF NOT EXISTS msa_studies (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    study_type          VARCHAR(30) NOT NULL
                        CHECK (study_type IN ('grr', 'linearity', 'bias', 'stability', 'attribute_agreement')),
    title               VARCHAR(500) NOT NULL,
    gauge_id            UUID,
    operators_count     INT NOT NULL DEFAULT 0,
    parts_count         INT NOT NULL DEFAULT 0,
    trials_count        INT NOT NULL DEFAULT 0,
    status              VARCHAR(20) NOT NULL DEFAULT 'planned'
                        CHECK (status IN ('planned', 'in_progress', 'completed')),
    repeatability_ev    DOUBLE PRECISION,
    reproducibility_av  DOUBLE PRECISION,
    grr_percent         DOUBLE PRECISION,
    ndc                 INT,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, title)
);

CREATE INDEX idx_msa_studies_tenant ON msa_studies(tenant_id);
CREATE INDEX idx_msa_studies_type ON msa_studies(study_type);
CREATE INDEX idx_msa_studies_status ON msa_studies(status);

-- SPC data: Statistical Process Control measurements for capability analysis.
CREATE TABLE IF NOT EXISTS spc_data (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID,
    process_step        VARCHAR(255),
    characteristic      VARCHAR(255) NOT NULL,
    measured_value      DOUBLE PRECISION NOT NULL,
    usl                 DOUBLE PRECISION,
    lsl                 DOUBLE PRECISION,
    target              DOUBLE PRECISION,
    unit                VARCHAR(50),
    subgroup_id         VARCHAR(100),
    sample_size         INT,
    operator_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    gauge_id            UUID,
    measured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_spc_data_tenant ON spc_data(tenant_id);
CREATE INDEX idx_spc_data_product ON spc_data(tenant_id, product_id);
CREATE INDEX idx_spc_data_characteristic ON spc_data(tenant_id, characteristic);
CREATE INDEX idx_spc_data_measured ON spc_data(tenant_id, measured_at DESC);

-- Stage gates: NPI project stage-gate decisions and reviews.
CREATE TABLE IF NOT EXISTS stage_gates (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id          UUID NOT NULL,
    stage               VARCHAR(30) NOT NULL
                        CHECK (stage IN ('intake', 'dfm', 'prototype', 'pilot', 'sop', 'completed', 'cancelled')),
    decision            VARCHAR(20)
                        CHECK (decision IN ('go', 'no_go', 'conditional_go', 'hold')),
    decision_rationale  TEXT,
    reviewed_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    conducted_at        TIMESTAMPTZ,
    is_completed        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, project_id, stage)
);

CREATE INDEX idx_stage_gates_project ON stage_gates(project_id);
CREATE INDEX idx_stage_gates_stage ON stage_gates(tenant_id, stage);

-- ── Production / Manufacturing Domain ─────────────────────────────────────

-- Products: items manufactured or assembled by the organization.
CREATE TABLE IF NOT EXISTS products (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_number      VARCHAR(50) NOT NULL,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    category            VARCHAR(100),
    unit_of_measure     VARCHAR(20) NOT NULL DEFAULT 'pcs',
    standard_cost       DOUBLE PRECISION,
    list_price          DOUBLE PRECISION,
    quantity_on_hand    DOUBLE PRECISION NOT NULL DEFAULT 0,
    reorder_point       DOUBLE PRECISION,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    product_type        VARCHAR(30) NOT NULL DEFAULT 'finished_good'
                        CHECK (product_type IN ('raw_material', 'component', 'subassembly', 'finished_good', 'supply')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, product_number)
);

CREATE INDEX idx_products_tenant ON products(tenant_id);
CREATE INDEX idx_products_type ON products(tenant_id, product_type);
CREATE INDEX idx_products_active ON products(tenant_id, is_active) WHERE is_active = TRUE;

-- BOM items: component quantities required to produce a parent product.
CREATE TABLE IF NOT EXISTS bom_items (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    parent_product_id       UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    component_product_id    UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity                DOUBLE PRECISION NOT NULL DEFAULT 1,
    unit_of_measure         VARCHAR(20) NOT NULL DEFAULT 'pcs',
    scrap_percent           DOUBLE PRECISION DEFAULT 0,
    operation_sequence      INT,
    effective_date          TIMESTAMPTZ,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, parent_product_id, component_product_id, effective_date)
);

CREATE INDEX idx_bom_items_parent ON bom_items(parent_product_id);
CREATE INDEX idx_bom_items_component ON bom_items(component_product_id);
CREATE INDEX idx_bom_items_active ON bom_items(parent_product_id, is_active) WHERE is_active = TRUE;

-- Production orders: authorize manufacturing of specific product quantities.
CREATE TABLE IF NOT EXISTS production_orders (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    order_number        VARCHAR(50) NOT NULL,
    product_id          UUID NOT NULL REFERENCES products(id),
    quantity_planned    DOUBLE PRECISION NOT NULL DEFAULT 0,
    quantity_produced   DOUBLE PRECISION NOT NULL DEFAULT 0,
    quantity_scrapped   DOUBLE PRECISION NOT NULL DEFAULT 0,
    status              VARCHAR(20) NOT NULL DEFAULT 'created'
                        CHECK (status IN ('created', 'released', 'in_progress', 'completed', 'cancelled', 'on_hold')),
    work_center_id      UUID,
    scheduled_start     TIMESTAMPTZ,
    scheduled_end       TIMESTAMPTZ,
    actual_start        TIMESTAMPTZ,
    actual_completion   TIMESTAMPTZ,
    priority            VARCHAR(20) DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    work_order_id       UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, order_number)
);

CREATE INDEX idx_production_orders_tenant ON production_orders(tenant_id);
CREATE INDEX idx_production_orders_status ON production_orders(tenant_id, status);
CREATE INDEX idx_production_orders_product ON production_orders(product_id);
CREATE INDEX idx_production_orders_schedule ON production_orders(tenant_id, scheduled_start);

-- MRP records: Material Requirements Planning results.
CREATE TABLE IF NOT EXISTS mrp_records (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    run_id                  UUID,
    product_id              UUID NOT NULL REFERENCES products(id),
    gross_requirement       DOUBLE PRECISION NOT NULL DEFAULT 0,
    scheduled_receipts      DOUBLE PRECISION NOT NULL DEFAULT 0,
    projected_on_hand       DOUBLE PRECISION NOT NULL DEFAULT 0,
    net_requirement         DOUBLE PRECISION NOT NULL DEFAULT 0,
    planned_order_receipt   DOUBLE PRECISION NOT NULL DEFAULT 0,
    planned_order_release   DOUBLE PRECISION NOT NULL DEFAULT 0,
    planned_order_date      TIMESTAMPTZ,
    is_shortage             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mrp_records_tenant ON mrp_records(tenant_id);
CREATE INDEX idx_mrp_records_product ON mrp_records(product_id);
CREATE INDEX idx_mrp_records_run ON mrp_records(run_id);
CREATE INDEX idx_mrp_records_shortage ON mrp_records(tenant_id, is_shortage) WHERE is_shortage = TRUE;

-- Work centers: production resources (machines, cells, workstations).
CREATE TABLE IF NOT EXISTS work_centers (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    work_center_number  VARCHAR(50) NOT NULL,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    work_center_type    VARCHAR(30) NOT NULL DEFAULT 'manual'
                        CHECK (work_center_type IN ('manual', 'semi_automated', 'automated', 'assembly', 'test')),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    capacity_per_shift  DOUBLE PRECISION,
    shifts_per_day      INT DEFAULT 1,
    efficiency          DOUBLE PRECISION DEFAULT 1.0,
    department          VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, work_center_number)
);

CREATE INDEX idx_work_centers_tenant ON work_centers(tenant_id);
CREATE INDEX idx_work_centers_active ON work_centers(tenant_id, is_active) WHERE is_active = TRUE;

-- ── Maintenance Domain ────────────────────────────────────────────────────

-- Equipment: machines, tools, and assets used in production and maintenance.
CREATE TABLE IF NOT EXISTS equipment (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    equipment_number        VARCHAR(50) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    description             TEXT,
    equipment_type          VARCHAR(30) NOT NULL DEFAULT 'machine'
                            CHECK (equipment_type IN ('machine', 'tool', 'vehicle', 'facility', 'instrument')),
    manufacturer            VARCHAR(255),
    model                   VARCHAR(255),
    serial_number           VARCHAR(255),
    location                VARCHAR(255),
    department              VARCHAR(100),
    status                  VARCHAR(30) NOT NULL DEFAULT 'operational'
                            CHECK (status IN ('operational', 'under_maintenance', 'out_of_service', 'retired')),
    install_date            TIMESTAMPTZ,
    useful_life_months      INT,
    meter_unit              VARCHAR(20),
    current_meter_value     DOUBLE PRECISION,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, equipment_number)
);

CREATE INDEX idx_equipment_tenant ON equipment(tenant_id);
CREATE INDEX idx_equipment_status ON equipment(tenant_id, status);
CREATE INDEX idx_equipment_type ON equipment(tenant_id, equipment_type);

-- Maintenance work requests: submitted when equipment issues are identified.
CREATE TABLE IF NOT EXISTS maintenance_work_requests (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    request_number      VARCHAR(50) NOT NULL,
    equipment_id        UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    title               VARCHAR(500) NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    priority            VARCHAR(20) NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'emergency')),
    status              VARCHAR(30) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'assigned', 'in_progress', 'completed', 'cancelled')),
    work_type           VARCHAR(30) NOT NULL DEFAULT 'corrective'
                        CHECK (work_type IN ('corrective', 'preventive', 'predictive')),
    requested_by        UUID NOT NULL REFERENCES users(id),
    assigned_to         UUID REFERENCES users(id) ON DELETE SET NULL,
    work_order_id       UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    target_date         TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, request_number)
);

CREATE INDEX idx_maint_work_requests_tenant ON maintenance_work_requests(tenant_id);
CREATE INDEX idx_maint_work_requests_equipment ON maintenance_work_requests(equipment_id);
CREATE INDEX idx_maint_work_requests_status ON maintenance_work_requests(tenant_id, status);
CREATE INDEX idx_maint_work_requests_priority ON maintenance_work_requests(tenant_id, priority);

-- PM schedules: recurring preventive maintenance tasks for equipment.
CREATE TABLE IF NOT EXISTS pm_schedules (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    equipment_id                UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    schedule_number             VARCHAR(50) NOT NULL,
    title                       VARCHAR(500) NOT NULL,
    description                 TEXT,
    frequency_type              VARCHAR(20) NOT NULL DEFAULT 'calendar'
                                CHECK (frequency_type IN ('calendar', 'meter', 'usage')),
    frequency_value             INT NOT NULL DEFAULT 30,
    frequency_unit              VARCHAR(20) NOT NULL DEFAULT 'days'
                                CHECK (frequency_unit IN ('days', 'hours', 'cycles', 'km')),
    last_performed_at           TIMESTAMPTZ,
    next_due_at                 TIMESTAMPTZ,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    assigned_to                 UUID REFERENCES users(id) ON DELETE SET NULL,
    estimated_duration_minutes  INT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, schedule_number)
);

CREATE INDEX idx_pm_schedules_tenant ON pm_schedules(tenant_id);
CREATE INDEX idx_pm_schedules_equipment ON pm_schedules(equipment_id);
CREATE INDEX idx_pm_schedules_due ON pm_schedules(next_due_at) WHERE is_active = TRUE;

-- ── Finance Domain ────────────────────────────────────────────────────────

-- Invoices: accounts payable (supplier) or accounts receivable (customer).
CREATE TABLE IF NOT EXISTS invoices (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_number      VARCHAR(50) NOT NULL,
    invoice_type        VARCHAR(20) NOT NULL
                        CHECK (invoice_type IN ('payable', 'receivable')),
    status              VARCHAR(30) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'sent', 'approved', 'paid', 'overdue', 'cancelled')),
    counterparty_id     UUID NOT NULL,
    counterparty_name   VARCHAR(255) NOT NULL,
    invoice_date        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_date            TIMESTAMPTZ NOT NULL,
    subtotal            DOUBLE PRECISION NOT NULL DEFAULT 0,
    tax_amount          DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_amount        DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    order_id            UUID,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, invoice_number)
);

CREATE INDEX idx_invoices_tenant ON invoices(tenant_id);
CREATE INDEX idx_invoices_type ON invoices(tenant_id, invoice_type);
CREATE INDEX idx_invoices_status ON invoices(tenant_id, status);
CREATE INDEX idx_invoices_due ON invoices(tenant_id, due_date) WHERE status NOT IN ('paid', 'cancelled');

-- Payments: money received from customers or sent to suppliers.
CREATE TABLE IF NOT EXISTS payments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    payment_number      VARCHAR(50) NOT NULL,
    payment_type        VARCHAR(20) NOT NULL
                        CHECK (payment_type IN ('received', 'issued')),
    payment_method      VARCHAR(30) NOT NULL DEFAULT 'bank_transfer'
                        CHECK (payment_method IN ('bank_transfer', 'check', 'cash', 'credit_card', 'wire')),
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    amount              DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    counterparty_id     UUID NOT NULL,
    invoice_id          UUID REFERENCES invoices(id) ON DELETE SET NULL,
    payment_date        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reference           VARCHAR(255),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, payment_number)
);

CREATE INDEX idx_payments_tenant ON payments(tenant_id);
CREATE INDEX idx_payments_type ON payments(tenant_id, payment_type);
CREATE INDEX idx_payments_status ON payments(tenant_id, status);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);

-- Budgets: financial plans for departments, projects, or cost centers.
CREATE TABLE IF NOT EXISTS budgets (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    budget_code         VARCHAR(50) NOT NULL,
    name                VARCHAR(255) NOT NULL,
    budget_type         VARCHAR(30) NOT NULL
                        CHECK (budget_type IN ('departmental', 'project', 'capital', 'operational')),
    fiscal_period       VARCHAR(20) NOT NULL,
    department          VARCHAR(100),
    budgeted_amount     DOUBLE PRECISION NOT NULL DEFAULT 0,
    spent_amount        DOUBLE PRECISION NOT NULL DEFAULT 0,
    committed_amount    DOUBLE PRECISION NOT NULL DEFAULT 0,
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'active', 'closed', 'cancelled')),
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, budget_code)
);

CREATE INDEX idx_budgets_tenant ON budgets(tenant_id);
CREATE INDEX idx_budgets_period ON budgets(tenant_id, fiscal_period);
CREATE INDEX idx_budgets_type ON budgets(tenant_id, budget_type);

-- Journal entries: accounting transactions in the general ledger.
CREATE TABLE IF NOT EXISTS journal_entries (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entry_number        VARCHAR(50) NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    entry_type          VARCHAR(20) NOT NULL DEFAULT 'standard'
                        CHECK (entry_type IN ('standard', 'adjusting', 'closing', 'reversing')),
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'posted', 'reversed')),
    debit_total         DOUBLE PRECISION NOT NULL DEFAULT 0,
    credit_total        DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    period              VARCHAR(20) NOT NULL,
    entry_date          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    posted_by           UUID REFERENCES users(id) ON DELETE SET NULL,
    posted_at           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, entry_number)
);

CREATE INDEX idx_journal_entries_tenant ON journal_entries(tenant_id);
CREATE INDEX idx_journal_entries_period ON journal_entries(tenant_id, period);
CREATE INDEX idx_journal_entries_status ON journal_entries(tenant_id, status);

-- Cost rollups: calculated total product costs from BOM structure.
CREATE TABLE IF NOT EXISTS cost_rollups (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id),
    version             VARCHAR(50) NOT NULL,
    total_cost          DOUBLE PRECISION NOT NULL DEFAULT 0,
    material_cost       DOUBLE PRECISION NOT NULL DEFAULT 0,
    labor_cost          DOUBLE PRECISION NOT NULL DEFAULT 0,
    overhead_cost       DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'finalized')),
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    computed_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, product_id, version)
);

CREATE INDEX idx_cost_rollups_product ON cost_rollups(product_id);
CREATE INDEX idx_cost_rollups_status ON cost_rollups(tenant_id, status);

-- ── Human Resources Domain ────────────────────────────────────────────────

-- Employees: the organization's workforce.
CREATE TABLE IF NOT EXISTS employees (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_number     VARCHAR(50) NOT NULL,
    first_name          VARCHAR(255) NOT NULL,
    last_name           VARCHAR(255) NOT NULL,
    email               VARCHAR(320) NOT NULL,
    phone               VARCHAR(50),
    job_title           VARCHAR(255),
    department          VARCHAR(100),
    employment_type     VARCHAR(20) NOT NULL DEFAULT 'full_time'
                        CHECK (employment_type IN ('full_time', 'part_time', 'contractor', 'intern', 'temporary')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'on_leave', 'terminated', 'suspended')),
    hire_date           TIMESTAMPTZ NOT NULL,
    termination_date    TIMESTAMPTZ,
    manager_id          UUID REFERENCES employees(id) ON DELETE SET NULL,
    user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
    location            VARCHAR(255),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, employee_number),
    UNIQUE(tenant_id, email)
);

CREATE INDEX idx_employees_tenant ON employees(tenant_id);
CREATE INDEX idx_employees_department ON employees(tenant_id, department);
CREATE INDEX idx_employees_status ON employees(tenant_id, status);
CREATE INDEX idx_employees_manager ON employees(manager_id);

-- Training records: employee participation in training courses.
CREATE TABLE IF NOT EXISTS training_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id         UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    training_name       VARCHAR(500) NOT NULL,
    training_type       VARCHAR(30) NOT NULL DEFAULT 'internal'
                        CHECK (training_type IN ('internal', 'external', 'online', 'on_the_job', 'certification')),
    description         TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'enrolled'
                        CHECK (status IN ('enrolled', 'in_progress', 'completed', 'failed', 'expired')),
    score               DOUBLE PRECISION,
    passed              BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at        TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ,
    trainer_id          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_training_records_employee ON training_records(employee_id);
CREATE INDEX idx_training_records_status ON training_records(tenant_id, status);
CREATE INDEX idx_training_records_expires ON training_records(expires_at) WHERE expires_at IS NOT NULL;

-- Certifications: formal qualifications held by employees.
CREATE TABLE IF NOT EXISTS certifications (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id             UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    certification_name      VARCHAR(500) NOT NULL,
    issuing_body            VARCHAR(255),
    certification_number    VARCHAR(255),
    status                  VARCHAR(20) NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'expired', 'revoked', 'pending')),
    issued_at               TIMESTAMPTZ NOT NULL,
    expires_at              TIMESTAMPTZ,
    renewed_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_certifications_employee ON certifications(employee_id);
CREATE INDEX idx_certifications_status ON certifications(tenant_id, status);
CREATE INDEX idx_certifications_expires ON certifications(expires_at) WHERE status = 'active';

-- Attendance: employee presence, absences, and check-in/check-out records.
CREATE TABLE IF NOT EXISTS attendance (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id         UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    attendance_date     DATE NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'present'
                        CHECK (status IN ('present', 'absent', 'late', 'half_day', 'holiday', 'excused')),
    check_in            TIMESTAMPTZ,
    check_out           TIMESTAMPTZ,
    hours_worked        DOUBLE PRECISION,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, employee_id, attendance_date)
);

CREATE INDEX idx_attendance_employee ON attendance(employee_id);
CREATE INDEX idx_attendance_date ON attendance(tenant_id, attendance_date);
CREATE INDEX idx_attendance_status ON attendance(tenant_id, status);

-- Performance reviews: periodic employee evaluations.
CREATE TABLE IF NOT EXISTS performance_reviews (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id         UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    reviewer_id         UUID NOT NULL REFERENCES users(id),
    review_period       VARCHAR(20) NOT NULL,
    review_type         VARCHAR(20) NOT NULL DEFAULT 'annual'
                        CHECK (review_type IN ('annual', 'quarterly', 'probation', 'project', '360')),
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'in_progress', 'completed', 'acknowledged')),
    rating              VARCHAR(20),
    overall_score       DOUBLE PRECISION,
    strengths           TEXT,
    improvements        TEXT,
    goals               TEXT,
    employee_comments   TEXT,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, employee_id, review_period)
);

CREATE INDEX idx_performance_reviews_employee ON performance_reviews(employee_id);
CREATE INDEX idx_performance_reviews_reviewer ON performance_reviews(reviewer_id);
CREATE INDEX idx_performance_reviews_status ON performance_reviews(tenant_id, status);

-- Timecards: employee clock-in/clock-out events for payroll.
CREATE TABLE IF NOT EXISTS timecards (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id         UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    event_type          VARCHAR(20) NOT NULL
                        CHECK (event_type IN ('clock_in', 'clock_out', 'break_start', 'break_end')),
    event_time          TIMESTAMPTZ NOT NULL,
    work_order_id       UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_timecards_employee ON timecards(employee_id);
CREATE INDEX idx_timecards_date ON timecards(tenant_id, event_time);
CREATE INDEX idx_timecards_event_type ON timecards(tenant_id, event_type);

-- Leave requests: employee time-off requests and approvals.
CREATE TABLE IF NOT EXISTS leave_requests (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id         UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type          VARCHAR(30) NOT NULL
                        CHECK (leave_type IN ('vacation', 'sick', 'personal', 'maternity', 'paternity', 'bereavement', 'unpaid')),
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled', 'in_progress')),
    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    total_days          DOUBLE PRECISION NOT NULL,
    reason              TEXT,
    approved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    manager_notes       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_leave_requests_employee ON leave_requests(employee_id);
CREATE INDEX idx_leave_requests_status ON leave_requests(tenant_id, status);
CREATE INDEX idx_leave_requests_dates ON leave_requests(tenant_id, start_date, end_date);

-- ── Supply Chain Domain ───────────────────────────────────────────────────

-- Purchase orders: issued to suppliers for materials, components, or services.
CREATE TABLE IF NOT EXISTS purchase_orders (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    po_number           VARCHAR(50) NOT NULL,
    supplier_id         UUID NOT NULL REFERENCES suppliers(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'sent', 'confirmed', 'received', 'cancelled', 'closed')),
    order_date          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expected_date       TIMESTAMPTZ,
    total_amount        DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_terms       VARCHAR(100),
    shipping_terms      VARCHAR(100),
    shipping_address    TEXT,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, po_number)
);

CREATE INDEX idx_purchase_orders_tenant ON purchase_orders(tenant_id);
CREATE INDEX idx_purchase_orders_supplier ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(tenant_id, status);

-- Purchase order items: line items within a purchase order.
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    purchase_order_id   UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    line_number         INT NOT NULL,
    product_id          UUID NOT NULL REFERENCES products(id),
    quantity            DOUBLE PRECISION NOT NULL DEFAULT 1,
    quantity_received   DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_price          DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_amount        DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit_of_measure     VARCHAR(20) NOT NULL DEFAULT 'pcs',
    expected_date       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(purchase_order_id, line_number)
);

CREATE INDEX idx_po_items_order ON purchase_order_items(purchase_order_id);
CREATE INDEX idx_po_items_product ON purchase_order_items(product_id);

-- Inventory items: product quantities in warehouse locations.
CREATE TABLE IF NOT EXISTS inventory_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id),
    location            VARCHAR(255) NOT NULL DEFAULT 'main',
    bin_location        VARCHAR(100),
    quantity_on_hand    DOUBLE PRECISION NOT NULL DEFAULT 0,
    quantity_reserved   DOUBLE PRECISION NOT NULL DEFAULT 0,
    quantity_available  DOUBLE PRECISION NOT NULL DEFAULT 0,
    lot_number          VARCHAR(100),
    serial_number       VARCHAR(100),
    expiry_date         TIMESTAMPTZ,
    unit_of_measure     VARCHAR(20) NOT NULL DEFAULT 'pcs',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, product_id, location, lot_number)
);

CREATE INDEX idx_inventory_items_product ON inventory_items(product_id);
CREATE INDEX idx_inventory_items_location ON inventory_items(tenant_id, location);
CREATE INDEX idx_inventory_items_lot ON inventory_items(tenant_id, lot_number);

-- Stock moves: transfer of inventory between locations.
CREATE TABLE IF NOT EXISTS stock_moves (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES products(id),
    from_location       VARCHAR(255),
    to_location         VARCHAR(255) NOT NULL,
    quantity            DOUBLE PRECISION NOT NULL,
    move_type           VARCHAR(20) NOT NULL
                        CHECK (move_type IN ('receipt', 'issue', 'transfer', 'adjustment')),
    reference_type      VARCHAR(50),
    reference_id        UUID,
    lot_number          VARCHAR(100),
    unit_of_measure     VARCHAR(20) NOT NULL DEFAULT 'pcs',
    moved_by            UUID REFERENCES users(id) ON DELETE SET NULL,
    moved_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stock_moves_product ON stock_moves(product_id);
CREATE INDEX idx_stock_moves_type ON stock_moves(tenant_id, move_type);
CREATE INDEX idx_stock_moves_date ON stock_moves(tenant_id, moved_at DESC);

-- Goods receipts: documentation of material receipt against purchase orders.
CREATE TABLE IF NOT EXISTS goods_receipts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    receipt_number      VARCHAR(50) NOT NULL,
    purchase_order_id   UUID NOT NULL REFERENCES purchase_orders(id),
    supplier_id         UUID NOT NULL REFERENCES suppliers(id),
    status              VARCHAR(30) NOT NULL DEFAULT 'expected'
                        CHECK (status IN ('expected', 'partially_received', 'fully_received', 'cancelled')),
    receipt_date        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivery_note       VARCHAR(255),
    is_quality_approved BOOLEAN,
    received_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, receipt_number)
);

CREATE INDEX idx_goods_receipts_po ON goods_receipts(purchase_order_id);
CREATE INDEX idx_goods_receipts_supplier ON goods_receipts(supplier_id);
CREATE INDEX idx_goods_receipts_status ON goods_receipts(tenant_id, status);

-- RFQs (Requests for Quote): sent to suppliers for pricing.
CREATE TABLE IF NOT EXISTS rfqs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rfq_number          VARCHAR(50) NOT NULL,
    supplier_id         UUID NOT NULL REFERENCES suppliers(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'sent', 'quoted', 'expired', 'cancelled', 'awarded')),
    issue_date          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deadline            TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, rfq_number)
);

CREATE INDEX idx_rfqs_tenant ON rfqs(tenant_id);
CREATE INDEX idx_rfqs_supplier ON rfqs(supplier_id);
CREATE INDEX idx_rfqs_status ON rfqs(tenant_id, status);

-- Quotes: supplier responses to RFQs with pricing and terms.
CREATE TABLE IF NOT EXISTS quotes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    quote_number        VARCHAR(50) NOT NULL,
    rfq_id              UUID REFERENCES rfqs(id) ON DELETE SET NULL,
    supplier_id         UUID NOT NULL REFERENCES suppliers(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'submitted', 'under_review', 'approved', 'rejected', 'expired')),
    quote_date          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until         TIMESTAMPTZ,
    total_amount        DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_terms       VARCHAR(100),
    lead_time_days      INT,
    reviewed_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, quote_number)
);

CREATE INDEX idx_quotes_tenant ON quotes(tenant_id);
CREATE INDEX idx_quotes_supplier ON quotes(supplier_id);
CREATE INDEX idx_quotes_status ON quotes(tenant_id, status);
CREATE INDEX idx_quotes_rfq ON quotes(rfq_id);

-- Sales orders: customer orders for products or services.
CREATE TABLE IF NOT EXISTS sales_orders (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    so_number           VARCHAR(50) NOT NULL,
    customer_id         UUID NOT NULL,
    status              VARCHAR(30) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'confirmed', 'in_production', 'shipped', 'delivered', 'invoiced', 'cancelled')),
    order_date          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    requested_date      TIMESTAMPTZ,
    delivered_date      TIMESTAMPTZ,
    total_amount        DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_terms       VARCHAR(100),
    shipping_address    TEXT,
    sales_rep_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, so_number)
);

CREATE INDEX idx_sales_orders_tenant ON sales_orders(tenant_id);
CREATE INDEX idx_sales_orders_status ON sales_orders(tenant_id, status);
CREATE INDEX idx_sales_orders_customer ON sales_orders(customer_id);

-- ── Operations / Continuous Improvement Domain ────────────────────────────

-- Projects: structured initiatives with defined scope, timeline, and resources.
CREATE TABLE IF NOT EXISTS projects (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_number      VARCHAR(50) NOT NULL,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    project_type        VARCHAR(30) NOT NULL DEFAULT 'other'
                        CHECK (project_type IN ('npi', 'continuous_improvement', 'kaizen', 'capital', 'other')),
    status              VARCHAR(20) NOT NULL DEFAULT 'idea'
                        CHECK (status IN ('idea', 'planned', 'in_progress', 'completed', 'on_hold', 'cancelled')),
    priority            VARCHAR(20) DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    start_date          TIMESTAMPTZ,
    target_date         TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    project_manager_id  UUID REFERENCES users(id) ON DELETE SET NULL,
    budget_amount       DOUBLE PRECISION,
    currency            VARCHAR(3),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, project_number)
);

CREATE INDEX idx_projects_tenant ON projects(tenant_id);
CREATE INDEX idx_projects_status ON projects(tenant_id, status);
CREATE INDEX idx_projects_type ON projects(tenant_id, project_type);

-- Kanban cards: work items on visual management boards.
CREATE TABLE IF NOT EXISTS kanban_cards (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    board_id            UUID NOT NULL,
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    column_name         VARCHAR(100) NOT NULL DEFAULT 'backlog',
    position            INT NOT NULL DEFAULT 0,
    card_type           VARCHAR(30) NOT NULL DEFAULT 'task'
                        CHECK (card_type IN ('task', 'issue', 'improvement', 'standard_work')),
    priority            VARCHAR(20) DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    size                INT,
    assignee_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date            TIMESTAMPTZ,
    is_blocked          BOOLEAN NOT NULL DEFAULT FALSE,
    block_reason        TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kanban_cards_board ON kanban_cards(board_id);
CREATE INDEX idx_kanban_cards_column ON kanban_cards(board_id, column_name);
CREATE INDEX idx_kanban_cards_assignee ON kanban_cards(assignee_id);

-- Issues: problems, bugs, tasks, and action items across the organization.
CREATE TABLE IF NOT EXISTS issues (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    issue_number        VARCHAR(50) NOT NULL,
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    issue_type          VARCHAR(30) NOT NULL DEFAULT 'task'
                        CHECK (issue_type IN ('bug', 'task', 'improvement', 'question', 'risk', 'action_item')),
    severity            VARCHAR(20) NOT NULL DEFAULT 'minor'
                        CHECK (severity IN ('minor', 'major', 'critical', 'blocker')),
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'assigned', 'in_progress', 'resolved', 'closed', 'rejected')),
    priority            VARCHAR(20) DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    reporter_id         UUID NOT NULL REFERENCES users(id),
    assignee_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    project_id          UUID REFERENCES projects(id) ON DELETE SET NULL,
    source_type         VARCHAR(50),
    source_id           UUID,
    due_date            TIMESTAMPTZ,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, issue_number)
);

CREATE INDEX idx_issues_tenant ON issues(tenant_id);
CREATE INDEX idx_issues_status ON issues(tenant_id, status);
CREATE INDEX idx_issues_assignee ON issues(assignee_id);
CREATE INDEX idx_issues_project ON issues(project_id);

-- A3 reports: structured problem-solving reports following PDCA.
CREATE TABLE IF NOT EXISTS a3_reports (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    a3_number           VARCHAR(50) NOT NULL,
    title               VARCHAR(500) NOT NULL,
    a3_type             VARCHAR(30) NOT NULL DEFAULT 'problem_solving'
                        CHECK (a3_type IN ('problem_solving', 'proposal', 'status', 'kaizen')),
    status              VARCHAR(30) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'in_progress', 'under_review', 'approved', 'implemented', 'closed')),
    priority            VARCHAR(20) DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    background          TEXT,
    current_condition   TEXT,
    root_cause          TEXT,
    target_condition    TEXT,
    action_plan         JSONB,
    follow_up           TEXT,
    outcome             VARCHAR(30)
                        CHECK (outcome IN ('effective', 'ineffective', 'inconclusive')),
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    source_id           UUID,
    source_type         VARCHAR(50),
    due_date            TIMESTAMPTZ,
    closed_at           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, a3_number)
);

CREATE INDEX idx_a3_reports_tenant ON a3_reports(tenant_id);
CREATE INDEX idx_a3_reports_status ON a3_reports(tenant_id, status);
CREATE INDEX idx_a3_reports_owner ON a3_reports(owner_id);

-- Risk register: identified risks with assessments, mitigation, and status.
CREATE TABLE IF NOT EXISTS risks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    risk_number         VARCHAR(50) NOT NULL,
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    category            VARCHAR(30) NOT NULL
                        CHECK (category IN ('quality', 'safety', 'schedule', 'cost', 'compliance', 'operational', 'strategic')),
    severity            INT NOT NULL DEFAULT 1 CHECK (severity BETWEEN 1 AND 5),
    likelihood          INT NOT NULL DEFAULT 1 CHECK (likelihood BETWEEN 1 AND 5),
    risk_score          INT NOT NULL DEFAULT 1,
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'mitigating', 'closed', 'accepted')),
    entity_type         VARCHAR(50),
    entity_id           UUID,
    owner_id            UUID REFERENCES users(id) ON DELETE SET NULL,
    mitigation_plan     TEXT,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, risk_number)
);

CREATE INDEX idx_risks_tenant ON risks(tenant_id);
CREATE INDEX idx_risks_status ON risks(tenant_id, status);
CREATE INDEX idx_risks_category ON risks(tenant_id, category);
CREATE INDEX idx_risks_score ON risks(tenant_id, risk_score DESC);

-- Andon events: visual signals for issues on the production line.
CREATE TABLE IF NOT EXISTS andon_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_number        VARCHAR(50) NOT NULL,
    andon_type          VARCHAR(30) NOT NULL
                        CHECK (andon_type IN ('safety', 'quality', 'production', 'maintenance', 'material')),
    severity            VARCHAR(20) NOT NULL DEFAULT 'medium'
                        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'acknowledged', 'resolved', 'cancelled')),
    description         TEXT NOT NULL DEFAULT '',
    station_id          UUID,
    work_order_id       UUID REFERENCES work_orders(id) ON DELETE SET NULL,
    triggered_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at     TIMESTAMPTZ,
    resolved_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    resolution          TEXT,
    downtime_minutes    DOUBLE PRECISION,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, event_number)
);

CREATE INDEX idx_andon_events_tenant ON andon_events(tenant_id);
CREATE INDEX idx_andon_events_type ON andon_events(tenant_id, andon_type);
CREATE INDEX idx_andon_events_status ON andon_events(tenant_id, status);

-- ── AI / ML Domain ────────────────────────────────────────────────────────

-- Anomaly detections: potential anomalies identified by AI/ML models.
CREATE TABLE IF NOT EXISTS anomaly_detections (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type         VARCHAR(50) NOT NULL,
    entity_id           UUID NOT NULL,
    anomaly_type        VARCHAR(100) NOT NULL,
    confidence          DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    description         TEXT NOT NULL DEFAULT '',
    status              VARCHAR(20) NOT NULL DEFAULT 'new'
                        CHECK (status IN ('new', 'reviewed', 'escalated', 'dismissed')),
    features            JSONB,
    reviewed_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at         TIMESTAMPTZ,
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_anomaly_detections_tenant ON anomaly_detections(tenant_id);
CREATE INDEX idx_anomaly_detections_entity ON anomaly_detections(entity_type, entity_id);
CREATE INDEX idx_anomaly_detections_status ON anomaly_detections(tenant_id, status);

-- Model registry: tracks ML model versions, performance, and deployment status.
CREATE TABLE IF NOT EXISTS model_registry (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    model_name          VARCHAR(255) NOT NULL,
    version             VARCHAR(50) NOT NULL,
    model_type          VARCHAR(50) NOT NULL
                        CHECK (model_type IN ('anomaly_detection', 'prediction', 'classification', 'recommendation')),
    status              VARCHAR(30) NOT NULL DEFAULT 'development'
                        CHECK (status IN ('development', 'testing', 'deployed', 'archived', 'deprecated')),
    accuracy            DOUBLE PRECISION CHECK (accuracy BETWEEN 0 AND 1),
    precision           DOUBLE PRECISION CHECK (precision BETWEEN 0 AND 1),
    recall              DOUBLE PRECISION CHECK (recall BETWEEN 0 AND 1),
    f1_score            DOUBLE PRECISION CHECK (f1_score BETWEEN 0 AND 1),
    dataset_size        BIGINT,
    artifact_path       TEXT,
    config              JSONB,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    deployed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, model_name, version)
);

CREATE INDEX idx_model_registry_tenant ON model_registry(tenant_id);
CREATE INDEX idx_model_registry_status ON model_registry(tenant_id, status);
CREATE INDEX idx_model_registry_name ON model_registry(tenant_id, model_name);

-- Predictions: output of ML model inferences with input context and confidence.
CREATE TABLE IF NOT EXISTS predictions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    model_id            UUID NOT NULL REFERENCES model_registry(id),
    prediction_type     VARCHAR(50) NOT NULL
                        CHECK (prediction_type IN ('quality', 'maintenance', 'demand', 'risk')),
    entity_type         VARCHAR(50) NOT NULL,
    entity_id           UUID NOT NULL,
    predicted_value     VARCHAR(255) NOT NULL,
    actual_value        VARCHAR(255),
    confidence          DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    input_features      JSONB,
    is_accurate         BOOLEAN,
    predicted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_predictions_tenant ON predictions(tenant_id);
CREATE INDEX idx_predictions_model ON predictions(model_id);
CREATE INDEX idx_predictions_type ON predictions(tenant_id, prediction_type);
CREATE INDEX idx_predictions_entity ON predictions(entity_type, entity_id);

-- ── Common / Cross-Cutting Domain ─────────────────────────────────────────

-- Notifications: messages sent to users about events or actions.
CREATE TABLE IF NOT EXISTS notifications (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type   VARCHAR(30) NOT NULL
                        CHECK (notification_type IN ('alert', 'reminder', 'approval_request', 'mention', 'system')),
    title               VARCHAR(500) NOT NULL,
    body                TEXT NOT NULL DEFAULT '',
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    read_at             TIMESTAMPTZ,
    action_url          VARCHAR(1000),
    entity_type         VARCHAR(50),
    entity_id           UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_tenant ON notifications(tenant_id, created_at DESC);
CREATE INDEX idx_notifications_unread ON notifications(user_id, created_at DESC) WHERE is_read = FALSE;

-- Attachments: file metadata linked to various domain entities.
CREATE TABLE IF NOT EXISTS attachments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    file_name           VARCHAR(500) NOT NULL,
    file_size           BIGINT NOT NULL DEFAULT 0,
    content_type        VARCHAR(255) NOT NULL DEFAULT 'application/octet-stream',
    storage_path        TEXT NOT NULL,
    entity_type         VARCHAR(50) NOT NULL,
    entity_id           UUID NOT NULL,
    uploaded_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attachments_entity ON attachments(entity_type, entity_id);
CREATE INDEX idx_attachments_tenant ON attachments(tenant_id);
CREATE INDEX idx_attachments_uploader ON attachments(uploaded_by);
