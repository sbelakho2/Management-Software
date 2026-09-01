-- Migration-from-real-history safety (seventeenth audit item): migration
-- 128 added the strict organizational_memory anchor CHECK immediately. On
-- a CLEAN database every row satisfies it, but an EXISTING installation
-- with legacy personal/site memory that predates the anchors would FAIL
-- the upgrade. This remediation recreates the CHECK as NOT VALID: new
-- rows are strictly enforced, legacy rows are grandfathered — the
-- upgrade can never fail on historical data, and the anchor law still
-- governs everything written after this migration.
ALTER TABLE organizational_memory
    DROP CONSTRAINT IF EXISTS organizational_memory_anchor_check;
ALTER TABLE organizational_memory
    ADD CONSTRAINT organizational_memory_anchor_check CHECK (
        (tier = 'personal' AND owner_principal_id IS NOT NULL)
        OR (tier = 'role' AND slot_id IS NOT NULL)
        OR (tier = 'process' AND process IS NOT NULL AND process <> '')
        OR (tier = 'site' AND scope_site_id IS NOT NULL)
        OR (tier = 'corporate')
    )
    NOT VALID;
