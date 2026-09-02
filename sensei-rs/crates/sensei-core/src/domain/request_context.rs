//! RequestContext (eighteenth audit P0-1/P1-11; nineteenth audit P1):
//! ONE server-created, internally consistent object every scoped
//! repository operation takes instead of naked `tenant_id`/`site_id`/UUID
//! combinations.
//!
//! - `entitlement_sites` — every site the principal's ACTIVE role-slot
//!   assignments entitle (authorization).
//! - `active_*` — the single operational context the session acts in
//!   (site / value stream / work center / shift). The builder proves the
//!   chain is consistent: every active sub-scope is validated
//!   INDEPENDENTLY against the DB — a work center's, shift's or value
//!   stream's resolved site must exist and equal the active site, and a
//!   sub-scope without an active site is unrepresentable.
//!
//! Invariants (nineteenth audit P1): an active site MUST be contained in
//! `entitlement_sites` — a principal can never act in a site they are not
//! entitled to; empty `entitlement_sites` with an active site is a
//! Validation error (no entitlement → no operating scope). Only the
//! all-active-None state is valid without entitlements (the no-scope
//! state). Invariant: No entitlement → empty `entitlement_sites` → every
//! repository command with `WHERE ... site_id = ANY($n)` matches zero
//! rows → NotFound/Forbidden. No assignment can never become broader
//! access (eighteenth audit P0-1).
use uuid::Uuid;

use crate::error::{Result, SenseiError};

/// Server-created request context. `entitlement_sites` is the security
/// boundary: repository commands embed `site_id = ANY($n)` with this
/// vector in the SAME transaction as the mutation.
///
/// `locale` / `timezone` / `currency` / `country_policy_revision` are
/// server-derived from the active site's `country_policies` row
/// (`language` / `timezone` / `currency` columns) and the currently
/// effective `country_policy_versions.revision`; all are `None` when
/// there is no active site.
#[derive(Debug, Clone, serde::Serialize)]
pub struct RequestContext {
    pub tenant: Uuid,
    pub principal: Uuid,
    pub entitlement_sites: Vec<Uuid>,
    pub active_site: Option<Uuid>,
    pub active_value_stream: Option<Uuid>,
    pub active_work_center: Option<Uuid>,
    pub active_shift: Option<Uuid>,
    #[serde(default)]
    pub locale: Option<String>,
    #[serde(default)]
    pub timezone: Option<String>,
    #[serde(default)]
    pub currency: Option<String>,
    #[serde(default)]
    pub country_policy_revision: Option<u64>,
    pub trace_id: String,
}

impl RequestContext {
    /// Build a context from the DB (eighteenth audit P0-1; nineteenth
    /// audit P1): entitlement sites come from ACTIVE
    /// principal-assignment → role-slot scope; the active operating scope
    /// is validated against the topology chain — `work_centers.site_id`,
    /// `shifts.site_id` and `value_streams.site_id` must each exist and
    /// equal the active site, a sub-scope without an active site is a
    /// Validation error, and the active site must be contained in the
    /// entitlement sites.
    ///
    /// `active_scope` supplies the session's claimed operating context
    /// (from the agent context); the builder VERIFIES it instead of
    /// trusting it.
    #[cfg(not(target_arch = "wasm32"))]
    #[allow(clippy::too_many_arguments)]
    pub async fn build(
        pool: &sqlx::PgPool,
        tenant: Uuid,
        principal: Uuid,
        active_site: Option<Uuid>,
        active_value_stream: Option<Uuid>,
        active_work_center: Option<Uuid>,
        active_shift: Option<Uuid>,
        trace_id: String,
    ) -> Result<Self> {
        use crate::db::TenantTx;

        let mut tx = TenantTx::begin(pool, tenant)
            .await
            .map_err(|e| SenseiError::Database(format!("request-context: begin tx: {e}")))?;
        let entitlement_sites: Vec<Uuid> = sqlx::query_scalar(
            "SELECT DISTINCT rs.scope_site_id \
             FROM principal_assignments pa \
             JOIN role_slots rs ON rs.id = pa.slot_id \
             WHERE pa.principal_id = $1 AND pa.ended_at IS NULL \
               AND rs.scope_site_id IS NOT NULL",
        )
        .bind(principal)
        .fetch_all(&mut **tx.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("request-context: entitlements: {e}")))?;

