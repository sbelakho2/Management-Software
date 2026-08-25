//! Analytics worker — replaces Celery's `daily_analytics_snapshot` and
//! `compute_warehouse_kpis`.
//!
//! Listens on:
//! - `sensei.tasks.analytics.snapshot` — daily analytics snapshots
//! - `sensei.tasks.analytics.kpi` — warehouse KPI computation
//!
//! Queries real aggregate data from the database when a pool is available.
/// Falls back to empty results with a warning when no pool is configured.
use crate::error::{Result, WorkerError};
use crate::task::{IdempotencyGuard, TaskConsumer, TaskMetadata, TaskOutcome};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tracing::{error, info, warn};

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
    /// Recorded query failures: query label → error message.
    failures: Arc<RwLock<HashMap<String, String>>>,
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
            failures: Arc::new(RwLock::new(HashMap::new())),
            idempotency: IdempotencyGuard::new(None, "analytics"),
        }
    }

    /// Create an [`AnalyticsWorker`] with a custom cache.
    pub fn with_cache(cache: Arc<AnalyticsCache>) -> Self {
        Self {
            cache,
            pool: None,
            failures: Arc::new(RwLock::new(HashMap::new())),
            idempotency: IdempotencyGuard::new(None, "analytics"),
        }
    }

    /// Create an [`AnalyticsWorker`] with a database pool.
    pub fn with_pool(pool: Option<Arc<PgPool>>) -> Self {
        Self {
            cache: Arc::new(AnalyticsCache::new(Duration::from_secs(300))),
            pool: pool.clone(),
            failures: Arc::new(RwLock::new(HashMap::new())),
            idempotency: IdempotencyGuard::new(pool, "analytics"),
        }
    }

    /// Record a failed analytics query and return the error.
    async fn query_failed(&self, label: &str, e: sqlx::Error) -> WorkerError {
        let msg = e.to_string();
        error!(query = %label, error = %msg, "Analytics query failed");
        self.failures
            .write()
            .await
            .insert(label.to_string(), msg.clone());
        WorkerError::Processing(format!("Analytics query '{label}' failed: {msg}"))
    }

    /// Fetch a scalar i64 aggregate, recording failures instead of defaulting.
    async fn fetch_count(&self, pool: &PgPool, label: &str, sql: &str, date: &str) -> Result<i64> {
        match sqlx::query_scalar::<_, i64>(sql)
            .bind(date)
            .fetch_one(pool)
            .await
        {
            Ok(v) => Ok(v),
            Err(e) => Err(self.query_failed(label, e).await),
        }
    }

    /// Fetch an optional f64 aggregate, recording failures instead of defaulting.
    async fn fetch_optional_f64(
        &self,
        pool: &PgPool,
        label: &str,
        sql: &str,
        date: &str,
    ) -> Result<Option<f64>> {
        match sqlx::query_scalar::<_, f64>(sql)
            .bind(date)
            .fetch_optional(pool)
            .await
        {
            Ok(row) => Ok(row),
            Err(e) => Err(self.query_failed(label, e).await),
        }
    }

    /// Convert a `NULL` aggregate into `0.0` as a last resort.
    ///
    /// A `NULL` result means the aggregate ran over zero rows (e.g. `AVG`
    /// over an empty day). The value is logged as missing rather than
    /// silently defaulted.
    fn null_aggregate_to_zero(label: &str, value: Option<f64>) -> f64 {
        match value {
            Some(v) => v,
            None => {
                warn!(metric = %label, "No data for metric — recording 0.0");
                0.0
            }
        }
    }

    /// Compute a daily analytics snapshot.
    ///
    /// Queries real aggregate data from the database for each domain
    /// (production, quality, finance, inventory). Falls back to empty
    /// domain data if no pool is available.
    async fn compute_snapshot(&self, payload: &AnalyticsTaskPayload) -> Result<AnalyticsSnapshot> {
        let date = payload
            .date
            .clone()
            .unwrap_or_else(|| chrono::Utc::now().format("%Y-%m-%d").to_string());

        // Check cache first.
        let cache_key = format!("snapshot:{}", date);
        if let Some(cached) = self.cache.get_snapshot(&cache_key).await {
            info!(date = %date, "Returning cached analytics snapshot");
            return Ok(cached);
        }

        info!(date = %date, domains = ?payload.domains, "Computing daily analytics snapshot");

        let mut domains = HashMap::new();

        if let Some(pool) = &self.pool {
            // Query real production metrics.
            domains.insert(
                "production".to_string(),
                self.query_production_metrics(pool, &date).await?,
            );

            // Query real quality metrics.
            domains.insert(
                "quality".to_string(),
                self.query_quality_metrics(pool, &date).await?,
            );

            // Query real finance metrics.
            domains.insert(
                "finance".to_string(),
                self.query_finance_metrics(pool, &date).await?,
            );

            // Query real inventory metrics.
            domains.insert(
                "inventory".to_string(),
                self.query_inventory_metrics(pool, &date).await?,
            );
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

    /// Query production metrics from the database.
    ///
    /// `work_orders` has no dedicated completion timestamp: `status`
    /// transitions to `'completed'` via `UPDATE`, so `updated_at` is the
    /// completion timestamp, `created_at` the start, and `scheduled_end`
    /// the plan deadline.
    async fn query_production_metrics(
        &self,
        pool: &PgPool,
        date: &str,
    ) -> Result<serde_json::Value> {
        let work_orders_completed = self
            .fetch_count(
                pool,
                "production.work_orders_completed",
                "SELECT COUNT(*) FROM work_orders \
                 WHERE status = 'completed' AND DATE(updated_at) = $1",
                date,
            )
            .await?;

        let avg_cycle_time = self
            .fetch_optional_f64(
                pool,
                "production.cycle_time",
                "SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60.0) \
                 FROM work_orders \
                 WHERE status = 'completed' AND DATE(updated_at) = $1",
                date,
            )
            .await?;

        let on_time_count = self
            .fetch_count(
                pool,
                "production.on_time",
                "SELECT COUNT(*) FROM work_orders \
                 WHERE status = 'completed' AND DATE(updated_at) = $1 \
                 AND updated_at <= scheduled_end",
                date,
            )
            .await?;

        let on_time_rate = if work_orders_completed == 0 {
            warn!(
                date = %date,
                "No completed work orders for date — recording on-time delivery rate 0.0"
            );
            0.0
        } else {
            on_time_count as f64 / work_orders_completed as f64
        };

        Ok(serde_json::json!({
            "work_orders_completed": work_orders_completed,
            "cycle_time_avg_minutes": Self::null_aggregate_to_zero("production.cycle_time", avg_cycle_time),
            "on_time_delivery_rate": on_time_rate,
        }))
    }

    /// Query quality metrics from the database.
    ///
    /// Quality state lives in the `ncr_reports` and `capas` tables with
    /// plain `status` columns (there is no JSONB-backed `quality_ncrs` /
    /// `quality_capas` pair in the schema).
    async fn query_quality_metrics(&self, pool: &PgPool, date: &str) -> Result<serde_json::Value> {
        let ncrs_opened = self
            .fetch_count(
                pool,
                "quality.ncrs_opened",
                "SELECT COUNT(*) FROM ncr_reports WHERE DATE(created_at) = $1",
                date,
            )
            .await?;

        let ncrs_closed = self
            .fetch_count(
                pool,
                "quality.ncrs_closed",
                "SELECT COUNT(*) FROM ncr_reports \
                 WHERE status = 'closed' AND DATE(updated_at) = $1",
                date,
            )
            .await?;

        let open_ncr_count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM ncr_reports \
             WHERE status IN ('open', 'under_investigation', 'action_defined', 'in_progress')",
        )
        .fetch_one(pool)
        .await
        .map_err(|e| {
            let msg = e.to_string();
            error!(query = "quality.open_ncr_count", error = %msg, "Analytics query failed");
            WorkerError::Processing(format!(
                "Analytics query 'quality.open_ncr_count' failed: {msg}"
            ))
        })?;

        let capa_open: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM capas \
             WHERE status IN ('open', 'analysis_in_progress', 'approved', \
                              'implementation_in_progress', 'verification_in_progress')",
        )
        .fetch_one(pool)
        .await
        .map_err(|e| {
            let msg = e.to_string();
            error!(query = "quality.capa_open", error = %msg, "Analytics query failed");
            WorkerError::Processing(format!("Analytics query 'quality.capa_open' failed: {msg}"))
        })?;

        Ok(serde_json::json!({
            "ncrs_opened": ncrs_opened,
            "ncrs_closed": ncrs_closed,
            "open_ncr_count": open_ncr_count,
            "capa_open": capa_open,
        }))
    }

    /// Query finance metrics from the database.
    ///
    /// `invoices` has no `paid_at` column: `invoice_date` is the issuance
    /// date and `updated_at` the payment-status transition timestamp.
    async fn query_finance_metrics(&self, pool: &PgPool, date: &str) -> Result<serde_json::Value> {
        let invoices_issued = self
            .fetch_count(
                pool,
                "finance.invoices_issued",
                "SELECT COUNT(*) FROM invoices WHERE DATE(invoice_date) = $1",
                date,
            )
            .await?;

        let total_revenue = self
            .fetch_optional_f64(
                pool,
                "finance.total_revenue",
                "SELECT SUM(total_amount) FROM invoices \
                 WHERE status = 'paid' AND DATE(updated_at) = $1",
                date,
            )
            .await?;

        let outstanding_ar: Option<f64> = sqlx::query_scalar(
            "SELECT SUM(total_amount) FROM invoices \
             WHERE status IN ('sent', 'overdue')",
        )
        .fetch_optional(pool)
        .await
        .map_err(|e| {
            let msg = e.to_string();
            error!(query = "finance.outstanding_ar", error = %msg, "Analytics query failed");
            WorkerError::Processing(format!(
                "Analytics query 'finance.outstanding_ar' failed: {msg}"
            ))
        })?;

        Ok(serde_json::json!({
            "invoices_issued": invoices_issued,
            "total_revenue": Self::null_aggregate_to_zero("finance.total_revenue", total_revenue),
            "outstanding_ar": Self::null_aggregate_to_zero("finance.outstanding_ar", outstanding_ar),
        }))
    }

    /// Query inventory metrics from the database.
    ///
    /// `inventory_items` has no `reorder_point` column — the reorder level
    /// lives on `products` — and `stock_moves.move_type` uses
    /// `('receipt', 'issue', 'transfer', 'adjustment')` (no `'delivery'`).
    async fn query_inventory_metrics(
        &self,
        pool: &PgPool,
        _date: &str,
    ) -> Result<serde_json::Value> {
        let total_items: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM inventory_items")
            .fetch_one(pool)
            .await
            .map_err(|e| {
                let msg = e.to_string();
                error!(query = "inventory.total_items", error = %msg, "Analytics query failed");
                WorkerError::Processing(format!(
                    "Analytics query 'inventory.total_items' failed: {msg}"
                ))
            })?;

        let low_stock_items: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM inventory_items ii \
             JOIN products p ON p.id = ii.product_id \
             WHERE ii.quantity_on_hand <= COALESCE(p.reorder_point, 0)",
        )
        .fetch_one(pool)
        .await
        .map_err(|e| {
            let msg = e.to_string();
            error!(query = "inventory.low_stock", error = %msg, "Analytics query failed");
            WorkerError::Processing(format!(
                "Analytics query 'inventory.low_stock' failed: {msg}"
            ))
        })?;

        // Turnover: units moved out over the trailing 30 days divided by the
        // average on-hand quantity (real stock_moves data).
        let inventory_turnover: Option<f64> = sqlx::query_scalar(
            "SELECT CASE WHEN COALESCE(SUM(ii.quantity_on_hand), 0) > 0 \
             THEN COALESCE(SUM(sm.quantity) FILTER (WHERE sm.move_type IN ('issue', 'transfer')), 0) \
                  / SUM(ii.quantity_on_hand) \
             ELSE 0.0 END \
             FROM inventory_items ii \
             LEFT JOIN stock_moves sm ON sm.product_id = ii.product_id \
              AND sm.moved_at > NOW() - INTERVAL '30 days'",
        )
        .fetch_optional(pool)
        .await
        .map_err(|e| {
            let msg = e.to_string();
            error!(query = "inventory.turnover", error = %msg, "Analytics query failed");
            WorkerError::Processing(format!("Analytics query 'inventory.turnover' failed: {msg}"))
        })?;

        Ok(serde_json::json!({
            "total_items": total_items,
            "low_stock_items": low_stock_items,
            "inventory_turnover": Self::null_aggregate_to_zero("inventory.turnover", inventory_turnover),
        }))
    }

    /// Compute warehouse KPIs.
    ///
    /// Queries real aggregate data from the database. Falls back to empty
    /// KPIs if no pool is available.
    async fn compute_warehouse_kpis(
        &self,
        payload: &AnalyticsTaskPayload,
    ) -> Result<Vec<KpiValue>> {
        let date = payload
            .date
            .clone()
            .unwrap_or_else(|| chrono::Utc::now().format("%Y-%m-%d").to_string());

        let cache_key = format!("kpi:warehouse:{}", date);
        if let Some(cached) = self.cache.get_kpis(&cache_key).await {
            info!(date = %date, "Returning cached warehouse KPIs");
            return Ok(cached);
        }

        info!(date = %date, "Computing warehouse KPIs");

        let computed_at = chrono::Utc::now().to_rfc3339();

        let kpis = if let Some(pool) = &self.pool {
            let storage_utilization: f64 = sqlx::query_scalar(
                "SELECT COALESCE(AVG(utilization_pct), 0.0) \
                 FROM warehouse_storage_locations",
            )
            .fetch_one(pool.as_ref())
            .await
            .map_err(|e| {
                let msg = e.to_string();
                error!(query = "kpi.storage_utilization", error = %msg, "Analytics query failed");
                WorkerError::Processing(format!(
                    "Analytics query 'kpi.storage_utilization' failed: {msg}"
                ))
            })?;

            let picking_accuracy: f64 = sqlx::query_scalar(
                "SELECT CASE WHEN COUNT(*) > 0 \
                 THEN SUM(CASE WHEN status = 'correct' THEN 1 ELSE 0 END)::float / COUNT(*) * 100.0 \
                 ELSE 0.0 END \
                 FROM warehouse_pick_events WHERE DATE(event_date) = $1",
            )
            .bind(&date)
            .fetch_one(pool.as_ref())
            .await
            .map_err(|e| {
                let msg = e.to_string();
                error!(query = "kpi.picking_accuracy", error = %msg, "Analytics query failed");
                WorkerError::Processing(format!("Analytics query 'kpi.picking_accuracy' failed: {msg}"))
            })?;

            let order_cycle_time: f64 = sqlx::query_scalar(
                "SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600.0), 0.0) \
                 FROM warehouse_orders WHERE DATE(completed_at) = $1",
            )
            .bind(&date)
            .fetch_one(pool.as_ref())
            .await
            .map_err(|e| {
                let msg = e.to_string();
                error!(query = "kpi.order_cycle_time", error = %msg, "Analytics query failed");
                WorkerError::Processing(format!("Analytics query 'kpi.order_cycle_time' failed: {msg}"))
            })?;

            let dock_to_stock_time: f64 = sqlx::query_scalar(
                "SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (putaway_at - received_at)) / 3600.0), 0.0) \
                 FROM warehouse_receipts WHERE DATE(received_at) = $1",
            )
            .bind(&date)
            .fetch_one(pool.as_ref())
            .await
            .map_err(|e| {
                let msg = e.to_string();
                error!(query = "kpi.dock_to_stock_time", error = %msg, "Analytics query failed");
                WorkerError::Processing(format!("Analytics query 'kpi.dock_to_stock_time' failed: {msg}"))
            })?;

            let inventory_accuracy: f64 = sqlx::query_scalar(
                "SELECT CASE WHEN COUNT(*) > 0 \
                 THEN SUM(CASE WHEN ABS(counted_qty - expected_qty)::float / \
                     GREATEST(expected_qty, 1) < 0.05 THEN 1 ELSE 0 END)::float / COUNT(*) * 100.0 \
                 ELSE 0.0 END \
                 FROM warehouse_cycle_counts WHERE DATE(count_date) = $1",
            )
            .bind(&date)
            .fetch_one(pool.as_ref())
            .await
            .map_err(|e| {
                let msg = e.to_string();
                error!(query = "kpi.inventory_accuracy", error = %msg, "Analytics query failed");
                WorkerError::Processing(format!(
                    "Analytics query 'kpi.inventory_accuracy' failed: {msg}"
                ))
            })?;

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
            Ok(true) => {}
            Ok(false) => {
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
                Ok(TaskOutcome::Completed)
            }
            crate::task::TaskType::ComputeWarehouseKpis => {
                let kpis = self.compute_warehouse_kpis(&analytics_payload).await?;
                info!(
                    task_id = %metadata.task_id,
                    kpi_count = kpis.len(),
                    "Warehouse KPI computation completed"
                );
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
    pub fn new() -> Self {
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

impl Default for SnapshotWorker {
    fn default() -> Self {
        Self::new()
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
    pub fn new() -> Self {
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

impl Default for KpiWorker {
    fn default() -> Self {
        Self::new()
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
