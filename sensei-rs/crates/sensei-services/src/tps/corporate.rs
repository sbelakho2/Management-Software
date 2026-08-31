//! Corporate federation (fifteenth audit 29/46/66-67 + A19/A24,
//! sixteenth audit items 25-28): cross-site aggregation with
//! authorization. Corporate analytics are STRATIFIED — FPY is reported
//! per product family and only the SAME family is comparable across
//! sites; a naive Bizerte-vs-Tangier leaderboard is forbidden. Every
//! metric is computed with its TRUE definition (documented per metric in
//! `definitions`), and the metric engine (`metric_engine`) is the ONE
//! executable definition — API, dashboard, AI and corporate rollup all
//! call the same Rust computers. Causal questions ("Why is Bizerte
//! better at changeovers?") produce HYPOTHESES with evidence, never
//! answers: every candidate carries `epistemic_status = "hypothesis"` so
//! the corporate layer can never present a guess as a fact.

use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

use super::lessons;

/// One site's row in the STRATIFIED corporate comparison. `fpy` is a
/// FRACTION (0..1) and a documented FIRST-PASS PROXY: completed without
/// scrap / completed — the schema has no unit-level first-pass quality
/// signal (inspection_records are sample-based), so the approximation is
/// documented instead of hidden. `scrap_rate` is scrapped / completed
/// (produced units). `otd` is delivered / (delivered + pending_due) —
/// sales_orders carry NO site scope in this schema, so the honest value
/// is computed at tenant level and reported identically for every site.
/// `lead_time_days` is the MANUFACTURING LEAD TIME PROXY: delivered_at
/// (updated_at) − created_at — no shipped_at column exists.
/// `complexity_index` is the deterministic product-complexity proxy (mean
/// routing standard_time in seconds — 0 when the site has no routings).
/// There is NO `fpy_mix_adjusted`: dividing a fraction by seconds is
/// dimensionally invalid; the stratified comparison replaced it.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SiteRow {
    pub site_id: Uuid,
    pub site_name: String,
    pub fpy: f64,
    pub scrap_rate: f64,
    pub otd: f64,
    pub lead_time_days: f64,
    pub complexity_index: f64,
}

/// One stratum of the stratified comparison: FPY for ONE product family
/// at ONE site. `product_family_id` is NULL for products without a
/// family — that unassigned stratum is still comparable across sites.
/// `sample_size` is the completed units behind the FPY.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SiteFamilyStratum {
    pub site_id: Uuid,
    pub product_family_id: Option<Uuid>,
    pub fpy: f64,
    pub sample_size: i64,
}

/// The EXACT definition used for one metric (sixteenth audit items
/// 25-28): `metric_id` + `definition_note` — the audit demands honesty
/// about what each number means, approximations included.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct MetricDefinitionNote {
    pub metric_id: String,
    pub definition_note: String,
}

/// The corporate cross-site view. `stratified` carries the per-site FPY
/// WITHIN the same product family — the shape EXISTS so consumers cannot
/// silently build a naive leaderboard; `definitions` documents the exact
/// definition of every metric; `guidance` carries the standing warning
/// plus per-site evidence.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CrossSiteAnalytics {
    pub site_rows: Vec<SiteRow>,
    pub stratified: Vec<SiteFamilyStratum>,
    pub definitions: Vec<MetricDefinitionNote>,
    pub guidance: Vec<String>,
}

/// One causal hypothesis for a metric gap. `epistemic_status` is ALWAYS
/// "hypothesis" — the corporate layer surfaces candidates and evidence,
/// and the local site (not headquarters) verifies which one applies.
/// Each candidate carries CANDIDATE-SPECIFIC evidence (sixteenth audit
/// items 74-75): `supporting_evidence` = observations consistent with
/// THIS hypothesis, `contradicting_evidence` = observations showing the
/// opposite, `missing_evidence` = the fields that would confirm it (the
/// hypothesis is never presented as a root cause when the data cannot
/// distinguish — supporting/contradicting stay empty then), and
/// `next_test` = a concrete deterministic next step. `evidence` keeps the
/// shared observable context (lessons, episodes, event counts).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CausalCandidate {
    pub hypothesis: String,
    pub evidence: Vec<String>,
    pub supporting_evidence: Vec<String>,
    pub contradicting_evidence: Vec<String>,
    pub missing_evidence: Vec<String>,
    pub next_test: Option<String>,
    pub epistemic_status: String,
}

