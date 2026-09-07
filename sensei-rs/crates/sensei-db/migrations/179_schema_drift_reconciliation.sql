-- Schema/service drift reconciliation (thirtieth-first-audit item 17):
-- the module suite must cover EVERY module, so the four documented
-- schema/service drifts converge. This migration carries the narrow
-- additive schema changes only; the service SQL is aligned to the REAL
-- product tables in the matching sensei-services changes:
--
--   1. HR employees — NO schema change here. The REAL employees table
--      (002-era: employee_number, first_name/last_name, manager_id) is
--      the product's canonical identity table (178 hardens the
--      (tenant_id, user_id) mapping on it; 009 FKs point at it). The
--      DatabaseHrService employee SQL (which read employee_code /
--      full_name / supervisor_id) is rewritten to the real columns.
--
--   2. Supply chain RFQs/quotes — the RFQ service SQL is rewritten to
--      the REAL normalized shape (rfqs.supplier_id -> suppliers.name,
--      child rows in rfq_line_items), and the quote service SQL to
--      `sales_quotes` (migration 098's canonical customer quotation
--      table: customer_id/customer_name + JSONB line_items +
--      NUMERIC total_amount + 'converted' lifecycle). Schema changes
--      below are the ONLY genuinely missing pieces of that canonical
--      shape:
--        a. rfq_line_items.product_id — migration 098's canonical
--           child-row model (product_id, part_number, quantity,
--           unit_of_measure) was a CREATE TABLE IF NOT EXISTS no-op
--           against 004's earlier child table, so the LIVE table never
--           gained product_id, which both the integration importer
--           (098-era INSERT) and the RFQ service need. The 004-era
--           UNIQUE(rfq_id, line_number) + NOT NULL line_number is
--           incompatible with 098's (tenant_id, rfq_id, part_number)
--           identity — drop the NOT NULL so rows written by the
--           canonical writers (no line_number) are admitted; NULLs stay
--           distinct under the surviving unique index, and service
--           writers still number their rows 1..n.
--        b. sales_quotes.status — the module contract CANCELS quotes
--           (delete_quote: "business history — cancelled, never
--           erased"), and the RFQ counterpart's vocabulary already
--           admits 'cancelled'. Add the genuinely richer terminal state
--           to the 098 vocabulary (draft/submitted/approved/rejected/
--           converted/expired + cancelled); no existing row changes.
--
--   3. AI model_registry — NO schema change here. Migration 176 already
--      reconciled the table (JSONB ModelStatus, model_type vocabulary
--      CHECK, UNIQUE(tenant_id, model_name), version '0.0.0'); the
--      DatabaseAiService::queue_model_training INSERT is rewritten to
--      that shape.
--
--   4. notifications.notification_type — NO schema change here. The
--      CHECK vocabulary ('alert','reminder','approval_request',
--      'mention','system') already covers the live senders' intent:
--      informational task/state-machine sends map to 'system' and
--      event-rule trigger sends map to 'alert' at the callers.
--
-- Guarded + idempotent throughout (re-runs are no-ops); only the two
-- tables above are touched.

-- ── 2a. rfq_line_items: canonical 098 child-row shape ─────────────────────
ALTER TABLE rfq_line_items
    ADD COLUMN IF NOT EXISTS product_id UUID REFERENCES products(id) ON DELETE SET NULL;

-- The canonical writers (integration importer 098-era INSERT and the
-- supply-chain service) do not number rows; 004's NOT NULL line_number
-- is the legacy leftover. NULLs remain distinct under the surviving
-- UNIQUE(rfq_id, line_number). Guarded for the exotic 098-only topology
-- where line_number does not exist at all.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'rfq_line_items'
           AND column_name = 'line_number'
           AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE public.rfq_line_items ALTER COLUMN line_number DROP NOT NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_rfq_line_items_tenant_rfq
    ON rfq_line_items (tenant_id, rfq_id);

-- ── 2b. sales_quotes.status: module-contract 'cancelled' terminal ─────────
-- (098 created the table with an inline CHECK whose name is
-- sales_quotes_status_check; re-create the constraint with the extended
-- vocabulary — the drop is conditional so re-runs converge.)
ALTER TABLE sales_quotes DROP CONSTRAINT IF EXISTS sales_quotes_status_check;
ALTER TABLE sales_quotes
    ADD CONSTRAINT sales_quotes_status_check
        CHECK (status IN ('draft', 'submitted', 'approved', 'rejected',
                          'converted', 'expired', 'cancelled'));
