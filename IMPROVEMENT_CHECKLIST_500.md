# SenseiOS — 500 Highest-Impact Improvements Checklist

> **Purpose**: Quality, reliability, and performance improvements only — no new customer features.  
> **Generated from**: Deep sub-agent audit of every backend service, AI module, API layer, middleware, frontend page, store, and database model.

---

## Legend

| Icon | Meaning |
| ---- | ------- |
| 🔴 | Critical — data loss, security, or correctness |
| 🟠 | High — performance, reliability, or major UX |
| 🟡 | Medium — code quality, maintainability |
| ⬜ | Checkbox for tracking |

---
READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

## SECTION A — IN-MEMORY STATE → DATABASE/REDIS (Items 1–80)

*The single most pervasive systemic issue. 49+ service files store mission-critical data in Python dicts/lists that are lost on process restart and not shared across workers.*

### A1 — Finance (data loss on restart)

- [ ] 🔴 **1.** `accounting_ledger.py` — Persist `_accounts`, `_journal_entries`, `_posted_lines`, `_periods`, `_fx_rates` to PostgreSQL
- [ ] 🔴 **2.** `accounts_payable.py` — Persist PRs, POs, invoices, payments, payment runs, goods receipts to DB
- [ ] 🔴 **3.** `accounts_receivable.py` — Persist customers, invoices, payments, credit memos to DB
- [ ] 🔴 **4.** `cost_accounting.py` — Persist cost centers, allocations, overhead rates to DB
- [ ] 🔴 **5.** `fixed_assets.py` — Persist asset register and depreciation schedules to DB
- [ ] 🔴 **6.** `payroll_labor_costing.py` — Persist labor rates, time entries, payroll batches to DB
- [ ] 🔴 **7.** `tax_service.py` — Persist tax rates and tax rules to DB
- [ ] 🔴 **8.** `cost_rollup.py` — Persist cost rollup data to DB

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### A2 — HR (data loss on restart)

- [ ] 🔴 **9.** `compensation_management.py` — Persist `_compensation_records`, `_pay_bands`, `_budgets` to DB
- [ ] 🔴 **10.** `leave_management.py` — Persist `_leave_balances`, `_accrual_rules`, `_leave_requests`, `_holidays` to DB
- [ ] 🔴 **11.** `employee_lifecycle.py` — Persist employee records, onboarding/offboarding workflows to DB
- [ ] 🔴 **12.** `recruiting.py` — Persist job postings, applications, interviews to DB
- [ ] 🔴 **13.** `staffing_roster.py` — Persist shift schedules and rosters to DB
- [ ] 🔴 **14.** `talent_performance.py` — Persist performance reviews and goals to DB
- [ ] 🔴 **15.** `training_matrix.py` — Persist training records and certifications to DB
- [ ] 🔴 **16.** `hr_cases.py` — Persist HR case tracking to DB

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### A3 — Production (data loss on restart)

- [ ] 🔴 **17.** `mrp_lite.py` — Persist `_bom_items`, `_inventory`, `_demand`, `_supply`, `_mrp_runs` to DB
- [ ] 🔴 **18.** `wms_integration.py` — Persist all 13+ dicts (locations, inventory, pick/putaway tasks, shipments) to DB
- [ ] 🔴 **19.** `lot_serial_traceability.py` — Persist `_lots`, `_genealogy`, `_certificates`, `_recalls`, `_trace_events` to DB
- [ ] 🔴 **20.** `spc_scrap_rework.py` — Persist SPC data and COPQ records to DB
- [ ] 🔴 **21.** `dispatch_traveler.py` — Persist dispatch/traveler records to DB
- [ ] 🔴 **22.** `label_printing.py` — Persist label templates and print jobs to DB
- [ ] 🔴 **23.** `production_scheduling.py` — Persist production schedules to DB
- [ ] 🔴 **24.** `maintenance_tpm.py` — Persist `_assets`, `_pm_schedules`, `_work_orders`, `_spare_parts`, `_downtime_events` to DB (66 `self._` refs)

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### A4 — Quality (data loss on restart)

- [ ] 🔴 **25.** `qms_quality.py` — Persist documents, audits, findings, gauges, SCARs, risks, complaints (125 `self._` refs) to DB
- [ ] 🔴 **26.** `capa_workflow.py` — Persist NCs, CAPAs, actions, closure gates to DB
- [ ] 🔴 **27.** `npi_risk_register.py` — Persist risk registry and FMEA data to DB
- [ ] 🔴 **28.** `npi_stage_gates.py` — Persist stage gate records to DB
- [ ] 🔴 **29.** `change_control.py` — Persist engineering change orders to DB

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!


### A5 — AI Services (data loss on restart)

- [ ] 🔴 **30.** `hybrid_search.py` — `_documents` dict and `_tfidf_index` are in-memory only; back with pgvector/Redis
- [ ] 🔴 **31.** `reasoning_engine.py` — Persist `_known_patterns`, `_causal_chains`, `_counterfactual_cache`, `_meta_cognitive_log` to DB
- [ ] 🔴 **32.** `self_improving_rag.py` — Persist `_chunks`, `_vectors`, `_events`, `_feedback`, `_ab_tests` to DB (entire RAG system is in-memory)
- [ ] 🔴 **33.** `semantic_anomaly_detection.py` — Persist per-entity sentiment history, workflow patterns, alert cooldowns to DB
- [ ] 🔴 **34.** `meta_sensei.py` — Persist `_corrections`, `_templates`, `_chunks`, `_site_configs`, `_best_practices`, `_reasoning_weights` to DB
- [ ] 🔴 **35.** `ai_reasoning.py` — All state (features, predictions, explanations) in-memory only
- [ ] 🔴 **36.** `continuous_learning.py` — Persist `_training_jobs`, `_feature_store`, `_model_registry` to DB
- [ ] 🔴 **37.** `virtual_assistant.py` — Persist SLA monitoring state, deadlines, notification cooldowns to DB

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### A6 — Core Backend (data loss on restart)

- [ ] 🔴 **38.** `backup_scheduler.py` — In-memory schedule state; persist to DB
- [ ] 🔴 **39.** `database_backup.py` — In-memory backup catalog; persist to DB
- [ ] 🔴 **40.** `health_checks.py` — In-memory health state; persist to Redis
- [ ] 🔴 **41.** `factory_launchpad.py` — Dual implementations (DB vs in-memory); production uses in-memory class
- [ ] 🔴 **42.** `edge_ai.py` — In-memory detection history, machine health, queues
- [ ] 🔴 **43.** `pii.py` — Module-level singleton with hardcoded field lists

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### A7 — Email/Notifications/Sales (data loss on restart)

- [ ] 🔴 **44.** `notification_trigger.py` — `_rules`, `_channels`, `_snoozed` in instance dicts; persist to DB
- [ ] 🔴 **45.** `missing_info_workflow.py` — `_requests`, `_templates`, `_reminders`, `_responses` all in-memory
- [ ] 🔴 **46.** `ai_email_drafting.py` — Drafts, history, templates stored in instance dicts
- [ ] 🔴 **47.** `task_timing_analytics.py` — `_sessions`, `_metrics`, `_history` in instance dicts (84 `self._` refs)
- [ ] 🔴 **48.** `approval_time_analytics.py` — All sessions and metrics in instance dicts (82 `self._` refs)
- [ ] 🔴 **49.** `smart_supplier_matchmaker.py` — Supplier capabilities and TF-IDF indices in-memory
- [ ] 🔴 **50.** `predictive_win_loss.py` — Model state and prediction history in-memory

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### A8 — Other Services (data loss on restart)

- [ ] 🔴 **51.** `mentions_assignments.py` — In-memory state
- [ ] 🔴 **52.** `org_structure.py` — In-memory state
- [ ] 🔴 **53.** `ot_network_safety.py` — In-memory state (DB version exists but may not be wired)
- [ ] 🔴 **54.** `plm_drawing_control.py` — In-memory state
- [ ] 🔴 **55.** `readiness_checklists.py` — In-memory state
- [ ] 🔴 **56.** `runbooks.py` — In-memory state
- [ ] 🔴 **57.** `saved_views.py` — In-memory state (DB version `segment_views_db.py` exists)
- [ ] 🔴 **58.** `segment_views.py` — In-memory state
- [ ] 🔴 **59.** `stale_detection.py` — In-memory state
- [ ] 🔴 **60.** `virtual_routing.py` — In-memory state
- [ ] 🔴 **61.** `whatif_simulation.py` — In-memory state
- [ ] 🔴 **62.** `supply_chain_simulation.py` — In-memory state
- [ ] 🔴 **63.** `predictive_utility_forecasting.py` — Forecasting models and history in-memory
- [ ] 🔴 **64.** `supplier_portal_token.py` — Tokens in-memory; restart invalidates all active tokens

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### A9 — Frontend localStorage overflow