/// The answer to "Why is Bizerte better at changeovers?" — a question, a
/// set of hypotheses, and the evidence each one stands on.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CausalChain {
    pub question: String,
    pub candidates: Vec<CausalCandidate>,
}

/// Transaction-scoped tenant context for RLS — same convention as
/// `crates/sensei-services/src/tps/lessons.rs` (FAIL-CLOSED: missing
/// context = no rows).
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

/// The standing corporate guidance: cross-site comparison is a
/// STRATIFIED investigation — only the same product family is comparable
/// across sites; never a naive leaderboard.
pub const STRATIFIED_GUIDANCE: &str =
    "stratified comparison: only compare the same product family across sites; \
     never a naive leaderboard — investigate the causal chain before concluding.";

/// The exact per-metric definitions used by the corporate rollup — these
/// are the same TRUE definitions the metric engine computes
/// (`crates/sensei-services/src/tps/metric_engine.rs`).
fn metric_definitions() -> Vec<MetricDefinitionNote> {
    vec![
        MetricDefinitionNote {
            metric_id: "fpy".to_string(),
            definition_note: "first-pass proxy: completed without scrap / completed \
                              (the schema has no unit-level first-pass quality signal — \
                              inspection_records are sample-based)"
                .to_string(),
        },
        MetricDefinitionNote {
            metric_id: "scrap_rate".to_string(),
            definition_note: "scrapped / completed (produced units)".to_string(),
        },
        MetricDefinitionNote {
            metric_id: "otd".to_string(),
            definition_note: "delivered / (delivered + pending_due) where delivered = status in \
                              ('shipped','delivered') and pending_due = the other non-cancelled, \
                              non-draft orders (confirmed, in_production, invoiced). \
                              sales_orders carry NO site scope in this schema, so OTD is \
                              tenant-level and reported identically for every site"
                .to_string(),
        },
        MetricDefinitionNote {
            metric_id: "lead_time".to_string(),
            definition_note: "manufacturing lead time proxy: delivered_at − created_at \
                              (updated_at of delivered orders − created_at — no shipped_at \
                              column exists). sales_orders carry NO site scope in this schema, \
                              so lead time is tenant-level and reported identically for every \
                              site"
                .to_string(),
        },
    ]
}

