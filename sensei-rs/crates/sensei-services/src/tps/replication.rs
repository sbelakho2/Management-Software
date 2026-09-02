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

/// The FANOUT outcome (twenty-third audit P1): one publish of one source
/// event across ALL its federation edges, counted by what the single
/// transaction actually did.
///
/// - `newly_enqueued`: queue rows INSERTed by this call (edges whose
///   (tenant, source_event_id, target_tenant, target_site) key was free).
/// - `already_present`: edges whose row already existed — the
///   `ON CONFLICT ... DO NOTHING` skip. A retry of a fully-published
///   event reports `newly_enqueued = 0` and `already_present = N`, so
///   repeated publishes CONVERGE to the same complete set instead of
///   500-ing on the first duplicate.
/// - `blocked`: edges the residency/class gate denied (the projection
///   may not cross that edge). Blocked edges are counted separately —
///   they are not enqueue failures, and the count lets the route decide
///   whether a restricted/personal projection was refused outright.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct FanoutReport {
    pub newly_enqueued: i64,
    pub already_present: i64,
    pub blocked: i64,
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

    /// The EDGE-LEVEL export gate (twentieth audit P0): the residency
    /// policy of the membership row decides whether data may move between
    /// two KNOWN jurisdictions, with the data-CLASS rule layered on top —
    /// Restricted/Personal never cross a country border even when the
    /// edge's policy is CorporateAllowed (sixteenth audit item 17 rule,
    /// unchanged). Same-jurisdiction movement never leaves the country,
    /// so every policy allows it. Cross-border:
    /// - LocalOnly => false for ANY data class (twentieth audit P0:
    ///   LocalOnly must stop Public/Internal/Confidential export too);
    /// - AllowedCountries => the target must be on the membership's list;
    /// - CorporateAllowed => anywhere within the corporate group.
    pub fn allows_export(
        &self,
        data_class: DataPolicy,
        source: &Jurisdiction,
        target: &Jurisdiction,
    ) -> bool {
        if source == target {
            return true;
        }
        if matches!(data_class, DataPolicy::Restricted | DataPolicy::Personal) {
            return false;
        }
        self.allows(source, target)
    }

    /// The migration-148 CHECK label of this policy ('local_only',
    /// 'allowed_countries', 'corporate_allowed').
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::LocalOnly => "local_only",
            Self::AllowedCountries(_) => "allowed_countries",
            Self::CorporateAllowed => "corporate_allowed",
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

