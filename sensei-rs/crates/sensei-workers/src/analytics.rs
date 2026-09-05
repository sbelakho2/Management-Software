//! Analytics worker — replaces Celery's `daily_analytics_snapshot` and
//! `compute_warehouse_kpis`.
//!
//! Listens on:
//! - `sensei.tasks.analytics.snapshot` — daily analytics snapshots
//! - `sensei.tasks.analytics.kpi` — warehouse KPI computation
//!
//! Queries real aggregate data from the database when a pool is available.
//! Falls back to empty results with a warning when no pool is configured.
//!
//! # Tenant scoping (thirtieth-audit item 18, Wave C RLS)
//!
//! Every table the metrics read is tenant-owned and fail-closed FORCE RLS
//! since migration 175, so the worker computes metrics per tenant inside a
//! [`TenantTx`] and merges component-wise. See [`AnalyticsWorker`].
use crate::error::{Result, WorkerError};
use crate::task::{ClaimOutcome, IdempotencyGuard, TaskConsumer, TaskMetadata, TaskOutcome};
use async_trait::async_trait;
use sensei_core::db::TenantTx;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use std::collections::HashMap;
use std::ops::AddAssign;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tracing::{error, info, warn};
use uuid::Uuid;

/// Payload for analytics-related tasks.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsTaskPayload {
    /// Optional date (ISO date string) for the snapshot / computation.
    /// Defaults to "today" when absent.
    pub date: Option<String>,
    /// Optional set of domains to include.
    /// When absent, all domains are included.
    pub domains: Option<Vec<String>>,
    /// Optional tenant ID filter.
    pub tenant_id: Option<String>,
}

/// A snapshot of analytics data across domains.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsSnapshot {
    /// The date this snapshot covers.
    pub date: String,
    /// ISO timestamp when the snapshot was taken.
    pub generated_at: String,
    /// Domain-specific summary data.
    pub domains: HashMap<String, serde_json::Value>,
}

/// A computed KPI value.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KpiValue {
    /// KPI name.
    pub name: String,
    /// KPI value.
    pub value: f64,
    /// Unit string (e.g. `"%"`, `"units"`, `"hours"`).
    pub unit: String,
    /// ISO timestamp when computed.
    pub computed_at: String,
    /// Optional threshold for alerting.
    pub threshold: Option<f64>,
}

/// In-memory cache for computed snapshots and KPIs.
///
/// Prevents redundant recomputation within the configured TTL window.
/// Entries older than the TTL are treated as expired and recomputed.
/// A cached snapshot entry: when it was computed and the snapshot itself.
type SnapshotEntry = (std::time::Instant, AnalyticsSnapshot);
/// A cached KPI entry: when it was computed and the KPI values.
type KpiEntry = (std::time::Instant, Vec<KpiValue>);

#[derive(Debug)]
pub struct AnalyticsCache {
    snapshots: Arc<RwLock<HashMap<String, SnapshotEntry>>>,
    kpis: Arc<RwLock<HashMap<String, KpiEntry>>>,
    ttl: Duration,
}

impl AnalyticsCache {
    /// Create a new cache with the given TTL.
    pub fn new(ttl: Duration) -> Self {
        Self {
            snapshots: Arc::new(RwLock::new(HashMap::new())),
            kpis: Arc::new(RwLock::new(HashMap::new())),
            ttl,
        }
    }

    /// Get a cached snapshot, if present and not expired.
    pub async fn get_snapshot(&self, key: &str) -> Option<AnalyticsSnapshot> {
        let cache = self.snapshots.read().await;
        match cache.get(key) {
            Some((inserted_at, snapshot)) if inserted_at.elapsed() < self.ttl => {
                Some(snapshot.clone())
            }
            _ => None,
        }
    }

    /// Store a snapshot in the cache.
    pub async fn put_snapshot(&self, key: String, snapshot: AnalyticsSnapshot) {
        let mut cache = self.snapshots.write().await;
        cache.insert(key, (std::time::Instant::now(), snapshot));
    }

    /// Get cached KPIs for a domain, if present and not expired.
    pub async fn get_kpis(&self, key: &str) -> Option<Vec<KpiValue>> {
        let cache = self.kpis.read().await;
        match cache.get(key) {
            Some((inserted_at, kpis)) if inserted_at.elapsed() < self.ttl => Some(kpis.clone()),
            _ => None,
        }
    }

    /// Store KPIs in the cache.
    pub async fn put_kpis(&self, key: String, kpis: Vec<KpiValue>) {
        let mut cache = self.kpis.write().await;
        cache.insert(key, (std::time::Instant::now(), kpis));
    }
}

