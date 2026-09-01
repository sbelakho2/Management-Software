//! Declarative SITE MANIFEST (fifteenth audit 83/93/A17) with a REAL
//! lifecycle (sixteenth audit items 63-64/96): a new plant comes onto
//! Starz Forge WITHOUT modifying core domain code — the manifest IS the
//! configuration. Country, timezone, languages, currency, capabilities,
//! integrations and the policy bundle are RECORDS, not code; the only
//! domain reference is `site_id`. `bootstrap_site` only PROVISIONS the
//! manifest + canonical metric seed — a site becomes operational through
//! the guarded ladder Draft → Validated → Provisioning →
//! ReadyForTraining → OperationalQualification → Active, climbed by
//! `validate_site` (validation report) and `activate_site`. Manifest
//! codes are STRONGLY validated against ISO 3166-1 alpha-2, ISO 4217,
//! IANA tz names and BCP 47 tags — never free-form strings.

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

/// A BCP 47 language tag matches `^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$` — the
/// primary subtag is 2-3 lowercase ASCII letters, each extension is 2-8
/// ASCII alphanumerics. Regex-free split on '-'.
fn is_bcp47_tag(tag: &str) -> bool {
    let mut parts = tag.split('-');
    match parts.next() {
        Some(primary) => {
            let p = primary.as_bytes();
            if p.len() < 2 || p.len() > 3 || !p.iter().all(|b| b.is_ascii_lowercase()) {
                return false;
            }
        }
        None => return false,
    }
    parts.all(|part| {
        let p = part.as_bytes();
        !p.is_empty() && p.len() <= 8 && p.iter().all(|b| b.is_ascii_alphanumeric())
    })
}

/// STRONG manifest code validation (sixteenth audit item 64/96): the
/// locale/code fields must be real ISO/IANA/BCP 47 identifiers, never
/// free-form strings:
/// - country: ISO 3166-1 alpha-2 (exactly 2 uppercase ASCII letters) OR
///   the capitalized policy-registry country name the manifest's country
///   policy is keyed on ('Morocco', 'Tunisia' — migration 122 / the lazy
///   seed use the full name, so both forms are accepted; a lowercase or
///   malformed name is rejected);
/// - currency: ISO 4217 (exactly 3 uppercase ASCII letters);
/// - timezone: IANA name — must contain '/' with non-empty ASCII
///   alphanumeric parts (full validation needs the tz database; the
///   '/' + alnum check is the documented approximation);
/// - languages: BCP 47 tags (`^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$`).
pub fn validate_manifest_codes(manifest: &SiteManifest) -> std::result::Result<(), String> {
    let country = manifest.country.as_bytes();
    let alpha2 = country.len() == 2 && country.iter().all(|b| b.is_ascii_uppercase());
    let policy_name = !country.is_empty()
        && country[0].is_ascii_uppercase()
        && country.iter().all(|b| b.is_ascii_alphabetic());
    if !alpha2 && !policy_name {
        return Err(format!(
            "country '{}' is not a valid ISO 3166-1 alpha-2 code \
             (exactly 2 uppercase ASCII letters) or a registered policy \
             country name",
            manifest.country
        ));
    }
    let currency = manifest.currency.as_bytes();
    if currency.len() != 3 || !currency.iter().all(|b| b.is_ascii_uppercase()) {
        return Err(format!(
            "currency '{}' is not a valid ISO 4217 code \
             (exactly 3 uppercase ASCII letters)",
            manifest.currency
        ));
    }
    let tz_ok = !manifest.timezone.is_empty()
        && manifest
            .timezone
            .split('/')
            .all(|part| !part.is_empty() && part.chars().all(|c| c.is_ascii_alphanumeric()))
        && manifest.timezone.contains('/');
    if !tz_ok {
        return Err(format!(
            "timezone '{}' is not a valid IANA name \
             (must be 'Area/Location' with non-empty ASCII parts)",
            manifest.timezone
        ));
    }
    if let Some(bad) = manifest.languages.iter().find(|l| !is_bcp47_tag(l)) {
        return Err(format!(
            "language '{}' is not a valid BCP 47 tag \
             (^[a-z]{{2,3}}(-[A-Za-z0-9]{{2,8}})*$)",
            bad
        ));
    }
    Ok(())
}

