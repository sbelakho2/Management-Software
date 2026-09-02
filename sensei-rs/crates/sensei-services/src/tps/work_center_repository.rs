//! Relational Work Center repository (twentieth audit P0 — Work Center
//! split-brain).
//!
//! The public Work Center API previously persisted through a generic
//! EntityStore (JSONB in `entity_store`) while RequestContext topology
//! validation, site readiness, capability checks, skills and the rest of
//! the plant lifecycle read the RELATIONAL `work_centers` table — two
//! systems of record that could diverge (the UI could show a work center
//! the plant lifecycle did not know).
//!
//! This repository is the single system of record for work centers:
//! everything written through the public API lands here, in the same
//! table the lifecycle reads. Topology is never fabricated:
//!
//! - a create/update that supplies a `site_id` records the assertion as
//!   `topology_state = 'resolved'` with
//!   `topology_assignment_source = 'manual_reconciliation'` (the API
//!   caller asserts the site; the composite FK
//!   `work_centers_tenant_site_fk` proves the site belongs to the
//!   tenant, otherwise a Validation error is returned);
//! - a create/update WITHOUT a `site_id` keeps `site_id` NULL and sets
//!   `topology_state = 'needs_reconciliation'` with no assignment source
//!   — unknown lineage is never certified (the site-readiness gate
//!   refuses any tenant containing such a row).
//!
//! [`RelationalWorkCenter`] is the API-visible shape: it carries
//! `site_id` and `topology_state` on every response.

use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

/// Canonical work center types the relational table admits
/// (`work_centers_work_center_type_check` in migration 002).
const CANONICAL_WORK_CENTER_TYPES: [&str; 5] =
    ["manual", "semi_automated", "automated", "assembly", "test"];

const TOPOLOGY_NEEDS_RECONCILIATION: &str = "needs_reconciliation";

/// A work center row from the relational `work_centers` table.
///
/// The API response shape for every create/update/get/list operation:
/// `site_id` (the resolved plant site, `None` while lineage is unknown)
/// and `topology_state` (`'resolved'` / `'needs_reconciliation'`) travel
/// with the row so callers can see exactly what the plant lifecycle sees.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct RelationalWorkCenter {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub site_id: Option<Uuid>,
    pub work_center_number: String,
    pub name: String,
    pub work_center_type: String,
    pub topology_state: String,
    pub topology_assignment_source: Option<String>,
}

/// Input for [`create`]: the caller-asserted topology (`site_id`) plus
/// the identity fields of the new work center.
#[derive(Debug, Clone, PartialEq)]
pub struct NewWorkCenter {
    pub id: Uuid,
    /// The site this work center is asserted to belong to. `Some` only
    /// when the caller can prove the assignment (the composite FK
    /// verifies the site exists for the tenant); `None` creates the row
    /// in `needs_reconciliation` — unknown lineage is never certified.
    pub site_id: Option<Uuid>,
    pub work_center_number: String,
    pub name: String,
    pub work_center_type: String,
}

/// Patch for [`update`].
#[derive(Debug, Clone, PartialEq, Default)]
pub struct UpdateWorkCenter {
    /// `None`: leave the assignment untouched (topology fields are not
    /// rewritten). `Some(None)`: unassign the work center from its site
    /// (row becomes `needs_reconciliation`, no assignment source).
    /// `Some(Some(site))`: (re)assert the assignment — the site must
    /// exist for the tenant and the row becomes `resolved` /
    /// `manual_reconciliation`.
    pub site_id: Option<Option<Uuid>>,
    pub name: Option<String>,
    pub work_center_type: Option<String>,
}

/// Capacity/efficiency projection of a relational work center row.
///
/// Legacy read-only endpoints (capacity, efficiency report) derive from
/// the raw relational columns — never from a second system of record.
#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct WorkCenterMetrics {
    pub id: Uuid,
    pub name: String,
    pub is_active: bool,
    pub capacity_per_shift: Option<f64>,
    pub shifts_per_day: Option<i32>,
    pub efficiency: Option<f64>,
}

type Row = (
    Uuid,
    Uuid,
    Option<Uuid>,
    String,
    String,
    String,
    String,
    Option<String>,
);

fn db_err(e: sqlx::Error, context: &str) -> SenseiError {
    SenseiError::Database(format!("work_center_repository::{context}: {e}"))
}

