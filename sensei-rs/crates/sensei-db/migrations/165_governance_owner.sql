-- Governance-function owner transfer (twenty-sixth audit P1 item 5): the
-- SECURITY DEFINER governance edges (migration 156) are owned by the
-- migrator role by default; 25th-audit role hardening created the
-- narrower `sensei_governance_definer` owner in the canonical docker init
-- script (docker/postgres-init/01-app-role.sh), which runs BEFORE the
-- migration chain on a clean bootstrap. This migration LANDs the owner
-- transfer as an executable step so the ownership is correct no matter
-- how the schema is provisioned — but only when the role exists (a
-- minimal/CI bootstrap that skipped the init script must not fail).
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'sensei_governance_definer') THEN
        ALTER FUNCTION public.federation_governance_edges() OWNER TO sensei_governance_definer;
        ALTER FUNCTION public.federation_governance_edges_for(uuid) OWNER TO sensei_governance_definer;
    END IF;
END $$;
