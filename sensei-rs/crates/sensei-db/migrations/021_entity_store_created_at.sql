-- entity_store: enforce created_at and backfill from data
--
-- entity_store rows carry the entity's own `created_at` inside the JSONB
-- `data` payload. This migration makes the column NOT NULL (with NOW()
-- default) and backfills existing rows from `data->>'created_at'` where
-- that value is parseable, keeping the default for everything else.

-- Backfill: try-cast each entity's embedded created_at; unparseable values
-- keep the existing timestamp.
DO $$
DECLARE
    row record;
    parsed timestamptz;
BEGIN
    FOR row IN SELECT entity_type, id, data FROM entity_store
               WHERE data->>'created_at' IS NOT NULL LOOP
        BEGIN
            parsed := (row.data->>'created_at')::timestamptz;
            UPDATE entity_store
               SET created_at = parsed
             WHERE entity_type = row.entity_type AND id = row.id;
        EXCEPTION WHEN others THEN
            NULL; -- not parseable; keep default
        END;
    END LOOP;
END $$;

ALTER TABLE entity_store
    ALTER COLUMN created_at SET NOT NULL;

-- Common query pattern: list entities of a type ordered by creation.
CREATE INDEX IF NOT EXISTS idx_entity_store_type_created
    ON entity_store (entity_type, created_at);
