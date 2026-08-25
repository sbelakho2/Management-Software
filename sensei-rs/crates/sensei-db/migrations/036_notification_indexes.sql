-- Notification indexes.
--
-- The notification service filters by (tenant, user) with read-state and
-- timestamp ordering; the preferences table is upserted by (tenant, user).

CREATE INDEX IF NOT EXISTS idx_notifications_user
    ON notifications (tenant_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_unread
    ON notifications (tenant_id, user_id) WHERE is_read = FALSE;
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_notification_prefs_tenant_user
    ON user_notification_preferences (tenant_id, user_id);
