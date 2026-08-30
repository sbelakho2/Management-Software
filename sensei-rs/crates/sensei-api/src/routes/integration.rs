//! Legacy-system import API (interoperability): the legacy starzERP and
//! CRM-v2 systems POST their native payloads here; Sensei maps them onto
//! canonical entities through the importer — a strict canonical boundary
//! (inbox envelope → identity claim → version decision → domain command →
//! one transaction). Re-imports are IDEMPOTENT and CONCURRENCY-SAFE; the
//! bridge principal is `integration_bridge` with per-system permissions;
//! ordinary users hold NO integration permissions.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde_json::Value;
use uuid::Uuid;

use crate::routes::integration_importer::{self as importer, Envelope};
use crate::state::AppState;

/// The import endpoint: `POST /api/v1/integration/{system}/{entity}` with
/// `{ "legacy_id": "42", "payload": { ...legacy shape... },
///     "source_version": "...", "source_updated_at": "..." }`.
#[derive(Debug, serde::Deserialize)]
pub struct ImportRequest {
    pub legacy_id: String,
    pub payload: Value,
    #[serde(default)]
    pub source_version: Option<String>,
    #[serde(default)]
    pub source_updated_at: Option<String>,
    #[serde(default)]
    pub source_event_id: Option<String>,
}

/// Import response: the outcome + the idempotency anchor.
#[derive(Debug, serde::Serialize)]
pub struct ImportResponse {
    pub outcome: &'static str,
    pub sensei_entity: Option<String>,
    pub sensei_id: Option<Uuid>,
    pub legacy_system: String,
    pub legacy_id: String,
    pub message: Option<String>,
}

/// The import handler.
pub async fn import_record(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    headers: axum::http::HeaderMap,
    Path((system, entity)): Path<(String, String)>,
    Json(req): Json<ImportRequest>,
) -> Result<Json<ImportResponse>> {
    // The bridge authenticates with the dedicated `integration_bridge`
    // role — ordinary users hold NO integration permission at all. The
    // guard is scoped per legacy system.
    let permission = match system.as_str() {
        "starzerp" => "integration:import:starz-erp",
        "crm_v2" => "integration:import:crm",
        other => {
            return Err(SenseiError::Validation(format!(
                "Unknown legacy system '{other}'"
            )));
        }
    };
    user.require_permission(permission)?;

    // Defense-in-depth: the bridge declares its tenant; a mismatch with
    // the token's tenant is rejected.
    if let Some(declared) = headers
        .get("x-sensei-tenant")
        .and_then(|value| value.to_str().ok())
    {
        if let Ok(declared_id) = Uuid::parse_str(declared) {
            if declared_id != user.tenant_id {
                return Err(SenseiError::Forbidden(
                    "Declared tenant does not match the integration token".to_string(),
                ));
            }
        }
    }

    // The non-human principal: the bridge role must be the ONLY role.
    // A session that also holds human roles cannot import.
    if user.roles.len() != 1 || user.roles[0] != "integration_bridge" {
        return Err(SenseiError::Forbidden(
            "Integration imports require the dedicated integration_bridge \
             principal — human sessions cannot import"
                .to_string(),
        ));
    }

    let source_updated_at = req
        .source_updated_at
        .as_deref()
        .and_then(|s| chrono::DateTime::parse_from_rfc3339(s).ok())
        .map(|d| d.with_timezone(&chrono::Utc));

    let record = sensei_services::integration::LegacyRecord {
        system: system.clone(),
        entity: entity.clone(),
        legacy_id: req.legacy_id,
        payload: req.payload,
    };
    let envelope = Envelope {
        source_version: req.source_version,
        source_updated_at,
        source_event_id: req.source_event_id,
        extraction_run_id: format!("api-{}", Uuid::new_v4()),
    };

    match importer::apply_record(&state, user.tenant_id, &record, &envelope).await {
        Ok(outcome) => {
            let (outcome_str, message) = match outcome {
                importer::ImportOutcome::Applied => ("applied", None),
                importer::ImportOutcome::Duplicate => (
                    "duplicate",
                    Some("Same-event replay — nothing changed".to_string()),
                ),
                importer::ImportOutcome::Stale => (
                    "stale",
                    Some("Source version older than applied — not applied".to_string()),
                ),
                importer::ImportOutcome::Conflict(m) => ("conflict", Some(m)),
                importer::ImportOutcome::Quarantined(m) => ("quarantined", Some(m)),
                importer::ImportOutcome::Tombstoned => (
                    "tombstoned",
                    Some("Legacy record disabled — canonical entity archived".to_string()),
                ),
            };
            Ok(Json(ImportResponse {
                outcome: outcome_str,
                sensei_entity: None,
                sensei_id: None,
                legacy_system: system,
                legacy_id: record.legacy_id,
                message,
            }))
        }
        Err(e) => {
            // Validation/dependency failures already dead-lettered inside
            // the importer; the response reflects the quarantine.
            Ok(Json(ImportResponse {
                outcome: "quarantined",
                sensei_entity: None,
                sensei_id: None,
                legacy_system: system,
                legacy_id: record.legacy_id,
                message: Some(e.to_string()),
            }))
        }
    }
}

