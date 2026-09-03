//! Integration INSTANCE lifecycle + checkpoint producer (twenty-second
//! audit P1 + twenty-third audit P1 closure): the integration instance is
//! the unit of readiness — the bridge advances ONE instance
//! (instance_id), never a tenant-global (source_system, source_table)
//! cursor, so one healthy SAP checkpoint can never certify another site's
//! SAP.
//!
//! - `reconcile_instances` is the PRODUCER: it reads the site manifest's
//!   declared integration kinds and materializes one
//!   `integration_instances` row per declared kind FOR THIS SITE
//!   (fail-closed RLS like every tenant-owned table). Twenty-third audit
//!   P1: reconciliation is a CLOSURE, not an additive upsert — a kind
//!   REMOVED from the manifest is DISABLED (decommissioned:
//!   enabled = FALSE, required = FALSE; it never blocks readiness and can
//!   never be advanced), and every declared kind is re-asserted as
//!   enabled = TRUE, required = TRUE at the CURRENT
//!   `configuration_revision` (= manifest_version). The run reports
//!   (created, enabled, disabled) counts.
//! - `reconcile_instances_tx` is the pub(crate) hook bootstrap/manifest
//!   writes invoke IN THE SAME tenant transaction (twenty-third audit
//!   P1): instance state never lags the manifest.
//! - `write_checkpoint` advances ONE instance's durable watermark
//!   (instance_id): the instance must be visible under the caller's
//!   tenant (unknown → NotFound = 404) and must be ENABLED (disabled →
//!   Conflict = 409 — a decommissioned instance can never be advanced).
//!   Twenty-sixth audit P0.2 (one-shot, token-authenticated completion):
//!   completion is server-attested END TO END — the caller presents the
//!   run_token that `start_run` issued, and the attestation step is an
//!   ATOMIC ONE-SHOT CONSUME:
//!
//!   ```sql
//!   UPDATE integration_runs
//!      SET completed_at = NOW(), result = 'succeeded'
//!    WHERE tenant_id = $1 AND instance_id = $2 AND run_id = $3
//!      AND run_token = $4 AND completed_at IS NULL
//!    RETURNING configuration_revision, configuration_digest
//!   ```
//!
//!   0 rows → Conflict (the run is absent, already consumed, or the token
//!   does not match) — the SAME run can NEVER complete twice, so a replay
//!   of an old completion can never refresh last_run_at /
//!   last_verified_revision into manufactured fresh readiness. The
//!   completion write records NO client-claimed revision:
//!   - the instance's verification stamp (`last_verified_revision`, the
//!     guarded conditional update) uses the CONSUMED run's RETURNED
//!     configuration_revision and only succeeds while the instance's
//!     CURRENT configuration_revision still equals it AND the instance is
//!     still enabled — a run started at revision 1 that completes after
//!     the manifest moved the instance to revision 2 is refused
//!     (Conflict = 409) and the whole write (consume included) rolls
//!     back, so an untested revision is never stamped;
//!   - the checkpoint row records the digest-derived attested
//!     verified_revision, so the durable cursor names exactly what the
//!     server attested at run start.
//! - `get_checkpoint` reads that instance's watermark: `None` means the
//!   instance NEVER RAN (NeverRun/Unknown) — never a fabricated
//!   `Utc::now()`. `get_site_checkpoint` resolves the instance by
//!   (tenant, site, integration_type) for the instance-keyed legacy read.
//! - `read_integration_state` reads the tenant's integration-layer
//!   counters (dead letters, open reconciliations, tombstones, latest
//!   checkpoint) inside ONE tenant-scoped transaction — under a missing
//!   RLS context the raw pool fabricates zeros; the tenant tx returns the
//!   correct values.

use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

use super::replication::with_tenant_tx;

/// The durable cursor of ONE integration instance (NeverRun when absent).
#[derive(Debug, Clone, serde::Serialize)]
pub struct CheckpointState {
    pub watermark: chrono::DateTime<chrono::Utc>,
    pub watermark_id: Option<String>,
    pub last_run_id: Option<String>,
    pub last_run_at: chrono::DateTime<chrono::Utc>,
}

