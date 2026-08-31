# TPS Behavior Mapping — INTERNAL ONLY

Engineering documentation, not user-facing content. Every product behavior maps to a
TPS principle, a failure mode and a metric.

| Feature | Desired behavior | TPS principle | Failure mode | Metric |
|---------|-----------------|---------------|--------------|--------|
| I NEED HELP | expose problem immediately | jidoka | hiding problems | detection→response time |
| Pitch target vs actual | see the gap early | flow/andon | explaining late totals | pitch gap |
| STANDARD UNAVAILABLE | never guess the target | standardization | fabricated targets | — |
| Released standard freeze | exact revision per order | standardization | latest-wins leakage | revision binding |
| Recurrence condition | treat as countermeasure failure | kaizen/PDCA | closing without verifying | recurrence_count |
| Next-process pull | produce what's needed | Just-in-Time | push/overproduction | WIP/lead time |
| Skill coverage | develop people | hitozukuri | single-point dependency | bus_factor |
| Verified → new standard | institutionalize learning | standardization | learning stays in a PDF | standardization rate |

The user should never see this table; they should find that this is how the system works.