/// DETERMINISTIC residency gate (sixteenth audit item 17 + eighteenth
/// audit P0-3 + nineteenth audit P0 + twentieth audit P0): decides
/// whether one projection of `data_policy` may move from
/// `source_jurisdiction` to `target_jurisdiction` UNDER THE RESIDENCY
/// POLICY OF THE FEDERATION EDGE that would carry it. The caller can
/// never choose which policy applies — the membership row owns the edge,
/// and `may_replicate` only evaluates what the edge grants. The route
/// evaluates the gate ONCE PER EDGE against that edge's policy; a
/// LocalOnly edge now stops Public/Internal/Confidential export too
/// (twentieth audit P0-2). FAIL-CLOSED at every unknown:
///
/// - `(None, None) => false` — the old `(None, None) => true` let an
///   unrestricted projection be queued with NO derivable destination.
/// - `(None, Some) => false` — no source jurisdiction, nothing leaves.
/// - `(Some, None)` — only CorporateAllowed may export an unrestricted
///   class toward an UNKNOWN destination (the legacy nineteenth-audit
///   semantics, pinned by the adversarial gate; the production route
///   never reaches this branch — every edge carries a derived target
///   jurisdiction).
/// - Restricted/Personal never cross a country border and never move
///   toward an unknown destination, whatever the residency policy says.
///
/// Both jurisdictions are server-derived; an unparsed string cannot reach
/// the gate.
pub fn may_replicate(
    data_policy: DataPolicy,
    source_jurisdiction: Option<&Jurisdiction>,
    target_jurisdiction: Option<&Jurisdiction>,
    residency: &ResidencyPolicy,
) -> bool {
    match (source_jurisdiction, target_jurisdiction) {
        // Known source AND destination: the EDGE's own residency policy
        // makes the decision.
        (Some(src), Some(dst)) => residency.allows_export(data_policy, src, dst),
        // Known source, UNKNOWN destination: an unknown destination is
        // not 'same country'. CorporateAllowed may still export an
        // unrestricted class (the nineteenth-audit contract); LocalOnly
        // and AllowedCountries grant nothing to a destination they cannot
        // vouch for.
        (Some(_src), None) => match residency {
            ResidencyPolicy::CorporateAllowed => {
                !matches!(data_policy, DataPolicy::Restricted | DataPolicy::Personal)
            }
            ResidencyPolicy::LocalOnly | ResidencyPolicy::AllowedCountries(_) => false,
        },
        // No source jurisdiction -> nothing may leave.
        (None, Some(_dst)) => false,
        // FAIL-CLOSED (twentieth audit P0): no source AND no destination
        // grants nothing.
        (None, None) => false,
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
/// P0-3 + twenty-second audit P0/P1-1): from the source EVENT's
/// sensitivity (the data class), its scope site's manifest country (the
/// source jurisdiction — `country_policies.data_residency` holds
/// JURISDICTION codes such as "ma"/"tn", never data classifications),
/// and the country policy revision. FAIL-CLOSED at every step:
/// - no source event -> error (the artifact always names a real event)
/// - unparseable sensitivity -> error (never a silent downgrade)
/// - missing manifest / unknown jurisdiction -> error
///
/// Twenty-second audit P0/P1-1: every read here targets FORCE-RLS tables
/// (`operational_events`, `site_manifests`, `country_policies`,
/// `country_policy_versions`), so the WHOLE body runs inside ONE
/// [`with_tenant_tx`] — under a production NOSUPERUSER/NOBYPASSRLS app
/// role a raw pooled read (no `app.tenant_id` context) returns nothing
/// and the route would fail closed for EVERY event. With the tenant
/// context set on the transaction, the tenant-scoped reads resolve and
/// every check below stays identical.
///
/// Twenty-second audit P0/P1-5: when `projection_schema` is empty the
/// artifact's schema label is derived from the source EVENT's own
/// `event_type` — the route no longer passes any client-supplied
/// identity, so the label is server-fixed.
pub async fn authorize_projection(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    source_event_id: Uuid,
    projection_schema: &str,
) -> Result<AuthorizedProjection> {
    let projection_schema = projection_schema.to_string();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            // 1. The source event must EXIST in this tenant (FORCE RLS
            //    makes a foreign event id resolve to nothing).
            type EvRow = (Option<Uuid>, String, String, serde_json::Value);
            let event: Option<EvRow> = sqlx::query_as(
                "SELECT scope_site_id, sensitivity, event_type, payload FROM operational_events \
                 WHERE id = $1 AND tenant_id = $2",
            )
            .bind(source_event_id)
            .bind(tenant_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: source event: {e}")))?;
            let Some((scope_site_id, sensitivity, event_type, event_payload)) = event else {
                return Err(SenseiError::Validation(
                    "replication: source_event_id must reference an EXISTING canonical event \
                     in this tenant — an artifact without a real source event is refused"
                        .to_string(),
                ));
            };
            // The projector builds the projection from the CANONICAL event
            // row: event type, occurrence time, scope and the event's own
            // payload. A client-supplied payload can never be substituted.
            // Twenty-second audit P0/P1-5: an empty schema label is
            // derived from the event's own type (server-fixed) — the
            // route accepts no client projection identity anymore.
            let projection_schema = if projection_schema.trim().is_empty() {
                event_type.clone()
            } else {
                projection_schema
            };
            let projected_payload = serde_json::json!({
                "source_event": source_event_id,
                "event_type": event_type,
                "occurred_at": sqlx::query_scalar::<_, chrono::DateTime<chrono::Utc>>(
                    "SELECT occurred_at FROM operational_events WHERE id = $1 AND tenant_id = $2",
                )
                .bind(source_event_id)
                .bind(tenant_id)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("replication: event time: {e}")))?,
                "scope_site": scope_site_id,
                "payload": event_payload,
            });

            let data_class = DataPolicy::parse(&sensitivity).map_err(SenseiError::Validation)?;

            // 2. Source jurisdiction: the event's scope site manifest
            //    country -> the country policy's data_residency
            //    JURISDICTION code.
            let site_id = scope_site_id;
            let source_jurisdiction = match site_id {
                Some(site_id) => {
                    let country: Option<String> = sqlx::query_scalar(
                        "SELECT sm.country FROM site_manifests sm                  WHERE sm.tenant_id = $1 AND sm.site_id = $2",
                    )
                    .bind(tenant_id)
                    .bind(site_id)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        SenseiError::Database(format!("replication: manifest lookup: {e}"))
                    })?;
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
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        SenseiError::Database(format!("replication: policy lookup: {e}"))
                    })?;
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

            // 3. Policy revision: the country policy revision governing
            //    the source jurisdiction (the artifact pins the decision
            //    to a revision).
            let policy_revision: i64 = sqlx::query_scalar(
                "SELECT COALESCE(MAX(revision), 0) FROM country_policy_versions          WHERE tenant_id = $1 AND country =              (SELECT country FROM site_manifests WHERE tenant_id = $1 AND site_id = $2)",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("replication: policy revision: {e}"))
            })?;

            Ok(AuthorizedProjection {
                source_event_id,
                source_site: site_id,
                source_jurisdiction,
                data_class: data_class.as_str().to_string(),
                projection_schema,
                policy_revision: policy_revision as u64,
                projected_payload,
            })
        })
    })
    .await
}

