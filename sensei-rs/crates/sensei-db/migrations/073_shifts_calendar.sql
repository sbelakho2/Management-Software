-- Shifts and operating calendar: takt and capacity must never be inferred
-- from a generic 24-hour day — available time is scheduled time minus
-- breaks and planned downtime.
CREATE TABLE IF NOT EXISTS shifts (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_id       UUID,
    name          VARCHAR(100) NOT NULL,
    start_time    TIME NOT NULL,
    end_time      TIME NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS production_calendar (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_id                  UUID,
    calendar_date            DATE NOT NULL,
    shift_id                 UUID REFERENCES shifts(id) ON DELETE CASCADE,
    scheduled_seconds        BIGINT NOT NULL DEFAULT 0,
    breaks_seconds           BIGINT NOT NULL DEFAULT 0,
    planned_downtime_seconds BIGINT NOT NULL DEFAULT 0,
    is_holiday               BOOLEAN NOT NULL DEFAULT FALSE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, site_id, calendar_date, shift_id)
);
CREATE INDEX IF NOT EXISTS idx_calendar_tenant_date
    ON production_calendar (tenant_id, calendar_date);
