//! Role-specific analytics route (fifteenth audit 48-68 + A14): the
//! response shape is NOW / ABNORMAL / WHY / NEXT / LEARN for EVERY role —
//! what needs attention, why, and what to do about it. The role is derived
//! from the caller's own roles and the scope (site + work center) comes
//! from the caller's context: an operator only ever sees their own work
//! center, never a universal dashboard, never operator rankings.

use axum::extract::State;
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_services::tps::role_analytics::{
    build_role_analytics, select_active_role, RoleAnalytics,
};

use crate::routes::agent::build_context;
use crate::state::AppState;

/// GET /api/v1/analytics/role — the caller's role-specific analytics,
/// scoped to the caller's site and work center (resolved server-side from
/// the employee assignment; the caller never supplies the scope). The
/// active role is resolved by the EXPLICIT analytics priority (item 32),
/// NOT by the order of `user.roles`: a user who is both an operator and a
/// site manager sees the site-manager analytics of their primary
/// function.
pub async fn get_role_analytics(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<RoleAnalytics>> {
    user.require_permission("tps:kpi:read")?;
    let role = select_active_role(user.roles.as_slice()).ok_or_else(|| {
        SenseiError::Forbidden(
            "no supported active role (site_manager/manager/quality/planner/supervisor/team_lead/operator)"
                .to_string(),
        )
    })?;
    let pool = state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("no database pool configured".to_string()))?;
    // The scope is SERVER-resolved from the caller's own context (item
    // 17): the caller cannot ask for another site/work center.
    let ctx = build_context(&user, &state).await;
    let analytics =
        build_role_analytics(pool, user.tenant_id, &role, ctx.site_id, ctx.work_center_id).await?;
    Ok(Json(analytics))
}