/// Derive the projection's ENTITY IDENTITY from the source event
/// (twentieth audit P0): when the event's relational object projection
/// names a 'subject' (`operational_event_objects.role = 'subject'`), the
/// subject's object type and id ARE the projection's entity identity —
/// the client cannot relabel an event as some other entity's projection.
/// Twenty-second audit P0/P1-5: the ROUTE derives the identity SOLELY
/// from the source event (no client fallback), and this read runs inside
/// a tenant transaction — `operational_event_objects` is FORCE RLS, so
/// under a NOSUPERUSER/NOBYPASSRLS app role a raw pooled read would find
/// no subject.
///
/// Twenty-third audit P1 (subject-count strictness): identity is exact —
/// there is no `LIMIT 1` guess over the subject objects anymore:
/// - ZERO subjects is a Validation error (nothing names the entity the
///   queue row would be keyed on — nothing client-supplied may stand in);
/// - MORE THAN ONE subject is a Validation error TOO: a projection that
///   would claim two entities at once requires EXPLICIT projector
///   semantics (which entity is the identity?), and none are defined yet —
///   so it is refused, never guessed;
/// - EXACTLY one subject is used.
pub async fn derive_projection_identity(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    event_id: Uuid,
) -> Result<(String, Uuid)> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            type SubjectRow = (String, Uuid);
            // NO LIMIT 1: the subject set must be counted EXACTLY, so the
            // derivation can reject both the empty set and the ambiguous
            // multi-subject set instead of picking an arbitrary one.
            let subjects: Vec<SubjectRow> = sqlx::query_as(
                "SELECT object_type, object_id FROM operational_event_objects \
                 WHERE tenant_id = $1 AND event_id = $2 AND role = 'subject' \
                 ORDER BY object_type ASC, object_id ASC",
            )
            .bind(tenant_id)
            .bind(event_id)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: subject derivation: {e}")))?;
            match subjects.len() {
                0 => Err(SenseiError::Validation(
                    "replication: the source event carries no subject object — the projection \
                     identity cannot be derived, so it cannot be enqueued"
                        .to_string(),
                )),
                1 => Ok(subjects.into_iter().next().expect("exactly one subject")),
                _ => Err(SenseiError::Validation(
                    "replication: the source event projects MULTIPLE subject objects — multiple \
                     subjects require explicit projector semantics (none defined yet), so the \
                     projection identity cannot be derived"
                        .to_string(),
                )),
            }
        })
    })
    .await
}

/// ONE federation edge the source tenant holds toward a destination
/// (twentieth audit P0 + twenty-second audit P0/P1-4): the membership row
/// IS the policy record. The edge names the target that receives the
/// projection and carries the governance the residency decision must run
/// against — `target_tenant` is the peer of one `federation_memberships`
/// row, `target_site` the PEER SITE MANIFEST the projection would land on
/// (migration 156 exposes the peer's `site_manifests.site_id`, so the
/// enqueued `site_replication_log` row records exactly which peer site
/// the edge authorized), `target_jurisdiction` the TYPED residency code
/// of that destination (derived from the peer's country policy — never an
/// arbitrary `LIMIT 1` pick), `allowed_data_classes` the classes the
/// membership permits over the edge, `residency_policy` the policy that
/// governs cross-border movement, and `policy_revision` the peer country
/// policy version the decision is pinned to — ONE deterministic revision
/// per peer site (a lateral `ORDER BY revision DESC LIMIT 1`, so multiple
/// version rows can never duplicate an edge).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FederationEdge {
    pub source_tenant: Uuid,
    pub source_site: Option<Uuid>,
    pub target_tenant: Uuid,
    pub target_site: Option<Uuid>,
    pub target_jurisdiction: Jurisdiction,
    pub allowed_data_classes: Vec<DataPolicy>,
    pub residency_policy: ResidencyPolicy,
    pub policy_revision: u64,
}