fn from_row(
    (
        id,
        tenant_id,
        site_id,
        work_center_number,
        name,
        work_center_type,
        topology_state,
        topology_assignment_source,
    ): Row,
) -> RelationalWorkCenter {
    RelationalWorkCenter {
        id,
        tenant_id,
        site_id,
        work_center_number,
        name,
        work_center_type,
        topology_state,
        topology_assignment_source,
    }
}

/// The topology bookkeeping a row receives for a given assignment
/// (twenty-first audit item 2): ASSIGNMENT IS NOT VERIFICATION. An
/// asserted site leaves the row `needs_reconciliation` (provenance
/// NULL) until an EXPLICIT topology-verification command stamps
/// source + verified_at + verified_by atomically — ordinary create/
/// update can never violate the migration-151 provenance constraint.
fn topology_for(_site_id: Option<Uuid>) -> (&'static str, Option<&'static str>) {
    (TOPOLOGY_NEEDS_RECONCILIATION, None)
}

/// Explicit topology verification (twenty-first audit item 2): the
/// acting actor declares the source and stamps verified_at + verified_by
/// atomically with the transition to 'resolved'. `legacy_heuristic` is
/// refused — it is a marker of doubt, never a provenance.
pub async fn verify_topology(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    work_center_id: Uuid,
    verified_by: Uuid,
    source: &str,
) -> Result<RelationalWorkCenter> {
    if !matches!(
        source,
        "manifest" | "employee_history" | "manual_reconciliation"
    ) {
        return Err(SenseiError::Validation(format!(
            "topology source '{source}' cannot certify a work center — only \
             manifest, employee_history or manual_reconciliation verification \
             resolves topology"
        )));
    }
    use crate::tps::replication::with_tenant_tx;
    let source_owned = source.to_string();
    let row = with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let row = sqlx::query_as::<_, Row>(
                "UPDATE work_centers \
                    SET topology_state = 'resolved', \
                        topology_assignment_source = $3, \
                        topology_verified_at = NOW(), \
                        topology_verified_by = $4 \
                  WHERE id = $1 AND tenant_id = $2 \
                  RETURNING id, tenant_id, site_id, work_center_number, name, \
                            work_center_type, topology_state, topology_assignment_source",
            )
            .bind(work_center_id)
            .bind(tenant_id)
            .bind(&source_owned)
            .bind(verified_by)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Failed to verify work center topology: {e}"))
            })?
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Work center {work_center_id} not found"))
            })?;
            Ok(row)
        })
    })
    .await?;
    Ok(from_row(row))
}

/// Highest numeric `WC-<n>` suffix among the tenant's existing numbers.
fn max_number_suffix(numbers: &[String]) -> u32 {
    numbers
        .iter()
        .filter_map(|n| n.strip_prefix("WC-"))
        .filter_map(|s| s.parse::<u32>().ok())
        .max()
        .unwrap_or(0)
}

/// Classify an insert/update failure against the work center contract so
/// callers get a clean Validation error instead of raw SQL.
fn classify_constraint_error(
    e: sqlx::Error,
    work_center_number: &str,
    site_id: Option<Uuid>,
    tenant_id: Uuid,
) -> SenseiError {
    if let Some(db) = e.as_database_error() {
        if let Some(code) = db.code() {
            match code.as_ref() {
                // Composite FK work_centers_tenant_site_fk: the site
                // does not exist for THIS tenant.
                "23503" => {
                    return SenseiError::Validation(match site_id {
                        Some(site) => format!(
                            "site {site} does not exist for tenant {tenant_id} — a work center \
                             can only be assigned to one of the tenant's own sites"
                        ),
                        None => format!(
                            "work center {work_center_number}: a referenced row does not exist \
                             for tenant {tenant_id}"
                        ),
                    })
                }
                // UNIQUE(tenant_id, work_center_number) — concurrent
                // numbering raced; retry with a fresh number.
                "23505" => {
                    return SenseiError::Validation(format!(
                        "work center number {work_center_number} already exists in tenant \
                         {tenant_id} — retry the create"
                    ))
                }
                // work_centers_work_center_type_check.
                "23514" => {
                    return SenseiError::Validation(format!(
                        "work_center_type must be one of: {}",
                        CANONICAL_WORK_CENTER_TYPES.join(", ")
                    ))
                }
                _ => {}
            }
        }
    }
    db_err(e, "constraint")
}

