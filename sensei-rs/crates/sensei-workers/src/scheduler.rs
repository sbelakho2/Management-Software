//! Periodic task scheduler — replaces Celery Beat.
//!
//! The [`TaskScheduler`] publishes task messages to NATS subjects on a
//! configurable schedule, emulating the Celery Beat tasks:
//!
//! | Task                          | Schedule         |
//! |-------------------------------|------------------|
//! | `daily_analytics_snapshot`    | daily@02:00      |
//! | `compute_warehouse_kpis`      | every@4hours     |
//! | `scheduled_retrain_all`       | daily@03:00      |

use crate::error::{Result, WorkerError};
use crate::task::{TaskEnvelope, TaskType};
use async_nats::jetstream::Context;
use chrono::Timelike;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tracing::{error, info};

/// Represents a single scheduled task entry.
#[derive(Debug, Clone)]
pub struct ScheduledTask {
    /// Human-readable cron-like expression.
    ///
    /// Supported formats:
    /// - `"daily@HH:MM"` — run daily at the given wall-clock time (UTC).
    /// - `"hourly@:MM"`  — run every hour at MM minutes past.
    /// - `"every@Nhours"` — run every N hours from process start.
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
    /// Run every N hours.
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
            let minute: u32 = minute_str.parse().map_err(|_| {
                WorkerError::InvalidConfig(format!("Invalid minute in '{}'", expr))
            })?;
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

    /// Compute the delay until the next scheduled run.
    async fn delay_until_next(&self) -> Duration {
        match self {
            Self::Daily { hour, minute } => {
                let now = chrono::Utc::now();
                let today_target = now
                    .date_naive()
                    .and_hms_opt(*hour, *minute, 0)
                    .unwrap_or_else(|| {
                        // Fallback: should not happen with validated input.
                        now.date_naive().and_time(chrono::NaiveTime::MIN)
                    });
                let target = today_target
                    .and_local_timezone(chrono::Utc)
                    .single()
                    .unwrap_or(now);

                if target > now {
                    (target - now).to_std().unwrap_or(Duration::ZERO)
                } else {
                    // Schedule for tomorrow.
                    (target + chrono::Duration::days(1) - now)
                        .to_std()
                        .unwrap_or(Duration::ZERO)
                }
            }
            Self::Hourly { minute } => {
                let now = chrono::Utc::now();
                let current_minute = now.minute();
                let secs = if current_minute < *minute {
                    (*minute - current_minute) as u64 * 60
                } else {
                    (60 - current_minute + *minute) as u64 * 60
                };
                let secs = secs.saturating_sub(now.second() as u64);
                Duration::from_secs(secs.max(1))
            }
            Self::Every { hours } => Duration::from_secs(hours * 3600),
        }
    }
}

/// Periodic scheduler that publishes task messages to NATS JetStream subjects.
///
/// Uses tokio timers to wake at the appropriate times, constructs a
/// [`TaskEnvelope`] for the scheduled task type, and publishes it to the
/// corresponding NATS subject.
pub struct TaskScheduler {
    /// NATS JetStream context for publishing.
    js: Context,
    /// List of scheduled tasks.
    tasks: Arc<RwLock<Vec<ScheduledTask>>>,
}

impl TaskScheduler {
    /// Create a new [`TaskScheduler`].
    pub fn new(js: Context) -> Self {
        Self {
            js,
            tasks: Arc::new(RwLock::new(Vec::new())),
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
    /// Spawns one tokio task per schedule entry. Each task independently
    /// computes the next run time, sleeps, publishes to NATS, and repeats.
    /// Returns a list of join handles so the caller can await shutdown.
    pub async fn start(&self) -> Result<Vec<tokio::task::JoinHandle<()>>> {
        let tasks = self.tasks.read().await.clone();
        let mut handles = Vec::new();

        for task in tasks {
            let js = self.js.clone();
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
                    // Compute delay until next run.
                    let delay = schedule.delay_until_next().await;
                    // Clamp to at least 1 second to avoid busy loops.
                    let delay = if delay.is_zero() {
                        Duration::from_secs(1)
                    } else {
                        delay
                    };

                    info!(
                        cron = %task.cron_expression,
                        task_type = ?task.task_type,
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

                    // Build and publish the task envelope.
                    let envelope = TaskEnvelope::new(task.task_type.clone(), task.payload.clone());
                    let subject = task.task_type.subject();

                    match serde_json::to_vec(&envelope) {
                        Ok(data) => {
                            let payload = bytes::Bytes::from(data);
                            match js.publish(subject.to_string(), payload).await {
                                Ok(ack) => {
                                    info!(
                                        subject = %subject,
                                        task_type = ?task.task_type,
                                        "Scheduled task published"
                                    );
                                    drop(ack);
                                }
                                Err(e) => {
                                    error!(
                                        subject = %subject,
                                        task_type = ?task.task_type,
                                        error = %e,
                                        "Failed to publish scheduled task"
                                    );
                                }
                            }
                        }
                        Err(e) => {
                            error!(
                                task_type = ?task.task_type,
                                error = %e,
                                "Failed to serialize scheduled task envelope"
                            );
                        }
                    }
                }
            });

            handles.push(handle);
        }

        info!(task_count = handles.len(), "Task scheduler started");
        Ok(handles)
    }

    /// Return the number of registered scheduled tasks.
    pub fn task_count(&self) -> usize {
        self.tasks.try_read().map(|t| t.len()).unwrap_or(0)
    }
}

/// Default schedule entries matching the Celery Beat tasks.
impl TaskScheduler {
    /// Create a new [`TaskScheduler`] pre-populated with the standard Celery
    /// Beat replacement schedules.
    pub async fn with_default_schedule(js: Context) -> Self {
        let mut scheduler = Self::new(js);

        // daily_analytics_snapshot → daily at 02:00 UTC
        scheduler
            .add_task(
                "daily@02:00",
                TaskType::DailyAnalyticsSnapshot,
                serde_json::json!({
                    "domains": ["production", "quality", "finance", "inventory"]
                }),
            )
            .await;

        // compute_warehouse_kpis → every 4 hours
        scheduler
            .add_task(
                "every@4hours",
                TaskType::ComputeWarehouseKpis,
                serde_json::json!({}),
            )
            .await;

        // scheduled_retrain_all → daily at 03:00 UTC
        scheduler
            .add_task(
                "daily@03:00",
                TaskType::ScheduledRetrainAll,
                serde_json::json!({}),
            )
            .await;

        scheduler
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
        assert!(matches!(s, CronSchedule::Daily { hour: 23, minute: 59 }));
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
    fn test_delay_every() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let s = CronSchedule::Every { hours: 4 };
            let d = s.delay_until_next().await;
            assert_eq!(d.as_secs(), 4 * 3600);
        });
    }
}
