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
) -> Result<(axum::http::StatusCode, Json<ImportResponse>)> {
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
            let (outcome_str, message, status) = match outcome {
                importer::ImportOutcome::Applied => ("applied", None, axum::http::StatusCode::OK),
                importer::ImportOutcome::Duplicate => (
                    "duplicate",
                    Some("Same-event replay — nothing changed".to_string()),
                    axum::http::StatusCode::OK,
                ),
                importer::ImportOutcome::Stale => (
                    "stale",
                    Some("Source version older than applied — not applied".to_string()),
                    axum::http::StatusCode::OK,
                ),
                importer::ImportOutcome::Conflict(m) => {
                    ("conflict", Some(m), axum::http::StatusCode::CONFLICT)
                }
                importer::ImportOutcome::Quarantined(m) => (
                    "quarantined",
                    Some(m),
                    axum::http::StatusCode::UNPROCESSABLE_ENTITY,
                ),
                importer::ImportOutcome::Tombstoned => (
                    "tombstoned",
                    Some("Legacy record disabled — canonical entity archived".to_string()),
                    axum::http::StatusCode::OK,
                ),
            };
            Ok((
                status,
                Json(ImportResponse {
                    outcome: outcome_str,
                    sensei_entity: None,
                    sensei_id: None,
                    legacy_system: system,
                    legacy_id: record.legacy_id,
                    message,
                }),
            ))
        }
        Err(e) => {
            // Fourteenth audit: typed error semantics with matching HTTP
            // codes — a transient infrastructure failure is NEVER
            // reported as a permanent "quarantined" record.
            let (status, outcome_str) = match &e {
                sensei_core::error::SenseiError::Validation(_) => (
                    axum::http::StatusCode::UNPROCESSABLE_ENTITY,
                    "permanent_validation",
                ),
                sensei_core::error::SenseiError::Conflict(_) => {
                    (axum::http::StatusCode::CONFLICT, "conflict")
                }
                sensei_core::error::SenseiError::Database(msg) => {
                    let lowered = msg.to_lowercase();
                    if ["deadlock", "timeout", "connection", "pool ", "retry"]
                        .iter()
                        .any(|k| lowered.contains(k))
                    {
                        (
                            axum::http::StatusCode::SERVICE_UNAVAILABLE,
                            "retryable_infrastructure",
                        )
                    } else {
                        (
                            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                            "internal_invariant",
                        )
                    }
                }
                _ => (
                    axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                    "internal_invariant",
                ),
            };
            Ok((
                status,
                Json(ImportResponse {
                    outcome: outcome_str,
                    sensei_entity: None,
                    sensei_id: None,
                    legacy_system: system,
                    legacy_id: record.legacy_id,
                    message: Some(e.to_string()),
                }),
            ))
        }
    }
}

/// Persist a source checkpoint (item 20: the bridge is incremental — the
/// watermark is the ONLY durable cursor; a crashed run resumes from it).
/// Twenty-second audit P1: the checkpoint advances ONE integration
/// INSTANCE (instance_id) — the readiness proof is instance_id, never the
/// legacy tenant-global (source_system, source_table) cursor. The legacy
/// fields are optional metadata only.
/// Twenty-sixth audit P0.2 (one-shot, token-authenticated completion):
/// the request carries the run_token that `start_run` returned — NO
/// client-claimed revision exists anymore. The service consumes the open
/// run ATOMICALLY (token-bound, `completed_at IS NULL`) and records the
/// server-attested configuration revision returned by that consume; a
/// second completion of the same run is refused (Conflict = 409).
#[derive(Debug, serde::Deserialize)]
pub struct CheckpointRequest {
    /// The integration instance this run advances (resolved against the
    /// caller's tenant: unknown → 404, disabled → 409).
    pub instance_id: Uuid,
    /// Optional legacy cursor metadata (kept for bridge compatibility;
    /// no longer required — NULL rows are instance-keyed).
    #[serde(default)]
    pub source_system: Option<String>,
    #[serde(default)]
    pub source_table: Option<String>,
    pub watermark: String,
    /// The composite cursor's primary-key component (updated_at, id).
    #[serde(default)]
    pub watermark_id: Option<String>,
    pub run_id: String,
    /// The server-issued credential from `POST /runs/start`: completing a
    /// run REQUIRES the exact token the server bound to the instance's
    /// configuration at start — a completion without it (or a replay of
    /// an already-consumed run) is refused (Conflict = 409).
    pub run_token: Uuid,
}