/// Cross-site analytics for the tenant, all in ONE tenant-scoped
/// transaction. Deterministic inputs, each with its TRUE definition:
///   - fpy = FIRST-PASS PROXY: completed without scrap / completed, from
///     `work_orders` per `site_id` (units passing without rework / units
///     entering is not directly available — there is no unit-level
///     first-pass quality signal; the approximation is documented);
///   - scrap_rate = quantity_scrapped / quantity_completed;
///   - otd = delivered / (delivered + pending_due) over `sales_orders`
///     (status in ('shipped','delivered') / non-cancelled, non-draft) —
///     TENANT-level: sales_orders carry no site scope;
///   - lead_time_days = manufacturing lead time proxy: AVG(updated_at −
///     created_at) of delivered sales orders in days — no shipped_at
///     column exists;
///   - complexity_index = AVG(standard_time) of routings for the site's
///     products (informational context only — it is NEVER divided into a
///     fraction, which would be dimensionally invalid);
///   - stratified = per-site FPY WITHIN each product family (join
///     products.product_family_id), so only the same family is compared
///     across sites — never a naive leaderboard.
///
/// Andon response counts per site are reported in `guidance` as a
/// responsiveness signal.
pub async fn cross_site_analytics(pool: &PgPool, tenant_id: Uuid) -> Result<CrossSiteAnalytics> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let sites: Vec<(Uuid, String)> = sqlx::query_as(
                "SELECT s.id, s.name FROM sites s \
                 WHERE s.tenant_id = $1 ORDER BY s.name ASC, s.id ASC",
            )
            .bind(tenant_id)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("corporate: sites: {e}")))?;

            // Tenant-level OTD: sales_orders carry NO site scope in this
            // schema, so the honest value is computed ONCE and reported
            // identically for every site row.
            let (delivered, eligible): (i64, i64) = sqlx::query_as(
                "SELECT COUNT(*) FILTER (WHERE status IN ('shipped','delivered'))::bigint, \
                        COUNT(*) FILTER (WHERE status NOT IN ('cancelled','draft'))::bigint \
                 FROM sales_orders \
                 WHERE tenant_id = $1",
            )
            .bind(tenant_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("corporate: sales orders: {e}")))?;
            let otd = if eligible > 0 {
                delivered as f64 / eligible as f64
            } else {
                0.0
            };

            // Tenant-level lead time: manufacturing lead time proxy,
            // delivered_at (updated_at) − created_at, in days.
            let lead_time_days: f64 = sqlx::query_scalar(
                "SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (so.updated_at - so.created_at)) \
                                     / 86400.0), 0)::float8 \
                 FROM sales_orders so \
                 WHERE so.tenant_id = $1 AND so.status IN ('shipped','delivered')",
            )
            .bind(tenant_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("corporate: lead time: {e}")))?;

            let mut site_rows = Vec::with_capacity(sites.len());
            let mut guidance = Vec::new();
            for (site_id, site_name) in &sites {
                // Deterministic work-order aggregate: completed-without-
                // scrap units, completed units, scrapped units and the
                // complexity proxy (informational only).
                let (good_units, completed_units, scrapped_units, complexity): (
                    i64,
                    i64,
                    i64,
                    f64,
                ) = sqlx::query_as(
                    "SELECT COALESCE(SUM(GREATEST(wo.quantity_completed \
                                                       - wo.quantity_scrapped, 0)), 0)::bigint, \
                                COALESCE(SUM(wo.quantity_completed), 0)::bigint, \
                                COALESCE(SUM(wo.quantity_scrapped), 0)::bigint, \
                                COALESCE((SELECT AVG(r.standard_time) \
                                          FROM routings r \
                                          WHERE r.tenant_id = $1 \
                                            AND r.product_id IN ( \
                                                SELECT DISTINCT w.product_id \
                                                FROM work_orders w \
                                                WHERE w.tenant_id = $1 \
                                                  AND w.site_id = $2)) \
                                         , 0)::float8 \
                         FROM work_orders wo \
                         WHERE wo.tenant_id = $1 AND wo.site_id = $2 \
                           AND wo.status <> 'cancelled'",
                )
                .bind(tenant_id)
                .bind(site_id)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("corporate: work orders for {site_name}: {e}"))
                })?;

                // Andon response count per site (a responsiveness signal).
                let (andons_total, andons_resolved): (i64, i64) = sqlx::query_as(
                    "SELECT COUNT(*)::bigint, \
                            COUNT(*) FILTER (WHERE a.status = 'resolved')::bigint \
                     FROM andons a WHERE a.tenant_id = $1 AND a.site_id = $2",
                )
                .bind(tenant_id)
                .bind(site_id)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("corporate: andons for {site_name}: {e}"))
                })?;

                let fpy = if completed_units > 0 {
                    good_units as f64 / completed_units as f64
                } else {
                    0.0
                };
                let scrap_rate = if completed_units > 0 {
                    scrapped_units as f64 / completed_units as f64
                } else {
                    0.0
                };

                site_rows.push(SiteRow {
                    site_id: *site_id,
                    site_name: site_name.clone(),
                    fpy,
                    scrap_rate,
                    otd,
                    lead_time_days,
                    complexity_index: complexity,
                });
                guidance.push(format!(
                    "{site_name}: {andons_total} andons raised, {andons_resolved} resolved \
                     — response count signal"
                ));
            }

            // STRATIFIED comparison: FPY per site WITHIN each product
            // family — only the same family is comparable across sites.
            let strata_rows: Vec<(Uuid, Option<Uuid>, i64, i64)> = sqlx::query_as(
                "SELECT wo.site_id, p.product_family_id, \
                        COALESCE(SUM(GREATEST(wo.quantity_completed \
                                               - wo.quantity_scrapped, 0)), 0)::bigint, \
                        COALESCE(SUM(wo.quantity_completed), 0)::bigint \
                 FROM work_orders wo \
                 LEFT JOIN products p ON p.id = wo.product_id \
                                      AND p.tenant_id = wo.tenant_id \
                 WHERE wo.tenant_id = $1 AND wo.status <> 'cancelled' \
                 GROUP BY wo.site_id, p.product_family_id \
                 ORDER BY wo.site_id ASC, p.product_family_id ASC",
            )
            .bind(tenant_id)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("corporate: strata: {e}")))?;
            let stratified = strata_rows
                .into_iter()
                .map(
                    |(site_id, product_family_id, good_units, completed_units)| SiteFamilyStratum {
                        site_id,
                        product_family_id,
                        fpy: if completed_units > 0 {
                            good_units as f64 / completed_units as f64
                        } else {
                            0.0
                        },
                        sample_size: completed_units,
                    },
                )
                .collect();

            guidance.push(STRATIFIED_GUIDANCE.to_string());
            if site_rows.len() < 2 {
                guidance.push("insufficient sites for comparison".to_string());
            }

            Ok(CrossSiteAnalytics {
                site_rows,
                stratified,
                definitions: metric_definitions(),
                guidance,
            })
        })
    })
    .await
}