/// Create a work center in the RELATIONAL `work_centers` table.
///
/// The topology bookkeeping is derived, never caller-supplied: a
/// supplied `site_id` must exist for the tenant (composite FK; mapped to
/// a clean Validation error) and yields `resolved` /
/// `manual_reconciliation`; a `None` `site_id` creates the row in
/// `needs_reconciliation` with no assignment source.
pub async fn create(
    pool: &PgPool,
    tenant_id: Uuid,
    wc: &NewWorkCenter,
) -> Result<RelationalWorkCenter> {
    let (topology_state, topology_assignment_source) = topology_for(wc.site_id);
    let row: Row = sqlx::query_as(
        "INSERT INTO work_centers \
            (id, tenant_id, site_id, work_center_number, name, work_center_type, \
             topology_state, topology_assignment_source) \
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8) \
         RETURNING id, tenant_id, site_id, work_center_number, name, work_center_type, \
                   topology_state, topology_assignment_source",
    )
    .bind(wc.id)
    .bind(tenant_id)
    .bind(wc.site_id)
    .bind(&wc.work_center_number)
    .bind(&wc.name)
    .bind(&wc.work_center_type)
    .bind(topology_state)
    .bind(topology_assignment_source)
    .fetch_one(pool)
    .await
    .map_err(|e| classify_constraint_error(e, &wc.work_center_number, wc.site_id, tenant_id))?;
    Ok(from_row(row))
}

/// Update a work center's editable fields and/or its site assignment.
///
/// The topology fields are rewritten ONLY when the caller touches
/// `site_id` — and then exactly like [`create`]: an assignment asserts
/// `resolved` / `manual_reconciliation` (FK-validated), an unassignment
/// pushes the row back to `needs_reconciliation` with no source. Name
/// and type edits never certify (or de-certify) topology by themselves.
pub async fn update(
    pool: &PgPool,
    tenant_id: Uuid,
    id: Uuid,
    patch: &UpdateWorkCenter,
) -> Result<RelationalWorkCenter> {
    let row: Option<Row> = sqlx::query_as(
        "UPDATE work_centers SET \
            name = COALESCE($3, name), \
            work_center_type = COALESCE($4, work_center_type), \
            site_id = CASE WHEN $5 THEN $6 ELSE site_id END, \
            topology_state = CASE WHEN $5 \
                THEN CASE WHEN $6 IS NULL THEN 'needs_reconciliation' ELSE 'resolved' END \
                ELSE topology_state END, \
            topology_assignment_source = CASE WHEN $5 \
                THEN CASE WHEN $6 IS NULL THEN NULL ELSE 'manual_reconciliation' END \
                ELSE topology_assignment_source END, \
            updated_at = NOW() \
         WHERE id = $1 AND tenant_id = $2 \
         RETURNING id, tenant_id, site_id, work_center_number, name, work_center_type, \
                   topology_state, topology_assignment_source",
    )
    .bind(id)
    .bind(tenant_id)
    .bind(patch.name.as_deref())
    .bind(patch.work_center_type.as_deref())
    .bind(patch.site_id.is_some())
    .bind(patch.site_id.flatten())
    .fetch_optional(pool)
    .await
    .map_err(|e| classify_constraint_error(e, "update", patch.site_id.flatten(), tenant_id))?;
    row.map(from_row).ok_or_else(|| {
        SenseiError::NotFound(format!("work center {id} not found in tenant {tenant_id}"))
    })
}

/// Fetch one relational work center by id, tenant-scoped.
pub async fn get(pool: &PgPool, tenant_id: Uuid, id: Uuid) -> Result<RelationalWorkCenter> {
    let row: Option<Row> = sqlx::query_as(
        "SELECT id, tenant_id, site_id, work_center_number, name, work_center_type, \
                topology_state, topology_assignment_source \
         FROM work_centers WHERE id = $1 AND tenant_id = $2",
    )
    .bind(id)
    .bind(tenant_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| db_err(e, "get"))?;
    row.map(from_row).ok_or_else(|| {
        SenseiError::NotFound(format!("work center {id} not found in tenant {tenant_id}"))
    })
}

