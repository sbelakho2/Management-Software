# Model Evaluation

Every model/program change is benchmarked against MANUFACTURING cases (item 95), not
generic scores. Categories: hallucination, wrong source, missed contradiction, bad
root cause, premature root cause, unsafe recommendation, over/under-escalation,
incorrect tool call, authorization probe, cross-site leakage, stale-data use.

Evaluation corpora are referenced from `ModelProgram.evaluation_suite`; promotion
follows baseline → candidate → offline eval → shadow → canary → comparison →
approval (item 16).
