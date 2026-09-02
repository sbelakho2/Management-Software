-- Federation-governance edges (twenty-first audit item 4): the ONLY
-- cross-tenant federation-governance boundary. The edge loader joins
-- `federation_memberships` to the PEER tenant's `site_manifests` and
-- `country_policies` — tables with FORCE RLS and tenant-local policies —
-- so under a production non-BYPASSRLS role with app.tenant_id set to the
-- SOURCE tenant, the peer rows are invisible and correct edge logic
-- becomes unusable. This function is SECURITY DEFINER: it executes with
-- the migration owner's rights, so RLS cannot hide the peer metadata the
-- residency decision needs. It is deliberately NARROW: federation-edge
-- metadata only (peer country, residency code, policy revision, the
-- membership's own governance labels) — never business payload rows —
-- and callers are granted EXECUTE explicitly; PUBLIC never gets it.
CREATE OR REPLACE FUNCTION federation_governance_edges(p_source_tenant uuid)
RETURNS TABLE(peer_tenant_id uuid, peer_country text, peer_residency text,
              peer_policy_revision bigint, allowed_classes jsonb,
              residency_policy text, allowed_countries jsonb)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT fm.peer_tenant_id, sm.country, cp.data_residency,
           COALESCE(cpv.revision, 0), fm.allowed_data_classes,
           fm.residency_policy, fm.allowed_countries
    FROM federation_memberships fm
    JOIN site_manifests sm ON sm.tenant_id = fm.peer_tenant_id
    JOIN country_policies cp
         ON cp.tenant_id = fm.peer_tenant_id AND cp.country = sm.country
    LEFT JOIN country_policy_versions cpv
           ON cpv.tenant_id = fm.peer_tenant_id AND cpv.country = sm.country
    WHERE fm.tenant_id = p_source_tenant
$$;

-- The migration owner keeps EXECUTE; every other role must be granted it
-- explicitly (the test grants it to the app role; PUBLIC never executes
-- the cross-tenant boundary by default).
REVOKE ALL ON FUNCTION federation_governance_edges(uuid) FROM PUBLIC;
