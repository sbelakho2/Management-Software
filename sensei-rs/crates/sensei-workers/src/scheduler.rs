//! Periodic task scheduler — replaces Celery Beat.
//!
//! The [`TaskScheduler`] publishes task messages to NATS subjects on a
//! configurable wall-clock schedule, emulating the Celery Beat tasks:
//!
//! | Task                          | Schedule         |
//! |-------------------------------|------------------|
//! | `daily_analytics_snapshot`    | daily@02:00      |
//! | `compute_warehouse_kpis`      | every@4hours     |
//! | `scheduled_retrain_all`       | daily@03:00      |
//!
//! # Leader election (no duplicate scheduled jobs across pods)
//!
//! When a database pool is configured ([`TaskScheduler::with_leader_election`]),
//! only the instance holding the PostgreSQL session advisory lock
//! (`SELECT pg_try_advisory_lock(<const>)`) runs the schedule loops. The
//! lock is session-scoped, so it auto-releases when the leader's connection
//! closes (crash, restart, roll-out); followers poll every few seconds and
//! take over when the lock becomes free. Migration 054
//! (`scheduler_run_log`) additionally deduplicates each wall-clock slot, so
//! a takeover never re-publishes a slot the dead leader already fired.
//!
//! # Dev mode (no database)
//!
//! Without a pool the scheduler runs directly — this is a single-process
//! assumption and must not be deployed with multiple scheduler replicas.

use crate::error::{Result, WorkerError};
use crate::task::{TaskEnvelope, TaskType};
use async_nats::jetstream::Context;
use chrono::{DateTime, Timelike, Utc};
use sqlx::PgPool;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tracing::{error, info};

/// How the scheduler decides which process runs the schedule loops.
#[derive(Debug, Clone)]
pub enum LeadershipMode {
    /// No database: every process runs the loops. Single-process assumption
    /// for development — running multiple scheduler processes duplicates
    /// every scheduled task.
    InMemory,
    /// PostgreSQL `pg_try_advisory_lock` leader election: exactly one
    /// process runs the loops; followers poll and take over on failure.
    Postgres {
        /// Pool used to hold the advisory-lock session.
        pool: Arc<PgPool>,
        /// Advisory-lock key (must match across replicas).
        lock_key: i64,
    },
}

/// Interval at which non-leader instances poll for the advisory lock.
pub const LEADER_POLL_INTERVAL: Duration = Duration::from_secs(5);

/// Represents a single scheduled task entry.
#[derive(Debug, Clone)]
pub struct ScheduledTask {
    /// Human-readable cron-like expression.
    ///
    /// Supported formats (all wall-clock, UTC):
    /// - `"daily@HH:MM"` — run daily at the given wall-clock time (UTC).
    /// - `"hourly@:MM"`  — run every hour at MM minutes past.
    /// - `"every@Nhours"` — run every N hours aligned to the wall clock
    ///   (e.g. `every@4hours` fires at 00:00, 04:00, 08:00, … UTC).
    pub cron_expression: String,
    /// The type of task to publish.
    pub task_type: TaskType,
    /// The JSON payload to include in the published message.
    pub payload: serde_json::Value,
}

/// Parsed representation of a cron-like expression.
#[derive(Debug, Clone)]
enum CronSchedule {
    /// Run daily at HH:MM UTC.
    Daily { hour: u32, minute: u32 },
    /// Run every hour at :MM minutes past.
    Hourly { minute: u32 },
    /// Run every N hours aligned to the wall clock.
    Every { hours: u64 },
}