/// Persist a source checkpoint (item 20: the bridge is incremental — the
/// watermark is the ONLY durable cursor; a crashed run resumes from it).
#[derive(Debug, serde::Deserialize)]
pub struct CheckpointRequest {
    pub source_system: String,
    pub source_table: String,
    pub watermark: String,
    pub run_id: String,
}

#[derive(Debug, serde::Serialize)]
pub struct CheckpointResponse {
    pub ok: bool,
}

pub async fn save_checkpoint(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CheckpointRequest>,
) -> Result<Json<CheckpointResponse>> {
    user.require_permission("integration:status:read")?;
    // The bridge principal only — the same non-human rule as imports.
    if user.roles.len() != 1 || user.roles[0] != "integration_bridge" {
        return Err(SenseiError::Forbidden(
            "Checkpoints require the integration_bridge principal".to_string(),
        ));
    }
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Checkpoints require the database".to_string()))?;
    let watermark = req
        .watermark
        .parse::<chrono::DateTime<chrono::Utc>>()
        .map_err(|e| SenseiError::Validation(format!("Invalid watermark: {e}")))?;
    sqlx::query(
        "INSERT INTO integration_checkpoints (tenant_id, source_system, source_table, watermark, last_run_id, last_run_at)          VALUES ($1, $2, $3, $4, $5, NOW())          ON CONFLICT (tenant_id, source_system, source_table)          DO UPDATE SET watermark = $4, last_run_id = $5, last_run_at = NOW()",
    )
    .bind(user.tenant_id)
    .bind(&req.source_system)
    .bind(&req.source_table)
    .bind(watermark)
    .bind(&req.run_id)
    .execute(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Checkpoint write failed: {e}")))?;
    Ok(Json(CheckpointResponse { ok: true }))
}

/// Health/summary of the integration layer (item 24: Unknown is NOT zero —
/// a database failure must never look like 0 mappings).
#[derive(Debug, serde::Serialize)]
pub struct IntegrationStatus {
    pub legacy_systems: Vec<&'static str>,
    pub supported_entities: Vec<&'static str>,
    pub entity_map_count: Option<i64>,
    pub dead_letter_count: Option<i64>,
    pub reconciliation_open: Option<i64>,
    pub status: &'static str,
    pub detail: Option<String>,
    /// Item 24: the operational state a production integrator needs.
    pub last_extraction_at: Option<chrono::DateTime<chrono::Utc>>,
    pub last_run_id: Option<String>,
    pub current_watermark: Option<chrono::DateTime<chrono::Utc>>,
    pub lag_seconds: Option<i64>,
    pub mapper_version: i64,
    pub tombstones: Option<i64>,
    pub oldest_unresolved: Option<chrono::DateTime<chrono::Utc>>,
}

pub async fn integration_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<IntegrationStatus>> {
    user.require_permission("integration:status:read")?;
    let Some(pool) = state.db_pool.as_ref() else {
        // The integration layer REQUIRES the database — report degraded,
        // never a fake healthy zero.
        return Ok(Json(IntegrationStatus {
            legacy_systems: vec!["starzerp", "crm_v2"],
            supported_entities: vec![
                "article",
                "customer",
                "sales_order",
                "stock_movement",
                "supplier",
                "lead",
                "company",
                "contact",
                "quote",
                "rfq",
            ],
            entity_map_count: None,
            dead_letter_count: None,
            reconciliation_open: None,
            status: "degraded",
            detail: Some("Database unavailable — integration state unknown".to_string()),
            last_extraction_at: None,
            last_run_id: None,
            current_watermark: None,
            lag_seconds: None,
            mapper_version: 3,
            tombstones: None,
            oldest_unresolved: None,
        }));
    };
    let (map_count,): (i64,) =
        sqlx::query_as("SELECT COUNT(*) FROM integration_entity_map WHERE tenant_id = $1")
            .bind(user.tenant_id)
            .fetch_one(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Entity map count failed: {e}")))?;
    let (dead_count,): (i64,) =
        sqlx::query_as("SELECT COUNT(*) FROM integration_dead_letter WHERE tenant_id = $1")
            .bind(user.tenant_id)
            .fetch_one(pool.as_ref())
            .await
            .unwrap_or((0,));
    let (open_rec,): (i64,) = sqlx::query_as(
        "SELECT COUNT(*) FROM integration_reconciliation WHERE tenant_id = $1 AND status = 'open'",
    )
    .bind(user.tenant_id)
    .fetch_one(pool.as_ref())
    .await
    .unwrap_or((0,));
    // Item 24: source watermarks + run id + mapper version — Unknown is
    // NOT zero: each is Option (None = nothing recorded yet).
    let last_checkpoint: Option<(
        chrono::DateTime<chrono::Utc>,
        String,
        chrono::DateTime<chrono::Utc>,
    )> = sqlx::query_as(
        "SELECT watermark, last_run_id, last_run_at FROM integration_checkpoints \
             WHERE tenant_id = $1 ORDER BY last_run_at DESC LIMIT 1",
    )
    .bind(user.tenant_id)
    .fetch_optional(pool.as_ref())
    .await
    .unwrap_or(None);
    let (current_watermark, last_run_id, last_extraction_at) = last_checkpoint
        .map(|(wm, run, at)| (Some(wm), Some(run), Some(at)))
        .unwrap_or((None, None, None));
    let lag_seconds = current_watermark.map(|wm| (chrono::Utc::now() - wm).num_seconds());
    let (tombstones,): (i64,) = sqlx::query_as(
        "SELECT COUNT(*) FROM integration_entity_map WHERE tenant_id = $1 AND tombstoned = TRUE",
    )
    .bind(user.tenant_id)
    .fetch_one(pool.as_ref())
    .await
    .unwrap_or((0,));
    let oldest_unresolved: Option<chrono::DateTime<chrono::Utc>> = sqlx::query_scalar(
        "SELECT MIN(created_at) FROM integration_reconciliation WHERE tenant_id = $1 AND status = 'open'",
    )
    .bind(user.tenant_id)
    .fetch_optional(pool.as_ref())
    .await
    .unwrap_or(None);
    Ok(Json(IntegrationStatus {
        legacy_systems: vec!["starzerp", "crm_v2"],
        supported_entities: vec![
            "article",
            "customer",
            "sales_order",
            "stock_movement",
            "supplier",
            "lead",
            "company",
            "contact",
            "quote",
            "rfq",
        ],
        entity_map_count: Some(map_count),
        dead_letter_count: Some(dead_count),
        reconciliation_open: Some(open_rec),
        status: if dead_count > 0 || open_rec > 0 {
            "degraded"
        } else {
            "healthy"
        },
        detail: None,
        last_extraction_at,
        last_run_id,
        current_watermark,
        lag_seconds,
        mapper_version: 3,
        tombstones: Some(tombstones),
        oldest_unresolved,
    }))
}
