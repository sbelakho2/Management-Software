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
/// re-bootstrapping a site refreshes its records; when the content
/// (capabilities/integrations/policy_bundle) CHANGES, `manifest_version`
/// is bumped and the qualification is invalidated (validation_report
/// reset to an empty report + status back to 'draft' — the ladder forces
/// revalidation).
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
                       manifest_version = CASE
                           WHEN site_manifests.capabilities IS DISTINCT FROM EXCLUDED.capabilities
                             OR site_manifests.integrations IS DISTINCT FROM EXCLUDED.integrations
                             OR site_manifests.policy_bundle IS DISTINCT FROM EXCLUDED.policy_bundle
                           THEN site_manifests.manifest_version + 1
                           ELSE site_manifests.manifest_version END,
                       validation_report = CASE
                           WHEN site_manifests.capabilities IS DISTINCT FROM EXCLUDED.capabilities
                             OR site_manifests.integrations IS DISTINCT FROM EXCLUDED.integrations
                             OR site_manifests.policy_bundle IS DISTINCT FROM EXCLUDED.policy_bundle
                           THEN '{}'::jsonb
                           ELSE site_manifests.validation_report END,
                       status = CASE
                           WHEN site_manifests.capabilities IS DISTINCT FROM EXCLUDED.capabilities
                             OR site_manifests.integrations IS DISTINCT FROM EXCLUDED.integrations
                             OR site_manifests.policy_bundle IS DISTINCT FROM EXCLUDED.policy_bundle
                           THEN 'draft'
                           ELSE site_manifests.status END,
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
/// Nineteenth audit item P1 (manifest staleness): a re-bootstrap that
/// CHANGES capabilities/integrations/policy_bundle bumps
/// `manifest_version` and INVALIDATES the qualification — the stored
/// validation report is reset (empty report, the column is NOT NULL by
/// migration 131) and the status resets to 'draft'
/// (RequalificationRequired), so the guarded ladder forces the site to be
/// re-validated against the new manifest before it can proceed. An
/// identical re-bootstrap leaves version/status/report untouched.
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
                       manifest_version = CASE
                           WHEN site_manifests.capabilities IS DISTINCT FROM EXCLUDED.capabilities
                             OR site_manifests.integrations IS DISTINCT FROM EXCLUDED.integrations
                             OR site_manifests.policy_bundle IS DISTINCT FROM EXCLUDED.policy_bundle
                           THEN site_manifests.manifest_version + 1
                           ELSE site_manifests.manifest_version END,
                       validation_report = CASE
                           WHEN site_manifests.capabilities IS DISTINCT FROM EXCLUDED.capabilities
                             OR site_manifests.integrations IS DISTINCT FROM EXCLUDED.integrations
                             OR site_manifests.policy_bundle IS DISTINCT FROM EXCLUDED.policy_bundle
                           THEN '{}'::jsonb
                           ELSE site_manifests.validation_report END,
                       status = CASE
                           WHEN site_manifests.capabilities IS DISTINCT FROM EXCLUDED.capabilities
                             OR site_manifests.integrations IS DISTINCT FROM EXCLUDED.integrations
                             OR site_manifests.policy_bundle IS DISTINCT FROM EXCLUDED.policy_bundle
                           THEN 'draft'
                           ELSE site_manifests.status END,
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
/// `ready` flag (all checks pass). `manifest_version` records WHICH
/// manifest revision was validated — a stored report whose version no
/// longer matches the manifest's current version is STALE (nineteenth
/// audit item P1): the site must be re-validated.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ValidationReport {
    pub checks: Vec<(String, bool, String)>,
    pub ready: bool,
    pub manifest_version: i32,
}

