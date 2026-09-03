//! Metric engine (sixteenth audit items 27-28): ONE executable
//! definition per metric — API, dashboard, AI and corporate rollup all
//! call the same engine. The database metric catalog (migration 115)
//! DESCRIBES; Rust COMPUTES. Unknown metric ids are a Validation error,
//! never a silent fallback.
//!
//! True definitions (audit items 25-28):
//!
//! - `fpy` — FIRST-PASS PROXY: completed without scrap / completed. The
//!   schema has no unit-level first-pass quality signal (inspection_records
//!   are sample-based), so the approximation is documented, not hidden.
//!   Rework is never treated as scrap.
//! - `scrap_rate` — scrapped / completed (produced units).
//! - `otd` — ON-TIME DELIVERY: deliveries at or before the immutable
//!   committed_date / all orders with a commitment. NOT a completion
//!   ratio — a late delivery never counts as on time. sales_orders carry
//!   a site scope (`fulfilling_site_id`, migration 139), honored by the
//!   metric when a site_id is bound.
//! - `lead_time` — MANUFACTURING LEAD TIME PROXY: delivered_at
//!   (updated_at) − created_at, in days — no shipped_at column exists.

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use rust_decimal::Decimal;

use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

/// One computed metric value with its data provenance: `sample_size` is
/// the population behind the value (units for work-order metrics, orders
/// for sales-order metrics) and `coverage` is the share of the in-scope
/// population whose data was valid for the metric.
#[derive(Debug, Clone, serde::Serialize)]
pub struct MetricResult {
    pub metric_id: String,
    pub value: Decimal,
    pub unit: String,
    pub period_start: DateTime<Utc>,
    pub period_end: DateTime<Utc>,
    pub sample_size: u64,
    pub coverage: f64,
    pub computed_at: DateTime<Utc>,
}

/// A versioned executable metric definition. The database metric catalog
/// DESCRIBES; the `compute` implementations below are the ONLY allowed
/// way to obtain a metric value.
#[async_trait]
pub trait MetricComputer: Send + Sync {
    fn id(&self) -> &'static str;
    fn version(&self) -> u32;
    async fn compute(
        &self,
        pool: &PgPool,
        tenant_id: Uuid,
        site_id: Option<Uuid>,
    ) -> Result<MetricResult>;
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
        .map_err(|e| SenseiError::Database(format!("metric engine: set tenant context: {e}")))?;
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
        .map_err(|e| SenseiError::Database(format!("metric engine: begin tenant tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let result = f(&mut tx).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("metric engine: commit tenant tx: {e}")))?;
    Ok(result)
}

/// Work-order scope shared by `fpy` and `scrap_rate`: non-cancelled work
/// orders of the tenant (optionally one site). `good_units` is completed
/// units that did NOT become scrap — the first-pass proxy numerator.
/// Returns (good_units, completed_units, scrapped_units, sample_units,
/// rows_in_scope, rows_valid, period_start, period_end) — sample units
/// are read as BIGINT so no Decimal conversion is needed.
async fn work_order_scope(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
) -> Result<(
    Decimal,
    Decimal,
    Decimal,
    i64,
    i64,
    i64,
    Option<DateTime<Utc>>,
    Option<DateTime<Utc>>,
)> {
    let site_clause = if site_id.is_some() {
        "AND wo.site_id = $2"
    } else {
        ""
    };
    let sql = format!(
        "SELECT COALESCE(SUM(GREATEST(wo.quantity_completed - wo.quantity_scrapped, 0)), 0)::numeric, \
                COALESCE(SUM(wo.quantity_completed), 0)::numeric, \
                COALESCE(SUM(wo.quantity_scrapped), 0)::numeric, \
                COALESCE(SUM(wo.quantity_completed), 0)::bigint, \
                COUNT(*)::bigint, \
                COUNT(*) FILTER (WHERE wo.quantity_completed > 0 \
                                 OR wo.quantity_scrapped > 0)::bigint, \
                MIN(wo.created_at), \
                MAX(wo.updated_at) \
         FROM work_orders wo \
         WHERE wo.tenant_id = $1 AND wo.status <> 'cancelled' {site_clause}"
    );
    let mut query = sqlx::query_as::<
        _,
        (
            Decimal,
            Decimal,
            Decimal,
            i64,
            i64,
            i64,
            Option<DateTime<Utc>>,
            Option<DateTime<Utc>>,
        ),
    >(&sql);
    query = query.bind(tenant_id);
    if let Some(site) = site_id {
        query = query.bind(site);
    }
    query
        .fetch_one(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("metric engine: work-order scope: {e}")))
}

/// PROCESS YIELD PROXY (sixteenth audit item 25):
/// `completed / (completed + scrapped)`.
///
/// quantity_completed is GOOD output and quantity_scrapped is a SEPARATE
/// count; the old (good − scrap)/good subtracted scrap twice. True
/// first-pass yield still needs unit-level first-pass data, so the metric
/// is named honestly — not called FPY.
pub struct FpyV1;

#[async_trait]
impl MetricComputer for FpyV1 {
    fn id(&self) -> &'static str {
        "process_yield_proxy"
    }

    fn version(&self) -> u32 {
        1
    }

    async fn compute(
        &self,
        pool: &PgPool,
        tenant_id: Uuid,
        site_id: Option<Uuid>,
    ) -> Result<MetricResult> {
        let metric_id = self.id().to_string();
        let computed_at = Utc::now();
        with_tenant_tx(pool, tenant_id, |tx| {
            Box::pin(async move {
                let (
                    _good_units,
                    completed_units,
                    _scrapped,
                    sample_units,
                    rows_in_scope,
                    rows_valid,
                    period_start,
                    period_end,
                ) = work_order_scope(tx, tenant_id, site_id).await?;
                let value = process_yield_ratio(completed_units, _scrapped);
                let sample_size = sample_units.max(0) as u64;
                let coverage = if rows_in_scope > 0 {
                    rows_valid as f64 / rows_in_scope as f64
                } else {
                    0.0
                };
                Ok(MetricResult {
                    metric_id,
                    value,
                    unit: "ratio".to_string(),
                    period_start: period_start.unwrap_or(computed_at),
                    period_end: period_end.unwrap_or(computed_at),
                    sample_size,
                    coverage,
                    computed_at,
                })
            })
        })
        .await
    }
}

/// SCRAP RATE: `quantity_scrapped / quantity_completed` (share of
/// produced units scrapped) — the same work-order scope as FPY.
pub struct ScrapRateV1;

#[async_trait]
impl MetricComputer for ScrapRateV1 {
    fn id(&self) -> &'static str {
        "scrap_rate"
    }

