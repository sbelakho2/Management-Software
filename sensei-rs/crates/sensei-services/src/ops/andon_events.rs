//! Canonical Andon stream events (seventeenth audit item 11): EVERY Andon
//! aggregate transition appends a canonical operational event in the SAME
//! transaction as the transition — acknowledged / escalated /
//! restart_authorized / resolved / voided — so the process miner's
//! expected Andon path is reconstructible from the canonical log alone.
//! The stream is 'andon' with stream_id = the andon id and a
//! deterministic idempotency key per (andon, event_type): a retried
//! transition can never duplicate an event.

use chrono::Utc;
use sqlx::Postgres;
use uuid::Uuid;

use sensei_core::error::{Result, SenseiError};

#[allow(clippy::too_many_arguments)]
pub async fn write_andon_stream_event(
    tx: &mut sqlx::Transaction<'_, Postgres>,
    tenant_id: Uuid,
    event_type: &str,
    andon_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Uuid,
    actor_id: Uuid,
    occurred_at: chrono::DateTime<Utc>,
    payload: serde_json::Value,
) -> Result<()> {
    let event_id = Uuid::new_v4();
    let objects = serde_json::json!([
        { "object_type": "andon", "object_id": andon_id, "role": "subject" },
        {
            "object_type": "work_center",
            "object_id": work_center_id,
            "role": "scope",
        },
    ]);
    sqlx::query(
        "INSERT INTO operational_events \
             (id, tenant_id, event_type, occurred_at, recorded_at, scope_site_id, actor_id, \
              objects, source_system, source_id, sensitivity, payload, sequence, \
              event_schema_version, stream_type, stream_id, stream_sequence, idempotency_key) \
         VALUES ($1, $2, $3, $4, NOW(), $5, $6, $7, 'starz_forge', NULL, 'internal', $8, 1, \
                 1, 'andon', $9, 1, $10)",
    )
    .bind(event_id)
    .bind(tenant_id)
    .bind(event_type)
    .bind(occurred_at)
    .bind(site_id)
    .bind(actor_id)
    .bind(objects.clone())
    .bind(payload)
    .bind(andon_id)
    .bind(format!("{andon_id}:{event_type}"))
    .execute(&mut **tx)
    .await
    .map_err(|e| {
        SenseiError::Database(format!(
            "Failed to write andon stream event '{event_type}': {e}"
        ))
    })?;

    sqlx::query(
        "INSERT INTO operational_event_objects \
             (tenant_id, event_id, object_type, object_id, role) \
         SELECT $1, $2, x.object_type, x.object_id, x.role \
         FROM jsonb_to_recordset($3::jsonb) \
              AS x(object_type text, object_id uuid, role text)",
    )
    .bind(tenant_id)
    .bind(event_id)
    .bind(objects)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to write andon object projection: {e}")))?;
    Ok(())
}

/// Site/work-center scope of an andon for the event envelope.
#[derive(Debug, Clone)]
pub struct AndonEventScope {
    pub andon_id: Uuid,
    pub site_id: Option<Uuid>,
    pub work_center_id: Uuid,
    pub actor_id: Uuid,
    pub occurred_at: chrono::DateTime<Utc>,
}