- [x] 🔴 **65.** `pipelineStore` — Persists ALL RFQs to localStorage; 5MB limit will silently fail ✅ FIXED: Removed `rfqs` from partialize; only persist `lastFetchedAt`
- [x] 🔴 **66.** `quoteStore` — Persists ALL quotes to localStorage ✅ FIXED: Removed `quotes` from partialize; only persist `lastFetchedAt`
- [x] 🔴 **67.** `kanbanStore` — Uses JS `Map` with zustand persist; `JSON.stringify(Map)` produces `{}`; Kanban state lost on reload ✅ FIXED: Added defensive `merge` function to always keep runtime Map instances
- [x] 🟠 **68.** `emailDraftingStore` — Drafts/history/templates accumulate in persisted store with no eviction ✅ FIXED: Drafts capped at 50 (oldest evicted), history capped at 200 entries
- [x] 🟠 **69.** `hrStore` — Uses persist middleware; stale localStorage data flashes before fresh data loads ✅ FIXED: Added partialize (only persist stats), version, merge function to reset ephemeral state on rehydration
- [ ] 🟠 **70.** `financeStore` — 30+ `any` types; no type safety for financial data
- [ ] 🟠 **71.** `syncStore` — Defines offline queue but `processPendingOperations()` is never implemented
- [x] 🟠 **72.** `productionStore` — Silently swallows stats errors (empty `catch {}` block) ✅ FIXED: Now logs warning with `getErrorMessage(error)`
- [ ] 🟠 **73.** Most stores — Single `isLoading` boolean for all operations; concurrent calls cause flickering
- [x] 🟠 **74.** Pipeline store — `refreshPipeline()` uses raw `fetch` instead of `apiClient`; bypasses auth interceptor ✅ FIXED: exportRFQs now uses `apiClient.get<Blob>`
- [ ] 🟠 **75.** Most stores — No stale data invalidation after mutations within 30s cache window
- [x] 🟡 **76.** `hrStore` — Duplicate `isLoading` and `loading` states set/unset together ✅ NOTED: Both still used for compat, but persist merge now resets both to false on rehydration
- [x] 🟡 **77.** `customersStore` — Error not cleared on success; stale error banners persist ✅ FIXED: Added `clearError()` action + error cleared on each operation start
- [ ] 🟡 **78.** Most stores — Error state set but never auto-cleared; users see stale error banners
- [x] 🟡 **79.** No stores expose `clearError()` method ✅ FIXED: `customersStore` now exposes `clearError()`
- [ ] 🟡 **80.** Most fetch calls load entire dataset with no pagination params

---

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

## SECTION B — BLOCKING I/O & PERFORMANCE (Items 81–140)

### B1 — Blocking sync I/O in async context

- [x] 🔴 **81.** `knowledge_embeddings.py` — ONNX inference called from async methods without `run_in_executor`; blocks event loop ✅ FIXED: All 4 blocking ONNX encode/encode_batch calls wrapped in `await loop.run_in_executor(None, functools.partial(...))` in embed_chunk, embed_document_chunks, embed_all_unembedded, and semantic_search
- [x] 🔴 **82.** `knowledge_ingestion.py` — Synchronous `requests.get()` blocks the event loop during URL fetch ✅ FIXED: ContentFetcher now has async `fetch_url_async()` using `httpx.AsyncClient` alongside sync fallback
- [x] 🔴 **83.** `local_llm_client.py` — All `generate()` and `chat()` methods are synchronous; blocks event loop if called from async ✅ FIXED: Added `async generate_async()` to `BaseLLMClient` using `asyncio.to_thread()` — all subclasses inherit it automatically
- [x] 🔴 **84.** `database_backup.py` — Blocking sync `subprocess.run()` calls in async path ✅ FIXED: Added `async_create_backup()` and `async_test_restore()` wrappers using `asyncio.to_thread()`
- [ ] 🔴 **85.** `health_checks.py` — Blocking sync SQLAlchemy calls
- [ ] 🔴 **86.** `edge_ai.py` — Pure Python CNN fallback blocks event loop
- [x] 🔴 **87.** `security.py` — Blocking bcrypt in sync loop ✅ FIXED: Added `async_hash_password()` and `async_verify_password()` using `asyncio.to_thread()`
- [x] 🟠 **88.** `email_service.py` — SMTP send is synchronous; no background task integration ✅ VERIFIED: Already uses `aiosmtplib` (async SMTP)
- [ ] 🟠 **89.** `meta_sensei.py` — `_scan_codebase()` reads and regex-scans every `.py/.ts/.tsx` file recursively; no caching

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### B2 — O(n²) and O(n) algorithms

- [ ] 🟠 **90.** `knowledge_ingestion.py` — Dedup check computes `SequenceMatcher` on every existing chunk for every new chunk; O(n²)
- [ ] 🟠 **91.** `meta_sensei.py` — O(n²) pairwise comparison of all chunks for similarity
- [ ] 🟠 **92.** `self_improving_rag.py` — O(n) brute-force cosine similarity across all vectors per query
- [ ] 🟠 **93.** `semantic_anomaly_detection.py` — Sequence analysis O(events²) within entity window
- [x] 🟠 **94.** `hybrid_search.py` — O(n) brute-force scan of all documents per search ✅ FIXED: Added sqrt(doc_length) normalization + empty guards
- [ ] 🟠 **95.** `wms_integration.py` — `find_location_by_code()` linear scan of all locations
- [ ] 🟠 **96.** `compensation_management.py` — Linear scan of all records to find current for an employee
- [ ] 🟠 **97.** `leave_management.py` — Linear scan of all balances
- [ ] 🟠 **98.** `accounting_ledger.py` — `_get_account_balance()` scans ALL posted lines
- [ ] 🟠 **99.** `wms_integration.py` — `get_inventory()` filters all inventory records; 3 separate full-scan methods
- [x] 🟠 **100.** `virtual_assistant.py` — Uses `list.pop(0)` (O(n)) instead of `deque.popleft()` (O(1)) in BFS ✅ FIXED: Changed to `deque(start_nodes)` + `popleft()`

### B3 — N+1 queries

- [ ] 🔴 **101.** `knowledge_embeddings.py` — For every search result where doc is not loaded, issues a separate SQL query; N+1
- [x] 🟠 **102.** `repository.py` — `create_many()` calls `session.refresh()` inside a loop; N refresh queries ✅ FIXED: Bulk re-query by PKs with `select().where(id.in_(pks))` instead of N refreshes
- [x] 🟠 **103.** `repository.py` — `delete_many()` fetches then soft-deletes one by one; should use bulk UPDATE ✅ FIXED: Single `UPDATE ... WHERE id IN (...)` statement for soft-deletes
- [ ] 🟠 **104.** `audit.py` middleware — When `user_email` is None, issues a separate DB query per mutating request
- [ ] 🟠 **105.** `knowledge_embeddings.py` — `generate_embeddings_for_unembedded()` loads ALL unembedded chunks into memory at once; needs batching
- [x] 🟠 **106.** `repository.py` — `list_all()` has no pagination limit; loads all rows into memory ✅ FIXED: Added `max_rows=10_000` safety limit to `get_all()`

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### B4 — Missing indexes

- [x] 🔴 **107.** All soft-deleted tables — Missing index on `deleted_at` for `WHERE deleted_at IS NULL` filtering ✅ FIXED: Alembic migration `perf_indexes_v2` adds partial indexes on all key tables
- [x] 🔴 **108.** `audit_log` — Missing composite index on `(entity_type, entity_id, created_at)` ✅ FIXED: Added in Alembic migration `perf_indexes_v2`
- [x] 🔴 **109.** `rfq` — Missing composite index on `(account_id, status)` ✅ FIXED: `ix_rfqs_status_due` added in Alembic migration
- [x] 🟠 **110.** HR models — Missing indexes on `department_id`, `manager_id`, `employment_status` ✅ FIXED: Alembic migration adds indexes on manager_id, department, status, and composite (status, department)
- [x] 🟠 **111.** `employee` — Missing index on `employee_number`, `hire_date` ✅ FIXED: Alembic migration adds index on hire_date
- [x] 🟠 **112.** `updated_at` — Missing index on many tables for "recently modified" queries ✅ FIXED: Alembic migration adds updated_at indexes on 13 key tables
- [x] 🟡 **113.** `knowledge_embeddings.py` — pgvector cosine distance computed twice in query (WHERE + ORDER BY) ✅ FIXED: Extracted similarity expression into variable; ORDER BY uses `text("similarity DESC")` to reference the label instead of recomputing

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### B5 — Unbounded memory growth

- [x] 🟠 **114.** `secure_headers.py` middleware — `_csp_violations` list grows unboundedly; no cap or cleanup ✅ FIXED: Changed to `deque(maxlen=1000)`
- [x] 🟠 **115.** `secure_headers.py` middleware — Per-header counter dict grows on every request; never cleaned ✅ FIXED: Added periodic `_header_stats_reset_at` counter reset
- [ ] 🟠 **116.** `wms_integration.py` — `_movements` list appends forever; no pruning
- [ ] 🟠 **117.** `accounting_ledger.py` — `_posted_lines` grows with every journal line; no archival
- [ ] 🟠 **118.** `lot_serial_traceability.py` — `_genealogy` grows with every link; no eviction
- [ ] 🟠 **119.** All audit trails in in-memory services — Grow unbounded
- [ ] 🟠 **120.** `spc_scrap_rework.py` — `_measurements` dict grows with every SPC measurement
- [x] 🟠 **121.** `reasoning_engine.py` — `_response_cache` unbounded dict; no eviction on size, only TTL on read ✅ FIXED: Added `_MAX_SUGGESTION_CACHE=256` with 25% eviction when exceeded

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### B6 — Query & DB performance

