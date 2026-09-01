-- shift_id as a REAL scope dimension (seventeenth audit item: TWI shift
-- scoping). Qualifications are anchored to the SHIFT they were
-- demonstrated on — coverage queries filter on the actual assignment
-- dimension, never on slot-name substring matching.
ALTER TABLE skill_qualifications
    ADD COLUMN IF NOT EXISTS shift_id UUID REFERENCES shifts(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_skill_qual_shift
    ON skill_qualifications (tenant_id, shift_id);
