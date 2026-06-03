# Taiga-like PM System — Fix Plan

> **Status:** Implementation-ready plan  
> **Context:** All 4 analysis documents + 17 source files read and verified  
> **Scope:** ~20 problems across 6 parallelization tracks  
> **Priority:** P0 (Critical) → P3 (Enhancement)

---

## Table of Contents

1. [Priority & Track Overview](#1-priority--track-overview)
2. [P0 — Critical Fixes (Must Fix Before Production)](#2-p0--critical-fixes)
3. [P1 — High Priority (Required for Taiga-like Functionality)](#3-p1--high-priority)
4. [P2 — Medium Priority (Important for Parity)](#4-p2--medium-priority)
5. [P3 — Low Priority (Enhancement)](#5-p3--enhancement)
6. [Parallelization Strategy](#6-parallelization-strategy)
7. [Dependency Graph](#7-dependency-graph)
8. [Risk Assessment](#8-risk-assessment)
9. [File Reference Index](#9-file-reference-index)

---

## 1. Priority & Track Overview

### Priority Tiers

| Tier | Count | Criteria |
|------|-------|----------|
| **P0** | 4 | Production blocker: data loss, crash on startup, security vulnerability, dead subsystem |
| **P1** | 7 | Required for Taiga-like PM functionality: features that make the system usable |
| **P2** | 6 | Important for parity: closes feature gaps, improves correctness |
| **P3** | 5 | Enhancement: polish, hardening, non-critical improvements |

### Tracks for Parallel Execution

| Track | Focus Area | P0 | P1 | P2 | P3 | Total |
|-------|-----------|----|----|----|----|-------|
| **A** | Data Layer & Persistence | 2 | 0 | 2 | 0 | 4 |
| **B** | Kanban + Obeya | 0 | 1 | 2 | 0 | 3 |
| **C** | Tasks + State Machines | 0 | 2 | 0 | 0 | 2 |
| **D** | Today + A3 + Notifications | 1 | 0 | 2 | 0 | 3 |
| **E** | Search + Saved Views | 0 | 2 | 1 | 1 | 4 |
| **F** | Frontend | 1 | 2 | 0 | 3 | 6 |

---

## 2. P0 — Critical Fixes

### P0-A1: Missing `entity_store` DDL → Database Crash on Startup

- **Source:** [`postgres-init/01-init.sql`](../postgres-init/01-init.sql) (28 lines)
- **Analysis ref:** [`data-model-and-stores-deep-dive.md`](../docs/analysis/data-model-and-stores-deep-dive.md#L200-L217), [`taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md#L521-L545)

#### Problem Statement

The [`01-init.sql`](../postgres-init/01-init.sql) script creates only PostgreSQL extensions (`vector`, `uuid-ossp`, `pgcrypto`, `pg_trgm`, `pg_stat_statements`) and sets `ALTER SYSTEM` parameters. It contains **zero `CREATE TABLE` statements**. The [`EntityStore`](../sensei-rs/crates/sensei-api/src/db_stores.rs#L75-L85) persistence layer executes `INSERT INTO entity_store ...` SQL in [`persist_changes()`](../sensei-rs/crates/sensei-api/src/db_stores.rs#L315-L372) and `SELECT ... FROM entity_store` in [`load_from_db()`](../sensei-rs/crates/sensei-api/src/db_stores.rs#L246-L309). When [`AppState::with_db_pool()`](../sensei-rs/crates/sensei-api/src/state.rs#L399-L489) is called, all 33 entity stores attempt to load from and persist to this non-existent table, causing an immediate PostgreSQL error.

#### Before State

```sql
-- 01-init.sql (ENTIRE file — 28 lines, NO CREATE TABLE)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
ALTER SYSTEM SET wal_buffers = '64MB';
ALTER SYSTEM SET max_wal_size = '4GB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
ALTER SYSTEM SET effective_io_concurrency = 200;
```

#### After State

```sql
-- entity_store table added to 01-init.sql
CREATE TABLE IF NOT EXISTS entity_store (
    id          UUID NOT NULL,
    entity_type VARCHAR(128) NOT NULL,
    data        JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_entity_store PRIMARY KEY (entity_type, id)
);

CREATE INDEX idx_entity_store_entity_type ON entity_store (entity_type);
CREATE INDEX idx_entity_store_updated_at ON entity_store (updated_at);
```

#### Fix Strategy

1. Add `CREATE TABLE entity_store (...)` with composite primary key `(entity_type, id)` and JSONB `data` column
2. Add indexes on `entity_type` (for store isolation queries) and `updated_at` (for sync/lookup)
3. Ensure the DDL is idempotent with `IF NOT EXISTS`
4. Add a migration check in [`sensei-db/src/migrations.rs`](../sensei-rs/crates/sensei-db/src/migrations.rs) to verify the table exists on startup
5. Consider adding a `SELECT COUNT(*) FROM entity_store` health-check endpoint

#### Dependencies

- **Blocked by:** Nothing (foundation fix)
- **Blocks:** P0-A2 (without the table, persistence is meaningless)
- **Risk:** Low. Adding a table cannot break existing in-memory-only deployments.

---

### P0-A2: Fire-and-Forget Persistence in `StoreWriteGuard::drop()` → Silent Data Loss

- **Source:** [`sensei-rs/crates/sensei-api/src/db_stores.rs`](../sensei-rs/crates/sensei-api/src/db_stores.rs#L216-L239)
- **Analysis ref:** [`data-model-and-stores-deep-dive.md`](../docs/analysis/data-model-and-stores-deep-dive.md#L173-L189)

#### Problem Statement

[`StoreWriteGuard::drop()`](../sensei-rs/crates/sensei-api/src/db_stores.rs#L219-L238) uses `tokio::spawn(async move { persist_changes(...).await })` to persist data. This is a fire-and-forget pattern: if the spawned task fails (e.g., database connection error, serialization failure, constraint violation), the error is silently swallowed. The caller has already released the write lock and returned the HTTP response, so there is zero feedback. On application crash before the async task completes, all unpersisted changes are lost.

#### Before State

```rust
// db_stores.rs:219-238 — Fire-and-forget in Drop
fn drop(&mut self) {
    let pool = match self.inner.pool.clone() {
        Some(p) => p,
        None => return, // silently skip persistence
    };
    let entity_type = self.inner.entity_type.clone();
    let snapshot = self.inner.data.read().unwrap().clone();
    tokio::spawn(async move {
        persist_changes(pool, &entity_type, &snapshot).await;
    });
    // ^^^ Errors discarded, no backpressure, no ordering guarantee
}
```

#### After State

```rust
// Option A — Immediate (synchronous) persistence in Drop with error logging
fn drop(&mut self) {
    let pool = match self.inner.pool.clone() {
        Some(p) => p,
        None => return,
    };
    let entity_type = self.inner.entity_type.clone();
    let snapshot = self.inner.data.read().unwrap().clone();
    let rt = tokio::runtime::Handle::try_current();
    match rt {
        Some(handle) => {
            // Block the current thread to persist synchronously
            // Use spawn_blocking to avoid blocking async runtime
            let _ = handle.block_on(async {
                if let Err(e) = persist_changes(&pool, &entity_type, &snapshot).await {
                    tracing::error!(%entity_type, error = %e, "Failed to persist changes in StoreWriteGuard::drop");
                }
            });
        }
        None => {
            // Outside async context — log warning
            tracing::warn!(%entity_type, "Cannot persist: no async runtime available");
        }
    }
}

// Alternative approach: prefer explicit commit method
// Add a `commit(&self)` method that callers invoke before the guard drops.
// The Drop impl becomes a fallback with error logging only.
```

#### Fix Strategy

**Recommended approach (two-phase):**

**Phase 1 (immediate safety):** Add error logging to [`persist_changes`](../sensei-rs/crates/sensei-api/src/db_stores.rs#L315-L372) calls and change `Drop` to use [`tokio::runtime::Handle::block_on`](https://docs.rs/tokio/latest/tokio/runtime/struct.Handle.html#method.block_on) with `spawn_blocking` for synchronous persistence, or at minimum log errors from the spawned task.

**Phase 2 (architectural):** Add an explicit [`StoreWriteGuard::commit()`](../sensei-rs/crates/sensei-api/src/db_stores.rs#L193-L214) method that returns `Result<(), DbError>`. The `Drop` impl becomes a fallback that logs a warning if `commit()` was not called. Update all route handlers to call `.commit().await?` after mutations.

```rust
impl<T: Serialize + DeserializeOwned + Clone + Send + Sync + 'static>
    StoreWriteGuard<'_, T>
{
    /// Explicitly persist changes to database. Returns error on failure.
    pub async fn commit(&self) -> Result<(), sqlx::Error> {
        let pool = self.inner.pool.as_ref().ok_or_else(|| {
            sqlx::Error::Protocol("No database pool configured".into())
        })?;
        let entity_type = &self.inner.entity_type;
        let snapshot = self.inner.data.read().unwrap().clone();
        persist_changes(pool, entity_type, &snapshot).await
    }
}
```

#### Dependencies

- **Blocked by:** P0-A1 (table must exist before persistence works)
- **Blocks:** Nothing directly, but ALL write operations remain unreliable until fixed
- **Risk:** Medium. Changing `Drop` behavior could cause deadlocks if not done carefully. Recommend `block_on` with a timeout.

---

### P0-D1: Zero Domain Events Published from PM Route Handlers → Dead Notification System

- **Source:** [`sensei-rs/crates/sensei-core/src/domain/events.rs`](../sensei-rs/crates/sensei-core/src/domain/events.rs) (3193 lines — 41+ events, ZERO for PM)
- **Analysis ref:** [`taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md#L499-L520)

#### Problem Statement

The codebase defines 41+ domain events in [`events.rs`](../sensei-rs/crates/sensei-core/src/domain/events.rs) across quality, production, finance, HR, and supply chain domains. But **zero** domain events are defined or published for the PM subsystem: no `KanbanCardMovedEvent`, `TaskStatusChangedEvent`, `ObeyaItemUpdatedEvent`, `StateMachineTransitionedEvent`, `SavedViewCreatedEvent`, or similar. Route handlers in [`kanban.rs`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs), [`tasks.rs`](../sensei-rs/crates/sensei-api/src/routes/tasks.rs), [`obeya.rs`](../sensei-rs/crates/sensei-api/src/routes/obeya.rs), [`state_machines.rs`](../sensei-rs/crates/sensei-api/src/routes/state_machines.rs) never access the event bus from [`AppState`](../sensei-rs/crates/sensei-api/src/state.rs#L68-L234). The [`NotificationTrigger`](../sensei-rs/crates/sensei-api/src/stores.rs#L855-L870) infrastructure (7 endpoints, conditions, actions, channels, cooldown) exists at [`notification_triggers.rs`](../sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs) but is completely disconnected — no code ever publishes events that would trigger notifications.

Wait — I need to correct this. Checking [`events.rs`](../sensei-rs/crates/sensei-core/src/domain/events.rs) more carefully:

There **are** some PM-like events defined:

| Event | Line | Used? |
|-------|------|-------|
| [`KanbanCardMovedEvent`](../sensei-rs/crates/sensei-core/src/domain/events.rs#L2442-L2461) | 2442 | **Never published** — no route handler fires it |
| [`ProjectCreatedEvent`](../sensei-rs/crates/sensei-core/src/domain/events.rs#L2504-L2521) | 2504 | **Never published** |
| [`SprintCompletedEvent`](../sensei-rs/crates/sensei-core/src/domain/events.rs#L2568-L2585) | 2568 | **Never published** |
| [`IssueCreatedEvent`](../sensei-rs/crates/sensei-core/src/domain/events.rs#L2632-L2649) | 2632 | **Never published** |
| [`A3CreatedEvent`](../sensei-rs/crates/sensei-core/src/domain/events.rs#L2696-L2713) | 2696 | **Possibly unused** — a3.rs delegates to ops_service |
| [`A3ClosedEvent`](../sensei-rs/crates/sensei-core/src/domain/events.rs#L2756-L2765) | 2756 | **Possibly unused** |
| [`RiskCreatedEvent`](../sensei-rs/crates/sensei-core/src/domain/events.rs#L2812-L2838) | 2812 | **Possibly unused** |
| [`RiskMitigatedEvent`](../sensei-rs/crates/sensei-core/src/domain/events.rs#L2883-L2898) | 2883 | **Possibly unused** |

**Still missing entirely:** `TaskCreatedEvent`, `TaskStatusChangedEvent`, `TaskAssignedEvent`, `SavedViewCreatedEvent`, `KanbanCardCreatedEvent`, `ObeyaItemCreatedEvent`, `StateMachineInstanceCreatedEvent`, `StateMachineTransitionedEvent`.

#### Before State

```rust
// kanban.rs:268-301 — add_card: no event published
pub async fn add_card(
    State(state): State<AppState>,
    Path((tenant_id, board_id)): Path<(Uuid, Uuid)>,
    Json(req): Json<CardRequest>,
) -> Result<Json<KanbanCard>, AppError> {
    let mut cards = state.kanban_cards.write().await;
    // ... insert logic ...
    // NO event published — no notification, no audit trail, no webhook
    Ok(Json(card))
}

// state.rs:303-309 — event bus wired only to ERP domain services
// PM services NEVER receive event bus:
let ops_service = Arc::new(OpsService::new(storage_service.clone()));
let quality_service = Arc::new(QualityServiceImpl::new(
    storage_service.clone(),
    Some(event_bus.clone()),  // ← Only ERP services get event bus
));
// No PM-equivalent wiring
```

#### After State

```rust
// kanban.rs — After fix
pub async fn add_card(
    State(state): State<AppState>,
    Path((tenant_id, board_id)): Path<(Uuid, Uuid)>,
    Json(req): Json<CardRequest>,
) -> Result<Json<KanbanCard>, AppError> {
    let mut cards = state.kanban_cards.write().await;
    // ... insert logic ...
    
    // Publish domain event
    if let Err(e) = state.event_bus.publish(
        KanbanCardCreatedEvent::new(tenant_id, card.id, board_id, req.column_id)
    ).await {
        tracing::warn!(error = %e, "Failed to publish KanbanCardCreatedEvent");
    }
    
    Ok(Json(card))
}
```

#### Fix Strategy

1. **Define missing domain events** in [`events.rs`](../sensei-rs/crates/sensei-core/src/domain/events.rs):
   - `TaskCreatedEvent`, `TaskStatusChangedEvent`, `TaskAssignedEvent`, `TaskDeletedEvent`
   - `KanbanCardCreatedEvent`, `KanbanCardMovedEvent` (exists but unused), `KanbanCardDeletedEvent`
   - `ObeyaItemCreatedEvent`, `ObeyaItemUpdatedEvent`, `ObeyaItemDeletedEvent`
   - `StateMachineInstanceCreatedEvent`, `StateMachineTransitionedEvent`
   - `SavedViewCreatedEvent`, `SavedViewUpdatedEvent`, `SavedViewDeletedEvent`

2. **Wire event bus to PM route handlers** by adding the `Arc<dyn EventBus>` field to relevant handler structs (or extracting from [`AppState`](../sensei-rs/crates/sensei-api/src/state.rs#L68-L234)).

3. **Publish events** in each mutation endpoint (create, update, delete, status change, assign, move).

4. **Wire NotificationTriggers** to subscribe to PM events by adding PM event types to [`list_event_types`](../sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs#L261-L308).

5. **Fix [`test_trigger`](../sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs#L235-L258)** — Replace hardcoded `condition_matched: true` with actual condition evaluation.

#### Dependencies

- **Blocked by:** Nothing structural, but benefits from P0-A1 (so events can trigger persistence)
- **Blocks:** P2-D2 (notification triggers remain dead until events flow)
- **Risk:** Low. Publishing events is additive and non-blocking (best-effort pattern). Won't break existing functionality.

---

### P0-F1: XSS Vulnerability via `innerHTML` in Legacy Frontend

- **Source:** [`frontend/public/dashboard.html`](../frontend/public/dashboard.html) (1653 lines)
- **Analysis ref:** [`frontend-integration-deep-dive.md`](../docs/analysis/frontend-integration-deep-dive.md#L548-L565)

#### Problem Statement

The legacy frontend SPA in [`dashboard.html`](../frontend/public/dashboard.html) uses `innerHTML` extensively to render API response data directly into the DOM. This includes user-controlled fields like `name`, `description`, `title`, `status`, and `priority`. An attacker who can inject malicious content into any entity field (e.g., via a task description or kanban card title) will achieve XSS when any user views the affected section. Multiple rendering functions are affected.

#### Vulnerable Locations

| Line | Function | Code |
|------|----------|------|
| 994 | `badge()` | `return '<span class="badge ' + cls + '">' + status + '</span>'` |
| 1005-1009 | `renderTable()` | `'<td>' + (val ?? '—') + '</td>'` — raw interpolation |
| 1016-1019 | `renderCards()` | `'<div class="card">...' + item.title + ...` |
| 1023 | `renderCards()` | `item.description` interpolated |
| 1027 | `renderCards()` | `item.priority` interpolated |
| 1140 | `renderObjectSection()` | `'<span class="obj-section-value...">' + (val ?? '—') + '</span>'` |

#### Fix Strategy

1. **Replace `innerHTML` with `textContent`** in all rendering functions. Since the legacy SPA renders plain text (no rich HTML needed), `textContent` is the correct choice:

```javascript
// Before (line 994)
function badge(status, type) {
    let cls = type === 'priority' ? 'badge-' + (status || 'none').toLowerCase() : 'badge-info';
    return '<span class="badge ' + cls + '">' + status + '</span>';
}

// After
function badge(status, type) {
    let cls = type === 'priority' ? 'badge-' + (status || 'none').toLowerCase() : 'badge-info';
    let span = document.createElement('span');
    span.className = 'badge ' + cls;
    span.textContent = status ?? '—';
    return span.outerHTML;
}
```

2. **Replace `innerHTML` assignments** with DOM API methods (`createElement`, `textContent`, `appendChild`), or use `insertAdjacentHTML` only with trusted template strings (no data interpolation).

3. **Add Content-Security-Policy header** via [`router.rs`](../sensei-rs/crates/sensei-api/src/router.rs) middleware to restrict script sources.

4. **Add input sanitization** on the backend for any user-submitted content (defense in depth).

5. **Move auth tokens** from [`localStorage`](../frontend/public/dashboard.html#L939) to `sessionStorage` or HTTP-only cookies (reduces XSS impact).

#### Dependencies

- **Blocked by:** Nothing
- **Blocks:** Nothing
- **Risk:** Low. The changes are mechanical (string concatenation → DOM API). High-value security fix.

---

## 3. P1 — High Priority

### P1-B1: WIP Limits Stored but Never Enforced

- **Source:** [`sensei-rs/crates/sensei-api/src/routes/kanban.rs`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L268-L301, L384-L414)
- **Entity model:** [`KanbanColumn.wip_limit`](../sensei-rs/crates/sensei-api/src/stores.rs#L36-L45)
- **Analysis ref:** [`taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md#L147-L224)

#### Problem Statement

[`KanbanColumn`](../sensei-rs/crates/sensei-api/src/stores.rs#L36-L45) has a `wip_limit: Option<i32>` field. The [`get_kanban_metrics`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L419-L507) endpoint reports `wip_limit_breached: true` when column card count exceeds `wip_limit`. However, neither [`add_card`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L268-L301) nor [`move_card`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L384-L414) checks the WIP limit before allowing the operation. Cards can be added to or moved into columns beyond their configured limit without any rejection or warning.

#### Before State

```rust
// kanban.rs:268-301 — add_card: no WIP check
pub async fn add_card(...) -> Result<Json<KanbanCard>, AppError> {
    let mut cards = state.kanban_cards.write().await;
    let columns = state.kanban_columns.read().await;
    // ... validate board_id, generate UUID, insert card ...
    // NO check: wip_limit vs current card count in target column
    Ok(Json(card))
}

// kanban.rs:384-414 — move_card: no WIP check
pub async fn move_card(...) -> Result<Json<KanbanCard>, AppError> {
    let mut cards = state.kanban_cards.write().await;
    // ... find card, update column_id, position ...
    // NO check: wip_limit on destination column
    Ok(Json(card))
}
```

#### After State

```rust
// kanban.rs — add_card with WIP enforcement
pub async fn add_card(...) -> Result<Json<KanbanCard>, AppError> {
    let mut cards = state.kanban_cards.write().await;
    let columns = state.kanban_columns.read().await;
    
    // Find target column and check WIP limit
    let column = columns.values()
        .find(|c| c.board_id == board_id && c.id == req.column_id)
        .ok_or(AppError::NotFound("Column not found".into()))?;
    
    if let Some(wip_limit) = column.wip_limit {
        let current_count = cards.values()
            .filter(|c| c.column_id == req.column_id)
            .count() as i32;
        if current_count >= wip_limit {
            return Err(AppError::Conflict(format!(
                "Column '{}' has reached its WIP limit of {}", column.name, wip_limit
            )));
        }
    }
    
    // ... insert card ...
    Ok(Json(card))
}
```

#### Fix Strategy

1. Add WIP-limit check in [`add_card`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L268-L301) — count current cards in target column before inserting
2. Add WIP-limit check in [`move_card`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L384-L414) — count current cards in **destination** column before moving
3. Return `409 Conflict` with a descriptive message when WIP limit is exceeded
4. Optionally add a `?bypass_wip=true` query parameter for managers/override scenarios

#### Dependencies

- **Blocked by:** Nothing
- **Blocks:** Nothing directly; this is an additive enforcement
- **Risk:** Low. Could break API clients that expect to exceed WIP limits (currently allowed). Make opt-in initially via a feature flag.

---

### P1-C1: State Machine `transition_instance` Ignores Conditions, Roles, and Hooks

- **Source:** [`sensei-rs/crates/sensei-api/src/routes/state_machines.rs`](../sensei-rs/crates/sensei-api/src/routes/state_machines.rs#L310-L373)
- **Entity model:** [`TransitionDefinition`](../sensei-rs/crates/sensei-api/src/stores.rs#L966-L972), [`StateDefinition`](../sensei-rs/crates/sensei-api/src/stores.rs#L957-L962)
- **Analysis ref:** [`taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md#L352-L407)

#### Problem Statement

[`transition_instance`](../sensei-rs/crates/sensei-api/src/routes/state_machines.rs#L310-L373) implements basic state machine transitions: it finds a [`TransitionDefinition`](../sensei-rs/crates/sensei-api/src/stores.rs#L966-L972) matching `(from_state, event)`, validates it exists, and updates the instance's `current_state`. However, it completely ignores:

1. **`conditions: Option<serde_json::Value>`** — Transition guard conditions are stored but never evaluated
2. **`allowed_roles: Option<Vec<String>>`** — Role-based access control for transitions is stored but never checked
3. **`on_transition: Option<Vec<String>>`** — Side-effect hooks are stored but never executed
4. **`on_entry_actions` / `on_exit_actions`** (on `StateDefinition`) — Actions are stored but never executed
5. **No event published** — No `StateMachineTransitionedEvent` or similar is emitted

```rust
// state_machines.rs:336-372 — Current transition logic
match transition {
    Some(t) => {
        // Only checks: does transition exist?
        // Missing: conditions evaluation
        // Missing: allowed_roles check
        // Missing: on_transition hook execution
        // Missing: event publishing
        instance.current_state = t.to_state.clone();
    }
    None => {
        return Err(AppError::Validation(format!(
            "No valid transition from '{}' with event '{}'",
            instance.current_state, req.event
        )));
    }
}
```

#### Fix Strategy

1. **Evaluate `conditions`**: Parse [`TransitionDefinition.conditions`](../sensei-rs/crates/sensei-api/src/stores.rs#L966-L972) JSON and check predicates against the instance's `context` data. Start with a simple expression evaluator (or use a library like [`json-predicate`](https://crates.io/crates/json-predicate)).

2. **Evaluate `allowed_roles`**: Extract the current user's roles from the request context (via auth middleware) and intersect with `allowed_roles`. Return `403 Forbidden` if not authorized.

3. **Execute `on_transition` hooks**: Parse the hook identifiers and dispatch to registered handler functions (or at minimum log them for audit).

4. **Execute lifecycle actions**: Run `on_exit_actions` from the current state's definition, then `on_entry_actions` on the new state.

5. **Publish `StateMachineTransitionedEvent`**: Emit event with tenant_id, instance_id, from_state, to_state, event, and user_id.

```rust
// After: Complete transition evaluation
pub async fn transition_instance(
    State(state): State<AppState>,
    Path((_tenant_id, instance_id)): Path<(Uuid, Uuid)>,
    Json(req): Json<TransitionRequest>,
) -> Result<Json<TransitionResult>, AppError> {
    let sm_defs = state.state_machine_definitions.read().await;
    let mut instances = state.state_machine_instances.write().await;
    
    let instance = instances.get_mut(&instance_id)
        .ok_or(AppError::NotFound("Instance not found".into()))?;
    
    let def = sm_defs.get(&instance.definition_id)
        .ok_or(AppError::NotFound("Definition not found".into()))?;
    
    let transition = def.transitions.iter()
        .find(|t| t.from_state == instance.current_state && t.event == req.event)
        .ok_or(AppError::Validation(format!("No transition from '{}' via '{}'", 
            instance.current_state, req.event)))?;
    
    // 1. Evaluate conditions
    if let Some(ref conditions) = transition.conditions {
        if !evaluate_conditions(conditions, &instance.context) {
            return Err(AppError::Validation("Transition conditions not met".into()));
        }
    }
    
    // 2. Check allowed roles
    if let Some(ref allowed) = transition.allowed_roles {
        let user_roles = extract_user_roles(&req); // from auth context
        if !allowed.iter().any(|r| user_roles.contains(r)) {
            return Err(AppError::Forbidden("User role not authorized for this transition".into()));
        }
    }
    
    // 3. Execute on_exit_actions (from current state definition)
    if let Some(current_def) = def.states.iter().find(|s| s.name == instance.current_state) {
        if let Some(ref actions) = current_def.on_exit_actions {
            execute_actions(actions, &instance).await;
        }
    }
    
    // 4. Perform transition
    let from_state = instance.current_state.clone();
    instance.current_state = transition.to_state.clone();
    
    // 5. Execute on_entry_actions (on new state)
    if let Some(new_def) = def.states.iter().find(|s| s.name == instance.current_state) {
        if let Some(ref actions) = new_def.on_entry_actions {
            execute_actions(actions, &instance).await;
        }
    }
    
    // 6. Execute on_transition hooks
    if let Some(ref hooks) = transition.on_transition {
        execute_hooks(hooks, &instance, &from_state, &req.event).await;
    }
    
    // 7. Publish event
    let _ = state.event_bus.publish(
        StateMachineTransitionedEvent::new(
            instance.tenant_id, instance_id, from_state,
            instance.current_state.clone(), req.event
        )
    ).await;
    
    Ok(Json(TransitionResult { 
        success: true, 
        new_state: instance.current_state.clone(),
        from_state,
        event: req.event,
    }))
}
```

#### Dependencies

- **Blocked by:** P0-D1 (event bus integration for publishing transition events)
- **Blocks:** P1-C2 (task status without SM enforcement is meaningless if SM is broken)
- **Risk:** High. This is the most architecturally significant fix. Requires careful design of the conditions evaluator and hook dispatcher. Recommend implementing in phases: (1) conditions + roles, (2) hooks, (3) events.

---

### P1-C2: Task Status Updates Bypass State Machine Entirely

- **Source:** [`sensei-rs/crates/sensei-api/src/routes/tasks.rs`](../sensei-rs/crates/sensei-api/src/routes/tasks.rs#L262-L278)
- **Analysis ref:** [`taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md#L306-L319)

#### Problem Statement

[`update_task_status`](../sensei-rs/crates/sensei-api/src/routes/tasks.rs#L262-L278) performs a raw string assignment: `task.status = req.status;` with zero validation. There is no lookup against any [`StateMachineDefinition`](../sensei-rs/crates/sensei-api/src/stores.rs#L976-L989) to verify the transition is valid. This means a task can go from "Done" to "In Progress" or from "New" directly to "Archived" — transitions that a proper state machine would reject. The state machine infrastructure exists (definitions, transitions, conditions, roles) but is completely disconnected from the task workflow.

#### Before State

```rust
// tasks.rs:262-278
pub async fn update_task_status(
    State(state): State<AppState>,
    Path((_tenant_id, task_id)): Path<(Uuid, Uuid)>,
    Json(req): Json<UpdateTaskStatusRequest>,
) -> Result<Json<Task>, AppError> {
    let mut tasks = state.tasks.write().await;
    let task = tasks.get_mut(&task_id)
        .ok_or(AppError::NotFound("Task not found".into()))?;
    
    task.status = req.status;  // ← Pure string assignment, no validation!
    
    Ok(Json(task.clone()))
}
```

#### After State

```rust
// tasks.rs — After: State machine integration
pub async fn update_task_status(
    State(state): State<AppState>,
    Path((tenant_id, task_id)): Path<(Uuid, Uuid)>,
    Json(req): Json<UpdateTaskStatusRequest>,
) -> Result<Json<Task>, AppError> {
    let mut tasks = state.tasks.write().await;
    // Find the task's assigned state machine definition
    let defs = state.state_machine_definitions.read().await;
    let mut instances = state.state_machine_instances.write().await;
    
    let task = tasks.get_mut(&task_id)
        .ok_or(AppError::NotFound("Task not found".into()))?;
    
    // Use a task-specific state machine (e.g., "task_status" or task_type-based)
    let sm_def = defs.values()
        .find(|d| d.name == "task_status" && d.tenant_id == tenant_id)
        .ok_or(AppError::Validation("No state machine configured for tasks".into()))?;
    
    // Find or create state machine instance for this task
    let instance = instances.values_mut()
        .find(|i| i.definition_id == sm_def.id && i.entity_id == Some(task_id))
        .ok_or(AppError::Validation(format!(
            "No state machine instance for task {}", task_id
        )))?;
    
    // Validate transition via state machine
    let transition = sm_def.transitions.iter()
        .find(|t| t.from_state == instance.current_state && t.event == req.event)
        .ok_or(AppError::Validation(format!(
            "Cannot transition task from '{}' via '{}'",
            instance.current_state, req.event
        )))?;
    
    // Apply transition
    task.status = transition.to_state.clone();
    instance.current_state = transition.to_state.clone();
    
    Ok(Json(task.clone()))
}
```

#### Fix Strategy

1. Find or create a [`StateMachineInstance`](../sensei-rs/crates/sensei-api/src/stores.rs#L993-L1003) for the task, linked by `entity_id = Some(task_id)`
2. Find a [`StateMachineDefinition`](../sensei-rs/crates/sensei-api/src/stores.rs#L976-L989) named `"task_status"` (or configured per tenant/project)
3. Validate the requested status change against the state machine's [`TransitionDefinition`](../sensei-rs/crates/sensei-api/src/stores.rs#L966-L972)
4. Apply the validated `to_state` to `task.status`
5. Create tasks with an initial state machine instance when [`create_task`](../sensei-rs/crates/sensei-api/src/routes/tasks.rs#L141-L175) is called
6. Backfill: add a migration to create default "task_status" state machine definitions per tenant

#### Dependencies

- **Blocked by:** P1-C1 (SM must work correctly before tasks can depend on it)
- **Blocks:** Nothing
- **Risk:** High. This changes the fundamental contract of `update_task_status`. Must be introduced with a migration path: (1) create default SM definitions, (2) add SM instances to existing tasks, (3) enable enforcement with a feature flag.

---

### P1-E1: Search Only Indexes 4 of 50+ Entity Types

- **Source:** [`sensei-rs/crates/sensei-api/src/state.rs`](../sensei-rs/crates/sensei-api/src/state.rs#L303-L309), [`sensei-rs/crates/sensei-api/src/routes/search.rs`](../sensei-rs/crates/sensei-api/src/routes/search.rs#L36-L57)
- **Analysis ref:** [`saved-views-and-search-deep-dive.md`](../docs/analysis/saved-views-and-search-deep-dive.md#L129-L153)

#### Problem Statement

The search service is seeded with only 4 entity services in [`AppState::new()`](../sensei-rs/crates/sensei-api/src/state.rs#L303-L309): `accounts_service`, `contacts_service`, `products_service`, and `users_service`. None of the PM entities (Tasks, KanbanCards, ObeyaItems, etc.) are registered for search. The [`search`](../sensei-rs/crates/sensei-api/src/routes/search.rs#L36-L57) endpoint returns results from only these 4 types, making it nearly useless for PM workflows.

```rust
// state.rs:303-309
let search_service = Arc::new(InMemorySearchService::new(vec![
    accounts_service.clone() as Arc<dyn SearchableService>,
    contacts_service.clone() as Arc<dyn SearchableService>,
    products_service.clone() as Arc<dyn SearchableService>,
    users_service.clone() as Arc<dyn SearchableService>,
]));
```

#### Fix Strategy

1. Implement [`SearchableService`](https://docs.rs/) trait for PM entity stores: `TaskStore`, `KanbanCardStore`, `KanbanBoardStore`, `ObeyaBoardStore`, `ObeyaItemStore`, `A3Store`, etc.
2. Register each new searchable service in the `InMemorySearchService` constructor call in [`AppState::new()`](../sensei-rs/crates/sensei-api/src/state.rs#L242-L390) and [`with_db_pool()`](../sensei-rs/crates/sensei-api/src/state.rs#L399-L489).
3. Add entity-type filter parameter to [`SearchParams`](../sensei-rs/crates/sensei-api/src/routes/search.rs#L18-L23) so clients can scope results.
4. Add proper pagination (offset/limit) instead of the current cap parameter.
5. Extend search indexing for DB-backed mode with PostgreSQL full-text search (`tsvector` columns or `pg_trgm` trigram search).

#### Dependencies

- **Blocked by:** Nothing structural
- **Blocks:** P2-E1 (entity-type filter is more useful after PM entities are indexed)
- **Risk:** Low. Adding more searchable types is additive.

---

### P1-E2: Saved Views Lack Sharing, RBAC, Compound Sorting, Typed Filters

- **Source:** [`sensei-rs/crates/sensei-api/src/routes/saved_views.rs`](../sensei-rs/crates/sensei-api/src/routes/saved_views.rs) (176 lines)
- **Entity model:** [`SavedView`](../sensei-rs/crates/sensei-api/src/stores.rs#L612-L625)
- **Analysis ref:** [`saved-views-and-search-deep-dive.md`](../docs/analysis/saved-views-and-search-deep-dive.md#L24-L103)

#### Problem Statement

The [`SavedView`](../sensei-rs/crates/sensei-api/src/stores.rs#L612-L625) entity supports `tenant_id`, `user_id`, `name`, `entity_type: String`, `filters: serde_json::Value`, `sort_by: Option<String>`, `sort_order: Option<String>`, and `is_default: bool`. The implementation is private-only (scoped by `user_id`), with no sharing mechanism, no RBAC, single-column sorting only, and untyped JSON blob filters. Compared to the Python/SQLAlchemy reference model which has segments, shared views, role-based visibility, compound sorting, and typed filter predicates, this is minimal.

#### Fix Strategy

1. **Add visibility/sharing**: Add `visibility: enum { Private, Shared, Team, Public }` field to [`SavedView`](../sensei-rs/crates/sensei-api/src/stores.rs#L612-L625). Update [`list_saved_views`](../sensei-rs/crates/sensei-api/src/routes/saved_views.rs#L34-L48) to respect visibility when filtering.
2. **Add compound sorting**: Replace `sort_by: Option<String>` with `sort_columns: Vec<SortColumn>` where each `SortColumn` has `field: String` and `direction: enum { Asc, Desc }`.
3. **Add typed filter schemas**: Define per-entity-type filter schemas (e.g., `TaskFilter`, `KanbanCardFilter`) instead of using untyped `serde_json::Value`.
4. **Add role-based access control**: Check user roles before returning shared views (e.g., `Team` visibility requires team membership).
5. **Add view count and analytics**: Track view usage for popular/default view suggestions.
6. **Extend the API**: Add endpoints for sharing, cloning, and bulk operations on saved views.

#### Dependencies

- **Blocked by:** Nothing
- **Blocks:** P3-E1 (compound sorting is a prerequisite for proper pagination UI)
- **Risk:** Medium. Changing the `SavedView` struct and its database schema requires a migration. The `filters` field change from untyped JSONB to typed schemas is particularly impactful.

---

### P1-F1: Frontend Is Entirely Read-Only — No CRUD UI

- **Source:** [`frontend/public/dashboard.html`](../frontend/public/dashboard.html) — all sections
- **Analysis ref:** [`frontend-integration-deep-dive.md`](../docs/analysis/frontend-integration-deep-dive.md)

#### Problem Statement

All views in the legacy SPA are read-only tables and card grids. There are no "Create", "Edit", "Delete" buttons, no forms, no modals, no drag-and-drop for kanban cards, no filter controls, and no detail views. The API exists for all CRUD operations (confirmed by [`router.rs`](../sensei-rs/crates/sensei-api/src/router.rs) showing 200+ routes), but the frontend only calls `GET` endpoints and renders the results.

#### Section-by-Section Coverage Gap

| Section | API Endpoints Available | Frontend Covers |
|---------|------------------------|-----------------|
| Tasks | 8 (list, create, get, update, delete, status, assign, stats) | `GET /tasks` only |
| Kanban | 13 (boards/columns/cards CRUD, move, metrics) | `GET /boards` only |
| Obeya | 8 (boards/items CRUD) | `GET /boards` only |
| Today | 1 (GET snapshot) | `GET /today` |
| A3 | 5 (list, create, get, update, close) | None |
| State Machines | 7+ (definitions, instances, transition) | None |
| Saved Views | 5 (list, create, get, update, delete) | None |
| Search | 1 (GET search) | None |
| Notifications | 7 (list, create, get, update, delete, toggle, test, event types) | None |

#### Fix Strategy

1. **Add modal system** to [`dashboard.html`](../frontend/public/dashboard.html) for create/edit forms (reuse pattern for all sections).
2. **Implement CRUD for Tasks first** (highest priority PM feature):
   - Add Task form with title, description, status, priority, assignee, due_date
   - Edit/Delete buttons on each table row
   - Inline status update dropdown
3. **Implement Kanban board view** with:
   - Column display (swimlanes)
   - Card rendering in columns
   - Drag-and-drop card movement (HTML5 Drag & Drop API or a lightweight library)
   - Add/Edit/Delete card modals
4. **Add views for remaining sections** (A3, State Machines, Saved Views, Search)
5. **Add client-side filtering** for task lists (by status, priority, assignee)

#### Dependencies

- **Blocked by:** P0-F1 (must fix XSS before adding interactive features)
- **Blocks:** Nothing
- **Risk:** Medium. Large surface area of UI changes. Recommend implementing per-section in priority order: Tasks → Kanban → Obeya → A3 → SM → Saved Views → Search.

---

### P1-F2: Dual Frontend Fragmentation — Legacy SPA + WASM, Neither Complete

- **Source:** [`frontend/public/dashboard.html`](../frontend/public/dashboard.html) (legacy), WASM frontend (separate build)
- **Analysis ref:** [`frontend-integration-deep-dive.md`](../docs/analysis/frontend-integration-deep-dive.md#L566-L697)

#### Problem Statement

The codebase has two frontend implementations: a legacy vanilla JS SPA at [`dashboard.html`](../frontend/public/dashboard.html) (1653 lines) and a WASM Leptos SPA (separate build via [`scripts/build-frontend-wasm.sh`](../scripts/build-frontend-wasm.sh)). Neither covers the other's sections. The legacy SPA covers Tasks, Kanban, Quality, Production views but is read-only. The WASM frontend covers different sections but its current state and coverage are unknown. Neither frontend provides a complete Taiga-like experience.

#### Fix Strategy

1. **Audit WASM frontend** to determine its current state, coverage, and whether it should be the migration target.
2. **Decide on a strategy**: Either (a) migrate the legacy SPA to WASM, (b) enhance the legacy SPA to full functionality, or (c) build a new frontend entirely.
3. **Recommended approach**: Enhance the legacy SPA incrementally (lower risk, immediate value) while continuing WASM development as the long-term replacement. This avoids the "all or nothing" problem where neither frontend is complete.
4. **Create a shared API client** that both frontends can use (or ensure the WASM frontend uses the same API endpoints).

#### Dependencies

- **Blocked by:** P0-F1 (must fix XSS before adding interactive features), P1-F1 (CRUD UI is the main deliverable)
- **Blocks:** Nothing
- **Risk:** High. This is a strategic decision with long-term implications. The recommendation to enhance the legacy SPA is pragmatic but the WASM approach may be the better long-term investment.

---

## 4. P2 — Medium Priority

### P2-A3: String-Enum Degradation in PM Entities

- **Source:** [`sensei-rs/crates/sensei-api/src/stores.rs`](../sensei-rs/crates/sensei-api/src/stores.rs) — multiple structs
- **Analysis ref:** [`data-model-and-stores-deep-dive.md`](../docs/analysis/data-model-and-stores-deep-dive.md#L588-L605)

#### Problem Statement

PM entity types use `String` for fields that should be proper Rust enums:

| Entity | Field | Current Type | Should Be |
|--------|-------|-------------|-----------|
| [`KanbanCard`](../sensei-rs/crates/sensei-api/src/stores.rs#L49-L62) | `priority` | `String` | `enum Priority { Low, Medium, High, Critical }` |
| [`Task`](../sensei-rs/crates/sensei-api/src/stores.rs#L542-L558) | `status` | `String` | `enum TaskStatus` (from state machine) |
| [`Task`](../sensei-rs/crates/sensei-api/src/stores.rs#L542-L558) | `priority` | `String` | `enum Priority` |
| [`ObeyaItem`](../sensei-rs/crates/sensei-api/src/stores.rs#L354-L369) | `item_type` | `String` | `enum ObeyaItemType` |
| [`ObeyaItem`](../sensei-rs/crates/sensei-api/src/stores.rs#L354-L369) | `status` | `String` | `enum ObeyaItemStatus` |
| [`ObeyaItem`](../sensei-rs/crates/sensei-api/src/stores.rs#L354-L369) | `priority` | `String` | `enum Priority` |
| [`ObeyaBoard`](../sensei-rs/crates/sensei-api/src/stores.rs#L337-L350) | `board_type` | `String` | `enum ObeyaBoardType` |
| [`SavedView`](../sensei-rs/crates/sensei-api/src/stores.rs#L612-L625) | `entity_type` | `String` | `enum EntityType` |

In contrast, core domain entities in [`entities.rs`](../sensei-rs/crates/sensei-core/src/domain/entities.rs) properly use enums: [`NcrSeverity`](../sensei-rs/crates/sensei-core/src/domain/entities.rs#L159-L166), [`NcrStatus`](../sensei-rs/crates/sensei-core/src/domain/entities.rs#L170-L183), [`CapaStatus`](../sensei-rs/crates/sensei-core/src/domain/entities.rs#L214-L227), [`WorkOrderStatus`](../sensei-rs/crates/sensei-core/src/domain/entities.rs#L258-L271).

#### Fix Strategy

1. Define shared enum types in `sensei-core` or a shared module (e.g., `Priority`, `TaskStatus`, `ObeyaItemType`, `ObeyaItemStatus`, `ObeyaBoardType`, `EntityType`)
2. Update all struct fields from `String` to the new enum types
3. Implement `Serialize`/`Deserialize` with `#[serde(rename_all = "snake_case")]` for API compatibility
4. Update all route handlers that match/compare these fields
5. Add enum validation in request DTOs (e.g., [`CreateTaskRequest`](../sensei-rs/crates/sensei-api/src/routes/tasks.rs#L33-L42) should accept only valid enum variants)

#### Dependencies

- **Blocked by:** Nothing structural, but if P1-C1 is done first, `TaskStatus` can be derived from state machine definitions
- **Blocks:** P2-A4 (referential integrity checks need stable entity type identifiers)
- **Risk:** Medium. Enum changes affect serialization format. Need careful `#[serde(alias)]` or custom deserialization to maintain backward compatibility with existing data.

---

### P2-A4: Zero Referential Integrity Across UUID Foreign Keys

- **Source:** All entity structs in [`stores.rs`](../sensei-rs/crates/sensei-api/src/stores.rs)
- **Analysis ref:** [`data-model-and-stores-deep-dive.md`](../docs/analysis/data-model-and-stores-deep-dive.md#L416-L448)

#### Problem Statement

Every entity struct uses `Uuid` fields for foreign key references (e.g., `board_id`, `column_id`, `assignee_id`, `tenant_id`). There is no enforcement at any level:

- **No DB foreign keys** (no `REFERENCES` constraints since there are no DDL tables)
- **No application-level validation** in route handlers when reading/writing
- **No orphan detection** when parent entities are deleted
- **No cascade behavior** (deleting a board doesn't delete its columns/cards)

#### Fix Strategy

1. **Add referential validation** to mutation endpoints:
   - `add_card`: verify `board_id` and `column_id` exist
   - `move_card`: verify destination `column_id` exists
   - `assign_task`: verify `assignee_id` is a valid user
   - `create_obeya_item`: verify `board_id` exists
   - etc.

2. **Add cascade delete logic** in delete handlers:
   - `delete_board`: also delete associated columns and cards
   - `delete_task`: also delete associated state machine instance
   - `delete_column`: move or delete associated cards

3. **Add database-level foreign keys** when DDL is generated (e.g., in a future migration):
   ```sql
   ALTER TABLE entity_store
   ADD CONSTRAINT fk_kanban_card_board
   FOREIGN KEY (board_id) REFERENCES entity_store(id)
   WHERE entity_type = 'kanban_board';
   -- Note: JSONB schema makes this impractical without normalization
   ```

#### Dependencies

- **Blocked by:** P0-A1 (DDL), P2-A3 (enum types help with entity type identification)
- **Blocks:** Nothing
- **Risk:** Low for application-level validation. High for DB-level FK constraints due to JSONB schema. Recommend focusing on application-level validation only.

---

### P2-A5: In-Memory Pagination (No SQL LIMIT/OFFSET)

- **Source:** All list endpoints across PM route handlers
- **Analysis ref:** [`data-model-and-stores-deep-dive.md`](../docs/analysis/data-model-and-stores-deep-dive.md#L190-L199)

#### Problem Statement

All list endpoints (e.g., [`list_tasks`](../sensei-rs/crates/sensei-api/src/routes/tasks.rs#L95-L138), [`list_boards`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L96-L111)) work by iterating over the full `HashMap<Uuid, T>` values, applying optional filters in Rust code, and returning the entire result set. There is no `LIMIT`, `OFFSET`, or cursor-based pagination. For DB-backed mode, this means loading ALL rows from the database into memory on every list request.

#### Fix Strategy

1. Add `limit` and `offset` parameters to all list endpoints (with sensible defaults: limit=50, offset=0)
2. Apply pagination **before** or **after** filtering depending on the use case:
   - For filtered queries: apply filter first, then paginate
   - For simple lists: apply `LIMIT/OFFSET` first for performance
3. Return pagination metadata in responses: `{ data: [...], total: N, limit: N, offset: N }`
4. For DB-backed mode, push pagination to SQL queries using `LIMIT ? OFFSET ?`

#### Dependencies

- **Blocked by:** Nothing
- **Blocks:** Nothing
- **Risk:** Low. Pagination is additive and backward-compatible if default values match current behavior (return all).

---

### P2-B2: Naive Cycle Time Calculation (String Matching on Column Names)

- **Source:** [`sensei-rs/crates/sensei-api/src/routes/kanban.rs`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L472)
- **Analysis ref:** [`taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md#L212-L224)

#### Problem Statement

Cycle time calculation in [`get_kanban_metrics`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L419-L507) uses string matching on column names to determine if a card has reached a terminal state:

```rust
// kanban.rs:472
let cycle_times: Vec<_> = cards
    .iter()
    .filter(|(_, c)| {
        let col_name = columns.get(&c.column_id).map(|col| col.name.to_lowercase()).unwrap_or_default();
        col_name_lower.contains("done") || col_name_lower.contains("completed")
    })
    // ...
```

This is fragile: renaming a column from "Done" to "Finished" breaks the calculation. There's no explicit "terminal" or "done" flag on columns.

#### Fix Strategy

1. Add a `is_terminal: bool` field to [`KanbanColumn`](../sensei-rs/crates/sensei-api/src/stores.rs#L36-L45) to explicitly mark columns as terminal/done states
2. Mark columns as terminal in [`add_column`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L193-L220) and [`update_column`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L223-L244)
3. Update [`get_kanban_metrics`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs#L472) to use the `is_terminal` field instead of string matching
4. Add a migration to auto-detect and set `is_terminal = true` for existing columns named "done", "completed", "closed", etc.

#### Dependencies

- **Blocked by:** Nothing
- **Blocks:** Nothing
- **Risk:** Low. Additive field with backward-compatible logic.

---

### P2-D2: Hardcoded Placeholder Zeros in Today Snapshot

- **Source:** [`sensei-rs/crates/sensei-api/src/routes/today.rs`](../sensei-rs/crates/sensei-api/src/routes/today.rs#L122-L124)
- **Analysis ref:** [`taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md)

#### Problem Statement

[`get_today_snapshot`](../sensei-rs/crates/sensei-api/src/routes/today.rs#L58-L175) returns a [`TodaySnapshot`](../sensei-rs/crates/sensei-api/src/routes/today.rs#L19-L24) containing `open_ncrs` and `open_capas` fields that are hardcoded to `0`:

```rust
// today.rs:122-124
let open_ncrs = 0;  // Placeholder – will be integrated when quality_service is extended
let open_capas = 0; // Placeholder – will be integrated when quality_service is extended
```

The method already has access to `state.quality_service` and uses it for other data (line 121: `let quality_service = state.quality_service.clone();`). It should query actual NCR and CAPA counts.

#### Fix Strategy

1. Add methods to the [`QualityService`](https://docs.rs/) trait: `count_open_ncrs(tenant_id) -> i64` and `count_open_capas(tenant_id) -> i64`
2. Implement these methods on [`QualityServiceImpl`](https://docs.rs/) (or whatever concrete implementation is used)
3. Update [`get_today_snapshot`](../sensei-rs/crates/sensei-api/src/routes/today.rs#L122-L124) to call these methods instead of hardcoding zeros

#### Dependencies

- **Blocked by:** Nothing (quality_service already exists and is wired)
- **Blocks:** Nothing
- **Risk:** Low. Replacing placeholders with actual queries.

---

### P2-D3: Notification Triggers Exist but Completely Disconnected

- **Source:** [`sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs`](../sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs)
- **Analysis ref:** [`taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md#L499-L520)

#### Problem Statement

The notification trigger subsystem has full CRUD endpoints, condition/action/channel schemas, event type descriptors, and a test endpoint. However, it is completely disconnected from the event bus:

1. [`list_event_types`](../sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs#L261-L308) lists 10 event types (all from ERP domains: `work_order.status_change`, `quality.defect_recorded`, `andon.raised`, etc.) — **none** are PM-specific
2. No code subscribes [`NotificationTrigger`](../sensei-rs/crates/sensei-api/src/stores.rs#L855-L870) conditions to the event bus
3. [`test_trigger`](../sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs#L235-L258) is a stub that hardcodes `condition_matched: true` instead of evaluating actual conditions

#### Fix Strategy

1. **Wire triggers to the event bus**: Create a background task (or event bus subscriber) that listens to all domain events, evaluates registered [`NotificationTrigger`](../sensei-rs/crates/sensei-api/src/stores.rs#L855-L870) conditions against each event, and executes matching actions (send email, webhook, in-app notification).
2. **Add PM event types** to [`list_event_types`](../sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs#L261-L308): `task.created`, `task.status_changed`, `kanban.card.moved`, `obeya.item.updated`, `state_machine.transitioned`, etc.
3. **Fix [`test_trigger`](../sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs#L235-L258)** to actually evaluate the trigger's condition against a sample event payload.
4. **Implement action execution**: Wire the `action` and `channels` fields to actual notification dispatch (email via [`sensei-services/src/notifications/`](../sensei-rs/crates/sensei-services/src/notifications/), webhook via HTTP client, in-app via SSE/WebSocket).

#### Dependencies

- **Blocked by:** P0-D1 (events must be published before triggers can respond to them)
- **Blocks:** Nothing
- **Risk:** Medium. Requires careful design to avoid performance issues (every event matching against all triggers) and ensure reliable delivery.

---

### P2-E2: Search Lacks Entity-Type Filter, Faceting, and Proper Pagination

- **Source:** [`sensei-rs/crates/sensei-api/src/routes/search.rs`](../sensei-rs/crates/sensei-api/src/routes/search.rs)
- **Analysis ref:** [`saved-views-and-search-deep-dive.md`](../docs/analysis/saved-views-and-search-deep-dive.md#L352-L368)

#### Problem Statement

The [`search`](../sensei-rs/crates/sensei-api/src/routes/search.rs#L36-L57) endpoint only accepts `q` (query string) and `limit` parameters. It has no:

- `entity_type` filter to scope results to a specific entity type
- `offset`/`page` for cursor-based pagination
- Faceted counts (e.g., "10 results in Tasks, 3 results in Kanban")
- Sorting by relevance, date, or any field

#### Fix Strategy

1. Add `entity_type: Option<String>` to [`SearchParams`](../sensei-rs/crates/sensei-api/src/routes/search.rs#L18-L23)
2. Add `offset: Option<i64>` for pagination support
3. Return faceted counts in [`SearchResponse`](../sensei-rs/crates/sensei-api/src/routes/search.rs#L27-L31): `{ results: [...], facets: { tasks: 10, kanban_cards: 3, ... }, total: 13 }`
4. Implement `entity_type` filtering in the [`InMemorySearchService`](https://docs.rs/)
5. For DB-backed mode, push filtering and faceting to SQL via `COUNT(*) ... GROUP BY entity_type`

#### Dependencies

- **Blocked by:** P1-E1 (without PM entities indexed, entity-type filter has little value)
- **Blocks:** Nothing
- **Risk:** Low. Additive changes to the search API.

---

## 5. P3 — Enhancement

### P3-E1: No Compound Sorting in Saved Views

- **Source:** [`SavedView`](../sensei-rs/crates/sensei-api/src/stores.rs#L612-L625)
- **Analysis ref:** [`saved-views-and-search-deep-dive.md`](../docs/analysis/saved-views-and-search-deep-dive.md)

Replace `sort_by: Option<String>` with `sort_columns: Vec<SortColumn>` where each `SortColumn` has `field: String` and `direction: enum { Asc, Desc }`. See P1-E2 for full details.

### P3-F2: No Audit Logging for PM Entity Operations

- **Source:** Router configuration (audit logging middleware exists)
- **Analysis ref:** [`taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md)

The audit logging middleware is configured in [`router.rs`](../sensei-rs/crates/sensei-api/src/router.rs) but the PM route handlers don't produce audit log entries. Add audit logging to all mutation endpoints.

### P3-F3: Frontend Auth Uses localStorage (XSS-Vulnerable Token Storage)

- **Source:** [`frontend/public/dashboard.html`](../frontend/public/dashboard.html#L939)
- **Analysis ref:** [`frontend-integration-deep-dive.md`](../docs/analysis/frontend-integration-deep-dive.md#L548-L565)

Move auth token from `localStorage` to `sessionStorage` (slightly better XSS resistance, lost on tab close) or HTTP-only cookies (best, but requires backend changes). Recommend HTTP-only cookies for production, with a fallback to `sessionStorage` for development.

### P3-F4: No CSP Headers in Frontend

- **Source:** [`router.rs`](../sensei-rs/crates/sensei-api/src/router.rs)
- **Analysis ref:** [`frontend-integration-deep-dive.md`](../docs/analysis/frontend-integration-deep-dive.md#L548-L565)

Add Content-Security-Policy header via `secure_headers` middleware or custom layer in [`router.rs`](../sensei-rs/crates/sensei-api/src/router.rs). Recommended policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'` (unsafe-inline needed for legacy SPA's inline styles).

### P3-F5: WASM Frontend Audit and Migration Decision

Audit the WASM Leptos frontend to determine its current state and decide on the migration path (see P1-F2).

---

## 6. Parallelization Strategy

### Track Assignments

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PARALLELIZATION MAP                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Track A (Data Layer)         Track B (Kanban+Obeya)                │
│  ┌─────────────────┐         ┌─────────────────┐                   │
│  │ P0-A1: DDL       │         │ P1-B1: WIP enforce │               │
│  │ P0-A2: Drop-persist│        │ P2-B2: cycle time  │               │
│  │ P2-A3: Enums      │         │ P2-A4: ref. integ. │               │
│  │ P2-A5: Pagination │         └─────────────────┘                   │
│  └─────────────────┘                                                │
│                                                                     │
│  Track C (Tasks+SM)           Track D (Today+A3+Notif)              │
│  ┌─────────────────┐         ┌─────────────────┐                   │
│  │ P1-C1: SM eval   │         │ P0-D1: Events     │                  │
│  │ P1-C2: Task+SM   │         │ P2-D2: Today zeros │                 │
│  └─────────────────┘         │ P2-D3: Notif conn  │                 │
│                               └─────────────────┘                   │
│                                                                     │
│  Track E (Search+Views)       Track F (Frontend)                    │
│  ┌─────────────────┐         ┌─────────────────┐                   │
│  │ P1-E1: Search idx│         │ P0-F1: XSS        │                  │
│  │ P1-E2: SV enrich│         │ P1-F1: CRUD UI     │                  │
│  │ P2-E2: Search pg │         │ P1-F2: Fragmentation │               │
│  │ P3-E1: Comp sort │         │ P3-F2..F5: Polish  │                 │
│  └─────────────────┘         └─────────────────┘                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Execution Order Per Track

**Track A — Data Layer**
1. P0-A1: Add `entity_store` DDL (the foundation)
2. P0-A2: Fix drop-persist anti-pattern (data safety)
3. P2-A3: String-to-enum migration (can be parallel with A4, A5)
4. P2-A4: Add referential integrity checks
5. P2-A5: Add pagination to list endpoints

**Track B — Kanban + Obeya**
1. P1-B1: Add WIP limit enforcement to add_card and move_card
2. P2-B2: Add `is_terminal` flag to KanbanColumn, fix cycle time calc
3. P2-A4 (shared): Add referential integrity for board/column/card FK chains

**Track C — Tasks + State Machines**
1. P1-C1: Implement full transition evaluation (conditions, roles, hooks, events)
2. P1-C2: Integrate task status updates with state machine

**Track D — Today + A3 + Notifications**
1. P0-D1: Define and publish PM domain events (foundation for all notification work)
2. P2-D2: Replace hardcoded zeros in Today snapshot with real queries
3. P2-D3: Wire notification triggers to event bus subscriber

**Track E — Search + Saved Views**
1. P1-E1: Index PM entities in search service
2. P1-E2: Enrich Saved Views (visibility, compound sorting, typed filters)
3. P2-E2: Add entity-type filter, faceting, pagination to search
4. P3-E1: Compound sorting for Saved Views (can be part of P1-E2)

**Track F — Frontend**
1. P0-F1: Fix XSS (replace all innerHTML with DOM API)
2. P1-F1: Implement CRUD UI (Task first, then Kanban, then others)
3. P1-F2: Audit WASM frontend, decide migration path
4. P3-F2: Add audit logging UI
5. P3-F3: Move auth to HTTP-only cookies
6. P3-F4: Add CSP headers

---

## 7. Dependency Graph

```
P0-A1 (DDL)
  └── P0-A2 (Drop-persist fix)
  
P0-D1 (PM events)
  ├── P1-C1 (SM evaluation) — needs events for transition publishing
  ├── P2-D3 (Notification wiring) — needs events to trigger on
  └── P2-D2 (Today zeros) — independent, but uses same quality_service

P1-C1 (SM evaluation)
  └── P1-C2 (Task+SM integration) — needs working SM first

P1-E1 (Search indexing)
  └── P2-E2 (Search pagination/filtering) — needs more entities indexed

P1-E2 (Saved Views enrichment)
  └── P3-E1 (Compound sorting) — can be rolled into P1-E2

P0-F1 (XSS fix)
  └── P1-F1 (CRUD UI) — must fix XSS before adding interactive forms

P1-F1 (CRUD UI)
  └── P1-F2 (Frontend fragmentation) — need to understand what exists

Independent (can start immediately):
  P2-A3 (String enums)
  P2-A4 (Referential integrity)
  P2-A5 (Pagination)
  P2-B2 (Cycle time fix)
  P3-F3 (Auth token migration)
  P3-F4 (CSP headers)
```

### Critical Path

The shortest path to a functional Taiga-like PM system:

```
P0-A1 → P0-A2 → (Track A completes)
P0-D1 → P1-C1 → P1-C2 (Tasks become state-machine governed)
P0-F1 → P1-F1 (Frontend becomes interactive)
P1-E1 → P1-E2 (Search and views become useful)
```

These 8 fixes (4 P0 + 4 P1) are the minimum to go from "non-functional prototype" to "usable PM system".

---

## 8. Risk Assessment

| Fix | Risk Level | Mitigation |
|-----|-----------|------------|
| P0-A1: DDL | Low | Idempotent DDL, verified by migration check |
| P0-A2: Drop-persist | Medium | Two-phase: log first, restructure later |
| P0-D1: Events | Low | Best-effort publish, won't break existing flows |
| P0-F1: XSS | Low | Mechanical replacement, easy to test |
| P1-B1: WIP enforce | Low | Additive with feature flag |
| P1-C1: SM eval | **High** | Most complex; phase implementation |
| P1-C2: Task+SM | **High** | Changes task update contract; migration needed |
| P1-E1: Search idx | Low | Additive |
| P1-E2: SV enrich | Medium | Schema migration needed |
| P1-F1: CRUD UI | Medium | Large surface area; implement per-section |
| P1-F2: Fragmentation | **High** | Strategic decision; audit-first approach |
| P2-A3: Enums | Medium | Serialization compatibility |
| P2-A4: Ref integrity | Low | App-level validation only |
| P2-A5: Pagination | Low | Additive with defaults |
| P2-B2: Cycle time | Low | Additive field |
| P2-D2: Today zeros | Low | Simple query integration |
| P2-D3: Notif wiring | Medium | Performance: event-trigger matching |
| P2-E2: Search pg | Low | Additive API params |

---

## 9. File Reference Index

### Core Infrastructure

| File | Purpose | Key Lines |
|------|---------|-----------|
| [`sensei-rs/crates/sensei-api/src/db_stores.rs`](../sensei-rs/crates/sensei-api/src/db_stores.rs) | Generic EntityStore persistence layer | L75-85 (struct), L216-239 (Drop), L246-309 (load), L315-372 (persist) |
| [`sensei-rs/crates/sensei-api/src/stores.rs`](../sensei-rs/crates/sensei-api/src/stores.rs) | All 52+ entity type definitions | L23-1085 (all structs) |
| [`sensei-rs/crates/sensei-api/src/state.rs`](../sensei-rs/crates/sensei-api/src/state.rs) | AppState with all stores and services | L68-234 (struct), L242-390 (new), L399-489 (with_db_pool) |
| [`sensei-rs/crates/sensei-api/src/router.rs`](../sensei-rs/crates/sensei-api/src/router.rs) | Complete route definitions (200+ routes) | L718-1143 (build_router) |
| [`sensei-rs/crates/sensei-core/src/domain/events.rs`](../sensei-rs/crates/sensei-core/src/domain/events.rs) | 41+ domain event definitions | L1-3193 (all events) |
| [`sensei-rs/crates/sensei-core/src/domain/entities.rs`](../sensei-rs/crates/sensei-core/src/domain/entities.rs) | Core domain entities with proper enums | L1-464 (User, NCR, CAPA, etc.) |
| [`postgres-init/01-init.sql`](../postgres-init/01-init.sql) | Database initialization | L1-28 (NO entity_store table!) |
| [`sensei-rs/crates/sensei-db/src/migrations.rs`](../sensei-rs/crates/sensei-db/src/migrations.rs) | Database migrations | L1-? (add entity_store check) |

### Route Handlers

| File | Endpoints | Issues |
|------|-----------|--------|
| [`sensei-rs/crates/sensei-api/src/routes/kanban.rs`](../sensei-rs/crates/sensei-api/src/routes/kanban.rs) | 13 Kanban endpoints | No WIP enforcement, no events, naive cycle time |
| [`sensei-rs/crates/sensei-api/src/routes/obeya.rs`](../sensei-rs/crates/sensei-api/src/routes/obeya.rs) | 8 Obeya endpoints | No events, string enums |
| [`sensei-rs/crates/sensei-api/src/routes/tasks.rs`](../sensei-rs/crates/sensei-api/src/routes/tasks.rs) | 8 Task endpoints | No SM integration, no events |
| [`sensei-rs/crates/sensei-api/src/routes/state_machines.rs`](../sensei-rs/crates/sensei-api/src/routes/state_machines.rs) | 7+ SM endpoints | No conditions/roles/hooks evaluation |
| [`sensei-rs/crates/sensei-api/src/routes/today.rs`](../sensei-rs/crates/sensei-api/src/routes/today.rs) | 1 Today endpoint | Hardcoded zeros |
| [`sensei-rs/crates/sensei-api/src/routes/a3.rs`](../sensei-rs/crates/sensei-api/src/routes/a3.rs) | 5 A3 endpoints | Well-structured, no events |
| [`sensei-rs/crates/sensei-api/src/routes/search.rs`](../sensei-rs/crates/sensei-api/src/routes/search.rs) | 1 Search endpoint | Only 4 entity types indexed |
| [`sensei-rs/crates/sensei-api/src/routes/saved_views.rs`](../sensei-rs/crates/sensei-api/src/routes/saved_views.rs) | 5 Saved View endpoints | No sharing, no compound sorting |
| [`sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs`](../sensei-rs/crates/sensei-api/src/routes/notification_triggers.rs) | 7 Notification endpoints | Disconnected from events |

### Frontend

| File | Purpose | Key Lines |
|------|---------|-----------|
| [`frontend/public/dashboard.html`](../frontend/public/dashboard.html) | Legacy SPA | L1-1653 (read-only views, XSS) |
| [`frontend/public/index.html`](../frontend/public/index.html) | WASM entry point | L1-? (alternative frontend) |

### Analysis Documents

| File | Purpose |
|------|---------|
| [`docs/analysis/taiga-system-master-analysis.md`](../docs/analysis/taiga-system-master-analysis.md) | Master synthesis of all ~20 problems with priority matrix |
| [`docs/analysis/data-model-and-stores-deep-dive.md`](../docs/analysis/data-model-and-stores-deep-dive.md) | Deep dive into data layer, entity stores, DDL, persistence |
| [`docs/analysis/saved-views-and-search-deep-dive.md`](../docs/analysis/saved-views-and-search-deep-dive.md) | Search indexing gaps, saved views feature gaps |
| [`docs/analysis/frontend-integration-deep-dive.md`](../docs/analysis/frontend-integration-deep-dive.md) | Frontend coverage gaps, XSS, fragmentation |

---

## Appendix: Quick-Reference Checklist

### Track A — Data Layer (4 fixes)
- [ ] **P0-A1**: Add `CREATE TABLE entity_store` to `01-init.sql` with composite PK `(entity_type, id)`
- [ ] **P0-A2**: Fix `StoreWriteGuard::drop()` — add error logging, phase 1; add explicit `commit()` method, phase 2
- [ ] **P2-A3**: Migrate String fields to enums (Priority, TaskStatus, ObeyaItemType, etc.)
- [ ] **P2-A4**: Add referential integrity validation in mutation handlers
- [ ] **P2-A5**: Add `limit`/`offset` pagination to all list endpoints

### Track B — Kanban + Obeya (2 fixes)
- [ ] **P1-B1**: Add WIP-limit check in `add_card` and `move_card`
- [ ] **P2-B2**: Add `is_terminal` field to `KanbanColumn`, fix cycle time calculation

### Track C — Tasks + State Machines (2 fixes)
- [ ] **P1-C1**: Implement conditions evaluation, roles check, hooks execution, and event publishing in `transition_instance`
- [ ] **P1-C2**: Integrate `update_task_status` with state machine validation

### Track D — Today + A3 + Notifications (3 fixes)
- [ ] **P0-D1**: Define and publish PM domain events (8+ new events)
- [ ] **P2-D2**: Replace hardcoded `open_ncrs: 0` and `open_capas: 0` with real queries
- [ ] **P2-D3**: Wire notification triggers to event bus subscriber, add PM event types, fix test_trigger

### Track E — Search + Saved Views (4 fixes)
- [ ] **P1-E1**: Implement SearchableService for all PM entity stores
- [ ] **P1-E2**: Add visibility/sharing, compound sorting, typed filters, RBAC to Saved Views
- [ ] **P2-E2**: Add entity_type filter, faceting, pagination to search endpoint
- [ ] **P3-E1**: Compound sort columns for Saved Views (can merge with P1-E2)

### Track F — Frontend (6 fixes)
- [ ] **P0-F1**: Replace all `innerHTML` with DOM API (`textContent`, `createElement`)
- [ ] **P1-F1**: Implement CRUD UI (Tasks first, then Kanban, then remaining sections)
- [ ] **P1-F2**: Audit WASM frontend, decide migration strategy
- [ ] **P3-F2**: Add audit logging display to frontend
- [ ] **P3-F3**: Move auth tokens from localStorage to HTTP-only cookies
- [ ] **P3-F4**: Add Content-Security-Policy header via router middleware
