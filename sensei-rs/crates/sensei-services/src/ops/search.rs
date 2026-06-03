//! Full-text search service for the Sensei ERP system.
//!
//! Provides a unified search capability across multiple entity types
//! (users, accounts, contacts, products) using PostgreSQL `pg_trgm`
//! trigram similarity for database-backed environments, and in-memory
//! scanning for development/testing.

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
use std::sync::Arc;

// ---------------------------------------------------------------------------
// DTO
// ---------------------------------------------------------------------------

/// A single search result returned by the unified search.
#[derive(Debug, Clone, Serialize)]
pub struct SearchResult {
    /// The entity type: "user", "account", "contact", or "product".
    pub result_type: String,
    /// The unique identifier of the matched entity.
    pub result_id: Uuid,
    /// A human-readable title for the result (e.g., entity name).
    pub result_title: String,
    /// Relevance score (higher = more relevant).
    pub relevance: f32,
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
    async fn search(
        &self,
        tenant_id: EntityId,
        query: &str,
    ) -> Result<Vec<SearchResult>>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of [`SearchService`].
///
/// Delegates to the domain services' `list_*` methods, then applies
/// client-side string similarity scoring. Suitable for development,
/// testing, and demo environments without a database.
pub struct InMemorySearchService {
    accounts_service: Arc<dyn AccountsService>,
    contacts_service: Arc<dyn ContactsService>,
    products_service: Arc<dyn ProductsService>,
    users_service: Arc<dyn UsersService>,
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
        }
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
}

#[async_trait]
impl SearchService for InMemorySearchService {
    async fn search(
        &self,
        tenant_id: EntityId,
        query: &str,
    ) -> Result<Vec<SearchResult>> {
        let query = query.trim();
        if query.is_empty() {
            return Ok(Vec::new());
        }

        let mut results: Vec<SearchResult> = Vec::new();

        // Search accounts
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

        // Search contacts
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

        // Search products
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

        // Search users
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

        // Sort by relevance descending, limit to 50
        results.sort_by(|a, b| b.relevance.partial_cmp(&a.relevance).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(50);

        Ok(results)
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
    ) -> Result<Vec<SearchResult>> {
        let query = query.trim();
        if query.is_empty() {
            return Ok(Vec::new());
        }

        let rows = sqlx::query_as::<_, (String, Uuid, String, f32)>(
            "SELECT result_type, result_id, result_title, relevance FROM search_all($1, $2)",
        )
        .bind(query)
        .bind(tenant_id)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Full-text search failed: {e}")))?;

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
}
