//! Context Kernel compact live bundle (sixteenth audit 8/96): the
//! deterministic plan decides what live tenant state is fetched BEFORE
//! generation — the model receives the authoritative bundle as context,
//! it never invents the retrieval strategy. Every fact carries its
//! section name and the `[live]` authority tag so the model can
//! distinguish authoritative current state from its own inference.
//!
//! Twenty-fifth audit: section identity is ALSO carried as TYPED facts
//! ([`ContextFact`] / [`build_context_facts`]) — a flat string is never
//! the source of truth for scope, so a site-marked section can neither be
//! dropped by string parsing nor stripped of its source site. The string
//! bundle ([`build_compact_context`]) is now a pure rendering of the same
//! facts for callers that still consume lines.
//!
//! Thirtieth audit item 23: the typed facts are FULLY typed — each fact
//! carries its [`FactAddress`] (object_type/object_id/attribute), its
//! TYPED value, its unit and its source observation time; `display_text`
//! is the model rendering ONLY. The model-facing verifier checks claims
//! against the typed fields (address/operator/value/unit/observed_at),
//! never against the sentence language.

use sensei_agent_core::context::{ContextPlan, TaskKind};
use sensei_agent_core::facts::FactDerivation;
use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

/// Soft cap on the bundle: ~600 tokens ≈ 2400 chars (1 token ≈ 4 chars).
const MAX_BUNDLE_CHARS: usize = 2400;
/// Per-line cap so one runaway row cannot exhaust the budget.
const MAX_LINE_CHARS: usize = 160;

/// One TYPED kernel fact (twenty-fifth audit + thirtieth audit item 23):
/// section, `FactAddress` (object/attribute), typed value, unit, source
/// site/work center and source observation time are DATA; `display_text`
/// is only the model rendering. `site_id` is the SOURCE site the fact was
/// retrieved under — `None` when the retrieval had no site scope, and the
/// caller must never substitute its own site afterwards.
/// `work_center_id` is the work center the fact was fetched under when
/// the section had one.
pub use sensei_agent_core::facts::ContextFact as KernelContextFact;

/// Re-exported under the historical name: the typed [`ContextFact`] is
/// the one and only authoritative fact type (agent-core).
pub use sensei_agent_core::facts::ContextFact;

/// The unit of measured production quantities.
const UNITS: &str = "units";

fn render_fact(fact: &ContextFact) -> String {
    line_at(&fact.section, &fact.display_text, fact.site_id)
}

/// Build the COMPACT authoritative context bundle for a plan — the
/// flat-line rendering of [`build_context_facts`] kept for callers that
/// consume strings (the API chat preparation prefers the typed facts).
/// The plan's `required` sections decide what is fetched; sections the
/// kernel does not support contribute a single "no additional context"
/// line. Fetches run in a tenant-scoped transaction (SET LOCAL
/// `app.tenant_id`) so the RLS fail-closed policies apply exactly as on
/// every other surface. The result is deterministic and bounded.
pub async fn build_compact_context(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    plan: &ContextPlan,
) -> Vec<String> {
    let facts = build_context_facts(pool, tenant_id, site_id, work_center_id, plan).await;
    // Deterministic token budget: drop lines (whole lines, never partial
    // rows) once the ~600 token cap is reached.
    let mut lines: Vec<String> = Vec::with_capacity(facts.len());
    let mut total: usize = 0;
    for fact in facts {
        let rendered = render_fact(&fact);
        let capped: String = rendered.chars().take(MAX_LINE_CHARS).collect();
        if total + capped.len() > MAX_BUNDLE_CHARS {
            break;
        }
        total += capped.len();
        lines.push(capped);
    }
    if lines.is_empty() {
        lines.push("no additional context for this task".to_string());
    }
    lines
}

