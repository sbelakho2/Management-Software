//! Attachment parent-resource authorization (twenty-ninth audit Wave B
//! item 11).
//!
//! Attachments inherit their PARENT's authorization: an attachment on a
//! work order, an NCR, an opportunity, an inventory item, an audit-log
//! entry, a knowledge pack (or any other entity-store parent) is only as
//! readable/manageable as the parent itself.
//!
//! * `require_parent_read` — permission + existence (+ site scope where
//!   the parent row carries a site) — runs BEFORE any attachment row is
//!   listed or any blob is presigned/downloaded.
//! * `require_parent_manage` — the manage-side equivalent — runs before
//!   an upload or delete touches the parent's attachments.
//!
//! Unknown parent types fail closed (default `Err`). The canonical
//! per-type permission pairs mirror the ordinary route surfaces (a
//! missing permission for an attachment-surface user = the parent may not
//! be touched through its own API either).

use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::scope::AuthorizedScope;
use sensei_core::error::{Result, SenseiError};
use uuid::Uuid;

use crate::authorization::request_context::build_request_context;
use crate::state::AppState;

/// The attachment parent kind, parsed from a canonical `entity_type`
/// string. Variants carry the parent `entity_id` they were parsed with.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ParentResource {
    /// `work_order` — site derived from its work center
    /// (`work_centers.site_id`).
    WorkOrder(Uuid),
    /// `ncr` — quality nonconformance record.
    Ncr(Uuid),
    /// `opportunity` — sales opportunity (entity-store backed).
    Opportunity(Uuid),
    /// `inventory_item` — inventory row (entity-store backed).
    InventoryItem(Uuid),
    /// `audit_log_entry` (alias `audit_log`) — business audit log.
    AuditLog(Uuid),
    /// `knowledge_pack` — controlled knowledge document.
    KnowledgePack(Uuid),
    /// Any other entity-store-backed attachment host: no site-scoped
    /// domain authorization exists for it — permission + existence only.
    Attachmentless,
}

/// Parse the attachment parent from an `entity_type` string + `entity_id`.
///
/// Entity types that host attachments but have no domain resource of
/// their own (everything in the upload allowlist except the six typed
/// parents above) parse as [`ParentResource::Attachmentless`]. Unknown
/// types fail closed with a [`SenseiError::Validation`] error.
pub fn parse(entity_type: &str, entity_id: Uuid) -> Result<ParentResource> {
    match entity_type {
        "work_order" => Ok(ParentResource::WorkOrder(entity_id)),
        "ncr" => Ok(ParentResource::Ncr(entity_id)),
        "opportunity" => Ok(ParentResource::Opportunity(entity_id)),
        "inventory_item" => Ok(ParentResource::InventoryItem(entity_id)),
        "audit_log_entry" | "audit_log" => Ok(ParentResource::AuditLog(entity_id)),
        "knowledge_pack" => Ok(ParentResource::KnowledgePack(entity_id)),
        _ if is_attachmentless_type(entity_type) => Ok(ParentResource::Attachmentless),
        other => Err(SenseiError::Validation(format!(
            "entity_type '{other}' cannot host attachments (or is not a \
             known attachment parent type)"
        ))),
    }
}

/// Every entity-store type that can host attachments (must mirror the
/// upload allowlist in `routes/attachments.rs`).
fn is_attachmentless_type(entity_type: &str) -> bool {
    ATTACHMENTLESS_TYPES.contains(&entity_type)
}

const ATTACHMENTLESS_TYPES: &[&str] = &[
    "task",
    "kanban_board",
    "notification",
    "notification_preference",
    "quote_version",
    "learning_module",
    "escalation_policy",
    "training_matrix_entry",
    "ingestion_job",
    "work_center",
    "obeya_board",
    "ctq_characteristic",
    "ctq_record",
    "stock_move",
    "warehouse",
    "demand_entry",
    "supply_order",
    "mrp_run",
    "saved_view",
    "work_packet",
    "cost_build",
    "npi_conversion",
    "kpi_definition",
    "kpi_value",
    "lsw_standard",
    "lsw_audit",
    "notification_trigger",
    "standard_work",
    "standard_work_version",
    "state_machine_definition",
    "state_machine_instance",
    "training_course",
    "training_enrollment",
];

// ---------------------------------------------------------------------------
// Canonical (read, manage) permission pairs
// ---------------------------------------------------------------------------