/// Upsert the declarative manifest for one site of a tenant. Idempotent:
/// re-bootstrapping a site refreshes its records and bumps
/// `manifest_version` instead of failing.
pub async fn upsert_manifest(pool: &PgPool, tenant_id: Uuid, manifest: SiteManifest) -> Result<()> {
    validate_manifest_codes(&manifest).map_err(SenseiError::Validation)?;
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
/// manifest AND (2) seeds the tenant's canonical metric definitions (the
/// SAME registry as migration 115, `ON CONFLICT DO NOTHING` keeps
/// re-bootstraps idempotent). Bootstrap ONLY PROVISIONS the manifest +
/// metrics: it does NOT make the site operational. A site becomes
/// operational through the guarded lifecycle ladder — `validate_site`
/// produces the operational-qualification report (country policy, roles,
/// work centers, capabilities, metrics) and moves draft → validated, then
/// `activate_site` moves validated → active.
pub async fn bootstrap_site(pool: &PgPool, tenant_id: Uuid, manifest: SiteManifest) -> Result<()> {
    validate_manifest_codes(&manifest).map_err(SenseiError::Validation)?;
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

// ── Site lifecycle (sixteenth audit items 63-64/96) ──────────────────────
//
// Bootstrap only PROVISIONS a site. A site becomes operational through the
// guarded ladder Draft → Validated → Provisioning → ReadyForTraining →
// OperationalQualification → Active: `validate_site` produces the
// operational-qualification report (country policy, roles, work centers,
// capabilities, metrics) and advances draft → validated; `activate_site`
// advances validated → active. Every step is guarded — a site can never
// jump the ladder.

/// The operational-qualification report of one site: every prerequisite as
/// an explicit `(check name, passed, detail)` row plus the aggregate
/// `ready` flag (all checks pass).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ValidationReport {
    pub checks: Vec<(String, bool, String)>,
    pub ready: bool,
}

/// Run the operational-qualification checks for one site inside a single
/// tenant-scoped transaction and produce the validation report. When every
/// check passes the manifest advances draft → validated (only from
/// 'draft' — the guarded ladder); a failed report leaves the status
/// untouched. The report is stored in `validation_report` either way.
pub async fn validate_site(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Uuid,
) -> Result<ValidationReport> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            // A site without a manifest cannot be validated — bootstrap first.
            type ManifestRow = (String, serde_json::Value);
            let row: Option<ManifestRow> = sqlx::query_as(
                r#"SELECT country, capabilities
                   FROM site_manifests
                   WHERE tenant_id = $1 AND site_id = $2"#,
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Site manifest read failed: {e}")))?;
            let (country, capabilities) = row.ok_or_else(|| {
                SenseiError::Validation(format!(
                    "no site manifest for site {site_id} — bootstrap the site first"
                ))
            })?;
            let capabilities: Vec<String> = serde_json::from_value(capabilities).map_err(|e| {
                SenseiError::Database(format!("Invalid capabilities in manifest: {e}"))
            })?;

            let mut checks: Vec<(String, bool, String)> = Vec::new();

            // 1. Country policy exists — the manifest's country must have a
            // policy record (err-free lookup; missing = failed check).
            let policy: Option<String> = sqlx::query_scalar(
                "SELECT country FROM country_policies WHERE tenant_id = $1 AND country = $2",
            )
            .bind(tenant_id)
            .bind(&country)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Country policy lookup failed: {e}")))?;
            match policy {
                Some(_) => checks.push((
                    "country_policy".into(),
                    true,
                    "country policy exists".into(),
                )),
                None => checks.push((
                    "country_policy".into(),
                    false,
                    format!("no country policy for {country}"),
                )),
            }

            // 2. Roles defined — at least one role slot SCOPED TO THIS
            // SITE (seventeenth audit item 12: tenant-level slots from
            // another site must not pass this site's readiness).
            let role_slots: i64 = sqlx::query_scalar(
                "SELECT COUNT(*) FROM role_slots WHERE tenant_id = $1 AND scope_site_id = $2",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Role slot count failed: {e}")))?;
            checks.push((
                "roles_defined".into(),
                role_slots > 0,
                format!("{role_slots} role slot(s) scoped to this site"),
            ));

            // 3. Work centers created — at least one FOR THIS SITE
            // (work_centers.site_id, migration 134).
            let work_centers: i64 = sqlx::query_scalar(
                "SELECT COUNT(*) FROM work_centers WHERE tenant_id = $1 AND site_id = $2",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Work center count failed: {e}")))?;
            checks.push((
                "work_centers_created".into(),
                work_centers > 0,
                format!("{work_centers} work center(s) in this site"),
            ));

            // 3b. Shifts/calendar — the site's employee assignments define
            // at least one shift (seventeenth audit item 12).
            let shifts: i64 = sqlx::query_scalar(
                "SELECT COUNT(DISTINCT shift_id) FROM employee_assignments \
                 WHERE tenant_id = $1 AND site_id = $2 AND shift_id IS NOT NULL",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Shift count failed: {e}")))?;
            checks.push((
                "shifts_defined".into(),
                shifts > 0,
                format!("{shifts} shift(s) assigned in this site"),
            ));

            // 3c. Skill coverage — qualified principals assigned to this
            // site's slots (sixteenth audit: skills are site-aware). The
            // qualification level lives on skill_qualifications.
            let skills: i64 = sqlx::query_scalar(
                "SELECT COUNT(DISTINCT sq.skill_id) FROM skill_qualifications sq \
                 JOIN principal_assignments pa ON pa.principal_id = sq.principal_id \
                 JOIN role_slots rs ON rs.id = pa.slot_id \
                 WHERE sq.tenant_id = $1 AND rs.scope_site_id = $2 AND pa.ended_at IS NULL \
                   AND sq.level IN ('independent', 'trainer')",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Skill coverage failed: {e}")))?;
            checks.push((
                "skill_coverage".into(),
                skills > 0,
                format!("{skills} qualified skill(s) on this site's principals"),
            ));

            // 3d. Integrations healthy — the manifest declares
            // integrations and none is marked failed in this site's log.
            let integrations_ok: bool = {
                let declared: Vec<serde_json::Value> = serde_json::from_value(
                    sqlx::query_scalar::<_, serde_json::Value>(
                        "SELECT integrations FROM site_manifests \
                         WHERE tenant_id = $1 AND site_id = $2",
                    )
                    .bind(tenant_id)
                    .bind(site_id)
                    .fetch_one(&mut **tx)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Integrations read failed: {e}")))?,
                )
                .unwrap_or_default();
                let failures: i64 = sqlx::query_scalar(
                    "SELECT COUNT(*) FROM integration_dead_letter \
                     WHERE tenant_id = $1",
                )
                .bind(tenant_id)
                .bind(site_id)
                .fetch_one(&mut **tx)
                .await
                .unwrap_or(0);
                !declared.is_empty() && failures == 0
            };
            checks.push((
                "integrations_healthy".into(),
                integrations_ok,
                if integrations_ok {
                    "integrations declared and healthy".to_string()
                } else {
                    "no declared integrations or a failed integration".to_string()
                },
            ));

            // 4. Capabilities mapped — the manifest declares at least one.
            checks.push((
                "capabilities_mapped".into(),
                !capabilities.is_empty(),
                if capabilities.is_empty() {
                    "manifest declares no capabilities".to_string()
                } else {
                    format!("{} capability(ies) mapped", capabilities.len())
                },
            ));

            // 5. Metrics seeded — the canonical metric registry (>= 5).
            let metrics: i64 =
                sqlx::query_scalar("SELECT COUNT(*) FROM metric_definitions WHERE tenant_id = $1")
                    .bind(tenant_id)
                    .fetch_one(&mut **tx)
                    .await
                    .map_err(|e| {
                        SenseiError::Database(format!("Metric definition count failed: {e}"))
                    })?;
            checks.push((
                "metrics_seeded".into(),
                metrics >= 5,
                format!("{metrics} metric definition(s) seeded (need >= 5)"),
            ));

            // 6. Replication policy valid — the site's replication log
            // must exist and contain no rows stuck in failed state with
            // no retry scheduled (seventeenth audit item 12: this is no
            // longer hardcoded true).
            let (rep_entries, rep_failed): (i64, i64) = sqlx::query_as(
                "SELECT COUNT(*)::bigint, \
                        COUNT(*) FILTER (WHERE status = 'failed' \
                                         AND next_attempt_at <= NOW())::bigint \
                 FROM site_replication_log \
                 WHERE tenant_id = $1 AND site_id = $2",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Replication check failed: {e}")))?;
            let rep_valid = rep_failed == 0;
            checks.push((
                "replication_policy_valid".into(),
                rep_valid,
                if rep_entries == 0 {
                    "no replication entries — queue is idle".to_string()
                } else {
                    format!("{rep_entries} replication entry(ies), {rep_failed} retry-due failed")
                },
            ));

            let ready = checks.iter().all(|(_, ok, _)| *ok);
            let report = ValidationReport { checks, ready };
            let report_json = serde_json::to_value(&report).map_err(|e| {
                SenseiError::Validation(format!("Invalid validation report JSON: {e}"))
            })?;

            // Store the report; a READY report advances draft → validated.
            sqlx::query(
                "UPDATE site_manifests
                    SET validation_report = $3, updated_at = NOW()
                  WHERE tenant_id = $1 AND site_id = $2",
            )
            .bind(tenant_id)
            .bind(site_id)
            .bind(report_json.clone())
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Validation report store failed: {e}")))?;
            if ready {
                let advanced = sqlx::query(
                    "UPDATE site_manifests
                        SET status = 'validated', updated_at = NOW()
                      WHERE tenant_id = $1 AND site_id = $2 AND status = 'draft'",
                )
                .bind(tenant_id)
                .bind(site_id)
                .execute(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Status advance failed: {e}")))?;
                if advanced.rows_affected() == 0 {
                    return Err(SenseiError::Validation(format!(
                        "site {site_id} cannot advance draft → validated: \
                         it must be in 'draft' (guarded ladder)"
                    )));
                }
            }
            Ok(report)
        })
    })
    .await
}

/// Move a VALIDATED site to 'active' — the guarded ladder step
/// validated → active. A site in any other status is rejected, so a site
/// can never skip its operational qualification.
/// The FULL six-stage lifecycle ladder (seventeenth audit item 12): the
/// previous implementation accepted only draft → validated → active and
/// let the intermediate stages exist only in the CHECK constraint. Every
/// transition now has a REAL gate — a site can only advance one step,
/// and the step's prerequisite must hold:
///
/// - validated → provisioning: the validation report exists and is ready
/// - provisioning → ready_for_training: skills + shifts + roles + work
///   centers exist FOR THIS SITE (the qualification checks)
/// - ready_for_training → operational_qualification: at least one
///   training/qualification evidence record exists
/// - operational_qualification → active: the site's replication policy
///   passes and no failed integration exists
fn lifecycle_order() -> &'static [&'static str] {
    &[
        "draft",
        "validated",
        "provisioning",
        "ready_for_training",
        "operational_qualification",
        "active",
    ]
}

async fn advance_lifecycle(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    site_id: Uuid,
    from: &str,
    to: &str,
) -> Result<()> {
    let order = lifecycle_order();
    let from_idx = order
        .iter()
        .position(|s| *s == from)
        .ok_or_else(|| SenseiError::Validation(format!("unknown lifecycle state {from}")))?;
    let to_idx = order
        .iter()
        .position(|s| *s == to)
        .ok_or_else(|| SenseiError::Validation(format!("unknown lifecycle state {to}")))?;
    if to_idx != from_idx + 1 {
        return Err(SenseiError::Validation(format!(
            "lifecycle is a one-step guarded ladder: {from} → {to} is not the next step"
        )));
    }
    let updated = sqlx::query(
        "UPDATE site_manifests SET status = $3, updated_at = NOW() \
         WHERE tenant_id = $1 AND site_id = $2 AND status = $4",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(to)
    .bind(from)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Lifecycle advance failed: {e}")))?;
    if updated.rows_affected() == 0 {
        return Err(SenseiError::Validation(format!(
            "site {site_id} is not in state '{from}' — the ladder is strictly sequential"
        )));
    }
    Ok(())
}

async fn site_qualification_checks(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    site_id: Uuid,
) -> Result<()> {
    let role_slots: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM role_slots WHERE tenant_id = $1 AND scope_site_id = $2",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_one(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Role slot count failed: {e}")))?;
    if role_slots == 0 {
        return Err(SenseiError::Validation(
            "no role slots scoped to this site".to_string(),
        ));
    }
    let work_centers: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM work_centers WHERE tenant_id = $1 AND site_id = $2",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_one(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Work center count failed: {e}")))?;
    if work_centers == 0 {
        return Err(SenseiError::Validation(
            "no work centers in this site".to_string(),
        ));
    }
    let shifts: i64 = sqlx::query_scalar(
        "SELECT COUNT(DISTINCT shift_id) FROM employee_assignments \
         WHERE tenant_id = $1 AND site_id = $2 AND shift_id IS NOT NULL",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_one(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Shift count failed: {e}")))?;
    if shifts == 0 {
        return Err(SenseiError::Validation(
            "no shifts assigned in this site".to_string(),
        ));
    }
    let skills: i64 = sqlx::query_scalar(
        "SELECT COUNT(DISTINCT sq.skill_id) FROM skill_qualifications sq \
         JOIN principal_assignments pa ON pa.principal_id = sq.principal_id \
         JOIN role_slots rs ON rs.id = pa.slot_id \
         WHERE sq.tenant_id = $1 AND rs.scope_site_id = $2 AND pa.ended_at IS NULL \
           AND sq.level IN ('independent', 'trainer')",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_one(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Skill coverage failed: {e}")))?;
    if skills == 0 {
        return Err(SenseiError::Validation(
            "no qualified skills on this site's principals".to_string(),
        ));
    }
    Ok(())
}

/// Advance a site one step on the guarded ladder. The gate for each step
/// is checked INSIDE the same transaction as the transition.
pub async fn advance_site_lifecycle(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Uuid,
    to: &str,
) -> Result<()> {
    let to = to.to_string();
    let pool_for_validation = pool.clone();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let current: String = sqlx::query_scalar(
                "SELECT status FROM site_manifests WHERE tenant_id = $1 AND site_id = $2",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Site status read failed: {e}")))?;
            match (current.as_str(), to.as_str()) {
                ("draft", "validated") => {
                    // Eighteenth audit P0-4: draft -> validated is
                    // IMPOSSIBLE without a real validation — the
                    // transition RUNS validate_site (which stores the
                    // report AND advances only when ready) instead of a
                    // blind status bump. The ladder cannot move without
                    // the report by construction.
                    let report = validate_site(&pool_for_validation, tenant_id, site_id).await?;
                    if !report.ready {
                        return Err(SenseiError::Validation(
                            "site is not ready — the validation report lists the failing                              checks; draft -> validated requires a READY report"
                                .to_string(),
                        ));
                    }
                }
                ("validated", "provisioning") => {
                    let report_ready: bool = sqlx::query_scalar(
                        "SELECT COALESCE((validation_report->>'ready')::boolean, false) \
                         FROM site_manifests WHERE tenant_id = $1 AND site_id = $2",
                    )
                    .bind(tenant_id)
                    .bind(site_id)
                    .fetch_one(&mut **tx)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Report read failed: {e}")))?;
                    if !report_ready {
                        return Err(SenseiError::Validation(
                            "validation report is not ready — run validate_site first".to_string(),
                        ));
                    }
                    advance_lifecycle(tx, tenant_id, site_id, "validated", "provisioning").await?;
                }
                ("provisioning", "ready_for_training") => {
                    site_qualification_checks(tx, tenant_id, site_id).await?;
                    advance_lifecycle(tx, tenant_id, site_id, "provisioning", "ready_for_training")
                        .await?;
                }
                ("ready_for_training", "operational_qualification") => {
                    // At least one QUALIFIED skill must exist for this
                    // site's principals (the qualification table is
                    // skill_qualifications).
                    let evidence: i64 = sqlx::query_scalar(
                        "SELECT COUNT(*) FROM skill_qualifications sq \
                         JOIN principal_assignments pa ON pa.principal_id = sq.principal_id \
                         JOIN role_slots rs ON rs.id = pa.slot_id \
                         WHERE sq.tenant_id = $1 AND rs.scope_site_id = $2 \
                           AND pa.ended_at IS NULL \
                           AND sq.level IN ('independent', 'trainer')",
                    )
                    .bind(tenant_id)
                    .bind(site_id)
                    .fetch_one(&mut **tx)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Evidence count failed: {e}")))?;
                    if evidence == 0 {
                        return Err(SenseiError::Validation(
                            "no qualification evidence for this site's principals".to_string(),
                        ));
                    }
                    advance_lifecycle(
                        tx,
                        tenant_id,
                        site_id,
                        "ready_for_training",
                        "operational_qualification",
                    )
                    .await?;
                }
                ("operational_qualification", "active") => {
                    let failed: i64 = sqlx::query_scalar(
                        "SELECT COUNT(*) FROM site_replication_log \
                         WHERE tenant_id = $1 AND site_id = $2 \
                           AND status = 'failed' AND next_attempt_at <= NOW()",
                    )
                    .bind(tenant_id)
                    .bind(site_id)
                    .fetch_one(&mut **tx)
                    .await
                    .unwrap_or(0);
                    if failed > 0 {
                        return Err(SenseiError::Validation(
                            "replication has retry-due failed entries — activation blocked"
                                .to_string(),
                        ));
                    }
                    let integ_failed: i64 = sqlx::query_scalar(
                        "SELECT COUNT(*) FROM integration_dead_letter \
                         WHERE tenant_id = $1",
                    )
                    .bind(tenant_id)
                    .bind(site_id)
                    .fetch_one(&mut **tx)
                    .await
                    .unwrap_or(0);
                    if integ_failed > 0 {
                        return Err(SenseiError::Validation(
                            "a site integration is failed — activation blocked".to_string(),
                        ));
                    }
                    advance_lifecycle(
                        tx,
                        tenant_id,
                        site_id,
                        "operational_qualification",
                        "active",
                    )
                    .await?;
                }
                _ => {
                    return Err(SenseiError::Validation(format!(
                        "no guarded transition from '{current}' to '{to}'"
                    )))
                }
            }
            Ok(())
        })
    })
    .await
}

/// Kept for API compatibility: activation is now the LAST rung of the
/// guarded ladder — only an 'operational_qualification' site activates.
pub async fn activate_site(pool: &PgPool, tenant_id: Uuid, site_id: Uuid) -> Result<()> {
    advance_site_lifecycle(pool, tenant_id, site_id, "active").await
}
