# Metric Catalog

Every metric has ONE canonical definition in `metric_definitions` (migration 115),
seeded with the core set. `metric_registry::get_metric` rejects unregistered metrics
("no unnamed dashboard SQL", item 69-70 + A13).

| metric_id | unit | grain | source | owner_role | anti-gaming | expected action |
|-----------|------|-------|--------|-----------|-------------|-----------------|
| otd | % | site | sales_orders + goods_receipts | production_planner | cancelled-late is still a miss | find the constraint, decide recovery |
| fpy | % | line | production_events + quality | quality_engineer | rework counted as first-pass inflates | trace defect introduction |
| lead_time | days | site | sales_orders + shipments | production_planner | backdated ship dates hide truth | compare vs demonstrated capacity |
| scrap_rate | % | line | work_orders.quantity_scrapped | quality_engineer | end-of-line scrapping hides introduction | trace to first operation |
| help_response | s | cell | andons | team_lead | acknowledging without acting is not responding | go to the waiting work center |

Every definition carries: name, purpose, formula, unit, time boundary, timezone,
grain, source, owner, version, applicable sites, aggregation rule, anti-gaming risk,
expected user action.
