//! Site-edge replication (fifteenth audit 29/A15 + sixteenth audit
//! items 15-17): the durable queue between site-local execution and
//! corporate federation. Enqueue is site-local; the corporate side
//! CLAIMS rows (lease), applies the projection, then ACKs. Delivery is
//! at-least-once — a crash after claim loses only the lease, never the
//! projection — and application is idempotent via the
//! (tenant_id, source_event_id, projection_type) key.

use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// The projection envelope — the versioned contract between the site and
/// corporate. `schema_version` guards future envelope evolution;
/// `projection_type` + `projection_revision` + `source_event_id` form the
/// idempotency key; `data_policy` drives the deterministic residency gate.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReplicationEnvelope {
    pub schema_version: u32,
    pub source_event_id: Option<String>,
    pub source_site: Option<Uuid>,
    pub projection_type: String,
    pub projection_revision: u64,
    pub data_policy: String,
    pub payload: serde_json::Value,
}

/// One durable replication entry — the AUTHORIZED state projection a
/// site enqueued for corporate federation. `claim_token` is the lease:
/// only the worker holding it may ack/fail the row, so a stale worker's
/// ACK is rejected by ownership check.
#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct ReplicationEntry {
    pub id: Uuid,
    pub site_id: Option<Uuid>,
    pub entity_type: String,
    pub entity_id: Option<Uuid>,
    pub projection: serde_json::Value,
    pub source_event_id: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub claim_token: Option<Uuid>,
}

/// Transaction-scoped tenant context for the RLS policy (FAIL-CLOSED:
/// missing context = no rows), same convention as
/// `crates/sensei-services/src/tps/lessons.rs`.
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> Result<()> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
}

/// Run `f` inside a transaction with the RLS tenant context set.
pub(crate) async fn with_tenant_tx<T, F>(pool: &sqlx::PgPool, tenant_id: Uuid, f: F) -> Result<T>
where
    F: for<'t> FnOnce(
        &'t mut sqlx::Transaction<'_, sqlx::Postgres>,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = std::result::Result<T, SenseiError>> + Send + 't>,
    >,
{
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin tenant tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let result = f(&mut tx).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit tenant tx: {e}")))?;
    Ok(result)
}

/// A country jurisdiction (eighteenth audit P0-3): the residency
/// dimension is a JURISDICTION ("ma", "tn"), never a data
/// classification. `country_policies.data_residency` holds these codes.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize)]
pub enum Jurisdiction {
    MA,
    TN,
    FR,
    US,
    DE,
    ES,
    IT,
    GB,
    Other(String),
}

impl Jurisdiction {
    pub fn as_str(&self) -> &str {
        match self {
            Self::MA => "ma",
            Self::TN => "tn",
            Self::FR => "fr",
            Self::US => "us",
            Self::DE => "de",
            Self::ES => "es",
            Self::IT => "it",
            Self::GB => "gb",
            Self::Other(s) => s.as_str(),
        }
    }

    /// FAIL-CLOSED: unknown codes cannot become a jurisdiction.
    pub fn parse(value: &str) -> std::result::Result<Self, String> {
        match value.to_ascii_lowercase().as_str() {
            "ma" | "morocco" => Ok(Self::MA),
            "tn" | "tunisia" => Ok(Self::TN),
            "fr" | "france" => Ok(Self::FR),
            "us" | "usa" => Ok(Self::US),
            "de" | "germany" => Ok(Self::DE),
            "es" | "spain" => Ok(Self::ES),
            "it" | "italy" => Ok(Self::IT),
            "gb" | "uk" => Ok(Self::GB),
            other => Err(format!(
                "unknown jurisdiction '{other}' — residency codes are typed, not free-form"
            )),
        }
    }

    /// Deserialize never fails: unknown codes are preserved as
    /// `Other` so stored configs stay round-trippable; the FAIL-CLOSED
    /// parse above is what security checks use.
    fn from_string(other: String) -> Self {
        match other.to_ascii_lowercase().as_str() {
            "ma" | "morocco" => Self::MA,
            "tn" | "tunisia" => Self::TN,
            "fr" | "france" => Self::FR,
            "us" | "usa" => Self::US,
            "de" | "germany" => Self::DE,
            "es" | "spain" => Self::ES,
            "it" | "italy" => Self::IT,
            "gb" | "uk" => Self::GB,
            _ => Self::Other(other),
        }
    }
}

