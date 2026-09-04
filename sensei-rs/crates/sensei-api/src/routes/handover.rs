#![allow(clippy::type_complexity)]
//! Role-slot / principal-separation routes (fifteenth audit items 40-44).
//!
//! Identity is NOT role ownership. A role slot (`electronics_buyer_tangier`)
//! owns the work; principals are merely assigned to slots. When a person
//! leaves, the deterministic departure operation:
//!   1. ends every active assignment of that principal,
//!   2. collects their open work (andons, tasks, operational conditions),
//!   3. transfers it to the caller-provided successor principal or to the
//!      slot with the highest assignment recency,
//!   4. returns a handover view (open work, at-risk deadlines, recent
//!      abnormalities, pending approvals, active conditions, retained role
//!      memory) so the next assignee inherits the slot's history.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

// ── Permission ──────────────────────────────────────────────────────────────
//
// `hr:manage` is granted to the `hr_manager` role (see
// crates/sensei-auth/src/rbac.rs). Slot administration and departures are
// HR-grade operations.

// ── Request / response DTOs ─────────────────────────────────────────────────

/// The slot's operational scope (twenty-ninth-audit Wave A item 5) —
/// explicit and typed, never inferred from which id column is set:
///
/// - `none`: the slot carries no operational scope.
/// - `tenant`: the slot is TENANT-WIDE — creating it additionally
///   requires `hr:role-slot:tenant-wide` (a deliberate grant, never an
///   accident of a NULL scope).
/// - `site`: the slot is scoped to one site.
/// - `work_center`: the slot is scoped to one work center; the owning
///   site is resolved from `work_centers.site_id` (NotFound when the
///   work center does not exist in the tenant) and stored denormalized
///   alongside it.
#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum SlotScopeRequest {
    None,
    Tenant,
    Site { site_id: Uuid },
    WorkCenter { work_center_id: Uuid },
}

/// Body for creating a role slot.
#[derive(Debug, Deserialize)]
pub struct CreateSlotRequest {
    pub role_name: String,
    pub slot_name: String,
    pub scope: SlotScopeRequest,
    pub description: Option<String>,
}

/// Body for assigning a principal to a slot.
#[derive(Debug, Deserialize)]
pub struct AssignRequest {
    pub principal_id: Uuid,
}

/// Body for the deterministic employee-departure operation.
#[derive(Debug, Deserialize)]
pub struct DepartureRequest {
    /// The departing principal (every active assignment is ended).
    pub principal_id: Uuid,
    /// Reason for the departure — retained in the handover view.
    pub reason: String,
    /// Optional successor: open work is re-pointed to this principal.
    /// When absent, open work transfers to the slot with the highest
    /// assignment recency and is inherited by its next assignee.
    pub target_principal_id: Option<Uuid>,
}

/// A role slot as returned by the list/create endpoints.
#[derive(Debug, Serialize)]
pub struct RoleSlot {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub role_name: String,
    pub slot_name: String,
    pub scope_kind: String,
    pub scope_site_id: Option<Uuid>,
    pub scope_work_center_id: Option<Uuid>,
    pub description: Option<String>,
    pub current_principal_id: Option<Uuid>,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// A principal assignment row as returned by assign/unassign.
#[derive(Debug, Serialize)]
pub struct Assignment {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub principal_id: Uuid,
    pub slot_id: Uuid,
    pub assigned_at: chrono::DateTime<chrono::Utc>,
    pub ended_at: Option<chrono::DateTime<chrono::Utc>>,
}

// ── Helpers ─────────────────────────────────────────────────────────────────

/// Set the transaction-scoped tenant context that the role_slots RLS policy
/// enforces (same pattern as the service crates).
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

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Role slots require the database".to_string()))
        .map(|p| p.as_ref())
}

