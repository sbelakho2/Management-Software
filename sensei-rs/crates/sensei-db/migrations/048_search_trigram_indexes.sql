-- Trigram search support for database-mode unified search.
--
-- The DatabaseSearchService (sensei-api) ranks matches with pg_trgm
-- `similarity()` over the typed entity tables. Migration 016 already added
-- trigram indexes for users (name, email), accounts (name), contacts
-- (name) and products (name, sku); this migration completes coverage with
-- accounts(email) and adapts the contacts index to the real schema
-- (contacts has first_name/last_name columns, not a `name` column — the
-- 016 index on `contacts(name)` was written against a column that never
-- existed).
--
-- All statements are idempotent (IF NOT EXISTS), so re-runs are no-ops.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_accounts_name_trgm
    ON accounts USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_accounts_email_trgm
    ON accounts USING GIN (email gin_trgm_ops);

-- Expression index over the full contact display name (first + last).
CREATE INDEX IF NOT EXISTS idx_contacts_full_name_trgm
    ON contacts USING GIN ((first_name || ' ' || last_name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_name_trgm
    ON products USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_sku_trgm
    ON products USING GIN (sku gin_trgm_ops);