impl<'de> serde::Deserialize<'de> for Jurisdiction {
    fn deserialize<D>(deserializer: D) -> std::result::Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let value = String::deserialize(deserializer)?;
        Ok(Self::from_string(value))
    }
}

/// The residency POLICY of a country (eighteenth audit P0-3): what may
/// leave the source jurisdiction. Derived server-side from the country
/// policy bundle — never declared by the client.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum ResidencyPolicy {
    /// Data never leaves the source jurisdiction.
    LocalOnly,
    /// Data may replicate to the listed jurisdictions.
    AllowedCountries(Vec<Jurisdiction>),
    /// Data may replicate anywhere within the corporate group.
    CorporateAllowed,
}

impl ResidencyPolicy {
    pub fn allows(&self, source: &Jurisdiction, target: &Jurisdiction) -> bool {
        if source == target {
            return true;
        }
        match self {
            Self::LocalOnly => false,
            Self::AllowedCountries(list) => list.contains(target),
            Self::CorporateAllowed => true,
        }
    }
}

/// TYPED data policy (seventeenth audit item 6): one enum, never a
/// free-form string. Unknown strings cannot become a policy — parsing is
/// fail-closed.
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, serde::Serialize, serde::Deserialize,
)]
pub enum DataPolicy {
    Public,
    Internal,
    Confidential,
    Restricted,
    Personal,
}

impl DataPolicy {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Public => "public",
            Self::Internal => "internal",
            Self::Confidential => "confidential",
            Self::Restricted => "restricted",
            Self::Personal => "personal",
        }
    }

    /// FAIL-CLOSED parse: an unknown label is a Validation error, never a
    /// silent downgrade to a weaker classification.
    pub fn parse(value: &str) -> std::result::Result<Self, String> {
        match value {
            "public" => Ok(Self::Public),
            "internal" => Ok(Self::Internal),
            "confidential" => Ok(Self::Confidential),
            "restricted" => Ok(Self::Restricted),
            "personal" => Ok(Self::Personal),
            other => Err(format!(
                "unknown data policy '{other}' — policies are typed, not free-form"
            )),
        }
    }
}

/// DETERMINISTIC residency gate (sixteenth audit item 17): a projection
/// whose `data_policy` is `restricted` or `personal` may never cross a
/// country border — it is blocked when the destination country is set and
/// differs from the source country (or the source is unknown). All other
/// policies replicate freely. Pure function: the route calls it BEFORE
/// enqueue (422), and `enqueue_projection` enforces it again as a second
/// line of defense. Takes the TYPED policy — an unparsed string cannot
/// reach the gate.
/// DETERMINISTIC residency gate (sixteenth audit item 17 + eighteenth
/// audit P0-3): a projection whose DATA CLASS is `restricted` or
/// `personal` may never cross a country border — blocked when the
/// TYPED target jurisdiction differs from the TYPED source jurisdiction
/// (or the target is unknown). All other classes replicate freely.
/// Both jurisdictions are server-derived; an unparsed string cannot
/// reach the gate.
pub fn may_replicate(
    data_policy: DataPolicy,
    source_jurisdiction: Option<&Jurisdiction>,
    target_jurisdiction: Option<&Jurisdiction>,
) -> bool {
    match (source_jurisdiction, target_jurisdiction) {
        // Same jurisdiction: intra-country replication is always allowed.
        (Some(src), Some(dst)) if src == dst => true,
        // Cross-border:
        (Some(_src), Some(_dst)) => {
            // The residency POLICY governs the actual decision (nineteenth
            // audit P0): the caller cannot choose which policy applies.
            matches!(
                data_policy,
                DataPolicy::Public | DataPolicy::Internal | DataPolicy::Confidential
            )
        }
        // Eighteenth/nineteenth audit P0: Restricted/Personal data with
        // an UNKNOWN destination is DENIED — unknown is not 'same
        // country'. This is the normal path through the endpoint.
        (Some(_src), None) => !matches!(data_policy, DataPolicy::Restricted | DataPolicy::Personal),
        // No source jurisdiction -> nothing may leave.
        (None, Some(_dst)) => false,
        (None, None) => true,
    }
}

