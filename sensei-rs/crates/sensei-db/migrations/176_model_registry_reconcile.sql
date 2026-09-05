-- Model-registry reconcile for the sensei-workers ML tenant channel
-- (thirtieth-audit item 18, Wave C RLS residual conversion).
--
-- WHY this migration exists
-- -------------------------
-- Migration 002 (the domain-tables era) created model_registry with the
-- FULL platform shape (id, tenant_id, model_type CHECK, status as a
-- constrained VARCHAR(30), accuracy/dataset_size/config columns, UNIQUE
-- (tenant_id, model_name, version)); migration 031's later
-- CREATE TABLE IF NOT EXISTS for the worker-oriented shape is therefore a
-- permanent no-op and the live table NEVER gained the columns the
-- sensei-workers ML registry persists (parameters, baseline_histogram,
-- trained_at) — its INSERT named columns that do not exist, so DB-mode
-- ML persistence failed at runtime regardless of RLS.
--
-- Migration 175 made model_registry fail-closed FORCE RLS with the
-- canonical tenant_isolation policy. The ML worker conversion (this
-- audit) therefore needs TWO things: (a) every statement inside a
-- TenantTx per tenant (no-context raw queries return zero rows under the
-- production sensei_app role), and (b) a row model the worker can
-- actually persist: one row per (tenant_id, model_name) — the 031-era
-- worker columns plus the tenant column the platform shape already
-- carries. THIS migration reconciles the table to that shape.
--
-- What changes
-- ------------
-- 1. Add the worker-persisted columns when missing:
--    parameters JSONB, baseline_histogram JSONB, trained_at TIMESTAMPTZ.
--    (accuracy/dataset_size/config/model_type already exist in the
--    platform shape; on an exotic 031-shaped table they are added too.)
-- 2. status: the worker persists its structured ModelStatus JSON
--    ({Healthy:null}, {Trained:{accuracy,...}}, ...). The platform
--    shape constrains status to five VARCHAR states — that vocabulary
--    cannot carry the worker state, so the column becomes JSONB (check
--    constraints and the scalar default are dropped first, existing
--    values are wrapped as {"<value>": null}-compatible strings via
--    to_jsonb, and the worker default '{"Healthy": null}'::jsonb is
--    set).
-- 3. version: default '0.0.0', NOT NULL enforced (the worker always
--    supplies a version; a NULL/'' legacy value is converged).
-- 4. Uniqueness: the platform shape's UNIQUE (tenant_id, model_name,
--    version) would let per-version rows accumulate while the worker
--    upserts ONE row per (tenant_id, model_name) — drop the
--    three-column constraint and enforce UNIQUE (tenant_id, model_name).
--
-- Guarded + idempotent throughout (re-runs are no-ops), so both the
-- clean chain and re-applied topologies converge. Only public
-- model_registry is touched; no policy/RLS statement changes (migration
-- 175's canonical tenant_isolation policy is untouched and migration 175
-- itself is NOT edited).

-- ── 1. Worker-persisted columns (add when missing) ──────────────────────
ALTER TABLE model_registry
    ADD COLUMN IF NOT EXISTS parameters         JSONB,
    ADD COLUMN IF NOT EXISTS baseline_histogram JSONB,
    ADD COLUMN IF NOT EXISTS trained_at         TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS dataset_size       BIGINT,
    ADD COLUMN IF NOT EXISTS accuracy           DOUBLE PRECISION
        CHECK (accuracy BETWEEN 0 AND 1),
    ADD COLUMN IF NOT EXISTS config             JSONB;

-- The worker's INSERT names model_type; the platform shape already has
-- it (NOT NULL + vocabulary CHECK). A hypothetical 031-shaped table
-- lacks it entirely, so add it there with the same vocabulary; the
-- ADD COLUMN IF NOT EXISTS is a no-op where the column exists.
ALTER TABLE model_registry
    ADD COLUMN IF NOT EXISTS model_type VARCHAR(50) NOT NULL DEFAULT 'prediction'
        CHECK (model_type IN ('anomaly_detection', 'prediction',
                              'classification', 'recommendation'));

-- ── 2. status VARCHAR -> JSONB (guarded on the live type) ───────────────
DO $$
DECLARE
    col_type text;
    con record;
BEGIN
    SELECT data_type INTO col_type
      FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name = 'model_registry'
       AND column_name = 'status';
    IF col_type = 'character varying' THEN
        -- Drop every CHECK constraint that constrains status (the
        -- platform vocabulary) and the scalar default, so the type
        -- change is legal.
        FOR con IN
            SELECT c.conname
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.conrelid
              JOIN pg_namespace n ON n.oid = t.relnamespace
             WHERE n.nspname = 'public'
               AND t.relname = 'model_registry'
               AND c.contype = 'c'
               AND pg_get_constraintdef(c.oid) LIKE '%status%'
        LOOP
            EXECUTE format('ALTER TABLE public.model_registry DROP CONSTRAINT %I', con.conname);
        END LOOP;
        ALTER TABLE public.model_registry ALTER COLUMN status DROP DEFAULT;
        -- Existing platform vocabulary values become JSON strings the
        -- worker's ModelStatus parser ignores gracefully (it falls back
        -- to Healthy on unparseable rows) — no legacy value is lost.
        ALTER TABLE public.model_registry
            ALTER COLUMN status TYPE JSONB USING to_jsonb(status);
        ALTER TABLE public.model_registry
            ALTER COLUMN status SET DEFAULT '{"Healthy": null}'::jsonb;
    END IF;
END
$$;

-- ── 3. version: worker default + NOT NULL convergence ───────────────────
UPDATE model_registry
   SET version = '0.0.0'
 WHERE version IS NULL OR version = '';
ALTER TABLE model_registry ALTER COLUMN version SET DEFAULT '0.0.0';
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'model_registry'
           AND column_name = 'version'
           AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE public.model_registry ALTER COLUMN version SET NOT NULL;
    END IF;
END
$$;

-- ── 4. One row per (tenant_id, model_name) ──────────────────────────────
-- The worker upserts ON CONFLICT (tenant_id, model_name). Drop the
-- platform shape's per-version uniqueness first (it would make the
-- upsert conflict target ambiguous), then enforce the per-tenant
-- single-row model.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'public'
           AND t.relname = 'model_registry'
           AND c.contype = 'u'
           AND pg_get_constraintdef(c.oid) LIKE '%model_name%version%'
    ) THEN
        EXECUTE (
            SELECT format('ALTER TABLE public.model_registry DROP CONSTRAINT %I', c.conname)
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.conrelid
              JOIN pg_namespace n ON n.oid = t.relnamespace
             WHERE n.nspname = 'public'
               AND t.relname = 'model_registry'
               AND c.contype = 'u'
               AND pg_get_constraintdef(c.oid) LIKE '%model_name%version%'
             LIMIT 1
        );
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = 'public'
           AND t.relname = 'model_registry'
           AND c.contype = 'u'
           AND pg_get_constraintdef(c.oid) LIKE '%model_name%'
           AND pg_get_constraintdef(c.oid) NOT LIKE '%version%'
    ) THEN
        ALTER TABLE public.model_registry
            ADD CONSTRAINT model_registry_tenant_model_key UNIQUE (tenant_id, model_name);
    END IF;
END
$$;
