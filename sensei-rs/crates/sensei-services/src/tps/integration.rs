//! Integration INSTANCE lifecycle + checkpoint producer (twenty-second
//! audit P1): the integration instance is the unit of readiness — the
//! bridge advances ONE instance (instance_id), never a tenant-global
//! (source_system, source_table) cursor, so one healthy SAP checkpoint
//! can never certify another site's SAP.
//!
//! - `reconcile_instances` is the PRODUCER: it reads the site manifest's
//!   declared integration kinds and materializes one
//!   `integration_instances` row per declared kind FOR THIS SITE
//!   (fail-closed RLS like every tenant-owned table).
//! - `write_checkpoint` advances ONE instance's durable watermark
//!   (instance_id): the instance must be visible under the caller's
//!   tenant (unknown → NotFound = 404) and must be ENABLED (disabled →
//!   Conflict = 409 — a decommissioned instance can never be advanced).
//! - `get_checkpoint` reads that instance's watermark: `None` means the
//!   instance NEVER RAN (NeverRun/Unknown) — never a fabricated
//!   `Utc::now()`.

use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

use super::site_manifest::with_tenant_tx;

/// The durable cursor of ONE integration instance (NeverRun when absent).
#[derive(Debug, Clone, serde::Serialize)]
pub struct CheckpointState {
    pub watermark: chrono::DateTime<chrono::Utc>,
    pub watermark_id: Option<String>,
    pub last_run_id: Option<String>,
    pub last_run_at: chrono::DateTime<chrono::Utc>,
}

/// The instance producer: read the site manifest's declared integration
/// kinds (`site_manifests.integrations`, a JSONB array of `{kind}`) and
/// UPSERT one `integration_instances` row per declared kind for THIS
/// site. Re-running is idempotent: the row's `configuration_revision`
/// follows the manifest revision (an INSERT seeds it from the current
/// `manifest_version`; the ON CONFLICT update refreshes it to the
/// EXCLUDED revision so a re-reconciled site tracks the manifest it was
/// reconciled from).
///
/// Returns the number of integration instances that exist for this site
/// after reconciliation.
///
/// - A site with NO manifest row is an error (bootstrap first).
/// - A manifest whose `integrations` is NULL has no integration policy —
///   nothing can be provisioned from it (fail closed).
/// - An EXPLICIT empty `[]` policy provisions nothing and returns 0.
pub async fn reconcile_instances(pool: &PgPool, tenant_id: Uuid, site_id: Uuid) -> Result<i64> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let row: Option<(Option<serde_json::Value>, i32)> = sqlx::query_as(
                "SELECT integrations, manifest_version FROM site_manifests \
                 WHERE tenant_id = $1 AND site_id = $2",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Site manifest read failed: {e}")))?;
            let (integrations, manifest_version) = row.ok_or_else(|| {
                SenseiError::Validation(format!(
                    "no site manifest for site {site_id} — bootstrap the site first"
                ))
            })?;
            match &integrations {
                None => {
                    return Err(SenseiError::Validation(
                        "integration policy not configured — the site manifest's \
                         integrations column is NULL; declare an explicit [] policy \
                         or provision declared kinds"
                            .to_string(),
                    ));
                }
                Some(v) if !v.is_array() => {
                    return Err(SenseiError::Validation(
                        "integration policy is malformed — site_manifests.integrations \
                         must be a JSON array of {kind} objects"
                            .to_string(),
                    ));
                }
                Some(v) => {
                    if v.as_array().map(|a| a.is_empty()).unwrap_or(false) {
                        // Explicit '[]' policy: the site requires no
                        // integrations — nothing to provision.
                    } else {
                        sqlx::query(
                            "INSERT INTO integration_instances \
                                 (tenant_id, site_id, integration_type, endpoint, \
                                  configuration_revision) \
                             SELECT $1, $2, elem->>'kind', NULL, $3 \
                             FROM jsonb_array_elements($4::jsonb) AS elem \
                             WHERE elem->>'kind' IS NOT NULL AND elem->>'kind' <> '' \
                             ON CONFLICT (tenant_id, site_id, integration_type) \
                             DO UPDATE SET configuration_revision = EXCLUDED.configuration_revision",
                        )
                        .bind(tenant_id)
                        .bind(site_id)
                        .bind(manifest_version)
                        .bind(v)
                        .execute(&mut **tx)
                        .await
                        .map_err(|e| {
                            SenseiError::Database(format!(
                                "Integration instance reconcile failed: {e}"
                            ))
                        })?;
                    }
                }
            }
            let count: i64 = sqlx::query_scalar(
                "SELECT COUNT(*) FROM integration_instances \
                 WHERE tenant_id = $1 AND site_id = $2",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Instance count failed: {e}")))?;
            Ok(count)
        })
    })
    .await
}