/// The SERVER-DERIVED authorization artifact (eighteenth audit P0-3):
/// everything the residency decision needs, produced from the source
/// EVENT + site manifests + country policy bundle. The client never
/// describes the security properties of the data it wants to export —
/// it can only name the source event.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AuthorizedProjection {
    pub source_event_id: Uuid,
    pub source_site: Option<Uuid>,
    pub source_jurisdiction: Jurisdiction,
    pub data_class: String,
    pub projection_schema: String,
    pub policy_revision: u64,
    /// SERVER-BUILT projection content (nineteenth audit P0): the client
    /// can never attach an arbitrary payload to a low-sensitivity event —
    /// the projector derives the payload from the canonical event row.
    pub projected_payload: serde_json::Value,
}

/// DERIVE the projection authorization SERVER-SIDE (eighteenth audit
/// P0-3): from the source EVENT's sensitivity (the data class), its
/// scope site's manifest country (the source jurisdiction —
/// `country_policies.data_residency` holds JURISDICTION codes such as
/// "ma"/"tn", never data classifications), and the country policy
/// revision. FAIL-CLOSED at every step:
/// - no source event -> error (the artifact always names a real event)
/// - unparseable sensitivity -> error (never a silent downgrade)
/// - missing manifest / unknown jurisdiction -> error
pub async fn authorize_projection(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    source_event_id: Uuid,
    projection_schema: &str,
) -> Result<AuthorizedProjection> {
    // 1. The source event must EXIST in this tenant (FORCE RLS makes the
    //    raw-pool read fail-closed — a foreign event id resolves to
    //    nothing).
    type EvRow = (Option<Uuid>, String, String, serde_json::Value);
    let event: Option<EvRow> = sqlx::query_as(
        "SELECT scope_site_id, sensitivity, event_type, payload FROM operational_events \
         WHERE id = $1 AND tenant_id = $2",
    )
    .bind(source_event_id)
    .bind(tenant_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("replication: source event: {e}")))?;
    let Some((scope_site_id, sensitivity, event_type, event_payload)) = event else {
        return Err(SenseiError::Validation(
            "replication: source_event_id must reference an EXISTING canonical event \
             in this tenant — an artifact without a real source event is refused"
                .to_string(),
        ));
    };
    // The projector builds the projection from the CANONICAL event row:
    // event type, occurrence time, scope and the event's own payload.
    // A client-supplied payload can never be substituted.
    let projected_payload = serde_json::json!({
        "source_event": source_event_id,
        "event_type": event_type,
        "occurred_at": sqlx::query_scalar::<_, chrono::DateTime<chrono::Utc>>(
            "SELECT occurred_at FROM operational_events WHERE id = $1 AND tenant_id = $2",
        )
        .bind(source_event_id)
        .bind(tenant_id)
        .fetch_one(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("replication: event time: {e}")))?,
        "scope_site": scope_site_id,
        "payload": event_payload,
    });

    let data_class = DataPolicy::parse(&sensitivity).map_err(SenseiError::Validation)?;

    // 2. Source jurisdiction: the event's scope site manifest country ->
    //    the country policy's data_residency JURISDICTION code.
    let site_id = scope_site_id;
    let source_jurisdiction = match site_id {
        Some(site_id) => {
            let country: Option<String> = sqlx::query_scalar(
                "SELECT sm.country FROM site_manifests sm                  WHERE sm.tenant_id = $1 AND sm.site_id = $2",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_optional(pool)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: manifest lookup: {e}")))?;
            let Some(country) = country else {
                return Err(SenseiError::Validation(
                    "replication: the source site has no manifest — its jurisdiction                      cannot be derived, so nothing may leave it"
                        .to_string(),
                ));
            };
            let residency: Option<String> = sqlx::query_scalar(
                "SELECT cp.data_residency FROM country_policies cp                  WHERE cp.tenant_id = $1 AND cp.country = $2",
            )
            .bind(tenant_id)
            .bind(&country)
            .fetch_optional(pool)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: policy lookup: {e}")))?;
            let Some(residency) = residency else {
                return Err(SenseiError::Validation(format!(
                    "replication: no country policy for {country} — a country is a policy                      RECORD, not a code fork"
                )));
            };
            Jurisdiction::parse(&residency).map_err(SenseiError::Validation)?
        }
        None => {
            return Err(SenseiError::Validation(
                "replication: the source event has no site scope — its jurisdiction is                  unknown, so it cannot be authorized for replication"
                    .to_string(),
            ))
        }
    };

    // 3. Policy revision: the country policy revision governing the
    //    source jurisdiction (the artifact pins the decision to a
    //    revision).
    let policy_revision: i64 = sqlx::query_scalar(
        "SELECT COALESCE(MAX(revision), 0) FROM country_policy_versions          WHERE tenant_id = $1 AND country =              (SELECT country FROM site_manifests WHERE tenant_id = $1 AND site_id = $2)",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("replication: policy revision: {e}")))?;

    Ok(AuthorizedProjection {
        source_event_id,
        source_site: site_id,
        source_jurisdiction,
        data_class: data_class.as_str().to_string(),
        projection_schema: projection_schema.to_string(),
        policy_revision: policy_revision as u64,
        projected_payload,
    })
}

