# Saved Views & Search — Deep Technical Analysis

> **Date:** 2026-06-03  
> **Scope:** [`sensei-rs/crates/sensei-api/src/routes/saved_views.rs`](../../sensei-rs/crates/sensei-api/src/routes/saved_views.rs), [`sensei-rs/crates/sensei-api/src/routes/search.rs`](../../sensei-rs/crates/sensei-api/src/routes/search.rs), [`sensei-rs/crates/sensei-api/src/stores.rs`](../../sensei-rs/crates/sensei-api/src/stores.rs), [`sensei-rs/crates/sensei-api/src/db_stores.rs`](../../sensei-rs/crates/sensei-api/src/db_stores.rs), [`sensei-rs/crates/sensei-api/src/state.rs`](../../sensei-rs/crates/sensei-api/src/state.rs), [`sensei-rs/crates/sensei-api/src/router.rs`](../../sensei-rs/crates/sensei-api/src/router.rs), [`sensei-rs/crates/sensei-services/src/ops/search.rs`](../../sensei-rs/crates/sensei-services/src/ops/search.rs), [`sensei-rs/crates/sensei-core/src/domain/events.rs`](../../sensei-rs/crates/sensei-core/src/domain/events.rs), [`docs/BACKEND_DATA_MODELS_MAP.md`](../../docs/BACKEND_DATA_MODELS_MAP.md), [`docs/api/saved-views.md`](../../docs/api/saved-views.md), [`docs/api/search.md`](../../docs/api/search.md)  
> **Analyst:** Roo

---

## 1. Executive Summary

The **Saved Views** and **Search** subsystems are two standalone, narrowly-scoped features within the Sensei OS Rust backend. Neither subsystem integrates with the other, nor do they participate in the event-driven architecture that the rest of the system uses.

| Subsystem | Maturity | Lines of Code | Event Integration | DB-Backed |
|-----------|----------|--------------|-------------------|-----------|
| **Saved Views** | Minimal CRUD | ~175 (routes) + struct def | ❌ None | ✅ EntityStore (JSONB) |
| **Search** | Single-endpoint | ~270 (service) + ~60 (route) | ❌ None | ✅ `pg_trgm` / in-memory |

Both are functional but lack the richness of the Python/SQLAlchemy reference model, which defines a sophisticated **Segments** system with RBAC sharing, visibility tiers, usage analytics, and compound sorting.

---

## 2. Saved Views — Deep Dive

### 2.1 Data Model

