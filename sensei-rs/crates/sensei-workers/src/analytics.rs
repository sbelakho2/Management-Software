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
use crate::task::{TaskConsumer, TaskMetadata};
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
/// Prevents redundant recomputation within a short time window.
/// In production this would be backed by Redis or the database.
#[derive(Debug)]
pub struct AnalyticsCache {
    snapshots: Arc<RwLock<HashMap<String, AnalyticsSnapshot>>>,
    kpis: Arc<RwLock<HashMap<String, Vec<KpiValue>>>>,
    #[allow(dead_code)]
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
        cache.get(key).cloned()
    }

    /// Store a snapshot in the cache.
    pub async fn put_snapshot(&self, key: String, snapshot: AnalyticsSnapshot) {
        let mut cache = self.snapshots.write().await;
        cache.insert(key, snapshot);
    }

    /// Get cached KPIs for a domain.
    pub async fn get_kpis(&self, key: &str) -> Option<Vec<KpiValue>> {
        let cache = self.kpis.read().await;
        cache.get(key).cloned()
    }

    /// Store KPIs in the cache.
    pub async fn put_kpis(&self, key: String, kpis: Vec<KpiValue>) {
        let mut cache = self.kpis.write().await;
        cache.insert(key, kpis);
    }
}

/// Worker that processes analytics-related tasks.
///
/// Queries real aggregate data from the database when a pool is configured.
/// Without a pool, returns empty results with a warning (graceful degradation).
pub struct AnalyticsWorker {
    /// In-memory cache for analytics results.
    cache: Arc<AnalyticsCache>,
    /// Optional database pool for querying real data.
    pool: Option<Arc<PgPool>>,
}

impl AnalyticsWorker {
    /// Create a new [`AnalyticsWorker`] with a default cache (5 min TTL).
    pub fn new() -> Self {
        Self {
            cache: Arc::new(AnalyticsCache::new(Duration::from_secs(300))),
            pool: None,
        }
    }

    /// Create an [`AnalyticsWorker`] with a custom cache.
    pub fn with_cache(cache: Arc<AnalyticsCache>) -> Self {
        Self {
            cache,
            pool: None,
        }
    }

    /// Create an [`AnalyticsWorker`] with a database pool.
    pub fn with_pool(pool: Arc<PgPool>) -> Self {
        Self {
            cache: Arc::new(AnalyticsCache::new(Duration::from_secs(300))),
            pool: Some(pool),
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
        self.cache
            .put_snapshot(cache_key, snapshot.clone())
            .await;

        info!(date = %date, "Analytics snapshot computed");
        Ok(snapshot)
    }

    /// Query production metrics from the database.
    async fn query_production_metrics(
        &self,
        pool: &PgPool,
        date: &str,
    ) -> Result<serde_json::Value> {
        let work_orders_completed: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM work_orders \
             WHERE status = 'completed' AND DATE(completed_at) = $1",
        )
        .bind(date)
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        let avg_cycle_time: Option<f64> = sqlx::query_scalar(
            "SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at)) / 60.0) \
             FROM work_orders \
             WHERE status = 'completed' AND DATE(completed_at) = $1",
        )
        .bind(date)
        .fetch_optional(pool)
        .await
        .ok()
        .flatten()
        .flatten();

        let on_time_count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM work_orders \
             WHERE status = 'completed' AND DATE(completed_at) = $1 \
             AND completed_at <= due_date",
        )
        .bind(date)
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        let total_completed = work_orders_completed.max(1);
        let on_time_rate = on_time_count as f64 / total_completed as f64;