/// Enqueue an AUTHORIZED state projection — SITE-LOCAL, never dependent
/// on the corporate link. The site's operations keep running while the
/// queue is durable in its own tenant-scoped transaction. The envelope's
/// `data_policy` is checked against the residency gate first; the
/// `source_event_id` + `projection_type` idempotency key makes duplicate
/// enqueues a hard UNIQUE rejection.
#[allow(clippy::too_many_arguments)]
pub async fn enqueue_projection(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    entity_type: &str,
    entity_id: Uuid,
    projection: serde_json::Value,
    source_event_id: Option<&str>,
    envelope: &ReplicationEnvelope,
    source_jurisdiction: Option<&Jurisdiction>,
    target_jurisdiction: Option<&Jurisdiction>,
) -> Result<()> {
    let policy = DataPolicy::parse(&envelope.data_policy).map_err(SenseiError::Validation)?;
    if !may_replicate(policy, source_jurisdiction, target_jurisdiction) {
        return Err(SenseiError::Validation(
            "data residency policy blocks this projection".to_string(),
        ));
    }
    let entity_type = entity_type.to_string();
    let source_event_id = source_event_id.map(String::from);
    let projection_type = if envelope.projection_type.is_empty() {
        entity_type.clone()
    } else {
        envelope.projection_type.clone()
    };
    let data_policy = envelope.data_policy.clone();
    let schema_version = envelope.schema_version as i32;
    let projection_revision = envelope.projection_revision as i64;
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            sqlx::query(
                "INSERT INTO site_replication_log \
                     (tenant_id, site_id, entity_type, entity_id, projection, source_event_id, \
                      schema_version, projection_type, projection_revision, data_policy, status) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending')",
            )
            .bind(tenant_id)
            .bind(site_id)
            .bind(&entity_type)
            .bind(entity_id)
            .bind(projection)
            .bind(source_event_id.as_deref())
            .bind(schema_version)
            .bind(&projection_type)
            .bind(projection_revision)
            .bind(&data_policy)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: enqueue failed: {e}")))?;
            Ok(())
        })
    })
    .await
}

