//! Lessons (fifteenth audit 46-47/A19): explicit lesson objects with
//! context signatures and APPLICABILITY. Yokoten: a lesson from another
//! site is OFFERED as a comparison — local teams verify applicability
//! before adoption; the status ladder proposed -> verified (locally) ->
//! adopted makes the transfer an experiment.

use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// A lesson row (the read model returned by `yokoten_match`).
#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct Lesson {
    pub id: Uuid,
    pub lesson_id: String,
    pub title: String,
    pub source_problem_id: Option<Uuid>,
    pub context_signature: serde_json::Value,
    pub hypothesis: Option<String>,
    pub countermeasure: String,
    pub observed_result: serde_json::Value,
    pub confidence: Option<f64>,
    pub applicability: serde_json::Value,
    pub status: String,
    pub origin_site_id: Option<Uuid>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Payload for recording a lesson (always inserted as `proposed`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewLesson {
    pub lesson_id: String,
    pub title: String,
    pub source_problem_id: Option<Uuid>,
    #[serde(default)]
    pub context_signature: serde_json::Value,
    pub hypothesis: Option<String>,
    pub countermeasure: String,
    #[serde(default)]
    pub observed_result: serde_json::Value,
    pub confidence: Option<f64>,
    #[serde(default)]
    pub applicability: serde_json::Value,
    pub origin_site_id: Option<Uuid>,
}

const LESSON_COLUMNS: &str = "id, lesson_id, title, source_problem_id, context_signature, \
    hypothesis, countermeasure, observed_result, confidence, applicability, status, \
    origin_site_id, created_at";

/// Transaction-scoped tenant context for the RLS policy (FAIL-CLOSED:
/// missing context = no rows), same convention as
/// `crates/sensei-services/src/tps/skills.rs`.
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

/// Run `f` inside a transaction with the RLS tenant context set.
async fn with_tenant_tx<T, F>(pool: &sqlx::PgPool, tenant_id: Uuid, f: F) -> Result<T>
where
    F: for<'t> FnOnce(
        &'t mut sqlx::Transaction<'_, sqlx::Postgres>,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = std::result::Result<T, SenseiError>> + Send + 't>,
    >,
{
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin tenant tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let result = f(&mut tx).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit tenant tx: {e}")))?;
    Ok(result)
}

/// Record a lesson. Every lesson enters the ladder as `proposed` — the
/// local team, not the recorder, decides whether the countermeasure
/// applies HERE. Idempotent on `(tenant_id, lesson_id)` via upsert.
pub async fn record_lesson(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    lesson: NewLesson,
) -> Result<Uuid> {
    if lesson.lesson_id.trim().is_empty() || lesson.countermeasure.trim().is_empty() {
        return Err(SenseiError::Validation(
            "lesson_id and countermeasure are required".to_string(),
        ));
    }
    let id = Uuid::new_v4();
    let lesson_id = lesson.lesson_id.clone();
    let title = lesson.title.clone();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            sqlx::query(
                "INSERT INTO lessons \
                     (id, tenant_id, lesson_id, title, source_problem_id, context_signature, \
                      hypothesis, countermeasure, observed_result, confidence, applicability, \
                      status, origin_site_id) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'proposed', $12) \
                 ON CONFLICT (tenant_id, lesson_id) DO UPDATE SET \
                     title = EXCLUDED.title, \
                     source_problem_id = EXCLUDED.source_problem_id, \
                     context_signature = EXCLUDED.context_signature, \
                     hypothesis = EXCLUDED.hypothesis, \
                     countermeasure = EXCLUDED.countermeasure, \
                     observed_result = EXCLUDED.observed_result, \
                     confidence = EXCLUDED.confidence, \
                     applicability = EXCLUDED.applicability, \
                     origin_site_id = EXCLUDED.origin_site_id, \
                     status = 'proposed', \
                     updated_at = NOW()",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(&lesson_id)
            .bind(&title)
            .bind(lesson.source_problem_id)
            .bind(lesson.context_signature.clone())
            .bind(&lesson.hypothesis)
            .bind(&lesson.countermeasure)
            .bind(lesson.observed_result.clone())
            .bind(lesson.confidence)
            .bind(lesson.applicability.clone())
            .bind(lesson.origin_site_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to record lesson: {e}")))?;
            Ok(id)
        })
    })
    .await
}

/// Fetch a single lesson by id (used by the routes to return the row
/// after a state transition).
pub async fn get_lesson(pool: &sqlx::PgPool, tenant_id: Uuid, id: Uuid) -> Result<Lesson> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            sqlx::query_as(&format!(
                "SELECT {LESSON_COLUMNS} FROM lessons \
                 WHERE id = $1 AND tenant_id = $2"
            ))
            .bind(id)
            .bind(tenant_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to fetch lesson: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("lesson {id}")))
        })
    })
    .await
}