/// Build the TYPED authoritative context facts for a plan (twenty-fifth
/// audit; thirtieth audit item 23): the section identity, the fact
/// address, the typed value/unit and the SOURCE site/work-center scope of
/// every fact are data — [`build_compact_context`] renders these facts to
/// strings and the API chat preparation consumes the facts directly, so
/// no caller ever has to re-derive identity by parsing markers out of a
/// line.
///
/// The plan's `required` sections decide what is fetched; sections the
/// kernel does not support contribute a single "no additional context"
/// fact. Live operational conditions are only fetched under a KNOWN
/// scope: a request with neither site nor work center fails closed with
/// an explicit "unavailable: no site scope for live conditions" fact
/// instead of degrading into a tenant-wide dump (twenty-fifth audit P0:
/// no scope leak).
pub async fn build_context_facts(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    plan: &ContextPlan,
) -> Vec<ContextFact> {
    let mut facts: Vec<ContextFact> = Vec::new();
    let mut no_context_emitted = false;

    for section in &plan.required {
        match section.as_str() {
            "current_work" if work_center_id.is_some() => {
                let wc = work_center_id.expect("guarded by match");
                // Twenty-fifth audit: the current-work facts are stamped
                // with the WORK CENTER'S OWN site (resolved from
                // work_centers.site_id inside the same tenant transaction)
                // so the evidence keeps its structural source-site
                // identity; rows under a site-less work center stay
                // site-less (honest — no scope laundering).
                match current_work_facts(pool, tenant_id, wc).await {
                    Ok((wc_site, contents)) => {
                        for mut fact in contents {
                            if fact.site_id.is_none() {
                                fact.site_id = wc_site;
                            }
                            facts.push(fact);
                        }
                    }
                    Err(e) => {
                        facts.push(ContextFact::measured(
                            section,
                            "work_center",
                            wc.to_string(),
                            "availability",
                            "unavailable",
                            None::<&str>,
                            site_id,
                            Some(wc),
                            None,
                            format!("unavailable ({e})"),
                        ));
                    }
                }
            }
            "live_state" => {
                // Twenty-fifth audit P0 (fail closed): with NO scope at
                // all, the section must never become tenant-wide by
                // accident — an unverifiable conditions dump is not
                // produced; the explicit fact tells the model why.
                if site_id.is_none() && work_center_id.is_none() {
                    facts.push(ContextFact::measured(
                        section,
                        "scope",
                        "live_state",
                        "availability",
                        "unavailable",
                        None::<&str>,
                        None,
                        None,
                        None,
                        "unavailable: no site scope for live conditions".to_string(),
                    ));
                    continue;
                }
                match live_state_facts(pool, tenant_id, site_id, work_center_id).await {
                    Ok(contents) => {
                        for mut fact in contents {
                            if fact.site_id.is_none() && fact.work_center_id.is_none() {
                                // The facts carry the scope the query ran
                                // under: a site-scoped query returns the
                                // site's conditions (site marker); a work
                                // center query without a site returns that
                                // work center's + corporate conditions with
                                // NO marker (no site identity to claim).
                                fact.site_id = site_id;
                                fact.work_center_id = work_center_id;
                            }
                            facts.push(fact);
                        }
                    }
                    Err(e) => {
                        facts.push(ContextFact::measured(
                            section,
                            "scope",
                            "live_state",
                            "availability",
                            "unavailable",
                            None::<&str>,
                            site_id,
                            work_center_id,
                            None,
                            format!("unavailable ({e})"),
                        ));
                    }
                }
            }
            "metric_tree" if plan.task == TaskKind::ExecutiveAnalysis => {
                // Twenty-fifth audit: the metric facts carry the site the
                // metric engine was scoped to. Thirtieth audit item 23:
                // metric values are DERIVED facts — they carry the
                // deterministic derivation program id + version, and the
                // verifier re-runs that program before accepting any
                // derived claim.
                match metric_tree_facts(pool, tenant_id, site_id).await {
                    Ok(contents) => facts.extend(contents),
                    Err(e) => {
                        facts.push(ContextFact::measured(
                            section,
                            "metric",
                            "tree",
                            "availability",
                            "unavailable",
                            None::<&str>,
                            site_id,
                            None,
                            None,
                            format!("unavailable ({e})"),
                        ));
                    }
                }
            }
            _ => {
                if !no_context_emitted {
                    facts.push(ContextFact::measured(
                        section,
                        "context",
                        section.clone(),
                        "availability",
                        "no_additional_context",
                        None::<&str>,
                        None,
                        None,
                        None,
                        "no additional context for this task".to_string(),
                    ));
                    no_context_emitted = true;
                }
            }
        }
    }

    facts
}

/// Emit a live section line. When the section was produced under a
/// KNOWN source site, the site is embedded ("site:<uuid>") so the
/// evidence construction stamps the SOURCE site — a retrieval bug that
/// returns another site's row can never be relabeled with the request's
/// site (twenty-fourth audit: no scope laundering).
fn line_at(section: &str, content: impl AsRef<str>, source_site_id: Option<Uuid>) -> String {
    match source_site_id {
        Some(site) => format!("{section} [live site:{site}]: {}", content.as_ref()),
        None => line(section, content),
    }
}

/// One bundle line: section name + `[live]` authority tag + content.
fn line(section: &str, content: impl AsRef<str>) -> String {
    format!("{section} [live]: {}", content.as_ref())
}