/// The slot with the highest assignment recency for a principal (NULL when
/// the principal never held a slot). All assignments are ended by the time
/// departure calls this, so it reads the historical assignments.
async fn most_recent_slot_id(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    principal_id: Uuid,
) -> Result<Option<(Uuid, String, String)>> {
    let row: Option<(Uuid, String, String)> = sqlx::query_as(
        "SELECT rs.id, rs.role_name, rs.slot_name \
         FROM principal_assignments pa \
         JOIN role_slots rs ON rs.id = pa.slot_id \
         WHERE pa.tenant_id = $1 AND pa.principal_id = $2 \
         ORDER BY pa.assigned_at DESC LIMIT 1",
    )
    .bind(tenant_id)
    .bind(principal_id)
    .fetch_optional(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Most-recent slot lookup failed: {e}")))?;
    Ok(row)
}

// ── Handlers ────────────────────────────────────────────────────────────────

/// `POST /api/v1/roles/slots` — create a role slot. The slot (not the
/// person) owns the work; principals are assigned to it later. Scope is
/// EXPLICIT (twenty-ninth-audit Wave A item 5): a tenant-wide slot is a
/// deliberate grant requiring `hr:role-slot:tenant-wide` on top of the
/// slot-management permission; a work-center slot resolves (and stores)
/// the owning site from `work_centers.site_id`.
pub async fn create_slot(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<CreateSlotRequest>,
) -> Result<Json<RoleSlot>> {
    user.require_permission("hr:manage")?;
    if matches!(req.scope, SlotScopeRequest::Tenant) {
        user.require_permission("hr:role-slot:tenant-wide")?;
    }
    let tenant_id = user.tenant_id;
    let p = pool(&state)?;
    let mut tx = p
        .begin()
        .await
        .map_err(|e| SenseiError::Database(e.to_string()))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let (scope_kind, scope_site_id, scope_work_center_id): (&str, Option<Uuid>, Option<Uuid>) =
        match req.scope {
            SlotScopeRequest::None => ("none", None, None),
            SlotScopeRequest::Tenant => ("tenant", None, None),
            SlotScopeRequest::Site { site_id } => ("site", Some(site_id), None),
            SlotScopeRequest::WorkCenter { work_center_id } => {
                // DB-resolved scope: the owning site comes from the work
                // center's row — the caller can never name a site themselves
                // (migration 169 shape CHECK stores kind + BOTH ids).
                let site_id: Option<Uuid> = sqlx::query_scalar(
                    "SELECT site_id FROM work_centers WHERE id = $1 AND tenant_id = $2",
                )
                .bind(work_center_id)
                .bind(tenant_id)
                .fetch_optional(&mut *tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Work-center site resolve failed: {e}"))
                })?;
                let Some(site_id) = site_id else {
                    return Err(SenseiError::NotFound(format!(
                        "work center {work_center_id}"
                    )));
                };
                ("work_center", Some(site_id), Some(work_center_id))
            }
        };
    let slot: (
        Uuid,
        Uuid,
        String,
        String,
        String,
        Option<Uuid>,
        Option<Uuid>,
        Option<String>,
        chrono::DateTime<chrono::Utc>,
    ) = sqlx::query_as(
        "INSERT INTO role_slots \
             (tenant_id, role_name, slot_name, scope_kind, scope_site_id, \
              scope_work_center_id, description) \
             VALUES ($1, $2, $3, $4, $5, $6, $7) \
             RETURNING id, tenant_id, role_name, slot_name, scope_kind, \
                       scope_site_id, scope_work_center_id, description, created_at",
    )
    .bind(tenant_id)
    .bind(&req.role_name)
    .bind(&req.slot_name)
    .bind(scope_kind)
    .bind(scope_site_id)
    .bind(scope_work_center_id)
    .bind(req.description)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| {
        if let sqlx::Error::Database(db) = &e {
            if db.code().as_deref() == Some("23505") {
                return SenseiError::AlreadyExists(format!(
                    "slot '{}' already exists in this tenant",
                    req.slot_name
                ));
            }
        }
        SenseiError::Database(format!("Slot create failed: {e}"))
    })?;
    // Seventeenth audit item 5: a role slot is a policy/relationship
    // object — its creation bumps the revision in the SAME transaction.
    sensei_services::tps::authorization_revisions::bump_in_tx(
        &mut tx,
        tenant_id,
        "relationship_revision",
    )
    .await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Slot create commit failed: {e}")))?;
    Ok(Json(RoleSlot {
        id: slot.0,
        tenant_id: slot.1,
        role_name: slot.2,
        slot_name: slot.3,
        scope_kind: slot.4,
        scope_site_id: slot.5,
        scope_work_center_id: slot.6,
        description: slot.7,
        current_principal_id: None,
        created_at: slot.8,
    }))
}

