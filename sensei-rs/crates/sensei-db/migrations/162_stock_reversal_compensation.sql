-- Twenty-fifth audit P1: compensating stock-move reversal and the
-- site-local receiving location.
--
-- 1. Reversal no longer merely flips metadata: reversing a move now
--    posts a NEW 'posted' COMPENSATING move of the opposite direction,
--    so the ledger always sums back to the physical balance. The new
--    compensating row links back through `reversal_of` (the original
--    move), and the original row is marked `reversed_by_move` (the
--    compensating entry that undid its effect). Both columns are
--    self-referencing with ON DELETE SET NULL, mirroring the migration
--    160 `reversed_by` pattern.
--
-- 2. `site_manifests` gains the SITE-CONFIGURED default receiving
--    location used when a receipt lands at a site with no inventory row
--    for the product (twenty-fifth audit P1 item: a receipt's fallback
--    must be THIS site's configured receiving label — never a label
--    discovered tenant-wide from another plant). NULL means the site
--    has not configured one and the service falls back to the literal
--    site-local label 'receiving'.

ALTER TABLE stock_moves
    ADD COLUMN IF NOT EXISTS reversal_of UUID REFERENCES stock_moves(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS reversed_by_move UUID REFERENCES stock_moves(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_stock_moves_reversal_of
    ON stock_moves (tenant_id, reversal_of);
CREATE INDEX IF NOT EXISTS idx_stock_moves_reversed_by_move
    ON stock_moves (tenant_id, reversed_by_move);

ALTER TABLE site_manifests
    ADD COLUMN IF NOT EXISTS default_receiving_location VARCHAR(255);
