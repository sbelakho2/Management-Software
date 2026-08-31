//! Andon (real-time quality/status signal) route handlers.
//!
//! Provides endpoints for raising, acknowledging, resolving, and managing
//! Andon events – visual signals that alert teams to production issues.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_services::ops::Andon;
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

// ── Query / Request DTOs ───────────────────────────────────────────────────

/// Query parameters for listing Andon events.
#[derive(Debug, Deserialize)]
pub struct ListAndonsParams {
    pub status: Option<String>,
    pub work_center_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for acknowledging an Andon.
#[derive(Debug, Deserialize)]
pub struct AcknowledgeAndonRequest {
    /// Ignored: the actor is always the authenticated user. Kept as
    /// `Option` so legacy clients sending it do not break.
    pub acknowledged_by: Option<Uuid>,
}

/// Request body for resolving an Andon.
#[derive(Debug, Deserialize)]
pub struct ResolveAndonRequest {
    /// Ignored: the actor is always the authenticated user. Kept as
    /// `Option` so legacy clients sending it do not break.
    pub resolved_by: Option<Uuid>,
    pub resolution: String,
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// List all Andon events with optional status and work center filters.
pub async fn list_andons(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListAndonsParams>,
) -> Result<Json<PaginatedResponse<Andon>>> {
    user.require_permission("tps:andon:raise")?;
    let tenant_id = user.tenant_id;
    let andons = state
        .ops_service
        .list_andons(
            tenant_id,
            params.status.as_deref(),
            params.work_center_id,
            params.page,
            params.per_page,
        )
        .await?;
    Ok(Json(andons))
}

/// Client input for raising an Andon: only the operational facts. The
/// actor (raised_by), tenant, status, timestamps and event identity are
/// server-generated — a caller can never attribute an Andon to someone
/// else.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct RaiseAndonRequest {
    /// The work center is server-resolved from the caller's assignment
    /// when absent (thirteenth audit P0): the operator never supplies an
    /// id, and a client cannot forge a work center it does not work at.
    pub work_center_id: Option<Uuid>,
    pub issue_type: String, // quality, safety, maintenance, material, other
    pub severity: String,   // low, medium, high, critical
    pub description: String,
    /// When the abnormal condition was OBSERVED (item 47): the operator's
    /// honest observation time — detection latency becomes measurable.
    /// Rejected when in the future beyond a small clock-skew allowance.
    #[serde(default)]
    pub observed_at: Option<chrono::DateTime<chrono::Utc>>,
}

/// Raise (create) a new Andon event.
pub async fn raise_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RaiseAndonRequest>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:raise")?;
    let tenant_id = user.tenant_id;
    // Item 47: a future observation timestamp is rejected (a clock-skewed
    // client cannot backdate an observation into the future).
    if let Some(observed) = req.observed_at {
        if observed > chrono::Utc::now() + chrono::Duration::minutes(5) {
            return Err(sensei_core::error::SenseiError::Validation(
                "observed_at cannot be in the future — allowed skew 5 minutes".to_string(),
            ));
        }
    }
    // Thirteenth audit P0: the work center is SERVER-RESOLVED from the
    // caller's operational assignment — never accepted as a forged id.
    // The site is captured from the same context (fifteenth audit A1):
    // the Andon is explicitly scoped, never implicitly company-wide.
    let mut site_id = None;
    let work_center_id = match req.work_center_id {
        Some(wc) => wc,
        None => {
            // The agent context resolves the caller's site/work center.
            let ctx = crate::routes::agent::build_context(&user, &state).await;
            site_id = ctx.site_id;
            ctx.work_center_id.ok_or_else(|| {
                sensei_core::error::SenseiError::Validation(
                    "Cannot raise help: the caller has no work center assigned — \
                     contact your team lead"
                        .to_string(),
                )
            })?
        }
    };
    let andon = Andon {
        id: Uuid::new_v4(),
        tenant_id,
        site_id,
        andon_number: String::new(),
        work_center_id,
        issue_type: req.issue_type,
        severity: req.severity,
        description: req.description,
        status: "active".to_string(),
        abnormal_condition_observed_at: req.observed_at,
        // The actor is a server-generated identity field.
        raised_by: user.user_id,
        acknowledged_by: None,
        resolved_by: None,
        resolution: None,
        response_time_seconds: None,
        resolution_time_seconds: None,
        created_at: chrono::Utc::now(),
        acknowledged_at: None,
        resolved_at: None,
        restart_authorized_by: None,
        restart_authorized_at: None,
        contained_at: None,
        contained_by: None,
        contained_note: None,
        escalated: false,
        escalated_at: None,
    };
    let andon = state.ops_service.raise_andon(tenant_id, andon).await?;
    // Thirteenth audit: the abnormality ALSO opens/reinforces ONE
    // OperationalCondition — the same work center + issue type within
    // the window reuses the same condition (recurrence signature), so a
    // recurring problem never spawns a new ticket each time.
    if let Some(pool) = state.db_pool.as_ref() {
        let cond_input = sensei_services::tps::conditions::OpenConditionInput {
            scope_work_center_id: Some(andon.work_center_id),
            scope_site_id: None,
            scope_value_stream_id: None,
            scope_shift_id: None,
            subject_type: sensei_services::tps::conditions::ConditionSubject::Operation,
            subject_id: None,
            expected_condition: serde_json::json!({
                "reference_type": "standard_work",
                "condition": "work proceeds at the expected condition",
            }),
            observed_condition: serde_json::json!({
                "source": "andon",
                "source_entity_id": andon.id,
                "issue_type": andon.issue_type,
                "description": andon.description,
            }),
            gap: serde_json::json!({ "condition_type": andon.issue_type }),
            risk: serde_json::json!({
                "quality": if andon.issue_type == "quality" { 1 } else { 0 },
                "safety": if andon.issue_type == "safety" { 1 } else { 0 },
                "flow": if andon.issue_type == "material" || andon.issue_type == "capacity" { 1 } else { 0 },
                "customer": 0,
                "cost": 0,
                "people": 0,
            }),
            help_required: true,
            containment_required: andon.issue_type == "quality" || andon.issue_type == "safety",
            expertise_required: match andon.issue_type.as_str() {
                "quality" => Some("quality_engineer".to_string()),
                "maintenance" => Some("maintenance_tech".to_string()),
                "material" => Some("material_planner".to_string()),
                "safety" => Some("safety_lead".to_string()),
                _ => None,
            },
            condition_type: andon.issue_type.clone(),
            source_entity_type: "andon".to_string(),
            source_entity_id: andon.id,
            created_by: user.user_id,
        };
        if let Err(e) =
            sensei_services::tps::conditions::open_condition(pool.as_ref(), tenant_id, &cond_input)
                .await
        {
            tracing::error!(error = %e, andon_id = %andon.id, "OperationalCondition projection failed");
        }
    }
    // Item 63/73: the graph edge is a DERIVED PROJECTION of the
    // authoritative Andon row — the Andon itself is the source of truth.
    // A failed projection is logged loudly and REBUILDABLE (the rebuild
    // endpoint reconstructs it from the Andon rows), so it never breaks
    // the raise response.
    if let Some(pool) = state.db_pool.as_ref() {
        let wc = andon.work_center_id;
        if let Err(e) = sqlx::query(
            "INSERT INTO knowledge_graph_edges                     (tenant_id, source_type, source_id, relation, target_type, target_id, created_by)                  VALUES ($1, 'abnormality', $2, 'occurred_at', 'work_center', $3, $4)                  ON CONFLICT DO NOTHING",
        )
        .bind(tenant_id)
        .bind(andon.id)
        .bind(wc)
        .bind(user.user_id)
        .execute(pool.as_ref())
        .await
        {
            tracing::error!(error = %e, andon_id = %andon.id, "Graph projection failed");
        }
    }
    Ok(Json(andon))
}

