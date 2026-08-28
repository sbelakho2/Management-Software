-- Full-text search support for Sensei ERP
--
-- Enables trigram-based fuzzy search across key entity text columns
-- and provides a unified search_all() function for cross-entity search.
--
-- Also adds a user-level notification preferences table (simple per-user
-- boolean flags model) complementing the existing channel/event-type table.

-- ── pg_trgm Extension ────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ── GIN Indexes for Trigram Search ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email_trgm ON users USING GIN (email gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_users_name_trgm ON users USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_accounts_name_trgm ON accounts USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_contacts_name_trgm ON contacts USING GIN (last_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON products USING GIN (name gin_trgm_ops);

-- ── User Notification Preferences ────────────────────────────────────────────
-- Simple per-user preferences model complementing the channel/event-type
-- table in 011_system_tables.sql. Each user has a single row here.
CREATE TABLE IF NOT EXISTS user_notification_preferences (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    push_notifications  BOOLEAN NOT NULL DEFAULT TRUE,
    in_app_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    digest_frequency    VARCHAR(20) NOT NULL DEFAULT 'instant'
                        CHECK (digest_frequency IN ('instant', 'hourly', 'daily', 'never')),
    quiet_hours_start   TIME,
    quiet_hours_end     TIME,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_notif_prefs_tenant ON user_notification_preferences(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_notif_prefs_user ON user_notification_preferences(user_id);

-- ── Unified Search Function ─────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION search_all(query text, p_tenant_id uuid)
RETURNS TABLE(result_type text, result_id uuid, result_title text, relevance real) AS $$
BEGIN
    RETURN QUERY
    -- Search users
    SELECT 'user'::text, u.id, u.name, similarity(u.name, query) + similarity(COALESCE(u.email,''), query) * 0.5
    FROM users u WHERE u.tenant_id = p_tenant_id AND (u.name ILIKE '%' || query || '%' OR u.email ILIKE '%' || query || '%')
    UNION ALL
    -- Search accounts
    SELECT 'account'::text, a.id, a.name, similarity(a.name, query)
    FROM accounts a WHERE a.tenant_id = p_tenant_id AND a.name ILIKE '%' || query || '%'
    UNION ALL
    -- Search contacts (first/last name — the actual schema)
    SELECT 'contact'::text, c.id, c.last_name, similarity(COALESCE(c.last_name,''), query) + similarity(COALESCE(c.first_name,''), query) * 0.5
    FROM contacts c WHERE c.tenant_id = p_tenant_id
       AND (COALESCE(c.last_name,'') ILIKE '%' || query || '%' OR COALESCE(c.first_name,'') ILIKE '%' || query || '%')
    UNION ALL
    -- Search products (product_number is the unique business key)
    SELECT 'product'::text, p.id, p.name, similarity(p.name, query) + similarity(COALESCE(p.product_number,''), query) * 0.3
    FROM products p WHERE p.tenant_id = p_tenant_id AND (p.name ILIKE '%' || query || '%' OR p.product_number ILIKE '%' || query || '%')
    ORDER BY relevance DESC
    LIMIT 50;
END;
$$ LANGUAGE plpgsql STABLE;