    fn version(&self) -> u32 {
        1
    }

    async fn compute(
        &self,
        pool: &PgPool,
        tenant_id: Uuid,
        site_id: Option<Uuid>,
    ) -> Result<MetricResult> {
        let metric_id = self.id().to_string();
        let computed_at = Utc::now();
        with_tenant_tx(pool, tenant_id, |tx| {
            Box::pin(async move {
                let (
                    _good_units,
                    completed_units,
                    scrapped,
                    sample_units,
                    rows_in_scope,
                    rows_valid,
                    period_start,
                    period_end,
                ) = work_order_scope(tx, tenant_id, site_id).await?;
                let value = scrap_ratio(scrapped, completed_units);
                let sample_size = sample_units.max(0) as u64;
                let coverage = if rows_in_scope > 0 {
                    rows_valid as f64 / rows_in_scope as f64
                } else {
                    0.0
                };
                Ok(MetricResult {
                    metric_id,
                    value,
                    unit: "ratio".to_string(),
                    period_start: period_start.unwrap_or(computed_at),
                    period_end: period_end.unwrap_or(computed_at),
                    sample_size,
                    coverage,
                    computed_at,
                })
            })
        })
        .await
    }
}

/// ON-TIME DELIVERY (audit item P1-8): REAL on-time delivery, not a
/// delivery-completion ratio. `delivered_on_time / eligible` where
/// delivered_on_time = orders delivered AT OR BEFORE their committed date
/// (status in ('shipped','delivered') AND actual_delivery_date <=
/// committed_date) and eligible = every order with a commitment
/// (status not in ('cancelled','draft') AND committed_date IS NOT NULL).
///
/// ANTI-GAMING RULE (migration 139): `committed_date` is immutable — it
/// is written ONCE at first confirmation by the executable
/// status-transition path (COALESCE in update_sales_order_status) and
/// never updated by later edits. The metric therefore cannot be improved
/// by editing dates: a late order stays late. sales_orders carry a site
/// scope (`fulfilling_site_id`, migration 139): when `site_id` is bound,
/// only orders that site fulfills count in BOTH the numerator
/// (delivered_on_time) and the denominator (eligible); `site_id = None`
/// keeps the tenant-level value.
pub struct OtdV1;