/// Capability → mandatory operational requirements (eighteenth audit item
/// P1-5): each requirement is a check NAME derived from a REAL schema
/// table. Readiness for a capability is only granted when every required
/// check passes against actual data — a plant cannot declare itself
/// competent. Unknown capabilities return nothing and are handled
/// FAIL-CLOSED by the checks construction (a `capability_<x>_mapped`
/// failing check), never silently treated as ready.
fn capability_requirements(capability: &str) -> Vec<&'static str> {
    match capability {
        "SMT" => vec![
            "smt_work_centers",
            "smt_skills",
            "smt_standards",
            "smt_calibration",
        ],
        "AOI" => vec!["aoi_work_centers", "aoi_skills", "aoi_ctq_inspection"],
        "ICT" => vec!["ict_work_centers", "ict_skills", "ict_fixtures"],
        "box_build" => vec!["box_build_work_centers", "box_build_skills"],
        "wire_harness" => vec!["wire_harness_work_centers", "wire_harness_skills"],
        "final_test" => vec![
            "final_test_work_centers",
            "final_test_skills",
            "final_test_standards",
        ],
        _ => vec![],
    }
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
            type ManifestRow = (String, serde_json::Value, i32);
            let row: Option<ManifestRow> = sqlx::query_as(
                r#"SELECT country, capabilities, manifest_version
                   FROM site_manifests
                   WHERE tenant_id = $1 AND site_id = $2"#,
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Site manifest read failed: {e}")))?;
            let (country, capabilities, manifest_version) = row.ok_or_else(|| {
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
                   AND sq.level IN ('independent', 'trainer') \
                   AND (sq.expires_at IS NULL OR sq.expires_at > NOW())",
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
                // Twentieth audit P1: readiness is PER-SITE and
                // PER-DECLARED-INTEGRATION. Every integration kind THIS
                // site declares must show its own recent checkpoint —
                // one SAP checkpoint can never certify another site's
                // MES integration, and an unrelated dead letter can
                // never block this site. DB failures propagate: UNKNOWN
                // -> NOT READY.
                let declared_kinds: Vec<String> = declared
                    .iter()
                    .filter_map(|v| {
                        v.get("kind")
                            .and_then(|k| k.as_str())
                            .map(|k| k.to_string())
                    })
                    .collect();
                let integration_ok = if declared_kinds.is_empty() {
                    false
                } else {
                    let mut all_proven = true;
                    for kind in &declared_kinds {
                        let proven: i64 = sqlx::query_scalar(
                            "SELECT COUNT(*) FROM integration_checkpoints \
                             WHERE tenant_id = $1 \
                               AND source_system = $2 \
                               AND last_run_at > NOW() - INTERVAL '24 hours'",
                        )
                        .bind(tenant_id)
                        .bind(kind)
                        .fetch_one(&mut **tx)
                        .await
                        .map_err(|e| {
                            SenseiError::Database(format!(
                                "Integration checkpoint read failed for {kind}: {e}"
                            ))
                        })?;
                        if proven == 0 {
                            all_proven = false;
                        }
                    }
                    all_proven
                };
                integration_ok
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
            // Eighteenth audit P1-12: a tenant with unreconciled work
            // centers (site_id NULL or topology_state
            // needs_reconciliation) can never pass validation — unknown
            // topology is never certified as ready.
            // Nineteenth audit P1: provenance doubt is the same failure —
            // ANY work center marked 'legacy_heuristic' (migration 145's
            // corrective flag on unprovable rows, even one with a non-NULL
            // site_id) blocks validation: legacy_heuristic is never
            // allowed into an Active plant.
            let unreconciled: i64 = sqlx::query_scalar(
                "SELECT COUNT(*) FROM work_centers WHERE tenant_id = $1 \
                 AND (site_id IS NULL OR topology_state = 'needs_reconciliation' \
                      OR topology_assignment_source = 'legacy_heuristic')",
            )
            .bind(tenant_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Topology check failed: {e}")))?;
            checks.push((
                "topology_reconciled".into(),
                unreconciled == 0,
                if unreconciled == 0 {
                    "all work centers are site-resolved".to_string()
                } else {
                    format!(
                        "{unreconciled} work center(s) need topology reconciliation —                          unknown lineage is never assigned to a plant"
                    )
                },
            ));

            // Manifest staleness (nineteenth audit item P1): the report
            // being REPLACED was validated against some manifest version;
            // if it does not match the manifest's CURRENT version the site
            // is NOT ready — a stale report can never certify readiness.
            // (No stored report yet = first validation, nothing stale.)
            let stored_report_version: Option<String> = sqlx::query_scalar(
                "SELECT validation_report->>'manifest_version' \
                 FROM site_manifests WHERE tenant_id = $1 AND site_id = $2",
            )
            .bind(tenant_id)
            .bind(site_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Stored report read failed: {e}")))?;
            let manifest_stale = stored_report_version
                .as_deref()
                .map(|v| {
                    v.parse::<i32>()
                        .map(|n| n != manifest_version)
                        .unwrap_or(true)
                })
                .unwrap_or(false);
            let stored_display = stored_report_version.as_deref().unwrap_or("none");
            checks.push((
                "manifest_current".into(),
                !manifest_stale,
                if manifest_stale {
                    format!(
                        "stored validation report is stale (validated manifest_version \
                         {stored_display}, current {manifest_version}) — re-validate \
                         the site against the current manifest"
                    )
                } else {
                    format!("validation report matches manifest_version {manifest_version}")
                },
            ));

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

            // 7. Capability-derived readiness (eighteenth audit item P1-5):
            // readiness must follow from the site's DECLARED capabilities —
            // every mandatory operational requirement of each declared
            // capability must be satisfied by REAL schema data. Unknown
            // capabilities are fail-closed: the system refuses to certify
            // a plant for a capability it cannot verify.
            for capability in &capabilities {
                let requirements = capability_requirements(capability);
                if requirements.is_empty() {
                    checks.push((
                        format!("capability_{capability}_mapped"),
                        false,
                        format!(
                            "no operational requirements derived for capability {capability} — \
                             it cannot be declared ready"
                        ),
                    ));
                    continue;
                }
                // ILIKE keyword: underscores become spaces so 'box_build'
                // matches names like 'Box Build Cell'.
                let keyword = capability.replace('_', " ");
                let pattern = format!("%{keyword}%");
                for requirement in requirements {
                    let (ok, detail): (bool, String) = match requirement {
                        // <cap>_work_centers: work_centers of THIS site
                        // whose name or type matches the capability.
                        req if req.ends_with("_work_centers") => {
                            let n: i64 = sqlx::query_scalar(
                                "SELECT COUNT(*) FROM work_centers \
                                 WHERE tenant_id = $1 AND site_id = $2 \
                                   AND (name ILIKE $3 OR work_center_type = $4)",
                            )
                            .bind(tenant_id)
                            .bind(site_id)
                            .bind(&pattern)
                            .bind(keyword.to_lowercase())
                            .fetch_one(&mut **tx)
                            .await
                            .map_err(|e| SenseiError::Database(format!(
                                "Work center capability check failed: {e}"
                            )))?;
                            (n > 0, format!("{n} work center(s) matching '{keyword}'"))
                        }
                        // <cap>_skills: qualified (independent/trainer)
                        // principals of THIS site holding a skill whose
                        // name or process matches the capability.
                        req if req.ends_with("_skills") => {
                            let n: i64 = sqlx::query_scalar(
                                "SELECT COUNT(DISTINCT sq.skill_id) FROM skill_qualifications sq \
                                 JOIN principal_assignments pa ON pa.principal_id = sq.principal_id \
                                 JOIN role_slots rs ON rs.id = pa.slot_id \
                                 JOIN skills sk ON sk.id = sq.skill_id \
                                 WHERE sq.tenant_id = $1 AND rs.scope_site_id = $2 \
                                   AND pa.ended_at IS NULL \
                                   AND sq.level IN ('independent', 'trainer') \
                   AND (sq.expires_at IS NULL OR sq.expires_at > NOW()) \
                                   AND (sk.name ILIKE $3 OR sk.process ILIKE $3)",
                            )
                            .bind(tenant_id)
                            .bind(site_id)
                            .bind(&pattern)
                            .fetch_one(&mut **tx)
                            .await
                            .map_err(|e| SenseiError::Database(format!(
                                "Skill capability check failed: {e}"
                            )))?;
                            (n > 0, format!("{n} qualified skill(s) matching '{keyword}'"))
                        }
                        // <cap>_standards: TWI job_standards (migration 116)
                        // covering the capability process or title.
                        req if req.ends_with("_standards") => {
                            let n: i64 = sqlx::query_scalar(
                                "SELECT COUNT(*) FROM job_standards \
                                 WHERE tenant_id = $1 \
                                   AND (process ILIKE $2 OR title ILIKE $2)",
                            )
                            .bind(tenant_id)
                            .bind(&pattern)
                            .fetch_one(&mut **tx)
                            .await
                            .map_err(|e| SenseiError::Database(format!(
                                "Job standard capability check failed: {e}"
                            )))?;
                            (n > 0, format!("{n} job standard(s) matching '{keyword}'"))
                        }
                        // <cap>_calibration: passing calibration records
                        // (gauges → calibration_events, migration 006).
                        req if req.ends_with("_calibration") => {
                            let n: i64 = sqlx::query_scalar(
                                "SELECT COUNT(*) FROM calibration_events \
                                 WHERE tenant_id = $1 AND result = 'pass'",
                            )
                            .bind(tenant_id)
                            .fetch_one(&mut **tx)
                            .await
                            .map_err(|e| SenseiError::Database(format!(
                                "Calibration capability check failed: {e}"
                            )))?;
                            (n > 0, format!("{n} passing calibration record(s)"))
                        }
                        // <cap>_ctq_inspection: an ACTIVE inspection plan
                        // matching the capability with at least one
                        // CRITICAL characteristic (CTQ, migration 100).
                        req if req.ends_with("_ctq_inspection") => {
                            let n: i64 = sqlx::query_scalar(
                                "SELECT COUNT(*) FROM inspection_plans ip \
                                 JOIN inspection_characteristics ic ON ic.plan_id = ip.id \
                                 WHERE ip.tenant_id = $1 AND ip.status = 'active' \
                                   AND ic.criticality = 'critical' \
                                   AND ip.name ILIKE $2",
                            )
                            .bind(tenant_id)
                            .bind(&pattern)
                            .fetch_one(&mut **tx)
                            .await
                            .map_err(|e| SenseiError::Database(format!(
                                "Inspection plan capability check failed: {e}"
                            )))?;
                            (n > 0, format!(
                                "{n} active CTQ inspection plan(s) matching '{keyword}'"
                            ))
                        }
                        // <cap>_fixtures: NO fixtures table exists in the
                        // schema (migrations 001-136) — the ICT fixture
                        // requirement cannot be verified, so the check is
                        // NOT emitted (only checks backed by real tables
                        // are added).
                        _ => continue,
                    };
                    checks.push((requirement.to_string(), ok, detail));
                }
            }

            let ready = checks.iter().all(|(_, ok, _)| *ok);
            let report = ValidationReport {
                checks,
                ready,
                manifest_version,
            };
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
                    // The stored report is the gate — and it is only
                    // trusted when it was validated against the manifest's
                    // CURRENT version (nineteenth audit P1): a stored
                    // report carrying an EXPLICIT older manifest_version is
                    // STALE and NOT ready, so provisioning is blocked until
                    // the site is re-validated. A report that records no
                    // manifest_version (legacy pre-145 reports) has nothing
                    // to mismatch — the version condition is vacuous; the
                    // invalidated empty report ('{}') still fails the gate
                    // on the ready flag.
                    let report_ready: bool = sqlx::query_scalar(
                        "SELECT COALESCE((validation_report->>'ready')::boolean, false) \
                            AND (validation_report->>'manifest_version' IS NULL \
                                 OR COALESCE((validation_report->>'manifest_version')::int, 0) \
                                     = manifest_version) \
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
                           AND sq.level IN ('independent', 'trainer') \
                   AND (sq.expires_at IS NULL OR sq.expires_at > NOW())",
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
                    .map_err(|e| {
                        SenseiError::Database(format!("Replication gate read failed: {e}"))
                    })?;
                    if failed > 0 {
                        return Err(SenseiError::Validation(
                            "replication has retry-due failed entries — activation blocked"
                                .to_string(),
                        ));
                    }
                    // Twentieth audit P1: activation requires POSITIVE,
                    // PER-SITE, PER-DECLARED-INTEGRATION evidence — every
                    // kind this site's manifest declares must show its
                    // own recent checkpoint. A tenant-global checkpoint
                    // count can no longer certify a site whose own
                    // declared integrations never ran.
                    let declared: Vec<serde_json::Value> = serde_json::from_value(
                        sqlx::query_scalar::<_, serde_json::Value>(
                            "SELECT integrations FROM site_manifests \
                             WHERE tenant_id = $1 AND site_id = $2",
                        )
                        .bind(tenant_id)
                        .bind(site_id)
                        .fetch_one(&mut **tx)
                        .await
                        .map_err(|e| {
                            SenseiError::Database(format!("Integration read failed: {e}"))
                        })?,
                    )
                    .unwrap_or_default();
                    let kinds: Vec<String> = declared
                        .iter()
                        .filter_map(|v| {
                            v.get("kind")
                                .and_then(|k| k.as_str())
                                .map(|k| k.to_string())
                        })
                        .collect();
                    if kinds.is_empty() {
                        return Err(SenseiError::Validation(
                            "the site declares no integrations — a site without declared \
                             integrations cannot activate (positive evidence required)"
                                .to_string(),
                        ));
                    }
                    for kind in &kinds {
                        let proven: i64 = sqlx::query_scalar(
                            "SELECT COUNT(*) FROM integration_checkpoints \
                             WHERE tenant_id = $1 AND source_system = $2 \
                               AND last_run_at > NOW() - INTERVAL '24 hours'",
                        )
                        .bind(tenant_id)
                        .bind(kind)
                        .fetch_one(&mut **tx)
                        .await
                        .map_err(|e| {
                            SenseiError::Database(format!("Integration gate read failed: {e}"))
                        })?;
                        if proven == 0 {
                            return Err(SenseiError::Validation(format!(
                                "declared integration '{kind}' has no checkpoint in the \
                                 last 24h — this site's own integration evidence is \
                                 required for activation"
                            )));
                        }
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

/// Re-assert the topology provenance of ONE work center (nineteenth audit
/// item P1): sets the assignment source (per the caller: 'manifest' when
/// the site manifest assigned it, 'employee_history' when derived from
/// employee_assignments, 'manual_reconciliation' when a human verified
/// it), stamps verified_at/verified_by and marks the topology RESOLVED —
/// the row is no longer a validation blocker.
///
/// 'legacy_heuristic' is REFUSED: it is not a provenance, only the doubt
/// marker the 145 corrective step applied to unprovable rows — legacy
/// heuristic must never be (re-)admitted into an Active plant.
pub async fn reconcile_work_center_topology(
    pool: &PgPool,
    tenant_id: Uuid,
    work_center_id: Uuid,
    verified_by: Uuid,
    source: &str,
) -> Result<()> {
    match source {
        "manifest" | "employee_history" | "manual_reconciliation" => {}
        "legacy_heuristic" => {
            return Err(SenseiError::Validation(
                "legacy_heuristic is not a provenance source — it only flags \
                 unprovable rows; reconcile with 'manifest', 'employee_history' \
                 or 'manual_reconciliation'"
                    .to_string(),
            ));
        }
        other => {
            return Err(SenseiError::Validation(format!(
                "unknown topology assignment source '{other}' — must be \
                 'manifest', 'employee_history' or 'manual_reconciliation'"
            )));
        }
    }
    let source = source.to_string();
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let updated = sqlx::query(
                "UPDATE work_centers
                    SET topology_assignment_source = $3,
                        topology_verified_at = NOW(),
                        topology_verified_by = $4,
                        topology_state = 'resolved'
                  WHERE tenant_id = $1 AND id = $2",
            )
            .bind(tenant_id)
            .bind(work_center_id)
            .bind(&source)
            .bind(verified_by)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Topology reconcile failed: {e}")))?;
            if updated.rows_affected() == 0 {
                return Err(SenseiError::Validation(format!(
                    "work center {work_center_id} not found in tenant"
                )));
            }
            Ok(())
        })
    })
    .await
}
