# Architecture Invariants — Starz Forge

These are PASS/FAIL requirements (fifteenth audit items 86/103). Every change to the
repository must preserve them; the CI gates enforce the mechanical ones.

| Law | Requirement | Enforcement |
|-----|-------------|-------------|
| A1 | Every operational object has explicit organizational/site scope | Migration 112 adds site/area/line/cell to work_orders, andons, production_events, work_order_operations, inventory_items, operational_conditions, ctq_characteristics, standard_work_documents. `Scope` in sensei-core is the type. |
| A2 | Authorization is evaluated before retrieval, not after | Tools re-check authorization inside `execute` (sensei-agent-core/tools.rs); the Context Kernel filters by sensitivity ceiling before assembly. |
| A3 | Models never enforce permissions | Authorization is deterministic Rust (`require_permission`, PolicyEngine). The model receives a filtered toolset; it cannot widen it. |
| A4 | Stable knowledge may use CAG; volatile operational truth may not | CAG eligibility is restricted to stable corpora (principles, roles, methodology). Live state (inventory, orders, defects) is always live retrieval/tool calls. |
| A5 | KV/context caches are isolated by authorization/trust domain | Cache keys must include trust domain + access digest; cache salting is mandatory for shared caches. |
| A6 | Identity, role, role-slot and process ownership are separate | role_slots + principal_assignments (migration 114): a departure ends assignments; the slot and its history survive. |
| A7 | Employee departure cannot delete operational knowledge | The departure operation transfers open work, retains role memory, generates a handover view. |
| A8 | AI learning cannot silently change standards/policy/production logic | Standard Work is immutable once controlled; organizational memory promotes only via the deterministic/reviewed ladder. |
| A9 | Every model-generated operational assertion retains provenance | ContextItem carries source, source_revision, observed_at, authority, epistemic status. |
| A10 | Fact, inference, hypothesis and recommendation are distinct | `EpistemicStatus` (RecordedFact/DerivedFact/Inference/Hypothesis) in sensei-agent-orchestrator + sensei-agent-core. |
| A11 | All model workflows are checkpointable and auditable | sensei-workflow: every transition writes a durable checkpoint; workflows resume from `latest_checkpoint`. |
| A12 | Every model tool call is independently authorized | PolicyEngine + tool-level recheck. |
| A13 | All metrics come from a versioned metric registry | metric_definitions (migration 115); `metric_registry::get_metric` rejects unregistered metrics. |
| A14 | Analytics are role/scenario-specific, not universal dashboards | RoleAnalytics: NOW/ABNORMAL/WHY/NEXT/LEARN per role with scope restrictions. |
| A15 | Site operations cannot depend on continuous HQ connectivity | Local-first execution; outbox relay is tenant-scoped and resumes from durable checkpoints. |
| A16 | Site differences are configuration/policy wherever possible | SiteManifest + country policy bundles (P2), never code forks. |
| A17 | New-site onboarding must not require core domain code changes | Declarative site manifest + integration mapping (P2). |
| A18 | Organizational knowledge promotion requires evidence | organizational_memory: observation → repeated (occurrence ≥ 2, deterministic) → proposed → approved (human gate). |
| A19 | Cross-site "best practice" transfer is treated as an experiment | Lesson objects carry context_signature + applicability; local teams verify before adoption. |
| A20 | The retired appellation is prohibited from surface-visible artifacts | Gate test `retired_appellation_is_absent_from_surface_assets` scans UI/e2e/HTML. |
| A21 | The system optimizes value-stream outcomes, not isolated utilization | Flow economics is bottleneck-based; anti-gaming notes in the metric registry. |
| A22 | Safety and quality constraints override throughput optimization | Andon restart authorization; quality/safety containment requirements gate releases. |
| A23 | Models must surface missing/contradictory evidence rather than fill gaps | `has_contradiction` keeps both sides; unmeasured metrics are `Unavailable(reason)`. |
| A24 | Corporate aggregate authority does not imply unrestricted personal-data authority | Analytical visibility is separated from transactional authority; scope restricts every query. |
| A25 | Every critical operation exposes skill-depth and knowledge-concentration risk | Skill coverage: bus_factor, single_point, trainer_count per skill. |
