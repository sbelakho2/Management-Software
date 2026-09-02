-- Tenant-bound federation-governance edges (twenty-second audit P0/P1
-- items 2-4): migration 153's `federation_governance_edges(p_source_tenant
-- uuid)` TRUSTED the caller-supplied tenant — under a production
-- non-BYPASSRLS app role any session (that may freely `set_config`
-- `app.tenant_id`) could pass ANOTHER tenant's id and read that tenant's
-- cross-tenant federation-governance metadata, and the loader had to carry
-- the tenant through the call. This migration closes the trust boundary:
--
--  1. `federation_governance_edges()` — NO parameter. The source tenant is
--     read INSIDE the function from the session context
--     (`current_setting('app.tenant_id', true)`); an ABSENT setting
--     reports '' (not NULL), so NULLIF folds it to NULL and the
--     `WHERE fm.tenant_id = NULL` filter yields zero rows — fail-closed,
--     never an error and never a cross-tenant read. PUBLIC keeps EXECUTE
--     on the no-argument form: the session context it reads is exactly
--     the context the app role must set (via `set_config`, permitted for
--     any role) to read its own tenant-scoped rows at all, so the
--     function exposes nothing a FORCE-RLS SELECT under the same context
--     would not. The old parameterized signature is DROPPED so no caller
--     can bypass the binding.
--
--  2. `federation_governance_edges_for(p_source_tenant uuid)` — the
--     migration/admin-only escape hatch (maintenance, cross-tenant
--     reconciliation). EXECUTE is revoked from PUBLIC; it is not granted
--     to the app role, so only the migration owner (and roles granted it
--     explicitly) may call it.
--
--  3. Both functions now also return `peer_site_id` (the peer tenant's
--     `site_manifests.site_id` the projection would land on) and pin the
--     policy revision DETERMINISTICALLY with a lateral
--     `ORDER BY revision DESC LIMIT 1` over `country_policy_versions` —
--     the migration-153 plain LEFT JOIN produced one output row PER
--     VERSION ROW, duplicating edges whenever a country carried more than
--     one revision. The lateral yields exactly ONE revision per peer site.
DROP FUNCTION IF EXISTS federation_governance_edges(uuid);

CREATE OR REPLACE FUNCTION federation_governance_edges()
RETURNS TABLE(peer_tenant_id uuid, peer_site_id uuid, peer_country text,
              peer_residency text, peer_policy_revision bigint,
              allowed_classes jsonb, residency_policy text,
              allowed_countries jsonb)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT fm.peer_tenant_id, sm.site_id, sm.country, cp.data_residency,
           COALESCE(cpv.revision, 0), fm.allowed_data_classes,
           fm.residency_policy, fm.allowed_countries
    FROM federation_memberships fm
    JOIN site_manifests sm ON sm.tenant_id = fm.peer_tenant_id
    JOIN country_policies cp
         ON cp.tenant_id = fm.peer_tenant_id AND cp.country = sm.country
    LEFT JOIN LATERAL (
        SELECT cpv2.revision
        FROM country_policy_versions cpv2
        WHERE cpv2.tenant_id = fm.peer_tenant_id
          AND cpv2.country = sm.country
        ORDER BY cpv2.revision DESC
        LIMIT 1
    ) cpv ON TRUE
    WHERE fm.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
$$;

-- Migration/admin-only variant: explicit tenant argument, EXECUTE revoked
-- from PUBLIC (the app role never gets it — see migration 153's note:
-- every other role must be granted it explicitly).
CREATE OR REPLACE FUNCTION federation_governance_edges_for(p_source_tenant uuid)
RETURNS TABLE(peer_tenant_id uuid, peer_site_id uuid, peer_country text,
              peer_residency text, peer_policy_revision bigint,
              allowed_classes jsonb, residency_policy text,
              allowed_countries jsonb)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT fm.peer_tenant_id, sm.site_id, sm.country, cp.data_residency,
           COALESCE(cpv.revision, 0), fm.allowed_data_classes,
           fm.residency_policy, fm.allowed_countries
    FROM federation_memberships fm
    JOIN site_manifests sm ON sm.tenant_id = fm.peer_tenant_id
    JOIN country_policies cp
         ON cp.tenant_id = fm.peer_tenant_id AND cp.country = sm.country
    LEFT JOIN LATERAL (
        SELECT cpv2.revision
        FROM country_policy_versions cpv2
        WHERE cpv2.tenant_id = fm.peer_tenant_id
          AND cpv2.country = sm.country
        ORDER BY cpv2.revision DESC
        LIMIT 1
    ) cpv ON TRUE
    WHERE fm.tenant_id = p_source_tenant
$$;

REVOKE ALL ON FUNCTION federation_governance_edges_for(uuid) FROM PUBLIC;