impl FederationEdge {
    /// The JSONB audit snapshot persisted on every enqueued row
    /// (`site_replication_log.edge_policy`): the full edge context the
    /// decision was made against, in canonical DB labels.
    pub fn policy_snapshot(&self) -> serde_json::Value {
        serde_json::json!({
            "source_tenant": self.source_tenant,
            "source_site": self.source_site,
            "target_tenant": self.target_tenant,
            "target_site": self.target_site,
            "target_jurisdiction": self.target_jurisdiction.as_str(),
            "allowed_data_classes": self
                .allowed_data_classes
                .iter()
                .map(|c| c.as_str())
                .collect::<Vec<_>>(),
            "residency_policy": self.residency_policy.as_str(),
            "policy_revision": self.policy_revision,
        })
    }
}

/// Load EVERY federation edge the SOURCE tenant holds (twentieth audit
/// P0, twenty-first audit item 4, twenty-second audit P0/P1-2/4): the
/// membership-to-peer-governance join is a SINGLE call into the SECURITY
/// DEFINER function `federation_governance_edges()` (migrations 153 +
/// 156) — the ONLY cross-tenant federation-governance boundary. The
/// function executes with the migration owner's rights, so the FORCE-RLS
/// tenant-local policies of the peer's `site_manifests`/
/// `country_policies` cannot hide the peer metadata: under a production
/// non-BYPASSRLS role with `app.tenant_id` set to the SOURCE tenant, the
/// peer rows are invisible to any raw pooled read, and the loader no
/// longer performs one. Twenty-second audit P0/P1-2: the function takes
/// NO tenant argument — migration 156 dropped the caller-trusted
/// parameterized form; the source tenant is read from the session context
/// INSIDE the function, and this loader opens its own tenant transaction
/// (with the crate's [`with_tenant_tx`]) so `app.tenant_id` is set for
/// the call under ANY role (every role may `set_config`). NO `LIMIT 1`:
/// one edge per peer SITE the projection could land on, so the route can
/// make one target-specific decision per edge instead of checking an
/// arbitrary country — migration 156's lateral pins ONE deterministic
/// policy revision per peer site and exposes `peer_site_id`, which this
/// loader carries as `target_site = Some(peer_site_id)` so enqueued rows
/// record the exact destination site. FAIL-CLOSED per row: an edge whose
/// governance cannot be read EXACTLY (no peer country policy, an unknown
/// jurisdiction code, an unparseable residency label or an unparseable
/// allow-list entry) grants nothing and yields NO edge — an ambiguous or
/// corrupt membership is never guessed into an arbitrary decision.
pub async fn load_federation_edges(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    source_site_id: Option<Uuid>,
) -> Result<Vec<FederationEdge>> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            type EdgeRow = (
                Uuid,              // peer_tenant_id
                Uuid,              // peer_site_id (the destination's site manifest)
                String,            // peer_country (the destination's manifest country)
                Option<String>,    // peer data_residency (NULL when unset -> row skipped)
                i64,               // peer country policy revision (0 when none)
                serde_json::Value, // allowed_data_classes
                String,            // residency_policy label
                serde_json::Value, // allowed_countries
            );
            let rows: Vec<EdgeRow> = sqlx::query_as("SELECT * FROM federation_governance_edges()")
                .fetch_all(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("replication: federation edges: {e}"))
                })?;

            let mut edges = Vec::with_capacity(rows.len());
            for (
                peer_tenant,
                peer_site,
                _peer_country,
                data_residency,
                revision,
                allowed_classes_json,
                residency_label,
                allowed_countries_json,
            ) in rows
            {
                // No peer country policy record (or an unknown residency
                // code): the destination's jurisdiction cannot be derived,
                // so nothing is ever exported to it.
                let Some(residency_code) = data_residency.as_deref() else {
                    continue;
                };
                let Ok(target_jurisdiction) = Jurisdiction::parse(residency_code) else {
                    continue;
                };
                // The membership's allow-list must parse EXACTLY — an
                // unparseable class cannot be honored, so the edge grants
                // nothing.
                let allowed_labels: Vec<String> = match serde_json::from_value(allowed_classes_json)
                {
                    Ok(labels) => labels,
                    Err(_) => continue,
                };
                let mut allowed_data_classes = Vec::with_capacity(allowed_labels.len());
                let mut classes_ok = true;
                for label in allowed_labels {
                    match DataPolicy::parse(&label) {
                        Ok(policy) => allowed_data_classes.push(policy),
                        Err(_) => {
                            classes_ok = false;
                            break;
                        }
                    }
                }
                if !classes_ok {
                    continue;
                }
                let residency_policy = match residency_label.as_str() {
                    "local_only" => ResidencyPolicy::LocalOnly,
                    "corporate_allowed" => ResidencyPolicy::CorporateAllowed,
                    "allowed_countries" => {
                        // The allowed-country list must parse EXACTLY too.
                        let codes: Vec<String> =
                            match serde_json::from_value(allowed_countries_json) {
                                Ok(codes) => codes,
                                Err(_) => continue,
                            };
                        let mut countries = Vec::with_capacity(codes.len());
                        let mut countries_ok = true;
                        for code in codes {
                            match Jurisdiction::parse(&code) {
                                Ok(jurisdiction) => countries.push(jurisdiction),
                                Err(_) => {
                                    countries_ok = false;
                                    break;
                                }
                            }
                        }
                        if !countries_ok {
                            continue;
                        }
                        ResidencyPolicy::AllowedCountries(countries)
                    }
                    // The CHECK constraint in migration 148 makes this
                    // unreachable; the guard keeps the loader fail-closed
                    // anyway.
                    _ => continue,
                };
                edges.push(FederationEdge {
                    source_tenant: tenant_id,
                    source_site: source_site_id,
                    target_tenant: peer_tenant,
                    // Twenty-second audit P0/P1-4: the governance function
                    // exposes the peer's site identity, so the edge names
                    // the EXACT destination site the queue row records as
                    // target_site_id.
                    target_site: Some(peer_site),
                    target_jurisdiction,
                    allowed_data_classes,
                    residency_policy,
                    policy_revision: revision as u64,
                });
            }
            Ok(edges)
        })
    })
    .await
}