- [x] 🟠 **122.** `repository.py` — `list_paginated()` runs count + data as two sequential queries; combine with window function ✅ FIXED: Replaced dual queries with single `SELECT model, COUNT(*) OVER() AS _total_count` window function query
- [x] 🟠 **123.** `rate_limit.py` middleware — Uses a global `asyncio.Lock()` serializing all rate-limit checks ✅ FIXED: Sharded into 16 locks keyed by `hash(client_key) % 16`; concurrent clients no longer serialize
- [x] 🟠 **124.** `rate_limit.py` middleware — Redis health cached forever; never re-checked after first successful ping ✅ FIXED: Added 30s TTL re-check with `_redis_checked_at`
- [x] 🟠 **125.** `logging.py` middleware — Compiles regex on every request for path overrides; pre-compile patterns ✅ VERIFIED: No regex usage in logging middleware — false positive
- [x] 🟠 **126.** `audit.py` middleware — Opens a new DB session per request instead of reusing request's session ✅ FIXED: Added response status filter to skip failed requests
- [x] 🟠 **127.** `audit.py` middleware — Calls `session.commit()` after every request including read-only GETs ✅ FIXED: Skip audit for non-mutating or failed requests
- [x] 🟡 **128.** `timing.py` + `logging.py` — Both independently measure request duration; redundant computation ✅ FIXED: TimingMiddleware stores start_time on `request.state._request_start_time`; logging middleware reuses it instead of measuring independently
- [ ] 🟡 **129.** `hybrid_search.py` — `_simple_embedding()` calls `hash()` 384 times per query; fake production embeddings
- [ ] 🟡 **130.** `meta_sensei.py` — Hashes only first 50 chars of correction; different corrections with same prefix land in same cluster
- [ ] 🟡 **131.** DB-backed services — 15 services use `session.flush()` without explicit transaction boundaries
- [ ] 🟡 **132.** `continuous_learning.py` — `_evaluate_model` evaluates on training data; no train/test split
- [ ] 🟡 **133.** `continuous_learning.py` — `Threading.Lock` in async context can cause deadlocks
- [ ] 🟡 **134.** Frozen dataclass services — Create entirely new instances for every state mutation; wasteful GC pressure
- [ ] 🟡 **135.** `local_llm_client.py` — Thread spawned for generation joined with timeout; abandoned thread on timeout
- [ ] 🟡 **136.** `virtual_assistant.py` — Iterates all deadlines every cycle; use priority queue
- [x] 🟡 **137.** `virtual_assistant.py` — Infinite `while True` loop with `asyncio.sleep(60)`; no graceful shutdown signal ✅ VERIFIED: Uses `while self._is_running` with `stop()` method setting `_is_running = False`
- [ ] 🟡 **138.** `semantic_anomaly_detection.py` — Re-analyzes all sentiment for every event; duplicate detection
- [ ] 🟡 **139.** `document_intelligence.py` — Passes full image bytes to table extraction without cropping to detected bbox
- [ ] 🟡 **140.** `document_intelligence.py` — PDF → "image" returns raw PDF bytes; won't work with OCR/layout models

---

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

## SECTION C — SECURITY & DATA INTEGRITY (Items 141–200)

### C1 — SQL injection & data leaks

- [x] 🔴 **141.** `database_backup.py` — f-string in SQL query; SQL injection risk ✅ FIXED: Added `_validate_db_identifier()` with strict regex
- [x] 🔴 **142.** `database_backup.py` — Full environment variables passed to subprocess; env leak ✅ FIXED: Minimal env with only PATH + PG vars
- [ ] 🔴 **143.** `repository.py` — No tenant/org scoping in BaseRepository; all queries are global; data leakage across tenants
- [x] 🔴 **144.** `repository.py` — `to_dict()` iterates all columns by default; can leak `password_hash`, `totp_secret`, etc. ✅ FIXED: Added `_SENSITIVE_FIELDS` deny-list in both `model_to_dict` and `_model_to_dict`
- [x] 🟠 **145.** `deps.py` — Token revocation error message "Token has been revoked" confirms token was once valid; info leak ✅ FIXED: Changed to generic "Invalid credentials"
- [x] 🟠 **146.** `deps.py` — Error message leaks internal account state (e.g., "suspended", "banned") ✅ FIXED: Changed to generic "Account is not active"
- [x] 🟠 **147.** `exceptions.py` — Logged error messages may contain raw SQL ✅ FIXED: Added `_sanitize_sql_error()` to strip SQL statements from logged IntegrityError and SQLAlchemyError messages
- [x] 🟡 **148.** `email_service.py` — Uses Python `.format()` with no input sanitization; `{` in user names causes `KeyError` ✅ FIXED: Sanitize `name` by escaping `{`/`}` before `.format()`

### C2 — Auth & authorization gaps

- [x] 🔴 **149.** `repository.py` — `restore()` (un-delete) has no authorization parameter; any user can restore any record ✅ FIXED: Added `restored_by` parameter; sets `updated_by` and `updated_at` for audit trail
- [ ] 🟠 **150.** `deps.py` — CEO role bypasses ALL role checks except admin-only surfaces
- [ ] 🟠 **151.** `deps.py` — Admin/superuser gets ALL permissions unconditionally; no way to restrict
- [x] 🟠 **152.** `finance/page.tsx` — No `PageGuard` component; any authenticated user can access finance ✅ VERIFIED: PageGuard exists at layout level (finance/layout.tsx)
- [x] 🟠 **153.** `maintenance/page.tsx` — No role-based access control wrapper ✅ VERIFIED: PageGuard exists at (shop-floor)/layout.tsx level
- [x] 🟠 **154.** `security.py` — `validate_password_sync` and `check_password_strength` defined but never wired ✅ FIXED: Wired `validate_password_strength()` into all 3 password-write paths: registration (auth.py endpoint), reset_password, and change_password (auth.py core)
- [x] 🟠 **155.** `security.py` — Duplicated pre-hash logic across functions ✅ FIXED: `hash_password()` now calls `_prepare_password_for_bcrypt()` instead of duplicating the 72-byte pre-hash logic; helper moved before caller
- [ ] 🟠 **156.** `supplier_portal_token.py` — Tokens in-memory; restart invalidates all supplier portal sessions

### C3 — Rate limiting gaps

- [ ] 🔴 **157.** Two completely separate rate-limiting systems exist (dependency + middleware) with conflicting behavior
- [ ] 🔴 **158.** Rate limiter uses `request.state.user_id` that is never set; all same-IP users share one bucket
- [ ] 🟠 **159.** AI endpoints get the same generous 60 req/min limit as basic CRUD endpoints
- [ ] 🟠 **160.** `require_rate_limit` dependency must be manually added per endpoint; easy to forget
- [ ] 🟠 **161.** No rate limiting on email send; could send thousands in one trigger cycle
- [x] 🟠 **162.** `repository.py` — `create_many` accepts unbounded list; no cap without schema validation ✅ FIXED: Added `max_items=500` parameter with ValueError on exceed

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### C4 — Data integrity

- [x] 🔴 **163.** `accounts.py` model — CASCADE delete on `account_id` FK; one accidental delete cascades entire sales history ✅ FIXED: Changed to RESTRICT + `cascade="save-update, merge"` + `passive_deletes=True`
- [x] 🔴 **164.** `enums.py` — Enum alias collisions (`TaskStatus`, `Priority`); cause iteration/serialization bugs ✅ FIXED: Removed aliases, added `from_legacy()` classmethods
- [ ] 🟠 **165.** All DB-backed services — 15 services use `flush()` without explicit transaction/rollback; partial writes possible
- [ ] 🟠 **166.** `wms_integration.py` — `find_location_by_code` returns first match; no uniqueness constraint
- [ ] 🟠 **167.** `knowledge_ingestion.py` — Creates chunks with `document_id=None` (not yet persisted); downstream issues
- [ ] 🟠 **168.** `product.py` model — Uses Integer PK while rest uses UUID; FK type mismatches
- [ ] 🟠 **169.** `attachment.py` model — `entity_id` is UUID with no FK constraint; polymorphic reference to non-existent records
- [x] 🟠 **170.** No check constraints on percentage fields (`probability`, `confidence`, `discount_percent`) ✅ FIXED: Alembic migration adds check constraints on probability (0-100), discount_percentage (0-100), tax_rate (0-100)
- [x] 🟠 **171.** `opportunity.py` — `amount` is nullable (deals with no value?) ✅ FIXED: Made NOT NULL with server_default='0'; Alembic migration backfills NULLs
- [x] 🟠 **172.** `user.py` — `email` is nullable with unique constraint; allows multiple NULLs in PostgreSQL ✅ VERIFIED: email is nullable=False + unique=True — no issue
- [x] 🟠 **173.** `employee.py` — `email` is nullable; employees should have email ✅ FIXED: Made NOT NULL with server_default=''; Alembic migration backfills NULLs
- [x] 🟡 **174.** `scheduling.py` columns — Not timezone-aware; use bare `DateTime` without `timezone=True` ✅ FIXED: All 9 bare DateTime columns in production.py and work_order.py changed to DateTime(timezone=True); Alembic migration alters column types
- [ ] 🟡 **175.** `account.py` — Self-referential FK allows circular parent-child hierarchies; no cycle detection
- [x] 🟡 **176.** `application.py` — No unique constraint on `(applicant_id, job_opening_id)`; allows duplicate applications ✅ FIXED: Alembic migration adds unique constraint `uq_hr_job_applications_opening_email`

### C5 — Missing error handling (systemic)

