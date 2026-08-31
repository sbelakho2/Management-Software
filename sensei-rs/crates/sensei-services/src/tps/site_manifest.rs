//! Declarative SITE MANIFEST (fifteenth audit 83/93/A17): a new plant comes
//! onto Starz Forge WITHOUT modifying core domain code — the manifest IS the
//! configuration. Country, timezone, languages, currency, capabilities,
//! integrations and the policy bundle are RECORDS, not code; the only domain
//! reference is `site_id`. `bootstrap_site` makes the site operational by
//! seeding the canonical metric definitions in the SAME transaction —
//! "site operational after records, not code".

use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

/// Declarative per-site configuration record.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SiteManifest {
    pub site_id: Uuid,
    pub country: String,
    pub timezone: String,
    pub languages: Vec<String>,
    pub currency: String,
    pub capabilities: Vec<String>,
    pub integrations: Vec<serde_json::Value>,
    pub policy_bundle: Option<String>,
}

/// Transaction-scoped tenant context for RLS (SET LOCAL app.tenant_id) —
/// same convention as `crates/sensei-services/src/ops/database.rs`.
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> std::result::Result<(), SenseiError> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
}

/// Run `f` inside a transaction with the RLS tenant context set — the
/// `site_manifests` policy is FAIL-CLOSED (missing context = no rows).
async fn with_tenant_tx<T, F>(pool: &PgPool, tenant_id: Uuid, f: F) -> Result<T>
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

/// A manifest must name a country, a timezone and at least one capability —
/// anything less is a configuration error, not a valid plant.
fn validate(manifest: &SiteManifest) -> Result<()> {
    if manifest.country.trim().is_empty() {
        return Err(SenseiError::Validation(
            "Site manifest country must be non-empty".to_string(),
        ));
    }
    if manifest.timezone.trim().is_empty() {
        return Err(SenseiError::Validation(
            "Site manifest timezone must be non-empty".to_string(),
        ));
    }
    if manifest.capabilities.is_empty() {
        return Err(SenseiError::Validation(
            "Site manifest capabilities must be non-empty".to_string(),
        ));
    }
    Ok(())
}

/// Upsert the declarative manifest for one site of a tenant. Idempotent:
/// re-bootstrapping a site refreshes its records and bumps
/// `manifest_version` instead of failing.
pub async fn upsert_manifest(pool: &PgPool, tenant_id: Uuid, manifest: SiteManifest) -> Result<()> {
    validate(&manifest)?;
    let languages = serde_json::to_value(&manifest.languages)
        .map_err(|e| SenseiError::Validation(format!("Invalid languages JSON: {e}")))?;
    let capabilities = serde_json::to_value(&manifest.capabilities)
        .map_err(|e| SenseiError::Validation(format!("Invalid capabilities JSON: {e}")))?;
    let integrations = serde_json::to_value(&manifest.integrations)
        .map_err(|e| SenseiError::Validation(format!("Invalid integrations JSON: {e}")))?;
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            sqlx::query(
                r#"INSERT INTO site_manifests
                       (tenant_id, site_id, country, timezone, languages, currency,
                        capabilities, integrations, policy_bundle, manifest_version)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 1)
                   ON CONFLICT (tenant_id, site_id) DO UPDATE SET
                       country = EXCLUDED.country,
                       timezone = EXCLUDED.timezone,
                       languages = EXCLUDED.languages,
                       currency = EXCLUDED.currency,
                       capabilities = EXCLUDED.capabilities,
                       integrations = EXCLUDED.integrations,
                       policy_bundle = EXCLUDED.policy_bundle,
                       manifest_version = site_manifests.manifest_version + 1,
                       updated_at = NOW()"#,
            )
            .bind(tenant_id)
            .bind(manifest.site_id)
            .bind(&manifest.country)
            .bind(&manifest.timezone)
            .bind(&languages)
            .bind(&manifest.currency)
            .bind(&capabilities)
            .bind(&integrations)
            .bind(&manifest.policy_bundle)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Site manifest upsert failed: {e}")))?;
            Ok(())
        })
    })
    .await
}

/// Read the declarative manifest for one site, if it has been bootstrapped.
pub async fn get_manifest(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Uuid,
) -> Result<Option<SiteManifest>> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            type ManifestRow = (
                Uuid,
                String,
                String,
                serde_json::Value,
                String,
                serde_json::Value,
                serde_json::Value,
                Option<String>,
            );
            let row: Option<ManifestRow> = sqlx::query_as(
                r#"SELECT site_id, country, timezone, languages, currency,
                          capabilities, integrations, policy_bundle
                   FROM site_manifests
                   WHERE tenant_id = $1 AND site_id = $2"#,
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Site manifest read failed: {e}")))?;
            let manifest = row
                .map(
                    |(
                        site_id,
                        country,
                        timezone,
                        languages,
                        currency,
                        capabilities,
                        integrations,
                        policy_bundle,
                    )| {
                        Ok::<_, SenseiError>(SiteManifest {
                            site_id,
                            country,
                            timezone,
                            languages: serde_json::from_value(languages).map_err(|e| {
                                SenseiError::Database(format!("Invalid languages in manifest: {e}"))
                            })?,
                            currency,
                            capabilities: serde_json::from_value(capabilities).map_err(|e| {
                                SenseiError::Database(format!(
                                    "Invalid capabilities in manifest: {e}"
                                ))
                            })?,
                            integrations: serde_json::from_value(integrations).map_err(|e| {
                                SenseiError::Database(format!(
                                    "Invalid integrations in manifest: {e}"
                                ))
                            })?,
                            policy_bundle,
                        })
                    },
                )
                .transpose()?;
            Ok(manifest)
        })
    })
    .await
}