#[derive(Debug, serde::Serialize)]
pub struct CheckpointResponse {
    pub ok: bool,
}

/// `POST /api/v1/integration/runs/start` — the bridge asks the SERVER to
/// start a run: the token it receives is bound to the instance's CURRENT
/// configuration revision, so completion can never claim a revision the
/// server did not attest (twenty-fifth audit P1).
#[derive(Debug, serde::Deserialize)]
pub struct StartRunRequest {
    pub instance_id: Uuid,
    pub run_id: String,
}

pub async fn start_run(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<StartRunRequest>,
) -> Result<Json<serde_json::Value>> {
    // Run start is a BRIDGE WRITE — the same gate as checkpoint completion
    // (integration:bridge:write): only the non-human integration bridge
    // may open a run.
    user.require_permission("integration:bridge:write")?;
    // The bridge principal only — the same non-human rule as imports and
    // checkpoint completion: a session that also holds human roles cannot
    // start integration runs.
    if user.roles.len() != 1 || user.roles[0] != "integration_bridge" {
        return Err(SenseiError::Forbidden(
            "Run starts require the integration_bridge principal".to_string(),
        ));
    }
    let Some(pool) = state.db_pool.as_ref() else {
        return Err(sensei_core::error::SenseiError::Database(
            "no database configured".to_string(),
        ));
    };
    let token = sensei_services::tps::integration::start_run(
        pool,
        user.tenant_id,
        req.instance_id,
        req.run_id,
    )
    .await?;
    Ok(Json(serde_json::json!({ "run_token": token })))
}

pub async fn save_checkpoint(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CheckpointRequest>,
) -> Result<Json<CheckpointResponse>> {
    // Completion is a BRIDGE WRITE — the same gate as run start
    // (integration:bridge:write): only the non-human integration bridge
    // may advance a run's checkpoint.
    user.require_permission("integration:bridge:write")?;
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
    // The instance resolution (tenant-scoped) + the write live in the
    // service: an instance invisible under the caller's tenant is
    // NotFound (404); a DISABLED instance refuses advancement with
    // Conflict (409) — a decommissioned instance can never be advanced.
    // Twenty-sixth audit P0.2 (one-shot, token-authenticated
    // completion): the run_token from `POST /runs/start` is the ONLY
    // credential that completes the run — the service consumes the open
    // run ATOMICALLY (run_id + run_token + `completed_at IS NULL`) and
    // uses the configuration state RETURNED by that consume, so the
    // client never claims a revision and an already-completed run can
    // never be replayed into fresh readiness.
    sensei_services::tps::integration::write_checkpoint(
        pool,
        user.tenant_id,
        req.instance_id,
        req.source_system,
        req.source_table,
        watermark,
        req.watermark_id,
        req.run_id,
        req.run_token,
    )
    .await?;
    Ok(Json(CheckpointResponse { ok: true }))
}

/// Read a saved checkpoint watermark (the bridge resumes incrementally).
/// Twenty-second audit P1: a checkpoint that does not exist is NEVER RUN
/// (Unknown) — `watermark` is None, never a fabricated `Utc::now()`.
/// Twenty-third audit P1: the legacy (system, source_table) cursor is
/// RETIRED — checkpoints are instance-keyed, so this read resolves the
/// caller's ACTIVE-SITE instance of the legacy system
/// (tenant, site, integration_type) through the one authoritative
/// RequestContext/agent-context builder (server-derived, never client
/// input) and returns the INSTANCE's checkpoint. A caller with no active
/// site has no instance to resume — fail closed.
#[derive(Debug, serde::Serialize)]
pub struct CheckpointReadResponse {
    pub watermark: Option<chrono::DateTime<chrono::Utc>>,
    #[serde(default)]
    pub watermark_id: Option<String>,
}