/// `current_work`: the in_progress work order (wo, product,
/// completed/quantity) and the open andons at the work center
/// (andon, issue, severity) — LIMIT 3 each, newest first.
///
/// Thirtieth audit item 23: every row becomes a TYPED fact — the work
/// order's `quantity_completed` (units) and the andon's `status` carry
/// typed addresses/values/units/observed_at; the rendered text stays the
/// flat line grammar. Returns the work center's OWN site
/// (work_centers.site_id — the site the current work belongs to)
/// alongside the facts.
async fn current_work_facts(
    pool: &PgPool,
    tenant_id: Uuid,
    work_center_id: Uuid,
) -> Result<(Option<Uuid>, Vec<ContextFact>)> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let wc_site: Option<Uuid> = sqlx::query_scalar::<_, Option<Uuid>>(
                "SELECT site_id FROM work_centers WHERE tenant_id = $1 AND id = $2",
            )
            .bind(tenant_id)
            .bind(work_center_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("context kernel: work center site: {e}")))?
            .flatten();
            let mut facts: Vec<ContextFact> = Vec::new();
            let work_orders: Vec<(String, String, i64, i64, chrono::DateTime<chrono::Utc>)> =
                sqlx::query_as(
                    "SELECT wo_number, product_name, quantity_completed, quantity, updated_at \
                     FROM work_orders \
                     WHERE tenant_id = $1 AND work_center_id = $2 AND status = 'in_progress' \
                     ORDER BY created_at DESC LIMIT 3",
                )
                .bind(tenant_id)
                .bind(work_center_id)
                .fetch_all(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("context kernel: current work orders: {e}"))
                })?;
            for (wo_number, product, completed, quantity, updated_at) in work_orders {
                let display = format!(
                    "wo={wo_number} product={product} completed={completed}/{quantity}"
                );
                facts.push(ContextFact::measured(
                    "current_work",
                    "work_order",
                    wo_number,
                    "quantity_completed",
                    completed,
                    Some(UNITS),
                    None, // stamped by the caller with wc_site
                    Some(work_center_id),
                    Some(updated_at),
                    display,
                ));
            }
            let andons: Vec<(String, String, String, String, chrono::DateTime<chrono::Utc>)> =
                sqlx::query_as(
                    "SELECT andon_number, issue_type, severity, status, created_at \
                     FROM andons \
                     WHERE tenant_id = $1 AND work_center_id = $2 \
                       AND status IN ('active', 'acknowledged') \
                     ORDER BY created_at DESC LIMIT 3",
                )
                .bind(tenant_id)
                .bind(work_center_id)
                .fetch_all(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("context kernel: open andons: {e}")))?;
            for (andon_number, issue_type, severity, status, created_at) in andons {
                let display =
                    format!("andon={andon_number} issue={issue_type} severity={severity}");
                facts.push(ContextFact::measured(
                    "current_work",
                    "andon",
                    andon_number,
                    "status",
                    status,
                    None::<&str>,
                    None, // stamped by the caller with wc_site
                    Some(work_center_id),
                    Some(created_at),
                    display,
                ));
            }
            Ok((wc_site, facts))
        })
    })
    .await
}

