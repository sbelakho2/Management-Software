# AI Programs

Every model program is typed (sensei-agent-orchestrator/programs.rs): input/output
signature, allowed models, tools, risk level, fallback, evaluation suite. Structured
output is ENFORCED natively by `decode_structured` — required fields, correct kinds,
NO extra fields (item 82: compile the output grammar; don't ask politely for JSON).

| program | risk | models | output contract | tools | eval |
|---------|------|--------|-----------------|-------|------|
| corrective_action.investigate | high | glm-5.3, qwen3.5 | fact + status + gap_hypothesis | read_condition, read_events | corrective_action_suite_v1 |
| material_shortage.resolve | medium | functiongemma, ministral | evidence + action | read_inventory, read_purchase_orders | — |

Epistemic status is part of the contract (A10): FACT / INFERENCE / HYPOTHESIS are
distinct; the model must never invent operational facts (item 79).

Promotion of any program change: baseline → candidate → offline evaluation → shadow →
canary → comparison → approval → versioned promotion (item 16 + AI_CHANGE_CONTROL).