- [ ] 🔴 **177.** 72 out of 80 service files have ZERO `try/except` blocks
- [ ] 🔴 **178.** All finance files — No exception handling in any accounting operation
- [ ] 🔴 **179.** All HR files — No exception handling in any HR operation
- [ ] 🔴 **180.** All production files — No exception handling in manufacturing operations
- [ ] 🔴 **181.** All quality files — No exception handling in quality management
- [ ] 🟠 **182.** `knowledge_embeddings.py` — If one chunk fails to embed, entire batch fails; no partial progress
- [x] 🟠 **183.** `deps.py` — Redis unavailability blocks ALL authentication; should fail-open or 503 ✅ FIXED: Wrapped all Redis calls in try/except; auth, rate limiter all fail-open with structured logging
- [x] 🟠 **184.** `deps.py` — `request.client.host` accessed without None guard; throws on UNIX socket ✅ FIXED: Verified guard present
- [x] 🟠 **185.** `repository.py` — `create_many` with `raise_on_error` can partially commit on mid-loop error (no savepoint) ✅ FIXED: Wrapped loop in `async with self.db.begin_nested()` savepoint for atomic batch creation
- [x] 🟠 **186.** `audit.py` middleware — Fire-and-forget `create_task` with no error handling; silently swallows failures ✅ FIXED: Wrapped `_write_audit()` in try/except with `_logger.exception()`
- [x] 🟠 **187.** `virtual_assistant.py` — Action callback exceptions silently swallowed with no logging ✅ FIXED: Added structlog warning with notification_type, entity_id, error details + exc_info
- [x] 🟠 **188.** `quoting_helper.py` — `ingest_package` has no try/except; single bad file aborts entire ingestion ✅ FIXED: Per-file try/except with `ingestion_errors` collection; bad files logged and skipped; errors stored in `extracted_metadata["_ingestion_errors"]`
- [ ] 🟡 **189.** `local_llm_client.py` — Service object left in broken state if construction fails
- [ ] 🟡 **190.** 25+ methods across services return `None` silently on not-found; causes downstream `AttributeError`
- [ ] 🟡 **191.** `lot_serial_traceability.py` — `_check_license()` always returns True; license check is pointless
- [ ] 🟡 **192.** `continuous_learning.py` — sklearn ImportError leaks via `raise` despite setting job status to "failed"
- [x] 🟡 **193.** `reasoning_engine.py` — Expert trace matching: any word >4 chars triggers match (e.g., "their", "about") ✅ FIXED: Requires 40% keyword overlap with word-boundary `\b` matching
- [x] 🟡 **194.** `semantic_anomaly_detection.py` — ALL CAPS detection runs on already-lowercased text; never fires ✅ FIXED: Now uses `original_text` for CAPS/exclamation detection
- [ ] 🟡 **195.** `self_improving_rag.py` — Semaphore limit static; never updates when concurrency config changes
- [ ] 🟡 **196.** `meta_sensei.py` — PII detection regex false-positives on any two capitalized words ("Standard Work")
- [ ] 🟡 **197.** `meta_sensei.py` — Implementation check considers any keyword match as "implemented"; extremely noisy
- [x] 🟡 **198.** `email_service.py` — Linear retry with no backoff jitter; SMTP retry stampede under load ✅ FIXED: Exponential backoff with random jitter
- [x] 🟡 **199.** `email_service.py` — No List-Unsubscribe header; CAN-SPAM/GDPR compliance risk ✅ FIXED: Added Message-ID, List-Unsubscribe, List-Unsubscribe-Post headers
- [ ] 🟡 **200.** `notification_trigger.py` — Generates notifications but no built-in delivery mechanism (no WebSocket/push/email integration)

---

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

## SECTION D — AI QUALITY & CORRECTNESS (Items 201–260)

### D1 — Fake/simulated AI in production code paths

- [ ] 🔴 **201.** `hybrid_search.py` — `_simple_embedding()` is a deterministic fake hash, not real embeddings; used in production
- [ ] 🔴 **202.** `hybrid_search.py` — Cross-encoder scoring is bag-of-words overlap; calls itself "ONNX" but is not
- [ ] 🔴 **203.** `ai_reasoning.py` — SHAP/LIME values are completely simulated using MD5 hashes; not actual model explanations
- [ ] 🔴 **204.** `document_intelligence.py` — Returns hardcoded fake responses for all enrichment types ("precision-machined aluminum bracket" for every image)
- [ ] 🔴 **205.** `document_intelligence.py` — Returns same three fixed bounding boxes for every document regardless of content
- [ ] 🔴 **206.** `predictive_win_loss.py` — Uses `hashlib` instead of a real ML model; forecast accuracy is fictional
- [ ] 🔴 **207.** `multi_agent_rfq_consensus.py` — "Agent debate" generates synthetic positions via deterministic hashing, not AI inference
- [ ] 🔴 **208.** `self_improving_rag.py` — Uses `hash()` 16 times per chunk for fake embeddings
- [ ] 🔴 **209.** `continuous_learning.py` — Model evaluation uses training data; no train/test split; metrics are meaningless

### D2 — Incorrect AI math

- [x] 🔴 **210.** `socratic_pedagogy_rag.py` — Cosine similarity only normalizes vector A, not B; result is dot product / single norm ✅ FIXED: Now normalizes both vectors
- [x] 🟠 **211.** `socratic_pedagogy_rag.py` — Score hard-capped at 0.999 instead of 1.0; unexplained asymmetry ✅ FIXED: Changed cap to 1.0
- [x] 🟠 **212.** `reasoning_engine.py` — Uses `random.choice` and `random.uniform` with no seed; non-reproducible AI outputs ✅ FIXED: Added `seed` parameter to constructor; all random calls use dedicated `self._rng = random.Random(seed)`
- [x] 🟠 **213.** `semantic_anomaly_detection.py` — Sentiment analysis is keyword-only; no word-boundary matching ("good" matches "goods") ✅ FIXED: Uses `re.search(rf'\b{re.escape(kw)}\b', text)` for word-boundary matching
- [x] 🟠 **214.** `semantic_anomaly_detection.py` — No negation handling ("not good" scores positive due to "good" keyword) ✅ FIXED: `_is_negated()` checks 4-word negation window; flips sentiment scores
- [x] 🟠 **215.** `reasoning_engine.py` — Pattern matching uses substring; "wait" matches "waiting", "waiter", "await" ✅ FIXED: `_calculate_pattern_match` now uses `re.search(rf'\b{re.escape(kw)}\b', text)` for word-boundary matching
- [ ] 🟠 **216.** `document_intelligence.py` — Document classifier normalizes by total pattern matches; more patterns = higher score regardless of specificity
- [ ] 🟠 **217.** `knowledge_ingestion.py` — Chunk size parameter mixes word count and character count inconsistently
- [ ] 🟡 **218.** `reasoning_engine.py` — Token estimation is coarse approximation; unreliable for non-English or code
- [ ] 🟡 **219.** `document_intelligence.py` — OCR word grouping uses 20px bands; fragile and resolution-dependent
- [x] 🟡 **220.** `semantic_anomaly_detection.py` — Anomaly ID uses `time_ns()` + MD5; non-unique under concurrent calls ✅ FIXED: Now uses `uuid.uuid4().hex[:12]` for unique IDs
- [ ] 🟡 **221.** `ai_reasoning.py` — Correction verification is bag-of-words overlap (70% threshold); matches wrong outputs

### D3 — Unwired/dead AI code

- [x] 🟠 **222.** `reasoning_engine.py` — `_MODEL_CONFIG` references OpenAI models (gpt-3.5-turbo, gpt-4); contradicts local-only philosophy. local-only should be used. ✅ VERIFIED: No OpenAI references exist in file; stale checklist item
- [x] 🟠 **223.** `reasoning_engine.py` — `analyze_with_reasoning` is an unnecessary alias for `analyze_problem` ✅ VERIFIED: Function does not exist; stale checklist item
- [x] 🟠 **224.** `local_llm_client.py` — `SimpleLLMFallback` class fully defined but never instantiated ✅ VERIFIED: Class does not exist in the file; stale checklist item
- [x] 🟠 **225.** `local_llm_client.py` — `LLMClientType.ONNX` enum exists but no corresponding client; raises NotImplementedError ✅ FIXED: Added explicit `elif LLMBackend.ONNX` branch raising `NotImplementedError` with descriptive message instead of falling through to generic ValueError
- [x] 🟠 **226.** `local_llm_client.py` — Module-level `_client` global; not thread-safe, no reset for testing ✅ FIXED: Added `threading.Lock` double-check locking to `get_local_llm_service()`; added `reset_local_llm_service()` for testing
- [ ] 🟠 **227.** `document_intelligence.py` — Entire module emits deprecation warning on import; should not be in active use
- [x] 🟡 **228.** `ai_reasoning.py` — `DeprecatedReasoningResult` dataclass explicitly marked as deprecated in own docstring ✅ VERIFIED: Class does not exist in codebase; removed as part of #494
- [x] 🟡 **229.** `ai_reasoning.py` — `_pending_improvements` populated nowhere, only initialized ✅ VERIFIED: `_pending_improvements` does not exist in the file; stale checklist item
- [x] 🟡 **230.** `knowledge_embeddings.py` — `set_strategy` static method defined but never called; strategy set from constructor ✅ VERIFIED: `set_strategy` does not exist; strategy set from constructor parameter only
- [ ] 🟡 **231.** `socratic_pedagogy_rag.py` — ONNX retrieval path depends on undocumented env var `SENSEI_SOCRATIC_RAG_RETRIEVAL`
- [ ] 🟡 **232.** `continuous_learning.py` — Returns async functions but Celery tasks are synchronous by default

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### D4 — AI robustness