impl CronSchedule {
    /// Parse a cron-like expression string.
    fn parse(expr: &str) -> Result<Self> {
        if let Some(rest) = expr.strip_prefix("daily@") {
            let parts: Vec<&str> = rest.split(':').collect();
            if parts.len() != 2 {
                return Err(WorkerError::InvalidConfig(format!(
                    "Invalid daily expression '{}': expected daily@HH:MM",
                    expr
                )));
            }
            let hour: u32 = parts[0]
                .parse()
                .map_err(|_| WorkerError::InvalidConfig(format!("Invalid hour in '{}'", expr)))?;
            let minute: u32 = parts[1]
                .parse()
                .map_err(|_| WorkerError::InvalidConfig(format!("Invalid minute in '{}'", expr)))?;
            if hour > 23 || minute > 59 {
                return Err(WorkerError::InvalidConfig(format!(
                    "Invalid time in '{}': HH must be 0-23, MM must be 0-59",
                    expr
                )));
            }
            Ok(Self::Daily { hour, minute })
        } else if let Some(rest) = expr.strip_prefix("hourly@") {
            let minute_str = rest.strip_prefix(':').unwrap_or(rest);
            let minute: u32 = minute_str
                .parse()
                .map_err(|_| WorkerError::InvalidConfig(format!("Invalid minute in '{}'", expr)))?;
            if minute > 59 {
                return Err(WorkerError::InvalidConfig(format!(
                    "Invalid minute in '{}': must be 0-59",
                    expr
                )));
            }
            Ok(Self::Hourly { minute })
        } else if let Some(rest) = expr.strip_prefix("every@") {
            let hours_str = rest
                .strip_suffix("hours")
                .or_else(|| rest.strip_suffix("hour"))
                .unwrap_or(rest);
            let hours: u64 = hours_str.parse().map_err(|_| {
                WorkerError::InvalidConfig(format!(
                    "Invalid hours in '{}': expected every@Nhours",
                    expr
                ))
            })?;
            if hours == 0 {
                return Err(WorkerError::InvalidConfig(format!(
                    "Invalid interval in '{}': must be >= 1 hour",
                    expr
                )));
            }
            Ok(Self::Every { hours })
        } else {
            Err(WorkerError::InvalidConfig(format!(
                "Unrecognised cron expression '{}'. Expected: daily@HH:MM, hourly@:MM, or every@Nhours",
                expr
            )))
        }
    }

    /// Compute the next wall-clock run strictly after `now`, plus a stable
    /// run key (migration 054) identifying that slot.
    ///
    /// The run key only depends on the fire time, so a takeover computes the
    /// same key for the same slot and cannot double-publish it.
    fn next_run(&self, now: DateTime<Utc>) -> Result<(DateTime<Utc>, String)> {
        match self {
            Self::Daily { hour, minute } => {
                let today = now
                    .date_naive()
                    .and_hms_opt(*hour, *minute, 0)
                    .ok_or_else(|| WorkerError::InvalidConfig("invalid daily time".into()))?
                    .and_local_timezone(Utc)
                    .single()
                    .ok_or_else(|| WorkerError::InvalidConfig("invalid daily timezone".into()))?;
                let next = if today > now {
                    today
                } else {
                    today + chrono::Duration::days(1)
                };
                Ok((next, next.format("%Y-%m-%dT%H:%M").to_string()))
            }
            Self::Hourly { minute } => {
                let next = if now.minute() < *minute {
                    now.date_naive()
                        .and_hms_opt(now.hour(), *minute, 0)
                        .unwrap()
                } else if now.hour() < 23 {
                    now.date_naive()
                        .and_hms_opt(now.hour() + 1, *minute, 0)
                        .unwrap()
                } else {
                    (now.date_naive() + chrono::Days::new(1))
                        .and_hms_opt(0, *minute, 0)
                        .unwrap()
                };
                let next = next
                    .and_local_timezone(Utc)
                    .single()
                    .unwrap_or(now + chrono::Duration::hours(1));
                let next = if next > now {
                    next
                } else {
                    next + chrono::Duration::hours(1)
                };
                Ok((next, next.format("%Y-%m-%dT%H:%M").to_string()))
            }
            Self::Every { hours } => {
                let period_minutes = (*hours * 60) as i64;
                let midnight = now
                    .date_naive()
                    .and_hms_opt(0, 0, 0)
                    .unwrap()
                    .and_local_timezone(Utc)
                    .single()
                    .unwrap();
                let elapsed_minutes = (now - midnight).num_minutes();
                // Next multiple of the period strictly after now, aligned to
                // the wall clock (00:00, 04:00, 08:00 … for every@4hours).
                let next_minutes = (elapsed_minutes / period_minutes + 1) * period_minutes;
                let next = midnight + chrono::Duration::minutes(next_minutes);
                Ok((next, next.format("%Y-%m-%dT%H:%M").to_string()))
            }
        }
    }
}

