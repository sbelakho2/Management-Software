//! Database-backed unified search service.
//!
//! Runs SQL search directly against PostgreSQL using `pg_trgm` trigram
//! similarity, replacing the in-memory windowed search in database mode.
//!
//! # Coverage
//!
//! * **Typed tables** — `users` (name, email), `accounts` (name, email),
//!   `contacts` (first_name/last_name, email), `products` (name, sku,
//!   product_number) with `similarity()` ranking.
//! * **Generic entity stores** — `entity_store` JSONB rows for the PM
//!   entity types (`task`, `kanban_board`, `obeya_board`, `knowledge_pack`,
//!   `training_course`, `work_center`, `state_machine_instance`,
//!   `production_cell`, `standard_work`, `lsw_standard`, `kpi_definition`,
//!   `notification_trigger`) searched via `data->>'name'` /
//!   `data->>'title'` / `data->>'description'` with ILIKE + trigram.
//!
//! Every query is scoped with `WHERE tenant_id = $1` — a tenant can only
//! ever see its own entities — and ranked by `similarity()`, truncated to a
//! bounded result set.
//!
//! # Authorization (twenty-ninth-audit Wave B item 10)
//!
//! [`search_db_authorized`] runs the caller-derived
//! [`AllowedSearchProjection`]: candidate tables/types are filtered
//! BEFORE ranking by the caller's permissions (result types whose read
//! permission the caller lacks are never queried) and operational types
//! are restricted to the caller's authorized sites INSIDE the SQL
//! (`NoOperationalScope` yields no operational rows at all). Search never
//! runs all tables and then filters the result set.
//!
//! # Indexing contract
//!
//! [`SearchService::index_entity`] / [`SearchService::remove_from_index`]
//! are **no-ops**: there is no separate `search_index` table (dropped by
//! migration 022) — the source tables and the `entity_store` JSONB column
//! are queried directly, so there is nothing to maintain.

use async_trait::async_trait;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::EntityId;
use sensei_services::ops::search::{SearchResult, SearchService};
use sqlx::PgPool;
use std::collections::HashMap;
use uuid::Uuid;

use crate::authorization::search_policy::{policy_for, AllowedSearchProjection, ScopeMode};

/// Maximum results per entity query before the cross-type merge.
const SEARCH_LIMIT: i64 = 50;

/// Entity types stored in the generic `entity_store` table: `(search result
/// type name, store entity_type)`.
///
/// The search result type names must match what the in-memory providers
/// report (`standard_work` for `standard_work_document` etc.) so the API
/// response shape is identical in both modes.
const GENERIC_ENTITY_TYPES: &[(&str, &str)] = &[
    ("task", "task"),
    ("kanban_board", "kanban_board"),
    ("obeya_board", "obeya_board"),
    ("knowledge_pack", "knowledge_pack"),
    ("training_course", "training_course"),
    ("work_center", "work_center"),
    ("state_machine_instance", "state_machine_instance"),
    ("production_cell", "production_cell"),
    ("standard_work", "standard_work_document"),
    ("lsw_standard", "lsw_standard"),
    ("kpi_definition", "kpi_definition"),
    ("notification_trigger", "notification_trigger"),
];

/// Database-backed implementation of [`SearchService`].
///
/// Constructed in [`crate::state::AppState::with_db_pool`] and installed in
/// `AppState::search_service`; in-memory mode keeps using
/// [`InMemorySearchService`](sensei_services::ops::search::InMemorySearchService).
pub struct DatabaseSearchService {
    pool: PgPool,
}