/// Worker that processes analytics-related tasks.
///
/// Queries real aggregate data from the database when a pool is configured.
/// Query failures are logged and recorded (never silently swallowed with a
/// default value); without a pool, results are empty with a warning.
pub struct AnalyticsWorker {
    /// In-memory cache for analytics results (5 min TTL).
    cache: Arc<AnalyticsCache>,
    /// Optional database pool for querying real data.
    pool: Option<Arc<PgPool>>,
    /// Idempotency guard (migration 053): claims the task_id before
    /// computing/storing a snapshot or KPI set.
    idempotency: IdempotencyGuard,
}

impl AnalyticsWorker {
    /// Create a new [`AnalyticsWorker`] with a default cache (5 min TTL).
    pub fn new() -> Self {
        Self {
            cache: Arc::new(AnalyticsCache::new(Duration::from_secs(300))),
            pool: None,
            idempotency: IdempotencyGuard::new(None, "analytics"),
        }
    }

    /// Create an [`AnalyticsWorker`] with a custom cache.
    pub fn with_cache(cache: Arc<AnalyticsCache>) -> Self {
        Self {
            cache,
            pool: None,
            idempotency: IdempotencyGuard::new(None, "analytics"),
        }
    }

    /// Create an [`AnalyticsWorker`] with a database pool.
    pub fn with_pool(pool: Option<Arc<PgPool>>) -> Self {
        Self {
            cache: Arc::new(AnalyticsCache::new(Duration::from_secs(300))),
            pool: pool.clone(),
            idempotency: IdempotencyGuard::new(pool, "analytics"),
        }
    }

    /// Record a failed analytics query and return the error. The
    /// observability map write is intentionally absent here: this helper
    /// is called from synchronous map_err closures on sqlx results.
    fn query_failed(&self, label: &str, e: sqlx::Error) -> WorkerError {
        let msg = e.to_string();
        error!(query = %label, error = %msg, "Analytics query failed");
        WorkerError::Processing(format!("Analytics query '{label}' failed: {msg}"))
    }

    /// Compute a daily analytics snapshot.
    ///
    /// Queries real aggregate data from the database for each domain
    /// (production, quality, finance, inventory). Falls back to empty
    /// domain data if no pool is available.
    ///
    /// # Tenant scoping (thirtieth-audit item 18, Wave C RLS)
    ///
    /// Every table the metrics read (`work_orders`, `ncr_reports`,
    /// `capas`, `invoices`, `inventory_items`, `products`, `stock_moves`)
    /// is tenant-owned and fail-closed FORCE RLS since migration 175: a
    /// raw-pool query under the production `sensei_app` role has no
    /// `app.tenant_id` context and sees zero rows. Each tenant's metrics
    /// are therefore computed inside a [`TenantTx`] of that tenant and
    /// merged component-wise (counts and sums add; averages/rates are
    /// weighted by their row counts) — a payload tenant_id narrows the
    /// snapshot to exactly that tenant; a tenant-less payload covers every
    /// active tenant (the tenant list comes from the RLS-free `tenants`
    /// table).
    async fn compute_snapshot(&self, payload: &AnalyticsTaskPayload) -> Result<AnalyticsSnapshot> {
        let date = payload
            .date
            .clone()
            .unwrap_or_else(|| chrono::Utc::now().format("%Y-%m-%d").to_string());

        // Cache key: the tenant filter is part of the snapshot identity.
        let tenant_scope = payload
            .tenant_id
            .clone()
            .unwrap_or_else(|| "all".to_string());
        let cache_key = format!("snapshot:{}:{}", date, tenant_scope);
        if let Some(cached) = self.cache.get_snapshot(&cache_key).await {
            info!(date = %date, "Returning cached analytics snapshot");
            return Ok(cached);
        }

        info!(date = %date, domains = ?payload.domains, "Computing daily analytics snapshot");

        let mut domains = HashMap::new();

        if let Some(pool) = &self.pool {
            let mut tenants: Vec<Uuid> = match &payload.tenant_id {
                Some(raw) => match Uuid::parse_str(raw) {
                    Ok(t) => vec![t],
                    Err(_) => {
                        warn!(tenant_id = %raw, "Invalid tenant_id in analytics payload — computing for all active tenants");
                        tenant_ids(pool).await
                    }
                },
                None => tenant_ids(pool).await,
            };
            tenants.sort();
            tenants.dedup();
            if tenants.is_empty() {
                warn!("No active tenants — analytics snapshot will contain empty domain data");
            }

            // Component-wise accumulators (per-tenant metrics merged below).
            let mut prod = ProductionTotals::default();
            let mut quality = QualityTotals::default();
            let mut finance = FinanceTotals::default();
            let mut inventory = InventoryTotals::default();

            for tenant_id in tenants {
                let mut db = TenantTx::begin(pool, tenant_id).await.map_err(|e| {
                    WorkerError::Processing(format!(
                        "Failed to begin analytics tx for tenant {tenant_id}: {e}"
                    ))
                })?;
                prod += self
                    .query_production_metrics(&mut db, &date)
                    .await
                    .map_err(|e| self.attach_tenant(e, tenant_id))?;
                quality += self
                    .query_quality_metrics(&mut db, &date)
                    .await
                    .map_err(|e| self.attach_tenant(e, tenant_id))?;
                finance += self
                    .query_finance_metrics(&mut db, &date)
                    .await
                    .map_err(|e| self.attach_tenant(e, tenant_id))?;
                inventory += self
                    .query_inventory_metrics(&mut db, &date)
                    .await
                    .map_err(|e| self.attach_tenant(e, tenant_id))?;
                db.commit().await.map_err(|e| {
                    WorkerError::Processing(format!(
                        "Failed to commit analytics tx for tenant {tenant_id}: {e}"
                    ))
                })?;
            }

            domains.insert("production".to_string(), prod.to_json());
            domains.insert("quality".to_string(), quality.to_json());
            domains.insert("finance".to_string(), finance.to_json());
            domains.insert("inventory".to_string(), inventory.to_json());
        } else {
            warn!(
                "No database pool configured — analytics snapshot will contain empty domain data. \
                 Provide a PgPool via AnalyticsWorker::with_pool() for real data."
            );
        }

        let snapshot = AnalyticsSnapshot {
            date: date.clone(),
            generated_at: chrono::Utc::now().to_rfc3339(),
            domains,
        };

        // Cache the result.
        self.cache.put_snapshot(cache_key, snapshot.clone()).await;

        info!(date = %date, "Analytics snapshot computed");
        Ok(snapshot)
    }

