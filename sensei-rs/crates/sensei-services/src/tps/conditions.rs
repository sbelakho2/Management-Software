//! OperationalCondition — the nervous system (thirteenth audit): one
//! common primitive underneath every abnormality surface. The user never
//! navigates modules; a condition acquires perspectives and a recurrence
//! signature keeps the SAME underlying condition from spawning a new
//! ticket every time it resurfaces.

use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// What the condition is about.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ConditionSubject {
    Customer,
    Order,
    Product,
    WorkOrder,
    Operation,
    Equipment,
    Supplier,
    Material,
    Process,
    Integration,
}

/// The recurrence signature: (work center, subject kind, subject id,
/// condition type) — the same underlying condition reuses ONE record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecurrenceSignature {
    pub work_center_id: Option<Uuid>,
    pub subject_type: String,
    pub subject_id: Option<Uuid>,
    pub condition_type: String,
}

/// A new condition to open or reinforce.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpenConditionInput {
    pub scope_work_center_id: Option<Uuid>,
    pub scope_site_id: Option<Uuid>,
    pub scope_value_stream_id: Option<Uuid>,
    pub scope_shift_id: Option<Uuid>,
    pub subject_type: ConditionSubject,
    pub subject_id: Option<Uuid>,
    pub expected_condition: serde_json::Value,
    pub observed_condition: serde_json::Value,
    pub gap: serde_json::Value,
    pub risk: serde_json::Value,
    pub help_required: bool,
    pub containment_required: bool,
    pub expertise_required: Option<String>,
    pub condition_type: String,
    pub source_entity_type: String,
    pub source_entity_id: Uuid,
    pub created_by: Uuid,
}

/// A resolved operational condition (the read model).
#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct OperationalCondition {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub condition_number: String,
    pub scope_work_center_id: Option<Uuid>,
    pub subject_type: String,
    pub subject_id: Option<Uuid>,
    pub expected_condition: serde_json::Value,
    pub observed_condition: serde_json::Value,
    pub gap: serde_json::Value,
    pub risk: serde_json::Value,
    pub status: String,
    pub help_required: bool,
    pub containment_required: bool,
    pub expertise_required: Option<String>,
    pub owner_id: Option<Uuid>,
    pub response_due_at: Option<chrono::DateTime<chrono::Utc>>,
    pub learning: serde_json::Value,
    pub recurrence_count: i64,
    pub source_entity_type: Option<String>,
    pub source_entity_id: Option<Uuid>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

