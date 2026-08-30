//! Daily tier management (item 54): Tier 1 (line/cell, every shift) through
//! Tier 4 (site/business). Escalations carry the SAME issue id upward.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::SenseiError;
use uuid::Uuid;

use crate::state::AppState;
use crate::stores::TierMeeting;

/// Schedule a tier meeting occurrence.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct ScheduleTierMeetingRequest {
    /// 1 = line/cell, 2 = value stream, 3 = plant, 4 = site/business.
    pub tier_level: u8,
    pub title: String,
    /// Topology anchors (item 15) — the meeting belongs to the SAME
    /// organizational objects the operating system tracks.
    pub site_id: Option<Uuid>,
    pub value_stream_id: Option<Uuid>,
    pub work_center_id: Option<Uuid>,
    pub shift_id: Option<Uuid>,
    pub leader_id: Option<Uuid>,
    #[serde(default)]
    pub attendee_ids: Vec<Uuid>,
    pub area: Option<String>,
    pub scheduled_at: chrono::DateTime<chrono::Utc>,
}

pub async fn schedule_tier_meeting(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ScheduleTierMeetingRequest>,
) -> Result<Json<TierMeeting>, SenseiError> {
    user.require_permission("tps:obeya:manage")?;
    if !(1..=4).contains(&req.tier_level) {
        return Err(SenseiError::Validation(
            "tier_level must be 1 (line/cell), 2 (value stream), 3 (plant) or 4 (site)".to_string(),
        ));
    }
    // A line/cell meeting (tier 1) without a work center is not anchored —
    // reject it rather than storing a floating meeting.
    if req.tier_level == 1 && req.work_center_id.is_none() {
        return Err(SenseiError::Validation(
            "tier_level 1 (line/cell) meetings require a work_center_id".to_string(),
        ));
    }
    if req.tier_level == 2 && req.value_stream_id.is_none() {
        return Err(SenseiError::Validation(
            "tier_level 2 (value stream) meetings require a value_stream_id".to_string(),
        ));
    }
    let now = chrono::Utc::now();
    let meeting = TierMeeting {
        id: Uuid::new_v4(),
        tenant_id: user.tenant_id,
        tier_level: req.tier_level,
        title: req.title,
        site_id: req.site_id,
        value_stream_id: req.value_stream_id,
        work_center_id: req.work_center_id,
        shift_id: req.shift_id,
        leader_id: req.leader_id,
        attendee_ids: req.attendee_ids,
        status: "planned".to_string(),
        area: req.area,
        scheduled_at: req.scheduled_at,
        started_at: None,
        completed_at: None,
        metric_snapshots: vec![],
        abnormality_ids: vec![],
        escalation_ids: vec![],
        action_ids: vec![],
        abnormality_id: None,
        escalated_from: None,
        escalated_to: None,
        action_id: None,
        owner: None,
        deadline: None,
        created_by: user.user_id,
        created_at: now,
    };
    let mut store = state.tier_meetings.write(user.tenant_id).await;
    store.insert(meeting.id, meeting.clone());
    store.persist().await?;
    Ok(Json(meeting))
}