/// Deterministic hypothesis generation for a metric gap (item 67): the
/// question is answered with HYPOTHESES and evidence, never with facts.
/// Evidence is drawn from the operational event log (event_type counts
/// per site), the lesson registry (context_signature process) and the
/// episode memory (process links). Each candidate carries CANDIDATE-
/// SPECIFIC evidence (items 74-75): supporting/contradicting/missing
/// observations plus a next test, queried per hypothesis against the
/// event payloads — never the same blob for every candidate — and
/// `epistemic_status` is always "hypothesis".
pub async fn causal_candidates(
    pool: &PgPool,
    tenant_id: Uuid,
    metric_gap: &str,
    object_type: &str,
) -> Result<CausalChain> {
    let question =
        format!("Why is {metric_gap} performance better at one site than another ({object_type})?");
    let gap = metric_gap.to_string();
    let object = object_type.to_string();

    let candidates = with_tenant_tx(pool, tenant_id, move |tx| {
        let gap = gap.clone();
        let object = object.clone();
        Box::pin(async move {
            // Relevant event counts per site for the gapped event type.
            let events: Vec<(Option<Uuid>, i64)> = sqlx::query_as(
                "SELECT scope_site_id, COUNT(*)::bigint \
                 FROM operational_events \
                 WHERE tenant_id = $1 AND event_type = $2 \
                 GROUP BY scope_site_id ORDER BY scope_site_id NULLS LAST",
            )
            .bind(tenant_id)
            .bind(&gap)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("corporate: causal events: {e}")))?;

            // Lessons whose context signature names the object's process.
            let lesson_titles: Vec<String> = sqlx::query_scalar(
                "SELECT title FROM lessons \
                 WHERE tenant_id = $1 AND context_signature->>'process' = $2 \
                 ORDER BY created_at ASC",
            )
            .bind(tenant_id)
            .bind(&object)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("corporate: causal lessons: {e}")))?;

            // Episodes linked to the process (kind = 'process', label or
            // id matching the object type).
            let episode_titles: Vec<String> = sqlx::query_scalar(
                "SELECT title FROM episodes \
                 WHERE tenant_id = $1 AND EXISTS ( \
                     SELECT 1 FROM jsonb_array_elements(links) l \
                     WHERE l->>'kind' = 'process' \
                       AND (l->>'label' = $2 OR l->>'id' = $2)) \
                 ORDER BY occurred_at ASC",
            )
            .bind(tenant_id)
            .bind(&object)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("corporate: causal episodes: {e}")))?;

            let mut evidence = Vec::new();
            for title in lesson_titles {
                evidence.push(format!("lesson: {title}"));
            }
            for title in episode_titles {
                evidence.push(format!("episode: {title}"));
            }
            for (site_id, count) in events {
                let site = site_id
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| "unassigned".to_string());
                evidence.push(format!("{count} {gap} events at site {site}"));
            }

            // Deterministic candidate set for changeover gaps (item 67);
            // other gaps get one generic causal candidate rather than an
            // invented list. Each hypothesis carries CANDIDATE-SPECIFIC
            // evidence (sixteenth audit items 74-75): the event payload
            // keys that would support or contradict IT, the fields that
            // are missing, and a concrete next test — never the same blob
            // for every candidate. When the data cannot distinguish,
            // supporting/contradicting stay empty and missing_evidence
            // says what would decide; the hypothesis is never presented
            // as a root cause.
            let candidates = if gap == "changeover" {
                // Per-site counts of events whose payload carries the
                // hypothesis's confirming field.
                async fn key_presence(
                    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
                    tenant_id: Uuid,
                    event_type: &str,
                    key: &str,
                ) -> std::result::Result<Vec<(String, i64)>, sqlx::Error> {
                    sqlx::query_as(
                        "SELECT COALESCE(s.name, 'unassigned'), COUNT(*)::bigint \
                         FROM operational_events e \
                         LEFT JOIN sites s ON s.id = e.scope_site_id \
                                      AND s.tenant_id = e.tenant_id \
                         WHERE e.tenant_id = $1 AND e.event_type = $2 AND e.payload ? $3 \
                         GROUP BY s.name ORDER BY s.name NULLS LAST",
                    )
                    .bind(tenant_id)
                    .bind(event_type)
                    .bind(key)
                    .fetch_all(&mut **tx)
                    .await
                }
                // Per-site counts of events whose payload key equals a
                // specific value (e.g. pre_staged=true vs false).
                async fn key_value_counts(
                    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
                    tenant_id: Uuid,
                    event_type: &str,
                    key: &str,
                    value: &str,
                ) -> std::result::Result<Vec<(String, i64)>, sqlx::Error> {
                    sqlx::query_as(
                        "SELECT COALESCE(s.name, 'unassigned'), COUNT(*)::bigint \
                         FROM operational_events e \
                         LEFT JOIN sites s ON s.id = e.scope_site_id \
                                      AND s.tenant_id = e.tenant_id \
                         WHERE e.tenant_id = $1 AND e.event_type = $2 \
                           AND payload->>$3 = $4 \
                         GROUP BY s.name ORDER BY s.name NULLS LAST",
                    )
                    .bind(tenant_id)
                    .bind(event_type)
                    .bind(key)
                    .bind(value)
                    .fetch_all(&mut **tx)
                    .await
                }
                // (distinct recorded values, rows carrying the key) — one
                // distinct value across sites CONTRADICTS the hypothesis.
                async fn key_value_span(
                    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
                    tenant_id: Uuid,
                    event_type: &str,
                    key: &str,
                ) -> std::result::Result<(i64, i64), sqlx::Error> {
                    sqlx::query_as(
                        "SELECT COUNT(DISTINCT payload->>$3)::bigint, COUNT(*)::bigint \
                         FROM operational_events \
                         WHERE tenant_id = $1 AND event_type = $2 AND payload ? $3",
                    )
                    .bind(tenant_id)
                    .bind(event_type)
                    .bind(key)
                    .fetch_one(&mut **tx)
                    .await
                }
                // Average recorded duration_seconds for pre-staged events.
                async fn avg_duration(
                    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
                    tenant_id: Uuid,
                    event_type: &str,
                    staged: bool,
                ) -> std::result::Result<f64, sqlx::Error> {
                    sqlx::query_scalar(
                        "SELECT COALESCE(AVG((payload->>'duration_seconds')::float8), 0)::float8 \
                         FROM operational_events \
                         WHERE tenant_id = $1 AND event_type = $2 \
                           AND payload ? 'duration_seconds' \
                           AND payload->>'pre_staged' = $3",
                    )
                    .bind(tenant_id)
                    .bind(event_type)
                    .bind(if staged { "true" } else { "false" })
                    .fetch_one(&mut **tx)
                    .await
                }

                let mut out = Vec::new();
                for (hypothesis, key, meaning, confirm, test) in [
                    (
                        "setup sequence differs (check episodes/lessons with process changeover)",
                        "setup_sequence",
                        "the recorded setup sequence per site differs",
                        "a recorded setup sequence per changeover would decide",
                        "record the setup sequence of 10 comparable changeovers at each site and compare the step lists",
                    ),
                    (
                        "pre-staging differs",
                        "pre_staged",
                        "pre-staging is applied at one site, not the other",
                        "a staging flag per changeover would decide",
                        "measure 10 comparable changeovers with identical staging condition at each site and compare durations",
                    ),
                    (
                        "skill mix differs (check skills coverage)",
                        "operator_skills",
                        "operator skill coverage differs between sites",
                        "operator-skill tags per changeover would decide",
                        "certify the operator skill coverage of the changeover teams at each site and compare",
                    ),
                    (
                        "fixture design differs",
                        "fixture_id",
                        "different fixtures are used across sites",
                        "fixture identifiers per changeover would decide",
                        "run the same changeover with the same fixture at both sites and compare durations",
                    ),
                ] {
                    let mut supporting = Vec::new();
                    let mut contradicting = Vec::new();
                    let mut missing = Vec::new();

                    let present = key_presence(tx, tenant_id, &gap, key)
                        .await
                        .map_err(|e| SenseiError::Database(format!("corporate: causal {key}: {e}")))?;
                    for (site, count) in &present {
                        supporting.push(format!(
                            "{count} {gap} event(s) at site {site} record '{key}' — {meaning}"
                        ));
                    }
                    let (distinct, total) = key_value_span(tx, tenant_id, &gap, key)
                        .await
                        .map_err(|e| SenseiError::Database(format!("corporate: causal {key} span: {e}")))?;
                    if total > 0 && distinct == 1 {
                        contradicting.push(format!(
                            "all {total} {gap} events record the SAME '{key}' value — the condition does not differ between sites"
                        ));
                    }
                    if present.is_empty() {
                        missing.push(format!("no {gap} event records '{key}' — {confirm}"));
                    }

                    // The pre-staging hypothesis is also checked against
                    // durations: changeovers WITHOUT pre-staging that are
                    // still fast CONTRADICT it.
                    if key == "pre_staged" {
                        let staged = key_value_counts(tx, tenant_id, &gap, "pre_staged", "true")
                            .await
                            .map_err(|e| SenseiError::Database(format!("corporate: causal staged: {e}")))?;
                        let unstaged = key_value_counts(tx, tenant_id, &gap, "pre_staged", "false")
                            .await
                            .map_err(|e| SenseiError::Database(format!("corporate: causal unstaged: {e}")))?;
                        for (site, count) in &staged {
                            supporting.push(format!(
                                "{count} {gap} event(s) at site {site} are pre-staged (pre_staged=true)"
                            ));
                        }
                        for (site, count) in &unstaged {
                            contradicting.push(format!(
                                "{count} {gap} event(s) at site {site} run WITHOUT pre-staging (pre_staged=false) — the opposite condition"
                            ));
                        }
                        let staged_avg = avg_duration(tx, tenant_id, &gap, true)
                            .await
                            .map_err(|e| SenseiError::Database(format!("corporate: causal staged avg: {e}")))?;
                        let unstaged_avg = avg_duration(tx, tenant_id, &gap, false)
                            .await
                            .map_err(|e| SenseiError::Database(format!("corporate: causal unstaged avg: {e}")))?;
                        if staged_avg > 0.0 && unstaged_avg > 0.0 {
                            if unstaged_avg < staged_avg {
                                contradicting.push(format!(
                                    "changeovers WITHOUT pre-staging average {unstaged_avg:.0}s — FASTER than pre-staged {staged_avg:.0}s; pre-staging does not explain the gap"
                                ));
                            } else {
                                supporting.push(format!(
                                    "pre-staged changeovers average {staged_avg:.0}s vs {unstaged_avg:.0}s without — pre-staging correlates with the gap"
                                ));
                            }
                        }
                    }

                    // The field that would CONFIRM staging effort is absent
                    // from every changeover payload — that absence is the
                    // missing evidence for the staging hypotheses.
                    let (_, prep_total) = key_value_span(tx, tenant_id, &gap, "fixture_prep_seconds")
                        .await
                        .map_err(|e| SenseiError::Database(format!("corporate: causal prep: {e}")))?;
                    if prep_total == 0 {
                        missing.push(
                            "fixture-preparation timestamps ('fixture_prep_seconds') are absent \
                             from changeover payloads — they would confirm staging effort"
                                .to_string(),
                        );
                    }

                    out.push(CausalCandidate {
                        hypothesis: hypothesis.to_string(),
                        evidence: evidence.clone(),
                        supporting_evidence: supporting,
                        contradicting_evidence: contradicting,
                        missing_evidence: missing,
                        next_test: Some(test.to_string()),
                        epistemic_status: "hypothesis".to_string(),
                    });
                }
                out
            } else {
                vec![CausalCandidate {
                    hypothesis: format!(
                        "{object} {gap} root cause differs — compare operational events, \
                         lessons and episodes"
                    ),
                    evidence: evidence.clone(),
                    supporting_evidence: evidence.clone(),
                    contradicting_evidence: Vec::new(),
                    missing_evidence: vec![format!(
                        "operational_events payloads record no per-site '{gap}' field — \
                         capturing {gap} inputs per event would decide"
                    )],
                    next_test: Some(format!(
                        "run the {object} {gap} process at both sites with identical inputs \
                         and compare outcomes"
                    )),
                    epistemic_status: "hypothesis".to_string(),
                }]
            };

            Ok(candidates)
        })
    })
    .await?;

    Ok(CausalChain {
        question,
        candidates,
    })
}