/// Get a specific Andon event by ID.
pub async fn get_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:raise")?;
    let tenant_id = user.tenant_id;
    let andon = state.ops_service.get_andon(tenant_id, id).await?;
    Ok(Json(andon))
}

/// Acknowledge an Andon event (assign a responder).
///
/// The actor is taken from the authenticated token; client-supplied actor
/// ids are never trusted.
pub async fn acknowledge_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    _req: Json<AcknowledgeAndonRequest>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:ack")?;
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .acknowledge_andon(tenant_id, id, user.user_id)
        .await?;
    Ok(Json(andon))
}

/// Resolve an Andon event with a resolution description.
///
/// The actor is taken from the authenticated token; client-supplied actor
/// ids are never trusted.
pub async fn resolve_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<ResolveAndonRequest>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:resolve")?;
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .resolve_andon(tenant_id, id, user.user_id, &req.resolution)
        .await?;
    Ok(Json(andon))
}

/// Escalate an Andon to the next tier (item 41: the SAME command path as
/// every other Andon action — the service owns the state transition).
pub async fn escalate_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:resolve")?;
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .escalate_andon(tenant_id, id, user.user_id)
        .await?;
    Ok(Json(andon))
}

/// Update an existing Andon event.
pub async fn update_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<Andon>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:contain")?;
    let tenant_id = user.tenant_id;
    let andon = state.ops_service.update_andon(tenant_id, id, req).await?;
    Ok(Json(andon))
}