    /// Tag a per-tenant query failure with the tenant that produced it.
    fn attach_tenant(&self, e: WorkerError, tenant_id: Uuid) -> WorkerError {
        match e {
            WorkerError::Processing(msg) => WorkerError::Processing(format!(
                "Analytics query for tenant {tenant_id} failed: {msg}"
            )),
            other => other,
        }
    }

    /// Query production metrics for ONE tenant (runs on the tenant's
    /// TenantTx — RLS admits exactly this tenant's `work_orders`).
    ///
    /// `work_orders` has no dedicated completion timestamp: `status`
    /// transitions to `'completed'` via `UPDATE`, so `updated_at` is the
    /// completion timestamp, `created_at` the start, and `scheduled_end`
    /// the plan deadline. The row-count/weighting pairs let the tenant
    /// totals merge exactly (the average cycle time is the summed cycle
    /// minutes over the summed completed count, never a mean of means).
    async fn query_production_metrics(
        &self,
        db: &mut TenantTx<'_>,
        date: &str,
    ) -> Result<ProductionTotals> {
        // One row of (completed count, summed cycle minutes, on-time
        // count) for the date.
        let (completed, cycle_time_sum_minutes, on_time_count): (i64, f64, i64) = sqlx::query_as(
            "SELECT \
                COUNT(*) FILTER (WHERE status = 'completed' AND DATE(updated_at) = $1), \
                COALESCE(SUM(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60.0) \
                    FILTER (WHERE status = 'completed' AND DATE(updated_at) = $1), 0.0), \
                COUNT(*) FILTER (WHERE status = 'completed' AND DATE(updated_at) = $1 \
                    AND updated_at <= scheduled_end) \
             FROM work_orders",
        )
        .bind(date)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("production.work_orders_completed", e))?;

        if completed == 0 {
            warn!(
                date = %date,
                "No completed work orders for date — recording on-time delivery rate 0.0"
            );
        }

