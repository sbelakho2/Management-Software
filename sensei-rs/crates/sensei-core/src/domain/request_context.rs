//! RequestContext (eighteenth audit P0-1/P1-11; nineteenth audit P1;
//! twenty-ninth audit Wave A item 6): ONE server-created, internally
//! consistent object every scoped repository operation takes instead of
//! naked `tenant_id`/`site_id`/UUID combinations.
//!
//! - `scope` — the principal's AUTHORIZATION boundary: an
//!   [`AuthorizedScope`] resolved from their ACTIVE role-slot
//!   assignments (see `AuthorizedScope::resolve`). A principal with no
//!   active assignment resolves to `NoOperationalScope` — FAIL-CLOSED
//!   (eighteenth audit P0-1): no assignment can never become broader
//!   access, and `TenantWide` is only ever an EXPLICIT bootstrap grant.
//!   The tenant-side authorization model and the operational side are
//!   now separated: `scope` carries what the principal MAY access;
//!   `focus` carries where the session acts.
//! - `focus` — the single OPERATIONAL context the session acts in
//!   (site / value stream / work center / shift), an
//!   [`OperationalFocus`]. The builder proves the chain is consistent:
//!   every active sub-scope is validated INDEPENDENTLY against the DB —
//!   a work center's, shift's or value stream's resolved site must
//!   exist and equal the focus site, and a sub-scope without a focus
//!   site is unrepresentable.
//!
//! Invariants (nineteenth audit P1; twenty-ninth audit Wave A item 6):
//! the focus is validated against the scope, never trusted from the
//! client:
//!
//! - `NoOperationalScope` ⇒ the focus must be entirely `None` — no
//!   entitlement → no operating context (no entitlement → no scope →
//!   no data).
//! - `Sites(sites)` ⇒ a focus site, when set, must be `∈ sites` — a
//!   principal can never act in a site they are not entitled to.
//! - `WorkCenter(wc)` ⇒ a focus site, when set, must equal `wc.site`.
//! - `TenantWide` ⇒ every well-formed focus is authorized.
//! - A focus sub-scope (value stream / work center / shift) without a
//!   focus site is unrepresentable.
//!
//! Every repository command with `WHERE ... site_id = ANY($n)` embeds
//! `authorized_sites()` from `scope` in the SAME transaction as the
//! mutation; a `NoOperationalScope` caller's empty set matches zero
//! rows → NotFound/Forbidden.
use uuid::Uuid;

use crate::domain::scope::AuthorizedScope;
use crate::error::{Result, SenseiError};

/// The session's single OPERATIONAL context (twenty-ninth audit Wave A
/// item 6): where the principal acts, as distinct from [`AuthorizedScope`]
/// (what they are entitled to). All components are optional — the
/// all-`None` focus is the "no operating context chosen" state, valid
/// for every scope; the builder validates any `Some` component against
/// the scope and the topology chain.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct OperationalFocus {
    pub site: Option<Uuid>,
    pub value_stream: Option<Uuid>,
    pub work_center: Option<Uuid>,
    pub shift: Option<Uuid>,
}

impl OperationalFocus {
    pub fn is_empty(&self) -> bool {
        self.site.is_none()
            && self.value_stream.is_none()
            && self.work_center.is_none()
            && self.shift.is_none()
    }
}

/// Server-created request context. `scope` is the security boundary:
/// repository commands embed `site_id = ANY($n)` with
/// [`RequestContext::authorized_sites`] in the SAME transaction as the
/// mutation; `focus` is the validated operating context.
///
/// `locale` / `timezone` / `currency` / `country_policy_revision` are
/// server-derived from the focus site's `country_policies` row
/// (`language` / `timezone` / `currency` columns) and the currently
/// effective `country_policy_versions.revision`; all are `None` when
/// there is no focus site.
#[derive(Debug, Clone, serde::Serialize)]
pub struct RequestContext {
    pub tenant: Uuid,
    pub principal: Uuid,
    /// The principal's authorization (what they MAY access) — see
    /// [`AuthorizedScope`]. TenantWide is only ever an explicit
    /// bootstrap grant; the DB-resolved builder never returns it.
    pub scope: AuthorizedScope,
    /// The validated operating context (where the session acts).
    pub focus: OperationalFocus,
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
    /// audit P1; twenty-ninth audit Wave A item 6): the scope comes from
    /// ACTIVE principal-assignment → role-slot sites; the operating
    /// focus is validated against the topology chain —
    /// `work_centers.site_id`, `shifts.site_id` and
    /// `value_streams.site_id` must each exist and equal the focus site,
    /// a sub-scope without a focus site is a Validation error — and
    /// against the scope (see [`Self::validate_operating_scope`]).
    ///
    /// `active_site` / `active_value_stream` / `active_work_center` /
    /// `active_shift` supply the session's claimed operating context
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
        // The AUTHORIZATION boundary, DB-resolved (the same active
        // role-slot query as before): Sites(sites) or — with no active
        // assignment — NoOperationalScope. Never TenantWide.
        let scope = AuthorizedScope::resolve(&mut tx, principal).await?;

