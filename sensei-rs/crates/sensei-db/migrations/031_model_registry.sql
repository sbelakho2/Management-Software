-- ML model registry.
--
-- Persistent store for the sensei-workers ML registry: one row per model,
-- holding the current status (JSONB), statistical parameters (JSONB) and
-- the baseline histogram used for PSI drift detection.

CREATE TABLE IF NOT EXISTS model_registry (
    model_name         VARCHAR(100) PRIMARY KEY,
    version            VARCHAR(50) NOT NULL DEFAULT '0.0.0',
    status             JSONB NOT NULL DEFAULT '{"Healthy": null}'::jsonb,
    parameters         JSONB,
    baseline_histogram JSONB,
    trained_at         TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
