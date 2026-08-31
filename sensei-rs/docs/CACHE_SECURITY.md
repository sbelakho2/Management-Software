# Cache Security

The context architecture makes caching security-critical (item 96). Mandatory:

- Cache keys include: model fingerprint (architecture/weights/tokenizer/quantization),
  trust domain, policy revision, source revisions, prefix hash, cache salt.
- Cache salting isolates principals — a restricted plant-A context is never reused
  for plant-B (item 23; vLLM's own cache salting precedent).
- Eviction and zeroization must handle restricted classes; timing side channels are
  documented as a review item.
- An authorization snapshot (policy_revision, relationship_revision,
  principal_revision) travels through the whole execution (item 24): retrieval and
  execution can never run under different permission states.
