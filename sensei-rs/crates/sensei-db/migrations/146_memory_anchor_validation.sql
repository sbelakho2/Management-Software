-- Memory-anchor validation completion (nineteenth audit P2): migration
-- 141 quarantined anchor-violating rows; the reconcile operation
-- discards them. THIS migration makes the lifecycle observable and
-- completes the final stage: if the tenant's quarantine is empty the
-- anchor CHECK is VALIDATED and the completion is recorded; if
-- violations still exist the constraint stays NOT VALID and the state is
-- visible for alerting.
CREATE TABLE IF NOT EXISTS migration_state (
    migration_id   VARCHAR(100) PRIMARY KEY,
    state          VARCHAR(40) NOT NULL,
    details        JSONB NOT NULL DEFAULT '{}',
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO migration_state (migration_id, state, details)
VALUES ('141_memory_anchor_quarantine', 'applied', '{}')
ON CONFLICT (migration_id) DO UPDATE SET state = 'applied';

DO $$
DECLARE
    violations BIGINT;
BEGIN
    SELECT COUNT(*) INTO violations
    FROM organizational_memory
    WHERE NOT (
        (tier = 'personal' AND owner_principal_id IS NOT NULL)
        OR (tier = 'role' AND slot_id IS NOT NULL)
        OR (tier = 'process' AND process IS NOT NULL AND process <> '')
        OR (tier = 'site' AND scope_site_id IS NOT NULL)
        OR (tier = 'corporate')
    );
    IF violations = 0 THEN
        ALTER TABLE organizational_memory VALIDATE CONSTRAINT organizational_memory_anchor_check;
        UPDATE migration_state
           SET state = 'completed', details = jsonb_build_object('violations', 0)
         WHERE migration_id = '141_memory_anchor_quarantine';
        RAISE NOTICE 'memory anchor CHECK validated: % violations', violations;
    ELSE
        UPDATE migration_state
           SET state = 'quarantine_remaining',
               details = jsonb_build_object('violations', violations)
         WHERE migration_id = '141_memory_anchor_quarantine';
        RAISE NOTICE 'memory anchor CHECK stays NOT VALID: % violations remain — run reconcile_quarantined_memory', violations;
    END IF;
END $$;
