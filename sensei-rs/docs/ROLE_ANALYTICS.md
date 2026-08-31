# Role Analytics

Every role gets NOW / ABNORMAL / WHY / NEXT / LEARN (item 48) — what needs my
attention, why, and what to do about it. `role_analytics::build_role_analytics`
restricts every query by the caller's site/work center; per-person comparison
metrics are forbidden (item 49-50: never rank operators; the system optimizes
value-stream outcomes, not isolated utilization — A21).

- operator/team_lead: work-center pitch gaps, active andons, material conditions,
  skill coverage, last abnormality; NEXT is deterministic ("respond to andon X",
  "observe the material queue at <wc>").
- manager/site_manager/quality/planner: site aggregates (flow, WIP, scrap, andon
  response) with target/actual/delta/first divergence.
- LEARN surfaces recurring conditions (recurrence ≥ 2): "observe the work; the
  standard may not fit."
