//! Episode memory (fifteenth audit 12/14): historical episodes with
//! associative links; retrieval finds episodes related by SHARED LINKS —
//! a connector failure associates with the same supplier/machine/process
//! even when the text is dissimilar.
//!
//! Episodes are a first-class organizational memory tier: an NCR
//! resolved, an andon with a countermeasure, a standard changed. Each
//! episode carries explicit links (`{kind, id, label}` — supplier,
//! machine, process, material, part family, operator, work center), and
//! [`find_related`] walks those links instead of comparing text, so a
//! "connector intermittent failure" retrieves the "crimp force drop" on
//! the same supplier while a text-similar but link-dissimilar episode
//! stays out.

use sensei_core::error::{Result, SenseiError};
use serde::Serialize;
use uuid::Uuid;

/// A historical operational episode with its associative links.
#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct Episode {
    pub id: Uuid,
    pub episode_type: String,
    pub title: String,
    pub description: Option<String>,
    pub status: String,
    pub outcome: Option<String>,
    pub confidence: Option<f64>,
    pub links: serde_json::Value,
    pub source_entity_type: Option<String>,
    pub source_entity_id: Option<Uuid>,
    pub occurred_at: chrono::DateTime<chrono::Utc>,
    /// Number of links shared with the retrieval probe — populated by
    /// [`find_related`], absent on a plain single-episode fetch.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub shared_links: Option<i64>,
}

/// Transaction-scoped tenant context for the RLS policy (the policy is
/// FAIL-CLOSED: missing context = no rows), same convention as
/// `crates/sensei-services/src/ops/database.rs`.
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> Result<()> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
}

/// Record an episode (an NCR resolved, an andon with a countermeasure, a
/// standard changed). `links` is a JSON array of `{kind, id, label}`
/// objects anchoring the episode in the operational graph — these are the
/// associative retrieval keys.
#[allow(clippy::too_many_arguments)]
pub async fn record_episode(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    episode_type: &str,
    title: &str,
    description: Option<&str>,
    status: &str,
    outcome: Option<&str>,
    confidence: Option<f64>,
    links: Vec<serde_json::Value>,
    source_entity_type: Option<&str>,
    source_entity_id: Option<Uuid>,
) -> Result<Uuid> {
    let links_json = serde_json::Value::Array(links);
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin episode tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let id: Uuid = sqlx::query_scalar(
        "INSERT INTO episodes (tenant_id, episode_type, title, description, status, outcome, \
                               confidence, links, source_entity_type, source_entity_id) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) \
         RETURNING id",
    )
    .bind(tenant_id)
    .bind(episode_type)
    .bind(title)
    .bind(description)
    .bind(status)
    .bind(outcome)
    .bind(confidence)
    .bind(links_json)
    .bind(source_entity_type)
    .bind(source_entity_id)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to record episode: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit episode tx: {e}")))?;
    Ok(id)
}

/// Fetch a single episode by id (tenant-scoped read).
pub async fn get_episode(pool: &sqlx::PgPool, tenant_id: Uuid, id: Uuid) -> Result<Episode> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin episode read tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let row: Option<Episode> = sqlx::query_as(
        "SELECT id, episode_type, title, description, status, outcome, confidence, links, \
                source_entity_type, source_entity_id, occurred_at, NULL::bigint AS shared_links \
         FROM episodes WHERE id = $1 AND tenant_id = $2",
    )
    .bind(id)
    .bind(tenant_id)
    .fetch_optional(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to get episode: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit episode read tx: {e}")))?;
    row.ok_or_else(|| SenseiError::NotFound(format!("Episode {id} not found")))
}

/// ASSOCIATIVE retrieval: episodes sharing ANY link (kind + id) with the
/// probe are returned — text is never consulted, only the links. Each
/// result carries the count of links shared with the probe; results are
/// ranked by shared-link count, then recency.
pub async fn find_related(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    links: &[serde_json::Value],
    limit: i64,
) -> Result<Vec<Episode>> {
    let probe = serde_json::Value::Array(links.to_vec());
    let limit = limit.clamp(1, 200);
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin episode related tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let rows: Vec<Episode> = sqlx::query_as(
        r#"SELECT e.id, e.episode_type, e.title, e.description, e.status, e.outcome,
                  e.confidence, e.links, e.source_entity_type, e.source_entity_id, e.occurred_at,
                  (SELECT COUNT(*) FROM jsonb_array_elements(e.links) l
                   JOIN jsonb_array_elements($2::jsonb) q
                     ON q.value->>'kind' = l.value->>'kind'
                    AND q.value->>'id' = l.value->>'id') AS shared_links
           FROM episodes e
           WHERE e.tenant_id = $1
             AND EXISTS (
                 SELECT 1 FROM jsonb_array_elements(e.links) l
                 JOIN jsonb_array_elements($2::jsonb) q
                   ON q.value->>'kind' = l.value->>'kind'
                  AND q.value->>'id' = l.value->>'id'
             )
           ORDER BY shared_links DESC, e.occurred_at DESC
           LIMIT $3"#,
    )
    .bind(tenant_id)
    .bind(&probe)
    .bind(limit)
    .fetch_all(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to find related episodes: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit episode related tx: {e}")))?;
    Ok(rows)
}