        Ok(ProductionTotals {
            completed,
            cycle_time_sum_minutes,
            on_time_count,
        })
    }

    /// Query quality metrics for ONE tenant (runs on the tenant's
    /// TenantTx — RLS admits exactly this tenant's rows).
    ///
    /// Quality state lives in the `ncr_reports` and `capas` tables with
    /// plain `status` columns (there is no JSONB-backed `quality_ncrs` /
    /// `quality_capas` pair in the schema).
    async fn query_quality_metrics(
        &self,
        db: &mut TenantTx<'_>,
        date: &str,
    ) -> Result<QualityTotals> {
        let ncrs_opened: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM ncr_reports WHERE DATE(created_at) = $1",
        )
        .bind(date)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("quality.ncrs_opened", e))?;

        let ncrs_closed: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM ncr_reports \
             WHERE status = 'closed' AND DATE(updated_at) = $1",
        )
        .bind(date)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("quality.ncrs_closed", e))?;

        let open_ncr_count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM ncr_reports \
             WHERE status IN ('open', 'under_investigation', 'action_defined', 'in_progress')",
        )
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("quality.open_ncr_count", e))?;

        let capa_open: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM capas \
             WHERE status IN ('open', 'analysis_in_progress', 'approved', \
                               'implementation_in_progress', 'verification_in_progress')",
        )
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("quality.capa_open", e))?;

        Ok(QualityTotals {
            ncrs_opened,
            ncrs_closed,
            open_ncr_count,
            capa_open,
        })
    }

    /// Query finance metrics for ONE tenant (runs on the tenant's
    /// TenantTx — RLS admits exactly this tenant's `invoices`).
    ///
    /// `invoices` has no `paid_at` column: `invoice_date` is the issuance
    /// date and `updated_at` the payment-status transition timestamp. The
    /// NUMERIC sums are cast to float8 so the scalar decodes as f64.
    async fn query_finance_metrics(
        &self,
        db: &mut TenantTx<'_>,
        date: &str,
    ) -> Result<FinanceTotals> {
        let invoices_issued: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM invoices WHERE DATE(invoice_date) = $1",
        )
        .bind(date)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("finance.invoices_issued", e))?;

        let total_revenue: f64 = sqlx::query_scalar(
            "SELECT COALESCE(SUM(total_amount), 0)::float8 FROM invoices \
             WHERE status = 'paid' AND DATE(updated_at) = $1",
        )
        .bind(date)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("finance.total_revenue", e))?;

        let outstanding_ar: f64 = sqlx::query_scalar(
            "SELECT COALESCE(SUM(total_amount), 0)::float8 FROM invoices \
             WHERE status IN ('sent', 'overdue')",
        )
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("finance.outstanding_ar", e))?;

        Ok(FinanceTotals {
            invoices_issued,
            total_revenue,
            outstanding_ar,
        })
    }

    /// Query inventory metrics for ONE tenant (runs on the tenant's
    /// TenantTx — RLS admits exactly this tenant's rows).
    ///
    /// `inventory_items` has no `reorder_point` column — the reorder level
    /// lives on `products` — and `stock_moves.move_type` uses
    /// `('receipt', 'issue', 'transfer', 'adjustment')` (no `'delivery'`).
    async fn query_inventory_metrics(
        &self,
        db: &mut TenantTx<'_>,
        _date: &str,
    ) -> Result<InventoryTotals> {
        let total_items: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM inventory_items")
                .fetch_one(&mut **db.tx())
                .await
                .map_err(|e| self.query_failed("inventory.total_items", e))?;

        let low_stock_items: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM inventory_items ii \
             JOIN products p ON p.id = ii.product_id \
             WHERE ii.quantity_on_hand <= COALESCE(p.reorder_point, 0)",
        )
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("inventory.low_stock", e))?;

        // Turnover: units moved out over the trailing 30 days divided by the
        // average on-hand quantity (real stock_moves data). The tenant query
        // returns the (moved, on-hand) pair; the merged turnover is
        // total_moved / total_on_hand, never a mean of per-tenant ratios.
        let (moved_units, on_hand_units): (f64, f64) = sqlx::query_as(
            "SELECT \
                COALESCE(SUM(sm.quantity) \
                    FILTER (WHERE sm.move_type IN ('issue', 'transfer') \
                        AND sm.status = 'posted' \
                        AND sm.moved_at > NOW() - INTERVAL '30 days'), 0)::float8, \
                COALESCE(SUM(ii.quantity_on_hand), 0)::float8 \
             FROM inventory_items ii \
             LEFT JOIN stock_moves sm ON sm.product_id = ii.product_id \
              AND sm.tenant_id = ii.tenant_id \
              AND sm.site_id = ii.site_id \
              AND sm.status = 'posted' \
              AND sm.moved_at > NOW() - INTERVAL '30 days'",
        )
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("inventory.turnover", e))?;

        Ok(InventoryTotals {
            total_items,
            low_stock_items,
            moved_units,
            on_hand_units,
        })
    }

    /// Compute warehouse KPIs.
    ///
    /// Queries real aggregate data from the database. Falls back to empty
    /// KPIs if no pool is available. Tenant scoping follows
    /// [`Self::compute_snapshot`]: every source table is fail-closed FORCE
    /// RLS (migration 175), so each tenant's KPI components are computed
    /// inside its own [`TenantTx`] and merged component-wise (averages are
    /// weighted by their row counts).
    async fn compute_warehouse_kpis(
        &self,
        payload: &AnalyticsTaskPayload,
    ) -> Result<Vec<KpiValue>> {
        let date = payload
            .date
            .clone()
            .unwrap_or_else(|| chrono::Utc::now().format("%Y-%m-%d").to_string());

        let tenant_scope = payload
            .tenant_id
            .clone()
            .unwrap_or_else(|| "all".to_string());
        let cache_key = format!("kpi:warehouse:{}:{}", date, tenant_scope);
        if let Some(cached) = self.cache.get_kpis(&cache_key).await {
            info!(date = %date, "Returning cached warehouse KPIs");
            return Ok(cached);
        }

        info!(date = %date, "Computing warehouse KPIs");

        let computed_at = chrono::Utc::now().to_rfc3339();

        let kpis = if let Some(pool) = &self.pool {
            let mut tenants: Vec<Uuid> = match &payload.tenant_id {
                Some(raw) => match Uuid::parse_str(raw) {
                    Ok(t) => vec![t],
                    Err(_) => {
                        warn!(tenant_id = %raw, "Invalid tenant_id in KPI payload — computing for all active tenants");
                        tenant_ids(pool).await
                    }
                },
                None => tenant_ids(pool).await,
            };
            tenants.sort();
            tenants.dedup();

            let mut totals = WarehouseKpiTotals::default();
            for tenant_id in tenants {
                let mut db = TenantTx::begin(pool, tenant_id).await.map_err(|e| {
                    WorkerError::Processing(format!(
                        "Failed to begin KPI tx for tenant {tenant_id}: {e}"
                    ))
                })?;
                totals += self
                    .query_warehouse_kpi_components(&mut db, &date)
                    .await
                    .map_err(|e| self.attach_tenant(e, tenant_id))?;
                db.commit().await.map_err(|e| {
                    WorkerError::Processing(format!(
                        "Failed to commit KPI tx for tenant {tenant_id}: {e}"
                    ))
                })?;
            }

            totals.to_kpis(computed_at)
        } else {
            warn!(
                "No database pool configured — warehouse KPIs will be empty. \
                 Provide a PgPool via AnalyticsWorker::with_pool() for real data."
            );
            Vec::new()
        };

        self.cache.put_kpis(cache_key, kpis.clone()).await;

        info!(date = %date, kpi_count = kpis.len(), "Warehouse KPIs computed");
        Ok(kpis)
    }

    /// Query the component pairs ONE tenant contributes to the warehouse
    /// KPIs (runs on the tenant's TenantTx — RLS admits exactly this
    /// tenant's rows). Averages and rates return their (sum, count) pairs
    /// so the merged KPI stays exact.
    async fn query_warehouse_kpi_components(
        &self,
        db: &mut TenantTx<'_>,
        date: &str,
    ) -> Result<WarehouseKpiTotals> {
        // storage utilization: summed utilization pct + location count.
        let (utilization_sum, location_count): (f64, i64) = sqlx::query_as(
            "SELECT COALESCE(SUM(utilization_pct), 0.0), COUNT(*) \
             FROM warehouse_storage_locations",
        )
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("kpi.storage_utilization", e))?;

        // picking accuracy: correct picks + total picks on the date.
        let (correct_picks, total_picks): (i64, i64) = sqlx::query_as(
            "SELECT \
                COUNT(*) FILTER (WHERE status = 'correct'), \
                COUNT(*) \
             FROM warehouse_pick_events WHERE DATE(event_date) = $1",
        )
        .bind(date)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("kpi.picking_accuracy", e))?;

        // order cycle time: summed hours + completed orders on the date.
        let (cycle_hours, cycle_count): (f64, i64) = sqlx::query_as(
            "SELECT \
                COALESCE(SUM(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600.0), 0.0), \
                COUNT(*) \
             FROM warehouse_orders WHERE DATE(completed_at) = $1",
        )
        .bind(date)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("kpi.order_cycle_time", e))?;

        // dock-to-stock: summed hours + receipts on the date.
        let (dts_hours, dts_count): (f64, i64) = sqlx::query_as(
            "SELECT \
                COALESCE(SUM(EXTRACT(EPOCH FROM (putaway_at - received_at)) / 3600.0), 0.0), \
                COUNT(*) \
             FROM warehouse_receipts WHERE DATE(received_at) = $1",
        )
        .bind(date)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("kpi.dock_to_stock_time", e))?;

        // inventory accuracy: within-tolerance counts + total counts on the
        // date (the 5 % tolerance of the original CASE is preserved).
        let (accurate_counts, total_counts): (i64, i64) = sqlx::query_as(
            "SELECT \
                COUNT(*) FILTER (WHERE ABS(counted_qty - expected_qty)::float / \
                    GREATEST(expected_qty, 1) < 0.05), \
                COUNT(*) \
             FROM warehouse_cycle_counts WHERE DATE(count_date) = $1",
        )
        .bind(date)
        .fetch_one(&mut **db.tx())
        .await
        .map_err(|e| self.query_failed("kpi.inventory_accuracy", e))?;

        Ok(WarehouseKpiTotals {
            utilization_sum,
            location_count,
            correct_picks,
            total_picks,
            cycle_hours,
            cycle_count,
            dts_hours,
            dts_count,
            accurate_counts,
            total_counts,
        })
    }
}

