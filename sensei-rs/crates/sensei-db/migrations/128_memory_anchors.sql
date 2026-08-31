-- Organizational memory anchors (sixteenth audit items 40-41): each tier
-- STRUCTURALLY requires its anchor — personal memory is bound to a
-- principal, role memory to a slot, process memory to a process, site
-- memory to a site. The database enforces it; it is not a service habit.
ALTER TABLE organizational_memory
    ADD COLUMN IF NOT EXISTS owner_principal_id UUID,
    ADD COLUMN IF NOT EXISTS scope_site_id UUID,
    ADD COLUMN IF NOT EXISTS provenance_event_ids JSONB NOT NULL DEFAULT '[]';

ALTER TABLE organizational_memory
    DROP CONSTRAINT IF EXISTS organizational_memory_anchor_check;
ALTER TABLE organizational_memory
    ADD CONSTRAINT organizational_memory_anchor_check CHECK (
        (tier = 'personal' AND owner_principal_id IS NOT NULL)
        OR (tier = 'role' AND slot_id IS NOT NULL)
        OR (tier = 'process' AND process IS NOT NULL AND process <> '')
        OR (tier = 'site' AND scope_site_id IS NOT NULL)
        OR (tier = 'corporate')
    );
