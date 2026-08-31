//! Context Kernel compact live bundle (sixteenth audit 8/96): the
//! deterministic plan decides what live tenant state is fetched BEFORE
//! generation — the model receives the authoritative bundle as context,
//! it never invents the retrieval strategy. Every line carries its
//! section name and the `[live]` authority tag so the model can
//! distinguish authoritative current state from its own inference.

use sensei_agent_core::context::{ContextPlan, TaskKind};
use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

/// Soft cap on the bundle: ~600 tokens ≈ 2400 chars (1 token ≈ 4 chars).
const MAX_BUNDLE_CHARS: usize = 2400;
/// Per-line cap so one runaway row cannot exhaust the budget.
const MAX_LINE_CHARS: usize = 160;

/// Build the COMPACT authoritative context bundle for a plan.
///
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
    let mut lines: Vec<String> = Vec::new();
    let mut no_context_emitted = false;

    for section in &plan.required {
        match section.as_str() {
            "current_work" if work_center_id.is_some() => {
                match current_work_lines(pool, tenant_id, work_center_id.expect("guarded")).await {
                    Ok(mut section_lines) => lines.append(&mut section_lines),
                    Err(e) => lines.push(line(section, format!("unavailable ({e})"))),
                }
            }
            "live_state" => match live_state_lines(pool, tenant_id).await {
                Ok(mut section_lines) => lines.append(&mut section_lines),
                Err(e) => lines.push(line(section, format!("unavailable ({e})"))),
            },
            "metric_tree" if plan.task == TaskKind::ExecutiveAnalysis => {
                match metric_tree_lines(pool, tenant_id, site_id).await {
                    Ok(mut section_lines) => lines.append(&mut section_lines),
                    Err(e) => lines.push(line(section, format!("unavailable ({e})"))),
                }
            }
            _ => {
                if !no_context_emitted {
                    lines.push(line(section, "no additional context for this task"));
                    no_context_emitted = true;
                }
            }
        }
    }

    if lines.is_empty() {
        lines.push("no additional context for this task".to_string());
    }

    // Deterministic token budget: drop lines (whole lines, never partial
    // rows) once the ~600 token cap is reached.
    let mut budgeted: Vec<String> = Vec::with_capacity(lines.len());
    let mut total: usize = 0;
    for content in lines {
        let capped: String = content.chars().take(MAX_LINE_CHARS).collect();
        if total + capped.len() > MAX_BUNDLE_CHARS {
            break;
        }
        total += capped.len();
        budgeted.push(capped);
    }
    budgeted
}

/// One bundle line: section name + `[live]` authority tag + content.
fn line(section: &str, content: impl AsRef<str>) -> String {
    format!("{section} [live]: {}", content.as_ref())
}

/// `current_work`: the in_progress work order (wo, product,
/// completed/quantity) and the open andons at the work center
/// (andon, issue, severity) — LIMIT 3 each, newest first.
async fn current_work_lines(
    pool: &PgPool,
    tenant_id: Uuid,
    work_center_id: Uuid,
) -> Result<Vec<String>> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let mut lines: Vec<String> = Vec::new();
            let work_orders: Vec<(String, String, i64, i64)> = sqlx::query_as(
                "SELECT wo_number, product_name, quantity_completed, quantity \
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
            for (wo_number, product, completed, quantity) in work_orders {
                lines.push(line(
                    "current_work",
                    format!("wo={wo_number} product={product} completed={completed}/{quantity}"),
                ));
            }
            let andons: Vec<(String, String, String)> = sqlx::query_as(
                "SELECT andon_number, issue_type, severity \
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
            for (andon_number, issue_type, severity) in andons {
                lines.push(line(
                    "current_work",
                    format!("andon={andon_number} issue={issue_type} severity={severity}"),
                ));
            }
            Ok(lines)
        })
    })
    .await
}

/// `live_state`: the open operational conditions (condition, status,
/// recurrence) — LIMIT 3, newest first.
async fn live_state_lines(pool: &PgPool, tenant_id: Uuid) -> Result<Vec<String>> {
    with_tenant_tx(pool, tenant_id, |tx| {
        Box::pin(async move {
            let conditions: Vec<(String, String, String)> = sqlx::query_as(
                "SELECT condition_number, status, \
                        COALESCE(learning ->> 'recurrence_count', '0') \
                 FROM operational_conditions \
                 WHERE tenant_id = $1 \
                   AND status IN ('open', 'responding', 'contained', 'investigating') \
                 ORDER BY created_at DESC LIMIT 3",
            )
            .bind(tenant_id)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("context kernel: operational conditions: {e}"))
            })?;
            let mut lines: Vec<String> = Vec::new();
            for (condition_number, status, recurrence_count) in conditions {
                lines.push(line(
                    "live_state",
                    format!(
                        "condition={condition_number} status={status} recurrence={recurrence_count}"
                    ),
                ));
            }
            Ok(lines)
        })
    })
    .await
}

/// `metric_tree` (ExecutiveAnalysis only): the metric engine values for
/// fpy + otd — the SAME executable definitions every surface uses.
async fn metric_tree_lines(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
) -> Result<Vec<String>> {
    let mut lines: Vec<String> = Vec::new();
    for metric_id in ["fpy", "otd"] {
        match super::metric_engine::compute_metric(pool, tenant_id, metric_id, site_id).await {
            Ok(result) => lines.push(line(
                "metric_tree",
                format!(
                    "metric_id={} value={} unit={}",
                    result.metric_id, result.value, result.unit
                ),
            )),
            Err(e) => lines.push(line(
                "metric_tree",
                format!("metric_id={metric_id} unavailable ({e})"),
            )),
        }
    }
    Ok(lines)
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