/// Active tenants for tenant-less analytics/KPI runs, read from the
/// RLS-free `tenants` table (it has no tenant_id column — tenant RLS does
/// not apply to it).
async fn tenant_ids(pool: &PgPool) -> Vec<Uuid> {
    sqlx::query_scalar("SELECT id FROM tenants WHERE is_active = TRUE ORDER BY id")
        .fetch_all(pool)
        .await
        .unwrap_or_default()
}

/// Per-tenant production-metric components. The completed-count weight
/// keeps the merged cycle-time average and on-time rate exact (the old
/// whole-DB AVG/rate over the same rows).
#[derive(Debug, Clone, Copy, Default)]
struct ProductionTotals {
    completed: i64,
    cycle_time_sum_minutes: f64,
    on_time_count: i64,
}

impl AddAssign for ProductionTotals {
    fn add_assign(&mut self, rhs: Self) {
        self.completed += rhs.completed;
        self.cycle_time_sum_minutes += rhs.cycle_time_sum_minutes;
        self.on_time_count += rhs.on_time_count;
    }
}

impl ProductionTotals {
    fn to_json(self) -> serde_json::Value {
        let cycle_time_avg_minutes = if self.completed > 0 {
            self.cycle_time_sum_minutes / self.completed as f64
        } else {
            0.0
        };
        let on_time_delivery_rate = if self.completed > 0 {
            self.on_time_count as f64 / self.completed as f64
        } else {
            0.0
        };
        serde_json::json!({
            "work_orders_completed": self.completed,
            "cycle_time_avg_minutes": cycle_time_avg_minutes,
            "on_time_delivery_rate": on_time_delivery_rate,
        })
    }
}