/// `POST /api/v1/roles/slots/{slot_id}/assign` — assign a principal to the
/// slot. Any currently active assignment of the slot is ended first, so the
/// slot has at most one active principal at a time while the full history
/// of assignments is retained.
pub async fn assign_principal(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(slot_id): Path<Uuid>,
    Json(req): Json<AssignRequest>,
) -> Result<Json<Assignment>> {
    user.require_permission("hr:manage")?;
    let tenant_id = user.tenant_id;
    let p = pool(&state)?;
    let mut tx = p
        .begin()
        .await
        .map_err(|e| SenseiError::Database(e.to_string()))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let exists: bool = sqlx::query_scalar(
        "SELECT EXISTS (SELECT 1 FROM role_slots WHERE id = $1 AND tenant_id = $2)",
    )
    .bind(slot_id)
    .bind(tenant_id)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Slot lookup failed: {e}")))?;
    if !exists {
        return Err(SenseiError::NotFound(format!("slot {slot_id}")));
    }
    let principal_ok: bool =
        sqlx::query_scalar("SELECT EXISTS (SELECT 1 FROM users WHERE id = $1 AND tenant_id = $2)")
            .bind(req.principal_id)
            .bind(tenant_id)
            .fetch_one(&mut *tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Principal lookup failed: {e}")))?;
    if !principal_ok {
        return Err(SenseiError::NotFound(format!(
            "principal {}",
            req.principal_id
        )));
    }
    // End any active assignment of the slot (single active principal per slot).
    sqlx::query(
        "UPDATE principal_assignments SET ended_at = NOW() \
         WHERE tenant_id = $1 AND slot_id = $2 AND ended_at IS NULL",
    )
    .bind(tenant_id)
    .bind(slot_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Slot re-assign failed: {e}")))?;
    let row: (
        Uuid,
        Uuid,
        Uuid,
        Uuid,
        chrono::DateTime<chrono::Utc>,
        Option<chrono::DateTime<chrono::Utc>>,
    ) = sqlx::query_as(
        "INSERT INTO principal_assignments (tenant_id, principal_id, slot_id) \
             VALUES ($1, $2, $3) \
             RETURNING id, tenant_id, principal_id, slot_id, assigned_at, ended_at",
    )
    .bind(tenant_id)
    .bind(req.principal_id)
    .bind(slot_id)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Assignment failed: {e}")))?;
    // Seventeenth audit item 5: the authorization revision bump is IN the
    // mutation transaction — the assignment and its revision are
    // inseparable.
    sensei_services::tps::authorization_revisions::bump_in_tx(
        &mut tx,
        tenant_id,
        "relationship_revision",
    )
    .await?;
    sensei_services::tps::authorization_revisions::bump_in_tx(
        &mut tx,
        tenant_id,
        "principal_revision",
    )
    .await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Assign commit failed: {e}")))?;
    Ok(Json(Assignment {
        id: row.0,
        tenant_id: row.1,
        principal_id: row.2,
        slot_id: row.3,
        assigned_at: row.4,
        ended_at: row.5,
    }))
}

/// `POST /api/v1/roles/slots/{slot_id}/unassign` — end the slot's current
/// active assignment. The slot and its history survive; only the
/// assignment ends.
pub async fn unassign_principal(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(slot_id): Path<Uuid>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("hr:manage")?;
    let tenant_id = user.tenant_id;
    let p = pool(&state)?;
    let mut tx = p
        .begin()
        .await
        .map_err(|e| SenseiError::Database(e.to_string()))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let ended = sqlx::query(
        "UPDATE principal_assignments SET ended_at = NOW() \
         WHERE tenant_id = $1 AND slot_id = $2 AND ended_at IS NULL",
    )
    .bind(tenant_id)
    .bind(slot_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Unassign failed: {e}")))?;
    if ended.rows_affected() > 0 {
        sensei_services::tps::authorization_revisions::bump_in_tx(
            &mut tx,
            tenant_id,
            "relationship_revision",
        )
        .await?;
        sensei_services::tps::authorization_revisions::bump_in_tx(
            &mut tx,
            tenant_id,
            "principal_revision",
        )
        .await?;
    }
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Unassign commit failed: {e}")))?;
    Ok(Json(serde_json::json!({
        "slot_id": slot_id,
        "ended_assignments": ended.rows_affected(),
    })))
}

/// `POST /api/v1/roles/departures` — the deterministic departure operation.
///
/// Runs inside ONE transaction:
///   a) end ALL active assignments of the principal (`ended_at = NOW()`);
///   b) collect the principal's open work: active andons they raised, open
///      tasks assigned to them, open operational conditions they own;
///   c) transfer that open work to the caller-provided successor principal,
///      or — when absent — to the slot with the highest assignment recency
///      (the next assignee inherits it);
///   d) return the handover view: open work, at-risk deadlines, recent
///      abnormalities, pending approvals, active conditions, and the
///      retained role memory (the slots the principal held persist; only
///      the assignment ends).
///
/// Identity is never erased: `raised_by` / assignee attribution stays in
/// the historical columns; the slot owns the work going forward.
pub async fn record_departure(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<DepartureRequest>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("hr:manage")?;
    let tenant_id = user.tenant_id;
    let p = pool(&state)?;
    let view = run_departure(p, tenant_id, req).await?;
    Ok(Json(view))
}

/// The deterministic departure operation (see [`record_departure`]).
///
/// Public so integration tests can drive the exact production logic
/// without the HTTP layer.
pub async fn run_departure(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    req: DepartureRequest,
) -> Result<serde_json::Value> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(e.to_string()))?;
    set_tenant_context(&mut tx, tenant_id).await?;

    // (a) End every active assignment of the departing principal.
    let ended = sqlx::query(
        "UPDATE principal_assignments SET ended_at = NOW() \
         WHERE tenant_id = $1 AND principal_id = $2 AND ended_at IS NULL",
    )
    .bind(tenant_id)
    .bind(req.principal_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Departure: end assignments failed: {e}")))?;

    // (b) Collect the principal's open work BEFORE the transfer so the
    //     handover view reflects everything they carried.
    let andons: Vec<(Uuid, String, String, String)> = sqlx::query_as(
        "SELECT id, andon_number, issue_type, status FROM andons \
         WHERE tenant_id = $1 AND raised_by = $2 AND status IN ('active', 'acknowledged') \
         ORDER BY created_at",
    )
    .bind(tenant_id)
    .bind(req.principal_id)
    .fetch_all(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Departure: andon collect failed: {e}")))?;
    let tasks: Vec<(
        Uuid,
        String,
        String,
        String,
        String,
        Option<chrono::DateTime<chrono::Utc>>,
    )> = sqlx::query_as(
        "SELECT id, task_number, title, status, task_type, due_date FROM tasks \
             WHERE tenant_id = $1 AND assignee_id = $2 \
             AND status NOT IN ('completed', 'cancelled') ORDER BY created_at",
    )
    .bind(tenant_id)
    .bind(req.principal_id)
    .fetch_all(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Departure: task collect failed: {e}")))?;
    let conditions: Vec<(Uuid, String, String, Option<chrono::DateTime<chrono::Utc>>)> =
        sqlx::query_as(
            "SELECT id, condition_number, status, response_due_at FROM operational_conditions \
             WHERE tenant_id = $1 AND owner_id = $2 \
             AND status NOT IN ('resolved', 'closed') ORDER BY created_at",
        )
        .bind(tenant_id)
        .bind(req.principal_id)
        .fetch_all(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Departure: condition collect failed: {e}")))?;

    // Transfer target: the successor principal when provided, otherwise the
    // slot with the highest assignment recency.
    let (slot_id, slot_role_name, slot_name) =
        most_recent_slot_id(&mut tx, tenant_id, req.principal_id)
            .await?
            .unwrap_or((Uuid::nil(), String::new(), String::new()));

    // (c) Transfer the open work.
    let mut transferred_tasks: u64 = 0;
    let mut transferred_conditions: u64 = 0;
    if let Some(target) = req.target_principal_id {
        // Successor principal: open tasks and conditions are re-pointed.
        let r = sqlx::query(
            "UPDATE tasks SET assignee_id = $1, updated_at = NOW() \
             WHERE tenant_id = $2 AND assignee_id = $3 \
             AND status NOT IN ('completed', 'cancelled')",
        )
        .bind(target)
        .bind(tenant_id)
        .bind(req.principal_id)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Departure: task transfer failed: {e}")))?;
        transferred_tasks = r.rows_affected();
        let r = sqlx::query(
            "UPDATE operational_conditions SET owner_id = $1 \
             WHERE tenant_id = $2 AND owner_id = $3 \
             AND status NOT IN ('resolved', 'closed')",
        )
        .bind(target)
        .bind(tenant_id)
        .bind(req.principal_id)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Departure: condition transfer failed: {e}")))?;
        transferred_conditions = r.rows_affected();
    }
    // Andons carry NO person-ownership column: they belong to the work
    // center/line, and `raised_by` is identity (item 40 — never rewritten).
    // The successor inherits them through the handover view.

    // (d) Handover view pieces — computed from the PRE-transfer collection
    //     (at-risk deadlines / pending approvals must reflect the work the
    //     principal carried, not the successor's post-transfer state).
    let at_risk_deadline = chrono::Utc::now() + chrono::Duration::days(7);
    let at_risk: Vec<&(
        Uuid,
        String,
        String,
        String,
        String,
        Option<chrono::DateTime<chrono::Utc>>,
    )> = tasks
        .iter()
        .filter(|(_, _, _, _, _, due)| due.map(|d| d <= at_risk_deadline).unwrap_or(false))
        .collect();
    let pending_approvals: Vec<&(
        Uuid,
        String,
        String,
        String,
        String,
        Option<chrono::DateTime<chrono::Utc>>,
    )> = tasks
        .iter()
        .filter(|(_, _, _, _, task_type, _)| task_type == "approval")
        .collect();
    let recent_abnormalities: Vec<(Uuid, String, String, String, String)> = sqlx::query_as(
        "SELECT id, andon_number, issue_type, severity, status FROM andons \
         WHERE tenant_id = $1 AND raised_by = $2 \
         AND created_at > NOW() - INTERVAL '30 days' \
         ORDER BY created_at DESC LIMIT 20",
    )
    .bind(tenant_id)
    .bind(req.principal_id)
    .fetch_all(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Departure: abnormalities failed: {e}")))?;
    // The role memory retained: every slot the principal ever held.
    let slots_held: Vec<(
        Uuid,
        String,
        String,
        Option<Uuid>,
        chrono::DateTime<chrono::Utc>,
        Option<chrono::DateTime<chrono::Utc>>,
    )> = sqlx::query_as(
        "SELECT rs.id, rs.role_name, rs.slot_name, rs.scope_site_id, pa.assigned_at, pa.ended_at \
             FROM role_slots rs \
             JOIN principal_assignments pa ON pa.slot_id = rs.id \
             WHERE rs.tenant_id = $1 AND pa.principal_id = $2 \
             ORDER BY pa.assigned_at",
    )
    .bind(tenant_id)
    .bind(req.principal_id)
    .fetch_all(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Departure: slots held failed: {e}")))?;

    // Sixteenth audit item 3: the departure is a COMPLETE security
    // revocation, atomic with the organizational changes — disable the
    // user, invalidate every credential/session/token, clear roles,
    // bump the principal revision, all in the SAME transaction.
    let user_rows = sqlx::query(
        "UPDATE users SET is_active = FALSE, credential_version = credential_version + 1, \
                updated_at = NOW() \
         WHERE id = $1 AND tenant_id = $2",
    )
    .bind(req.principal_id)
    .bind(tenant_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Departure: disable user failed: {e}")))?;
    if user_rows.rows_affected() == 0 {
        return Err(SenseiError::NotFound(format!(
            "Principal {} not found",
            req.principal_id
        )));
    }
    // Clear security roles (the users table holds roles as an array).
    sqlx::query("UPDATE users SET roles = '{}'::text[] WHERE id = $1 AND tenant_id = $2")
        .bind(req.principal_id)
        .bind(tenant_id)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Departure: clear roles failed: {e}")))?;
    // Revoke every refresh token (token revocation, not deletion-based
    // only: the rows are removed so no stale token survives).
    sqlx::query("DELETE FROM refresh_tokens WHERE user_id = $1")
        .bind(req.principal_id)
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            SenseiError::Database(format!("Departure: refresh token revoke failed: {e}"))
        })?;
    // Revoke active sessions.
    sqlx::query("UPDATE sessions SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL")
        .bind(req.principal_id)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Departure: session revoke failed: {e}")))?;
    // Bump the principal authorization revision INSIDE the transaction —
    // a revoked principal invalidates every authorization-derived cache.
    sqlx::query(
        "INSERT INTO authorization_revisions (tenant_id, policy_revision, relationship_revision, principal_revision) \
         VALUES ($1, 1, 1, 1) \
         ON CONFLICT (tenant_id) DO UPDATE SET principal_revision = authorization_revisions.principal_revision + 1, \
             updated_at = NOW()",
    )
    .bind(tenant_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Departure: principal revision failed: {e}")))?;
    // The departure is itself a durable event via the transactional outbox.
    sensei_db::outbox::enqueue_outbox(
        &mut tx,
        tenant_id,
        "hr",
        req.principal_id,
        "hr.principal_departed",
        serde_json::json!({
            "principal": req.principal_id,
            "effective_at": chrono::Utc::now(),
            "successor": req.target_principal_id,
        }),
    )
    .await
    .map_err(|e| SenseiError::Database(format!("Departure: outbox failed: {e}")))?;

    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Departure commit failed: {e}")))?;

    // Fifteenth audit 24/A5: a departure is a revocation — bump the
    // principal revision AFTER the departure transaction completes so the
    // new permission state is committed before caches are invalidated.
    // Every authorization-derived cache key embeds the snapshot salt, so
    // this invalidates them atomically (retrieval can never run under one
    // permission state and execution under another).
    // (the principal revision was bumped INSIDE the departure tx above —
    // security-changing state commits together, or not at all)
    let transferred_to_slot = (!slot_id.is_nil()).then(|| {
        serde_json::json!({ "slot_id": slot_id, "role_name": slot_role_name, "slot_name": slot_name })
    });
    let open_work: Vec<serde_json::Value> = andons
        .iter()
        .map(|(id, number, issue_type, status)| {
            serde_json::json!({
                "entity_type": "andon",
                "entity_id": id,
                "number": number,
                "summary": format!("{issue_type} abnormality"),
                "status": status,
                "transferred_to_slot": transferred_to_slot,
                "transferred_to_principal": req.target_principal_id,
            })
        })
        .chain(
            tasks
                .iter()
                .map(|(id, number, title, status, _task_type, _due)| {
                    serde_json::json!({
                        "entity_type": "task",
                        "entity_id": id,
                        "number": number,
                        "summary": title,
                        "status": status,
                        "transferred_to_slot": transferred_to_slot,
                        "transferred_to_principal": req.target_principal_id,
                    })
                }),
        )
        .chain(conditions.iter().map(|(id, number, status, _due)| {
            serde_json::json!({
                "entity_type": "condition",
                "entity_id": id,
                "number": number,
                "summary": format!("open condition {number}"),
                "status": status,
                "transferred_to_slot": transferred_to_slot,
                "transferred_to_principal": req.target_principal_id,
            })
        }))
        .collect();

    let view = serde_json::json!({
        "departed_principal_id": req.principal_id,
        "reason": req.reason,
        "ended_assignments": ended.rows_affected(),
        "transferred_tasks": transferred_tasks,
        "transferred_conditions": transferred_conditions,
        "transferred_to_slot": transferred_to_slot,
        "transferred_to_principal": req.target_principal_id,
        "memory_retained": true,
        "slots_held": slots_held.iter().map(|(id, role_name, slot_name, scope, assigned, ended_at)| {
            serde_json::json!({
                "slot_id": id,
                "role_name": role_name,
                "slot_name": slot_name,
                "scope_site_id": scope,
                "assigned_at": assigned,
                "ended_at": ended_at,
            })
        }).collect::<Vec<_>>(),
        "open_work": open_work,
        "at_risk_deadlines": at_risk.iter().map(|(id, number, title, status, _task_type, due)| {
            serde_json::json!({
                "task_id": id,
                "task_number": number,
                "title": title,
                "status": status,
                "due_date": due,
            })
        }).collect::<Vec<_>>(),
        "recent_abnormalities": recent_abnormalities.iter().map(|(id, number, issue_type, severity, status)| {
            serde_json::json!({
                "andon_id": id,
                "andon_number": number,
                "issue_type": issue_type,
                "severity": severity,
                "status": status,
            })
        }).collect::<Vec<_>>(),
        "pending_approvals": pending_approvals.iter().map(|(id, number, title, _status, _task_type, _due)| {
            serde_json::json!({ "task_id": id, "task_number": number, "title": title })
        }).collect::<Vec<_>>(),
        "active_conditions": conditions.iter().map(|(id, number, status, due)| {
            serde_json::json!({
                "condition_id": id,
                "condition_number": number,
                "status": status,
                "response_due_at": due,
            })
        }).collect::<Vec<_>>(),
    });

    Ok(view)
}

/// `GET /api/v1/roles/slots` — list the tenant's slots with their current
/// (active) principal.
pub async fn list_slots(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<RoleSlot>>> {
    user.require_permission("hr:manage")?;
    let tenant_id = user.tenant_id;
    let p = pool(&state)?;
    let mut tx = p
        .begin()
        .await
        .map_err(|e| SenseiError::Database(e.to_string()))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let rows: Vec<(
        Uuid,
        Uuid,
        String,
        String,
        String,
        Option<Uuid>,
        Option<Uuid>,
        Option<String>,
        chrono::DateTime<chrono::Utc>,
        Option<Uuid>,
    )> = sqlx::query_as(
        "SELECT rs.id, rs.tenant_id, rs.role_name, rs.slot_name, rs.scope_kind, \
                    rs.scope_site_id, rs.scope_work_center_id, rs.description, \
                    rs.created_at, pa.principal_id \
             FROM role_slots rs \
             LEFT JOIN LATERAL ( \
                 SELECT principal_id FROM principal_assignments \
                 WHERE slot_id = rs.id AND tenant_id = rs.tenant_id AND ended_at IS NULL \
                 ORDER BY assigned_at DESC LIMIT 1 \
             ) pa ON TRUE \
             WHERE rs.tenant_id = $1 \
             ORDER BY rs.slot_name",
    )
    .bind(tenant_id)
    .fetch_all(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Slot list failed: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Slot list commit failed: {e}")))?;
    Ok(Json(
        rows.into_iter()
            .map(
                |(
                    id,
                    tenant,
                    role_name,
                    slot_name,
                    scope_kind,
                    scope,
                    scope_wc,
                    desc,
                    created,
                    principal,
                )| RoleSlot {
                    id,
                    tenant_id: tenant,
                    role_name,
                    slot_name,
                    scope_kind,
                    scope_site_id: scope,
                    scope_work_center_id: scope_wc,
                    description: desc,
                    current_principal_id: principal,
                    created_at: created,
                },
            )
            .collect(),
    ))
}