/// Advance ONE integration instance's checkpoint (the bridge's durable
/// cursor). The instance row is resolved against the caller's tenant —
/// an instance that is not visible under that tenant is unknown
/// (NotFound), and a DISABLED (decommissioned) instance refuses
/// advancement (Conflict). `source_system`/`source_table` are OPTIONAL
/// legacy metadata: the readiness proof is `instance_id`, so a write
/// never needs them.
#[allow(clippy::too_many_arguments)]
pub async fn write_checkpoint(
    pool: &PgPool,
    tenant_id: Uuid,
    instance_id: Uuid,
    source_system: Option<String>,
    source_table: Option<String>,
    watermark: chrono::DateTime<chrono::Utc>,
    watermark_id: Option<String>,
    run_id: String,
) -> Result<()> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let instance: Option<(bool,)> = sqlx::query_as(
                "SELECT enabled FROM integration_instances \
                 WHERE tenant_id = $1 AND id = $2",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Integration instance lookup failed: {e}"))
            })?;
            let Some((enabled,)) = instance else {
                return Err(SenseiError::NotFound(format!(
                    "integration instance {instance_id} not found for this tenant"
                )));
            };
            if !enabled {
                return Err(SenseiError::Conflict(format!(
                    "integration instance {instance_id} is disabled — a decommissioned \
                     instance cannot be advanced"
                )));
            }
            sqlx::query(
                "INSERT INTO integration_checkpoints \
                     (tenant_id, instance_id, source_system, source_table, \
                      watermark, watermark_id, last_run_id, last_run_at) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, NOW()) \
                 ON CONFLICT (tenant_id, instance_id) DO UPDATE SET \
                     source_system = COALESCE(EXCLUDED.source_system, \
                                              integration_checkpoints.source_system), \
                     source_table = COALESCE(EXCLUDED.source_table, \
                                             integration_checkpoints.source_table), \
                     watermark = EXCLUDED.watermark, \
                     watermark_id = EXCLUDED.watermark_id, \
                     last_run_id = EXCLUDED.last_run_id, \
                     last_run_at = NOW()",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .bind(&source_system)
            .bind(&source_table)
            .bind(watermark)
            .bind(&watermark_id)
            .bind(&run_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Checkpoint write failed: {e}")))?;
            Ok(())
        })
    })
    .await
}

/// Read one integration instance's checkpoint. `Ok(None)` is NEVER
/// RUN (Unknown) — a missing checkpoint is never a fabricated
/// `Utc::now()`. An instance that is not visible under the caller's
/// tenant is NotFound.
pub async fn get_checkpoint(
    pool: &PgPool,
    tenant_id: Uuid,
    instance_id: Uuid,
) -> Result<Option<CheckpointState>> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let instance: Option<(Uuid,)> = sqlx::query_as(
                "SELECT id FROM integration_instances \
                 WHERE tenant_id = $1 AND id = $2",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Integration instance lookup failed: {e}"))
            })?;
            if instance.is_none() {
                return Err(SenseiError::NotFound(format!(
                    "integration instance {instance_id} not found for this tenant"
                )));
            }
            type CheckpointRow = (
                chrono::DateTime<chrono::Utc>,
                Option<String>,
                Option<String>,
                chrono::DateTime<chrono::Utc>,
            );
            let row: Option<CheckpointRow> = sqlx::query_as(
                "SELECT watermark, watermark_id, last_run_id, last_run_at \
                 FROM integration_checkpoints \
                 WHERE tenant_id = $1 AND instance_id = $2",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Checkpoint read failed: {e}")))?;
            Ok(row.map(
                |(watermark, watermark_id, last_run_id, last_run_at)| CheckpointState {
                    watermark,
                    watermark_id,
                    last_run_id,
                    last_run_at,
                },
            ))
        })
    })
    .await
}