/// The outcome of ONE reconcile run (twenty-third audit P1):
/// - `created`: rows materialized in THIS run for kinds that had no
///   instance row yet;
/// - `enabled`: declared-kind rows enabled + required + current
///   (`configuration_revision` = the manifest version) afterwards;
/// - `disabled`: rows decommissioned in THIS run because their kind is no
///   longer declared by the manifest (an already-decommissioned row is
///   not counted again).
#[derive(Debug, Clone, serde::Serialize)]
pub struct ReconcileCounts {
    pub created: i64,
    pub enabled: i64,
    pub disabled: i64,
}

/// The manifest's distinct declared kinds (empty string / missing `kind`
/// entries are not provisionable and never count).
fn declared_kinds(integrations: &serde_json::Value) -> Vec<String> {
    let mut seen = std::collections::HashSet::new();
    let mut kinds = Vec::new();
    if let Some(items) = integrations.as_array() {
        for v in items {
            if let Some(kind) = v.get("kind").and_then(|k| k.as_str()) {
                if !kind.is_empty() && seen.insert(kind.to_string()) {
                    kinds.push(kind.to_string());
                }
            }
        }
    }
    kinds
}

/// Reconcile the integration instances of one site against its CURRENT
/// manifest — the transaction-scoped form (`reconcile_instances` wraps it
/// in a tenant tx; the site bootstrap / manifest-update hooks call it IN
/// the same transaction as the manifest write, so instance state never
/// lags the manifest):
///
/// (a) every DECLARED kind is upserted as enabled = TRUE, required = TRUE
///     with `configuration_revision` = the manifest's current version
///     (re-asserting lifecycle state on re-declared kinds);
/// (b) every instance row whose kind is NO LONGER declared is
///     DECOMMISSIONED — enabled = FALSE, required = FALSE (it can never
///     be advanced by the bridge and never blocks readiness);
/// (c) returns (created, enabled, disabled) counts for the run.
///
/// - A site with NO manifest row is an error (bootstrap first).
/// - A manifest whose `integrations` is NULL has no integration policy —
///   nothing can be provisioned from it (fail closed).
/// - An EXPLICIT empty `[]` policy decommissions every instance (the site
///   no longer requires any integration) and returns enabled = 0.
pub(crate) async fn reconcile_instances_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    site_id: Uuid,
) -> Result<ReconcileCounts> {
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
    let integrations = integrations.ok_or_else(|| {
        SenseiError::Validation(
            "integration policy not configured — the site manifest's \
             integrations column is NULL; declare an explicit [] policy \
             or provision declared kinds"
                .to_string(),
        )
    })?;
    if !integrations.is_array() {
        return Err(SenseiError::Validation(
            "integration policy is malformed — site_manifests.integrations \
             must be a JSON array of {kind} objects"
                .to_string(),
        ));
    }
    let kinds = declared_kinds(&integrations);
    let declared_sql = r#"(SELECT elem->>'kind'
                            FROM jsonb_array_elements($3::jsonb) AS elem
                            WHERE elem->>'kind' IS NOT NULL AND elem->>'kind' <> '')"#;

    // Rows that already exist for DECLARED kinds — these are refreshed by
    // the upsert, never counted as created.
    let existing: i64 = sqlx::query_scalar(&format!(
        "SELECT COUNT(*) FROM integration_instances \
             WHERE tenant_id = $1 AND site_id = $2 \
               AND integration_type IN {declared_sql}"
    ))
    .bind(tenant_id)
    .bind(site_id)
    .bind(&integrations)
    .fetch_one(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Instance count failed: {e}")))?;

    // (a) Upsert every declared kind: enabled + required re-asserted and
    // the configuration revision follows the manifest version it was
    // reconciled from.
    sqlx::query(
        "INSERT INTO integration_instances \
             (tenant_id, site_id, integration_type, endpoint, \
              configuration_revision, enabled, required) \
         SELECT $1, $2, elem->>'kind', NULL, $3, TRUE, TRUE \
         FROM jsonb_array_elements($4::jsonb) AS elem \
         WHERE elem->>'kind' IS NOT NULL AND elem->>'kind' <> '' \
         ON CONFLICT (tenant_id, site_id, integration_type) \
         DO UPDATE SET \
             configuration_revision = EXCLUDED.configuration_revision, \
             enabled = TRUE, \
             required = TRUE",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(manifest_version)
    .bind(&integrations)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Integration instance reconcile failed: {e}")))?;

    // Enabled rows whose kind is NOT declared: decommissioned BY THIS RUN.
    let to_disable: i64 = sqlx::query_scalar(&format!(
        "SELECT COUNT(*) FROM integration_instances \
             WHERE tenant_id = $1 AND site_id = $2 AND enabled = TRUE \
               AND NOT (integration_type IN {declared_sql})"
    ))
    .bind(tenant_id)
    .bind(site_id)
    .bind(&integrations)
    .fetch_one(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Instance count failed: {e}")))?;

    // (b) Decommission removed kinds — never blocks readiness, never
    // advanceable.
    sqlx::query(&format!(
        "UPDATE integration_instances \
                SET enabled = FALSE, required = FALSE \
              WHERE tenant_id = $1 AND site_id = $2 \
                AND NOT (integration_type IN {declared_sql})"
    ))
    .bind(tenant_id)
    .bind(site_id)
    .bind(&integrations)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Integration instance decommission failed: {e}")))?;

    // (c) The enabled population afterwards: declared kinds only (the
    // disable above removed every other row from the enabled set).
    let enabled: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM integration_instances \
         WHERE tenant_id = $1 AND site_id = $2 AND enabled = TRUE AND required = TRUE",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_one(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Instance count failed: {e}")))?;

    let created = (kinds.len() as i64 - existing).max(0);
    Ok(ReconcileCounts {
        created,
        enabled,
        disabled: to_disable,
    })
}