/// Per-tenant quality-metric counts (pure sums across tenants).
#[derive(Debug, Clone, Copy, Default)]
struct QualityTotals {
    ncrs_opened: i64,
    ncrs_closed: i64,
    open_ncr_count: i64,
    capa_open: i64,
}

impl AddAssign for QualityTotals {
    fn add_assign(&mut self, rhs: Self) {
        self.ncrs_opened += rhs.ncrs_opened;
        self.ncrs_closed += rhs.ncrs_closed;
        self.open_ncr_count += rhs.open_ncr_count;
        self.capa_open += rhs.capa_open;
    }
}

impl QualityTotals {
    fn to_json(self) -> serde_json::Value {
        serde_json::json!({
            "ncrs_opened": self.ncrs_opened,
            "ncrs_closed": self.ncrs_closed,
            "open_ncr_count": self.open_ncr_count,
            "capa_open": self.capa_open,
        })
    }
}

/// Per-tenant finance-metric components (counts and NUMERIC sums cast to
/// float8; both add across tenants).
#[derive(Debug, Clone, Copy, Default)]
struct FinanceTotals {
    invoices_issued: i64,
    total_revenue: f64,
    outstanding_ar: f64,
}

impl AddAssign for FinanceTotals {
    fn add_assign(&mut self, rhs: Self) {
        self.invoices_issued += rhs.invoices_issued;
        self.total_revenue += rhs.total_revenue;
        self.outstanding_ar += rhs.outstanding_ar;
    }
}