/// Bootstrap a site — ONE transaction that (1) upserts the declarative
/// manifest AND (2) seeds the tenant's canonical metric definitions. The
/// metric seed is the SAME registry as migration 115 (`ON CONFLICT DO
/// NOTHING` keeps re-bootstraps idempotent), so a plant is operational the
/// moment its records exist: no core domain code is touched.
pub async fn bootstrap_site(pool: &PgPool, tenant_id: Uuid, manifest: SiteManifest) -> Result<()> {
    validate(&manifest)?;
    let languages = serde_json::to_value(&manifest.languages)
        .map_err(|e| SenseiError::Validation(format!("Invalid languages JSON: {e}")))?;
    let capabilities = serde_json::to_value(&manifest.capabilities)
        .map_err(|e| SenseiError::Validation(format!("Invalid capabilities JSON: {e}")))?;
    let integrations = serde_json::to_value(&manifest.integrations)
        .map_err(|e| SenseiError::Validation(format!("Invalid integrations JSON: {e}")))?;
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            sqlx::query(
                r#"INSERT INTO site_manifests
                       (tenant_id, site_id, country, timezone, languages, currency,
                        capabilities, integrations, policy_bundle, manifest_version)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 1)
                   ON CONFLICT (tenant_id, site_id) DO UPDATE SET
                       country = EXCLUDED.country,
                       timezone = EXCLUDED.timezone,
                       languages = EXCLUDED.languages,
                       currency = EXCLUDED.currency,
                       capabilities = EXCLUDED.capabilities,
                       integrations = EXCLUDED.integrations,
                       policy_bundle = EXCLUDED.policy_bundle,
                       manifest_version = site_manifests.manifest_version + 1,
                       updated_at = NOW()"#,
            )
            .bind(tenant_id)
            .bind(manifest.site_id)
            .bind(&manifest.country)
            .bind(&manifest.timezone)
            .bind(&languages)
            .bind(&manifest.currency)
            .bind(&capabilities)
            .bind(&integrations)
            .bind(&manifest.policy_bundle)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Site manifest upsert failed: {e}")))?;

            // Seed the canonical metric registry — the SAME 5 core metrics
            // and values as migration 115, applied per-tenant at bootstrap
            // so a tenant created after the migration still gets them.
            sqlx::query(
                r#"INSERT INTO metric_definitions
                       (tenant_id, metric_id, version, name, purpose, formula, unit,
                        grain, source, owner_role, audience, freshness,
                        anti_gaming, expected_action)
                   SELECT $1, v.metric_id, 1, v.name, v.purpose, v.formula, v.unit,
                          v.grain, v.source, v.owner_role, v.audience::jsonb,
                          v.freshness, v.anti_gaming, v.expected_action
                   FROM (VALUES
                       ('otd', 'On-time delivery', 'share of customer deliveries within the promised date', 'delivered_on_time / total_deliveries', '%', 'site', 'sales_orders.delivery_date + goods_receipts', 'production_planner', '["site_manager","production_manager","sales"]', 'daily', 'Do not exclude late orders via status churn; a cancelled-late order is still a miss.', 'Identify the constraint that pushed the delivery late and decide the recovery.'),
                       ('fpy', 'First-pass yield', 'share of units passing all checks without rework', 'passed_first_pass / total_units', '%', 'line', 'production_events + quality results', 'quality_engineer', '["site_manager","production_manager","quality"]', 'shift', 'Rework recorded as first-pass inflates the metric; audit the rework ledger.', 'Find the operation where defects are introduced and run the containment loop.'),
                       ('lead_time', 'Order lead time', 'elapsed time from order receipt to shipment', 'ship_date - order_date', 'days', 'site', 'sales_orders + shipments', 'production_planner', '["site_manager","production_manager","sales"]', 'daily', 'Backdating the ship date hides the true lead time.', 'Compare against demonstrated capacity and decide the honest promise.'),
                       ('scrap_rate', 'Scrap rate', 'share of produced units scrapped', 'scrapped / produced', '%', 'line', 'work_orders.quantity_scrapped', 'quality_engineer', '["production_manager","quality"]', 'shift', 'Scrapping at end-of-line only hides the true introduction point.', 'Trace the scrap to its first introduction operation.'),
                       ('help_response', 'Andon help response time', 'time from Andon raise to first acknowledgement', 'avg(acknowledged_at - created_at)', 's', 'cell', 'andons', 'team_lead', '["team_lead","site_manager"]', 'realtime', 'Acknowledging without acting is not a response; track containment separately.', 'Go to the work center where help is waiting.')
                   ) AS v(metric_id, name, purpose, formula, unit, grain, source, owner_role, audience, freshness, anti_gaming, expected_action)
                   ON CONFLICT (tenant_id, metric_id, version) DO NOTHING"#,
            )
            .bind(tenant_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Canonical metric seed failed: {e}")))?;
            Ok(())
        })
    })
    .await
}
