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
