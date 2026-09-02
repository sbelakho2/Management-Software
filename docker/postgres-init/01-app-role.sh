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
# MIGRATION-OWNER SPLIT (twenty-fourth audit P0, revised by the
# twenty-fifth audit P0 — migration privilege model): the migration chain
# is NEVER run by the app role. This script defines the DEPLOYMENT-ONLY
# bootstrap identities:
#
#   sensei_migrator — LOGIN NOSUPERUSER BYPASSRLS NOCREATEDB
#   NOCREATEROLE. The ONLY identity that ever runs the migration chain
#   (sensei-api --migrate-only) and owns every schema object the chain
#   creates (tables, indexes, SECURITY DEFINER functions). It is NEVER a
#   runtime application identity: production connects the API and workers
#   as sensei_app (docker-compose.prod.yml), and nothing outside the
#   bootstrap `migrate` one-shot (or CI's clean-bootstrap gate) connects
#   as sensei_migrator. Attributes:
#     - BYPASSRLS (twenty-fifth audit P0): FORCE ROW LEVEL SECURITY
#       applies to the table OWNER as well, and the migration chain
#       performs cross-tenant backfills and seeds with NO app.tenant_id
#       context — migration 122 seeds country_policies for every tenant
#       from the tenants table, and later migrations seed the FORCE-RLS
#       federation tables — so a NOBYPASSRLS migration identity cannot
#       bootstrap a clean database. BYPASSRLS is safe ONLY because the
#       migrator is deployment-only; the runtime app role (sensei_app)
#       stays NOBYPASSRLS, which is what FORCE RLS enforces for.
#     - NOCREATEDB (twenty-fifth audit P0): the migrator NEVER creates
#       databases — the database is created by the initdb bootstrap
#       superuser (docker-entrypoint's POSTGRES_DB; CI's superuser), so
#       CREATEDB is dropped. ALL ON the database below still covers
#       CONNECT (+ trusted-extension CREATE), and the chain runs against
#       the already-created database.
#     - NOCREATEROLE: probe roles belong to the DB superuser.
#
#   sensei_governance_definer — NOLOGIN NOSUPERUSER BYPASSRLS
#   NOCREATEDB NOCREATEROLE (twenty-fifth audit P0): the NARROWER owner
#   of ONLY the federation-governance functions —
#   federation_governance_edges() and federation_governance_edges_for(uuid).
#   Those SECURITY DEFINER functions read PEER tenants' rows on FORCE-RLS
#   tables (federation_memberships, site_manifests, country_policies,
#   country_policy_versions), so their owner must BYPASSRLS; NOLOGIN
#   means the role is never a connection identity and its privileges
#   exist only inside the SECURITY-DEFINER execution boundary. The
#   MIGRATION CHAIN must set the function OWNER to
#   sensei_governance_definer (ALTER FUNCTION ... OWNER TO
#   sensei_governance_definer, with the SELECT grants the definer body
#   needs) — this script only pre-creates the role; ownership flips in
#   the migration chain, NOT here (no migration files are edited from
#   this script). sensei_migrator is granted membership in
#   sensei_governance_definer below so the non-superuser chain CAN
#   perform that ownership transfer; the runtime app role is never
#   granted membership.
#
# sensei_app is stripped of schema CREATE entirely (REVOKE CREATE ON
# SCHEMA public FROM PUBLIC — the explicit grant back below is the only
# path back in, and it goes to sensei_migrator alone), so a production API
# connecting as sensei_app can never DDL, and the default privileges below
# are declared FOR ROLE sensei_migrator so every table the chain creates
# later inherits the app role's DML grants automatically.
set -e
: "${SENSEI_APP_PASSWORD:?SENSEI_APP_PASSWORD must be set (production docker-compose and db-contract CI provide it)}"
: "${SENSEI_MIGRATOR_PASSWORD:?SENSEI_MIGRATOR_PASSWORD must be set (production docker-compose and db-contract CI provide it)}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- ── sensei_migrator: deployment-only migration/bootstrap role ──────
    -- Runs the full migration chain as the owner of every object it
    -- creates (tables, indexes, SECURITY DEFINER functions). It is NEVER
    -- used by the runtime application — only the bootstrap `migrate`
    -- one-shot and CI's clean-bootstrap gate connect as it. Least
    -- privilege for a DDL role: NOSUPERUSER BYPASSRLS NOCREATEDB
    -- NOCREATEROLE. BYPASSRLS is REQUIRED (twenty-fifth audit P0):
    -- FORCE RLS applies to the table OWNER too, and the chain
    -- seeds/backfills FORCE-RLS tables cross-tenant with no
    -- app.tenant_id context (migration 122 country_policies seed; the
    -- federation tables) — a NOBYPASSRLS migrator cannot bootstrap a
    -- clean database. NOCREATEDB: the bootstrap superuser creates the
    -- database (docker-entrypoint POSTGRES_DB / CI superuser), never the
    -- migrator. NOCREATEROLE: probe roles belong to the DB superuser.
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
        NOSUPERUSER BYPASSRLS NOCREATEDB NOCREATEROLE;

    -- ── sensei_governance_definer: narrower governance owner (25th P0) ─
    -- NOLOGIN NOSUPERUSER BYPASSRLS NOCREATEDB NOCREATEROLE: owns ONLY
    -- the federation-governance functions — federation_governance_edges()
    -- and federation_governance_edges_for(uuid). The SECURITY DEFINER
    -- bodies read PEER tenants' rows on FORCE-RLS tables, so the owner
    -- must BYPASSRLS; NOLOGIN keeps it from ever becoming a connection
    -- identity — its privileges matter only inside the SECURITY-DEFINER
    -- boundary. The MIGRATION CHAIN must ALTER the governance functions'
    -- OWNER to this role (this script pre-creates it here so the chain
    -- can do that; ownership itself is NOT moved by this script). Grants
    -- survive ALTER OWNER, so sensei_app's EXECUTE on the no-argument
    -- form below stays valid after the flip.
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sensei_governance_definer') THEN
            CREATE ROLE sensei_governance_definer NOLOGIN;
        END IF;
    END
    \$\$;
    ALTER ROLE sensei_governance_definer WITH NOLOGIN NOSUPERUSER BYPASSRLS
        NOCREATEDB NOCREATEROLE;
    -- Membership: ALTER FUNCTION ... OWNER TO sensei_governance_definer
    -- (the chain's ownership flip) requires the executing role to be a
    -- member of the NEW owner. sensei_migrator is deployment-only, so
    -- this membership is inert at runtime; sensei_app is never a member.
    GRANT sensei_governance_definer TO sensei_migrator;

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
    -- 156 keeps on the no-argument form. The grant survives the
    -- chain-side ALTER OWNER to sensei_governance_definer. NEVER granted
    -- here (and revoked from PUBLIC by migration 156):
    -- federation_governance_edges_for(uuid).
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
    -- Defensive convergence for the migration/admin-only variant
    -- federation_governance_edges_for(uuid): migration 156 revokes it
    -- from PUBLIC and the app role is never granted it, but when this
    -- script runs against a schema where the function already exists
    -- (CI's post-suite database), enforce BOTH revocations here so the
    -- canonical script stays the single source of the app role's
    -- governance surface. Once the chain flips ownership to
    -- sensei_governance_definer the revocations persist (they are
    -- function-level grants, not ownership).
    DO \$\$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_proc p
                   JOIN pg_namespace n ON n.oid = p.pronamespace
                   WHERE n.nspname = 'public'
                     AND p.proname = 'federation_governance_edges_for'
                     AND p.pronargs = 1) THEN
            EXECUTE 'REVOKE ALL ON FUNCTION public.federation_governance_edges_for(uuid) FROM PUBLIC';
            EXECUTE 'REVOKE ALL ON FUNCTION public.federation_governance_edges_for(uuid) FROM sensei_app';
        ELSE
            RAISE NOTICE 'federation_governance_edges_for(uuid) not present yet — migration 156 revokes it from PUBLIC once the migrations create it, and the app role is never granted it';
        END IF;
    END
    \$\$;
EOSQL
