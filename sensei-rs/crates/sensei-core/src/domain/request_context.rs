//! RequestContext (eighteenth audit P0-1/P1-11): ONE server-created,
//! internally consistent object every scoped repository operation takes
//! instead of naked `tenant_id`/`site_id`/UUID combinations.
//!
//! - `entitlement_sites` — every site the principal's ACTIVE role-slot
//!   assignments entitle (authorization).
//! - `active_*` — the single operational context the session acts in
//!   (site / value stream / work center / shift). The builder proves the
//!   chain is consistent: a work center's DB-resolved site must equal the
//!   active site; a shift's site must equal the active site.
//!
//! Invariant: No entitlement → empty `entitlement_sites` → every
//! repository command with `WHERE ... site_id = ANY($n)` matches zero
//! rows → NotFound/Forbidden. No assignment can never become broader
//! access (eighteenth audit P0-1).
use uuid::Uuid;

use crate::error::{Result, SenseiError};

/// Server-created request context. `entitlement_sites` is the security
/// boundary: repository commands embed `site_id = ANY($n)` with this
/// vector in the SAME transaction as the mutation.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RequestContext {
    pub tenant: Uuid,
    pub principal: Uuid,
    pub entitlement_sites: Vec<Uuid>,
    pub active_site: Option<Uuid>,
    pub active_value_stream: Option<Uuid>,
    pub active_work_center: Option<Uuid>,
    pub active_shift: Option<Uuid>,
    pub trace_id: String,
}

impl RequestContext {
    /// Build a context from the DB (eighteenth audit P0-1): entitlement
    /// sites come from ACTIVE principal-assignment → role-slot scope;
    /// the active operating scope is validated against the topology chain
    /// (work_centers.site_id and shifts.site_id must agree with the
    /// active site) so `site = Tangier, work_center = Bizerte AOI` is
    /// unrepresentable.
    ///
    /// `active_scope` supplies the session's claimed operating context
    /// (from the agent context); the builder VERIFIES it instead of
    /// trusting it.
    #[cfg(not(target_arch = "wasm32"))]
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

        // Topology-consistency proof (eighteenth audit P1-11): a work
        // center's site must equal the active site.
        if let (Some(wc), Some(site)) = (active_work_center, active_site) {
            let wc_site: Option<Uuid> =
                sqlx::query_scalar("SELECT site_id FROM work_centers WHERE id = $1")
                    .bind(wc)
                    .fetch_optional(&mut **tx.tx())
                    .await
                    .map_err(|e| SenseiError::Database(format!("request-context: wc site: {e}")))?;
            match wc_site {
                Some(actual) if actual == site => {}
                Some(actual) => {
                    return Err(SenseiError::Validation(format!(
                        "active work center {wc} belongs to site {actual}, not {site} — \
                         the operating context is inconsistent"
                    )))
                }
                None => {
                    return Err(SenseiError::Validation(format!(
                        "active work center {wc} does not exist in this tenant"
                    )))
                }
            }
        }
        // A shift's site must equal the active site.
        if let (Some(shift), Some(site)) = (active_shift, active_site) {
            let shift_site: Option<Uuid> =
                sqlx::query_scalar("SELECT site_id FROM shifts WHERE id = $1")
                    .bind(shift)
                    .fetch_optional(&mut **tx.tx())
                    .await
                    .map_err(|e| {
                        SenseiError::Database(format!("request-context: shift site: {e}"))
                    })?;
            match shift_site {
                Some(actual) if actual == site => {}
                Some(actual) => {
                    return Err(SenseiError::Validation(format!(
                        "active shift {shift} belongs to site {actual}, not {site} — \
                         the operating context is inconsistent"
                    )))
                }
                None => {
                    return Err(SenseiError::Validation(format!(
                        "active shift {shift} does not exist in this tenant"
                    )))
                }
            }
        }
        tx.rollback()
            .await
            .map_err(|e| SenseiError::Database(format!("request-context: rollback: {e}")))?;

        Ok(Self {
            tenant,
            principal,
            entitlement_sites,
            active_site,
            active_value_stream,
            active_work_center,
            active_shift,
            trace_id,
        })
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
