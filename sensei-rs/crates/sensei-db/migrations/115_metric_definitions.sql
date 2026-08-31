-- Versioned metric registry (fifteenth audit 69/70 + A13): every
-- dashboard/API/AI metric has ONE canonical definition — formula, grain,
-- source, owner, anti-gaming notes and expected user action.
CREATE TABLE IF NOT EXISTS metric_definitions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    metric_id       VARCHAR(100) NOT NULL,   -- e.g. 'otd', 'fpy', 'lead_time'
    version         INT NOT NULL DEFAULT 1,
    name            VARCHAR(200) NOT NULL,
    purpose         TEXT,
    formula         TEXT NOT NULL,
    unit            VARCHAR(30) NOT NULL,
    grain           VARCHAR(30) NOT NULL,    -- site | line | cell | product | supplier | ...
    timezone        VARCHAR(50) NOT NULL DEFAULT 'UTC',
    source          VARCHAR(100) NOT NULL,
    owner_role      VARCHAR(100) NOT NULL,
    audience        JSONB NOT NULL DEFAULT '[]',
    freshness       VARCHAR(30) NOT NULL DEFAULT 'realtime',
    anti_gaming     TEXT,
    expected_action TEXT,
    applicable_sites JSONB NOT NULL DEFAULT '[]',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, metric_id, version)
);
ALTER TABLE metric_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE metric_definitions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON metric_definitions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Seed the canonical core metrics.
INSERT INTO metric_definitions (tenant_id, metric_id, version, name, purpose, formula, unit, grain, source, owner_role, audience, freshness, anti_gaming, expected_action)
SELECT t.id, v.metric_id, 1, v.name, v.purpose, v.formula, v.unit, v.grain, v.source, v.owner_role, v.audience::jsonb, v.freshness, v.anti_gaming, v.expected_action
FROM tenants t,
     (VALUES
        ('otd', 'On-time delivery', 'share of customer deliveries within the promised date', 'delivered_on_time / total_deliveries', '%', 'site', 'sales_orders.delivery_date + goods_receipts', 'production_planner', '["site_manager","production_manager","sales"]', 'daily', 'Do not exclude late orders via status churn; a cancelled-late order is still a miss.', 'Identify the constraint that pushed the delivery late and decide the recovery.'),
        ('fpy', 'First-pass yield', 'share of units passing all checks without rework', 'passed_first_pass / total_units', '%', 'line', 'production_events + quality results', 'quality_engineer', '["site_manager","production_manager","quality"]', 'shift', 'Rework recorded as first-pass inflates the metric; audit the rework ledger.', 'Find the operation where defects are introduced and run the containment loop.'),
        ('lead_time', 'Order lead time', 'elapsed time from order receipt to shipment', 'ship_date - order_date', 'days', 'site', 'sales_orders + shipments', 'production_planner', '["site_manager","production_manager","sales"]', 'daily', 'Backdating the ship date hides the true lead time.', 'Compare against demonstrated capacity and decide the honest promise.'),
        ('scrap_rate', 'Scrap rate', 'share of produced units scrapped', 'scrapped / produced', '%', 'line', 'work_orders.quantity_scrapped', 'quality_engineer', '["production_manager","quality"]', 'shift', 'Scrapping at end-of-line only hides the true introduction point.', 'Trace the scrap to its first introduction operation.'),
        ('help_response', 'Andon help response time', 'time from Andon raise to first acknowledgement', 'avg(acknowledged_at - created_at)', 's', 'cell', 'andons', 'team_lead', '["team_lead","site_manager"]', 'realtime', 'Acknowledging without acting is not a response; track containment separately.', 'Go to the work center where help is waiting.')
     ) AS v(metric_id, name, purpose, formula, unit, grain, source, owner_role, audience, freshness, anti_gaming, expected_action)
WHERE NOT EXISTS (
    SELECT 1 FROM metric_definitions m WHERE m.tenant_id = t.id AND m.metric_id = v.metric_id AND m.version = 1
);