/// Open or reinforce a condition: the recurrence signature decides — an
/// open condition with the same signature gets its observed condition
/// refreshed and the recurrence counter incremented; otherwise a new
/// condition is opened. One underlying problem = one record.
pub async fn open_condition(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    input: &OpenConditionInput,
) -> Result<OperationalCondition> {
    let signature = serde_json::json!({
        "recurrence_signature": format!(
            "{}:{}:{}:{}",
            input.scope_work_center_id.map(|w| w.to_string()).unwrap_or_else(|| "-".into()),
            serde_json::to_string(&input.subject_type).unwrap_or_default(),
            input.subject_id.map(|s| s.to_string()).unwrap_or_else(|| "-".into()),
            input.condition_type
        ),
    });

    // 1. Find an OPEN condition with the same signature — the same
    //    underlying condition reuses ONE record.
    let existing: Option<OperationalCondition> = sqlx::query_as(
        "SELECT id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                subject_id, expected_condition, observed_condition, gap, risk, status, \
                help_required, containment_required, expertise_required, owner_id, \
                response_due_at, learning, \
                COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                source_entity_type, source_entity_id, created_at, updated_at \
         FROM operational_conditions \
         WHERE tenant_id = $1 AND status IN ('open', 'responding', 'investigating') \
           AND learning->>'recurrence_signature' = $2 \
         ORDER BY created_at DESC LIMIT 1",
    )
    .bind(tenant_id)
    .bind(
        signature["recurrence_signature"]
            .as_str()
            .unwrap_or_default(),
    )
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Condition lookup failed: {e}")))?;

    if let Some(mut cond) = existing {
        // Reinforce: refresh the observed condition + recurrence count.
        let count = cond.recurrence_count + 1;
        let mut learning = cond.learning.clone();
        if let Some(obj) = learning.as_object_mut() {
            obj.insert("recurrence_count".to_string(), serde_json::json!(count));
        }
        let row: OperationalCondition = sqlx::query_as(
            "UPDATE operational_conditions SET \
                observed_condition = $3, risk = $4, gap = $5, status = 'responding', \
                help_required = $6, containment_required = $7, expertise_required = $8, \
                learning = $9, updated_at = NOW() \
             WHERE id = $1 AND tenant_id = $2 \
             RETURNING id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                subject_id, expected_condition, observed_condition, gap, risk, status, \
                help_required, containment_required, expertise_required, owner_id, \
                response_due_at, learning, \
                COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                source_entity_type, source_entity_id, created_at, updated_at",
        )
        .bind(cond.id)
        .bind(tenant_id)
        .bind(&input.observed_condition)
        .bind(&input.risk)
        .bind(&input.gap)
        .bind(input.help_required)
        .bind(input.containment_required)
        .bind(&input.expertise_required)
        .bind(learning)
        .fetch_one(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Condition reinforce failed: {e}")))?;
        cond = row;
        return Ok(cond);
    }

    // 2. New condition.
    let id = Uuid::new_v4();
    let number = format!(
        "COND-{}",
        &id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..6]
    );
    let learning = serde_json::json!({
        "recurrence_signature": signature["recurrence_signature"],
        "recurrence_count": 1,
    });
    let row: OperationalCondition = sqlx::query_as(
        "INSERT INTO operational_conditions \
            (id, tenant_id, condition_number, scope_site_id, scope_value_stream_id, \
             scope_work_center_id, scope_shift_id, subject_type, subject_id, \
             expected_condition, observed_condition, gap, risk, status, \
             help_required, containment_required, expertise_required, owner_id, \
             response_due_at, learning, source_entity_type, source_entity_id, \
             created_at, updated_at) \
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb,$11::jsonb,$12::jsonb,$13::jsonb, \
                 'open',$14,$15,$16,$17,NOW(),$18::jsonb,$19,$20,NOW(),NOW()) \
         RETURNING id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                subject_id, expected_condition, observed_condition, gap, risk, status, \
                help_required, containment_required, expertise_required, owner_id, \
                response_due_at, learning, \
                COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                source_entity_type, source_entity_id, created_at, updated_at",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(&number)
    .bind(input.scope_site_id)
    .bind(input.scope_value_stream_id)
    .bind(input.scope_work_center_id)
    .bind(input.scope_shift_id)
    .bind(serde_json::to_string(&input.subject_type).unwrap_or_default())
    .bind(input.subject_id)
    .bind(&input.expected_condition)
    .bind(&input.observed_condition)
    .bind(&input.gap)
    .bind(&input.risk)
    .bind(input.help_required)
    .bind(input.containment_required)
    .bind(&input.expertise_required)
    .bind(input.created_by)
    .bind(learning)
    .bind(&input.source_entity_type)
    .bind(input.source_entity_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Condition open failed: {e}")))?;
    Ok(row)
}

/// Mark a condition contained (risk controlled — distinct from resolved).
pub async fn contain_condition(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    id: Uuid,
    by: Uuid,
) -> Result<OperationalCondition> {
    let row: OperationalCondition = sqlx::query_as(
        "UPDATE operational_conditions SET status = 'contained', owner_id = $3, updated_at = NOW() \
         WHERE id = $1 AND tenant_id = $2 \
         RETURNING id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                subject_id, expected_condition, observed_condition, gap, risk, status, \
                help_required, containment_required, expertise_required, owner_id, \
                response_due_at, learning, \
                COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                source_entity_type, source_entity_id, created_at, updated_at",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(by)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Condition contain failed: {e}")))?
    .ok_or_else(|| SenseiError::NotFound(format!("Condition {id} not found")))?;
    Ok(row)
}

/// Attach learning artifacts to a condition (A3/experiment/verification/
/// standardization ids).
pub async fn attach_learning(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    id: Uuid,
    problem_solving_id: Option<Uuid>,
    experiment_id: Option<Uuid>,
    verification_id: Option<Uuid>,
    standardization_id: Option<Uuid>,
) -> Result<OperationalCondition> {
    let existing: Option<(serde_json::Value,)> = sqlx::query_as(
        "SELECT learning FROM operational_conditions WHERE id = $1 AND tenant_id = $2",
    )
    .bind(id)
    .bind(tenant_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Condition read failed: {e}")))?;
    let Some((mut learning,)) = existing else {
        return Err(SenseiError::NotFound(format!("Condition {id} not found")));
    };
    if let Some(obj) = learning.as_object_mut() {
        if let Some(v) = problem_solving_id {
            obj.insert("problem_solving_id".to_string(), serde_json::json!(v));
        }
        if let Some(v) = experiment_id {
            obj.insert("experiment_id".to_string(), serde_json::json!(v));
        }
        if let Some(v) = verification_id {
            obj.insert("verification_id".to_string(), serde_json::json!(v));
        }
        if let Some(v) = standardization_id {
            obj.insert("standardization_id".to_string(), serde_json::json!(v));
        }
    }
    let row: OperationalCondition = sqlx::query_as(
        "UPDATE operational_conditions SET learning = $3, updated_at = NOW() \
         WHERE id = $1 AND tenant_id = $2 \
         RETURNING id, tenant_id, condition_number, scope_work_center_id, subject_type, \
                subject_id, expected_condition, observed_condition, gap, risk, status, \
                help_required, containment_required, expertise_required, owner_id, \
                response_due_at, learning, \
                COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \
                source_entity_type, source_entity_id, created_at, updated_at",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(learning)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Condition learning attach failed: {e}")))?;
    Ok(row)
}