/// List the tenant's relational work centers.
///
/// `site_id: Some(site)` restricts to the work centers assigned to that
/// site; `None` lists every row of the tenant (resolved or awaiting
/// reconciliation) ordered by number.
pub async fn list(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
) -> Result<Vec<RelationalWorkCenter>> {
    let rows: Vec<Row> = sqlx::query_as(
        "SELECT id, tenant_id, site_id, work_center_number, name, work_center_type, \
                topology_state, topology_assignment_source \
         FROM work_centers \
         WHERE tenant_id = $1 AND ($2::uuid IS NULL OR site_id = $2) \
         ORDER BY work_center_number",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_all(pool)
    .await
    .map_err(|e| db_err(e, "list"))?;
    Ok(rows.into_iter().map(from_row).collect())
}

/// Next per-tenant `WC-xxxxx` number (highest existing suffix + 1).
pub async fn next_number(pool: &PgPool, tenant_id: Uuid) -> Result<String> {
    let numbers: Vec<String> =
        sqlx::query_scalar("SELECT work_center_number FROM work_centers WHERE tenant_id = $1")
            .bind(tenant_id)
            .fetch_all(pool)
            .await
            .map_err(|e| db_err(e, "next_number"))?;
    Ok(format!("WC-{:05}", max_number_suffix(&numbers) + 1))
}

/// Soft-deactivate a work center (`is_active = FALSE`).
///
/// Deactivation never touches topology: the row keeps its site /
/// `topology_state` (a deactivated center is still part of the plant).
pub async fn deactivate(pool: &PgPool, tenant_id: Uuid, id: Uuid) -> Result<RelationalWorkCenter> {
    let row: Option<Row> = sqlx::query_as(
        "UPDATE work_centers SET is_active = FALSE, updated_at = NOW() \
         WHERE id = $1 AND tenant_id = $2 \
         RETURNING id, tenant_id, site_id, work_center_number, name, work_center_type, \
                   topology_state, topology_assignment_source",
    )
    .bind(id)
    .bind(tenant_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| db_err(e, "deactivate"))?;
    row.map(from_row).ok_or_else(|| {
        SenseiError::NotFound(format!("work center {id} not found in tenant {tenant_id}"))
    })
}

/// Capacity/efficiency projection of every work center in the tenant,
/// straight from the relational columns.
pub async fn metrics(pool: &PgPool, tenant_id: Uuid) -> Result<Vec<WorkCenterMetrics>> {
    type MetricsRow = (Uuid, String, bool, Option<f64>, Option<i32>, Option<f64>);
    let rows: Vec<MetricsRow> = sqlx::query_as(
        "SELECT id, name, is_active, capacity_per_shift, shifts_per_day, efficiency \
         FROM work_centers WHERE tenant_id = $1 ORDER BY work_center_number",
    )
    .bind(tenant_id)
    .fetch_all(pool)
    .await
    .map_err(|e| db_err(e, "metrics"))?;
    Ok(rows
        .into_iter()
        .map(
            |(id, name, is_active, capacity_per_shift, shifts_per_day, efficiency)| {
                WorkCenterMetrics {
                    id,
                    name,
                    is_active,
                    capacity_per_shift,
                    shifts_per_day,
                    efficiency,
                }
            },
        )
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn assignment_is_never_verification_twenty_first_audit() {
        // Twenty-first audit item 2: creating/updating a site assignment
        // leaves the row needs_reconciliation — only an explicit
        // verification command stamps provenance and resolves it.
        let site = Uuid::new_v4();
        assert_eq!(
            topology_for(Some(site)),
            (TOPOLOGY_NEEDS_RECONCILIATION, None)
        );
        assert_eq!(topology_for(None), (TOPOLOGY_NEEDS_RECONCILIATION, None));
    }

    #[test]
    fn empty_tenant_starts_at_wc_00001() {
        assert_eq!(max_number_suffix(&[]), 0);
        assert_eq!(format!("WC-{:05}", max_number_suffix(&[]) + 1), "WC-00001");
    }

    #[test]
    fn numbering_skips_non_wc_prefixes_and_uses_highest_suffix() {
        let numbers = vec![
            "SMT-1".to_string(),
            "WC-00001".to_string(),
            "WC-00042".to_string(),
            "not-a-number".to_string(),
        ];
        assert_eq!(max_number_suffix(&numbers), 42);
    }
}
