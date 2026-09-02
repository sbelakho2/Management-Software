-- Memory-anchor quarantine (eighteenth audit P1-13): migration 137 made
-- the anchor CHECK NOT VALID so upgrades survive legacy rows; the final
-- stage is: flag every legacy violation, EXCLUDE quarantined memory from
-- every context-serving path (service-side), and give operations an
-- explicit reconcile (discard) path. After the violation count is
-- proven 0, the VALIDATE CONSTRAINT stage completes the sequence.
ALTER TABLE organizational_memory
    ADD COLUMN IF NOT EXISTS quarantined BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_org_memory_quarantined
    ON organizational_memory (tenant_id) WHERE quarantined;

UPDATE organizational_memory
SET quarantined = TRUE
WHERE NOT (
    (tier = 'personal' AND owner_principal_id IS NOT NULL)
    OR (tier = 'role' AND slot_id IS NOT NULL)
    OR (tier = 'process' AND process IS NOT NULL AND process <> '')
    OR (tier = 'site' AND scope_site_id IS NOT NULL)
    OR (tier = 'corporate')
);