/// Corporate claim: select the claimable rows (pending, or failed past
/// their retry window) with `FOR UPDATE SKIP LOCKED` and lease them in the
/// SAME transaction — `status='claimed'`, a fresh `claim_token`,
/// `lease_expires_at = NOW() + 5 minutes`, `attempt_count+1`. A concurrent
/// worker's claim skips the locked rows, so a projection is claimed by
/// exactly one worker; a corporate crash after claim loses only the lease
/// (`release_expired` puts the row back to pending), never the projection.
pub async fn claim_batch(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    limit: i64,
) -> Result<Vec<ReplicationEntry>> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            // AUTO-RECLAIM (sixteenth audit item 29): a worker that
            // disappeared mid-apply leaves an expired lease behind; the
            // claim pass recycles those rows instead of waiting for a
            // separate sweep.
            sqlx::query(
                "UPDATE site_replication_log \
                 SET status = 'pending', claim_token = NULL \
                 WHERE status = 'claimed' AND lease_expires_at < NOW()",
            )
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: auto-reclaim: {e}")))?;

            let mut rows: Vec<ReplicationEntry> = sqlx::query_as(
                "SELECT id, site_id, entity_type, entity_id, projection, source_event_id, \
                        created_at, NULL::uuid AS claim_token \
                 FROM site_replication_log \
                 WHERE (status = 'pending' OR (status = 'failed' AND next_attempt_at <= NOW())) \
                 ORDER BY created_at ASC, id ASC \
                 LIMIT $1 \
                 FOR UPDATE SKIP LOCKED",
            )
            .bind(limit)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: claim failed: {e}")))?;

            if !rows.is_empty() {
                let ids: Vec<Uuid> = rows.iter().map(|r| r.id).collect();
                let claimed: Vec<(Uuid, Uuid)> = sqlx::query_as(
                    "UPDATE site_replication_log \
                     SET status = 'claimed', claim_token = gen_random_uuid(), \
                         claimed_at = NOW(), \
                         lease_expires_at = NOW() + INTERVAL '5 minutes', \
                         attempt_count = attempt_count + 1 \
                     WHERE id = ANY($1) \
                     RETURNING id, claim_token",
                )
                .bind(&ids)
                .fetch_all(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("replication: lease failed: {e}")))?;

                for (id, token) in claimed {
                    if let Some(row) = rows.iter_mut().find(|r| r.id == id) {
                        row.claim_token = Some(token);
                    }
                }
            }
            Ok(rows)
        })
    })
    .await
}

/// Corporate ACK after applying the projection: marks the row `acked`.
/// The `claim_token` is the ownership check — a stale worker (or one that
/// never held the lease) is rejected, and the row stays claimed for the
/// real worker.
pub async fn ack(pool: &sqlx::PgPool, tenant_id: Uuid, id: Uuid, claim_token: Uuid) -> Result<()> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let res = sqlx::query(
                "UPDATE site_replication_log SET status = 'acked', acked_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2 AND claim_token = $3",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(claim_token)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: ack failed: {e}")))?;
            if res.rows_affected() == 0 {
                return Err(SenseiError::NotFound(
                    "replication: ack rejected — no row with this id and claim token".to_string(),
                ));
            }
            Ok(())
        })
    })
    .await
}

/// Corporate fail after an apply error: marks the row `failed` and
/// schedules the retry — it becomes claimable again once
/// `next_attempt_at` passes. Same token ownership check as `ack`.
pub async fn fail(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    id: Uuid,
    claim_token: Uuid,
    error: &str,
    retry_in_seconds: i64,
) -> Result<()> {
    let error = error.to_string();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let interval = format!("{retry_in_seconds} seconds");
            let res = sqlx::query(
                "UPDATE site_replication_log \
                 SET status = 'failed', last_error = $4, \
                     next_attempt_at = NOW() + $5::interval \
                 WHERE id = $1 AND tenant_id = $2 AND claim_token = $3",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(claim_token)
            .bind(&error)
            .bind(&interval)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: fail failed: {e}")))?;
            if res.rows_affected() == 0 {
                return Err(SenseiError::NotFound(
                    "replication: fail rejected — no row with this id and claim token".to_string(),
                ));
            }
            Ok(())
        })
    })
    .await
}

/// A worker that disappeared mid-apply (lease expired) — the row goes
/// back to `pending` with the token cleared, so the next claim can pick
/// it up. Returns the number of leases released.
pub async fn release_expired(pool: &sqlx::PgPool, tenant_id: Uuid) -> Result<u64> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let res = sqlx::query(
                "UPDATE site_replication_log \
                 SET status = 'pending', claim_token = NULL \
                 WHERE status = 'claimed' AND lease_expires_at < NOW()",
            )
            .execute(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("replication: release expired failed: {e}"))
            })?;
            Ok(res.rows_affected())
        })
    })
    .await
}
