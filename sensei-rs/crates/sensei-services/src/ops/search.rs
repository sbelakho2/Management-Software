//! Full-text search service for the Sensei ERP system.
//!
//! Provides a unified search capability across multiple entity types
//! (users, accounts, contacts, products, tasks, kanban cards, obeya items,
//! knowledge packs, training courses, work centers, and more) using
//! PostgreSQL `pg_trgm` trigram similarity for database-backed environments,
//! and in-memory scanning for development/testing.
//!
//! Also supports event-driven indexing via [`SearchService::index_entity`]
//! and [`SearchService::remove_from_index`] for real-time search index updates.

use async_trait::async_trait;
use serde::Serialize;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::EntityId;
use sqlx::PgPool;
use uuid::Uuid;

use crate::accounts::AccountsService;
use crate::contacts::ContactsService;
use crate::products::ProductsService;
use crate::users::UsersService;
use std::sync::{Arc, RwLock};

// ---------------------------------------------------------------------------
// DTO
// ---------------------------------------------------------------------------

/// A single search result returned by the unified search.
#[derive(Debug, Clone, Serialize)]
pub struct SearchResult {
    /// The entity type: "user", "account", "contact", "product", "task", etc.
    pub result_type: String,
    /// The unique identifier of the matched entity.
    pub result_id: Uuid,
    /// A human-readable title for the result (e.g., entity name).
    pub result_title: String,
    /// Relevance score (higher = more relevant).
    pub relevance: f32,
}

// ---------------------------------------------------------------------------
// Searchable Entity Provider Trait
// ---------------------------------------------------------------------------

/// A provider that can search its owned entities for a given query.
///
/// Implemented by entity stores (e.g., `EntityStore<Task>`) so that the
/// [`InMemorySearchService`] can search across PM entities that live in
/// the application state rather than in a domain service.
#[async_trait]
pub trait SearchableEntityProvider: Send + Sync {
    /// Search all entities managed by this provider for the given query.
    async fn search_entities(
        &self,
        tenant_id: EntityId,
        query: &str,
    ) -> Result<Vec<SearchResult>>;

    /// The entity type name returned in [`SearchResult::result_type`].
    fn entity_type_name(&self) -> &str;
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Unified full-text search service.
#[async_trait]
pub trait SearchService: Send + Sync {
    /// Execute a full-text search across all entity types for a tenant.
    ///
    /// Returns up to 50 results ordered by descending relevance.
    /// Pass `entity_type = Some("task")` to scope results to a single type.
    async fn search(
        &self,
        tenant_id: EntityId,
        query: &str,
        entity_type: Option<&str>,
    ) -> Result<Vec<SearchResult>>;

    /// Index (or re-index) a single entity into the search index.
    ///
    /// Called by event bus subscribers when an entity is created or updated.
    /// The `searchable_text` should be a concatenation of all text fields.
    async fn index_entity(
        &self,
        entity_type: &str,
        entity_id: Uuid,
        title: &str,
        searchable_text: &str,
        tenant_id: EntityId,
    ) -> Result<()>;

