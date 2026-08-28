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
    let now = chrono::Utc::now();
    let meeting = TierMeeting {
        id: Uuid::new_v4(),
        tenant_id: user.tenant_id,
        tier_level: req.tier_level,
        title: req.title,
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
    let cloned = meeting.clone();
    store.persist().await?;
    Ok(Json(cloned))
}