/// Canonical permission pair for the typed parents: `(read, manage)`.
///
/// The manage side is the ordinary mutation surface of the parent's own
/// routes (`production:work-order:update`, `quality:ncr:update`,
/// `sales:opportunity:manage`, `inventory:adjust`, `knowledge:manage`).
/// Audit-log entries are append-only: the audit read permission guards
/// both sides.
fn typed_parent_permissions(parent: ParentResource) -> Option<(&'static str, &'static str)> {
    match parent {
        ParentResource::WorkOrder(_) => {
            Some(("production:work-order:read", "production:work-order:update"))
        }
        ParentResource::Ncr(_) => Some(("quality:ncr:read", "quality:ncr:update")),
        ParentResource::Opportunity(_) => {
            Some(("sales:opportunity:read", "sales:opportunity:manage"))
        }
        ParentResource::InventoryItem(_) => Some(("inventory:read", "inventory:adjust")),
        ParentResource::AuditLog(_) => Some(("system:audit:read", "system:audit:read")),
        ParentResource::KnowledgePack(_) => Some(("knowledge:read", "knowledge:manage")),
        ParentResource::Attachmentless => None,
    }
}

/// Canonical `(read, manage)` pair for an entity-store parent type whose
/// ordinary route surface declares one; `None` when no domain permission
/// exists for the type (self-service surfaces and store-only types) — the
/// attachment permissions themselves are then the only domain gate and
/// existence is still verified.
fn attachmentless_permissions(entity_type: &str) -> Option<(&'static str, &'static str)> {
    match entity_type {
        "task" => Some(("tasks:read", "tasks:manage")),
        "kanban_board" => Some(("tps:kanban:read", "tps:kanban:manage")),
        "obeya_board" => Some(("tps:obeya:read", "tps:obeya:manage")),
        "work_center" => Some(("tps:work-center:read", "tps:work-center:manage")),
        "training_course" => Some(("training:read", "training:manage")),
        "training_matrix_entry" => Some(("tps:training-matrix:read", "tps:training-matrix:manage")),
        "training_enrollment" => Some(("training:read", "training:manage")),
        "learning_module" => Some(("learning:read", "learning:manage")),
        "ctq_characteristic" | "ctq_record" => Some(("tps:ctq:read", "tps:ctq:manage")),
        "kpi_definition" | "kpi_value" => Some(("tps:kpi:read", "tps:kpi:manage")),
        "lsw_standard" | "lsw_audit" => Some(("tps:lsw:execute", "tps:lsw:manage")),
        "notification_trigger" => Some((
            "tps:notification-triggers:manage",
            "tps:notification-triggers:manage",
        )),
        "standard_work" | "standard_work_version" => {
            Some(("tps:standard-work:read", "tps:standard-work:draft"))
        }
        "state_machine_definition" | "state_machine_instance" => {
            Some(("system:state-machines:read", "system:state-machines:manage"))
        }
        "escalation_policy" => Some(("tps:escalation:read", "tps:escalation:manage")),
        "saved_view" => Some(("dashboard:read", "dashboard:read")),
        "warehouse" => Some(("inventory:read", "inventory:warehouse:manage")),
        "stock_move" => Some(("inventory:read", "inventory:move")),
        "notification" => Some(("notifications:read", "notifications:read")),
        "notification_preference" => Some(("dashboard:read", "dashboard:read")),
        _ => None,
    }
}

// ---------------------------------------------------------------------------
// Authorization checks
// ---------------------------------------------------------------------------

/// Require the caller to be able to READ the attachment parent
/// `(entity_type, entity_id)` — permission first, then existence, then
/// (DB deployments) the parent's site scope.
///
/// * A missing/foreign parent or an out-of-scope parent is a
///   [`SenseiError::NotFound`] — indistinguishable from a nonexistent
///   parent, exactly like the scoped repository getters.
/// * Without a database pool (in-memory/dev deployments) there are no
///   site rows to entangle; the typed-parent existence proof is skipped
///   (dev semantics — same convention as `routes/supply_chain.rs`
///   `caller_scope`).
pub async fn require_parent_read(
    state: &AppState,
    user: &AuthenticatedUser,
    entity_type: &str,
    entity_id: Uuid,
) -> Result<()> {
    require_parent(state, user, entity_type, entity_id, false).await
}

/// Require the caller to be able to MANAGE the attachment parent
/// `(entity_type, entity_id)` — permission first, then existence, then
/// (DB deployments) the parent's site scope. Used by upload/delete.
pub async fn require_parent_manage(
    state: &AppState,
    user: &AuthenticatedUser,
    entity_type: &str,
    entity_id: Uuid,
) -> Result<()> {
    require_parent(state, user, entity_type, entity_id, true).await
}