    /// Remove an entity from the search index.
    ///
    /// Called by event bus subscribers when an entity is deleted.
    async fn remove_from_index(
        &self,
        entity_type: &str,
        entity_id: Uuid,
        tenant_id: EntityId,
    ) -> Result<()>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// An entity that has been indexed via [`SearchService::index_entity`].
#[derive(Debug, Clone)]
struct IndexedEntity {
    entity_type: String,
    entity_id: Uuid,
    title: String,
    searchable_text: String,
    tenant_id: EntityId,
}

/// In-memory implementation of [`SearchService`].
///
/// Delegates to the domain services' `list_*` methods and to any registered
/// [`SearchableEntityProvider`]s, then applies client-side string similarity
/// scoring. Also maintains an in-memory index for entities added via
/// [`index_entity`](SearchService::index_entity).
///
/// Suitable for development, testing, and demo environments without a database.
pub struct InMemorySearchService {
    accounts_service: Arc<dyn AccountsService>,
    contacts_service: Arc<dyn ContactsService>,
    products_service: Arc<dyn ProductsService>,
    users_service: Arc<dyn UsersService>,
    entity_providers: Vec<Arc<dyn SearchableEntityProvider>>,
    /// Entities added via [`SearchService::index_entity`].
    indexed_entities: Arc<RwLock<Vec<IndexedEntity>>>,
}

impl InMemorySearchService {
    /// Create a new [`InMemorySearchService`].
    pub fn new(
        accounts_service: Arc<dyn AccountsService>,
        contacts_service: Arc<dyn ContactsService>,
        products_service: Arc<dyn ProductsService>,
        users_service: Arc<dyn UsersService>,
    ) -> Self {
        Self {
            accounts_service,
            contacts_service,
            products_service,
            users_service,
            entity_providers: Vec::new(),
            indexed_entities: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Register a [`SearchableEntityProvider`] for searching PM entity stores.
    pub fn with_entity_provider(mut self, provider: Arc<dyn SearchableEntityProvider>) -> Self {
        self.entity_providers.push(provider);
        self
    }

    /// Register multiple [`SearchableEntityProvider`]s.
    pub fn with_entity_providers(
        mut self,
        providers: Vec<Arc<dyn SearchableEntityProvider>>,
    ) -> Self {
        self.entity_providers.extend(providers);
        self
    }

    fn score_match(query: &str, target: &str) -> f32 {
        let lower_q = query.to_lowercase();
        let lower_t = target.to_lowercase();

        if lower_t == lower_q {
            1.0
        } else if lower_t.starts_with(&lower_q) {
            0.8
        } else if lower_t.contains(&lower_q) {
            0.5
        } else {
            let q_words: Vec<&str> = lower_q.split_whitespace().collect();
            let t_words: Vec<&str> = lower_t.split_whitespace().collect();
            let matches = q_words.iter().filter(|w| t_words.contains(w)).count();
            if matches > 0 {
                matches as f32 / q_words.len() as f32 * 0.4
            } else {
                0.0
            }
        }
    }

    fn best_score(query: &str, fields: &[&str]) -> f32 {
        fields
            .iter()
            .map(|f| Self::score_match(query, f))
            .fold(0.0_f32, f32::max)
    }

    /// Search the in-memory indexed entities for matches.
    fn search_indexed(
        &self,
        tenant_id: EntityId,
        query: &str,
        entity_type: Option<&str>,
    ) -> Vec<SearchResult> {
        let index = match self.indexed_entities.read() {
            Ok(guard) => guard,
            Err(_) => return Vec::new(),
        };

        let mut results: Vec<SearchResult> = Vec::new();
        for entry in index.iter() {
            if entry.tenant_id != tenant_id {
                continue;
            }
            if let Some(et) = entity_type {
                if entry.entity_type != et {
                    continue;
                }
            }
            let score = Self::best_score(query, &[&entry.title, &entry.searchable_text]);
            if score > 0.0 {
                results.push(SearchResult {
                    result_type: entry.entity_type.clone(),
                    result_id: entry.entity_id,
                    result_title: entry.title.clone(),
                    relevance: score,
                });
            }
        }
        results
    }
}

#[async_trait]
impl SearchService for InMemorySearchService {
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

        // ── Search domain services ──────────────────────────────────────────
        // (only when no entity_type filter or filter matches)

        let search_domain = entity_type.map_or(true, |et| {
            matches!(et, "account" | "contact" | "product" | "user")
        });

        if search_domain {
            // Search accounts
            if entity_type.map_or(true, |et| et == "account") {
                let accounts = self
                    .accounts_service
                    .list_accounts(tenant_id, None, None, Some(1), Some(200))
                    .await?;
                for a in accounts.data {
                    let name_score = Self::score_match(query, &a.name);
                    let email_score = a.email.as_ref().map(|e| Self::score_match(query, e)).unwrap_or(0.0);
                    let tax_score = a.tax_id.as_ref().map(|t| Self::score_match(query, t)).unwrap_or(0.0);
                    let score = name_score.max(email_score).max(tax_score);
                    if score > 0.0 {
                        results.push(SearchResult {
                            result_type: "account".to_string(),
                            result_id: a.id,
                            result_title: a.name,
                            relevance: score,
                        });
                    }
                }
            }

            // Search contacts
            if entity_type.map_or(true, |et| et == "contact") {
                let contacts = self
                    .contacts_service
                    .list_contacts(tenant_id, None, Some(1), Some(200))
                    .await?;
                for c in contacts.data {
                    let full_name = format!("{} {}", c.first_name, c.last_name);
                    let score = Self::best_score(query, &[&full_name, &c.email]);
                    if score > 0.0 {
                        results.push(SearchResult {
                            result_type: "contact".to_string(),
                            result_id: c.id,
                            result_title: full_name,
                            relevance: score,
                        });
                    }
                }
            }

            // Search products
            if entity_type.map_or(true, |et| et == "product") {
                let products = self
                    .products_service
                    .list_products(tenant_id, None, None, Some(1), Some(200))
                    .await?;
                for p in products.data {
                    let name_score = Self::score_match(query, &p.name);
                    let sku_score = Self::score_match(query, &p.sku);
                    let desc_score = p.description.as_ref().map(|d| Self::score_match(query, d)).unwrap_or(0.0);
                    let score = name_score.max(sku_score).max(desc_score);
                    if score > 0.0 {
                        results.push(SearchResult {
                            result_type: "product".to_string(),
                            result_id: p.id,
                            result_title: p.name,
                            relevance: score,
                        });
                    }
                }
            }

            // Search users
            if entity_type.map_or(true, |et| et == "user") {
                let users = self
                    .users_service
                    .list_users_paginated(None, None, Some(1), Some(200))
                    .await?;
                for u in users.data {
                    if u.tenant_id != tenant_id {
                        continue;
                    }
                    let score = Self::best_score(query, &[&u.name, &u.email]);
                    if score > 0.0 {
                        results.push(SearchResult {
                            result_type: "user".to_string(),
                            result_id: u.id,
                            result_title: u.name,
                            relevance: score,
                        });
                    }
                }
            }
        }

        // ── Search entity providers (PM stores) ─────────────────────────────
        for provider in &self.entity_providers {
            let p_entity_type = provider.entity_type_name();
            if entity_type.map_or(true, |et| et == p_entity_type) {
                match provider.search_entities(tenant_id, query).await {
                    Ok(mut entities) => results.append(&mut entities),
                    Err(e) => {
                        tracing::warn!(
                            error = %e,
                            entity_type = %p_entity_type,
                            "SearchableEntityProvider failed"
                        );
                    }
                }
            }
        }

        // ── Search indexed entities (event-bus-based indexing) ─────────────
        let indexed = self.search_indexed(tenant_id, query, entity_type);
        results.extend(indexed);

        // ── Sort by relevance descending, limit to 50 ───────────────────────
        results.sort_by(|a, b| b.relevance.partial_cmp(&a.relevance).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(50);

        Ok(results)
    }

    async fn index_entity(
        &self,
        entity_type: &str,
        entity_id: Uuid,
        title: &str,
        searchable_text: &str,
        tenant_id: EntityId,
    ) -> Result<()> {
        let mut index = self
            .indexed_entities
            .write()
            .map_err(|e| SenseiError::Internal(format!("Search index lock poisoned: {e}")))?;

        // Remove any existing entry for the same entity
        index.retain(|e| !(e.entity_type == entity_type && e.entity_id == entity_id));

        index.push(IndexedEntity {
            entity_type: entity_type.to_string(),
            entity_id,
            title: title.to_string(),
            searchable_text: searchable_text.to_string(),
            tenant_id,
        });

        Ok(())
    }

    async fn remove_from_index(
        &self,
        entity_type: &str,
        entity_id: Uuid,
        _tenant_id: EntityId,
    ) -> Result<()> {
        let mut index = self
            .indexed_entities
            .write()
            .map_err(|e| SenseiError::Internal(format!("Search index lock poisoned: {e}")))?;

        index.retain(|e| !(e.entity_type == entity_type && e.entity_id == entity_id));

        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Database Implementation
// ---------------------------------------------------------------------------

/// Database-backed implementation of [`SearchService`].
///
/// Uses the PostgreSQL `search_all(query, tenant_id)` function which
/// leverages `pg_trgm` trigram similarity and ILIKE queries for fast,
/// production-grade full-text search.
pub struct DatabaseSearchService {
    pool: PgPool,
}

impl DatabaseSearchService {
    /// Create a new [`DatabaseSearchService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl SearchService for DatabaseSearchService {
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

        let rows = if let Some(et) = entity_type {
            sqlx::query_as::<_, (String, Uuid, String, f32)>(
                "SELECT result_type, result_id, result_title, relevance \
                 FROM search_all($1, $2) WHERE result_type = $3",
            )
            .bind(query)
            .bind(tenant_id)
            .bind(et)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Full-text search failed: {e}")))?
        } else {
            sqlx::query_as::<_, (String, Uuid, String, f32)>(
                "SELECT result_type, result_id, result_title, relevance FROM search_all($1, $2)",
            )
            .bind(query)
            .bind(tenant_id)
            .fetch_all(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Full-text search failed: {e}")))?
        };

        let results = rows
            .into_iter()
            .map(|(result_type, result_id, result_title, relevance)| SearchResult {
                result_type,
                result_id,
                result_title,
                relevance,
            })
            .collect();

        Ok(results)
    }

    async fn index_entity(
        &self,
        entity_type: &str,
        entity_id: Uuid,
        title: &str,
        searchable_text: &str,
        tenant_id: EntityId,
    ) -> Result<()> {
        sqlx::query(
            r#"
            INSERT INTO search_index (entity_type, entity_id, title, searchable_text, tenant_id)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (entity_type, entity_id) DO UPDATE
            SET title = EXCLUDED.title,
                searchable_text = EXCLUDED.searchable_text,
                updated_at = NOW()
            "#,
        )
        .bind(entity_type)
        .bind(entity_id)
        .bind(title)
        .bind(searchable_text)
        .bind(tenant_id)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to index entity: {e}")))?;

        Ok(())
    }

    async fn remove_from_index(
        &self,
        entity_type: &str,
        entity_id: Uuid,
        _tenant_id: EntityId,
    ) -> Result<()> {
        sqlx::query(
            "DELETE FROM search_index WHERE entity_type = $1 AND entity_id = $2",
        )
        .bind(entity_type)
        .bind(entity_id)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to remove from index: {e}")))?;

        Ok(())
    }
}