/// Enqueue one AUTHORIZED state projection for ONE federation edge —
/// SITE-LOCAL, never dependent on the corporate link. The site's
/// operations keep running while the queue is durable in its own
/// tenant-scoped transaction. Twentieth audit P0: the enqueued row names
/// its destination (`target_tenant_id`/`target_site_id`), the TYPED
/// `target_jurisdiction` the residency decision was made against, and the
/// full edge snapshot (`edge_policy`) — a destination-less queue row no
/// longer exists. The gate is evaluated against the EDGE's own
/// `residency_policy` and `allowed_data_classes` (the route screens
/// before calling; this is the second line of defense), and the
/// `source_event_id` + `projection_type` + target idempotency key makes
/// duplicate enqueues of the same event to the same edge a hard UNIQUE
/// rejection — while the SAME event to DIFFERENT edges is legal (one row
/// per edge).
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
    edge: &FederationEdge,
) -> Result<()> {
    let policy = DataPolicy::parse(&envelope.data_policy).map_err(SenseiError::Validation)?;
    if !edge.allowed_data_classes.contains(&policy) {
        return Err(SenseiError::Validation(
            "the federation edge's allowed_data_classes exclude this projection".to_string(),
        ));
    }
    if !may_replicate(
        policy,
        source_jurisdiction,
        Some(&edge.target_jurisdiction),
        &edge.residency_policy,
    ) {
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
    let target_tenant_id = edge.target_tenant;
    let target_site_id = edge.target_site;
    let target_jurisdiction = edge.target_jurisdiction.as_str().to_string();
    let edge_policy = edge.policy_snapshot();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            sqlx::query(
                "INSERT INTO site_replication_log \
                     (tenant_id, site_id, entity_type, entity_id, projection, source_event_id, \
                      schema_version, projection_type, projection_revision, data_policy, status, \
                      target_tenant_id, target_site_id, target_jurisdiction, edge_policy) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending', \
                         $11, $12, $13, $14)",
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
            .bind(target_tenant_id)
            .bind(target_site_id)
            .bind(&target_jurisdiction)
            .bind(edge_policy)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("replication: enqueue failed: {e}")))?;
            Ok(())
        })
    })
    .await
}