/// Reconcile the integration instances of one site against its CURRENT
/// manifest, inside ONE tenant-scoped transaction. See
/// [`reconcile_instances_tx`] for the semantics; returns the
/// (created, enabled, disabled) counts of the run.
pub async fn reconcile_instances(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Uuid,
) -> Result<ReconcileCounts> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move { reconcile_instances_tx(tx, tenant_id, site_id).await })
    })
    .await
}

/// Start a server-attested integration run (twenty-fifth audit P1): the
/// server issues the run_token bound to the instance's CURRENT
/// configuration revision + a digest of it (`'attested:' || revision`).
/// The bridge cannot declare which configuration it tested; the returned
/// token is the ONLY credential that may complete the run (twenty-sixth
/// audit P0.2), and completion consumes the run exactly once.
pub async fn start_run(
    pool: &PgPool,
    tenant_id: Uuid,
    instance_id: Uuid,
    run_id: String,
) -> Result<uuid::Uuid> {
    let token = uuid::Uuid::new_v4();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let revision: Option<i32> = sqlx::query_scalar(
                "SELECT configuration_revision FROM integration_instances \
                 WHERE tenant_id = $1 AND id = $2 AND enabled = TRUE",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Run start read failed: {e}")))?;
            let Some(revision) = revision else {
                return Err(SenseiError::Conflict(format!(
                    "integration instance {instance_id} is not enabled — no run may start"
                )));
            };
            // Twenty-seventh audit P1: the digest is a REAL SHA-256 over
            // the NORMALIZED configuration the instance points at, and the
            // run carries a server-side expiry.
            let config_type: String = sqlx::query_scalar(
                "SELECT integration_type FROM integration_instances \
                 WHERE tenant_id = $1 AND id = $2",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Run start config read failed: {e}")))?;
            let config_endpoint: Option<String> = sqlx::query_scalar(
                "SELECT endpoint FROM integration_instances \
                 WHERE tenant_id = $1 AND id = $2",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Run start endpoint read failed: {e}")))?;
            let normalized = serde_json::json!({
                "integration_type": config_type,
                "endpoint": config_endpoint,
                "configuration_revision": revision,
            });
            use sha2::{Digest, Sha256};
            let mut hasher = Sha256::new();
            hasher.update(
                serde_json::to_string(&normalized)
                    .unwrap_or_default()
                    .as_bytes(),
            );
            let digest = format!("sha256:{:x}", hasher.finalize());
            sqlx::query(
                "INSERT INTO integration_runs \
                     (tenant_id, instance_id, run_token, configuration_revision, \
                      configuration_digest, configuration, run_id, expires_at) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, NOW() + INTERVAL '15 minutes')",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .bind(token)
            .bind(revision as i64)
            .bind(&digest)
            .bind(&normalized)
            .bind(&run_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Run start failed: {e}")))?;
            Ok(token)
        })
    })
    .await
}

/// The configuration revision a consumed run's digest attests
/// (twenty-sixth audit P0.2). `start_run` mints the digest as
/// `'attested:' || configuration_revision`, so parsing the RUN's RETURNED
/// digest yields the revision the server bound the run_token to — the
/// checkpoint row's verified_revision always names the SERVER-ATTESTED
/// configuration, never a client claim. A digest shape that does not
/// encode a revision falls back to the run row's own returned
/// `configuration_revision`: both values are server-written in the same
/// `start_run` statement, so the fallback is equally server-attested.
fn attested_revision_from_digest(_digest: &str, fallback: i64) -> i64 {
    // The digest is now a real SHA-256 over the normalized configuration;
    // the run row's RETURNED configuration_revision is authoritative.
    fallback
}

/// Advance ONE integration instance's checkpoint (the bridge's durable
/// cursor) — the COMPLETION side of a server-attested run
/// (twenty-sixth audit P0.2). The instance row is resolved against the
/// caller's tenant — an instance that is not visible under that tenant is
/// unknown (NotFound), and a DISABLED (decommissioned) instance refuses
/// advancement (Conflict). `source_system`/`source_table` are OPTIONAL
/// legacy metadata: the readiness proof is `instance_id`, so a write
/// never needs them.
///
/// The completion is AUTHENTICATED by the run_token that `start_run`
/// issued, and the attestation is an ATOMIC ONE-SHOT CONSUME — the run
/// row is closed (`completed_at = NOW()`, `result = 'succeeded'`) and its
/// attested state RETURNED in the SAME statement:
///
/// ```sql
/// UPDATE integration_runs
///    SET completed_at = NOW(), result = 'succeeded'
///  WHERE tenant_id = $1 AND instance_id = $2 AND run_id = $3
///    AND run_token = $4 AND completed_at IS NULL
///  RETURNING configuration_revision, configuration_digest
/// ```
///
/// 0 rows → Conflict ("run is absent, already consumed, or the token does
/// not match") — a run that already completed can never complete again,
/// so replaying an OLD completion can never refresh
/// last_run_at / last_verified_revision into fresh readiness.
///
/// NO revision is taken from the caller. The write records the CONSUMED
/// run's server-attested state only:
/// - the verification stamp is a GUARDED conditional update on the
///   instance, conditioned on the RETURNED configuration_revision:
///
///   ```sql
///   UPDATE integration_instances
///      SET last_verified_revision = $rev
///    WHERE id = $instance AND configuration_revision = $rev AND enabled = TRUE
///   ```
///
///   A 0-row update means the instance moved (its configuration revision
///   advanced past the attested revision, or it was decommissioned)
///   between start_run and this completion — the run certified an OLDER
///   configuration, so the write is refused (Conflict = 409, "stale
///   integration run") and the WHOLE transaction rolls back (the consume
///   included — the run stays open, but can never stamp a revision it
///   did not test).
/// - the checkpoint row records the digest-derived attested revision
///   (`integration_checkpoints.verified_revision`, migration 161), so the
///   durable cursor itself names what the run verified. The instance's
///   `last_verified_revision` stamp is likewise the attested revision —
///   when a manifest change advances the instance's
///   configuration_revision, the old checkpoint stops certifying until a
///   fresh run stamps the new revision.
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
    run_token: uuid::Uuid,
) -> Result<()> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            // Instance visibility + lifecycle gate: unknown → NotFound,
            // decommissioned → Conflict. Checked BEFORE the run consume so
            // the refusal names the instance state, not the run.
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
            // Twenty-sixth audit P0.2: the attestation is an ATOMIC
            // ONE-SHOT CONSUME — the open run bound to (run_id, run_token)
            // is CLOSED and its server-attested state RETURNED in the same
            // UPDATE. 0 rows = the run is absent, already consumed, or the
            // token does not match: a second completion of the same run can
            // never succeed, so an old completed run can never refresh
            // last_run_at / last_verified_revision into fresh readiness.
            // Expire abandoned runs first: an open run past its server
            // maximum age can never complete (twenty-seventh audit P1).
            sqlx::query(
                "UPDATE integration_runs SET completed_at = NOW(), result = 'expired' \
                 WHERE tenant_id = $1 AND instance_id = $2 \
                   AND completed_at IS NULL AND expires_at IS NOT NULL \
                   AND expires_at <= NOW()",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Run expiry failed: {e}")))?;
            let attested: Option<(i64, String)> = sqlx::query_as(
                "UPDATE integration_runs \
                    SET completed_at = NOW(), result = 'succeeded' \
                  WHERE tenant_id = $1 AND instance_id = $2 AND run_id = $3 \
                    AND run_token = $4 AND completed_at IS NULL \
                    AND (expires_at IS NULL OR expires_at > NOW()) \
                  RETURNING configuration_revision, configuration_digest",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .bind(&run_id)
            .bind(run_token)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Run attestation consume failed: {e}")))?;
            let Some((attested_revision, digest)) = attested else {
                return Err(SenseiError::Conflict(
                    "run is absent, already consumed, or the token does not match — \
                     start_run must precede completion, and each run completes exactly once"
                        .to_string(),
                ));
            };
            // The revision this completion certifies is the run's OWN
            // server-attested state (RETURNED above): the digest-derived
            // attested revision — never a client claim.
            let verified_revision = attested_revision_from_digest(&digest, attested_revision);

            // The verification stamp is CONDITIONAL on the instance still
            // being ENABLED and still carrying the ATTESTED revision — a
            // run started against an old configuration can never stamp a
            // revision it did not test (0 rows updated = the instance
            // moved; the whole write rolls back, consume and checkpoint
            // included).
            let stamped = sqlx::query(
                "UPDATE integration_instances \
                    SET last_verified_revision = $3::int \
                  WHERE tenant_id = $1 AND id = $2 \
                    AND configuration_revision = $3 \
                    AND enabled = TRUE",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .bind(attested_revision)
            .execute(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Instance verification stamp failed: {e}"))
            })?;
            if stamped.rows_affected() == 0 {
                // The instance moved after the consume (a concurrent
                // manifest reconcile or decommission). Classify the
                // current state so the refusal names what actually
                // happened.
                let now: Option<(bool, i32)> = sqlx::query_as(
                    "SELECT enabled, configuration_revision FROM integration_instances \
                     WHERE tenant_id = $1 AND id = $2",
                )
                .bind(tenant_id)
                .bind(instance_id)
                .fetch_optional(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Integration instance lookup failed: {e}"))
                })?;
                match now {
                    None => {
                        return Err(SenseiError::NotFound(format!(
                            "integration instance {instance_id} not found for this tenant"
                        )))
                    }
                    Some((false, _)) => {
                        return Err(SenseiError::Conflict(format!(
                            "integration instance {instance_id} is disabled — a decommissioned \
                             instance cannot be advanced"
                        )))
                    }
                    Some((true, current_revision)) => {
                        return Err(SenseiError::Conflict(format!(
                            "stale integration run: instance moved to a newer configuration \
                             revision (instance {instance_id} is at revision \
                             {current_revision}, the run attested revision \
                             {attested_revision})"
                        )))
                    }
                }
            }
            sqlx::query(
                "INSERT INTO integration_checkpoints \
                     (tenant_id, instance_id, source_system, source_table, \
                      watermark, watermark_id, last_run_id, last_run_at, \
                      verified_revision) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8) \
                 ON CONFLICT (tenant_id, instance_id) DO UPDATE SET \
                     source_system = COALESCE(EXCLUDED.source_system, \
                                              integration_checkpoints.source_system), \
                     source_table = COALESCE(EXCLUDED.source_table, \
                                             integration_checkpoints.source_table), \
                     watermark = EXCLUDED.watermark, \
                     watermark_id = EXCLUDED.watermark_id, \
                     last_run_id = EXCLUDED.last_run_id, \
                     last_run_at = NOW(), \
                     verified_revision = EXCLUDED.verified_revision",
            )
            .bind(tenant_id)
            .bind(instance_id)
            .bind(&source_system)
            .bind(&source_table)
            .bind(watermark)
            .bind(&watermark_id)
            .bind(&run_id)
            .bind(verified_revision)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Checkpoint write failed: {e}")))?;
            Ok(())
        })
    })
    .await
}