/// Periodic scheduler that publishes task messages to NATS JetStream subjects.
///
/// Uses tokio timers to wake at the appropriate wall-clock times, constructs
/// a [`TaskEnvelope`] for the scheduled task type, and publishes it to the
/// corresponding NATS subject. See the module docs for the leader-election
/// model.
pub struct TaskScheduler {
    /// NATS JetStream context for publishing.
    js: Context,
    /// List of scheduled tasks.
    tasks: Arc<RwLock<Vec<ScheduledTask>>>,
    /// Leadership mode (in-memory dev mode vs PostgreSQL advisory lock).
    leadership: LeadershipMode,
}

impl TaskScheduler {
    /// Create a new [`TaskScheduler`].
    ///
    /// In-memory leadership: every instance runs the loops. Documented
    /// single-process assumption — do not run multiple scheduler processes
    /// without [`Self::with_leader_election`].
    pub fn new(js: Context) -> Self {
        Self {
            js,
            tasks: Arc::new(RwLock::new(Vec::new())),
            leadership: LeadershipMode::InMemory,
        }
    }

    /// Create a [`TaskScheduler`] with PostgreSQL advisory-lock leader
    /// election (migration-free; the lock auto-releases on connection close).
    pub fn with_leader_election(js: Context, pool: Arc<PgPool>, lock_key: i64) -> Self {
        Self {
            js,
            tasks: Arc::new(RwLock::new(Vec::new())),
            leadership: LeadershipMode::Postgres { pool, lock_key },
        }
    }

    /// Add a scheduled task.
    pub async fn add_task(&mut self, cron: &str, task_type: TaskType, payload: serde_json::Value) {
        let task = ScheduledTask {
            cron_expression: cron.to_string(),
            task_type,
            payload,
        };
        info!(
            cron = %task.cron_expression,
            task_type = ?task.task_type,
            "Added scheduled task"
        );
        self.tasks.write().await.push(task);
    }

    /// Start the scheduler loop.
    ///
    /// With PostgreSQL leadership, this acquires `pg_try_advisory_lock`:
    /// the leader runs the schedule loops immediately and holds the lock for
    /// the process lifetime; followers poll every [`LEADER_POLL_INTERVAL`]
    /// and take over when the lock frees (leader crash → connection close →
    /// lock release). With in-memory leadership (no DB) every instance runs
    /// the loops — single-process dev assumption only.
    ///
    /// Returns a list of join handles so the caller can await shutdown.
    pub async fn start(&self) -> Result<Vec<tokio::task::JoinHandle<()>>> {
        // Owned clones so spawned tasks never borrow from `self`.
        let js = self.js.clone();
        let tasks = Arc::clone(&self.tasks);

        match &self.leadership {
            LeadershipMode::InMemory => {
                info!(
                    "Task scheduler running in in-memory mode (no leader election). \
                     Single-process assumption: do not run multiple scheduler \
                     processes without a database pool."
                );
                self.start_schedule_loops().await
            }
            LeadershipMode::Postgres { pool, lock_key } => {
                let mut conn = pool.acquire().await.map_err(|e| {
                    WorkerError::Processing(format!(
                        "failed to acquire DB connection for scheduler leadership: {e}"
                    ))
                })?;

                let acquired: bool = sqlx::query_scalar("SELECT pg_try_advisory_lock($1)")
                    .bind(lock_key)
                    .fetch_one(&mut *conn)
                    .await
                    .map_err(|e| {
                        WorkerError::Processing(format!(
                            "failed to acquire scheduler advisory lock: {e}"
                        ))
                    })?;

                if acquired {
                    info!(
                        lock_key,
                        "Scheduler advisory lock acquired — running as leader"
                    );
                    // Pin the lock to the process lifetime: the connection
                    // lives inside this task until the process exits, at
                    // which point PostgreSQL releases the advisory lock.
                    tokio::spawn(async move {
                        std::future::pending::<()>().await;
                        drop(conn);
                    });
                    self.start_schedule_loops().await
                } else {
                    info!(
                        lock_key,
                        "Another scheduler instance holds the advisory lock — \
                         polling for leadership takeover"
                    );
                    let pool = pool.clone();
                    let lock_key = *lock_key;
                    Ok(vec![tokio::spawn(async move {
                        wait_for_leadership(js, tasks, pool, lock_key).await;
                    })])
                }
            }
        }
    }