Defined in [`sensei-rs/crates/sensei-api/src/stores.rs:612`](../../sensei-rs/crates/sensei-api/src/stores.rs#612):

```rust
pub struct SavedView {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub user_id: Uuid,
    pub name: String,
    pub entity_type: String,     // e.g. "task", "kanban_board", "contact", etc.
    pub filters: serde_json::Value,  // Free-form JSONB — no schema enforcement
    pub sort_by: Option<String>,     // Single field only — no compound sort
    pub sort_order: Option<String>,  // "asc" | "desc"
    pub columns: Vec<String>,        // Column name list
    pub is_default: bool,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}
```

**Key limitations:**

| Limitation | Impact |
|-----------|--------|
| `filters` is untyped `serde_json::Value` | No frontend/API contract for filter structure; every client must independently know the query DSL |
| `sort_by` is `Option<String>` | No compound sorting (e.g., `sort=priority,created_at DESC`) |
| `entity_type` is a free `String` | No enum/validation; any string accepted |
| No `visibility` field | Every view is private to the user; no team/department/organization sharing |
| No `pinned`, `smart`, `system` flags | Missing usability features present in the Python reference model |
| No usage tracking | No analytics on which views are actually used |

### 2.2 CRUD Operations

All 5 endpoints live in [`sensei-rs/crates/sensei-api/src/routes/saved_views.rs`](../../sensei-rs/crates/sensei-api/src/routes/saved_views.rs) and follow the same pattern:

| Operation | Route | Handler | User-Scoped? | Notes |
|-----------|-------|---------|-------------|-------|
| **List** | `GET /api/v1/saved-views` | [`list_saved_views`](../../sensei-rs/crates/sensei-api/src/routes/saved_views.rs:34) | ✅ `tenant_id + user_id` | Filters `.values()` in-memory; optional `entity_type` query param |
| **Create** | `POST /api/v1/saved-views` | [`create_saved_view`](../../sensei-rs/crates/sensei-api/src/routes/saved_views.rs:51) | ✅ `tenant_id + user_id` | Sets `is_default`; unmarks other defaults for same user+entity_type |
| **Get** | `GET /api/v1/saved-views/{id}` | [`get_saved_view`](../../sensei-rs/crates/sensei-api/src/routes/saved_views.rs:91) | ✅ `tenant_id + user_id` | Returns 404 if not owned by user |
| **Update** | `PUT /api/v1/saved-views/{id}` | [`update_saved_view`](../../sensei-rs/crates/sensei-api/src/routes/saved_views.rs:108) | ✅ `tenant_id + user_id` | Partial update via `SavedViewRequest` |
| **Delete** | `DELETE /api/v1/saved-views/{id}` | [`delete_saved_view`](../../sensei-rs/crates/sensei-api/src/routes/saved_views.rs:158) | ✅ `tenant_id + user_id` | Hard delete |

The `SavedViewRequest` DTO ([line 21](../../sensei-rs/crates/sensei-api/src/routes/saved_views.rs:21)):

```rust
pub struct SavedViewRequest {
    pub name: String,
    pub entity_type: String,
    pub filters: serde_json::Value,
    pub sort_by: Option<String>,
    pub sort_order: Option<String>,
    pub columns: Vec<String>,
    pub is_default: Option<bool>,
}
```

### 2.3 Persistence Layer

Saved Views use the generic [`EntityStore<T>`](../../sensei-rs/crates/sensei-api/src/db_stores.rs:87) pattern:

- **In-memory:** `EntityStore::new("saved_view")` — uses `Arc<RwLock<HashMap<Uuid, SavedView>>>`
- **Database:** `EntityStore::with_pool("saved_view", pool)` — lazy-loads from `entity_store` table's JSONB column on first read/write
- **Persistence:** On `StoreWriteGuard` drop, a `tokio::spawn` task persists changes via UPSERT into:
  ```sql
  INSERT INTO entity_store (entity_type, id, data, updated_at)
  VALUES ('saved_view', $1, $2, NOW())
  ON CONFLICT (entity_type, id) DO UPDATE SET data = $2, updated_at = NOW()
  ```
- **No dedicated `saved_views` table.** The same `entity_store` table stores Kanban boards, Tasks, Obeya items, notifications, etc.

### 2.4 Entity Type Coupling

The [`entity_type`](../../sensei-rs/crates/sensei-api/src/stores.rs:612) field is a free-string with no validation. The handler's `list` endpoint accepts an optional `entity_type` query parameter to filter views. The system does **not** enforce that a `SavedView` with `entity_type = "task"` actually has a valid task schema for its filters/columns.

**Practical coupling:** None. The saved views system stores opaque JSONB blobs. Any frontend entity type can have saved views, but the backend provides zero assistance with filter validation, column existence checking, or sort field validation. This is entirely a frontend concern.

---

## 3. Search — Deep Dive

### 3.1 Trait & DTO

Defined in [`sensei-rs/crates/sensei-services/src/ops/search.rs:27`](../../sensei-rs/crates/sensei-services/src/ops/search.rs#27):

```rust
#[derive(Debug, Clone, Serialize)]
pub struct SearchResult {
    pub result_type: String,   // "user" | "account" | "contact" | "product"
    pub result_id: Uuid,
    pub result_title: String,
    pub relevance: f32,
}

#[async_trait]
pub trait SearchService: Send + Sync {
    async fn search(
        &self,
        tenant_id: EntityId,
        query: &str,
    ) -> Result<Vec<SearchResult>>;
}
```

### 3.2 Indexed Entities

Only **4 entity types** are searchable:

| Entity | Fields Searched | InMemory Algorithm | Database Algorithm |
|--------|----------------|-------------------|-------------------|
| **Account** | name, email, tax_id | `score_match()` — prefix/contains/word-overlap | `pg_trgm` trigram similarity via `search_all()` |
| **Contact** | full_name, email | same | same |
| **Product** | name, sku, description | same | same |
| **User** | name, email | same | same |

**Notably absent from search indexing:**
- ❌ Tasks
- ❌ Kanban cards & boards
- ❌ Work orders
- ❌ Obeya items
- ❌ A3 reports
- ❌ Andon events
- ❌ Risks
- ❌ Opportunities/RFQs/Quotes
- ❌ Knowledge packs
- ❌ Training courses
- ❌ State machine instances
- ❌ Any entity stored in `EntityStore`

### 3.3 InMemory Search Algorithm

The [`score_match`](../../sensei-rs/crates/sensei-services/src/ops/search.rs:87) function applies a tiered scoring system:

```
1.0  — Exact match (case-insensitive)
0.8  — Prefix match (target starts with query)
0.5  — Substring match (target contains query)
0.4 * (word_match_ratio) — Partial word overlap
0.0  — No match
```

The `best_score` function takes the maximum score across all searched fields for an entity. Results are sorted descending by relevance and truncated to 50.

**Performance concern for InMemorySearchService:** On every search call, the in-memory implementation fetches **all** accounts (limit 200), contacts (limit 200), products (limit 200), and users from the respective domain services, then iterates through each to compute scores. For large tenants with thousands of entities, this is O(n) per search with n = total entities × fields-per-entity.

### 3.4 Database Search

The [`DatabaseSearchService`](../../sensei-rs/crates/sensei-services/src/ops/search.rs:226) delegates to a PostgreSQL function `search_all(query, tenant_id)`:

```rust
let rows = sqlx::query_as::<_, (String, Uuid, String, f32)>(
    "SELECT result_type, result_id, result_title, relevance FROM search_all($1, $2)",
)
.bind(query)
.bind(tenant_id)
.fetch_all(&self.pool)
.await?;
```

This function presumably uses `pg_trgm` similarity operators (`SIMILARITY()`, `ILIKE`, or `%` operator) across the `accounts`, `contacts`, `products`, and `users` tables. The function is not visible in the Rust source but is referenced in the service.

### 3.5 API Endpoint

Single endpoint in [`sensei-rs/crates/sensei-api/src/routes/search.rs:36`](../../sensei-rs/crates/sensei-api/src/routes/search.rs#36):

```
GET /api/v1/search?q=<query>&limit=<number>
```

| Parameter | Type | Default | Max |
|-----------|------|---------|-----|
| `q` | String | required | — |
| `limit` | usize | 10 | 50 |

Response ([`SearchResponse`](../../sensei-rs/crates/sensei-api/src/routes/search.rs:27)):

```json
{
  "results": [ { "result_type": "...", "result_id": "...", "result_title": "...", "relevance": 0.85 } ],
  "total": 42,
  "query": "search term"
}
```

No entity-type filter, no pagination beyond the cap, no faceting, no field-level search (can't search only product SKUs).

---

## 4. Integration Map

### 4.1 Saved Views ↔ External Systems

| Integration | Status | Details |
|------------|--------|---------|
| **Event Bus** | ❌ Not integrated | No `SavedViewCreated`, `SavedViewUpdated`, or `SavedViewDeleted` events published |
| **RBAC** | ❌ Not integrated | No role/permission checks; only user-scoped (`user_id` filter) |
| **Search** | ❌ Not integrated | Search does NOT index saved view names or configurations |
| **Audit Log** | ❌ Not integrated | No audit trail for saved view CRUD |
| **Kanban/Tasks/Obeya** | ❌ Not integrated | Saved views are stored as opaque JSONB; no system ensures saved view filters match the target entity's fields |
| **Domain Events** | ❌ Not subscribed | Saved views don't listen for events to update dynamic/smart views |

### 4.2 Search ↔ External Systems

| Integration | Status | Details |
|------------|--------|---------|
| **Event Bus** | ❌ Not integrated | No event handlers to re-index entities on create/update/delete |
| **Saved Views** | ❌ Not integrated | No saved search queries feature |
| **EntityStore** | ❌ Not integrated | All `EntityStore`-backed entities (tasks, kanban, obeya, etc.) are invisible to search |
| **Domain Services** | ⚠️ Partial | InMemory version calls `list_accounts`, `list_contacts`, `list_products`, `list_users_paginated` — but these may return stale/extraneous data |
| **Database** | ✅ Integrated | `search_all()` PG function queries `accounts`, `contacts`, `products`, `users` tables |
| **Tenant Isolation** | ✅ Proper | Both implementations filter by `tenant_id` |
| **Pg_trgm extension** | ✅ Required | Database implementation requires PostgreSQL `pg_trgm` for trigram similarity |

### 4.3 AppState Wiring

From [`sensei-rs/crates/sensei-api/src/state.rs:303`](../../sensei-rs/crates/sensei-api/src/state.rs#303) and [`line 425`](../../sensei-rs/crates/sensei-api/src/state.rs#425):

```rust
// InMemory mode (new() constructor)
let search_service = Arc::new(InMemorySearchService::new(
    accounts_service.clone(),
    contacts_service.clone(),
    products_service.clone(),
    users_service.clone(),
));

// Database mode (with_db_pool())
self.search_service = Arc::new(DatabaseSearchService::new(p.clone()));
```

**Key observation:** The `InMemorySearchService` receives `*Service` trait objects, while `DatabaseSearchService` receives only a `PgPool`. This means the DB implementation is completely independent of the domain service layer — it queries the database directly. The in-memory version is a development/testing shim.

---

## 5. Gap Analysis

### 5.1 Gaps vs. Python/SQLAlchemy Reference Model

The Python reference model in [`docs/BACKEND_DATA_MODELS_MAP.md:1019`](../../docs/BACKEND_DATA_MODELS_MAP.md#1019) defines two related concepts:

#### Segments (`segments` table) — Much richer than Rust Saved Views

| Feature | Python (`segments`) | Rust (`SavedView`) |
|---------|-------------------|-------------------|
| **Filter groups** | `filter_groups` (JSONB) — supports AND/OR groups | `filters` (JSONB) — single flat blob, no group structure |
| **Sort config** | `sort_config` (JSONB) — compound multi-field | `sort_by` (Option) + `sort_order` (Option) — single field only |
| **Visibility** | Enum: `private`/`team`/`department`/`organization` | ❌ None — implicitly private |
| **Sharing** | Dedicated `segment_shares` table with `can_edit` | ❌ None |
| **Pinned** | `pinned` boolean | ❌ None |
| **Smart** | `smart` boolean (auto-updating) | ❌ None |
| **System** | `system` boolean (built-in, non-deletable) | ❌ None |
| **Usage analytics** | `segment_usage` table with `result_count`, `execution_time_ms` | ❌ None |
| **Module association** | `module` Enum (rfq/quote/opportunity/kanban/andon/a3/etc.) | `entity_type` (free string, no validation) |

#### Saved Views (`saved_views` table) — Separate from segments

```python
saved_views:
    entity_type: str
    owner_id: FK -> users
    visibility: Enum(team, department, organization)
    conditions: JSONB
    sort: JSONB
    columns: JSONB
```

This is a separate concept from "segments" — it appears saved views are the Python equivalent of the Rust `SavedView`. The Python version adds **visibility** and uses JSONB for sort (enabling compound sorts).

#### Autosave & Drafts
The Python model also has `autosave_drafts` and `autosave_draft_versions` tables — completely absent in Rust.

### 5.2 Missing Features in Rust

| Missing Feature | Severity | Why It Matters |
|---------------|----------|---------------|
| **Saved View domain events** | Medium | Other subsystems can't react to view changes (e.g., a "smart" view clearing its cache) |
| **Compound sorting** | Low | Single-field sort is sufficient for most use cases, but power users need multi-field |
| **Sharing / RBAC** | High | The current user-only scoping prevents managers from sharing dashboards with their teams |
| **Search indexing for EntityStore entities** | High | Tasks, Kanban cards, work orders, and Obeya items are invisible to search |
| **Search entity-type filtering** | Medium | Users can't search only "tasks" or only "products" |
| **Saved search queries** | Medium | Users can't save a search and re-run it later |
| **Search event subscription** | Medium | Entities that are created/updated/deleted are not re-indexed in the in-memory search service |
| **Audit trail** | Low | Saved view CRUD is not auditable |
| **Filter schema validation** | Medium | No backend validation that saved view filters match the target entity's fields |
| **Dynamic/smart views** | Low | Auto-updating views based on conditions (e.g., "show all tasks due this week") |
| **Autosave/drafts** | Low | No draft recovery for unsaved work |
| **Usage analytics** | Medium | No data on which views are popular or slow |

### 5.3 Architectural Concerns

1. **EntityStore isolation from Search:** All entities stored via `EntityStore<T>` (tasks, kanban boards, obeya items, work packets, etc.) use the shared `entity_store` table with a JSONB `data` column. The `search_all()` PostgreSQL function does **not** query this table. To make EntityStore entities searchable, either:
   - The `search_all()` function would need to JOIN with `entity_store` and parse JSONB
   - Or each entity type would need its own dedicated table with proper columns for `pg_trgm`

2. **No write-behind cache for InMemorySearchService:** The in-memory search service fetches all entities on every search call. It could cache domain service results with an invalidation strategy tied to domain events.

3. **Route registration is manual:** Each entity type that wants to participate in search must be manually added to the search service (both in the search implementation and the `search_all()` PG function). There's no auto-registration mechanism.

4. **No full-text search (FTS):** The system uses `pg_trgm` trigram similarity, not PostgreSQL's built-in `tsvector`/`tsquery` full-text search with stemming, stop words, and ranking. Trigram search is better for fuzzy/typo-tolerant search; FTS is better for semantic document search. The current approach is reasonable for names/SKUs but wouldn't handle description-heavy search well.

---

## 6. API Surface Table

### 6.1 Saved Views API

| Method | Route | Request Body | Query Params | Response | Auth |
|--------|-------|-------------|-------------|----------|------|
| `GET` | `/api/v1/saved-views` | — | `entity_type` (optional) | `Vec<SavedView>` | JWT + tenant-scoped |
| `POST` | `/api/v1/saved-views` | `SavedViewRequest` | — | `SavedView` (201) | JWT + tenant-scoped |
| `GET` | `/api/v1/saved-views/{id}` | — | — | `SavedView` | JWT + user-ownership |
| `PUT` | `/api/v1/saved-views/{id}` | `SavedViewRequest` | — | `SavedView` | JWT + user-ownership |
| `DELETE` | `/api/v1/saved-views/{id}` | — | — | `204 No Content` | JWT + user-ownership |

**`SavedViewRequest` schema:**
```json
{
  "name": "My Task View",
  "entity_type": "task",
  "filters": { "status": { "eq": "open" } },
  "sort_by": "created_at",
  "sort_order": "desc",
  "columns": ["title", "status", "assignee", "due_date"],
  "is_default": true
}
```

### 6.2 Search API

| Method | Route | Request Body | Query Params | Response | Auth |
|--------|-------|-------------|-------------|----------|------|
| `GET` | `/api/v1/search` | — | `q` (required), `limit` (optional, default 10, max 50) | `SearchResponse` | JWT + tenant-scoped |

**`SearchResponse` schema:**
```json
{
  "results": [
    { "result_type": "account", "result_id": "uuid", "result_title": "Acme Corp", "relevance": 0.95 }
  ],
  "total": 1,
  "query": "acme"
}
```

### 6.3 Missing Endpoints

| Missing Endpoint | Priority | Rationale |
|-----------------|----------|-----------|
| `GET /api/v1/search/{entity_type}?q=...` | High | Entity-type scoped search without client-side filtering |
| `POST /api/v1/saved-views/{id}/share` | Medium | Share a saved view with other users/teams |
| `GET /api/v1/saved-views/shared-with-me` | Medium | List views shared with the current user |
| `POST /api/v1/saved-views/{id}/duplicate` | Low | Clone a view |
| `GET /api/v1/saved-views/{id}/usage` | Low | View usage analytics |
| `POST /api/v1/search/saved` | Medium | Save a search query for later reuse |

---

## 7. Mermaid Architecture Diagram

```mermaid
flowchart TB
    subgraph Client["🌐 Frontend Clients"]
        UI["Sensei UI (React/JS)"]
    end

    subgraph API["🗄️ API Layer (sensei-api)"]
        direction TB
        Router["Router (router.rs)"]
        SV_Routes["Saved Views Routes\n(saved_views.rs)\nGET/POST/PUT/DELETE\n/api/v1/saved-views"]
        Search_Route["Search Route\n(search.rs)\nGET /api/v1/search"]
        
        Router --> SV_Routes
        Router --> Search_Route
    end

    subgraph State["⚙️ AppState (state.rs)"]
        SV_Store["SavedViewStore\n(EntityStore<SavedView>)"]
        Search_Service["Arc<dyn SearchService>"]
    end

    subgraph Storage["💾 Storage Layer"]
        direction TB
        ES_Table["entity_store table\n(entity_type='saved_view')\nJSONB column"]
        ACCOUNTS_TABLE["accounts table"]
        CONTACTS_TABLE["contacts table"]
        PRODUCTS_TABLE["products table"]
        USERS_TABLE["users table"]
    end

    subgraph SearchImpl["🔍 Search Implementations"]
        direction TB
        IM_Search["InMemorySearchService\n(dev/testing)\n- Fetches all via domain services\n- Client-side string scoring"]
        DB_Search["DatabaseSearchService\n(production)\n- Calls search_all() PG function\n- pg_trgm trigram similarity"]
    end

    subgraph DomainServices["🧩 Domain Services (sensei-services)"]
        AS[("AccountsService")]
        CS[("ContactsService")]
        PS[("ProductsService")]
        US[("UsersService")]
    end

    subgraph Events["📡 Event Bus"]
        EventBus["InMemoryEventBus / NatsEventBus"]
        DomainEvents["~50 Domain Events\n(identity, quality, production,\nfinance, HR, supply chain)"]
        No_SV_Events["❌ No SavedView events\n(CREATED/UPDATED/DELETED)"]
        No_Search_Events["❌ No Search events\n(INDEX/UPDATED/REINDEX)"]
    end

    subgraph PythonRef["🐍 Python Reference Model\n(BACKEND_DATA_MODELS_MAP.md)"]
        Segments["segments table\n- module (enum)\n- visibility (enum)\n- filter_groups (JSONB)\n- sort_config (JSONB)\n- pinned/smart/system flags"]
        SegSharing["segment_shares table\n- shared_with_id\n- can_edit flag"]
        SegUsage["segment_usage table\n- result_count\n- execution_time_ms"]
        Py_SV["saved_views table\n- visibility (enum)\n- conditions/sort/columns (JSONB)"]
        Drafts["autosave_drafts\n- content (JSONB)\n- expires_at"]
    end

    %% Connections
    UI -->|HTTP| Router
    SV_Routes -->|read/write| SV_Store
    SV_Store --- ES_Table
    Search_Route -->|tenant_id, query| Search_Service
    Search_Service -->|dev mode| IM_Search
    Search_Service -->|prod mode| DB_Search
    DB_Search -->|pg_trgm| ACCOUNTS_TABLE
    DB_Search -->|pg_trgm| CONTACTS_TABLE
    DB_Search -->|pg_trgm| PRODUCTS_TABLE
    DB_Search -->|pg_trgm| USERS_TABLE
    IM_Search -->|list_accounts()| AS
    IM_Search -->|list_contacts()| CS
    IM_Search -->|list_products()| PS
    IM_Search -->|list_users_paginated()| US
    
    %% Event bus non-connections
    EventBus -.->|"❌ NO events published"| SV_Store
    EventBus -.->|"❌ NO events subscribed"| Search_Service
    DomainEvents -.->|"❌ NO saved view/search events"| No_SV_Events
    DomainEvents -.->|"❌ NO saved view/search events"| No_Search_Events

    %% Bypassed EntityStore entities
    subgraph MissingSearch["⚠️ NOT Searchable"]
        Tasks["tasks (EntityStore)"]
        Kanban["kanban_boards (EntityStore)"]
        Obeya["obeya_boards (EntityStore)"]
        WorkOrders["work_orders (EntityStore)"]
        A3["a3_reports (EntityStore)"]
        Risks["risks (EntityStore)"]
        Knowledge["knowledge_packs (EntityStore)"]
        Training["training_courses (EntityStore)"]
    end

    DB_Search -.->|"❌ NOT indexed"| Tasks
    DB_Search -.->|"❌ NOT indexed"| Kanban
    DB_Search -.->|"❌ NOT indexed"| Obeya

    %% Style definitions
    classDef missing fill:#ff6b6b,color:#fff,stroke:#c0392b
    classDef present fill:#2ecc71,color:#fff,stroke:#27ae60
    classDef partial fill:#f39c12,color:#fff,stroke:#e67e22
    classDef python fill:#9b59b6,color:#fff,stroke:#8e44ad
    classDef storage fill:#3498db,color:#fff,stroke:#2980b9

    class No_SV_Events,No_Search_Events,MissingSearch missing
    class SV_Routes,Search_Route,Router present
    class Segments,SegSharing,SegUsage,Py_SV,Drafts python
    class ES_Table,ACCOUNTS_TABLE,CONTACTS_TABLE,PRODUCTS_TABLE,USERS_TABLE storage
    class IM_Search partial
```

---

## 8. Key Recommendations

### 🔴 Critical

1. **Make EntityStore entities searchable.** Add a `search_all()` function that queries the `entity_store` table's JSONB column for tasks, kanban boards, obeya items, and other EntityStore-backed entities. At minimum, search entity names/titles. This requires a GIN index on `entity_store.data` for performance.

2. **Add Saved View domain events.** Publish `SavedViewCreated`, `SavedViewUpdated`, `SavedViewDeleted` events so that:
   - The audit log can track view changes
   - A future cache layer can invalidate view-related data
   - Smart/dynamic views (future) can be re-evaluated

### 🟠 High

3. **Add visibility/sharing to Saved Views.** At minimum, support a `visibility` enum (`Private` / `Team` / `Department` / `Organization`) matching the Python model. This enables managers to share dashboards without building a separate sharing system. Follow with a `segment_shares`-style table for explicit sharing with edit permissions.

4. **Support compound sorting.** Change `sort_by: Option<String>` to `sort_config: Vec<SortConfig>` where each entry has a field name and direction. This matches the Python model's `sort_config` JSONB approach.

5. **Add search entity-type filtering.** Support `GET /api/v1/search?q=...&entity_type=task` so clients can scope searches. This is a simple parameter pass-through to both the in-memory and database implementations.

### 🟡 Medium

6. **Add filter schema validation.** Define a `FilterGroup` struct with AND/OR nesting (matching the Python `filter_groups` concept) so the backend can validate saved view filters against known entity field schemas. This prevents frontend errors from persisting invalid filter configurations.

7. **Add usage tracking.** Create a `saved_view_usage` table (matching Python's `segment_usage`) to track which views are most used, query counts, and execution times. This data can drive UI decisions (showing popular views first) and performance monitoring.

8. **Wire search into the event bus.** When entities are created/updated/deleted, publish domain events that the search service can consume to refresh its index. For the in-memory implementation, this could invalidate a cached search result set. For the database implementation, this ensures the `search_all()` function always sees fresh data.

### 🟢 Low

9. **Add autosave/drafts support.** Implement the `autosave_drafts` table from the Python model to provide draft recovery for unsaved view configurations.

10. **Add saved search queries.** Allow users to save a search query + filters as a "Saved Search" that can be re-run from the UI. This is a natural extension of the Saved Views concept.

---

## Appendix A: File Reference Table

| File | Lines | Purpose | Key Types/Functions |
|------|-------|---------|-------------------|
| [`sensei-rs/crates/sensei-api/src/routes/saved_views.rs`](../../sensei-rs/crates/sensei-api/src/routes/saved_views.rs) | 1–175 | Saved Views HTTP handlers | `SavedViewRequest`, `list/ create/ get/ update/ delete_saved_view` |
| [`sensei-rs/crates/sensei-api/src/routes/search.rs`](../../sensei-rs/crates/sensei-api/src/routes/search.rs) | 1–57 | Search HTTP handler | `SearchParams`, `SearchResponse`, `search()` |
| [`sensei-rs/crates/sensei-api/src/stores.rs`](../../sensei-rs/crates/sensei-api/src/stores.rs) | 612–625 | `SavedView` struct definition | `SavedView { id, tenant_id, user_id, name, entity_type, filters, sort_by, sort_order, columns, is_default, ... }` |
| [`sensei-rs/crates/sensei-api/src/db_stores.rs`](../../sensei-rs/crates/sensei-api/src/db_stores.rs) | 1–372 | Generic `EntityStore<T>` | `EntityStore::new()`, `EntityStore::with_pool()`, `StoreReadGuard`, `StoreWriteGuard` |
| [`sensei-rs/crates/sensei-api/src/state.rs`](../../sensei-rs/crates/sensei-api/src/state.rs) | 68–496 | `AppState` with all services | `search_service: Arc<dyn SearchService>`, `saved_views: SavedViewStore` |
| [`sensei-rs/crates/sensei-api/src/router.rs`](../../sensei-rs/crates/sensei-api/src/router.rs) | 922, 1020–1021 | Route registration | `route("/api/v1/search", ...)`, `route("/api/v1/saved-views", ...)` |
| [`sensei-rs/crates/sensei-services/src/ops/search.rs`](../../sensei-rs/crates/sensei-services/src/ops/search.rs) | 1–270 | Search service trait + impls | `SearchService` trait, `SearchResult`, `InMemorySearchService`, `DatabaseSearchService` |
| [`sensei-rs/crates/sensei-core/src/domain/events.rs`](../../sensei-rs/crates/sensei-core/src/domain/events.rs) | 1–3192 | Domain events (no SV/search events) | ~50 events across identity, quality, production, finance, HR, supply chain |
| [`docs/BACKEND_DATA_MODELS_MAP.md`](../../docs/BACKEND_DATA_MODELS_MAP.md) | 1019–1037 | Python reference model | `segments`, `segment_shares`, `segment_usage`, `saved_views`, `autosave_drafts` |
| [`docs/api/saved-views.md`](../../docs/api/saved-views.md) | 1–4 | API doc (empty placeholder) | — |
| [`docs/api/search.md`](../../docs/api/search.md) | 1–4 | API doc (empty placeholder) | — |

## Appendix B: Scoring Algorithm Reference

From [`sensei-rs/crates/sensei-services/src/ops/search.rs:87`](../../sensei-rs/crates/sensei-services/src/ops/search.rs#87):

```rust
fn score_match(query: &str, target: &str) -> f32 {
    let lower_q = query.to_lowercase();
    let lower_t = target.to_lowercase();

    if lower_t == lower_q {           // Exact match
        1.0
    } else if lower_t.starts_with(&lower_q) {  // Prefix match
        0.8
    } else if lower_t.contains(&lower_q) {     // Substring match
        0.5
    } else {
        // Word overlap scoring
        let matches = query_words.iter()
            .filter(|w| target_words.contains(w)).count();
        if matches > 0 {
            matches as f32 / query_words.len() as f32 * 0.4
        } else {
            0.0
        }
    }
}
```

The `best_score` function takes the maximum score across all searched fields for an entity:

```rust
fn best_score(query: &str, fields: &[&str]) -> f32 {
    fields.iter()
        .map(|f| Self::score_match(query, f))
        .fold(0.0_f32, f32::max)
}
```
