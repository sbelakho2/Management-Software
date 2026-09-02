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
#
# MIGRATION-OWNER SPLIT (twenty-fourth audit P0 — production bootstrap):
# the migration chain is NEVER run by the app role. This script ALSO
# defines sensei_migrator, the LOGIN that owns every schema object: it
# runs the chain (sensei-api --migrate-only) with NOSUPERUSER NOBYPASSRLS
# CREATEDB NOCREATEROLE, holds CREATE ON SCHEMA public and ALL ON the
# database, and is the owner of the migration-created tables, indexes and
# SECURITY DEFINER functions (the migration role must be the function
# owner). sensei_app is stripped of schema CREATE entirely (REVOKE CREATE
# ON SCHEMA public FROM PUBLIC — the explicit grant back below is the only
# path back in, and it goes to sensei_migrator alone), so a production API
# connecting as sensei_app can never DDL, and the default privileges below
# are declared FOR ROLE sensei_migrator so every table the chain creates
# later inherits the app role's DML grants automatically.
set -e
: "${SENSEI_APP_PASSWORD:?SENSEI_APP_PASSWORD must be set (production docker-compose and db-contract CI provide it)}"
: "${SENSEI_MIGRATOR_PASSWORD:?SENSEI_MIGRATOR_PASSWORD must be set (production docker-compose and db-contract CI provide it)}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- ── sensei_migrator: migration/admin bootstrap role ────────────────
    -- Runs the full migration chain as the owner of every object it
    -- creates (tables, indexes, SECURITY DEFINER functions). Least
    -- privilege for a DDL role: NOSUPERUSER NOBYPASSRLS CREATEDB
    -- NOCREATEROLE (no RLS bypass — the functions it owns stay below the
    -- FORCE-RLS line; no role administration — probe roles belong to the
    -- DB superuser).
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sensei_migrator') THEN
            CREATE ROLE sensei_migrator LOGIN;
        END IF;
    END
    \$\$;
    -- Idempotent convergence on re-runs: attributes + password are
    -- enforced, never assumed from a previous bootstrap.
    ALTER ROLE sensei_migrator WITH LOGIN PASSWORD '${SENSEI_MIGRATOR_PASSWORD}'
        NOSUPERUSER NOBYPASSRLS CREATEDB NOCREATEROLE;

    -- ── sensei_app: the non-owner application role ─────────────────────
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sensei_app') THEN
            CREATE ROLE sensei_app LOGIN PASSWORD '${SENSEI_APP_PASSWORD}';
        END IF;
    END
    \$\$;
    ALTER ROLE sensei_app WITH LOGIN PASSWORD '${SENSEI_APP_PASSWORD}'
        NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;

    -- ── Schema-ownership split (twenty-fourth audit P0) ────────────────
    -- The chain runs inside "${POSTGRES_DB}": ALL ON the database
    -- (CONNECT + CREATE ON DATABASE for trusted-extension creation) and
    -- CREATE ON SCHEMA public so the chain can DDL. In PostgreSQL >= 15
    -- CREATE on public is already owner-only; the explicit grant keeps
    -- this script the single source on every server version.
    GRANT ALL PRIVILEGES ON DATABASE "${POSTGRES_DB}" TO sensei_migrator;
    GRANT USAGE, CREATE ON SCHEMA public TO sensei_migrator;
    -- No OTHER role may DDL on public: revoke the historical PUBLIC
    -- schema-CREATE (PostgreSQL < 15 default), then hand CREATE back
    -- explicitly — sensei_migrator only (granted above). This is the
    -- audit's "REVOKE CREATE FROM sensei_app entirely": the app role
    -- holds NO direct CREATE grant and inherits none from PUBLIC.
    REVOKE CREATE ON SCHEMA public FROM PUBLIC;
    REVOKE CREATE ON SCHEMA public FROM sensei_app;

    -- ── sensei_app grants (canonical, audited) ─────────────────────────
    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO sensei_app;
    GRANT USAGE ON SCHEMA public TO sensei_app;
    -- Tables the MIGRATION OWNER creates (the production bootstrap order:
    -- this script runs at first boot, the chain runs later as
    -- sensei_migrator) inherit the app role's DML through default
    -- privileges declared FOR ROLE sensei_migrator.
    ALTER DEFAULT PRIVILEGES FOR ROLE sensei_migrator IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sensei_app;
    -- Legacy superuser-created objects (dev bootstraps that ran the chain
    -- before the split): keep the same DML for tables that already exist.
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
