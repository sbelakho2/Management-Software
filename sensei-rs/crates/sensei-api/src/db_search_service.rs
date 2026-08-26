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
    /// entity types, scoped to the tenant.
    async fn search_entity_store(
        &self,
        tenant_id: EntityId,
        query: &str,
        store_types: &[String],
        limit: i64,
    ) -> Result<Vec<SearchResult>> {
        // Reverse map: store entity_type -> search result type name.
        let search_type_of: HashMap<&str, &str> =
            GENERIC_ENTITY_TYPES.iter().map(|(s, e)| (*e, *s)).collect();

        let rows = sqlx::query_as::<_, (Uuid, String, serde_json::Value, f32)>(
            "SELECT id, entity_type, data, \
                GREATEST(similarity(COALESCE(data->>'name', ''), $3), \
                         similarity(COALESCE(data->>'title', ''), $3), \
                         similarity(COALESCE(data->>'description', ''), $3)) AS relevance \
             FROM entity_store \
             WHERE tenant_id = $1 AND entity_type = ANY($2) \
               AND (COALESCE(data->>'name', '') ILIKE '%' || replace(replace($3, '%', '\\%'), '_', '\\_') || '%' \
                    OR COALESCE(data->>'title', '') ILIKE '%' || replace(replace($3, '%', '\\%'), '_', '\\_') || '%' \
                    OR COALESCE(data->>'description', '') ILIKE '%' || replace(replace($3, '%', '\\%'), '_', '\\_') || '%') \
             ORDER BY relevance DESC \
             LIMIT $4",
        )
        .bind(tenant_id)
        .bind(store_types)
        .bind(query)
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
