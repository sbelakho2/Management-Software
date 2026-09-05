//! REGISTERED target-side projectors (thirtieth audit item 25): the real
//! projector implementations behind the federation inbox state machine.
//! [`super::replication::apply_target_projection`] refuses to move an
//! inbox row out of 'received' unless a projector is registered here for
//! the queue row's entity type — the entity type is the subject's object
//! type of the canonical source event (the enqueue path derives it
//! exclusively from `operational_event_objects`, never from a client).
//!
//! Every registered projector applies the projection as a durable
//! business write into the TARGET tenant's existing canonical event store
//! (`operational_events` + `operational_event_objects`, migration 113 +
//! 130 — the same relational store the target's process mining,
//! organizational memory, metric engine and corporate analytics read), so
//! a federated site projection genuinely lands where the target consumes
//! it. The write is idempotent at the STORE level: the migration-130
//! unique `(tenant_id, source_system, source_id)` index makes a repeated
//! mirror insert a no-op, so even a projector body invoked twice applies
//! the business projection once — on top of the inbox receipt dedupe the
//! apply path already guarantees.
//!
//! Each projector row records its source provenance (`source_system =
//! 'federation'`, `source_id` = the source event id, the full envelope +
//! `federation_provenance` in the payload) so the mirrored event is an
//! auditable copy of the source projection — never a re-stamped original.
//! The mirror deliberately does NOT copy `scope_site_id`: the scope site
//! belongs to the SOURCE tenant's slice, and writing a foreign site id
//! into the target's event store would pollute the target's site-scoped
//! analytics. The source site identity is preserved inside
//! `federation_provenance.source_site_id` instead.

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sensei_core::error::{Result, SenseiError};
use sqlx::Postgres;
use uuid::Uuid;

use super::replication::{DataPolicy, ReplicationEntry};

/// The target-projector contract: one registration per entity type (the
/// subject's object type of the canonical events the federation carries).
/// The body runs INSIDE the apply transaction, under the TARGET tenant's
/// context, so its business writes commit (or roll back) together with
/// the inbox state transition and the receipt binding. A body error
/// leaves the inbox row 'reconcile_required' (the apply path records the
/// failure) — an application that did not land is never recorded as
/// 'applied'.
#[async_trait]
pub trait TargetProjector: Send + Sync {
    /// The registered entity type (the queue row's `entity_type`).
    fn entity_type(&self) -> &'static str;
    /// Apply the projection to the target's relational store.
    async fn apply(
        &self,
        tx: &mut sqlx::Transaction<'_, Postgres>,
        target_tenant_id: Uuid,
        source_tenant_id: Uuid,
        entry: &ReplicationEntry,
    ) -> Result<()>;
}

/// The canonical-event mirror projector: materializes the received
/// projection into the target tenant's canonical event store. One
/// registration per entity type the federation carries; the event store
/// dedupe key (`source_system` = 'federation', `source_id` = the source
/// event id) makes the mirror apply idempotent per source event.
struct CanonicalEventMirrorProjector {
    entity_type: &'static str,
}

/// The registered andon mirror — the production-proven canonical stream
/// (every andon aggregate transition writes an `andon.*` operational
/// event at the source; corporate receiving these events is what the
/// federation was built for: cross-site andon flows in the target's
/// process mining / organizational memory).
static ANDON_MIRROR: CanonicalEventMirrorProjector = CanonicalEventMirrorProjector {
    entity_type: "andon",
};

/// The registered work-order mirror — the canonical production stream
/// (`production.work-order.*` / `production.order.*` events whose subject
/// object type is `work_order`).
static WORK_ORDER_MIRROR: CanonicalEventMirrorProjector = CanonicalEventMirrorProjector {
    entity_type: "work_order",
};

/// Resolve the REGISTERED projector for an entity type — the allowlist
/// that replaced the empty `REGISTERED_TARGET_PROJECTORS` of the
/// twenty-sixth/twenty-seventh audits. A registration is only ever added
/// together with its implemented body: an entity type with no projector
/// here is refused by [`super::replication::apply_target_projection`]
/// (never silently claimed as applied).
pub(crate) fn registered_target_projector(
    entity_type: &str,
) -> Option<&'static dyn TargetProjector> {
    match entity_type {
        "andon" => Some(&ANDON_MIRROR),
        "work_order" => Some(&WORK_ORDER_MIRROR),
        _ => None,
    }
}

