-- Human resources tables for Sensei ERP
--
-- This migration adds HR-related tables extending the base employees,
-- training_records, certifications, performance_reviews, timecards, and
-- leave_requests from 002_domain_tables. New tables cover compensation,
-- training programs, and enrollment tracking.

-- ── Employee Compensation ─────────────────────────────────────────────────
-- Salary and compensation history for employees.
CREATE TABLE IF NOT EXISTS employee_compensation (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id         UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    base_salary         DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    pay_frequency       VARCHAR(20) NOT NULL DEFAULT 'monthly'
                        CHECK (pay_frequency IN ('hourly', 'weekly', 'bi_weekly', 'monthly', 'annual')),
    effective_date      TIMESTAMPTZ NOT NULL,
    end_date            TIMESTAMPTZ,
    review_date         TIMESTAMPTZ,
    bonus_eligible      BOOLEAN NOT NULL DEFAULT FALSE,
    bonus_target        DOUBLE PRECISION,
    benefits_value      DOUBLE PRECISION NOT NULL DEFAULT 0,
    notes               TEXT,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_employee_comp_tenant ON employee_compensation(tenant_id);
CREATE INDEX idx_employee_comp_employee ON employee_compensation(employee_id);
CREATE INDEX idx_employee_comp_effective ON employee_compensation(employee_id, effective_date DESC);

-- ── Training Programs ─────────────────────────────────────────────────────
-- Available training courses and programs.
CREATE TABLE IF NOT EXISTS training_programs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    program_code        VARCHAR(50) NOT NULL,
    name                VARCHAR(500) NOT NULL,
    description         TEXT,
    duration_hours      DOUBLE PRECISION NOT NULL DEFAULT 0,
    category            VARCHAR(100),
    delivery_method     VARCHAR(30) NOT NULL DEFAULT 'classroom'
                        CHECK (delivery_method IN ('classroom', 'online', 'on_the_job', 'blended', 'self_paced')),
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('draft', 'active', 'inactive', 'archived')),
    certification_required BOOLEAN NOT NULL DEFAULT FALSE,
    certification_validity INT,
    recertification_required BOOLEAN NOT NULL DEFAULT FALSE,
    max_participants    INT,
    trainer_id          UUID REFERENCES users(id) ON DELETE SET NULL,
    materials           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, program_code)
);

CREATE INDEX idx_training_programs_tenant ON training_programs(tenant_id);
CREATE INDEX idx_training_programs_category ON training_programs(tenant_id, category);
CREATE INDEX idx_training_programs_status ON training_programs(tenant_id, status);

-- ── Training Enrollments ──────────────────────────────────────────────────
-- Employee enrollment in training programs.
CREATE TABLE IF NOT EXISTS training_enrollments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    program_id          UUID NOT NULL REFERENCES training_programs(id) ON DELETE CASCADE,
    employee_id         UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    status              VARCHAR(20) NOT NULL DEFAULT 'enrolled'
                        CHECK (status IN ('enrolled', 'in_progress', 'completed', 'failed', 'cancelled', 'expired')),
    enrolled_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    score               DOUBLE PRECISION,
    passed              BOOLEAN NOT NULL DEFAULT FALSE,
    certificate_number  VARCHAR(100),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(program_id, employee_id)
);

CREATE INDEX idx_training_enrollments_tenant ON training_enrollments(tenant_id);
CREATE INDEX idx_training_enrollments_program ON training_enrollments(program_id);
CREATE INDEX idx_training_enrollments_employee ON training_enrollments(employee_id);
CREATE INDEX idx_training_enrollments_status ON training_enrollments(tenant_id, status);