impl DatabaseSearchService {
    /// Create a new [`DatabaseSearchService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    /// Search users by name/email (typed table).
    async fn search_users(
        &self,
        tenant_id: EntityId,
        query: &str,
        limit: i64,
    ) -> Result<Vec<SearchResult>> {
        let rows = sqlx::query_as::<_, (Uuid, String, Option<String>, f32)>(
            "SELECT id, name, email, \
                GREATEST(similarity(name, $2), similarity(COALESCE(email, ''), $2)) AS relevance \
             FROM users \
             WHERE tenant_id = $1 \
               AND (name ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%' OR email ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%') \
             ORDER BY relevance DESC \
             LIMIT $3",
        )
        .bind(tenant_id)
        .bind(query)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("User search failed: {e}")))?;

        Ok(rows
            .into_iter()
            .map(|(id, name, _email, relevance)| SearchResult {
                result_type: "user".to_string(),
                result_id: id,
                result_title: name,
                relevance,
            })
            .collect())
    }

    /// Search accounts by name/email (typed table).
    async fn search_accounts(
        &self,
        tenant_id: EntityId,
        query: &str,
        limit: i64,
    ) -> Result<Vec<SearchResult>> {
        let rows = sqlx::query_as::<_, (Uuid, String, Option<String>, f32)>(
            "SELECT id, name, email, \
                GREATEST(similarity(name, $2), similarity(COALESCE(email, ''), $2)) AS relevance \
             FROM accounts \
             WHERE tenant_id = $1 \
               AND (name ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%' OR email ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%') \
             ORDER BY relevance DESC \
             LIMIT $3",
        )
        .bind(tenant_id)
        .bind(query)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Account search failed: {e}")))?;

        Ok(rows
            .into_iter()
            .map(|(id, name, _email, relevance)| SearchResult {
                result_type: "account".to_string(),
                result_id: id,
                result_title: name,
                relevance,
            })
            .collect())
    }

    /// Search contacts by display name / email (typed table).
    async fn search_contacts(
        &self,
        tenant_id: EntityId,
        query: &str,
        limit: i64,
    ) -> Result<Vec<SearchResult>> {
        let rows = sqlx::query_as::<_, (Uuid, String, Option<String>, f32)>(
            "SELECT id, (first_name || ' ' || last_name) AS full_name, email, \
                GREATEST(similarity(first_name || ' ' || last_name, $2), \
                         similarity(COALESCE(email, ''), $2)) AS relevance \
             FROM contacts \
             WHERE tenant_id = $1 \
               AND (first_name ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%' \
                    OR last_name ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%' \
                    OR email ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%') \
             ORDER BY relevance DESC \
             LIMIT $3",
        )
        .bind(tenant_id)
        .bind(query)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Contact search failed: {e}")))?;

        Ok(rows
            .into_iter()
            .map(|(id, full_name, _email, relevance)| SearchResult {
                result_type: "contact".to_string(),
                result_id: id,
                result_title: full_name,
                relevance,
            })
            .collect())
    }

    /// Search products by name/sku/product_number (typed table).
    async fn search_products(
        &self,
        tenant_id: EntityId,
        query: &str,
        limit: i64,
    ) -> Result<Vec<SearchResult>> {
        let rows = sqlx::query_as::<_, (Uuid, String, Option<String>, f32)>(
            "SELECT id, name, sku, \
                GREATEST(similarity(name, $2), similarity(COALESCE(sku, ''), $2)) AS relevance \
             FROM products \
             WHERE tenant_id = $1 \
               AND (name ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%' \
                    OR sku ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%' \
                    OR product_number ILIKE '%' || replace(replace($2, '%', '\\%'), '_', '\\_') || '%') \
             ORDER BY relevance DESC \
             LIMIT $3",
        )
        .bind(tenant_id)
        .bind(query)
        .bind(limit)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Product search failed: {e}")))?;

        Ok(rows
            .into_iter()
            .map(|(id, name, _sku, relevance)| SearchResult {
                result_type: "product".to_string(),
                result_id: id,
                result_title: name,
                relevance,
            })
            .collect())
    }

    /// Search the generic `entity_store` JSONB rows for the given store
    /// entity types, scoped to the tenant (unrestricted operational
    /// variant — used by the legacy trait path).
    async fn search_entity_store(
        &self,
        tenant_id: EntityId,
        query: &str,
        store_types: &[String],
        limit: i64,
    ) -> Result<Vec<SearchResult>> {
        self.search_entity_store_rows(tenant_id, query, store_types, None, None, limit)
            .await
    }

    /// Search `entity_store` JSONB rows for the given store entity types.
    ///
    /// `operational_store_types` + `sites` carry the authorization
    /// restriction (Wave B item 10): when both are `Some`, operational
    /// rows must be attributable to one of the caller's authorized sites
    /// INSIDE the SQL — an unattributable operational row (or an empty
    /// entitlement) matches zero rows. `None` sites = no scope authority
    /// (dev/unrestricted). Candidate types are always filtered BEFORE
    /// ranking — search never runs the whole table and filters after.
    #[allow(clippy::too_many_arguments)]
    async fn search_entity_store_rows(
        &self,
        tenant_id: EntityId,
        query: &str,
        store_types: &[String],
        operational_store_types: Option<&[String]>,
        sites: Option<&[Uuid]>,
        limit: i64,
    ) -> Result<Vec<SearchResult>> {
        // Reverse map: store entity_type -> search result type name.
        let search_type_of: HashMap<&str, &str> =
            GENERIC_ENTITY_TYPES.iter().map(|(s, e)| (*e, *s)).collect();

        // Operational attribution clause (site predicate for the
        // operational tables that carry site_id — inserted BEFORE the
        // LIMIT, i.e. before ranking truncation):
        //
        // * work_center rows are attributed through the relational
        //   `work_centers.site_id`;
        // * production_cell rows through `production_cell_work_centers`
        //   → their work centers' sites;
        // * standard-work rows carry no site linkage — they are never
        //   attributable and are excluded under a site restriction.
        //
        // The clause is only assembled from fixed fragments; parameter
        // numbering is tracked explicitly below.
        let (site_clause, limit_param): (String, usize) = match (operational_store_types, sites) {
            (Some(op_types), Some(site_list)) if !site_list.is_empty() => (
                format!(
                    " AND (entity_type <> ALL($4::text[]) \
                     OR EXISTS (SELECT 1 FROM work_centers wc \
                                WHERE wc.tenant_id = entity_store.tenant_id \
                                  AND wc.id = entity_store.id \
                                  AND wc.site_id = ANY($5)) \
                     OR EXISTS (SELECT 1 FROM production_cell_work_centers pcwc \
                                JOIN work_centers wc \
                                  ON wc.tenant_id = pcwc.tenant_id \
                                 AND wc.id = pcwc.work_center_id \
                                WHERE pcwc.tenant_id = entity_store.tenant_id \
                                  AND pcwc.cell_id = entity_store.id \
                                  AND wc.site_id = ANY($5))) \
                     -- {op_type_count} operational types restricted to the \
                     -- caller's authorized sites",
                    op_type_count = op_types.len()
                ),
                6,
            ),
            _ => (String::new(), 4),
        };

        let base_sql = "SELECT id, entity_type, data, \
                GREATEST(similarity(COALESCE(data->>'name', ''), $3), \
                         similarity(COALESCE(data->>'title', ''), $3), \
                         similarity(COALESCE(data->>'description', ''), $3)) AS relevance \
             FROM entity_store \
             WHERE tenant_id = $1 AND entity_type = ANY($2) \
               AND (COALESCE(data->>'name', '') ILIKE '%' || replace(replace($3, '%', '\\%'), '_', '\\_') || '%' \
                    OR COALESCE(data->>'title', '') ILIKE '%' || replace(replace($3, '%', '\\%'), '_', '\\_') || '%' \
                    OR COALESCE(data->>'description', '') ILIKE '%' || replace(replace($3, '%', '\\%'), '_', '\\_') || '%') \
               -- Authority gate (item 24): knowledge packs are retrievable
               -- ONLY when effective (published, within their validity
               -- window). Draft/superseded/archived documents never enter
               -- the result set as authoritative.
               AND (entity_type <> 'knowledge_pack' \
                    OR (COALESCE(data->>'status', 'draft') = 'effective' \
                        AND (data->>'effective_from' IS NULL \
                             OR (data->>'effective_from')::timestamptz <= NOW()) \
                        AND (data->>'effective_to' IS NULL \
                             OR (data->>'effective_to')::timestamptz >= NOW())))";
        let sql = format!("{base_sql}{site_clause} ORDER BY relevance DESC LIMIT ${limit_param}");

        let mut query_builder = sqlx::query_as::<_, (Uuid, String, serde_json::Value, f32)>(&sql)
            .bind(tenant_id)
            .bind(store_types)
            .bind(query);
        if let (Some(op_types), Some(site_list)) = (operational_store_types, sites) {
            query_builder = query_builder.bind(op_types).bind(site_list);
        }
        let rows = query_builder
            .bind(limit)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Entity store search failed: {e}")))?;

        let mut results = Vec::with_capacity(rows.len());
        for (id, store_type, data, relevance) in rows {
            let title = data
                .get("title")
                .and_then(|v| v.as_str())
                .or_else(|| data.get("name").and_then(|v| v.as_str()))
                .unwrap_or("")
                .to_string();
            let result_type = search_type_of
                .get(store_type.as_str())
                .copied()
                .unwrap_or(store_type.as_str());
            results.push(SearchResult {
                result_type: result_type.to_string(),
                result_id: id,
                result_title: title,
                relevance,
            });
        }
        Ok(results)
    }

    /// Authorized full-text search (Wave B item 10): candidate types are
    /// filtered by the caller's admissible projection BEFORE any query
    /// runs (dropped types are never searched), and operational types are
    /// restricted to the projection's sites inside the SQL. An empty
    /// projection (or an empty entitlement for operational types) returns
    /// no rows — never a search-all-then-filter path.
    pub async fn search_authorized(
        &self,
        tenant_id: EntityId,
        query: &str,
        projection: &AllowedSearchProjection,
    ) -> Result<Vec<SearchResult>> {
        let query = query.trim();
        if query.is_empty() || projection.entity_types().is_empty() {
            return Ok(Vec::new());
        }

        let mut results: Vec<SearchResult> = Vec::new();

        // ── Typed tables (permission-admissible only) ─────────────────
        for &result_type in projection.entity_types() {
            match result_type {
                "user" => results.extend(self.search_users(tenant_id, query, SEARCH_LIMIT).await?),
                "account" => {
                    results.extend(self.search_accounts(tenant_id, query, SEARCH_LIMIT).await?)
                }
                "contact" => {
                    results.extend(self.search_contacts(tenant_id, query, SEARCH_LIMIT).await?)
                }
                "product" => {
                    results.extend(self.search_products(tenant_id, query, SEARCH_LIMIT).await?)
                }
                _ => {}
            }
        }

        // ── Generic entity_store types, split by scope mode ───────────
        // Tenant-mode types are searched without a site predicate;
        // operational types are restricted to the authorized sites (or
        // skipped entirely when the caller has no operational scope).
        let mut tenant_store_types: Vec<String> = Vec::new();
        let mut operational_store_types: Vec<String> = Vec::new();
        for &result_type in projection.entity_types() {
            let Some((_, store_type)) =
                GENERIC_ENTITY_TYPES.iter().find(|(s, _)| *s == result_type)
            else {
                continue;
            };
            match policy_for(result_type).map(|p| p.scope_mode()) {
                Some(ScopeMode::Tenant) => tenant_store_types.push(store_type.to_string()),
                Some(ScopeMode::Operational) => {
                    operational_store_types.push(store_type.to_string())
                }
                None => {}
            }
        }

        if !tenant_store_types.is_empty() {
            results.extend(
                self.search_entity_store_rows(
                    tenant_id,
                    query,
                    &tenant_store_types,
                    None,
                    None,
                    SEARCH_LIMIT,
                )
                .await?,
            );
        }
        if !operational_store_types.is_empty() {
            match projection.sites() {
                // No scope authority (dev deployments): unrestricted.
                None => {
                    results.extend(
                        self.search_entity_store_rows(
                            tenant_id,
                            query,
                            &operational_store_types,
                            None,
                            None,
                            SEARCH_LIMIT,
                        )
                        .await?,
                    );
                }
                // NoOperationalScope (empty): no operational rows —
                // never a tenant-wide fallback.
                Some(sites) => {
                    results.extend(
                        self.search_entity_store_rows(
                            tenant_id,
                            query,
                            &operational_store_types,
                            Some(&operational_store_types),
                            Some(sites),
                            SEARCH_LIMIT,
                        )
                        .await?,
                    );
                }
            }
        }

        // ── Sort by relevance descending, limit to 50 ─────────────────
        results.sort_by(|a, b| {
            b.relevance
                .partial_cmp(&a.relevance)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.result_type.cmp(&b.result_type))
                .then_with(|| a.result_id.cmp(&b.result_id))
        });
        results.truncate(SEARCH_LIMIT as usize);
        Ok(results)
    }

    /// The `entity_type` (store column) values for the search type names in
    /// the given filter; `None` when the filter names a generic type that
    /// is unknown.
    fn store_types_for(filter: Option<&str>) -> Option<Vec<String>> {
        match filter {
            None => Some(
                GENERIC_ENTITY_TYPES
                    .iter()
                    .map(|(_, store_type)| store_type.to_string())
                    .collect(),
            ),
            Some(et) => GENERIC_ENTITY_TYPES
                .iter()
                .find(|(search_type, _)| *search_type == et)
                .map(|(_, store_type)| vec![store_type.to_string()]),
        }
    }
}