    /// Spawn one schedule loop per registered task.
    async fn start_schedule_loops(&self) -> Result<Vec<tokio::task::JoinHandle<()>>> {
        let pool = match &self.leadership {
            LeadershipMode::Postgres { pool, .. } => Some(pool.clone()),
            LeadershipMode::InMemory => None,
        };
        let handles = run_schedule_loops(self.js.clone(), Arc::clone(&self.tasks), pool).await;
        info!(task_count = handles.len(), "Task scheduler started");
        Ok(handles)
    }

    /// Return the number of registered scheduled tasks.
    pub fn task_count(&self) -> usize {
        self.tasks.try_read().map(|t| t.len()).unwrap_or(0)
    }
}

/// Poll `pg_try_advisory_lock` until acquired, then run the schedule loops
/// for the rest of the process lifetime (holding the connection keeps the
/// session-scoped lock alive).
async fn wait_for_leadership(
    js: Context,
    tasks: Arc<RwLock<Vec<ScheduledTask>>>,
    pool: Arc<PgPool>,
    lock_key: i64,
) {
    let mut backoff = LEADER_POLL_INTERVAL;
    loop {
        tokio::time::sleep(backoff).await;

        let mut conn = match pool.acquire().await {
            Ok(conn) => conn,
            Err(e) => {
                error!(error = %e, "Scheduler leadership poll failed to connect — retrying");
                backoff = (backoff * 2).min(Duration::from_secs(60));
                continue;
            }
        };

        let acquired: bool = match sqlx::query_scalar("SELECT pg_try_advisory_lock($1)")
            .bind(lock_key)
            .fetch_one(&mut *conn)
            .await
        {
            Ok(acquired) => acquired,
            Err(e) => {
                error!(error = %e, "Scheduler leadership poll query failed — retrying");
                backoff = (backoff * 2).min(Duration::from_secs(60));
                continue;
            }
        };

        if !acquired {
            continue;
        }

        info!(
            lock_key,
            "Scheduler leadership acquired — running schedule loops"
        );
        tokio::spawn(async move {
            // Hold the advisory-lock session for the process lifetime.
            std::future::pending::<()>().await;
            drop(conn);
        });
        let task_list = tasks.read().await.clone();
        let handles = run_schedule_loops(js, Arc::new(RwLock::new(task_list)), Some(pool)).await;
        for handle in handles {
            let _ = handle.await;
        }
        // The schedule loops only end on Ctrl-C (they return on shutdown
        // signal); if they ever all end, re-poll for leadership.
        return;
    }
}