/// The LOCAL verification act: the local team ran the comparison and the
/// experiment passed (`verified_locally`) or failed (`rejected`). Only a
/// `proposed` lesson can be decided — the yokoten offer is never
/// auto-accepted.
pub async fn mark_verified(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    id: Uuid,
    verified_locally: bool,
) -> Result<()> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let status = if verified_locally {
                "verified"
            } else {
                "rejected"
            };
            let result = sqlx::query(
                "UPDATE lessons SET status = $1, updated_at = NOW() \
                 WHERE id = $2 AND tenant_id = $3 AND status = 'proposed'",
            )
            .bind(status)
            .bind(id)
            .bind(tenant_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to mark lesson verified: {e}")))?;
            if result.rows_affected() == 0 {
                return Err(SenseiError::Validation(
                    "only a PROPOSED lesson can be locally verified or rejected".to_string(),
                ));
            }
            Ok(())
        })
    })
    .await
}

/// Adopt a lesson — the final gate of the yokoten experiment. Only a
/// lesson the local team already verified (`verified`) can be adopted;
/// rejected lessons stay rejected.
pub async fn adopt(pool: &sqlx::PgPool, tenant_id: Uuid, id: Uuid) -> Result<()> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let result = sqlx::query(
                "UPDATE lessons SET status = 'adopted', updated_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2 AND status = 'verified'",
            )
            .bind(id)
            .bind(tenant_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to adopt lesson: {e}")))?;
            if result.rows_affected() == 0 {
                return Err(SenseiError::Validation(
                    "only a VERIFIED lesson can be adopted — the local experiment must pass first"
                        .to_string(),
                ));
            }
            Ok(())
        })
    })
    .await
}

/// Yokoten matching (law A19): a lesson from another site is OFFERED as a
/// comparison — "a similar issue was resolved elsewhere — would you like
/// to compare conditions?" — never a blind copy. RLS forbids cross-tenant
/// reads, so the corporate layer (out of scope here) propagates lessons to
/// other tenants as `proposed` with `origin_site_id` set; the local tenant
/// then matches those proposals against its own context and verifies
/// locally.
///
/// The match is deliberately permissive on the SQL side (any shared
/// context_signature KEY) and then filtered in Rust to require at least
/// one shared key with an EQUAL value — the actual condition overlap.
/// Only `proposed`/`verified` lessons are offered: rejected lessons are
/// dead and adopted ones are already in use here.
pub async fn yokoten_match(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    context_signature: serde_json::Value,
) -> Result<Vec<Lesson>> {
    let signature = context_signature.clone();
    let rows = with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let rows: Vec<Lesson> = sqlx::query_as(&format!(
                "SELECT {LESSON_COLUMNS} FROM lessons \
                 WHERE tenant_id = $1 \
                   AND status IN ('proposed','verified') \
                   AND context_signature ?| ARRAY(SELECT jsonb_object_keys($2::jsonb)) \
                 ORDER BY confidence DESC NULLS LAST, created_at DESC"
            ))
            .bind(tenant_id)
            .bind(signature.clone())
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to match lessons: {e}")))?;
            Ok(rows)
        })
    })
    .await?;

    // Rust-side filter: at least one shared key with an equal value.
    let query = context_signature.as_object().cloned().unwrap_or_default();
    Ok(rows
        .into_iter()
        .filter(|lesson| {
            lesson
                .context_signature
                .as_object()
                .map(|obj| {
                    query
                        .iter()
                        .any(|(key, value)| obj.get(key).is_some_and(|v| v == value))
                })
                .unwrap_or(false)
        })
        .collect())
}

/// Countermeasure recommender (fifteenth audit items 12/14): for a
/// recurring condition, OFFER prior countermeasures whose context
/// signature overlaps the condition — as hypotheses with applicability,
/// never as prescriptions (A19: local teams verify).
///
/// Only lessons the local team already resolved (`verified` or `adopted`)
/// are offered: a `proposed` yokoten transfer is still an untested offer,
/// and a `rejected` one is dead. Matching reuses `yokoten_match`'s
/// semantics — permissive SQL key overlap, then the Rust-side filter
/// requiring at least one shared key with an EQUAL value — ordered by
/// confidence DESC, limited to 5.
pub async fn recommend_countermeasures(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    condition_context: serde_json::Value,
) -> Result<Vec<Lesson>> {
    let signature = condition_context.clone();
    let rows = with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let rows: Vec<Lesson> = sqlx::query_as(&format!(
                "SELECT {LESSON_COLUMNS} FROM lessons \
                 WHERE tenant_id = $1 \
                   AND status IN ('verified','adopted') \
                   AND context_signature ?| ARRAY(SELECT jsonb_object_keys($2::jsonb)) \
                 ORDER BY confidence DESC NULLS LAST, created_at DESC"
            ))
            .bind(tenant_id)
            .bind(signature.clone())
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Failed to recommend countermeasures: {e}"))
            })?;
            Ok(rows)
        })
    })
    .await?;

    // Same overlap rule as yokoten_match: at least one shared key with an
    // equal value — the actual condition overlap, applied AFTER the
    // permissive SQL key prefilter so ranking is never skewed.
    let query = condition_context.as_object().cloned().unwrap_or_default();
    Ok(rows
        .into_iter()
        .filter(|lesson| {
            lesson
                .context_signature
                .as_object()
                .map(|obj| {
                    query
                        .iter()
                        .any(|(key, value)| obj.get(key).is_some_and(|v| v == value))
                })
                .unwrap_or(false)
        })
        .take(5)
        .collect())
}
