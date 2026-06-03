//! Notification service for the Sensei ERP system.
//!
//! Provides user notification management with in-app delivery,
//! database persistence, and preference controls. Supports both
//! in-memory (development/testing) and database-backed (production)
//! implementations.

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::Serialize;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::EntityId;
use sqlx::PgPool;
use std::collections::HashMap;
use tokio::sync::RwLock;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Domain Types
// ---------------------------------------------------------------------------

/// A user notification delivered in-app.
#[derive(Debug, Clone, Serialize)]
pub struct Notification {
    /// Unique identifier.
    pub id: Uuid,
    /// Tenant this notification belongs to.
    pub tenant_id: Uuid,
    /// The recipient user.
    pub user_id: Uuid,
    /// Short notification title.
    pub title: String,
    /// Notification body text.
    pub body: String,
    /// Type: "info", "warning", "error", "success".
    pub notification_type: String,
    /// Optional entity type this notification references (e.g., "ncr", "capa", "work_order").
    pub reference_type: Option<String>,
    /// Optional entity ID this notification references.
    pub reference_id: Option<Uuid>,
    /// Whether the user has read this notification.
    pub is_read: bool,
    /// When the notification was created.
    pub created_at: DateTime<Utc>,
}

/// User-level notification preferences.
#[derive(Debug, Clone, Serialize)]
pub struct NotificationPreferences {
    /// Unique identifier.
    pub id: Uuid,
    /// Tenant this preference belongs to.
    pub tenant_id: Uuid,
    /// The user these preferences apply to.
    pub user_id: Uuid,
    /// Whether to send email notifications.
    pub email_notifications: bool,
    /// Whether to send push notifications.
    pub push_notifications: bool,
    /// Whether to show in-app notifications.
    pub in_app_notifications: bool,
    /// How often to send digests: "instant", "hourly", "daily", "never".
    pub digest_frequency: String,
    /// Optional quiet hours start time (HH:MM).
    pub quiet_hours_start: Option<String>,
    /// Optional quiet hours end time (HH:MM).
    pub quiet_hours_end: Option<String>,
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Notification service for managing user notifications and preferences.
#[async_trait]
pub trait NotificationService: Send + Sync {
    /// Create and deliver a notification to a user.
    async fn notify(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        title: &str,
        body: &str,
        ntype: &str,
        ref_type: Option<&str>,
        ref_id: Option<EntityId>,
    ) -> Result<Notification>;

    /// List notifications for a user with pagination (newest first).
    async fn list_notifications(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        limit: i64,
        offset: i64,
    ) -> Result<Vec<Notification>>;

    /// Get the count of unread notifications for a user.
    async fn unread_count(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
    ) -> Result<i64>;

    /// Mark a single notification as read.
    async fn mark_read(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        notification_id: EntityId,
    ) -> Result<()>;

    /// Mark all notifications as read for a user.
    async fn mark_all_read(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
    ) -> Result<()>;

    /// Get notification preferences for a user. Creates default preferences
    /// if none exist.
    async fn get_preferences(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
    ) -> Result<NotificationPreferences>;

    /// Update notification preferences (UPSERT).
    async fn update_preferences(
        &self,
        prefs: &NotificationPreferences,
    ) -> Result<()>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of [`NotificationService`].
///
/// Stores notifications and preferences in `HashMap`s behind `RwLock`s.
/// Suitable for development, testing, and demo environments.
pub struct InMemoryNotificationService {
    notifications: RwLock<HashMap<Uuid, Notification>>,
    preferences: RwLock<HashMap<Uuid, NotificationPreferences>>,
}

impl InMemoryNotificationService {
    /// Create a new empty [`InMemoryNotificationService`].
    pub fn new() -> Self {
        Self {
            notifications: RwLock::new(HashMap::new()),
            preferences: RwLock::new(HashMap::new()),
        }
    }
}

impl Default for InMemoryNotificationService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl NotificationService for InMemoryNotificationService {
    async fn notify(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        title: &str,
        body: &str,
        ntype: &str,
        ref_type: Option<&str>,
        ref_id: Option<EntityId>,
    ) -> Result<Notification> {
        let notification = Notification {
            id: Uuid::new_v4(),
            tenant_id,
            user_id,
            title: title.to_string(),
            body: body.to_string(),
            notification_type: ntype.to_string(),
            reference_type: ref_type.map(|s| s.to_string()),
            reference_id: ref_id,
            is_read: false,
            created_at: Utc::now(),
        };

        let id = notification.id;
        self.notifications.write().await.insert(id, notification.clone());

        Ok(notification)
    }

    async fn list_notifications(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        limit: i64,
        offset: i64,
    ) -> Result<Vec<Notification>> {
        let store = self.notifications.read().await;
        let mut notes: Vec<Notification> = store
            .values()
            .filter(|n| n.tenant_id == tenant_id && n.user_id == user_id)
            .cloned()
            .collect();

        notes.sort_by(|a, b| b.created_at.cmp(&a.created_at));

        let offset = offset.max(0) as usize;
        let limit = limit.max(1) as usize;
        Ok(notes.into_iter().skip(offset).take(limit).collect())
    }