/// Enqueue ONE AUTHORIZED state projection across EVERY federation edge
/// in a SINGLE transaction (twenty-third audit P1 — fanout idempotency).
/// The route pre-authorizes (the source event exists, its jurisdiction
/// derives, its subject identity is EXACTLY one object) and then calls
/// this once; this function runs ONE [`with_tenant_tx`] over ALL edges:
///
/// - every edge is screened with the SAME gate as a per-edge enqueue —
///   the edge's own `allowed_data_classes` and its own `residency_policy`
///   via [`may_replicate`] (the route-level second line of defense); an
///   edge the gate denies is counted in `blocked`, never enqueued;
/// - every permitted edge is inserted with
///   `ON CONFLICT (tenant_id, source_event_id, target_tenant_id,
///   target_site_id) DO NOTHING` — the plain unique index added by
///   migration 159 (the migration-148 dedupe index is expression-based
///   and cannot be inferred by a plain conflict target). A row that
///   already exists (a previous publish, or a retry after a mid-way
///   failure) is skipped and counted in `already_present`, so repeated
///   publishes of the same command converge to the same complete set —
///   a retry NEVER 500s on the first duplicate, and an error mid-fanout
///   rolls the WHOLE transaction back (no partial success).
///
/// Returns the [`FanoutReport`] counting newly-enqueued vs already-present
/// vs blocked edges. Nothing is written until every edge has been
/// screened, and the single transaction commits (or rolls back) as one.
#[allow(clippy::too_many_arguments)]
pub async fn enqueue_projection_fanout(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    entity_type: &str,
    entity_id: Uuid,
    projection: serde_json::Value,
    source_event_id: &str,
    envelope: &ReplicationEnvelope,
    source_jurisdiction: &Jurisdiction,
    edges: &[FederationEdge],
) -> Result<FanoutReport> {
    let policy = DataPolicy::parse(&envelope.data_policy).map_err(SenseiError::Validation)?;
    // ALL edges of one fanout share the identity, projection content and
    // envelope — only the per-edge target/governance differs.
    let entity_type = entity_type.to_string();
    let projection_type = if envelope.projection_type.is_empty() {
        entity_type.clone()
    } else {
        envelope.projection_type.clone()
    };
    let source_event_id = source_event_id.to_string();
    let data_policy = envelope.data_policy.clone();
    let schema_version = envelope.schema_version as i32;
    let projection_revision = envelope.projection_revision as i64;
    let source_jurisdiction = source_jurisdiction.clone();
    // The tenant transaction closure owns every input (edge count is
    // small — a fanout spans a handful of edges).
    let edges = edges.to_vec();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let mut report = FanoutReport {
                newly_enqueued: 0,
                already_present: 0,
                blocked: 0,
            };
            for edge in &edges {
                // The gate is evaluated ONCE PER EDGE against THAT edge's
                // own policy record (twentieth audit P0): an edge whose
                // allowed classes exclude the projection, or whose
                // residency policy denies the move, is BLOCKED — counted,
                // not enqueued, and never an error.
                if !edge.allowed_data_classes.contains(&policy)
                    || !may_replicate(
                        policy,
                        Some(&source_jurisdiction),
                        Some(&edge.target_jurisdiction),
                        &edge.residency_policy,
                    )
                {
                    report.blocked += 1;
                    continue;
                }
                let edge_policy = edge.policy_snapshot();
                let res = sqlx::query(
                    "INSERT INTO site_replication_log \
                         (tenant_id, site_id, entity_type, entity_id, projection, source_event_id, \
                          schema_version, projection_type, projection_revision, data_policy, \
                          status, target_tenant_id, target_site_id, target_jurisdiction, \
                          edge_policy) \
                     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending', \
                             $11, $12, $13, $14) \
                     ON CONFLICT (tenant_id, source_event_id, target_tenant_id, target_site_id) \
                     DO NOTHING",
                )
                .bind(tenant_id)
                .bind(site_id)
                .bind(&entity_type)
                .bind(entity_id)
                .bind(projection.clone())
                .bind(source_event_id.as_str())
                .bind(schema_version)
                .bind(&projection_type)
                .bind(projection_revision)
                .bind(&data_policy)
                .bind(edge.target_tenant)
                .bind(edge.target_site)
                .bind(edge.target_jurisdiction.as_str())
                .bind(edge_policy)
                .execute(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("replication: fanout enqueue failed: {e}"))
                })?;
                // rows_affected counts ONLY rows the statement actually
                // inserted — a row skipped by DO NOTHING counts 0.
                if res.rows_affected() == 1 {
                    report.newly_enqueued += 1;
                } else {
                    report.already_present += 1;
                }
            }
            Ok(report)
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