async fn require_parent(
    state: &AppState,
    user: &AuthenticatedUser,
    entity_type: &str,
    entity_id: Uuid,
    manage: bool,
) -> Result<()> {
    let parent = parse(entity_type, entity_id)?;
    require_permission_for_parent(user, parent, entity_type, manage)?;
    proof_parent_access(state, user, parent, entity_type, entity_id).await
}

/// Permission gate: the canonical (read|manage) permission for the
/// parent. Parents without a domain permission are gated only by the
/// attachment surfaces themselves (and existence below).
fn require_permission_for_parent(
    user: &AuthenticatedUser,
    parent: ParentResource,
    entity_type: &str,
    manage: bool,
) -> Result<()> {
    let permissions =
        typed_parent_permissions(parent).or_else(|| attachmentless_permissions(entity_type));
    if let Some((read, manage_perm)) = permissions {
        let required = if manage { manage_perm } else { read };
        user.require_permission(required)
    } else {
        Ok(())
    }
}

/// Existence (+ scope) proof:
///
/// * entity-store parents (`Opportunity`, `InventoryItem`, `AuditLog`,
///   `KnowledgePack`, `Attachmentless`) — verified through the same
///   typed store checker the upload route uses (tenant-scoped existence;
///   the store rows carry no site column, so no site predicate applies);
/// * `Ncr` — DB deployments verify the tenant-scoped `ncr_reports` row
///   directly; dev deployments skip (no pool, no rows);
/// * `WorkOrder` — DB deployments verify the work order AND its work
///   center's site against the caller's authorized scope in one
///   statement (a foreign-site or site-less work order is
///   indistinguishable from a nonexistent one); dev deployments skip.
async fn proof_parent_access(
    state: &AppState,
    user: &AuthenticatedUser,
    parent: ParentResource,
    entity_type: &str,
    entity_id: Uuid,
) -> Result<()> {
    match parent {
        ParentResource::WorkOrder(id) => {
            proof_work_order(state, user, id).await?;
        }
        ParentResource::Ncr(id) => {
            proof_ncr(state, user, id).await?;
        }
        ParentResource::Opportunity(_)
        | ParentResource::InventoryItem(_)
        | ParentResource::AuditLog(_)
        | ParentResource::KnowledgePack(_) => {
            if !crate::routes::attachments::entity_exists(
                state,
                entity_type,
                entity_id,
                user.tenant_id,
            )
            .await
            {
                return Err(SenseiError::NotFound(format!(
                    "{entity_type} {entity_id} does not exist in tenant {}",
                    user.tenant_id
                )));
            }
        }
        ParentResource::Attachmentless => {
            if !crate::routes::attachments::entity_exists(
                state,
                entity_type,
                entity_id,
                user.tenant_id,
            )
            .await
            {
                return Err(SenseiError::NotFound(format!(
                    "{entity_type} {entity_id} does not exist in tenant {}",
                    user.tenant_id
                )));
            }
        }
    }
    Ok(())
}

/// Work-order proof (DB deployments): the row must exist in the caller's
/// tenant AND its work center's site must be inside the caller's
/// authorized sites. Site-less/foreign/unattributable rows and
/// `NoOperationalScope` callers match zero rows → NotFound. Dev
/// deployments (no pool, no sites) skip the proof.
async fn proof_work_order(
    state: &AppState,
    user: &AuthenticatedUser,
    work_order_id: Uuid,
) -> Result<()> {
    let Some(sites) = caller_authorized_sites(state, user).await? else {
        return Ok(());
    };
    let found: Option<Uuid> = sqlx::query_scalar(
        "SELECT wo.id \
         FROM work_orders wo \
         JOIN work_centers wc \
           ON wc.tenant_id = wo.tenant_id AND wc.id = wo.work_center_id \
         WHERE wo.tenant_id = $1 AND wo.id = $2 \
           AND wc.site_id = ANY($3)",
    )
    .bind(user.tenant_id)
    .bind(work_order_id)
    .bind(&sites)
    .fetch_optional(state.db_pool.as_deref().expect("checked above"))
    .await
    .map_err(|e| SenseiError::Database(format!("work-order parent proof failed: {e}")))?;
    if found.is_none() {
        return Err(SenseiError::NotFound(format!(
            "Work order {work_order_id} not found"
        )));
    }
    Ok(())
}