/// `live_state`: the open operational conditions (condition, status,
/// recurrence) — LIMIT 3, newest first. Twenty-fifth audit P0 (scope
/// leak fix): the query is scoped by the caller's SITE and WORK CENTER,
/// never tenant-wide:
/// - site Some: `AND scope_site_id = $site` (plus `scope_work_center_id`
///   when a work center is given) — another site's conditions can never
///   leak into this site's live state;
/// - site None + work center Some: that work center's own conditions plus
///   explicitly corporate conditions (both scope columns NULL) — still
///   never a tenant-wide dump;
/// - site None + work center None: guarded by [`build_context_facts`],
///   which fails closed before this query runs.
///
/// Thirtieth audit item 23: each condition becomes a TYPED fact on the
/// `recurrence_count` attribute (the measured second family) with the
/// row's `updated_at` as the source observation time.
async fn live_state_facts(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
) -> Result<Vec<ContextFact>> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let (sql, bind_site, bind_wc) = match (site_id, work_center_id) {
                (Some(_site), Some(_wc)) => (
                    "SELECT condition_number, status, \
                            COALESCE(learning ->> 'recurrence_count', '0')::bigint, \
                            COALESCE(updated_at, created_at) \
                     FROM operational_conditions \
                     WHERE tenant_id = $1 \
                       AND scope_site_id = $2 AND scope_work_center_id = $3 \
                       AND status IN ('open', 'responding', 'contained', 'investigating') \
                     ORDER BY created_at DESC LIMIT 3",
                    true,
                    true,
                ),
                (Some(_site), None) => (
                    "SELECT condition_number, status, \
                            COALESCE(learning ->> 'recurrence_count', '0')::bigint, \
                            COALESCE(updated_at, created_at) \
                     FROM operational_conditions \
                     WHERE tenant_id = $1 \
                       AND scope_site_id = $2 \
                       AND status IN ('open', 'responding', 'contained', 'investigating') \
                     ORDER BY created_at DESC LIMIT 3",
                    true,
                    false,
                ),
                (None, Some(_wc)) => (
                    "SELECT condition_number, status, \
                            COALESCE(learning ->> 'recurrence_count', '0')::bigint, \
                            COALESCE(updated_at, created_at) \
                     FROM operational_conditions \
                     WHERE tenant_id = $1 \
                       AND (scope_work_center_id = $2 OR \
                            (scope_work_center_id IS NULL AND scope_site_id IS NULL)) \
                       AND status IN ('open', 'responding', 'contained', 'investigating') \
                     ORDER BY created_at DESC LIMIT 3",
                    false,
                    true,
                ),
                (None, None) => return Ok(Vec::new()),
            };
            let mut query = sqlx::query_as::<
                _,
                (String, String, i64, chrono::DateTime<chrono::Utc>),
            >(sql)
            .bind(tenant_id);
            if bind_site {
                query = query.bind(site_id.expect("guarded by match"));
            }
            if bind_wc {
                query = query.bind(work_center_id.expect("guarded by match"));
            }
            let conditions = query.fetch_all(&mut **tx).await.map_err(|e| {
                SenseiError::Database(format!("context kernel: operational conditions: {e}"))
            })?;
            let mut facts: Vec<ContextFact> = Vec::new();
            for (condition_number, status, recurrence_count, source_time) in conditions {
                let display = format!(
                    "condition={condition_number} status={status} recurrence={recurrence_count}"
                );
                facts.push(ContextFact::measured(
                    "live_state",
                    "operational_condition",
                    condition_number,
                    "recurrence_count",
                    recurrence_count,
                    None::<&str>,
                    None, // stamped by the caller from the query scope
                    None,
                    Some(source_time),
                    display,
                ));
            }
            Ok(facts)
        })
    })
    .await
}

/// `metric_tree` (ExecutiveAnalysis only): the metric engine values for
/// fpy + otd — the SAME executable definitions every surface uses,
/// computed under the caller's site when one is given.
///
/// Thirtieth audit item 23: metric values are DERIVED facts — each typed
/// fact records the deterministic derivation program (`derivation_id` =
/// the canonical metric id, `derivation_version` = the program version)
/// so the verifier can re-run the program before accepting a derived
/// claim. `observed_at` is the computation time of the metric engine.
async fn metric_tree_facts(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
) -> Result<Vec<ContextFact>> {
    let mut facts: Vec<ContextFact> = Vec::new();
    for metric_id in ["fpy", "otd"] {
        match super::metric_engine::compute_metric(pool, tenant_id, metric_id, site_id).await {
            Ok(result) => {
                // The version of the deterministic program that produced
                // this value (registry lookup by the canonical metric id).
                let version = super::metric_engine::registry()
                    .into_iter()
                    .find(|c| c.id() == result.metric_id)
                    .map(|c| c.version());
                let value = serde_json::to_value(&result.value)
                    .unwrap_or(serde_json::Value::Null);
                let mut fact = ContextFact::measured(
                    "metric_tree",
                    "metric",
                    result.metric_id.clone(),
                    "value",
                    value,
                    Some(result.unit.clone()),
                    site_id,
                    None,
                    Some(result.computed_at),
                    format!(
                        "metric_id={} value={} unit={}",
                        result.metric_id, result.value, result.unit
                    ),
                );
                if let Some(version) = version {
                    fact.derivation = Some(FactDerivation {
                        derivation_id: result.metric_id,
                        derivation_version: version,
                    });
                }
                facts.push(fact);
            }
            Err(e) => facts.push(ContextFact::measured(
                "metric_tree",
                "metric",
                metric_id,
                "value",
                "unavailable",
                None::<&str>,
                site_id,
                None,
                None,
                format!("metric_id={metric_id} unavailable ({e})"),
            )),
        }
    }
    Ok(facts)
}

/// Transaction-scoped tenant context for RLS — same convention as
/// `crates/sensei-services/src/tps/corporate.rs` (FAIL-CLOSED: missing
/// context = no rows).
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> Result<()> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("context kernel: set tenant context: {e}")))?;
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
        .map_err(|e| SenseiError::Database(format!("context kernel: begin tenant tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let result = f(&mut tx).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("context kernel: commit tenant tx: {e}")))?;
    Ok(result)
}
