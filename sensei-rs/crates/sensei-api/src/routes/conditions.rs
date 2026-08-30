//! OperationalCondition API (thirteenth audit): the nervous system
//! surface. One list shows every abnormality regardless of which module
//! produced it — Andon, NCR, sales-flow warning, integration conflict.

use axum::extract::{Path, Query, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_services::tps::conditions::OperationalCondition;
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

#[derive(Debug, Deserialize)]
pub struct ListConditionsParams {
    pub status: Option<String>,
    pub work_center_id: Option<Uuid>,
    pub limit: Option<i64>,
}

pub async fn list_conditions(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListConditionsParams>,
) -> Result<Json<Vec<OperationalCondition>>> {
    user.require_permission("tps:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Conditions require the database".to_string()))?;
    let limit = params.limit.unwrap_or(100).min(500);
    let rows: Vec<OperationalCondition> = match (&params.status, params.work_center_id) {
        (Some(status), Some(wc)) => sqlx::query_as(
            "SELECT id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                    subject_id, expected_condition, observed_condition, gap, risk, status, \
                    help_required, containment_required, expertise_required, owner_id, \
                    response_due_at, learning, \
                    COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                    source_entity_type, source_entity_id, created_at, updated_at \
             FROM operational_conditions \
             WHERE tenant_id = $1 AND status = $2 AND scope_work_center_id = $3 \
             ORDER BY updated_at DESC LIMIT $4",
        )
        .bind(user.tenant_id)
        .bind(status)
        .bind(wc)
        .bind(limit)
        .fetch_all(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Conditions read failed: {e}")))?,
        (Some(status), None) => sqlx::query_as(
            "SELECT id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                    subject_id, expected_condition, observed_condition, gap, risk, status, \
                    help_required, containment_required, expertise_required, owner_id, \
                    response_due_at, learning, \
                    COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                    source_entity_type, source_entity_id, created_at, updated_at \
             FROM operational_conditions \
             WHERE tenant_id = $1 AND status = $2 \
             ORDER BY updated_at DESC LIMIT $3",
        )
        .bind(user.tenant_id)
        .bind(status)
        .bind(limit)
        .fetch_all(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Conditions read failed: {e}")))?,
        (None, Some(wc)) => sqlx::query_as(
            "SELECT id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                    subject_id, expected_condition, observed_condition, gap, risk, status, \
                    help_required, containment_required, expertise_required, owner_id, \
                    response_due_at, learning, \
                    COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                    source_entity_type, source_entity_id, created_at, updated_at \
             FROM operational_conditions \
             WHERE tenant_id = $1 AND scope_work_center_id = $2 \
             ORDER BY updated_at DESC LIMIT $3",
        )
        .bind(user.tenant_id)
        .bind(wc)
        .bind(limit)
        .fetch_all(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Conditions read failed: {e}")))?,
        (None, None) => sqlx::query_as(
            "SELECT id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                    subject_id, expected_condition, observed_condition, gap, risk, status, \
                    help_required, containment_required, expertise_required, owner_id, \
                    response_due_at, learning, \
                    COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                    source_entity_type, source_entity_id, created_at, updated_at \
             FROM operational_conditions \
             WHERE tenant_id = $1 \
             ORDER BY updated_at DESC LIMIT $2",
        )
        .bind(user.tenant_id)
        .bind(limit)
        .fetch_all(pool.as_ref())
        .await
        .map_err(|e| SenseiError::Database(format!("Conditions read failed: {e}")))?,
    };
    Ok(Json(rows))
}

pub async fn get_condition(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<OperationalCondition>> {
    user.require_permission("tps:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Conditions require the database".to_string()))?;
    let row: Option<OperationalCondition> = sqlx::query_as(
        "SELECT id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                subject_id, expected_condition, observed_condition, gap, risk, status, \
                help_required, containment_required, expertise_required, owner_id, \
                response_due_at, learning, \
                COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                source_entity_type, source_entity_id, created_at, updated_at \
         FROM operational_conditions WHERE id = $1 AND tenant_id = $2",
    )
    .bind(id)
    .bind(user.tenant_id)
    .fetch_optional(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Condition read failed: {e}")))?;
    row.ok_or_else(|| SenseiError::NotFound(id.to_string()))
        .map(Json)
}

pub async fn contain_condition(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<OperationalCondition>> {
    user.require_permission("tps:andon:resolve")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Conditions require the database".to_string()))?;
    let cond = sensei_services::tps::conditions::contain_condition(
        pool.as_ref(),
        user.tenant_id,
        id,
        user.user_id,
    )
    .await?;
    Ok(Json(cond))
}