#[async_trait]
impl TargetProjector for CanonicalEventMirrorProjector {
    fn entity_type(&self) -> &'static str {
        self.entity_type
    }

    async fn apply(
        &self,
        tx: &mut sqlx::Transaction<'_, Postgres>,
        target_tenant_id: Uuid,
        source_tenant_id: Uuid,
        entry: &ReplicationEntry,
    ) -> Result<()> {
        let source_event_id = entry
            .source_event_id
            .as_deref()
            .and_then(|e| Uuid::parse_str(e).ok())
            .ok_or_else(|| {
                SenseiError::Validation(
                    "projector: the entry carries no UUID source_event_id — a mirror without \
                     a source event identity would be unauditable and is refused"
                        .to_string(),
                )
            })?;
        let entity_id = entry.entity_id.ok_or_else(|| {
            SenseiError::Validation(
                "projector: the entry carries no entity_id — the mirror binds the subject \
                 identity, and a projection without one is refused"
                    .to_string(),
            )
        })?;
        let projection_type = if entry.projection_type.is_empty() {
            entry.entity_type.clone()
        } else {
            entry.projection_type.clone()
        };
        // occurred_at: the envelope timestamp when present (server-built
        // by authorize_projection), otherwise the delivery time — never a
        // guess at the event's own clock.
        let occurred_at: DateTime<Utc> = entry
            .projection
            .get("occurred_at")
            .and_then(|v| v.as_str())
            .and_then(|s| DateTime::parse_from_rfc3339(s).ok())
            .map(|dt| dt.with_timezone(&Utc))
            .unwrap_or_else(Utc::now);
        let sensitivity = DataPolicy::parse(&entry.data_policy)
            .map(|p| p.as_str().to_string())
            .unwrap_or_else(|_| "internal".to_string());
        // The mirrored payload is the full server-built envelope plus the
        // federation provenance (source tenant/queue/site + event). The
        // source event is never re-stamped as a target-originated one.
        let mut mirrored_payload = entry.projection.clone();
        if let serde_json::Value::Object(ref mut map) = mirrored_payload {
            map.insert(
                "federation_provenance".to_string(),
                serde_json::json!({
                    "source_tenant_id": source_tenant_id,
                    "source_queue_id": entry.id,
                    "source_site_id": entry.site_id,
                    "source_event_id": source_event_id,
                }),
            );
        }
        let objects = serde_json::json!([
            { "object_type": self.entity_type, "object_id": entity_id, "role": "subject" }
        ]);
        let mirror_id = Uuid::new_v4();
        let idempotency_key = format!("fed:{source_event_id}:{projection_type}");
        // INSERT ... ON CONFLICT DO NOTHING on the migration-130 unique
        // (tenant_id, source_system, source_id): a mirror that already
        // exists (a previous apply of the same source event) is a no-op
        // returning no row — the projector is idempotent at the store
        // level, so duplicate delivery can never double-apply.
        let inserted: Option<(Uuid,)> = sqlx::query_as(
            "INSERT INTO operational_events \
                 (id, tenant_id, event_type, occurred_at, recorded_at, scope_site_id, \
                  actor_id, objects, source_system, source_id, sensitivity, payload, \
                  sequence, event_schema_version, idempotency_key) \
             VALUES ($1, $2, $3, $4, NOW(), NULL, NULL, $5, 'federation', $6, $7, $8, 1, 1, $9) \
             ON CONFLICT (tenant_id, source_system, source_id) \
             WHERE source_system IS NOT NULL AND source_id IS NOT NULL \
             DO NOTHING \
             RETURNING id",
        )
        .bind(mirror_id)
        .bind(target_tenant_id)
        .bind(&projection_type)
        .bind(occurred_at)
        .bind(objects)
        .bind(source_event_id.to_string())
        .bind(&sensitivity)
        .bind(mirrored_payload)
        .bind(&idempotency_key)
        .fetch_optional(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("replication: mirror event: {e}")))?;
        let Some((event_id,)) = inserted else {
            // The store already holds this source event's mirror — the
            // projection was applied by an earlier (committed) apply.
            return Ok(());
        };
        // The relational object projection of the mirrored event: one
        // subject row per mirror (the operational_event_objects rows only
        // exist when the event row was newly inserted — a re-insert would
        // double the links).
        sqlx::query(
            "INSERT INTO operational_event_objects \
                 (tenant_id, event_id, object_type, object_id, role) \
             SELECT $1, $2, x.object_type, x.object_id, x.role \
             FROM jsonb_to_recordset($3::jsonb) \
                  AS x(object_type text, object_id uuid, role text)",
        )
        .bind(target_tenant_id)
        .bind(event_id)
        .bind(serde_json::json!([
            { "object_type": self.entity_type, "object_id": entity_id, "role": "subject" }
        ]))
        .execute(&mut **tx)
        .await
        .map_err(|e| {
            SenseiError::Database(format!("replication: mirror object projection: {e}"))
        })?;
        Ok(())
    }
}
