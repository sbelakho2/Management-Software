//! Authorization snapshot routes (fifteenth audit 24/A5): every AI
//! execution carries the policy/relationship/principal revision it was
//! authorized under. `GET /api/v1/authorization/snapshot` exposes the
//! current revision triple; `POST /api/v1/authorization/bump` bumps one
//! revision (a revocation bumps the principal revision), which changes the
//! cache salt and invalidates every authorization-derived cache.

use axum::extract::State;
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Deserialize;

use crate::state::AppState;

use sensei_services::tps::authorization_revisions::{self, AuthorizationSnapshot};

// ── Helpers ─────────────────────────────────────────────────────────────────

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| {
            SenseiError::Database("Authorization revisions require the database".to_string())
        })
        .map(|p| p.as_ref())
}

/// Administrative role gate — same authority set as `admin.rs`.
fn require_admin(user: &AuthenticatedUser) -> Result<()> {
    if user.has_any_role(&[
        "platform_admin",
        "tenant_admin",
        "finance_manager",
        "hr_manager",
        "purchasing_manager",
        "inventory_manager",
        "sales_manager",
        "quality_manager",
        "production_manager",
        "platform_superadmin",
    ]) {
        Ok(())
    } else {
        Err(SenseiError::Forbidden(
            "Administrative role required for this endpoint".to_string(),
        ))
    }
}

// ── Handlers ────────────────────────────────────────────────────────────────

/// `GET /api/v1/authorization/snapshot` — the current authorization
/// revision triple. Every execution embeds this snapshot so retrieval can
/// never run under one permission state and execution under another.
pub async fn get_snapshot(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<AuthorizationSnapshot>> {
    user.require_permission("system:audit:read")?;
    let p = pool(&state)?;
    let snapshot = authorization_revisions::current_snapshot(p, user.tenant_id).await?;
    Ok(Json(snapshot))
}

/// Body for the revision bump: which permission domain changed.
#[derive(Debug, Deserialize)]
pub struct BumpRequest {
    pub kind: String,
}

/// `POST /api/v1/authorization/bump` — increment one revision domain.
/// Bumping the principal revision is the A5 revocation signal: the cache
/// salt changes and every authorization-derived cache is invalidated.
pub async fn bump(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<BumpRequest>,
) -> Result<Json<AuthorizationSnapshot>> {
    require_admin(&user)?;
    let p = pool(&state)?;
    match req.kind.as_str() {
        "policy" => authorization_revisions::bump_policy(p, user.tenant_id).await?,
        "relationship" => authorization_revisions::bump_relationship(p, user.tenant_id).await?,
        "principal" => authorization_revisions::bump_principal(p, user.tenant_id).await?,
        other => {
            return Err(SenseiError::Validation(format!(
                "unknown revision kind: {other} (expected policy|relationship|principal)"
            )))
        }
    }
    let snapshot = authorization_revisions::current_snapshot(p, user.tenant_id).await?;
    Ok(Json(snapshot))
}
