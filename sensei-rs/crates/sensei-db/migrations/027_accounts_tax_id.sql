-- Tax identification number for CRM accounts.

ALTER TABLE accounts ADD COLUMN IF NOT EXISTS tax_id VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_accounts_tax_id ON accounts (tenant_id, tax_id) WHERE tax_id IS NOT NULL;