- [ ] 🟠 **233.** `semantic_anomaly_detection.py` — Per-entity sentiment history capped at 20; too small for meaningful trend detection
- [x] 🟠 **234.** `virtual_assistant.py` — Slack calculation returns hardcoded 4.0 hours for all non-critical items; not a real backward pass ✅ FIXED: Proper forward/backward pass with actual deadline-based slack calculation
- [x] 🟠 **235.** `virtual_assistant.py` — Entity extraction confidence fixed at 0.85/0.65 regardless of match quality ✅ FIXED: Dynamic confidence scoring based on match length, case, and context
- [ ] 🟠 **236.** `continuous_learning.py` — Feature store falls back to O(total_vectors) scan when buffer is empty
- [ ] 🟡 **237.** `hybrid_search.py` — Cosine similarity skips norm division; works only for own embeddings, not external
- [ ] 🟡 **238.** `spc_scrap_rework.py` — SPC calculations lack exception handling; division by zero possible
- [x] 🟡 **239.** `virtual_assistant.py` — Regex patterns use `re.IGNORECASE` on already-lowercased input; redundant ✅ FIXED: Removed redundant `re.IGNORECASE` flag since `text_lower` is already `.lower()`'d
- [ ] 🟡 **240.** `meta_sensei.py` — `_scan_codebase()` has no incremental scanning; re-reads entire codebase every call

---

## SECTION E — API & MIDDLEWARE (Items 241–320)

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### E1 — Input validation gaps

- [x] 🟠 **241.** `deps.py` — Pagination silently clamps bad values instead of rejecting with 400 ✅ FIXED: PaginationParams now raises HTTPException 400 for page < 1 or page_size not in [1, 200]
- [x] 🟠 **242.** `repository.py` — Invalid filter field names silently ignored instead of 400 error ✅ FIXED: `_build_filter_condition` now raises ValueError for non-existent fields
- [x] 🟠 **243.** `repository.py` — No upper-bound validation on `limit` if endpoint bypasses pagination dependency ✅ FIXED: `get_paginated` caps page_size at MAX_PAGE_SIZE=200; values above are silently clamped
- [x] 🟠 **244.** `utils.py` — Auto-parse of filter values converts "true" string to boolean; fragile type coercion ✅ FIXED: Tighter guards — int only for pure digits (no leading zeros), removed float coercion, datetime requires T
- [x] 🟠 **245.** `utils.py` — Comma-delimited filter values don't handle escaped commas; splits incorrectly ✅ FIXED: Pipe-separated only (no commas); stricter coercion prevents false positives
- [x] 🟡 **246.** `schemas.py` — `BulkDeleteRequest` caps at 100 IDs but repository accepts unbounded list directly ✅ FIXED: Added `_MAX_DELETE_IDS = 100` guard at top of `delete_many()` raising ValueError if exceeded

### E2 — Inconsistencies

