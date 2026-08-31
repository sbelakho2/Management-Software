//! Versioned metric registry (fifteenth audit 69/70 + A13): every metric
//! is code + a seeded DB definition — the same definition feeds every
//! dashboard, API and AI surface.

use sensei_core::db::tenant_tx::TenantTx;
use sensei_core::error::{Result, SenseiError};
use uuid::Uuid;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, sqlx::FromRow)]
pub struct MetricDefinition {
    pub metric_id: String,
    pub version: i32,
    pub name: String,
    pub purpose: String,
    pub formula: String,
    pub unit: String,
    pub grain: String,
    pub source: String,
    pub owner_role: String,
    /// The audience JSONB column (e.g. `["site_manager","quality"]`).
    pub audience: serde_json::Value,
    pub freshness: String,
    pub anti_gaming: String,
    pub expected_action: String,
    pub active: bool,
}

/// Look up the ACTIVE version of a metric for a tenant — metrics without
/// a registry definition are a CONFIGURATION ERROR (the audit's "no
/// unnamed dashboard SQL" rule): return an explicit error. The read runs
/// through a [`TenantTx`] (sixteenth audit items 21/83): the RLS tenant
/// context is construction-time, never a per-function afterthought.
pub async fn get_metric(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    metric_id: &str,
) -> Result<MetricDefinition> {
    let mut ttx = TenantTx::begin(pool, tenant_id)
        .await
        .map_err(|e| SenseiError::Database(format!("Metric registry read failed: {e}")))?;
    let row: Option<MetricDefinition> = sqlx::query_as(
        "SELECT metric_id, version, name, \
                COALESCE(purpose, '') AS purpose, formula, unit, grain, \
                COALESCE(source, '') AS source, \
                COALESCE(owner_role, '') AS owner_role, \
                COALESCE(audience, '[]')::jsonb AS audience, \
                COALESCE(freshness, 'realtime') AS freshness, \
                COALESCE(anti_gaming, '') AS anti_gaming, \
                COALESCE(expected_action, '') AS expected_action, active \
         FROM metric_definitions \
         WHERE tenant_id = $1 AND metric_id = $2 AND active = TRUE \
         ORDER BY version DESC LIMIT 1",
    )
    .bind(tenant_id)
    .bind(metric_id)
    .fetch_optional(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("Metric registry read failed: {e}")))?;
    ttx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Metric registry read failed: {e}")))?;
    row.ok_or_else(|| {
        SenseiError::Validation(format!(
            "Metric '{metric_id}' is not defined in the versioned metric registry — \
             every metric must have a definition"
        ))
    })
}
