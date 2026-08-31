-- Site manifest LIFECYCLE (sixteenth audit items 63-64/96): bootstrap
-- only PROVISIONS a site (manifest + canonical metrics); a site becomes
-- operational through the guarded ladder Draft → Validated →
-- Provisioning → ReadyForTraining → OperationalQualification → Active.
-- `status` records where the site is on that ladder and
-- `validation_report` stores the last operational-qualification report.
ALTER TABLE site_manifests
    ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','validated','provisioning','ready_for_training','operational_qualification','active')),
    ADD COLUMN IF NOT EXISTS validation_report JSONB NOT NULL DEFAULT '{}';