        // Topology-consistency proof (nineteenth audit P1): every active
        // sub-scope is validated INDEPENDENTLY, not only when paired with
        // an active site — a work center's site must exist and equal the
        // active site; an active sub-scope with no active site is a
        // Validation error (unrepresentable context).
        if let Some(wc) = active_work_center {
            let wc_site: Option<Uuid> =
                sqlx::query_scalar("SELECT site_id FROM work_centers WHERE id = $1")
                    .bind(wc)
                    .fetch_optional(&mut **tx.tx())
                    .await
                    .map_err(|e| SenseiError::Database(format!("request-context: wc site: {e}")))?;
            match wc_site {
                Some(actual) if active_site == Some(actual) => {}
                Some(actual) => {
                    return Err(SenseiError::Validation(match active_site {
                        Some(site) => format!(
                            "active work center {wc} belongs to site {actual}, not {site} — \
                             the operating context is inconsistent"
                        ),
                        None => format!(
                            "active work center {wc} belongs to site {actual} but no active \
                             site is set — a work center without a site context is unrepresentable"
                        ),
                    }))
                }
                None => {
                    return Err(SenseiError::Validation(format!(
                        "active work center {wc} does not exist in this tenant"
                    )))
                }
            }
        }
        // A shift's site must exist and equal the active site.
        if let Some(shift) = active_shift {
            let shift_site: Option<Uuid> =
                sqlx::query_scalar("SELECT site_id FROM shifts WHERE id = $1")
                    .bind(shift)
                    .fetch_optional(&mut **tx.tx())
                    .await
                    .map_err(|e| {
                        SenseiError::Database(format!("request-context: shift site: {e}"))
                    })?;
            match shift_site {
                Some(actual) if active_site == Some(actual) => {}
                Some(actual) => {
                    return Err(SenseiError::Validation(match active_site {
                        Some(site) => format!(
                            "active shift {shift} belongs to site {actual}, not {site} — \
                             the operating context is inconsistent"
                        ),
                        None => format!(
                            "active shift {shift} belongs to site {actual} but no active \
                             site is set — a shift without a site context is unrepresentable"
                        ),
                    }))
                }
                None => {
                    return Err(SenseiError::Validation(format!(
                        "active shift {shift} does not exist in this tenant"
                    )))
                }
            }
        }
        // A value stream's site must exist and equal the active site
        // (value_streams.site_id is NOT NULL in the schema).
        if let Some(vs) = active_value_stream {
            let vs_site: Option<Uuid> =
                sqlx::query_scalar("SELECT site_id FROM value_streams WHERE id = $1")
                    .bind(vs)
                    .fetch_optional(&mut **tx.tx())
                    .await
                    .map_err(|e| {
                        SenseiError::Database(format!("request-context: value stream site: {e}"))
                    })?;
            match vs_site {
                Some(actual) if active_site == Some(actual) => {}
                Some(actual) => {
                    return Err(SenseiError::Validation(match active_site {
                        Some(site) => format!(
                            "active value stream {vs} belongs to site {actual}, not {site} — \
                             the operating context is inconsistent"
                        ),
                        None => format!(
                            "active value stream {vs} belongs to site {actual} but no active \
                             site is set — a value stream without a site context is unrepresentable"
                        ),
                    }))
                }
                None => {
                    return Err(SenseiError::Validation(format!(
                        "active value stream {vs} does not exist in this tenant"
                    )))
                }
            }
        }