#[async_trait]
impl SearchService for DatabaseSearchService {
    /// Execute a full-text search across all entity types for a tenant.
    ///
    /// The query is run per entity type against PostgreSQL (pg_trgm
    /// `similarity()` + ILIKE), always scoped by `tenant_id`, then merged,
    /// sorted by descending relevance and truncated to 50 results.
    async fn search(
        &self,
        tenant_id: EntityId,
        query: &str,
        entity_type: Option<&str>,
    ) -> Result<Vec<SearchResult>> {
        let query = query.trim();
        if query.is_empty() {
            return Ok(Vec::new());
        }

        let mut results: Vec<SearchResult> = Vec::new();

        // ── Typed tables ──────────────────────────────────────────────
        let search_typed =
            entity_type.is_none_or(|et| matches!(et, "user" | "account" | "contact" | "product"));
        if search_typed {
            if entity_type.is_none_or(|et| et == "user") {
                results.extend(self.search_users(tenant_id, query, SEARCH_LIMIT).await?);
            }
            if entity_type.is_none_or(|et| et == "account") {
                results.extend(self.search_accounts(tenant_id, query, SEARCH_LIMIT).await?);
            }
            if entity_type.is_none_or(|et| et == "contact") {
                results.extend(self.search_contacts(tenant_id, query, SEARCH_LIMIT).await?);
            }
            if entity_type.is_none_or(|et| et == "product") {
                results.extend(self.search_products(tenant_id, query, SEARCH_LIMIT).await?);
            }
        }

        // ── Generic entity_store types ────────────────────────────────
        if let Some(store_types) = Self::store_types_for(entity_type) {
            results.extend(
                self.search_entity_store(tenant_id, query, &store_types, SEARCH_LIMIT)
                    .await?,
            );
        }

        // ── Sort by relevance descending, limit to 50 ─────────────────
        results.sort_by(|a, b| {
            b.relevance
                .partial_cmp(&a.relevance)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.result_type.cmp(&b.result_type))
                .then_with(|| a.result_id.cmp(&b.result_id))
        });
        results.truncate(SEARCH_LIMIT as usize);

