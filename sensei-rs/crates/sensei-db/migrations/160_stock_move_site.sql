-- Twenty-fourth audit P0 (items 1-2): stock movements become SITE-scoped
-- and REVERSIBLE — never erasable.
--
-- 1. stock_moves gains `site_id`: the site the move physically happened at
--    (the source inventory row's site). Without it the ledger is not
--    site-attributable and a scoped listing cannot be honest. The column
--    is backfilled from inventory_items at the move's (tenant, product,
--    to_location) — and from_location for the remaining NULLs — but ONLY
--    where the resolution is UNAMBIGUOUS (exactly one distinct site);
--    ambiguous legacy rows keep NULL rather than lie.
--
-- 2. Reversal metadata replaces deletion: a move is never erased, it is
--    flipped to status 'reversed' with the actor, timestamp and reason.
--
-- 3. stock_moves RLS is re-created FAIL-CLOSED (the migration-154
--    pattern): once the transaction-scoped app.tenant_id context is
--    expected, rows are visible ONLY under their own tenant. All
--    stock_moves writers run inside tenant-scoped transactions
--    (with_tenant_tx).
--
-- 4. inventory_items uniqueness becomes SITE-scoped: two sites may each
--    hold the same product at the same LOCATION NAME ('main'), so the
--    legacy tenant-global unique key (tenant, product, location,
--    lot_number) is replaced by a site-scoped key for sited rows, with
--    the legacy key preserved for the pre-site (NULL site_id) rows.

ALTER TABLE stock_moves
    ADD COLUMN IF NOT EXISTS site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'posted'
        CHECK (status IN ('posted', 'reversed')),
    ADD COLUMN IF NOT EXISTS reversed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS reversed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reversal_reason VARCHAR(300);

CREATE INDEX IF NOT EXISTS idx_stock_moves_site
    ON stock_moves (tenant_id, site_id, moved_at DESC);
CREATE INDEX IF NOT EXISTS idx_stock_moves_status
    ON stock_moves (tenant_id, status);

-- Backfill site_id from inventory_items: first by to_location (the
-- destination of a receipt/transfer/adjustment move), then by
-- from_location for the rows still unresolved. Only (tenant, product,
-- location) groups whose inventory rows name EXACTLY ONE distinct site
-- are candidates — ambiguous groups stay NULL.
UPDATE stock_moves sm
SET site_id = u.site_id
FROM (
    SELECT ii.tenant_id, ii.product_id, ii.location, ii.site_id
    FROM inventory_items ii
    JOIN (
        SELECT tenant_id, product_id, location
        FROM inventory_items
        WHERE site_id IS NOT NULL
        GROUP BY tenant_id, product_id, location
        HAVING COUNT(DISTINCT site_id) = 1
    ) u ON u.tenant_id = ii.tenant_id
       AND u.product_id = ii.product_id
       AND u.location = ii.location
    WHERE ii.site_id IS NOT NULL
    GROUP BY ii.tenant_id, ii.product_id, ii.location, ii.site_id
) u
WHERE sm.site_id IS NULL
  AND sm.tenant_id = u.tenant_id
  AND sm.product_id = u.product_id
  AND sm.to_location = u.location;

UPDATE stock_moves sm
SET site_id = u.site_id
FROM (
    SELECT ii.tenant_id, ii.product_id, ii.location, ii.site_id
    FROM inventory_items ii
    JOIN (
        SELECT tenant_id, product_id, location
        FROM inventory_items
        WHERE site_id IS NOT NULL
        GROUP BY tenant_id, product_id, location
        HAVING COUNT(DISTINCT site_id) = 1
    ) u ON u.tenant_id = ii.tenant_id
       AND u.product_id = ii.product_id
       AND u.location = ii.location
    WHERE ii.site_id IS NOT NULL
    GROUP BY ii.tenant_id, ii.product_id, ii.location, ii.site_id
) u
WHERE sm.site_id IS NULL
  AND sm.tenant_id = u.tenant_id
  AND sm.product_id = u.product_id
  AND sm.from_location = u.location;

-- Fail-closed RLS on stock_moves (migration-154 pattern).
ALTER TABLE stock_moves ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_moves FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON stock_moves;
CREATE POLICY tenant_isolation ON stock_moves
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Site-scoped inventory identity: the same location NAME may exist at
-- several sites of one tenant. The legacy tenant-global unique key is
-- dropped; sited rows are unique per site, legacy NULL-site rows keep
-- the exact legacy rule (partial index) so pre-site data stays protected.
ALTER TABLE inventory_items
    DROP CONSTRAINT IF EXISTS inventory_items_tenant_id_product_id_location_lot_number_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_items_site_identity
    ON inventory_items (tenant_id, site_id, product_id, location, lot_number)
    WHERE site_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_items_legacy_identity
    ON inventory_items (tenant_id, product_id, location, lot_number)
    WHERE site_id IS NULL;
