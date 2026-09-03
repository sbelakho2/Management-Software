//! Country policy bundle routes (fifteenth audit item 84): language,
//! currency, units, week/calendar, holiday schedule, timezone, data
//! residency, retention, employment-data visibility and local document
//! requirements — as POLICY OBJECTS, never `if country == Morocco` code
//! forks. `GET` reads the bundle for a country; `POST` PUBLISHES a
//! revision (a new country is a policy RECORD, never a code change) —
//! one atomic transaction appends the versioned compliance row AND
//! refreshes the current `country_policies` row (twenty-seventh-audit
//! P0), so current content and the reported revision never diverge.

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};

use crate::state::AppState;

use sensei_services::tps::country_policy::{
    self, locale_for_policy, publish_policy_version, CountryPolicy,
};

// ── Helpers ─────────────────────────────────────────────────────────────────

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Country policies require the database".to_string()))
        .map(|p| p.as_ref())
}

// ── Handlers ────────────────────────────────────────────────────────────────

/// `GET /api/v1/policies/country/{country}` — fetch the policy bundle for
/// one country. The bundle itself carries the locale (`locale`), so
/// clients format by POLICY, never by hard-coded country branches.
pub async fn get_country(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(country): Path<String>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("system:audit:read")?;
    let p = pool(&state)?;
    let policy = country_policy::get_country_policy(p, user.tenant_id, &country).await?;
    Ok(Json(serde_json::json!({
        "country": policy.country,
        "language": policy.language,
        "currency": policy.currency,
        "unit_system": policy.unit_system,
        "week_start": policy.week_start,
        "holiday_schedule": policy.holiday_schedule,
        "timezone": policy.timezone,
        "data_residency": policy.data_residency,
        "retention_days": policy.retention_days,
        "employment_data_visibility": policy.employment_data_visibility,
        "local_document_requirements": policy.local_document_requirements,
        "locale": locale_for_policy(&policy),
    })))
}

/// `POST /api/v1/policies/country` — PUBLISH a country policy revision.
/// Seventeenth audit item 13: the versioned publish operation is the ONLY
/// write path — every change creates the historical compliance record
/// (`country_policy_versions`); the unversioned upsert (a legacy seed
/// helper in the service layer) is never routed. Twenty-seventh-audit
/// P0: `publish_policy_version` writes ONE atomic transaction — it
/// appends the version row AND refreshes the current `country_policies`
/// row from the same payload, so the residency/locale CONTENT the
/// governance readers consume and the revision NUMBER they pin can never
/// diverge (revision 7 never carries revision-6 content). The caller
/// needs the dedicated management permission, not the read-only audit
/// permission.
pub async fn upsert(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(policy): Json<CountryPolicy>,
) -> Result<Json<CountryPolicy>> {
    user.require_permission("system:country-policy:manage")?;
    let p = pool(&state)?;
    publish_policy_version(p, user.tenant_id, policy.clone(), Some(user.user_id)).await?;
    Ok(Json(policy))
}