        Ok(results)
    }

    /// Index (or re-index) a single entity.
    ///
    /// No-op: database-mode search queries the source tables / `entity_store`
    /// directly, so there is no separate search index to maintain (the
    /// `search_index` table was dropped by migration 022).
    async fn index_entity(
        &self,
        _entity_type: &str,
        _entity_id: Uuid,
        _title: &str,
        _searchable_text: &str,
        _tenant_id: EntityId,
    ) -> Result<()> {
        Ok(())
    }

    /// Remove an entity from the search index.
    ///
    /// No-op for the same reason as [`Self::index_entity`].
    async fn remove_from_index(
        &self,
        _entity_type: &str,
        _entity_id: Uuid,
        _tenant_id: EntityId,
    ) -> Result<()> {
        Ok(())
    }
}

/// Authorized database search entry point used by the search route
/// (Wave B item 10): the caller-derived admissible projection (result
/// types the caller may read + authorized operational sites) is pushed
/// into the query so candidate tables are filtered BEFORE ranking.
///
/// The route reaches this directly through `AppState::db_pool` (which is
/// the same pool the installed `DatabaseSearchService` wraps), while
/// in-memory/dev deployments keep the in-memory search service.
pub async fn search_db_authorized(
    pool: &PgPool,
    tenant_id: EntityId,
    query: &str,
    projection: &AllowedSearchProjection,
) -> Result<Vec<SearchResult>> {
    DatabaseSearchService::new(pool.clone())
        .search_authorized(tenant_id, query, projection)
        .await
}
