-- Thirtieth-audit P0 items 6-8 (quality storage consolidation): the
-- runtime DatabaseQualityService must operate against the REAL relational
-- quality tables — never fabricated JSONB-style `quality_*` tables (none
-- of those exist anywhere in the chain; migration 170 stamped the actual
-- tables with `scope_site_id` / `scope_work_center_id`).
--
-- Canonical-table decision (the ambiguity resolution item 6 demands):
--
--   * NCR → `ncr_reports` (001). It is the table the rest of the runtime
--     reads: routes/today.rs dashboard queries, the attachment
--     parent-proof in sensei-api (proof_ncr verifies `ncr_reports` rows
--     against the caller's full scope), and migration 170's scope
--     columns. Its status CHECK already equals the NcrStatus lifecycle
--     (open / under_investigation / action_defined / in_progress /
--     closed), so the service's workflow maps onto it verbatim. This
--     migration adds the columns the service model (NonConformance)
--     carries beyond the 001 shape (nc_type, product/process, defect,
--     department, location, recurrence, source, RCA, disposition,
--     closed_at), widens the severity CHECK with the model's own scale
--     (low/medium/high/critical) and the status CHECK with 'cancelled',
--     and relaxes reported_by (the model's detected_by is optional).
--     `non_conformances` (006) REMAINS as a DIFFERENT domain concept: a
--     lean non-conformance LEDGER for inspection-detected material
--     events (work_order_id, disposition use_as_is/rework/..., closed_by)
--     with no CAPA-workflow lifecycle and no title/RCA/workflow fields;
--     it is not managed by QualityService. The two tables are two
--     different records, not two generations of one record.
--
--   * CAPA → `capas` (001). This migration adds the service model's
--     scalar state (description, capa_type, priority, nc_ids,
--     closed_at), widens the status CHECK to the full CapaStatusEx
--     lifecycle (legacy values stay valid for older rows/writers), and
--     relaxes owner_id (the model's owner is optional). The CAPA
--     workflow sub-state (root-cause analyses, corrective actions,
--     closure gates, effectiveness checks, entity links) is a nested
--     document with no relational home in the chain (only
--     capa_actions exists and covers a subset); it is persisted in a
--     `details` JSONB column on the canonical row — the same
--     JSONB-on-relational-table pattern the chain already uses
--     (self_inspections.characteristics, control_plans.characteristics,
--     eight_d_reports.d1_team/d8_closure). The SECURITY scope columns
--     stay real relational columns, enforced by SQL predicates.
--
--   * Audit → `audits` + `audit_findings` (002). The audits table's
--     CHECKs are exactly the model's AuditType (all nine variants,
--     certification/layered/system included) and AuditStatus
--     vocabularies, and audit_findings matches AuditFinding field for
--     field — the extended `quality_audits` (006) table is a legacy
--     summary with a narrower audit_type CHECK and is NOT the service
--     family table (retained for its direct SQL consumers; the
--     db-contract chain asserts its scope columns exist). `auditor_id`
--     and the checklist sub-state get real/JSONB storage here so the
--     whole-entity echo round-trips exactly.
--
-- Everything below is additive or constraint-widening: existing legacy
-- writers and readers of these tables keep working. All statements are
-- guarded so re-running the file by hand is safe.

-- ── ncr_reports: reconcile to the NonConformance service model ────────────
ALTER TABLE ncr_reports
    DROP CONSTRAINT IF EXISTS ncr_reports_severity_check;
ALTER TABLE ncr_reports
    ADD CONSTRAINT ncr_reports_severity_check
    CHECK (severity IN ('minor', 'major', 'critical', 'low', 'medium', 'high'));

ALTER TABLE ncr_reports
    DROP CONSTRAINT IF EXISTS ncr_reports_status_check;
ALTER TABLE ncr_reports
    ADD CONSTRAINT ncr_reports_status_check
    CHECK (status IN ('open', 'under_investigation', 'action_defined',
                      'in_progress', 'closed', 'rejected', 'cancelled'));

ALTER TABLE ncr_reports
    ALTER COLUMN reported_by DROP NOT NULL;

ALTER TABLE ncr_reports
    ADD COLUMN IF NOT EXISTS nc_type VARCHAR(40) NOT NULL DEFAULT 'other',
    ADD COLUMN IF NOT EXISTS product_id UUID,
    ADD COLUMN IF NOT EXISTS process_id UUID,
    ADD COLUMN IF NOT EXISTS defect_code TEXT,
    ADD COLUMN IF NOT EXISTS department TEXT,
    ADD COLUMN IF NOT EXISTS location TEXT,
    ADD COLUMN IF NOT EXISTS is_recurrence BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS source TEXT,
    ADD COLUMN IF NOT EXISTS root_cause TEXT,
    ADD COLUMN IF NOT EXISTS root_cause_type TEXT,
    ADD COLUMN IF NOT EXISTS analysis_method TEXT,
    ADD COLUMN IF NOT EXISTS disposition TEXT,
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_ncr_reports_scope_work_center
    ON ncr_reports (tenant_id, scope_work_center_id);
CREATE INDEX IF NOT EXISTS idx_ncr_reports_status_created
    ON ncr_reports (tenant_id, status, created_at DESC);

-- ── capas: reconcile to the CapaExtended service model ────────────────────
ALTER TABLE capas
    DROP CONSTRAINT IF EXISTS capas_status_check;
ALTER TABLE capas
    ADD CONSTRAINT capas_status_check
    CHECK (status IN ('open', 'analysis_in_progress', 'approved',
                      'implementation_in_progress', 'verification_in_progress', 'closed',
                      'draft', 'pending_approval', 'root_cause_analysis', 'action_planning',
                      'implementing', 'verification', 'effectiveness_check',
                      'pending_closure', 'rejected', 'cancelled'));

ALTER TABLE capas
    ALTER COLUMN owner_id DROP NOT NULL,
    ALTER COLUMN action_plan SET DEFAULT '';

ALTER TABLE capas
    ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS capa_type VARCHAR(20) NOT NULL DEFAULT 'corrective'
        CHECK (capa_type IN ('corrective', 'preventive', 'improvement')),
    ADD COLUMN IF NOT EXISTS priority VARCHAR(20) NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low', 'medium', 'high', 'emergency')),
    ADD COLUMN IF NOT EXISTS nc_ids UUID[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS details JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_capas_scope_work_center
    ON capas (tenant_id, scope_work_center_id);
CREATE INDEX IF NOT EXISTS idx_capas_status_created
    ON capas (tenant_id, status, created_at DESC);

-- ── audits: reconcile to the Audit service model ──────────────────────────
ALTER TABLE audits
    ADD COLUMN IF NOT EXISTS auditor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS details JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_audits_scope_work_center
    ON audits (tenant_id, scope_work_center_id);
CREATE INDEX IF NOT EXISTS idx_audits_status_created
    ON audits (tenant_id, status, created_at DESC);
