//! Document ingestion pipeline (item 72): document perception -> structured
//! elements -> semantic extraction -> HUMAN APPROVAL -> versioned
//! knowledge. OCR output must NEVER automatically become authoritative
//! standard work — every ingested document lands as a draft candidate that
//! a person approves or rejects before it can influence the RAG corpus.
//!
//! The endpoint accepts text/PDF metadata (the perception layer is
//! pluggable — today raw text extraction, with the PaddleOCR-VL class of
//! models as the future vision layer), runs the extraction heuristics,
//! and stores the candidate for review.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

/// Request: upload a document's perception output for ingestion.
#[derive(Debug, Deserialize)]
pub struct IngestDocumentRequest {
    pub title: String,
    pub source_path: String,
    pub mime_type: Option<String>,
    /// The raw perceived text (OCR/vision layer output, or direct paste).
    pub raw_text: String,
    /// Optional structured elements (paragraphs/tables) from the parser.
    #[serde(default)]
    pub structured: Vec<serde_json::Value>,
}

/// One extraction hypothesis (item 72: a CANDIDATE, never authority).
#[derive(Debug, Serialize, Deserialize)]
pub struct ExtractionCandidate {
    /// Authority class the extractor inferred (tps_canonical, ...).
    pub authority: String,
    pub content: String,
    /// The authority classes this text could plausibly be.
    pub possible_authorities: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct IngestedDocument {
    pub id: Uuid,
    pub title: String,
    pub status: String,
    pub candidate: Option<ExtractionCandidate>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Approve/reject an ingested document (the HUMAN gate).
#[derive(Debug, Deserialize)]
pub struct ReviewDocumentRequest {
    pub approve: bool,
    /// On approval: the authority class (enum vocabulary) the person
    /// confirms. On rejection: an optional reason.
    pub authority: Option<String>,
    pub reason: Option<String>,
}

/// Accept a document into the pipeline: extract a candidate, store it for
/// review (never auto-published).
pub async fn ingest_document(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<IngestDocumentRequest>,
) -> Result<Json<IngestedDocument>> {
    user.require_permission("knowledge:manage")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Ingestion requires the database".to_string()))?;
    if req.raw_text.trim().is_empty() {
        return Err(SenseiError::Validation(
            "raw_text is empty — the perception layer produced no content".to_string(),
        ));
    }

    // ── Semantic extraction (heuristics): infer the authority class from
    //    the content, with the possible classes for the human to confirm. ──
    let text = req.raw_text.to_lowercase();
    let mut authority = "employee_note";
    let mut possible = vec!["employee_note", "ai_hypothesis"];
    if text.contains("customer") && (text.contains("requirement") || text.contains("spec")) {
        authority = "customer_requirement";
        possible = vec![
            "customer_requirement",
            "corporate_policy",
            "effective_standard_work",
        ];
    } else if text.contains("standard")
        || text.contains("work instruction")
        || text.contains("procedure")
    {
        authority = "effective_standard_work";
        possible = vec![
            "effective_standard_work",
            "corporate_policy",
            "employee_note",
        ];
    } else if text.contains("policy") || text.contains("procedure") || text.contains("rule") {
        authority = "corporate_policy";
        possible = vec!["corporate_policy", "effective_standard_work"];
    } else if text.contains("tps") || text.contains("lean") || text.contains("jidoka") {
        authority = "tps_canonical";
        possible = vec!["tps_canonical", "corporate_policy"];
    }

    let candidate = serde_json::json!({
        "authority": authority,
        "content": req.raw_text,
        "possible_authorities": possible,
    });
    let id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO document_ingestions  (id, tenant_id, title, source_path, mime_type, raw_text, structured, candidate, status, uploaded_by, created_at, updated_at)  VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, 'extracted', $9, NOW(), NOW())",
    )
    .bind(id)
    .bind(user.tenant_id)
    .bind(&req.title)
    .bind(&req.source_path)
    .bind(&req.mime_type)
    .bind(&req.raw_text)
    .bind(serde_json::Value::Array(req.structured))
    .bind(&candidate)
    .bind(user.user_id)
    .execute(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Ingestion insert failed: {e}")))?;

    Ok(Json(IngestedDocument {
        id,
        title: req.title,
        status: "extracted".to_string(),
        candidate: Some(ExtractionCandidate {
            authority: authority.to_string(),
            content: text,
            possible_authorities: possible.into_iter().map(|s| s.to_string()).collect(),
        }),
        created_at: chrono::Utc::now(),
    }))
}

/// The HUMAN gate: approve (becomes a knowledge pack draft/under_review —
/// still not effective until published) or reject (never enters the RAG
/// corpus).
pub async fn review_document(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<ReviewDocumentRequest>,
) -> Result<Json<IngestedDocument>> {
    user.require_permission("knowledge:manage")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Ingestion requires the database".to_string()))?;

    // The document must exist and still be unreviewed.
    let row: Option<(
        String,
        String,
        String,
        serde_json::Value,
        chrono::DateTime<chrono::Utc>,
    )> = sqlx::query_as(
        "SELECT title, status, raw_text, candidate, created_at \
             FROM document_ingestions WHERE tenant_id = $1 AND id = $2",
    )
    .bind(user.tenant_id)
    .bind(id)
    .fetch_optional(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Ingestion read failed: {e}")))?;
    let Some((title, status, raw_text, candidate, created_at)) = row else {
        return Err(SenseiError::NotFound(format!(
            "Document ingestion {id} not found"
        )));
    };
    if status != "extracted" {
        return Err(SenseiError::Conflict(format!(
            "Document already {status} — it cannot be reviewed twice"
        )));
    }

    if req.approve {
        // The authority must be one of the enum classes (item 74).
        let authority = req.authority.unwrap_or_default();
        let valid = [
            "tps_canonical",
            "corporate_policy",
            "effective_standard_work",
            "customer_requirement",
            "production_fact",
            "historical_case",
            "employee_note",
            "ai_hypothesis",
        ];
        if !valid.contains(&authority.as_str()) {
            return Err(SenseiError::Validation(format!(
                "Authority '{authority}' is not one of: {}",
                valid.join(", ")
            )));
        }
        sqlx::query(
            "UPDATE document_ingestions SET status = 'approved', approved_by = $3, approved_at = NOW(), updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id)
        .bind(user.tenant_id)
        .bind(user.user_id)
        .execute(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Ingestion approve failed: {e}")))?;
        // Create a knowledge pack DRAFT with the approved authority —
        // still not effective; a separate publish flow promotes it.
        let pack_id = Uuid::new_v4();
        let _ = sqlx::query(
            "INSERT INTO entity_store (tenant_id, entity_type, id, data) \
             VALUES ($1, 'knowledge_pack', $2, $3)",
        )
        .bind(user.tenant_id)
        .bind(pack_id)
        .bind(serde_json::json!({
            "title": title,
            "content": raw_text,
            "authority": authority,
            "status": "draft",
            "source_document": id.to_string(),
        }))
        .execute(pool.as_ref())
        .await;
        Ok(Json(IngestedDocument {
            id,
            title,
            status: "approved".to_string(),
            candidate: serde_json::from_value(candidate).ok(),
            created_at,
        }))
    } else {
        sqlx::query(
            "UPDATE document_ingestions SET status = 'rejected', updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id)
        .bind(user.tenant_id)
        .execute(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Ingestion reject failed: {e}")))?;
        Ok(Json(IngestedDocument {
            id,
            title,
            status: "rejected".to_string(),
            candidate: None,
            created_at,
        }))
    }
}

/// List ingestions (pipeline queue).
#[derive(Debug, Serialize)]
pub struct IngestionItem {
    pub id: Uuid,
    pub title: String,
    pub status: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

pub async fn list_ingestions(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<IngestionItem>>> {
    user.require_permission("knowledge:manage")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Ingestion requires the database".to_string()))?;
    let rows: Vec<(Uuid, String, String, chrono::DateTime<chrono::Utc>)> = sqlx::query_as(
        "SELECT id, title, status, created_at FROM document_ingestions \
         WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 200",
    )
    .bind(user.tenant_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Ingestion list failed: {e}")))?;
    Ok(Json(
        rows.into_iter()
            .map(|(id, title, status, created_at)| IngestionItem {
                id,
                title,
                status,
                created_at,
            })
            .collect(),
    ))
}