/// NCR proof (DB deployments): tenant-scoped existence on the typed
/// `ncr_reports` row. Dev deployments skip (no pool, no rows).
async fn proof_ncr(state: &AppState, user: &AuthenticatedUser, ncr_id: Uuid) -> Result<()> {
    let Some(pool) = state.db_pool.as_ref() else {
        return Ok(());
    };
    let found: Option<Uuid> =
        sqlx::query_scalar("SELECT id FROM ncr_reports WHERE tenant_id = $1 AND id = $2")
            .bind(user.tenant_id)
            .bind(ncr_id)
            .fetch_optional(&**pool)
            .await
            .map_err(|e| SenseiError::Database(format!("ncr parent proof failed: {e}")))?;
    if found.is_none() {
        return Err(SenseiError::NotFound(format!("NCR {ncr_id} not found")));
    }
    Ok(())
}

/// The caller's authorized operational sites through the ONE shared
/// [`RequestContext`] builder ([`build_request_context`] — the
/// routes/andon.rs `caller_sites` pattern): `None` when no site
/// restriction applies (in-memory/dev mode carries the explicit
/// tenant-wide grant; DB `TenantWide` likewise unrestricted).
async fn caller_authorized_sites(
    state: &AppState,
    user: &AuthenticatedUser,
) -> Result<Option<Vec<Uuid>>> {
    let rc = build_request_context(user, state).await?;
    Ok(match &rc.scope {
        // Explicit all-access grant: no site predicate.
        AuthorizedScope::TenantWide => None,
        // Fail closed: no entitlement → no rows.
        AuthorizedScope::NoOperationalScope => Some(Vec::new()),
        AuthorizedScope::Sites(sites) => Some(sites.clone()),
        AuthorizedScope::WorkCenter(wc) => Some(vec![wc.site]),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_maps_canonical_types() {
        let id = Uuid::new_v4();
        assert_eq!(
            parse("work_order", id).unwrap(),
            ParentResource::WorkOrder(id)
        );
        assert_eq!(parse("ncr", id).unwrap(), ParentResource::Ncr(id));
        assert_eq!(
            parse("opportunity", id).unwrap(),
            ParentResource::Opportunity(id)
        );
        assert_eq!(
            parse("inventory_item", id).unwrap(),
            ParentResource::InventoryItem(id)
        );
        assert_eq!(
            parse("audit_log_entry", id).unwrap(),
            ParentResource::AuditLog(id)
        );
        assert_eq!(
            parse("audit_log", id).unwrap(),
            ParentResource::AuditLog(id)
        );
        assert_eq!(
            parse("knowledge_pack", id).unwrap(),
            ParentResource::KnowledgePack(id)
        );
        assert_eq!(parse("task", id).unwrap(), ParentResource::Attachmentless);
        assert_eq!(
            parse("work_center", id).unwrap(),
            ParentResource::Attachmentless
        );
        assert!(parse("wombat", id).is_err());
        assert!(parse("", id).is_err());
    }

    #[test]
    fn canonical_permission_pairs_exist_for_typed_parents() {
        let id = Uuid::new_v4();
        assert_eq!(
            typed_parent_permissions(ParentResource::WorkOrder(id)),
            Some(("production:work-order:read", "production:work-order:update"))
        );
        assert_eq!(
            typed_parent_permissions(ParentResource::Ncr(id)),
            Some(("quality:ncr:read", "quality:ncr:update"))
        );
        assert_eq!(
            typed_parent_permissions(ParentResource::Opportunity(id)),
            Some(("sales:opportunity:read", "sales:opportunity:manage"))
        );
        assert_eq!(
            typed_parent_permissions(ParentResource::InventoryItem(id)),
            Some(("inventory:read", "inventory:adjust"))
        );
        assert_eq!(
            typed_parent_permissions(ParentResource::KnowledgePack(id)),
            Some(("knowledge:read", "knowledge:manage"))
        );
    }

    #[test]
    fn attachmentless_permissions_cover_the_common_surfaces() {
        for (entity_type, read, manage) in [
            ("task", "tasks:read", "tasks:manage"),
            (
                "work_center",
                "tps:work-center:read",
                "tps:work-center:manage",
            ),
            ("training_course", "training:read", "training:manage"),
            ("lsw_standard", "tps:lsw:execute", "tps:lsw:manage"),
        ] {
            assert_eq!(
                attachmentless_permissions(entity_type),
                Some((read, manage)),
                "{entity_type}"
            );
        }
    }
}