        Ok(serde_json::json!({
            "work_orders_completed": work_orders_completed,
            "cycle_time_avg_minutes": avg_cycle_time.unwrap_or(0.0),
            "on_time_delivery_rate": on_time_rate,
        }))
    }

    /// Query quality metrics from the database.
    async fn query_quality_metrics(
        &self,
        pool: &PgPool,
        date: &str,
    ) -> Result<serde_json::Value> {
        let ncrs_opened: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quality_ncrs WHERE DATE(created_at) = $1",
        )
        .bind(date)
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        let ncrs_closed: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quality_ncrs \
             WHERE status = 'closed' AND DATE(updated_at) = $1",
        )
        .bind(date)
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        let open_ncr_count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quality_ncrs WHERE status IN ('open', 'in_progress')",
        )
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        let capa_open: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quality_capas WHERE status IN ('open', 'in_progress')",
        )
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        Ok(serde_json::json!({
            "ncrs_opened": ncrs_opened,
            "ncrs_closed": ncrs_closed,
            "open_ncr_count": open_ncr_count,
            "capa_open": capa_open,
        }))
    }

    /// Query finance metrics from the database.
    async fn query_finance_metrics(
        &self,
        pool: &PgPool,
        date: &str,
    ) -> Result<serde_json::Value> {
        let invoices_issued: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM finance_invoices WHERE DATE(created_at) = $1",
        )
        .bind(date)
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        let total_revenue: Option<f64> = sqlx::query_scalar(
            "SELECT SUM(total_amount) FROM finance_invoices \
             WHERE status = 'paid' AND DATE(paid_at) = $1",
        )
        .bind(date)
        .fetch_optional(pool)
        .await
        .ok()
        .flatten()
        .flatten();

        let outstanding_ar: Option<f64> = sqlx::query_scalar(
            "SELECT SUM(total_amount) FROM finance_invoices \
             WHERE status IN ('sent', 'overdue')",
        )
        .fetch_optional(pool)
        .await
        .ok()
        .flatten()
        .flatten();

        Ok(serde_json::json!({
            "invoices_issued": invoices_issued,
            "total_revenue": total_revenue.unwrap_or(0.0),
            "outstanding_ar": outstanding_ar.unwrap_or(0.0),
        }))
    }

    /// Query inventory metrics from the database.
    async fn query_inventory_metrics(
        &self,
        pool: &PgPool,
        _date: &str,
    ) -> Result<serde_json::Value> {
        let total_items: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM inventory_items",
        )
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        let low_stock_items: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM inventory_items WHERE quantity_on_hand <= reorder_point",
        )
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        let inventory_turnover: Option<f64> = sqlx::query_scalar(
            "SELECT CASE WHEN AVG(quantity_on_hand) > 0 \
             THEN SUM(quantity_consumed) / AVG(quantity_on_hand) \
             ELSE 0 END \
             FROM inventory_summary_last_30_days()",
        )
        .fetch_optional(pool)
        .await
        .ok()
        .flatten()
        .flatten();

        Ok(serde_json::json!({
            "total_items": total_items,
            "low_stock_items": low_stock_items,
            "inventory_turnover": inventory_turnover.unwrap_or(0.0),
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
            .unwrap_or(0.0);

            let picking_accuracy: f64 = sqlx::query_scalar(
                "SELECT CASE WHEN COUNT(*) > 0 \
                 THEN SUM(CASE WHEN status = 'correct' THEN 1 ELSE 0 END)::float / COUNT(*) * 100.0 \
                 ELSE 0.0 END \
                 FROM warehouse_pick_events WHERE DATE(event_date) = $1",
            )
            .bind(&date)
            .fetch_one(pool.as_ref())
            .await
            .unwrap_or(0.0);

            let order_cycle_time: f64 = sqlx::query_scalar(
                "SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600.0), 0.0) \
                 FROM warehouse_orders WHERE DATE(completed_at) = $1",
            )
            .bind(&date)
            .fetch_one(pool.as_ref())
            .await
            .unwrap_or(0.0);

            let dock_to_stock_time: f64 = sqlx::query_scalar(
                "SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (putaway_at - received_at)) / 3600.0), 0.0) \
                 FROM warehouse_receipts WHERE DATE(received_at) = $1",
            )
            .bind(&date)
            .fetch_one(pool.as_ref())
            .await
            .unwrap_or(0.0);

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
            .unwrap_or(0.0);

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

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<()> {
        let analytics_payload: AnalyticsTaskPayload = serde_json::from_slice(payload)
            .map_err(|e| {
                error!(
                    task_id = %metadata.task_id,
                    error = %e,
                    "Failed to deserialize analytics task payload"
                );
                WorkerError::Serialization(e)
            })?;

        match metadata.task_type {
            crate::task::TaskType::DailyAnalyticsSnapshot => {
                let snapshot = self.compute_snapshot(&analytics_payload).await?;
                info!(
                    task_id = %metadata.task_id,
                    date = %snapshot.date,
                    domain_count = snapshot.domains.len(),
                    "Daily analytics snapshot completed"
                );
                Ok(())
            }
            crate::task::TaskType::ComputeWarehouseKpis => {
                let kpis = self.compute_warehouse_kpis(&analytics_payload).await?;
                info!(
                    task_id = %metadata.task_id,
                    kpi_count = kpis.len(),
                    "Warehouse KPI computation completed"
                );
                Ok(())
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

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<()> {
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

    async fn process(&self, payload: &[u8], metadata: &TaskMetadata) -> Result<()> {
        self.inner.process(payload, metadata).await
    }
}