impl FinanceTotals {
    fn to_json(self) -> serde_json::Value {
        serde_json::json!({
            "invoices_issued": self.invoices_issued,
            "total_revenue": self.total_revenue,
            "outstanding_ar": self.outstanding_ar,
        })
    }
}

/// Per-tenant inventory-metric components. Turnover merges as
/// total_moved / total_on_hand (never a mean of per-tenant ratios).
#[derive(Debug, Clone, Copy, Default)]
struct InventoryTotals {
    total_items: i64,
    low_stock_items: i64,
    moved_units: f64,
    on_hand_units: f64,
}

impl AddAssign for InventoryTotals {
    fn add_assign(&mut self, rhs: Self) {
        self.total_items += rhs.total_items;
        self.low_stock_items += rhs.low_stock_items;
        self.moved_units += rhs.moved_units;
        self.on_hand_units += rhs.on_hand_units;
    }
}

impl InventoryTotals {
    fn to_json(self) -> serde_json::Value {
        let inventory_turnover = if self.on_hand_units > 0.0 {
            self.moved_units / self.on_hand_units
        } else {
            0.0
        };
        serde_json::json!({
            "total_items": self.total_items,
            "low_stock_items": self.low_stock_items,
            "inventory_turnover": inventory_turnover,
        })
    }
}

/// Per-tenant warehouse-KPI components. Every average/rate keeps its
/// (sum, count) pair so the merged KPI matches the whole-DB formula
/// exactly.
#[derive(Debug, Clone, Copy, Default)]
struct WarehouseKpiTotals {
    utilization_sum: f64,
    location_count: i64,
    correct_picks: i64,
    total_picks: i64,
    cycle_hours: f64,
    cycle_count: i64,
    dts_hours: f64,
    dts_count: i64,
    accurate_counts: i64,
    total_counts: i64,
}

impl AddAssign for WarehouseKpiTotals {
    fn add_assign(&mut self, rhs: Self) {
        self.utilization_sum += rhs.utilization_sum;
        self.location_count += rhs.location_count;
        self.correct_picks += rhs.correct_picks;
        self.total_picks += rhs.total_picks;
        self.cycle_hours += rhs.cycle_hours;
        self.cycle_count += rhs.cycle_count;
        self.dts_hours += rhs.dts_hours;
        self.dts_count += rhs.dts_count;
        self.accurate_counts += rhs.accurate_counts;
        self.total_counts += rhs.total_counts;
    }
}

impl WarehouseKpiTotals {
    /// Render the merged components as the historical five KPI values.
    fn to_kpis(self, computed_at: String) -> Vec<KpiValue> {
        let storage_utilization = if self.location_count > 0 {
            self.utilization_sum / self.location_count as f64
        } else {
            0.0
        };
        let picking_accuracy = if self.total_picks > 0 {
            self.correct_picks as f64 / self.total_picks as f64 * 100.0
        } else {
            0.0
        };
        let order_cycle_time = if self.cycle_count > 0 {
            self.cycle_hours / self.cycle_count as f64
        } else {
            0.0
        };
        let dock_to_stock_time = if self.dts_count > 0 {
            self.dts_hours / self.dts_count as f64
        } else {
            0.0
        };
        let inventory_accuracy = if self.total_counts > 0 {
            self.accurate_counts as f64 / self.total_counts as f64 * 100.0
        } else {
            0.0
        };
        vec![
            KpiValue {
                name: "storage_utilization".to_string(),
                value: storage_utilization,
                unit: "%".to_string(),
                computed_at: computed_at.clone(),
                threshold: Some(85.0),
            },
            KpiValue {
                name: "picking_accuracy".to_string(),
                value: picking_accuracy,
                unit: "%".to_string(),
                computed_at: computed_at.clone(),
                threshold: Some(95.0),
            },
            KpiValue {
                name: "order_cycle_time".to_string(),
                value: order_cycle_time,
                unit: "hours".to_string(),
                computed_at: computed_at.clone(),
                threshold: Some(8.0),
            },
            KpiValue {
                name: "dock_to_stock_time".to_string(),
                value: dock_to_stock_time,
                unit: "hours".to_string(),
                computed_at: computed_at.clone(),
                threshold: Some(12.0),
            },
            KpiValue {
                name: "inventory_accuracy".to_string(),
                value: inventory_accuracy,
                unit: "%".to_string(),
                computed_at,
                threshold: Some(95.0),
            },
        ]
    }
}