/// Read ONE instance's checkpoint row inside an open tenant transaction.
/// `Ok(None)` is NEVER RUN — the caller decides what an absent instance
/// means (NotFound) vs an absent checkpoint (NeverRun).
async fn read_instance_checkpoint(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    instance_id: Uuid,
) -> Result<Option<CheckpointState>> {
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
            read_instance_checkpoint(tx, tenant_id, instance_id).await
        })
    })
    .await
}

/// Resolve ONE site's instance of an integration kind and return ITS
/// checkpoint (twenty-third audit P1 — the legacy
/// checkpoint/{system}/{source_table} read is routed through the
/// instance): the instance is (tenant, site, integration_type), so the
/// returned cursor is instance-keyed and site-scoped. A site with no
/// instance of the kind, or an instance that never ran, is `Ok(None)`
/// (NeverRun) — never a fabricated `Utc::now()`.
pub async fn get_site_checkpoint(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Uuid,
    integration_type: &str,
) -> Result<Option<CheckpointState>> {
    let integration_type = integration_type.to_string();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let instance_id: Option<Uuid> = sqlx::query_scalar(
                "SELECT id FROM integration_instances \
                 WHERE tenant_id = $1 AND site_id = $2 AND integration_type = $3",
            )
            .bind(tenant_id)
            .bind(site_id)
            .bind(&integration_type)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Integration instance lookup failed: {e}"))
            })?;
            let Some(instance_id) = instance_id else {
                return Ok(None);
            };
            read_instance_checkpoint(tx, tenant_id, instance_id).await
        })
    })
    .await
}