        // Server-derived locale (nineteenth audit P1): the active site's
        // country_policies row (language/timezone/currency) and the
        // currently effective country_policy_versions.revision. One extra
        // query in the same tx; all four stay None when there is no
        // active site or no policy row for the site's country.
        let mut locale = None;
        let mut timezone = None;
        let mut currency = None;
        let mut country_policy_revision = None;
        if let Some(site) = active_site {
            type PolicyRow = (Option<String>, Option<String>, Option<String>, Option<i64>);
            let policy_row: Option<PolicyRow> = sqlx::query_as(
                "SELECT cp.language, cp.timezone, cp.currency, cpv.revision \
                     FROM sites s \
                     JOIN country_policies cp \
                       ON cp.tenant_id = s.tenant_id AND cp.country = s.country \
                     LEFT JOIN LATERAL ( \
                         SELECT cpv2.revision \
                         FROM country_policy_versions cpv2 \
                         WHERE cpv2.tenant_id = s.tenant_id AND cpv2.country = s.country \
                           AND cpv2.valid_from <= NOW() \
                           AND (cpv2.valid_until IS NULL OR cpv2.valid_until > NOW()) \
                         ORDER BY cpv2.valid_from DESC, cpv2.revision DESC \
                         LIMIT 1 \
                     ) cpv ON TRUE \
                     WHERE s.tenant_id = $1 AND s.id = $2",
            )
            .bind(tenant)
            .bind(site)
            .fetch_optional(&mut **tx.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("request-context: country policy: {e}")))?;
            if let Some((lang, tz, cur, rev)) = policy_row {
                locale = lang;
                timezone = tz;
                currency = cur;
                country_policy_revision = rev.map(|r| r as u64);
            }
        }
        tx.rollback()
            .await
            .map_err(|e| SenseiError::Database(format!("request-context: rollback: {e}")))?;

        let ctx = Self {
            tenant,
            principal,
            entitlement_sites,
            active_site,
            active_value_stream,
            active_work_center,
            active_shift,
            locale,
            timezone,
            currency,
            country_policy_revision,
            trace_id,
        };
        // Construction-time invariant re-check: invalid combinations are
        // impossible at construction.
        ctx.validate_operating_scope()?;
        Ok(ctx)
    }

    /// Re-check the operating-scope invariants (nineteenth audit P1):
    ///
    /// - an active site MUST be contained in `entitlement_sites` — a
    ///   principal can never act in a site they are not entitled to;
    ///   empty `entitlement_sites` with an active site is a Validation
    ///   error (no entitlement → no operating scope);
    /// - a sub-scope (work center / shift / value stream) without an
    ///   active site is unrepresentable.
    ///
    /// `build()` runs the DB-backed existence checks, then this check,
    /// before returning.
    pub fn validate_operating_scope(&self) -> Result<()> {
        if let Some(site) = self.active_site {
            if !self.entitlement_sites.contains(&site) {
                return Err(SenseiError::Validation(format!(
                    "active site {site} is not among the principal's entitlement sites — \
                     the operating context is unauthorized"
                )));
            }
        } else {
            for (label, id) in [
                ("work center", self.active_work_center),
                ("shift", self.active_shift),
                ("value stream", self.active_value_stream),
            ] {
                if let Some(id) = id {
                    return Err(SenseiError::Validation(format!(
                        "active {label} {id} requires an active site context — a {label} \
                         without a site is unrepresentable"
                    )));
                }
            }
        }
        Ok(())
    }

    /// FAIL-CLOSED (eighteenth audit P0-1): a principal with NO
    /// entitlement sites has no scope — repository commands embedding
    /// `site_id = ANY($n)` with this empty vector match zero rows.
    pub fn has_entitlement(&self) -> bool {
        !self.entitlement_sites.is_empty()
    }

    /// The SQL site-set placeholder value for scoped commands.
    pub fn authorized_sites(&self) -> &[Uuid] {
        &self.entitlement_sites
    }
}
