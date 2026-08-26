-- =============================================================================
-- Reconcile the finance tables with the SERVICE model (canonical) and move
-- monetary columns to exact NUMERIC(19,4).
--
-- The service domain is authoritative: invoices carry customer_id/
-- customer_name/line_items/tax_percentage/paid_at; payments carry
-- received_at; budgets use fiscal_year/category/allocated/remaining; journal
-- entries use debit_account/credit_account/amount; cost rollups carry
-- product_name/rollup_date. The original 002 schema used a different
-- (counterparty-based) shape and DOUBLE PRECISION money.
-- =============================================================================

-- ── invoices ───────────────────────────────────────────────────────────────
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS customer_id UUID,
    ADD COLUMN IF NOT EXISTS customer_name VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS line_items JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS tax_percentage NUMERIC(19,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ,
    DROP COLUMN IF EXISTS invoice_type,
    DROP COLUMN IF EXISTS counterparty_id,
    DROP COLUMN IF EXISTS counterparty_name;

ALTER TABLE invoices
    ALTER COLUMN subtotal TYPE NUMERIC(19,4),
    ALTER COLUMN tax_amount TYPE NUMERIC(19,4),
    ALTER COLUMN total_amount TYPE NUMERIC(19,4);

CREATE INDEX IF NOT EXISTS idx_invoices_tenant_status ON invoices(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_due ON invoices(tenant_id, due_date)
    WHERE status NOT IN ('paid', 'cancelled');

-- ── payments ───────────────────────────────────────────────────────────────
ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    DROP COLUMN IF EXISTS payment_type,
    DROP COLUMN IF EXISTS status,
    DROP COLUMN IF EXISTS counterparty_id;

ALTER TABLE payments
    ALTER COLUMN amount TYPE NUMERIC(19,4);

-- ── budgets ────────────────────────────────────────────────────────────────
ALTER TABLE budgets
    ADD COLUMN IF NOT EXISTS fiscal_year INT NOT NULL DEFAULT EXTRACT(YEAR FROM NOW()),
    ADD COLUMN IF NOT EXISTS category VARCHAR(100) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS allocated_amount NUMERIC(19,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS remaining_amount NUMERIC(19,4) NOT NULL DEFAULT 0,
    DROP COLUMN IF EXISTS budget_code,
    DROP COLUMN IF EXISTS name,
    DROP COLUMN IF EXISTS budget_type,
    DROP COLUMN IF EXISTS fiscal_period,
    DROP COLUMN IF EXISTS budgeted_amount,
    DROP COLUMN IF EXISTS committed_amount,
    DROP COLUMN IF EXISTS status,
    DROP COLUMN IF EXISTS owner_id,
    DROP COLUMN IF EXISTS notes;

ALTER TABLE budgets
    ALTER COLUMN spent_amount TYPE NUMERIC(19,4);

-- ── journal_entries ────────────────────────────────────────────────────────
ALTER TABLE journal_entries
    ADD COLUMN IF NOT EXISTS debit_account VARCHAR(50) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS credit_account VARCHAR(50) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS amount NUMERIC(19,4) NOT NULL DEFAULT 0,
    DROP COLUMN IF EXISTS entry_type,
    DROP COLUMN IF EXISTS debit_total,
    DROP COLUMN IF EXISTS credit_total,
    DROP COLUMN IF EXISTS period;

-- Posted-accounting model: status + posted_at + reversal_of (corrections
-- create reversing entries; history is never edited).
ALTER TABLE journal_entries
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'posted'
        CHECK (status IN ('draft', 'posted', 'reversed')),
    ADD COLUMN IF NOT EXISTS posted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reversal_of UUID REFERENCES journal_entries(id) ON DELETE SET NULL;

-- ── cost_rollups ───────────────────────────────────────────────────────────
ALTER TABLE cost_rollups
    ADD COLUMN IF NOT EXISTS product_name VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS rollup_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    DROP COLUMN IF EXISTS version,
    DROP COLUMN IF EXISTS currency,
    DROP COLUMN IF EXISTS status,
    DROP COLUMN IF EXISTS computed_at,
    DROP COLUMN IF EXISTS computed_by;

ALTER TABLE cost_rollups
    ALTER COLUMN total_cost TYPE NUMERIC(19,4),
    ALTER COLUMN material_cost TYPE NUMERIC(19,4),
    ALTER COLUMN labor_cost TYPE NUMERIC(19,4),
    ALTER COLUMN overhead_cost TYPE NUMERIC(19,4);