/// The tenant's integration-layer state snapshot — every counter read
/// inside ONE tenant-scoped transaction (twenty-third audit P1):
/// integration tables are FORCE RLS, so reads on the raw pool under a
/// wrong/missing tenant context fabricate zeros; the tenant tx returns
/// the CORRECT values (and one error budget: any query failure
/// propagates, never a fake zero).
#[derive(Debug, Clone)]
pub struct IntegrationState {
    pub entity_map_count: i64,
    pub dead_letter_count: i64,
    pub reconciliation_open: i64,
    /// (watermark, last_run_id, last_run_at) of the tenant's most recent
    /// checkpoint, if any.
    pub last_checkpoint: Option<(
        chrono::DateTime<chrono::Utc>,
        Option<String>,
        chrono::DateTime<chrono::Utc>,
    )>,
    pub tombstone_count: i64,
    pub oldest_unresolved: Option<chrono::DateTime<chrono::Utc>>,
}

/// Read the integration-layer state snapshot of one tenant inside ONE
/// tenant-scoped transaction. See [`IntegrationState`].
pub async fn read_integration_state(pool: &PgPool, tenant_id: Uuid) -> Result<IntegrationState> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let (map_count,): (i64,) =
                sqlx::query_as("SELECT COUNT(*) FROM integration_entity_map WHERE tenant_id = $1")
                    .bind(tenant_id)
                    .fetch_one(&mut **tx)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Entity map count failed: {e}")))?;
            let (dead_count,): (i64,) =
                sqlx::query_as("SELECT COUNT(*) FROM integration_dead_letter WHERE tenant_id = $1")
                    .bind(tenant_id)
                    .fetch_one(&mut **tx)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Dead letter count failed: {e}")))?;
            let (open_rec,): (i64,) = sqlx::query_as(
                "SELECT COUNT(*) FROM integration_reconciliation \
                 WHERE tenant_id = $1 AND status = 'open'",
            )
            .bind(tenant_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Reconciliation count failed: {e}")))?;
            // Source watermarks + run id: Unknown is NOT zero — each is
            // Option (None = nothing recorded yet).
            let last_checkpoint: Option<(
                chrono::DateTime<chrono::Utc>,
                Option<String>,
                chrono::DateTime<chrono::Utc>,
            )> = sqlx::query_as(
                "SELECT watermark, last_run_id, last_run_at \
                 FROM integration_checkpoints \
                 WHERE tenant_id = $1 ORDER BY last_run_at DESC LIMIT 1",
            )
            .bind(tenant_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Checkpoint read failed: {e}")))?;
            let (tombstones,): (i64,) = sqlx::query_as(
                "SELECT COUNT(*) FROM integration_entity_map \
                 WHERE tenant_id = $1 AND tombstoned = TRUE",
            )
            .bind(tenant_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Tombstone count failed: {e}")))?;
            let oldest_unresolved: Option<chrono::DateTime<chrono::Utc>> = sqlx::query_scalar(
                "SELECT MIN(created_at) FROM integration_reconciliation \
                 WHERE tenant_id = $1 AND status = 'open'",
            )
            .bind(tenant_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Oldest unresolved read failed: {e}")))?;
            Ok(IntegrationState {
                entity_map_count: map_count,
                dead_letter_count: dead_count,
                reconciliation_open: open_rec,
                last_checkpoint,
                tombstone_count: tombstones,
                oldest_unresolved,
            })
        })
    })
    .await
}