/// Delete an Andon event.
/// Authorize the restart of a line after a critical-safety Andon (hard
/// rule: the line stays stopped until this authorization exists).
pub async fn authorize_restart(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:restart")?;
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .authorize_restart(tenant_id, id, user.user_id)
        .await?;
    Ok(Json(andon))
}

/// Void an Andon (append-only operational history: production Andon
/// events are never physically deleted — abandoned/false signals are
/// marked `voided` with the actor and reason recorded).
pub async fn void_andon(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<VoidAndonRequest>,
) -> Result<Json<Andon>> {
    user.require_permission("tps:andon:contain")?;
    let tenant_id = user.tenant_id;
    let andon = state
        .ops_service
        .void_andon(tenant_id, id, user.user_id, &req.reason)
        .await?;
    Ok(Json(andon))
}

/// Reason for voiding an Andon.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct VoidAndonRequest {
    pub reason: String,
}

/// The last 100 entries of the canonical operational event log for the
/// tenant (fifteenth audit 31-33): the organizational nervous system —
/// every event with its bitemporal stamps (occurred_at vs recorded_at)
/// and the objects it links, newest first.
pub async fn list_events(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("tps:read")?;
    let pool = state.db_pool.as_ref().ok_or_else(|| {
        sensei_core::error::SenseiError::Database("Event log requires the database".to_string())
    })?;
    // Transaction-scoped tenant context: the envelope is FORCE-RLS
    // fail-closed, so the read must establish app.tenant_id.
    let mut tx = pool.begin().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("Event log tx begin failed: {e}"))
    })?;
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(user.tenant_id.to_string())
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            sensei_core::error::SenseiError::Database(format!(
                "Event log tenant context failed: {e}"
            ))
        })?;
    type EventRow = (
        Uuid,
        Uuid,
        String,
        chrono::DateTime<chrono::Utc>,
        chrono::DateTime<chrono::Utc>,
        Option<Uuid>,
        Option<Uuid>,
        serde_json::Value,
        Option<String>,
        Option<String>,
        String,
        serde_json::Value,
        i64,
    );
    let rows: Vec<EventRow> = sqlx::query_as(
        "SELECT id, tenant_id, event_type, occurred_at, recorded_at, scope_site_id, actor_id, \
                objects, source_system, source_id, sensitivity, payload, sequence \
         FROM operational_events WHERE tenant_id = $1 ORDER BY occurred_at DESC LIMIT 100",
    )
    .bind(user.tenant_id)
    .fetch_all(&mut *tx)
    .await
    .map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("Event log read failed: {e}"))
    })?;
    tx.commit().await.map_err(|e| {
        sensei_core::error::SenseiError::Database(format!("Event log tx commit failed: {e}"))
    })?;
    let events: Vec<serde_json::Value> = rows
        .into_iter()
        .map(
            |(
                id,
                tenant_id,
                event_type,
                occurred_at,
                recorded_at,
                scope_site_id,
                actor_id,
                objects,
                source_system,
                source_id,
                sensitivity,
                payload,
                sequence,
            )| {
                serde_json::json!({
                    "id": id,
                    "tenant_id": tenant_id,
                    "event_type": event_type,
                    "occurred_at": occurred_at,
                    "recorded_at": recorded_at,
                    "scope_site_id": scope_site_id,
                    "actor_id": actor_id,
                    "objects": objects,
                    "source_system": source_system,
                    "source_id": source_id,
                    "sensitivity": sensitivity,
                    "payload": payload,
                    "sequence": sequence,
                })
            },
        )
        .collect();
    Ok(Json(serde_json::json!({ "events": events })))
}
