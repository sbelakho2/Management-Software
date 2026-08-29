-- Fix search_all (item 71 discovery): the function body created by
-- migration 016 is a PL/pgSQL string — PostgreSQL does NOT validate it at
-- CREATE time, only at first CALL. The committed body has TWO defects
-- that make the unified search endpoint fail at runtime on every
-- deployment:
--
--   1. `ORDER BY relevance DESC LIMIT 50` is attached to a single
--      UNION ALL arm — PostgreSQL rejects it at runtime with
--      "invalid UNION/INTERSECT/EXCEPT ORDER BY clause".
--   2. The declared RETURNS TABLE says `result_title text`, but the
--      first arm returns `u.name` (VARCHAR(255)) — PostgreSQL requires
--      an exact type match, so the function fails with
--      "structure of query does not match function result type".
--
-- This migration replaces the function with a body whose ORDER BY/LIMIT
-- wrap the WHOLE union (a derived table) AND casts every title column to
-- the declared `text` type. This is a new migration (never edit an
-- applied one): databases that already recorded 016 keep their checksum,
-- and the function is fixed on upgrade; fresh databases get the corrected
-- function after 016 runs.
CREATE OR REPLACE FUNCTION search_all(query text, p_tenant_id uuid)
RETURNS TABLE(result_type text, result_id uuid, result_title text, relevance real) AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM (
        -- Search users
        SELECT 'user'::text AS result_type, u.id AS result_id, u.name::text AS result_title,
               (similarity(u.name, query) + similarity(COALESCE(u.email,''), query) * 0.5)::real AS relevance
        FROM users u WHERE u.tenant_id = p_tenant_id AND (u.name ILIKE '%' || query || '%' OR u.email ILIKE '%' || query || '%')
        UNION ALL
        -- Search accounts
        SELECT 'account'::text, a.id, a.name::text, similarity(a.name, query)::real
        FROM accounts a WHERE a.tenant_id = p_tenant_id AND a.name ILIKE '%' || query || '%'
        UNION ALL
        -- Search contacts (first/last name — the actual schema)
        SELECT 'contact'::text, c.id, c.last_name::text, (similarity(COALESCE(c.last_name,''), query) + similarity(COALESCE(c.first_name,''), query) * 0.5)::real
        FROM contacts c WHERE c.tenant_id = p_tenant_id
           AND (COALESCE(c.last_name,'') ILIKE '%' || query || '%' OR COALESCE(c.first_name,'') ILIKE '%' || query || '%')
        UNION ALL
        -- Search products (product_number is the unique business key)
        SELECT 'product'::text, p.id, p.name::text, (similarity(p.name, query) + similarity(COALESCE(p.product_number,''), query) * 0.3)::real
        FROM products p WHERE p.tenant_id = p_tenant_id AND (p.name ILIKE '%' || query || '%' OR p.product_number ILIKE '%' || query || '%')
    ) combined
    ORDER BY relevance DESC
    LIMIT 50;
END;
$$ LANGUAGE plpgsql STABLE;