pub async fn get_checkpoint(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((system, _source_table)): Path<(String, String)>,
) -> Result<Json<CheckpointReadResponse>> {
    user.require_permission("integration:status:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Checkpoints require the database".to_string()))?;
    // The active site comes from the caller's agent context (built on the
    // RequestContext entitlement/topology proof) — integration instances
    // are site-scoped, so a checkpoint can only be resolved for the site
    // the caller operates in.
    let ctx = crate::routes::agent::build_context(&user, &state).await;
    let site_id = ctx.site_id.ok_or_else(|| {
        SenseiError::Forbidden(
            "no active site context — integration checkpoints are instance-keyed \
             per site; set the caller's active site before reading a checkpoint"
                .to_string(),
        )
    })?;
    // The service resolves the instance (tenant, site, integration_type =
    // the legacy system) and reads ITS checkpoint inside one tenant-scoped
    // transaction; no raw-pool legacy (system, source_table) read remains.
    let checkpoint = sensei_services::tps::integration::get_site_checkpoint(
        pool,
        user.tenant_id,
        site_id,
        &system,
    )
    .await?;
    // A missing instance/checkpoint is None — never Utc::now(): a run
    // that never happened has no cursor.
    let (watermark, watermark_id) = checkpoint
        .map(|state| (Some(state.watermark), state.watermark_id))
        .unwrap_or((None, None));
    Ok(Json(CheckpointReadResponse {
        watermark,
        watermark_id,
    }))
}

/// Health/summary of the integration layer (item 24 + twenty-second audit
/// P1: Unknown is NOT zero — a database failure must never look like 0
/// mappings, 0 dead letters, 0 open reconciliations or no tombstones).
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

/// The epistemically honest degraded body: EVERY count is None (unknown),
/// status 'degraded' — never a fake healthy zero.
fn degraded_integration_status(detail: String) -> IntegrationStatus {
    IntegrationStatus {
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
        detail: Some(detail),
        last_extraction_at: None,
        last_run_id: None,
        current_watermark: None,
        lag_seconds: None,
        mapper_version: 3,
        tombstones: None,
        oldest_unresolved: None,
    }
}

/// The read model of the integration layer, read under ONE error budget
/// and inside ONE tenant-scoped transaction (twenty-third audit P1): the
/// counts live in `sensei_services::tps::integration::read_integration_state`
/// (a with_tenant_tx transaction) — integration tables are FORCE RLS, so
/// the raw-pool reads they replace fabricated zeros under a wrong/missing
/// tenant context. Every query failure PROPAGATES (map_err →
/// SenseiError) so the caller can degrade — a count query that fails can
/// never masquerade as 0.
struct IntegrationSnapshot {
    map_count: i64,
    dead_letter_count: i64,
    reconciliation_open: i64,
    last_checkpoint: Option<(
        chrono::DateTime<chrono::Utc>,
        Option<String>,
        chrono::DateTime<chrono::Utc>,
    )>,
    tombstones: i64,
    oldest_unresolved: Option<chrono::DateTime<chrono::Utc>>,
}

impl IntegrationSnapshot {
    async fn read(pool: &sqlx::PgPool, tenant_id: Uuid) -> std::result::Result<Self, SenseiError> {
        let state =
            sensei_services::tps::integration::read_integration_state(pool, tenant_id).await?;
        Ok(Self {
            map_count: state.entity_map_count,
            dead_letter_count: state.dead_letter_count,
            reconciliation_open: state.reconciliation_open,
            last_checkpoint: state.last_checkpoint,
            tombstones: state.tombstone_count,
            oldest_unresolved: state.oldest_unresolved,
        })
    }
}

pub async fn integration_status(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<IntegrationStatus>> {
    user.require_permission("integration:status:read")?;
    let Some(pool) = state.db_pool.as_ref() else {
        // The integration layer REQUIRES the database — report degraded,
        // never a fake healthy zero.
        return Ok(Json(degraded_integration_status(
            "Database unavailable — integration state unknown".to_string(),
        )));
    };
    // One error budget: ANY count/watermark query failure degrades the
    // whole report (every epistemic value None) — a DB error can never
    // read as 0 dead letters / 0 open reconciliations / no checkpoint.
    // The reads themselves run in ONE tenant-scoped transaction (the
    // service), so RLS can never fabricate zeros.
    let snapshot = match IntegrationSnapshot::read(pool, user.tenant_id).await {
        Ok(snapshot) => snapshot,
        Err(e) => {
            return Ok(Json(degraded_integration_status(format!(
                "Integration state unknown: {e}"
            ))))
        }
    };
    let (current_watermark, last_run_id, last_extraction_at) = snapshot
        .last_checkpoint
        .map(|(wm, run, at)| (Some(wm), run, Some(at)))
        .unwrap_or((None, None, None));
    let lag_seconds = current_watermark.map(|wm| (chrono::Utc::now() - wm).num_seconds());
    let dead_count = snapshot.dead_letter_count;
    let open_rec = snapshot.reconciliation_open;
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
        entity_map_count: Some(snapshot.map_count),
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
        tombstones: Some(snapshot.tombstones),
        oldest_unresolved: snapshot.oldest_unresolved,
    }))
}