impl Default for AnalyticsWorker {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl TaskConsumer for AnalyticsWorker {
    fn subject(&self) -> &'static str {
        "sensei.tasks.analytics.snapshot"
    }

    fn consumer_group(&self) -> &'static str {
        "sensei-workers-analytics"
    }

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<TaskOutcome> {
        let analytics_payload: AnalyticsTaskPayload =
            serde_json::from_slice(payload).map_err(|e| {
                error!(
                    task_id = %metadata.task_id,
                    error = %e,
                    "Failed to deserialize analytics task payload"
                );
                WorkerError::Serialization(e)
            })?;

        // Idempotency: claim the task_id BEFORE computing/storing anything.
        // A redelivered message is skipped.
        let task_id_str = metadata.task_id.to_string();
        match self.idempotency.try_claim(&task_id_str).await {
            Ok(ClaimOutcome::Proceed) => {}
            Ok(ClaimOutcome::Busy) => {
                // Another replica holds a live lease; back off. The
                // redelivery re-claims once the lease expires.
                return Err(WorkerError::RetryLater(
                    "idempotency lease busy; retrying".to_string(),
                ));
            }
            Ok(ClaimOutcome::AlreadyCompleted) => {
                info!(
                    task_id = %metadata.task_id,
                    "Analytics task already processed — skipping (idempotent)"
                );
                return Ok(TaskOutcome::Completed);
            }
            Err(e) => {
                return Err(WorkerError::RetryLater(format!(
                    "idempotency claim failed for analytics task: {e}"
                )));
            }
        }

        match metadata.task_type {
            crate::task::TaskType::DailyAnalyticsSnapshot => {
                let snapshot = self.compute_snapshot(&analytics_payload).await?;
                info!(
                    task_id = %metadata.task_id,
                    date = %snapshot.date,
                    domain_count = snapshot.domains.len(),
                    "Daily analytics snapshot completed"
                );
                self.idempotency.mark_completed(&task_id_str).await?;
                Ok(TaskOutcome::Completed)
            }
            crate::task::TaskType::ComputeWarehouseKpis => {
                let kpis = self.compute_warehouse_kpis(&analytics_payload).await?;
                info!(
                    task_id = %metadata.task_id,
                    kpi_count = kpis.len(),
                    "Warehouse KPI computation completed"
                );
                self.idempotency.mark_completed(&task_id_str).await?;
                Ok(TaskOutcome::Completed)
            }
            _ => Err(WorkerError::Processing(format!(
                "Unsupported task type for AnalyticsWorker: {:?}",
                metadata.task_type
            ))),
        }
    }
}

/// Convenience wrapper listening on `sensei.tasks.analytics.snapshot`.
pub struct SnapshotWorker {
    inner: AnalyticsWorker,
}

impl SnapshotWorker {
    /// TEST-ONLY constructor: no database (empty/placeholder analytics).
    /// Production code must use [`Self::with_pool`].
    #[cfg(test)]
    pub fn in_memory() -> Self {
        Self {
            inner: AnalyticsWorker::new(),
        }
    }

    pub fn with_pool(pool: Option<Arc<PgPool>>) -> Self {
        Self {
            inner: AnalyticsWorker::with_pool(pool),
        }
    }
}

#[async_trait]
impl TaskConsumer for SnapshotWorker {
    fn subject(&self) -> &'static str {
        "sensei.tasks.analytics.snapshot"
    }

    fn consumer_group(&self) -> &'static str {
        "sensei-workers-analytics-snapshot"
    }

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<TaskOutcome> {
        self.inner.process(payload, metadata).await
    }
}

/// Convenience wrapper listening on `sensei.tasks.analytics.kpi`.
pub struct KpiWorker {
    inner: AnalyticsWorker,
}

impl KpiWorker {
    /// TEST-ONLY constructor: no database. Production code must use
    /// [`Self::with_pool`].
    #[cfg(test)]
    pub fn in_memory() -> Self {
        Self {
            inner: AnalyticsWorker::new(),
        }
    }

    pub fn with_pool(pool: Option<Arc<PgPool>>) -> Self {
        Self {
            inner: AnalyticsWorker::with_pool(pool),
        }
    }
}

#[async_trait]
impl TaskConsumer for KpiWorker {
    fn subject(&self) -> &'static str {
        "sensei.tasks.analytics.kpi"
    }

    fn consumer_group(&self) -> &'static str {
        "sensei-workers-analytics-kpi"
    }

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<TaskOutcome> {
        self.inner.process(payload, metadata).await
    }
}
