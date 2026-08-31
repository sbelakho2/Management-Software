# Context Architecture

## Context Kernel (sensei-agent-core/context.rs + context_kernel.rs)

Every AI operation goes through the Context Kernel. There is no "search query string"
in the request — the system knows the principal, role, site, work center, task, focal
objects, token budget, sensitivity ceiling and trace id.

```
ContextRequest
   ↓
plan_context(req)          ← DETERMINISTIC: task decides required sections
   ↓
ContextBundle              ← items selected under max_tokens
   (plan, sections, total_tokens, contradictions)
```

## Context tiers assembled (item 8)

A. Immutable governing context — B. authority/scope — C. role operating context —
D. current work — E. exact process knowledge — F. episodic history — G. live facts —
H. causal neighborhood — I. lessons/standards — J. available tools.

Budget allocation is per-task (budget_allocation), e.g. Troubleshoot gives 20% to
episodic history; ExecutiveAnalysis gives 25% to aggregation.

## Authority ordering (item 76)

ApprovedStandard > ReleasedEngineeringRecord > TransactionalState >
ApprovedCorrectiveAction > VerifiedObservation > EmployeeNote > AiInference.
An AI summary never outranks the source it summarized.

## Contradiction survival (item 77)

`has_contradiction` detects conflicting items on a fact key; `build_context_bundle`
force-includes one item per distinct value of a contradicted key even past the budget.

## CAG tiers (items 3-5)

- L0 serialized context cache (canonical prompt sections)
- L1 retrieval cache (query shape → source ids)
- L2 assembled-bundle cache (exact scope + revisions)
- L3 model KV/prefix cache — isolated per `ModelFingerprint` + trust domain + cache
  salt (mandatory for multi-tenant safety, item 23).

CAG-eligible: principles, reasoning rules, role descriptions, methodology, stable
capability packs. NEVER CAG-only: live production, inventory, orders, defects,
machine condition, suppliers, NCR status, drawings, prices, commitments.

## Freshness rules (item 57)

Freshness by authority class: canonical principle → effective window; standard work →
revision effective date; production fact → observed_at; not the embedding index time.
