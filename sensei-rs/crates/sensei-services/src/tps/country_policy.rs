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

/// Publish a NEW revision of a country policy (sixteenth audit item 65):
/// policy is EFFECTIVE-DATED. The revision is MAX(revision)+1 for the
/// country, `valid_from` is NOW(), and the previously-latest OPEN version
/// is closed (`valid_until = NOW()`). The current `country_policies` row
/// is NOT the compliance record — the versioned rows are.
pub async fn publish_policy_version(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    policy: CountryPolicy,
    approved_by: Option<Uuid>,
) -> Result<()> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            // SERIALIZED revision allocation (seventeenth audit item 10):
            // a transaction-scoped advisory lock per (tenant, country)
            // makes concurrent MAX(revision)+1 writers impossible — two
            // publishers cannot select the same next revision.
            sqlx::query("SELECT pg_advisory_xact_lock(hashtext($1 || ':' || $2))")
                .bind(tenant_id.to_string())
                .bind(&policy.country)
                .execute(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Failed to lock policy revision: {e}"))
                })?;

            // Close the previously-latest open version (valid_until IS NULL).
            sqlx::query(
                "UPDATE country_policy_versions SET valid_until = NOW() \
                 WHERE tenant_id = $1 AND country = $2 AND valid_until IS NULL",
            )
            .bind(tenant_id)
            .bind(&policy.country)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to close policy version: {e}")))?;

            let revision = sqlx::query_scalar::<_, i64>(
                "SELECT COALESCE(MAX(revision), 0) + 1 FROM country_policy_versions \
                 WHERE tenant_id = $1 AND country = $2",
            )
            .bind(tenant_id)
            .bind(&policy.country)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to read policy revision: {e}")))?;

            sqlx::query(
                "INSERT INTO country_policy_versions \
                     (tenant_id, country, revision, valid_from, language, currency, \
                      unit_system, week_start, holiday_schedule, timezone, data_residency, \
                      retention_days, employment_data_visibility, local_document_requirements, \
                      approved_by) \
                 VALUES ($1, $2, $3, NOW(), $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)",
            )
            .bind(tenant_id)
            .bind(&policy.country)
            .bind(revision)
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
            .bind(approved_by)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to publish policy version: {e}")))?;
            // Seventeenth audit item 5: the policy revision bump is IN
            // the publish transaction — a policy change without a
            // revision change is impossible.
            super::authorization_revisions::bump_in_tx(tx, tenant_id, "policy_revision").await?;
            Ok(())
        })
    })
    .await
}

/// The policy version governing the country AT a timestamp (sixteenth
/// audit item 65): `valid_from <= at AND (valid_until IS NULL OR
/// valid_until > at)`. Historical reporting — "what policy governed this
/// employee/event in March 2027?" — answers with THIS function, never
/// with the current `country_policies` row.
pub async fn policy_governing(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    country: &str,
    at: chrono::DateTime<chrono::Utc>,
) -> Result<Option<CountryPolicy>> {
    let country = country.to_string();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let policy = sqlx::query_as::<_, CountryPolicy>(
                "SELECT country, language, currency, unit_system, week_start, \
                        holiday_schedule, timezone, data_residency, retention_days, \
                        employment_data_visibility, local_document_requirements \
                 FROM country_policy_versions \
                 WHERE tenant_id = $1 AND country = $2 \
                   AND valid_from <= $3 AND (valid_until IS NULL OR valid_until > $3) \
                 ORDER BY valid_from DESC LIMIT 1",
            )
            .bind(tenant_id)
            .bind(&country)
            .bind(at)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to read governing policy: {e}")))?;
            Ok(policy)
        })
    })
    .await
}

/// The holiday dates for a jurisdiction within `from..=to`, each with the
/// LATEST revision's name (sixteenth audit item 66): Morocco's calendar is
/// not a forever-static list — a date's holiday can be re-versioned.
pub async fn holidays_in(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    jurisdiction: &str,
    from: chrono::NaiveDate,
    to: chrono::NaiveDate,
) -> Result<Vec<(chrono::NaiveDate, String)>> {
    let jurisdiction = jurisdiction.to_string();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let rows = sqlx::query_as::<_, (chrono::NaiveDate, String)>(
                "SELECT holiday_date, name FROM jurisdiction_holidays \
                 WHERE tenant_id = $1 AND jurisdiction = $2 \
                   AND holiday_date BETWEEN $3 AND $4 \
                   AND revision = ( \
                       SELECT MAX(revision) FROM jurisdiction_holidays h \
                       WHERE h.tenant_id = jurisdiction_holidays.tenant_id \
                         AND h.jurisdiction = jurisdiction_holidays.jurisdiction \
                         AND h.holiday_date = jurisdiction_holidays.holiday_date \
                   ) \
                 ORDER BY holiday_date",
            )
            .bind(tenant_id)
            .bind(jurisdiction)
            .bind(from)
            .bind(to)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to read holidays: {e}")))?;
            Ok(rows)
        })
    })
    .await
}

/// Record a holiday for a jurisdiction (sixteenth audit item 66):
/// tenant-scoped insert with revision = MAX(revision)+1 for the date — a
/// second call for the same date creates a NEW revision (the calendar
/// evolves), never an in-place mutation.
pub async fn add_holiday(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    jurisdiction: &str,
    date: chrono::NaiveDate,
    name: &str,
) -> Result<()> {
    let jurisdiction = jurisdiction.to_string();
    let name = name.to_string();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            // Seventeenth audit item 10: advisory lock per
            // (tenant, jurisdiction, date) — no concurrent same-revision
            // holidays.
            sqlx::query("SELECT pg_advisory_xact_lock(hashtext($1 || ':' || $2 || ':' || $3))")
                .bind(tenant_id.to_string())
                .bind(&jurisdiction)
                .bind(date.to_string())
                .execute(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Holiday lock failed: {e}")))?;
            let revision = sqlx::query_scalar::<_, i64>(
                "SELECT COALESCE(MAX(revision), 0) + 1 FROM jurisdiction_holidays \
                 WHERE tenant_id = $1 AND jurisdiction = $2 AND holiday_date = $3",
            )
            .bind(tenant_id)
            .bind(&jurisdiction)
            .bind(date)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to read holiday revision: {e}")))?;

            sqlx::query(
                "INSERT INTO jurisdiction_holidays \
                     (tenant_id, jurisdiction, holiday_date, name, revision) \
                 VALUES ($1, $2, $3, $4, $5)",
            )
            .bind(tenant_id)
            .bind(jurisdiction)
            .bind(date)
            .bind(name)
            .bind(revision)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to add holiday: {e}")))?;
            Ok(())
        })
    })
    .await
}
