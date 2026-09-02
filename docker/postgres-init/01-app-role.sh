#!/bin/bash
# RLS requires the application to connect as a NON-OWNER role: the table
# owner bypasses ordinary RLS (FORCE ROW LEVEL SECURITY now removes that
# exemption, but the app identity must still be distinct so grants and
# ownership stay clean).
#
# CANONICAL sensei_app grants (twenty-third audit P1 — grant unification):
# this file is the ONE source of the production application grants; the
# least-privilege CI gate (.github/workflows/db-contract.yml) executes
# THIS script instead of maintaining its own grant list, and no other
# script grants the app role. The grants are EXPLICIT and audited:
#
#   - table DML: SELECT/INSERT/UPDATE/DELETE on the public schema's tenant
#     tables, plus the same default privileges for tables the migration
#     owner creates later;
#   - EXECUTE ONLY ON federation_governance_edges() — NEVER
#     GRANT EXECUTE ON ALL FUNCTIONS (that would hand the app role every
#     migration/admin function), and NEVER on
#     federation_governance_edges_for(uuid), which migration 156 revokes
#     from PUBLIC and keeps migration/admin-only.
#
# No other functions are granted today, so none are listed here.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sensei_app') THEN
            CREATE ROLE sensei_app LOGIN PASSWORD '${SENSEI_APP_PASSWORD}';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO sensei_app;
    GRANT USAGE ON SCHEMA public TO sensei_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sensei_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sensei_app;
    -- The ONE federation-governance function the app role may execute:
    -- the no-argument, tenant-context-bound form. This init script can
    -- run BEFORE the application migrations create the function
    -- (docker-entrypoint runs at first database boot), so the grant is
    -- applied when the function is present; while it is absent the app
    -- role still holds EXECUTE through the PUBLIC default that migration
    -- 156 keeps on the no-argument form. NEVER granted here (and revoked
    -- from PUBLIC by migration 156): federation_governance_edges_for(uuid).
    DO \$\$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_proc p
                   JOIN pg_namespace n ON n.oid = p.pronamespace
                   WHERE n.nspname = 'public'
                     AND p.proname = 'federation_governance_edges'
                     AND p.pronargs = 0) THEN
            EXECUTE 'GRANT EXECUTE ON FUNCTION public.federation_governance_edges() TO sensei_app';
        ELSE
            RAISE NOTICE 'federation_governance_edges() not present yet — the migration-156 PUBLIC default EXECUTE on the no-argument form applies once the migrations create it';
        END IF;
    END
    \$\$;
EOSQL
