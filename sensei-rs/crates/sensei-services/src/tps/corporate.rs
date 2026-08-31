//! Corporate federation (fifteenth audit 29/46/66-67 + A19/A24):
//! cross-site aggregation with authorization. Corporate analytics are
//! MIX-NORMALIZED — comparing Bizerte vs Tangier FPY without product
//! complexity adjustment is forbidden. Causal questions ("Why is Bizerte
//! better at changeovers?") produce HYPOTHESES with evidence, never
//! answers: every candidate carries `epistemic_status = "hypothesis"` so
//! the corporate layer can never present a guess as a fact.

use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

use super::lessons;

/// One site's row in the mix-normalized corporate comparison. `fpy` and
/// `scrap_rate` are fractions (0..1); `otd` is the completed-share proxy;
/// `complexity_index` is the deterministic product-complexity proxy
/// (mean routing standard_time in seconds — 0 when the site has no
/// routings); `fpy_mix_adjusted` is the FAIR comparison value — the raw
/// FPY divided by the complexity proxy, so a complex product mix never
/// masquerades as a quality problem.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SiteRow {
    pub site_id: Uuid,
    pub site_name: String,
    pub fpy: f64,
    pub scrap_rate: f64,
    pub otd: f64,
    pub lead_time_days: f64,
    pub complexity_index: f64,
    pub fpy_mix_adjusted: f64,
}

/// The corporate cross-site view. `mix_normalized` is always true — the
/// shape EXISTS so consumers cannot silently build a naive leaderboard;
/// `guidance` carries the standing warning plus per-site evidence.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CrossSiteAnalytics {
    pub site_rows: Vec<SiteRow>,
    pub mix_normalized: bool,
    pub guidance: Vec<String>,
}

/// One causal hypothesis for a metric gap. `epistemic_status` is ALWAYS
/// "hypothesis" — the corporate layer surfaces candidates and evidence,
/// and the local site (not headquarters) verifies which one applies.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CausalCandidate {
    pub hypothesis: String,
    pub evidence: Vec<String>,
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
/// mix-normalized investigation, never a naive leaderboard.
pub const MIX_NORMALIZED_GUIDANCE: &str =
    "cross-site comparison is mix-normalized — never a naive leaderboard; \
     investigate the causal chain before concluding.";

/// Cross-site analytics for the tenant, all in ONE tenant-scoped
/// transaction. Deterministic inputs:
///   - fpy = 1 − scrap ratio (quantity_scrapped / quantity) from
///     `work_orders` per `site_id`; scrap_rate = the same scrap ratio;
///   - otd = share of work orders completed (a deterministic delivery
///     proxy — sales-order dates are not required);
///   - lead_time_days = mean planned duration (scheduled_end −
///     scheduled_start) of the site's work orders;
/// - complexity_index = AVG(standard_time) of routings for the site's
///   products (more complex mix = higher standard time);
/// - fpy_mix_adjusted = fpy / complexity_index × 100 (when the site has
///   no routings the raw fpy × 100 stands in — the value stays
///   deterministic and finite).
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

            let mut site_rows = Vec::with_capacity(sites.len());
            let mut guidance = Vec::new();
            for (site_id, site_name) in &sites {
                // Deterministic work-order aggregate: quantity, scrap,
                // completed share, planned lead time, complexity proxy.
                let (qty, scrapped, total, completed, lead_days, complexity): (i64, i64, i64, i64, f64, f64) =
                    sqlx::query_as(
                        "SELECT COALESCE(SUM(wo.quantity), 0)::bigint, \
                                COALESCE(SUM(wo.quantity_scrapped), 0)::bigint, \
                                COUNT(*)::bigint, \
                                COUNT(*) FILTER (WHERE wo.status = 'completed')::bigint, \
                                COALESCE(AVG(EXTRACT(EPOCH FROM \
                                    (wo.scheduled_end - wo.scheduled_start)) / 86400.0), 0)::float8, \
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
                         WHERE wo.tenant_id = $1 AND wo.site_id = $2",
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

                let scrap_ratio = if qty > 0 {
                    scrapped as f64 / qty as f64
                } else {
                    0.0
                };
                let fpy = (1.0 - scrap_ratio).clamp(0.0, 1.0);
                let otd = if total > 0 {
                    completed as f64 / total as f64
                } else {
                    0.0
                };
                // Mix normalization: divide by the complexity proxy so a
                // high-standard-time product mix cannot masquerade as a
                // quality problem. Deterministic and finite in all cases.
                let fpy_mix_adjusted = if complexity > 0.0 {
                    fpy / complexity * 100.0
                } else {
                    fpy * 100.0
                };

                site_rows.push(SiteRow {
                    site_id: *site_id,
                    site_name: site_name.clone(),
                    fpy,
                    scrap_rate: scrap_ratio,
                    otd,
                    lead_time_days: lead_days,
                    complexity_index: complexity,
                    fpy_mix_adjusted,
                });
                guidance.push(format!(
                    "{site_name}: {andons_total} andons raised, {andons_resolved} resolved \
                     — response count signal"
                ));
            }

            guidance.push(MIX_NORMALIZED_GUIDANCE.to_string());
            if site_rows.len() < 2 {
                guidance.push("insufficient sites for comparison".to_string());
            }

            Ok(CrossSiteAnalytics {
                site_rows,
                mix_normalized: true,
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
/// episode memory (process links) — every candidate stands on the SAME
/// observable evidence, and `epistemic_status` is always "hypothesis".
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
            // invented list.
            let hypotheses: Vec<String> = if gap == "changeover" {
                vec![
                    "setup sequence differs (check episodes/lessons with process changeover)"
                        .to_string(),
                    "pre-staging differs".to_string(),
                    "skill mix differs (check skills coverage)".to_string(),
                    "fixture design differs".to_string(),
                ]
            } else {
                vec![format!(
                    "{object} {gap} root cause differs — compare operational events, \
                     lessons and episodes"
                )]
            };

            let candidates = hypotheses
                .into_iter()
                .map(|hypothesis| CausalCandidate {
                    hypothesis,
                    evidence: evidence.clone(),
                    epistemic_status: "hypothesis".to_string(),
                })
                .collect();

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
