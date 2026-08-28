-- Production service schema reconciliation (P0-1): the DatabaseProductionService
-- contract requires a richer work_orders / production_orders shape than the
-- base migrations provide. The service is the source of truth for the API —
-- these columns are added idempotently so both fresh and existing databases
-- converge on the contract.
ALTER TABLE work_orders
    ADD COLUMN IF NOT EXISTS product_name VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS quantity_completed BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS priority VARCHAR(20) NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    ADD COLUMN IF NOT EXISTS actual_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS actual_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS assigned_to UUID[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT '';

ALTER TABLE production_orders
    ADD COLUMN IF NOT EXISTS planned_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS planned_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS actual_end TIMESTAMPTZ;

-- The production-order domain vocabulary starts at 'planned' (the service
-- sets it on creation) — the base CHECK predates that contract.
ALTER TABLE production_orders DROP CONSTRAINT IF EXISTS production_orders_status_check;
ALTER TABLE production_orders ADD CONSTRAINT production_orders_status_check
    CHECK (status IN ('planned', 'created', 'released', 'in_progress', 'completed', 'cancelled', 'on_hold'));

-- Production quantities are COUNTS (whole units) — the base FLOAT8 columns
-- drift from the service contract (i64). Cast to BIGINT; fractional
-- leftovers are rounded to the nearest whole unit (never fabricated).
ALTER TABLE production_orders
    ALTER COLUMN quantity_planned TYPE BIGINT USING ROUND(quantity_planned)::BIGINT,
    ALTER COLUMN quantity_produced TYPE BIGINT USING ROUND(quantity_produced)::BIGINT,
    ALTER COLUMN quantity_scrapped TYPE BIGINT USING ROUND(quantity_scrapped)::BIGINT;
