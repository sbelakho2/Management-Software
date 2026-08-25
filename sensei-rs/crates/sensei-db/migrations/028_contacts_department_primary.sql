-- Contact department and primary-contact designation.

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS department VARCHAR(100);
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS is_primary BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_contacts_department ON contacts (tenant_id, department) WHERE department IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contacts_primary ON contacts (tenant_id, account_id) WHERE is_primary = TRUE;
