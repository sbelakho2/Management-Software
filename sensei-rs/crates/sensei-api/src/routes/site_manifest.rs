//! Declarative SITE MANIFEST routes (fifteenth audit 83/93/A17): a new
//! plant comes onto Starz Forge as RECORDS, not code. `POST
//! /api/v1/sites/manifest` upserts the declarative manifest,
//! `POST /api/v1/sites/bootstrap` upserts the manifest AND seeds the
//! canonical metric definitions in one transaction (provisioning only),
//! `GET /api/v1/sites/{site_id}/manifest` reads it back, and the
//! lifecycle (sixteenth audit 63-64/96) is climbed via
//! `POST /api/v1/sites/{site_id}/validate` (validation report +
//! draft → validated) and `POST /api/v1/sites/{site_id}/activate`
//! (validated → active).

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::Deserialize;
use uuid::Uuid;

use crate::state::AppState;

use sensei_services::tps::site_manifest::{self, SiteManifest, ValidationReport};

// ── Request DTO ─────────────────────────────────────────────────────────────

/// Body for `POST /api/v1/sites/manifest` and
/// `POST /api/v1/sites/bootstrap`.
#[derive(Debug, Deserialize)]
pub struct ManifestRequest {
    pub site_id: Uuid,
    pub country: String,
    #[serde(default = "default_timezone")]
    pub timezone: String,
    #[serde(default)]
    pub languages: Vec<String>,
    #[serde(default = "default_currency")]
    pub currency: String,
    pub capabilities: Vec<String>,
    #[serde(default)]
    pub integrations: Vec<serde_json::Value>,
    pub policy_bundle: Option<String>,
}

fn default_timezone() -> String {
    "UTC".to_string()
}

fn default_currency() -> String {
    "USD".to_string()
}

impl From<ManifestRequest> for SiteManifest {
    fn from(req: ManifestRequest) -> Self {
        Self {
            site_id: req.site_id,
            country: req.country,
            timezone: req.timezone,
            languages: req.languages,
            currency: req.currency,
            capabilities: req.capabilities,
            integrations: req.integrations,
            policy_bundle: req.policy_bundle,
        }
    }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

fn pool(state: &AppState) -> Result<&sqlx::PgPool> {
    state
        .db_pool
        .as_ref()
        .ok_or_else(|| SenseiError::Database("Site manifest requires the database".to_string()))
        .map(|p| p.as_ref())
}

// ── Handlers ────────────────────────────────────────────────────────────────

/// `POST /api/v1/sites/manifest` — upsert the declarative manifest for one
/// site of the caller's tenant.
pub async fn upsert_manifest(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ManifestRequest>,
) -> Result<Json<()>> {
    user.require_permission("master-data:products:manage")?;
    let p = pool(&state)?;
    site_manifest::upsert_manifest(p, user.tenant_id, req.into()).await?;
    Ok(Json(()))
}

/// `POST /api/v1/sites/bootstrap` — one transaction: upsert the manifest
/// AND seed the canonical metric definitions. This only PROVISIONS the
/// site (manifest + metrics); the site becomes operational through
/// `validate_site` + `activate_site`.
pub async fn bootstrap_site(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ManifestRequest>,
) -> Result<Json<()>> {
    user.require_permission("master-data:products:manage")?;
    let p = pool(&state)?;
    site_manifest::bootstrap_site(p, user.tenant_id, req.into()).await?;
    Ok(Json(()))
}

/// `GET /api/v1/sites/{site_id}/manifest` — read the declarative manifest
/// for one site of the caller's tenant.
pub async fn get_manifest(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(site_id): Path<Uuid>,
) -> Result<Json<Option<SiteManifest>>> {
    user.require_permission("master-data:products:manage")?;
    let p = pool(&state)?;
    Ok(Json(
        site_manifest::get_manifest(p, user.tenant_id, site_id).await?,
    ))
}

/// `POST /api/v1/sites/{site_id}/validate` — run the operational-
/// qualification checks (sixteenth audit 63/96) and return the validation
/// report; a ready report advances the site draft → validated.
pub async fn validate_site(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(site_id): Path<Uuid>,
) -> Result<Json<ValidationReport>> {
    user.require_permission("master-data:products:manage")?;
    let p = pool(&state)?;
    Ok(Json(
        site_manifest::validate_site(p, user.tenant_id, site_id).await?,
    ))
}

/// `POST /api/v1/sites/{site_id}/activate` — the guarded ladder step
/// validated → active; a site in any other status is rejected.
pub async fn activate_site(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(site_id): Path<Uuid>,
) -> Result<Json<()>> {
    user.require_permission("master-data:products:manage")?;
    let p = pool(&state)?;
    site_manifest::activate_site(p, user.tenant_id, site_id).await?;
    Ok(Json(()))
}