/// Corporate yokoten propagation (item 46 / law A19): copy a lesson from
/// THIS tenant into the TARGET tenant as `proposed` with `origin_site_id`
/// set to the source site — the transfer is an OFFER, and the target
/// tenant verifies applicability locally via its own lesson endpoints.
/// RLS forbids cross-tenant reads, so the copy runs in two tenant-scoped
/// transactions: the read under the SOURCE context, the insert under the
/// TARGET context. Idempotent on (tenant_id, lesson_id) via upsert.
pub async fn propagate_lesson(
    pool: &PgPool,
    source_tenant_id: Uuid,
    target_tenant_id: Uuid,
    lesson_id: Uuid,
) -> Result<Uuid> {
    // Transaction 1: read the lesson under the SOURCE tenant's context.
    let lesson = lessons::get_lesson(pool, source_tenant_id, lesson_id).await?;

    // Transaction 2: insert the copy under the TARGET tenant's context.
    let id = Uuid::new_v4();
    let lesson_id = lesson.lesson_id.clone();
    let title = lesson.title.clone();
    with_tenant_tx(pool, target_tenant_id, move |tx| {
        Box::pin(async move {
            sqlx::query(
                "INSERT INTO lessons \
                     (id, tenant_id, lesson_id, title, source_problem_id, context_signature, \
                      hypothesis, countermeasure, observed_result, confidence, applicability, \
                      status, origin_site_id) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'proposed', $12) \
                 ON CONFLICT (tenant_id, lesson_id) DO UPDATE SET \
                     title = EXCLUDED.title, \
                     source_problem_id = EXCLUDED.source_problem_id, \
                     context_signature = EXCLUDED.context_signature, \
                     hypothesis = EXCLUDED.hypothesis, \
                     countermeasure = EXCLUDED.countermeasure, \
                     observed_result = EXCLUDED.observed_result, \
                     confidence = EXCLUDED.confidence, \
                     applicability = EXCLUDED.applicability, \
                     origin_site_id = EXCLUDED.origin_site_id, \
                     status = 'proposed', \
                     updated_at = NOW()",
            )
            .bind(id)
            .bind(target_tenant_id)
            .bind(&lesson_id)
            .bind(&title)
            .bind(lesson.source_problem_id)
            .bind(lesson.context_signature.clone())
            .bind(&lesson.hypothesis)
            .bind(&lesson.countermeasure)
            .bind(lesson.observed_result.clone())
            .bind(lesson.confidence)
            .bind(lesson.applicability.clone())
            .bind(lesson.origin_site_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("corporate: propagate lesson failed: {e}"))
            })?;
            Ok(id)
        })
    })
    .await
}