/// Spawn one loop per scheduled task. Each loop computes the next wall-clock
/// fire time, sleeps until then, claims the slot in `scheduler_run_log`
/// (when a pool is present) and only publishes when the claim succeeds.
async fn run_schedule_loops(
    js: Context,
    tasks: Arc<RwLock<Vec<ScheduledTask>>>,
    db: Option<Arc<PgPool>>,
) -> Vec<tokio::task::JoinHandle<()>> {
    let tasks = tasks.read().await.clone();
    let mut handles = Vec::new();

    for task in tasks {
        let js = js.clone();
        let db = db.clone();
        let handle = tokio::spawn(async move {
            let schedule = match CronSchedule::parse(&task.cron_expression) {
                Ok(s) => s,
                Err(e) => {
                    error!(
                        cron = %task.cron_expression,
                        error = %e,
                        "Failed to parse schedule — skipping task"
                    );
                    return;
                }
            };

            loop {
                // Compute the next wall-clock fire time (never "N hours after
                // process start") and the stable slot key for dedup.
                let (fire_time, run_key) = match schedule.next_run(Utc::now()) {
                    Ok(v) => v,
                    Err(e) => {
                        error!(
                            cron = %task.cron_expression,
                            error = %e,
                            "Failed to compute next run — stopping this schedule"
                        );
                        return;
                    }
                };
                let delay = (fire_time - Utc::now())
                    .to_std()
                    .unwrap_or(Duration::ZERO)
                    .max(Duration::from_secs(1));

                info!(
                    cron = %task.cron_expression,
                    task_type = ?task.task_type,
                    next_run = %fire_time,
                    delay_secs = delay.as_secs(),
                    "Next scheduled run"
                );

                // Sleep until the next scheduled time (or until shutdown).
                tokio::select! {
                    _ = tokio::time::sleep(delay) => {
                        // Time to publish!
                    }
                    _ = tokio::signal::ctrl_c() => {
                        info!(
                            cron = %task.cron_expression,
                            task_type = ?task.task_type,
                            "Scheduler received shutdown signal"
                        );
                        return;
                    }
                }

                let task_type_str = format!("{:?}", task.task_type);
                // Claim the wall-clock slot (migration 054) so a leadership
                // takeover can never double-publish the same slot. Without a
                // pool (dev mode) there is nothing to deduplicate against.
                if let Some(pool) = &db {
                    match sqlx::query(
                        "INSERT INTO scheduler_run_log (task_type, run_key) \
                         VALUES ($1, $2) ON CONFLICT (task_type, run_key) DO NOTHING",
                    )
                    .bind(&task_type_str)
                    .bind(&run_key)
                    .execute(pool.as_ref())
                    .await
                    {
                        Ok(result) if result.rows_affected() == 0 => {
                            info!(
                                task_type = %task_type_str,
                                run_key = %run_key,
                                "Scheduled slot already executed — skipping publish"
                            );
                            continue;
                        }
                        Ok(_) => {}
                        Err(e) => {
                            error!(
                                task_type = %task_type_str,
                                run_key = %run_key,
                                error = %e,
                                "Failed to record scheduled slot — skipping publish \
                                 (a missed slot is safer than a duplicate)"
                            );
                            continue;
                        }
                    }
                }

                // Build and publish the task envelope.
                let envelope = TaskEnvelope::new(task.task_type.clone(), task.payload.clone());
                let subject = task.task_type.subject();

                match serde_json::to_vec(&envelope) {
                    Ok(data) => {
                        let payload = bytes::Bytes::from(data);
                        match js.publish(subject.to_string(), payload).await {
                            Ok(ack) => {
                                // Two-stage publish: only the SERVER ack
                                // makes the message durably accepted.
                                match ack.await {
                                    Ok(_) => {
                                        info!(
                                            subject = %subject,
                                            task_type = ?task.task_type,
                                            run_key = %run_key,
                                            "Scheduled task published (server acknowledged)"
                                        );
                                    }
                                    Err(e) => {
                                        error!(
                                            subject = %subject,
                                            task_type = ?task.task_type,
                                            error = %e,
                                            "Scheduled task publish NOT acknowledged by server — releasing slot for retry"
                                        );
                                        release_slot(&db, &task_type_str, &run_key).await;
                                    }
                                }
                            }
                            Err(e) => {
                                error!(
                                    subject = %subject,
                                    task_type = ?task.task_type,
                                    error = %e,
                                    "Failed to publish scheduled task — releasing slot for retry"
                                );
                                release_slot(&db, &task_type_str, &run_key).await;
                            }
                        }
                    }
                    Err(e) => {
                        error!(
                            task_type = ?task.task_type,
                            error = %e,
                            "Failed to serialize scheduled task envelope — releasing slot for retry"
                        );
                        release_slot(&db, &task_type_str, &run_key).await;
                    }
                }
            }
        });

        handles.push(handle);
    }

    handles
}

/// Release a claimed scheduler slot so the next loop iteration can retry
/// (a failed publication must never permanently suppress a scheduled job).
async fn release_slot(db: &Option<Arc<sqlx::PgPool>>, task_type: &str, run_key: &str) {
    if let Some(pool) = db {
        if let Err(e) =
            sqlx::query("DELETE FROM scheduler_run_log WHERE task_type = $1 AND run_key = $2")
                .bind(task_type)
                .bind(run_key)
                .execute(pool.as_ref())
                .await
        {
            error!(
                task_type = %task_type,
                run_key = %run_key,
                error = %e,
                "Failed to release scheduled slot — the job may be skipped this cycle"
            );
        }
    }
}