#[async_trait]
impl MetricComputer for OtdV1 {
    fn id(&self) -> &'static str {
        "otd"
    }

    fn version(&self) -> u32 {
        1
    }

    async fn compute(
        &self,
        pool: &PgPool,
        tenant_id: Uuid,
        site_id: Option<Uuid>,
    ) -> Result<MetricResult> {
        let metric_id = self.id().to_string();
        let computed_at = Utc::now();
        with_tenant_tx(pool, tenant_id, |tx| {
            Box::pin(async move {
                let (delivered_on_time, eligible, non_cancelled, period_start, period_end): (
                    i64,
                    i64,
                    i64,
                    Option<DateTime<Utc>>,
                    Option<DateTime<Utc>>,
                ) = sqlx::query_as(
                    "SELECT COUNT(*) FILTER (WHERE so.status IN ('shipped','delivered') \
                                             AND so.actual_delivery_date IS NOT NULL \
                                             AND so.actual_delivery_date <= so.committed_date)::bigint, \
                            COUNT(*) FILTER (WHERE so.status NOT IN ('cancelled','draft') \
                                             AND so.committed_date IS NOT NULL)::bigint, \
                            COUNT(*) FILTER (WHERE so.status <> 'cancelled')::bigint, \
                            MIN(so.created_at), \
                            MAX(so.updated_at) \
                     FROM sales_orders so \
                     WHERE so.tenant_id = $1 \
                       AND ($2::uuid IS NULL OR so.fulfilling_site_id = $2)",
                )
                .bind(tenant_id)
                .bind(site_id)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("metric engine: otd: {e}")))?;
                let value = if eligible > 0 {
                    Decimal::from(delivered_on_time)
                        .checked_div(Decimal::from(eligible))
                        .unwrap_or(Decimal::ZERO)
                } else {
                    Decimal::ZERO
                };
                let sample_size = eligible as u64;
                let coverage = if non_cancelled > 0 {
                    eligible as f64 / non_cancelled as f64
                } else {
                    0.0
                };
                Ok(MetricResult {
                    metric_id,
                    value,
                    unit: "ratio".to_string(),
                    period_start: period_start.unwrap_or(computed_at),
                    period_end: period_end.unwrap_or(computed_at),
                    sample_size,
                    coverage,
                    computed_at,
                })
            })
        })
        .await
    }
}

/// MANUFACTURING LEAD TIME PROXY (audit item 27): `delivered_at −
/// created_at` in days — the schema has no `shipped_at` column, so the
/// best available is `updated_at − created_at` of delivered orders
/// (status in ('shipped','delivered')). sales_orders DO carry a site
/// scope (`fulfilling_site_id`, migration 139), so the metric honors the
/// `site_id` parameter on BOTH the numerator (delivered orders driving
/// the average) and the denominator (non-cancelled orders driving the
/// coverage): `site_id = None` keeps the tenant-level value, `site_id =
/// Some(site)` restricts both to orders that site fulfills.
pub struct LeadTimeV1;

#[async_trait]
impl MetricComputer for LeadTimeV1 {
    fn id(&self) -> &'static str {
        "lead_time"
    }

    fn version(&self) -> u32 {
        1
    }

    async fn compute(
        &self,
        pool: &PgPool,
        tenant_id: Uuid,
        site_id: Option<Uuid>,
    ) -> Result<MetricResult> {
        let metric_id = self.id().to_string();
        let computed_at = Utc::now();
        with_tenant_tx(pool, tenant_id, |tx| {
            Box::pin(async move {
                let (value, delivered_count, non_cancelled, period_start, period_end): (
                    Decimal,
                    i64,
                    i64,
                    Option<DateTime<Utc>>,
                    Option<DateTime<Utc>>,
                ) = sqlx::query_as(
                    "SELECT COALESCE(AVG(EXTRACT(EPOCH FROM \
                                               (COALESCE(so.shipped_at, so.updated_at) \
                                                - so.created_at)) / 86400.0), 0)::numeric, \
                            COUNT(*)::bigint, \
                            (SELECT COUNT(*) FROM sales_orders so2 \
                             WHERE so2.tenant_id = $1 AND so2.status <> 'cancelled' \
                               AND ($2::uuid IS NULL OR so2.fulfilling_site_id = $2))::bigint, \
                            MIN(so.created_at), \
                            MAX(so.updated_at) \
                     FROM sales_orders so \
                     WHERE so.tenant_id = $1 AND so.status IN ('shipped','delivered') \
                       AND ($2::uuid IS NULL OR so.fulfilling_site_id = $2)",
                )
                .bind(tenant_id)
                .bind(site_id)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("metric engine: lead time: {e}")))?;
                let sample_size = delivered_count as u64;
                let coverage = if non_cancelled > 0 {
                    delivered_count as f64 / non_cancelled as f64
                } else {
                    0.0
                };
                Ok(MetricResult {
                    metric_id,
                    value,
                    unit: "days".to_string(),
                    period_start: period_start.unwrap_or(computed_at),
                    period_end: period_end.unwrap_or(computed_at),
                    sample_size,
                    coverage,
                    computed_at,
                })
            })
        })
        .await
    }
}