        // Topology-consistency proof (nineteenth audit P1): every active
        // sub-scope is validated INDEPENDENTLY, not only when paired with
        // a focus site — a work center's site must exist and equal the
        // focus site; an active sub-scope with no focus site is a
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

        // Server-derived locale (nineteenth audit P1): the focus site's
        // country_policies row (language/timezone/currency) and the
        // currently effective country_policy_versions.revision. One extra
        // query in the same tx; all four stay None when there is no
        // focus site or no policy row for the site's country.
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

        let focus = OperationalFocus {
            site: active_site,
            value_stream: active_value_stream,
            work_center: active_work_center,
            shift: active_shift,
        };
        let ctx = Self {
            tenant,
            principal,
            scope,
            focus,
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

    /// Re-check the operating-scope invariants (nineteenth audit P1;
    /// twenty-ninth audit Wave A item 6) — the focus vs the scope:
    ///
    /// - `NoOperationalScope` ⇒ the focus must be entirely `None` — no
    ///   entitlement → no operating context (no entitlement → no scope
    ///   → no data);
    /// - a focus site, when set, MUST be authorized by the scope
    ///   (`Sites` membership / the `WorkCenter` scope's own site — a
    ///   principal can never act in a site they are not entitled to);
    /// - a focus sub-scope (value stream / work center / shift) without
    ///   a focus site is unrepresentable.
    ///
    /// `build()` runs the DB-backed existence checks, then this check,
    /// before returning.
    pub fn validate_operating_scope(&self) -> Result<()> {
        if matches!(self.scope, AuthorizedScope::NoOperationalScope) {
            if self.focus.is_empty() {
                return Ok(());
            }
            return Err(SenseiError::Validation(
                "principal has no operational scope — no operating focus may be set \
                 (no entitlement → no operating context)"
                    .to_string(),
            ));
        }
        if let Some(site) = self.focus.site {
            if !self.scope.allows_site(site) {
                return Err(SenseiError::Validation(format!(
                    "operating site {site} is not among the principal's authorized sites — \
                     the operating context is unauthorized"
                )));
            }
        } else {
            for (label, id) in [
                ("work center", self.focus.work_center),
                ("shift", self.focus.shift),
                ("value stream", self.focus.value_stream),
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
    /// operational scope has no entitlement — repository commands
    /// embedding `site_id = ANY($n)` with the empty
    /// [`Self::authorized_sites`] vector match zero rows.
    pub fn has_entitlement(&self) -> bool {
        match &self.scope {
            AuthorizedScope::NoOperationalScope => false,
            AuthorizedScope::TenantWide => true,
            AuthorizedScope::Sites(sites) => !sites.is_empty(),
            AuthorizedScope::WorkCenter(_) => true,
        }
    }

    /// The SQL site-set placeholder value for scoped commands: the list
    /// of sites this scope authorizes (`Sites` → its sites;
    /// `WorkCenter` → its site).
    ///
    /// `TenantWide` → an EMPTY vec: tenant-wide is an explicit
    /// all-access grant, NOT representable as a site set — commands
    /// embedding `site_id = ANY($n)` with the empty set match zero rows,
    /// so a tenant-wide caller must go through resource-scoped
    /// enforcement (`AuthorizedScope::enforce_resource`) instead of the
    /// site-set predicates.
    pub fn authorized_sites(&self) -> Vec<Uuid> {
        match &self.scope {
            AuthorizedScope::NoOperationalScope => Vec::new(),
            AuthorizedScope::TenantWide => Vec::new(),
            AuthorizedScope::Sites(sites) => sites.clone(),
            AuthorizedScope::WorkCenter(wc) => vec![wc.site],
        }
    }

    /// The single operating site (the focus's site) — the legacy
    /// `active_site` accessor; `None` when the session has no operating
    /// context.
    pub fn active_site(&self) -> Option<Uuid> {
        self.focus.site
    }
}