/// Default schedule entries matching the Celery Beat tasks.
impl TaskScheduler {
    /// Populate this scheduler with the standard Celery Beat replacement
    /// schedules.
    pub async fn with_default_schedule(mut self) -> Self {
        // daily_analytics_snapshot → daily at 02:00 UTC
        self.add_task(
            "daily@02:00",
            TaskType::DailyAnalyticsSnapshot,
            serde_json::json!({
                "domains": ["production", "quality", "finance", "inventory"]
            }),
        )
        .await;

        // compute_warehouse_kpis → every 4 hours, aligned to the wall clock
        self.add_task(
            "every@4hours",
            TaskType::ComputeWarehouseKpis,
            serde_json::json!({}),
        )
        .await;

        // scheduled_retrain_all → daily at 03:00 UTC
        self.add_task(
            "daily@03:00",
            TaskType::ScheduledRetrainAll,
            serde_json::json!({}),
        )
        .await;

        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_daily() {
        let s = CronSchedule::parse("daily@02:00").unwrap();
        assert!(matches!(s, CronSchedule::Daily { hour: 2, minute: 0 }));
    }

    #[test]
    fn test_parse_daily_edge_cases() {
        let s = CronSchedule::parse("daily@00:00").unwrap();
        assert!(matches!(s, CronSchedule::Daily { hour: 0, minute: 0 }));

        let s = CronSchedule::parse("daily@23:59").unwrap();
        assert!(matches!(
            s,
            CronSchedule::Daily {
                hour: 23,
                minute: 59
            }
        ));
    }

    #[test]
    fn test_parse_hourly() {
        let s = CronSchedule::parse("hourly@:30").unwrap();
        assert!(matches!(s, CronSchedule::Hourly { minute: 30 }));
    }

    #[test]
    fn test_parse_hourly_zero() {
        let s = CronSchedule::parse("hourly@:00").unwrap();
        assert!(matches!(s, CronSchedule::Hourly { minute: 0 }));
    }

    #[test]
    fn test_parse_every() {
        let s = CronSchedule::parse("every@4hours").unwrap();
        assert!(matches!(s, CronSchedule::Every { hours: 4 }));
    }

    #[test]
    fn test_parse_every_singular() {
        let s = CronSchedule::parse("every@1hour").unwrap();
        assert!(matches!(s, CronSchedule::Every { hours: 1 }));
    }

    #[test]
    fn test_parse_invalid() {
        assert!(CronSchedule::parse("invalid").is_err());
        assert!(CronSchedule::parse("daily@25:00").is_err());
        assert!(CronSchedule::parse("daily@12:60").is_err());
        assert!(CronSchedule::parse("hourly@:60").is_err());
        assert!(CronSchedule::parse("every@0hours").is_err());
        assert!(CronSchedule::parse("").is_err());
    }

    #[test]
    fn test_every_aligns_to_wall_clock() {
        // every@4hours must fire on 00:00/04:00/08:00/12:00/16:00/20:00 UTC
        // regardless of process start time.
        let schedule = CronSchedule::Every { hours: 4 };
        for minute_of_day in [0, 1, 59, 360, 361, 719, 720, 1439] {
            let now = chrono::DateTime::parse_from_rfc3339(&format!(
                "2026-08-25T{:02}:{:02}:00Z",
                minute_of_day / 60,
                minute_of_day % 60
            ))
            .unwrap()
            .with_timezone(&Utc);

            let (next, _key) = schedule.next_run(now).unwrap();
            assert!(next > now, "next run must be strictly after now");

            let minutes_since_midnight = (next
                - next
                    .date_naive()
                    .and_hms_opt(0, 0, 0)
                    .unwrap()
                    .and_local_timezone(Utc)
                    .single()
                    .unwrap())
            .num_minutes();
            assert_eq!(
                minutes_since_midnight % 240,
                0,
                "next run {next} must be aligned to a 4-hour boundary"
            );
            assert!(
                (next - now) < chrono::Duration::hours(4) + chrono::Duration::minutes(1),
                "delay must be under one period"
            );
        }
    }

    #[test]
    fn test_every_run_key_is_stable() {
        let schedule = CronSchedule::Every { hours: 4 };
        let now = Utc::now();
        let (next, key1) = schedule.next_run(now).unwrap();
        // The same slot computed from a different "now" (before the fire)
        // must yield the same run key.
        let (_, key2) = schedule
            .next_run(next - chrono::Duration::minutes(1))
            .unwrap();
        assert_eq!(key1, key2);
    }

    #[test]
    fn test_daily_run_key_includes_date() {
        let schedule = CronSchedule::Daily { hour: 2, minute: 0 };
        let now = chrono::DateTime::parse_from_rfc3339("2026-08-25T10:00:00Z")
            .unwrap()
            .with_timezone(&Utc);
        let (next, key) = schedule.next_run(now).unwrap();
        assert_eq!(next.date_naive().to_string(), "2026-08-26");
        assert_eq!(key, "2026-08-26T02:00");
    }
}