/// The ONE registry of executable metrics — every surface (API,
/// dashboard, AI, corporate rollup) must resolve a metric through
/// [`compute_metric`], never through hand-written SQL.
pub fn registry() -> Vec<Box<dyn MetricComputer>> {
    vec![
        Box::new(OtdV1),
        Box::new(FpyV1),
        Box::new(ScrapRateV1),
        Box::new(LeadTimeV1),
    ]
}

/// Compute ONE metric with its TRUE definition. Unknown metric ids are a
/// Validation error — a metric with no executable definition must never
/// silently fall back to anything.
/// completed / (completed + scrapped) — scrap is a separate count, never
/// a subset of completed (sixteenth audit item 25).
fn process_yield_ratio(completed: Decimal, scrapped: Decimal) -> Decimal {
    let produced = completed + scrapped;
    if produced > Decimal::ZERO {
        completed.checked_div(produced).unwrap_or(Decimal::ZERO)
    } else {
        Decimal::ZERO
    }
}

/// scrapped / (completed + scrapped) — the SAME denominator as the yield
/// proxy so the two always sum to 1.
fn scrap_ratio(scrapped: Decimal, completed: Decimal) -> Decimal {
    let produced = completed + scrapped;
    if produced > Decimal::ZERO {
        scrapped.checked_div(produced).unwrap_or(Decimal::ZERO)
    } else {
        Decimal::ZERO
    }
}

fn computer_for(metric_id: &str) -> Option<Box<dyn MetricComputer>> {
    registry()
        .into_iter()
        .find(|c| c.id() == metric_id || (metric_id == "fpy" && c.id() == "process_yield_proxy"))
}

pub async fn compute_metric(
    pool: &PgPool,
    tenant_id: Uuid,
    metric_id: &str,
    site_id: Option<Uuid>,
) -> Result<MetricResult> {
    let computer = computer_for(metric_id).ok_or_else(|| {
        SenseiError::Validation(format!(
            "Unknown metric id '{metric_id}' — the metric engine computes: \
             'process_yield_proxy' (alias 'fpy'), 'otd', 'scrap_rate', 'lead_time'"
        ))
    })?;
    computer.compute(pool, tenant_id, site_id).await
}

#[cfg(test)]
mod metric_semantics_tests {
    use super::*;
    use std::str::FromStr;

    #[test]
    fn yield_and_scrap_share_the_denominator() {
        let y = process_yield_ratio(Decimal::from(100), Decimal::from(10));
        let r = scrap_ratio(Decimal::from(10), Decimal::from(100));
        assert!(
            y > Decimal::from_str("0.90909090909").unwrap()
                && y < Decimal::from_str("0.90909090910").unwrap()
        );
        assert_eq!(y + r, Decimal::ONE);
    }

    #[test]
    fn no_production_means_zero_not_nan() {
        assert_eq!(
            process_yield_ratio(Decimal::ZERO, Decimal::ZERO),
            Decimal::ZERO
        );
        assert_eq!(scrap_ratio(Decimal::ZERO, Decimal::ZERO), Decimal::ZERO);
    }

    #[test]
    fn old_double_subtraction_is_gone() {
        // Old (good − scrap)/good with good=100 scrap=10 gave 0.9;
        // the honest proxy is 100/110 ≈ 0.909091 — never 0.9.
        let y = process_yield_ratio(Decimal::from(100), Decimal::from(10));
        assert_ne!(y, Decimal::from_str("0.9").unwrap());
    }
}

