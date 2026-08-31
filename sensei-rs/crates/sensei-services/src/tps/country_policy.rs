//! Country policy bundles (fifteenth audit item 84): language, currency,
//! units, week/calendar, holiday schedule, timezone, data residency,
//! retention, employment-data visibility and local document requirements
//! — as POLICY OBJECTS. A new country is a policy RECORD (a migration
//! seed or an upsert), NEVER a code fork: `if country == Morocco`
//! branches in application code are the anti-pattern this module exists
//! to prevent. Fail-closed: an unknown country is a Validation error, not
//! a silent default.

use sensei_core::db::tenant_tx::TenantTx;
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// A country policy bundle — the single source of truth for everything
/// locale-dependent in the tenant.
#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct CountryPolicy {
    pub country: String,
    pub language: String,
    pub currency: String,
    pub unit_system: String,
    pub week_start: String,
    pub holiday_schedule: serde_json::Value,
    pub timezone: String,
    pub data_residency: Option<String>,
    pub retention_days: i32,
    pub employment_data_visibility: String,
    pub local_document_requirements: serde_json::Value,
}

/// Transaction-scoped tenant context for the RLS policy (FAIL-CLOSED:
/// missing context = no rows), same convention as
/// `crates/sensei-services/src/tps/skills.rs`.
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
async fn with_tenant_tx<T, F>(pool: &sqlx::PgPool, tenant_id: Uuid, f: F) -> Result<T>
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

/// Fetch the policy bundle for a country. FAIL-CLOSED: a country without
/// a policy is a Validation error — a new country is a policy RECORD,
/// never a code fork. The lazy seed AND the read run inside ONE
/// [`TenantTx`] (sixteenth audit items 21/83): the seeding INSERT is
/// tenant-admitted by RLS exactly like the SELECT — a raw-pool seed could
/// write rows the tenant context would never see.
pub async fn get_country_policy(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    country: &str,
) -> Result<CountryPolicy> {
    let mut ttx = TenantTx::begin(pool, tenant_id)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin tenant tx: {e}")))?;

    // Lazy per-tenant seeding (same pattern as the field-authority
    // matrix): tenants created AFTER migration 122 still get the
    // canonical operating-country policies.
    sqlx::query(
        "INSERT INTO country_policies (tenant_id, country, language, currency, unit_system, week_start, holiday_schedule, timezone, data_residency, retention_days, employment_data_visibility, local_document_requirements) \
         SELECT $1, v.country, v.language, v.currency, v.unit_system, v.week_start, v.holiday_schedule::jsonb, v.timezone, v.data_residency, v.retention_days, v.employment_data_visibility, v.local_document_requirements::jsonb \
         FROM (VALUES \
            ('Morocco', 'fr', 'MAD', 'metric', 'monday', '[\"new_year\",\"throne_day\",\"green_march\"]', 'Africa/Casablanca', 'ma', 365, 'restricted', '[\"invoice_ar\",\"invoice_fr\"]'), \
            ('Tunisia', 'fr', 'TND', 'metric', 'monday', '[\"new_year\",\"revolution_day\",\"independence_day\"]', 'Africa/Tunis', 'tn', 365, 'restricted', '[\"invoice_fr\"]') \
         ) AS v(country, language, currency, unit_system, week_start, holiday_schedule, timezone, data_residency, retention_days, employment_data_visibility, local_document_requirements) \
         WHERE NOT EXISTS ( \
             SELECT 1 FROM country_policies c WHERE c.tenant_id = $1 AND c.country = v.country \
         )",
    )
    .bind(tenant_id)
    .execute(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("Country policy seed failed: {e}")))?;

    let country = country.to_string();
    let policy = sqlx::query_as::<_, CountryPolicy>(
        "SELECT country, language, currency, unit_system, week_start, \
                holiday_schedule, timezone, data_residency, retention_days, \
                employment_data_visibility, local_document_requirements \
         FROM country_policies WHERE tenant_id = $1 AND country = $2",
    )
    .bind(tenant_id)
    .bind(&country)
    .fetch_optional(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to fetch country policy: {e}")))?
    .ok_or_else(|| {
        SenseiError::Validation(format!(
            "no country policy for {country} — a new country is a policy record, \
             never a code fork"
        ))
    })?;

    ttx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit tenant tx: {e}")))?;
    Ok(policy)
}

/// The locale string derived from a policy bundle (`language-country`),
/// e.g. `fr-Morocco`. Locale decisions read THIS object; nothing in
/// application code branches on the country name.
pub fn locale_for_policy(policy: &CountryPolicy) -> String {
    format!("{}-{}", policy.language, policy.country)
}

/// Upsert a country policy bundle within the tenant's RLS context
/// (idempotent on `(tenant_id, country)`).
pub async fn upsert_country_policy(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    policy: CountryPolicy,
) -> Result<()> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            sqlx::query(
                "INSERT INTO country_policies \
                     (tenant_id, country, language, currency, unit_system, week_start, \
                      holiday_schedule, timezone, data_residency, retention_days, \
                      employment_data_visibility, local_document_requirements) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) \
                 ON CONFLICT (tenant_id, country) DO UPDATE SET \
                     language = EXCLUDED.language, \
                     currency = EXCLUDED.currency, \
                     unit_system = EXCLUDED.unit_system, \
                     week_start = EXCLUDED.week_start, \
                     holiday_schedule = EXCLUDED.holiday_schedule, \
                     timezone = EXCLUDED.timezone, \
                     data_residency = EXCLUDED.data_residency, \
                     retention_days = EXCLUDED.retention_days, \
                     employment_data_visibility = EXCLUDED.employment_data_visibility, \
                     local_document_requirements = EXCLUDED.local_document_requirements, \
                     updated_at = NOW()",
            )
            .bind(tenant_id)
            .bind(&policy.country)
            .bind(&policy.language)
            .bind(&policy.currency)
            .bind(&policy.unit_system)
            .bind(&policy.week_start)
            .bind(policy.holiday_schedule.clone())
            .bind(&policy.timezone)
            .bind(&policy.data_residency)
            .bind(policy.retention_days)
            .bind(&policy.employment_data_visibility)
            .bind(policy.local_document_requirements.clone())
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to upsert country policy: {e}")))?;
            Ok(())
        })
    })
    .await
}