/// Start a tier meeting (server-owned timestamp).
pub async fn start_tier_meeting(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<TierMeeting>, SenseiError> {
    user.require_permission("tps:obeya:manage")?;
    let mut store = state.tier_meetings.write(user.tenant_id).await;
    let meeting = store
        .get_mut(&id)
        .filter(|m| m.tenant_id == user.tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Tier meeting {id} not found")))?;
    if meeting.started_at.is_none() {
        meeting.started_at = Some(chrono::Utc::now());
    }
    meeting.status = "in_progress".to_string();
    let cloned = meeting.clone();
    store.persist().await?;
    Ok(Json(cloned))
}

/// Complete a tier meeting (server-owned timestamp).
pub async fn complete_tier_meeting(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<TierMeeting>, SenseiError> {
    user.require_permission("tps:obeya:manage")?;
    let mut store = state.tier_meetings.write(user.tenant_id).await;
    let meeting = store
        .get_mut(&id)
        .filter(|m| m.tenant_id == user.tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Tier meeting {id} not found")))?;
    let now = chrono::Utc::now();
    if meeting.started_at.is_none() {
        meeting.started_at = Some(now);
    }
    meeting.completed_at = Some(now);
    meeting.status = "completed".to_string();
    let cloned = meeting.clone();
    store.persist().await?;
    Ok(Json(cloned))
}

/// Escalate the SAME issue from this meeting to a higher-tier meeting
/// (item 15): the abnormality/action linkage is carried up — the source
/// meeting is marked `escalated` and the target meeting records
/// `escalated_from`.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct EscalateRequest {
    pub target_meeting_id: Uuid,
    pub abnormality_id: Uuid,
    pub action_id: Option<Uuid>,
    pub owner: Option<Uuid>,
    pub deadline: Option<chrono::DateTime<chrono::Utc>>,
}

pub async fn escalate_issue(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<EscalateRequest>,
) -> Result<Json<TierMeeting>, SenseiError> {
    user.require_permission("tps:obeya:manage")?;
    let mut store = state.tier_meetings.write(user.tenant_id).await;
    let source_level = {
        let source = store
            .get_mut(&id)
            .filter(|m| m.tenant_id == user.tenant_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Tier meeting {id} not found")))?;
        if source.tier_level >= 4 {
            return Err(SenseiError::Validation(
                "Cannot escalate beyond tier 4 (site/business)".to_string(),
            ));
        }
        source.tier_level
    };
    let target = store
        .get_mut(&req.target_meeting_id)
        .filter(|m| m.tenant_id == user.tenant_id)
        .ok_or_else(|| {
            SenseiError::NotFound(format!(
                "Target tier meeting {} not found",
                req.target_meeting_id
            ))
        })?;
    if target.tier_level <= source_level {
        return Err(SenseiError::Validation(format!(
            "Escalation must go UP: source is tier {}, target must be tier {} or higher",
            source_level,
            source_level + 1
        )));
    }
    // The SAME issue id travels upward; the target records where it came from.
    target.abnormality_id = Some(req.abnormality_id);
    target.escalated_from = Some(id);
    target.action_id = req.action_id.or(target.action_id);
    target.owner = req.owner.or(target.owner);
    target.deadline = req.deadline.or(target.deadline);
    if !target.abnormality_ids.contains(&req.abnormality_id) {
        target.abnormality_ids.push(req.abnormality_id);
    }
    let cloned = target.clone();
    // The source meeting is marked escalated AFTER the target is recorded —
    // the source is identified by the same issue id carrying upward.
    let source = store
        .get_mut(&id)
        .filter(|m| m.tenant_id == user.tenant_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Tier meeting {id} not found")))?;
    if !source.escalation_ids.contains(&req.target_meeting_id) {
        source.escalation_ids.push(req.target_meeting_id);
    }
    source.status = "escalated".to_string();
    store.persist().await?;
    Ok(Json(cloned))
}

/// The GENERATED tier agenda (thirteenth audit): the meeting is an
/// exception-processing queue — unresolved conditions, open help calls,
/// active containments and persistent pitch gaps are brought
/// automatically. No manual board prep, no retyping, no PowerPoint. The
/// same condition ID flows upward.
#[derive(Debug, Clone, serde::Serialize, sqlx::FromRow)]
pub struct TierAgendaItem {
    pub condition_id: uuid::Uuid,
    pub condition_number: String,
    pub work_center_id: Option<uuid::Uuid>,
    pub subject_type: String,
    pub issue_type: String,
    pub status: String,
    pub recurrence_count: i64,
    pub help_required: bool,
    pub containment_required: bool,
    pub expertise_required: Option<String>,
    pub source_entity_type: Option<String>,
    pub source_entity_id: Option<uuid::Uuid>,
    pub opened_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, serde::Serialize)]
pub struct TierAgenda {
    pub tier_level: i64,
    pub generated_at: chrono::DateTime<chrono::Utc>,
    /// Unresolved conditions that flow upward with the SAME id.
    pub items: Vec<TierAgendaItem>,
    /// What the tier must decide about each (plain language).
    pub guidance: String,
}

pub async fn generate_agenda(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<TierAgendaParams>,
) -> Result<Json<TierAgenda>, SenseiError> {
    user.require_permission("tps:obeya:read")?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Agenda requires the database".to_string()))?;
    let tier = params.tier_level.unwrap_or(1).clamp(1, 4);
    // Tier 1 = everything unresolved at the work center; higher tiers
    // only receive what lower tiers cannot resolve (escalated/contained-
    // pending conditions with recurrence ≥ tier or open help calls).
    let rows: Vec<TierAgendaItem> = sqlx::query_as(
        "SELECT id, condition_number, scope_work_center_id, subject_type, \\
                COALESCE(observed_condition->>'issue_type', 'condition') AS issue_type, \\
                status, \\
                COALESCE((learning->>'recurrence_count')::bigint, 0) AS recurrence_count, \\
                help_required, containment_required, expertise_required, \\
                source_entity_type, source_entity_id, created_at \\
         FROM operational_conditions \\
         WHERE tenant_id = $1 \\
           AND status IN ('open', 'responding', 'contained', 'investigating') \\
           AND ($2 = 1 \\
                OR help_required = TRUE \\
                OR COALESCE((learning->>'recurrence_count')::bigint, 0) >= $2) \\
         ORDER BY \\
           CASE WHEN containment_required THEN 0 ELSE 1 END, \\
           COALESCE((learning->>'recurrence_count')::bigint, 0) DESC, \\
           created_at ASC \\
         LIMIT 100",
    )
    .bind(user.tenant_id)
    .bind(tier)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Agenda generation failed: {e}")))?;

    let guidance = match tier {
        1 => {
            "Tier 1 decides: contain it now, clear the barrier, or escalate the SAME condition id."
                .to_string()
        }
        2 => {
            "Tier 2 receives only what Tier 1 could not resolve — same condition ids, no retyping."
                .to_string()
        }
        3 => "Tier 3 receives only cross-functional conditions the lower tiers cannot clear."
            .to_string(),
        _ => {
            "Tier 4 (site/business) receives only conditions that survive three tiers.".to_string()
        }
    };
    Ok(Json(TierAgenda {
        tier_level: tier,
        generated_at: chrono::Utc::now(),
        items: rows,
        guidance,
    }))
}

#[derive(Debug, serde::Deserialize)]
pub struct TierAgendaParams {
    pub tier_level: Option<i64>,
}