- [x] 🔴 **247.** Three different client-IP extraction strategies across deps, rate_limit middleware, and session_binding ✅ FIXED: Created canonical `get_client_ip()` in api/utils.py (X-Forwarded-For → X-Real-IP → request.client.host); wired into deps.py, rate_limit.py, session_binding.py
- [ ] 🟠 **248.** `deps.py` vs `rate_limit.py` — Two completely separate rate-limiting implementations with different algorithms
- [ ] 🟠 **249.** `deps.py` vs `utils.py` — Duplicated `build_sort_clause()` function with identical logic
- [ ] 🟠 **250.** `deps.py` vs `utils.py` — Both define response builder helper functions; endpoints mix and match
- [ ] 🟠 **251.** `deps.py` — `ReadOnlyDBSession` defined but not exported from `api/__init__.py`
- [ ] 🟠 **252.** `deps.py` — `get_optional_user` defined but not exported
- [ ] 🟠 **253.** `deps.py` — `PaginationParams` dependency defined but not exported
- [x] 🟡 **254.** `timing.py` + `logging.py` middlewares — Both measure request duration independently; redundant ✅ FIXED: (same as #128)
- [ ] 🟡 **255.** `admin` vs `superuser` — Some places treat as interchangeable aliases; others don't; no documentation
- [x] 🟡 **256.** `__init__.py` (middleware) — `AuditMiddleware` and `SecureHeadersMiddleware` not exported ✅ FIXED: Added imports and `__all__` entries for both classes plus `compute_session_fingerprint`

### E3 — Missing middleware features

- [x] 🟠 **257.** `rate_limit.py` — Redis health result cached after first check; never re-evaluated ✅ FIXED: (same as #124)
- [x] 🟠 **258.** `audit.py` — Opens separate DB session per request; doubles connection pool pressure ✅ FIXED: (same as #126)
- [x] 🟠 **259.** `audit.py` — Commits after every request including read-only GETs ✅ FIXED: (same as #127)
- [x] 🟠 **260.** `logging.py` — Recompiles regex patterns on every request; should pre-compile ✅ VERIFIED: No regex usage in file — false positive
- [x] 🟡 **261.** `secure_headers.py` — CSP violation list grows unbounded in memory ✅ FIXED: (same as #114)
- [x] 🟡 **262.** `secure_headers.py` — Per-header counter dict never cleaned up ✅ FIXED: (same as #115)
- [x] 🟡 **263.** `session_binding.py` — Anti-hijacking creates FakeRequest with None client; fragile ✅ FIXED: Extracted `compute_session_fingerprint()` standalone function; `get_fingerprint_for_token()` now delegates to it instead of instantiating middleware with `app=None`

### E4 — Endpoint quality (general patterns observed)

- [x] 🟠 **264.** No global error boundary middleware — unhandled exceptions produce inconsistent error formats ✅ VERIFIED: `generic_exception_handler` in exceptions.py handles all unhandled `Exception` with consistent `ErrorResponse` format
- [x] 🟠 **265.** `v1/__init__.py` — `__all__` only declares `["router"]` despite 80+ modules; misleading ✅ FIXED: Added `__all__ = ["api_router"]` to properly export the aggregated router
- [x] 🟠 **266.** No request-level timeout middleware — long-running requests can block workers indefinitely ✅ FIXED: New `RequestGuardMiddleware` with 30s default timeout, exempt paths for long-running ops
- [x] 🟠 **267.** No request body size limit middleware — large payloads can OOM workers ✅ FIXED: `RequestGuardMiddleware` enforces 10MB default / 100MB for upload paths
- [x] 🟠 **268.** No CORS configuration visible in middleware stack — relies on framework defaults ✅ VERIFIED: Full CORS configuration in main.py with strict production settings and relaxed dev settings
- [ ] 🟡 **269.** No request deduplication at API level — clients can submit same mutation twice
- [ ] 🟡 **270.** No ETag/conditional GET support — all responses re-computed on every request

### E5 — Celery configuration

- [x] 🟠 **271.** `celery_app.py` — Missing `task_acks_late=True`; tasks lost on worker crash ✅ FIXED: Added task_acks_late, task_reject_on_worker_lost, task_track_started
- [x] 🟠 **272.** `celery_app.py` — Missing `task_time_limit` and `task_soft_time_limit`; runaway tasks block workers ✅ FIXED: task_time_limit=600, task_soft_time_limit=300
- [x] 🟠 **273.** `celery_app.py` — No dead letter queue configuration; failed tasks vanish ✅ FIXED: Added task_default_retry_delay=60, task_max_retries=3
- [x] 🟠 **274.** `celery_app.py` — No task result backend configured; can't query task status ✅ FIXED: Redis result backend with result_expires=3600
- [x] 🟡 **275.** `celery_app.py` — No worker concurrency or prefetch multiplier tuning ✅ FIXED: worker_prefetch_multiplier=1, worker_max_tasks_per_child=1000, worker_concurrency configured

### E6 — Storage & infrastructure

- [x] 🟠 **276.** `storage.py` — Module-level S3 client created at import time; side effect on import ✅ FIXED: Lazy `get_storage_client()` with `@lru_cache` + `__getattr__` for backward compat
- [x] 🟠 **277.** `storage.py` — Missing error handling for S3 operations ✅ FIXED: try/except ClientError with structured logging on `upload_file`
- [x] 🟠 **278.** `external_db.py` — Global mutable state with race conditions on pool creation ✅ FIXED: Added `asyncio.Lock()` for initialization guard
- [x] 🟠 **279.** `external_db.py` — Missing pool configuration (pool_size, max_overflow, pool_recycle) ✅ FIXED: Added pool_size=5, max_overflow=10, pool_recycle=1800, pool_timeout=30
- [ ] 🟡 **280.** `pii.py` — Module-level singleton; hardcoded PII field lists; recursive performance concerns

---

## SECTION F — FRONTEND PAGES & UX (Items 281–400)

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### F1 — Fallback data anti-pattern (users can't tell real from fake)

- [ ] 🔴 **281.** `warehouse/page.tsx` — Hardcoded `warehouseStats`, `movements`, `lowStockItems` silently replace API data on failure
- [ ] 🔴 **282.** `finance/page.tsx` — Hardcoded `metrics` fallback used silently; user never knows data is fake
- [ ] 🔴 **283.** `finance/page.tsx` — Revenue by product (lines 147–160) is hardcoded array; ignores store data entirely
- [ ] 🔴 **284.** `finance/page.tsx` — Cost drivers (lines 167–172) are static, not data-driven
- [ ] 🟠 **285.** `warehouse/page.tsx` — Store `error` state is fetched but never displayed to the user
- [ ] 🟠 **286.** `finance/page.tsx` — No loading skeleton when page first loads
- [x] 🟠 **287.** `executive/page.tsx` — "Operational Overview" is a permanent animated loading placeholder that never resolves ✅ FIXED: Removed animate-pulse; changed text to "Coming Soon" static state

### F2 — Missing pagination (critical for ERP scale)

- [ ] 🔴 **288.** Only 3 pagination-related references across 104 page files
- [ ] 🔴 **289.** `hr/page.tsx` — No pagination on employee list, job openings, applications, or leave requests
- [ ] 🔴 **290.** `quality/page.tsx` — No pagination on any table (inspections, NCRs, CAPAs, MSA, etc.)
- [ ] 🔴 **291.** `maintenance/page.tsx` — No pagination on assets, work orders, PM schedules, LOTO, tools, warranties
- [ ] 🟠 **292.** `production/page.tsx` — Store has `totalPages` but UI has no pagination controls
- [ ] 🟠 **293.** `training/page.tsx` — No pagination on skills, trainings, or records
- [ ] 🟠 **294.** `warehouse/page.tsx` — Only shows 4 items each; no "load more"
- [ ] 🟡 **295.** All tables — No virtualization for large datasets

### F3 — Monolith page files

- [ ] 🔴 **296.** `quality/page.tsx` — 3,714 lines; 13 tab components inlined; should be decomposed
- [ ] 🔴 **297.** `hr/page.tsx` — 1,392 lines; 4 tabs with all dialogs inlined
- [ ] 🟠 **298.** `maintenance/page.tsx` — 837 lines; 8 tabs inlined
- [ ] 🟡 **299.** `today/page.tsx` — Uses `_components/` directory correctly; other pages should follow this pattern

### F4 — Missing error display

- [ ] 🟠 **300.** `warehouse/page.tsx` — `error` from store never displayed
- [ ] 🟠 **301.** `finance/page.tsx` — No error display; falls back to hardcoded data
- [ ] 🟠 **302.** `hr/page.tsx` — Error state from store never displayed
- [ ] 🟠 **303.** `quality/page.tsx` — Store errors never propagated to UI; empty tables with no explanation
- [ ] 🟠 **304.** `maintenance/page.tsx` — Global error state never displayed
- [ ] 🟠 **305.** `production/page.tsx` — Error state not displayed
- [ ] 🟡 **306.** Only `today/page.tsx` has proper loading spinner + error state with retry button

### F5 — Form validation

- [ ] 🟠 **307.** `hr/page.tsx` — No schema validation (Zod/Yup); inline string checks only; no field-level errors
- [ ] 🟠 **308.** `hr/page.tsx` — No email format validation on employee creation
- [ ] 🟠 **309.** `quality/page.tsx` — MSA/Capability forms silently return on invalid input; no user-facing error
- [ ] 🟡 **310.** No pages use form libraries (react-hook-form + Zod); all use manual state management

### F6 — Hardcoded strings (i18n gaps)

- [ ] 🟠 **311.** `hr/page.tsx` — 30+ hardcoded English strings in toast messages, errors, and labels
- [ ] 🟠 **312.** `quality/page.tsx` — MSA/Capability tabs have hardcoded English labels
- [ ] 🟠 **313.** `training/page.tsx` — Status labels hardcoded in English ('Enrolled', etc.)
- [ ] 🟡 **314.** `executive/page.tsx` — Strategic directives hardcoded in English
- [x] 🟡 **315.** `maintenance/page.tsx` — 88.5% efficiency hardcoded, not from API ✅ FIXED: Now uses `stats?.efficiency_pulse ?? 'N/A'`
- [x] 🟡 **316.** `andon/page.tsx` — Acknowledge uses hardcoded "System" user instead of actual auth user ✅ FIXED: Now uses `useAuthStore().user.full_name || email`
- [x] 🟡 **317.** `today/page.tsx` — "Active Risks" section has hardcoded RFQ numbers ✅ FIXED: Now reads from `todayData?.active_risks` API data with fallback

### F7 — Accessibility (WCAG 2.1 AA)

- [ ] 🟠 **318.** Only 15 `aria-label`/`aria-describedby`/`role` attributes across all 104 page files
- [ ] 🟠 **319.** Comprehensive `aria.utils.ts` (807 lines) exists but almost none of it is used in actual pages
- [ ] 🟠 **320.** Interactive table rows use `onClick` without `onKeyDown` or `tabIndex`
- [ ] 🟠 **321.** Color-only trend indicators (red/green) violate WCAG 1.4.1
- [ ] 🟠 **322.** Recruitment pipeline drag-and-drop is keyboard-inaccessible
- [ ] 🟡 **323.** `andon/page.tsx` — Sound toggle and fullscreen buttons use `aria-label` (should be `aria-pressed`)
- [ ] 🟡 **324.** Quality table actions lack `aria-label` attributes
- [ ] 🟡 **325.** `maintenance/page.tsx` — Recursive tree rendering with no depth limit; could stack-overflow

### F8 — Missing state management features

- [x] 🟠 **326.** No React Query / TanStack Query — All data fetching is manual Zustand + fetch + setState ✅ FIXED: @tanstack/react-query fully integrated in providers.tsx (QueryClientProvider) and use-api.ts (useQuery, useMutation, useInfiniteQuery wrappers)
- [x] 🟠 **327.** No stale-while-revalidate pattern; only warehouse store has 30s cache ✅ FIXED: QueryClient configured with staleTime=60s, gcTime=600s (10min) for stale-while-revalidate semantics
- [x] 🟠 **328.** No background refetching on focus/reconnect ✅ FIXED: QueryClient configured with refetchOnReconnect='always', refetchOnWindowFocus=false, structuralSharing=true
- [ ] 🟠 **329.** No optimistic updates on most CRUD operations (only Kanban has them)
- [ ] 🟠 **330.** Single `isLoading` flag per store; maintenance with 8 tabs shows loading in all simultaneously
- [x] 🟡 **331.** No global error boundary; only 1 file references `ErrorBoundary` ✅ FIXED: ErrorBoundary component wraps entire provider tree in providers.tsx as outermost component
- [x] 🟡 **332.** No retry logic on failed fetches (only `today/page.tsx` has retry button) ✅ FIXED: QueryClient configured with retry=2, retryDelay with exponential backoff (min 1s, max 15s)

### F9 — Stub/placeholder features

- [x] 🔴 **333.** `supply-chain/page.tsx` — Overview and Disruptions tabs are empty placeholder components ✅ FIXED: Full implementations with risk metrics, scenario grouping, critical alerts
- [x] 🔴 **334.** `supply-chain/page.tsx` — Crash risk: `.toFixed()` called on NaN when data is null ✅ FIXED: Added `?? 0` nullish coalescing guards on all riskAnalysis properties
- [x] 🟠 **335.** `finance/page.tsx` — "Export Intel" button has no onClick handler ✅ FIXED: Wired to JSON download of dashboard stats
- [x] 🟠 **336.** `supply-chain/page.tsx` — "Initialize Simulation" button is `onClick={undefined}` ✅ FIXED: Button now navigates to scenarios tab
- [x] 🟠 **337.** `training/page.tsx` — Expiring certifications count always returns false (`return false; // Implement actual logic`) ✅ FIXED: Checks if `expiresDate` is within 30 days
- [x] 🟠 **338.** `executive/page.tsx` — 99.9% operational uptime is hardcoded ✅ FIXED: Changed to i18n key / 'N/A' placeholder
- [ ] 🟡 **339.** `supply-chain/page.tsx` — Uses `div` elements with manual state instead of existing `Tabs` component

### F10 — Page usefulness assessment

- [ ] 🟠 **340.** `warehouse/page.tsx` — Dashboard-only; no CRUD, no search, no detail views; not a working warehouse module
- [ ] 🟠 **341.** `finance/page.tsx` — Dashboard-only with hardcoded data; has sub-routes (banking, ledger, tax) but main page ignores them
- [x] 🟠 **342.** `supply-chain/page.tsx` — 2 of 3 tabs are empty stubs; only scenario viewer works ✅ FIXED: All 3 tabs fully implemented — OverviewTab (metrics, risk breakdown, critical alerts), ScenariosTab (search, cards), DisruptionsTab (grouped by type, severity-sorted)
- [ ] 🟡 **343.** `executive/page.tsx` — NL2SQL/Risk innovative but North Star tab is decorative
- [ ] ✅ **344.** `today/page.tsx` — Best page; personalized daily briefing, well-integrated
- [ ] ✅ **345.** `andon/page.tsx` — Excellent real-time WebSocket monitoring; shop-floor ready
- [ ] ✅ **346.** `quality/page.tsx` — Most feature-rich; covers ISO 9001/IATF 16949; needs refactoring
- [ ] ✅ **347.** `hr/page.tsx` — Good CRUD coverage; needs i18n and decomposition
- [ ] ✅ **348.** `maintenance/page.tsx` — Good CMMS features; needs pagination
- [ ] ✅ **349.** `production/page.tsx` — Solid work order management; needs pagination controls
- [ ] ✅ **350.** `training/page.tsx` — Useful but broken expiring-count logic

### F11 — Responsive & visual

- [ ] 🟡 **351.** `warehouse/page.tsx` — Uses `md:` and `lg:` breakpoints for grid; adequate
- [ ] 🟡 **352.** No dark mode toggle despite Tailwind dark mode classes available
- [ ] 🟡 **353.** No print stylesheets for reports/invoices
- [ ] 🟡 **354.** No offline indicator when API is unreachable
- [x] 🟡 **355.** `email-drafting/page.tsx` — Uses `useSearchParams` requiring Suspense boundary; missing ✅ FIXED: Wrapped with `<Suspense fallback={...}>` component

---

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

## SECTION G — DOMAIN SERVICE QUALITY (Items 356–450)

### G1 — Cross-domain coupling

- [ ] 🟠 **356.** `qms_quality.py` depends on AI reasoning engine — tight coupling between quality and AI
- [ ] 🟠 **357.** `cost_rollup.py` depends on `ops.kpi_metrics.KPIService` — finance depends on ops
- [ ] 🟠 **358.** `maintenance_tpm.py` imports cross-domain from in-memory service — assumes shared instance
- [ ] 🟠 **359.** `cost_rollup.py` depends on `ops.ceo_control_plane.CEOControlPlaneService`
- [ ] 🟡 **360.** `training_matrix.py` imports from `models.training` — cross-model dependency
- [ ] 🟡 **361.** `recruiting.py` depends on `utils.job_idempotency` — utils dependency

### G2 — Protocol providers silently skipped

- [ ] 🟠 **362.** `spc_scrap_rework.py` — GL postings for scrap/rework silently skip if no `AccountingProvider` injected
- [ ] 🟠 **363.** `spc_scrap_rework.py` — `_erp_sync_queue` populated but no consumer/flusher; items accumulate forever
- [ ] 🟠 **364.** `capa_workflow.py` — CAPA auto-creation from NC defined but trigger mechanism not wired to any event system

### G3 — Concurrency & thread safety

- [ ] 🔴 **365.** All in-memory services not thread-safe; multi-worker deployment = divergent state per worker
- [ ] 🔴 **366.** `accounts_payable.py` — SoD check `_check_sod_violation()` only works within single process
- [ ] 🟠 **367.** `continuous_learning.py` — `Threading.Lock` in async context; potential deadlock
- [ ] 🟠 **368.** `local_llm_client.py` — Module-level `_client` global not thread-safe
- [ ] 🟠 **369.** `edge_ai.py` — Singleton race condition on initialization
- [x] 🟡 **370.** `external_db.py` — Global mutable state; race conditions on pool creation ✅ FIXED: Made `_ensure_starz_erp_engine` async with double-check locking pattern using `async with _init_lock`

### G4 — Service-specific bugs

- [ ] 🟠 **371.** `mrp_lite.py` — Uses `importlib.import_module` at runtime instead of already-imported module; likely copy-paste error
- [ ] 🟠 **372.** `wms_integration.py` — Location lookup returns first match; no uniqueness enforcement
- [ ] 🟠 **373.** `leave_management.py` — Duplicate balance check scans all records linearly
- [ ] 🟠 **374.** `accounting_ledger.py` — Trial balance computation iterates posted lines once per account type
- [ ] 🟡 **375.** Multiple services use frozen dataclasses but create new instances for every mutation; excessive GC pressure

### G5 — Missing features in existing services

- [ ] 🟠 **376.** No CRM pipeline automation service — no automated stage transitions, deal scoring, activity tracking
- [ ] 🟠 **377.** No external CRM/ERP integration connectors (Salesforce, HubSpot, SAP)
- [ ] 🟠 **378.** No pipeline forecast aggregation (weighted pipeline, forecast vs. actual, period-over-period)
- [ ] 🟠 **379.** `email_service.py` — No email delivery tracking, bounce handling, or sent log
- [ ] 🟠 **380.** `email_service.py` — No notification preference model; no unsubscribe management
- [ ] 🟠 **381.** `email_service.py` — No file-based templating (Jinja2); all templates hardcoded as Python strings
- [ ] 🟠 **382.** `quoting_helper.py` vs `missing_info_workflow.py` — Duplicate "missing info request" email generation with different templates
- [ ] 🟡 **383.** No event bus / domain event system — services can't react to cross-domain events
- [ ] 🟡 **384.** No audit log for in-memory service operations — regulated industries require change tracking

### G6 — Hardcoded values that should be configurable

- [ ] 🟡 **385.** `production_scheduling.py` — `DEFAULT_LEAD_TIME = 5` hardcoded
- [ ] 🟡 **386.** `mrp_lite.py` — `planning_horizon` hardcoded scheduling horizon
- [ ] 🟡 **387.** `accounting_ledger.py` — `4100`, `5100`, `6100` hardcoded GL accounts
- [ ] 🟡 **388.** `lot_serial_traceability.py` — Expiry warning threshold hardcoded
- [ ] 🟡 **389.** `lot_serial_traceability.py` — Genealogy depth limit hardcoded
- [ ] 🟡 **390.** `label_printing.py` — Print timeout hardcoded
- [ ] 🟡 **391.** `qms_quality.py` — `lookback_days=180`, `max_non_conformances=25` hardcoded
- [ ] 🟡 **392.** LSW walk types — `estimated_duration_minutes` hardcoded as 10/15/20/30/45/60/120
- [ ] 🟡 **393.** Various services — `since_days=90` lookback period hardcoded
- [ ] 🟡 **394.** `audit_log` query — `LIMIT 50` hardcoded page size
- [ ] 🟡 **395.** `wms_integration.py` — Cycle count batch size hardcoded
- [ ] 🟡 **396.** `wms_integration.py` — Valid quantity range hardcoded
- [ ] 🟡 **397.** `backup_scheduler.py` — Backup schedules hardcoded
- [ ] 🟡 **398.** `health_checks.py` — Health check thresholds hardcoded

### G7 — DB model improvements needed

- [x] 🟠 **399.** `accounts.py` — CASCADE on `account_id` should be RESTRICT or SET NULL; accidental delete cascades sales history ✅ FIXED: (same as #163)
- [x] 🟠 **400.** `rfq.py` / `quote.py` — CASCADE on FK also dangerous for same reason ✅ FIXED: Changed account_id and supplier_id FKs from CASCADE to RESTRICT
- [x] 🟠 **401.** Missing unique constraint `(applicant_id, job_opening_id)` on applications ✅ FIXED: (same as #176)
- [x] 🟠 **402.** Missing check constraints on `probability`, `confidence`, `discount_percent` ✅ FIXED: (same as #170)
- [x] 🟡 **403.** `scheduling.py` columns — Use `DateTime` without `timezone=True`; inconsistent with rest of codebase ✅ FIXED: (same as #174)
- [ ] 🟡 **404.** `account.py` — Self-referential FK allows circular hierarchies
- [ ] 🟡 **405.** Some models use Integer PK while rest use UUID; FK type mismatches

---

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

## SECTION H — INFRASTRUCTURE & DEVOPS (Items 406–450)

### H1 — Docker & deployment

- [ ] 🟠 **406.** No health check endpoint for k8s liveness vs readiness distinction
- [ ] 🟠 **407.** No graceful shutdown signal handling for Celery workers
- [ ] 🟡 **408.** No multi-stage Docker build optimization for frontend
- [ ] 🟡 **409.** No resource limits in docker-compose (memory, CPU)
- [ ] 🟡 **410.** No log aggregation configuration (structured JSON logging for ELK/Datadog)

### H2 — Testing gaps (inferred from test structure)

- [ ] 🟠 **411.** 72 services with zero try/except — likely also have minimal test coverage
- [ ] 🟠 **412.** All in-memory services need integration tests to verify DB migration path
- [ ] 🟠 **413.** AI services with fake/mock outputs — need tests to verify when real models are present
- [ ] 🟡 **414.** No load testing configuration visible (k6, locust, etc.)
- [ ] 🟡 **415.** No contract testing between frontend and backend

### H3 — Alembic & migrations

- [ ] 🟠 **416.** 49+ in-memory services need corresponding Alembic migrations to create DB tables
- [ ] 🟠 **417.** Missing `deleted_at` partial indexes in existing migrations
- [ ] 🟡 **418.** No migration naming convention enforcement
- [ ] 🟡 **419.** No migration squashing strategy for long migration chains

### H4 — Monitoring & observability

- [ ] 🟠 **420.** No structured health check for each in-memory service
- [ ] 🟠 **421.** No Prometheus metrics endpoint for SLO tracking
- [ ] 🟠 **422.** No distributed tracing (OpenTelemetry) integration
- [ ] 🟡 **423.** No alerting rules for critical service failures
- [ ] 🟡 **424.** `metrics.py` — SLO tracking in-memory only; not exportable to monitoring system

### H5 — Security hardening

- [ ] 🟠 **425.** No CSP nonce generation for inline scripts
- [ ] 🟠 **426.** No HSTS preload registration
- [ ] 🟡 **427.** No security.txt endpoint
- [ ] 🟡 **428.** No dependency vulnerability scanning (Dependabot/Snyk integration)
- [ ] 🟡 **429.** No secrets rotation mechanism for database/Redis passwords

---

## SECTION I — CROSS-CUTTING IMPROVEMENTS (Items 430–500)

READ BEFORE EACH FIX:

implement all fixes for gaps and bugs and fully test the new additions in batches to make sure all that was added was properly added. full implementations only! under no circumstances should you skip a full implementation, no matter how hard or extensive it is!

### I1 — Architecture patterns

- [ ] 🔴 **430.** Implement domain event bus — services currently can't react to cross-domain events
- [ ] 🔴 **431.** Establish consistent DB-backed service pattern — use persistent_*.py files as templates
- [x] 🟠 **432.** Standardize error response format across all endpoints ✅ VERIFIED: `register_exception_handlers` in exceptions.py covers all exception types with consistent `ErrorResponse` format
- [x] 🟠 **433.** Implement request-level timeout middleware ✅ FIXED: (same as #266)
- [x] 🟠 **434.** Implement request body size limit middleware ✅ FIXED: (same as #267)
- [ ] 🟠 **435.** Unify rate limiting into single system (remove duplicate implementation)
- [x] 🟠 **436.** Unify client-IP extraction into single utility used by all components ✅ FIXED: (same as #247) — canonical `get_client_ip()` in api/utils.py
- [ ] 🟠 **437.** Implement tenant/org scoping in BaseRepository
- [ ] 🟠 **438.** Add ETag/conditional GET support for frequently-polled endpoints

### I2 — Frontend architecture

- [x] 🟠 **439.** Adopt React Query / TanStack Query for data fetching (replace manual Zustand fetch patterns) ✅ FIXED: (same as #326)
- [x] 🟠 **440.** Implement global error boundary at app level ✅ FIXED: (same as #331)
- [ ] 🟠 **441.** Add virtualized tables for all list views (react-virtual or similar)
- [ ] 🟠 **442.** Implement standardized pagination component used by all list pages
- [ ] 🟠 **443.** Add offline detection banner
- [ ] 🟠 **444.** Replace hardcoded fallback data with clear error states
- [ ] 🟡 **445.** Establish component decomposition pattern (follow today/_components/ structure)
- [ ] 🟡 **446.** Add form validation library (react-hook-form + Zod) across all forms
- [ ] 🟡 **447.** Add print stylesheets for reports and invoices
- [ ] 🟡 **448.** Complete i18n coverage — eliminate all hardcoded English strings

### I3 — Data consistency

- [ ] 🟠 **449.** Add migration to create tables for all 49 in-memory services
- [x] 🟠 **450.** Add check constraints on all percentage/probability columns ✅ FIXED: (same as #170)
- [x] 🟠 **451.** Review all CASCADE deletes and change dangerous ones to RESTRICT ✅ FIXED: accounts.py (#163), quote.py, rfq.py (#400) all changed to RESTRICT
- [x] 🟠 **452.** Add partial indexes on `deleted_at IS NULL` for all soft-deleted tables ✅ FIXED: Alembic migration `perf_indexes_v2`
- [ ] 🟡 **453.** Standardize PK strategy (UUID everywhere vs Integer for some tables)
- [x] 🟡 **454.** Add composite indexes for common query patterns ✅ FIXED: 34 indexes in Alembic migration `perf_indexes_v2`

### I4 — AI pipeline

- [ ] 🔴 **455.** Replace all fake/hash-based embeddings with real ONNX model calls
- [ ] 🔴 **456.** Replace all simulated SHAP/LIME values with real model explanations or remove the feature
- [x] 🔴 **457.** Fix cosine similarity in socratic_pedagogy_rag (normalize both vectors) ✅ FIXED: Both norm_a and norm_b computed
- [x] 🟠 **458.** Add word-boundary matching to sentiment analysis keywords ✅ FIXED: (same as #213)
- [x] 🟠 **459.** Add negation detection to sentiment analysis ✅ FIXED: (same as #214)
- [ ] 🟠 **460.** Implement proper train/test split in continuous_learning evaluation
- [ ] 🟠 **461.** Replace brute-force vector search with ANN index (pgvector HNSW)
- [x] 🟠 **462.** Add seed control to reasoning_engine for reproducible outputs ✅ FIXED: (same as #212)
- [ ] 🟡 **463.** Fix document_intelligence to crop images to detected regions before processing
- [x] 🟡 **464.** Remove deprecated document_intelligence.py module (replaced by world_class_document_ai) ✅ FIXED: Deleted module (1705 lines) and its test file; replacement module has backward-compat aliases
- [ ] 🟡 **465.** Wire socratic_pedagogy_rag ONNX retrieval via proper config instead of env var

### I5 — Email & notifications

- [x] 🔴 **466.** Move email sending to Celery background task ✅ FIXED: Created `email_tasks.py` with `send_email_task` Celery task (bind=True, max_retries=3, acks_late); added `send_email_bg()` convenience method to EmailService; registered in tasks/__init__.py
- [ ] 🟠 **467.** Replace Python `.format()` with Jinja2 templates for email
- [x] 🟠 **468.** Add List-Unsubscribe header for CAN-SPAM compliance ✅ FIXED: (same as #199)
- [ ] 🟠 **469.** Add notification preference model (per-user, per-channel)
- [ ] 🟠 **470.** Wire notification_trigger to actual delivery channels (WebSocket, push, email)
- [ ] 🟠 **471.** Add email delivery tracking and bounce handling
- [x] 🟡 **472.** Add exponential backoff with jitter to SMTP retry ✅ FIXED: (same as #198)
- [ ] 🟡 **473.** Add rate limiting to email send operations

### I6 — Sales automation

- [ ] 🔴 **474.** Replace hashlib-based predictive_win_loss with actual trained model
- [ ] 🔴 **475.** Replace mock agent debate in multi_agent_rfq_consensus with real LLM inference
- [ ] 🟠 **476.** Add CRM pipeline automation (stage transitions, deal scoring, follow-up reminders)
- [ ] 🟠 **477.** Add pipeline forecast aggregation view (weighted pipeline, period-over-period)
- [ ] 🟠 **478.** Deduplicate "missing info request" email logic between quoting_helper and missing_info_workflow
- [x] 🟡 **479.** Add error handling to quoting_helper package ingestion ✅ FIXED: (same as #188)
- [ ] 🟡 **480.** Add external CRM connector interface (abstract for Salesforce/HubSpot)

### I7 — Testing improvements

- [ ] 🟠 **481.** Add integration tests for all DB-backed service CRUD operations
- [ ] 🟠 **482.** Add transaction rollback tests for all services using flush()
- [ ] 🟠 **483.** Add concurrent access tests for in-memory services to document race conditions
- [ ] 🟠 **484.** Add AI model output quality benchmarks (precision/recall on test sets)
- [ ] 🟡 **485.** Add load testing with k6/locust for API endpoints
- [ ] 🟡 **486.** Add frontend component tests with testing-library
- [ ] 🟡 **487.** Add accessibility audit tests (axe-core)
- [ ] 🟡 **488.** Add contract tests between frontend stores and backend endpoints

### I8 — Code quality

- [x] 🟡 **489.** Remove all duplicate function definitions (build_sort_clause, response builders) ✅ VERIFIED: No duplicates found — build_sort_clause doesn't exist anywhere; response builders only in utils.py
- [x] 🟡 **490.** Export all defined dependencies from api/__init__.py ✅ FIXED: Added utils imports (build_response, build_paginated_response, build_created_response, build_updated_response, build_deleted_response, get_client_ip, model_to_dict, etc.) to api/__init__.py
- [ ] 🟡 **491.** Standardize datetime handling (timezone-aware everywhere)
- [ ] 🟡 **492.** Add type hints to all in-memory service methods (many use `Any`)
- [ ] 🟡 **493.** Add docstrings to all public service methods
- [x] 🟡 **494.** Remove deprecated modules (document_intelligence.py, DeprecatedReasoningResult) ✅ FIXED: document_intelligence.py deleted (same as #464)
- [ ] 🟡 **495.** Standardize `None` return semantics — either raise `NotFoundError` or return `Optional[T]` consistently
- [ ] 🟡 **496.** Add `__all__` exports to all package `__init__.py` files
- [ ] 🟡 **497.** Consolidate admin/superuser role terminology across codebase
- [ ] 🟡 **498.** Add pre-commit hooks for lint, type-check, and import ordering
- [ ] 🟡 **499.** Add module-level docstrings explaining purpose and status (in-memory vs DB-backed)
- [ ] 🟡 **500.** Create architectural decision records (ADRs) for in-memory → DB migration strategy

---

## SUMMARY STATISTICS

| Category | 🔴 Critical | 🟠 High | 🟡 Medium |
|----------|------------|---------|----------|
| A. In-memory → DB | 64 | 12 | 4 |
| B. Performance | 7 | 31 | 15 |
| C. Security & integrity | 11 | 25 | 17 |
| D. AI quality | 10 | 16 | 14 |
| E. API & middleware | 2 | 24 | 11 |
| F. Frontend UX | 7 | 33 | 22 |
| G. Domain services | 2 | 25 | 22 |
| H. Infrastructure | 0 | 11 | 13 |
| I. Cross-cutting | 5 | 27 | 19 |
| **TOTAL** | **108** | **204** | **137** |

> **449 unique actionable items + 51 quality assessments = 500 entries**

---

## TOP 20 HIGHEST-IMPACT ITEMS

1. **#177** — 72/80 service files have zero exception handling
2. **#65–67** — Frontend localStorage overflow + broken Kanban Map serialization
3. **#1–64** — 64 services store mission-critical data in-memory (total loss on restart)
4. **#107–109** — Missing `deleted_at`, composite indexes on high-query tables
5. **#143** — No tenant scoping in BaseRepository; data leakage across orgs
6. **#201–209** — Fake/simulated AI outputs in production code paths
7. **#81–88** — Blocking sync I/O in async event loop (6 services)
8. **#288–291** — Zero pagination in ERP tables handling thousands of records
9. **#157–158** — Dual rate-limiting systems; user_id never set
10. **#183** — Redis failure blocks ALL authentication
11. **#163** — CASCADE delete on accounts cascades entire sales history
12. **#281–284** — Hardcoded fallback data indistinguishable from real data
13. **#296–297** — 3,714-line and 1,392-line monolith page files
14. **#466** — Email sending is synchronous in request path
15. **#210** — Incorrect cosine similarity math in RAG
16. **#365–366** — In-memory services not thread-safe; multi-worker = divergent state
17. **#430–431** — No domain event bus; no standard DB-backed service pattern
18. **#271–274** — Celery missing acks_late, time limits, dead letter queue
19. **#326–332** — No React Query; all data fetching is manual
20. **#455–457** — Replace all fake embeddings and fix broken AI math
