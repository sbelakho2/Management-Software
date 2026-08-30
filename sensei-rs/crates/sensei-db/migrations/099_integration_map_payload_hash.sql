-- Integration map payload hash (item 4): the source-version comparison
-- needs the CURRENT payload's hash on the mapping row. Migration 098
-- intended to add `payload_hash` but only added the source-version
-- columns; the importer writes it. This migration adds the column
-- (a NEW migration — never edit the applied 098).
ALTER TABLE integration_entity_map
    ADD COLUMN IF NOT EXISTS payload_hash VARCHAR(64);
