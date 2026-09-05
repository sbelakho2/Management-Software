//! Employee active assignment (item 17): the distributed plant scope —
//! site, value stream, work center and shift — that the agent context and
//! the production truth resolve at request time. One active assignment
//! row per employee; the endpoint is admin-scoped.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

/// Set (or replace) an employee's active assignment.
#[derive(Debug, Deserialize)]
pub struct SetAssignmentRequest {
    pub site_id: Option<Uuid>,
    pub value_stream_id: Option<Uuid>,
    pub work_center_id: Option<Uuid>,
    pub shift_id: Option<Uuid>,
}

#[derive(Debug, Serialize)]
pub struct AssignmentResponse {
    pub user_id: Uuid,
    pub site_id: Option<Uuid>,
    pub value_stream_id: Option<Uuid>,
    pub work_center_id: Option<Uuid>,
    pub shift_id: Option<Uuid>,
    pub is_active: bool,
}

fn require_admin(user: &AuthenticatedUser) -> Result<()> {
    if user
        .roles
        .iter()
        .any(|r| r == "admin" || r == "platform_superadmin")
    {
        Ok(())
    } else {
        Err(SenseiError::Forbidden(
            "Admin role required for employee assignment management".to_string(),
        ))
    }
}

/// Set/replace the employee's active assignment (admin).
pub async fn set_employee_assignment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(user_id): Path<Uuid>,
    Json(req): Json<SetAssignmentRequest>,
) -> Result<Json<AssignmentResponse>> {
    require_admin(&user)?;
    let pool = state.db_pool.as_ref().ok_or_else(|| {
        SenseiError::Database("Assignment management requires the database pool".to_string())
    })?;

    // The target user must exist in this tenant. The users table is
    // fail-closed FORCE RLS (migration 175 universal policy), so the
    // check runs inside a TenantTx of the caller's tenant.
    let exists: bool = {
        let mut db = sensei_core::db::TenantTx::begin(pool, user.tenant_id)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Assignment lookup tx failed: {e}"))
            })?;
        let found: bool = sqlx::query_scalar(
            "SELECT EXISTS(SELECT 1 FROM users WHERE id = $1 AND tenant_id = $2)",
        )
        .bind(user_id)
        .bind(user.tenant_id)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("Assignment lookup failed: {e}")))?;
        drop(db);
        found
    };
    if !exists {
        return Err(SenseiError::NotFound(format!("User {user_id} not found")));
    }

    // Deactivate any existing active assignment, then insert the new one —
    // one active assignment per employee, atomically.
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Assignment tx failed: {e}")))?;
    sqlx::query(
        "UPDATE employee_assignments SET is_active = FALSE, updated_at = NOW() \
         WHERE tenant_id = $1 AND user_id = $2 AND is_active = TRUE",
    )
    .bind(user.tenant_id)
    .bind(user_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Assignment deactivate failed: {e}")))?;
    sqlx::query(
        "INSERT INTO employee_assignments \
            (tenant_id, user_id, site_id, value_stream_id, work_center_id, shift_id, is_active) \
         VALUES ($1, $2, $3, $4, $5, $6, TRUE)",
    )
    .bind(user.tenant_id)
    .bind(user_id)
    .bind(req.site_id)
    .bind(req.value_stream_id)
    .bind(req.work_center_id)
    .bind(req.shift_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Assignment insert failed: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Assignment commit failed: {e}")))?;

    Ok(Json(AssignmentResponse {
        user_id,
        site_id: req.site_id,
        value_stream_id: req.value_stream_id,
        work_center_id: req.work_center_id,
        shift_id: req.shift_id,
        is_active: true,
    }))
}

/// A row of the employee's active topology scope.
type AssignmentRow = (Option<Uuid>, Option<Uuid>, Option<Uuid>, Option<Uuid>);

/// Fetch the employee's active assignment (admin).
pub async fn get_employee_assignment(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(user_id): Path<Uuid>,
) -> Result<Json<Option<AssignmentResponse>>> {
    require_admin(&user)?;
    let pool = state.db_pool.as_ref().ok_or_else(|| {
        SenseiError::Database("Assignment management requires the database pool".to_string())
    })?;
    let row: Option<AssignmentRow> = sqlx::query_as(
        "SELECT site_id, value_stream_id, work_center_id, shift_id \
             FROM employee_assignments \
             WHERE tenant_id = $1 AND user_id = $2 AND is_active = TRUE \
             ORDER BY updated_at DESC LIMIT 1",
    )
    .bind(user.tenant_id)
    .bind(user_id)
    .fetch_optional(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Assignment lookup failed: {e}")))?;
    Ok(Json(row.map(|(site, vs, wc, sh)| AssignmentResponse {
        user_id,
        site_id: site,
        value_stream_id: vs,
        work_center_id: wc,
        shift_id: sh,
        is_active: true,
    })))
}
