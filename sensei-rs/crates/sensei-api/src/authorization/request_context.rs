//! Generic [`RequestContext`] builder (twenty-ninth audit Wave B item 7):
//! ONE server-created context per HTTP request, built from the
//! authenticated principal + application state — the domain service
//! methods no longer take naked `tenant_id`s, they take this context
//! (`ctx.tenant`, `ctx.scope`, `ctx.focus`).
//!
//! # Modes
//!
//! - **DB-backed state** (`state.db_pool` present): the focus candidate is
//!   resolved with the SAME one-pass logic as the agent context
//!   (`routes::agent::build_context` — the validated `active_site` /
//!   `active_value_stream` / `active_work_center` / `active_shift`
//!   tuple, the caller_sites pattern used by the Andon routes) and
//!   [`RequestContext::build`] re-validates it against the principal's
//!   ACTIVE role-slot scope and the topology chain in one transaction.
//!   A principal with no active assignment resolves to
//!   `NoOperationalScope` — every scoped statement then matches zero
//!   rows (fail closed).
//! - **In-memory state** (dev/tests, no pool): no scope authority exists,
//!   so the context carries the explicit `TenantWide` grant (the legacy
//!   in-memory semantics) and an empty focus. Pure in-memory API tests
//!   therefore exercise the same ctx-based service surface without a
//!   database.
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::request_context::{OperationalFocus, RequestContext};
use sensei_core::domain::scope::AuthorizedScope;
use sensei_core::error::{Result, SenseiError};

use crate::routes::agent::build_context;
use crate::state::AppState;

/// Build the server-created [`RequestContext`] for one authenticated
/// request.
///
/// The focus resolution is identical to the Andon routes' `caller_sites`
/// pattern: the agent-context candidate tuple (users.site_id hint + the
/// newest ACTIVE employee assignment) is validated by
/// [`RequestContext::build`] against the principal's DB-resolved scope
/// and the topology chain. With no database pool the context is the
/// explicit tenant-wide grant used by the in-memory development/test
/// services.
pub async fn build_request_context(
    user: &AuthenticatedUser,
    state: &AppState,
) -> Result<RequestContext> {
    match state.db_pool.as_ref() {
        Some(pool) => {
            let agent = build_context(user, state).await;
            RequestContext::build(
                pool,
                user.tenant_id,
                user.user_id,
                agent.site_id,
                agent.value_stream_id,
                agent.work_center_id,
                agent.shift_id,
                String::new(),
            )
            .await
            .map_err(|e| SenseiError::Validation(format!("request context build failed: {e}")))
        }
        // In-memory (dev/test) mode: no scope authority exists in the
        // in-memory services, so the caller acts with the explicit
        // tenant-wide grant inside their own tenant (the legacy
        // tenant_id-only semantics, now carried on the context).
        None => Ok(RequestContext {
            tenant: user.tenant_id,
            principal: user.user_id,
            scope: AuthorizedScope::tenant_wide(),
            focus: OperationalFocus {
                site: None,
                value_stream: None,
                work_center: None,
                shift: None,
            },
            locale: None,
            timezone: None,
            currency: None,
            country_policy_revision: None,
            trace_id: String::new(),
        }),
    }
}