/// Twenty-seventh-audit P2 (empirical performance evidence): micro-bench
/// smoke for the PURE hot paths behind every metric endpoint and every
/// paginated list — the metric ratio math ([`process_yield_ratio`] /
/// [`scrap_ratio`], which every fpy/scrap_rate compute runs) and the
/// in-memory pagination shape math of
/// `sensei_core::pagination::PaginatedResponse::new` used by the
/// supply-chain list endpoints. Runs under ordinary `cargo test`; reports
/// p50/p95 iteration rates to stderr only when `PERF_VERBOSE` is set, is
/// skipped when `SKIP_PERF` is set, and asserts a loose 250 ms ceiling
/// (avg ≪ 1 ms/op) so CI stays green on shared runners.
#[cfg(test)]
mod perf_smoke {
    use super::*;
    use sensei_core::pagination::PaginatedResponse;
    use std::str::FromStr;
    use std::time::{Duration, Instant};

    const CEILING: Duration = Duration::from_millis(250);
    const SAMPLES: usize = 5;

    /// Time `ops` invocations in `SAMPLES` equal batches and report the
    /// p50/p95 iteration rates when `PERF_VERBOSE` is set. Returns the
    /// total elapsed time.
    fn timed<F: FnMut()>(name: &str, ops: usize, mut f: F) -> Duration {
        let per_batch = ops / SAMPLES;
        let mut rates = Vec::with_capacity(SAMPLES);
        let mut total = Duration::ZERO;
        for _ in 0..SAMPLES {
            let start = Instant::now();
            for _ in 0..per_batch {
                f();
            }
            let elapsed = start.elapsed();
            total += elapsed;
            rates.push(per_batch as f64 / elapsed.as_secs_f64());
        }
        rates.sort_by(f64::total_cmp);
        if std::env::var_os("PERF_VERBOSE").is_some() {
            let p50 = rates[SAMPLES / 2];
            let p95 = rates[(SAMPLES * 95) / 100];
            eprintln!(
                "[perf::{name}] {ops} iters in {total:?} — p50 {p50:.0} iters/s, p95 {p95:.0} \
                 iters/s (avg {:.2} µs/op)",
                total.as_secs_f64() * 1e6 / ops as f64
            );
        }
        total
    }

    #[test]
    fn metric_ratio_math_10k_stays_fast_and_exact() {
        if std::env::var_os("SKIP_PERF").is_some() {
            eprintln!("SKIP_PERF set — skipping metric_engine::perf_smoke::ratio_math");
            return;
        }
        // Accumulated checksum keeps the compiler honest (the loop has a
        // real observable result) while mirroring the compute hot path.
        let mut yield_sum = Decimal::ZERO;
        let mut scrap_sum = Decimal::ZERO;
        let elapsed = timed("metric ratio math x10k", 10_000, || {
            let completed = Decimal::from(100);
            let scrapped = Decimal::from(10);
            yield_sum += process_yield_ratio(completed, scrapped);
            scrap_sum += scrap_ratio(scrapped, completed);
        });
        assert!(yield_sum > Decimal::ZERO && scrap_sum > Decimal::ZERO);
        // y + r == 1 per op (28-sig-digit rounding drift ≪ 1e-6), so the
        // pair sums to ≈ 10k after 10k ops.
        let drift = (yield_sum + scrap_sum - Decimal::from(10_000)).abs();
        assert!(
            drift < Decimal::from_str("0.000001").unwrap(),
            "yield+scrap drifted from 10k by {drift}"
        );
        assert!(
            elapsed < CEILING,
            "10k ratio pairs took {elapsed:?} — metric hot math must stay < {CEILING:?}"
        );
    }

    #[test]
    fn pagination_shape_10k_stays_fast() {
        if std::env::var_os("SKIP_PERF").is_some() {
            eprintln!("SKIP_PERF set — skipping metric_engine::perf_smoke::pagination_shape");
            return;
        }
        let mut pages_seen = 0usize;
        let mut items_seen = 0usize;
        let elapsed = timed("PaginatedResponse::new x10k", 10_000, || {
            // A 40-row in-memory page list, cycling the page/window shape
            // (clamped bounds, last page, walked-off end) like the
            // supply-chain list endpoints do per request.
            let page = 1 + (pages_seen % 6);
            let per_page = match pages_seen % 3 {
                0 => Some(15),
                1 => Some(25),
                _ => None,
            };
            let response = PaginatedResponse::new(
                (0..40).map(|i| i + pages_seen % 7).collect(),
                Some(page),
                per_page,
            );
            pages_seen += 1;
            items_seen += response.data.len();
            assert_eq!(response.per_page.clamp(1, 100), response.per_page);
        });
        assert!(pages_seen == 10_000 && items_seen > 0);
        assert!(
            elapsed < CEILING,
            "10k PaginatedResponse::new took {elapsed:?} — list pagination shape must stay < \
             {CEILING:?}"
        );
    }
}