    async fn unread_count(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
    ) -> Result<i64> {
        let store = self.notifications.read().await;
        let count = store
            .values()
            .filter(|n| n.tenant_id == tenant_id && n.user_id == user_id && !n.is_read)
            .count() as i64;
        Ok(count)
    }

    async fn mark_read(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        notification_id: EntityId,
    ) -> Result<()> {
        let mut store = self.notifications.write().await;
        let note = store
            .get_mut(&notification_id)
            .filter(|n| n.tenant_id == tenant_id && n.user_id == user_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Notification {notification_id} not found")))?;

        note.is_read = true;
        Ok(())
    }

    async fn mark_all_read(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
    ) -> Result<()> {
        let mut store = self.notifications.write().await;
        for note in store.values_mut() {
            if note.tenant_id == tenant_id && note.user_id == user_id {
                note.is_read = true;
            }
        }
        Ok(())
    }

    async fn get_preferences(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
    ) -> Result<NotificationPreferences> {
        let store = self.preferences.read().await;
        if let Some(prefs) = store
            .values()
            .find(|p| p.tenant_id == tenant_id && p.user_id == user_id)
        {
            return Ok(prefs.clone());
        }
        drop(store);

        // Create default preferences
        let prefs = NotificationPreferences {
            id: Uuid::new_v4(),
            tenant_id,
            user_id,
            email_notifications: true,
            push_notifications: true,
            in_app_notifications: true,
            digest_frequency: "instant".to_string(),
            quiet_hours_start: None,
            quiet_hours_end: None,
        };

        self.preferences
            .write()
            .await
            .insert(prefs.id, prefs.clone());

        Ok(prefs)
    }

    async fn update_preferences(
        &self,
        prefs: &NotificationPreferences,
    ) -> Result<()> {
        let mut store = self.preferences.write().await;

        // Check if preferences exist for this user/tenant
        if let Some(existing) = store
            .values_mut()
            .find(|p| p.tenant_id == prefs.tenant_id && p.user_id == prefs.user_id)
        {
            existing.email_notifications = prefs.email_notifications;
            existing.push_notifications = prefs.push_notifications;
            existing.in_app_notifications = prefs.in_app_notifications;
            existing.digest_frequency = prefs.digest_frequency.clone();
            existing.quiet_hours_start = prefs.quiet_hours_start.clone();
            existing.quiet_hours_end = prefs.quiet_hours_end.clone();
        } else {
            store.insert(prefs.id, prefs.clone());
        }

        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Database Implementation
// ---------------------------------------------------------------------------

/// Database-backed implementation of [`NotificationService`].
///
/// Uses the `notifications` table for persistent notification storage
/// and the `user_notification_preferences` table for preference management.
pub struct DatabaseNotificationService {
    pool: PgPool,
}

impl DatabaseNotificationService {
    /// Create a new [`DatabaseNotificationService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl NotificationService for DatabaseNotificationService {
    async fn notify(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        title: &str,
        body: &str,
        ntype: &str,
        ref_type: Option<&str>,
        ref_id: Option<EntityId>,
    ) -> Result<Notification> {
        let row = sqlx::query_as::<_, (Uuid, Uuid, Uuid, String, String, String, Option<String>, Option<Uuid>, bool, DateTime<Utc>)>(
            r#"INSERT INTO notifications (tenant_id, user_id, title, body, notification_type, entity_type, entity_id, is_read, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, false, NOW())
               RETURNING id, tenant_id, user_id, title, body, notification_type, entity_type, entity_id, is_read, created_at"#,
        )
        .bind(tenant_id)
        .bind(user_id)
        .bind(title)
        .bind(body)
        .bind(ntype)
        .bind(ref_type)
        .bind(ref_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create notification: {e}")))?;

        Ok(Notification {
            id: row.0,
            tenant_id: row.1,
            user_id: row.2,
            title: row.3,
            body: row.4,
            notification_type: row.5,
            reference_type: row.6,
            reference_id: row.7,
            is_read: row.8,
            created_at: row.9,
        })
    }

    async fn list_notifications(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        limit: i64,
        offset: i64,
    ) -> Result<Vec<Notification>> {
        let rows = sqlx::query_as::<_, (Uuid, Uuid, Uuid, String, String, String, Option<String>, Option<Uuid>, bool, DateTime<Utc>)>(
            r#"SELECT id, tenant_id, user_id, title, body, notification_type, entity_type, entity_id, is_read, created_at
               FROM notifications
               WHERE tenant_id = $1 AND user_id = $2
               ORDER BY created_at DESC
               LIMIT $3 OFFSET $4"#,
        )
        .bind(tenant_id)
        .bind(user_id)
        .bind(limit)
        .bind(offset)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list notifications: {e}")))?;

        Ok(rows
            .into_iter()
            .map(|r| Notification {
                id: r.0,
                tenant_id: r.1,
                user_id: r.2,
                title: r.3,
                body: r.4,
                notification_type: r.5,
                reference_type: r.6,
                reference_id: r.7,
                is_read: r.8,
                created_at: r.9,
            })
            .collect())
    }

    async fn unread_count(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
    ) -> Result<i64> {
        let (count,): (i64,) = sqlx::query_as(
            r#"SELECT COUNT(*) FROM notifications
               WHERE tenant_id = $1 AND user_id = $2 AND is_read = false"#,
        )
        .bind(tenant_id)
        .bind(user_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to count unread notifications: {e}")))?;

        Ok(count)
    }

    async fn mark_read(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        notification_id: EntityId,
    ) -> Result<()> {
        let result = sqlx::query(
            r#"UPDATE notifications
               SET is_read = true
               WHERE id = $1 AND tenant_id = $2 AND user_id = $3"#,
        )
        .bind(notification_id)
        .bind(tenant_id)
        .bind(user_id)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to mark notification as read: {e}")))?;

        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!(
                "Notification {notification_id} not found"
            )));
        }

        Ok(())
    }

    async fn mark_all_read(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
    ) -> Result<()> {
        sqlx::query(
            r#"UPDATE notifications
               SET is_read = true
               WHERE tenant_id = $1 AND user_id = $2 AND is_read = false"#,
        )
        .bind(tenant_id)
        .bind(user_id)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to mark all notifications as read: {e}")))?;

        Ok(())
    }

    async fn get_preferences(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
    ) -> Result<NotificationPreferences> {
        // Try to fetch existing preferences
        let result = sqlx::query_as::<_, (Uuid, Uuid, Uuid, bool, bool, bool, String, Option<String>, Option<String>)>(
            r#"SELECT id, tenant_id, user_id, email_notifications, push_notifications,
                      in_app_notifications, digest_frequency, quiet_hours_start::text, quiet_hours_end::text
               FROM user_notification_preferences
               WHERE tenant_id = $1 AND user_id = $2"#,
        )
        .bind(tenant_id)
        .bind(user_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get notification preferences: {e}")))?;

        if let Some(row) = result {
            return Ok(NotificationPreferences {
                id: row.0,
                tenant_id: row.1,
                user_id: row.2,
                email_notifications: row.3,
                push_notifications: row.4,
                in_app_notifications: row.5,
                digest_frequency: row.6,
                quiet_hours_start: row.7,
                quiet_hours_end: row.8,
            });
        }

        // Insert default preferences
        let row = sqlx::query_as::<_, (Uuid, Uuid, Uuid, bool, bool, bool, String, Option<String>, Option<String>)>(
            r#"INSERT INTO user_notification_preferences (tenant_id, user_id, email_notifications, push_notifications,
                      in_app_notifications, digest_frequency, quiet_hours_start, quiet_hours_end)
               VALUES ($1, $2, true, true, true, 'instant', NULL, NULL)
               RETURNING id, tenant_id, user_id, email_notifications, push_notifications,
                         in_app_notifications, digest_frequency, quiet_hours_start::text, quiet_hours_end::text"#,
        )
        .bind(tenant_id)
        .bind(user_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create default notification preferences: {e}")))?;

        Ok(NotificationPreferences {
            id: row.0,
            tenant_id: row.1,
            user_id: row.2,
            email_notifications: row.3,
            push_notifications: row.4,
            in_app_notifications: row.5,
            digest_frequency: row.6,
            quiet_hours_start: row.7,
            quiet_hours_end: row.8,
        })
    }

    async fn update_preferences(
        &self,
        prefs: &NotificationPreferences,
    ) -> Result<()> {
        let result = sqlx::query(
            r#"INSERT INTO user_notification_preferences (id, tenant_id, user_id, email_notifications, push_notifications,
                      in_app_notifications, digest_frequency, quiet_hours_start, quiet_hours_end, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8::time, $9::time, NOW())
               ON CONFLICT (tenant_id, user_id)
               DO UPDATE SET
                   email_notifications = EXCLUDED.email_notifications,
                   push_notifications = EXCLUDED.push_notifications,
                   in_app_notifications = EXCLUDED.in_app_notifications,
                   digest_frequency = EXCLUDED.digest_frequency,
                   quiet_hours_start = EXCLUDED.quiet_hours_start,
                   quiet_hours_end = EXCLUDED.quiet_hours_end,
                   updated_at = NOW()"#,
        )
        .bind(prefs.id)
        .bind(prefs.tenant_id)
        .bind(prefs.user_id)
        .bind(prefs.email_notifications)
        .bind(prefs.push_notifications)
        .bind(prefs.in_app_notifications)
        .bind(&prefs.digest_frequency)
        .bind(&prefs.quiet_hours_start)
        .bind(&prefs.quiet_hours_end)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update notification preferences: {e}")))?;

        // `result.rows_affected()` might be 0 on conflict-do-update
        // (it returns the number of rows modified, not matched), but this
        // is acceptable — the UPSERT guarantees the row exists afterwards.
        let _ = result;

        Ok(())
    }
}
