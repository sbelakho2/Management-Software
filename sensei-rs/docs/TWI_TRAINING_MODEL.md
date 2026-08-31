# TWI Training Model

Job Instruction (item 37): prepare → present → try → follow-up. The job breakdown is
structured: action, key points, REASONS (the WHY is essential), hazards, checks.

- `job_standards` (migration 116): standard_id + revision + process + steps JSONB with
  the TWI shape (action/key_points/reasons/hazards/checks).
- `skills` + `skill_qualifications`: level ladder unexposed → learning → supervised →
  independent → trainer, with demonstrated_at, evidence and expiry.
- Promotion is evidence-based (every qualification upsert stamps demonstrated_at).
- Coverage (`skill_coverage`): bus_factor (independent+ non-expired), trainer_count,
  single_point — "Shift 2 is technically staffed but only one person can independently
  run AOI programming" is a DETECTABLE operational vulnerability (A25).
