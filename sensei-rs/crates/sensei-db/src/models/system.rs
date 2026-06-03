//! System and cross-cutting models for notifications, state, knowledge, and configuration.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database representation of a notification preference.
///
/// Users can configure their notification preferences per channel and event type.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct NotificationPreferenceModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// User whose preference this is.
    pub user_id: Uuid,
    /// Notification channel (in_app, email, sms, push, webhook).
    pub channel: String,
    /// Event type to notify about.
    pub event_type: String,
    /// Whether notifications are enabled.
    pub enabled: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a data lineage link.
///
/// Data lineage links trace data flow between entities for
/// auditability and impact analysis.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct DataLineageLinkModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Source entity type.
    pub source_entity: String,
    /// Source entity ID.
    pub source_id: Uuid,
    /// Target entity type.
    pub target_entity: String,
    /// Target entity ID.
    pub target_id: Uuid,
    /// Transformation description.
    pub transformation: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of an AI reasoning trace.
///
/// Reasoning traces capture AI agent inputs, outputs, and performance
/// metrics for audit and debugging purposes.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ReasoningTraceModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Agent type identifier.
    pub agent_type: String,
    /// Input provided to the agent.
    pub input: String,
    /// Output produced by the agent.
    pub output: String,
    /// Number of tokens consumed.
    pub tokens_used: i32,
    /// Processing duration in milliseconds.
    pub duration_ms: i32,
    /// Model name used.
    pub model_name: Option<String>,
    /// Additional metadata (JSON).
    pub metadata: serde_json::Value,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of service state.
///
/// Service state provides persistent key-value storage for services,
/// state machines, and configuration data.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ServiceStateModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Service name.
    pub service_name: String,
    /// State key within the service.
    pub state_key: String,
    /// State value (JSON).
    pub state_value: serde_json::Value,
    /// User who last updated the state.
    pub updated_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a saved view.
///
/// Saved views store user-customizable list and dashboard configurations
/// for quick access to filtered and sorted data.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SavedViewModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// User who owns the view.
    pub user_id: Uuid,
    /// View name.
    pub name: String,
    /// Entity type the view applies to.
    pub entity_type: String,
    /// View configuration (filters, sorting, columns) as JSON.
    pub config: serde_json::Value,
    /// Whether this is the user's default view for the entity.
    pub is_default: bool,
    /// Whether the view is shared with other users.
    pub is_shared: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a site/facility.
///
/// Sites represent physical locations where operations occur,
/// with address and timezone information.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SiteModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Site name.
    pub name: String,
    /// Human-readable site code.
    pub site_code: String,
    /// Physical address.
    pub address: Option<String>,
    /// City.
    pub city: Option<String>,
    /// State/province.
    pub state: Option<String>,
    /// Postal/ZIP code.
    pub postal_code: Option<String>,
    /// Country.
    pub country: Option<String>,
    /// Timezone (IANA format, e.g., "Europe/Paris").
    pub timezone: String,
    /// Whether the site is active.
    pub is_active: bool,
    /// Whether this is the headquarters.
    pub is_headquarters: bool,
    /// Contact phone.
    pub contact_phone: Option<String>,
    /// Contact email.
    pub contact_email: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an escalation policy.
///
/// Escalation policies define rules for automatic escalation of issues
/// based on time, severity, or other conditions.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct EscalationPolicyModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Policy name.
    pub name: String,
    /// Entity type the policy applies to.
    pub entity_type: String,
    /// Escalation rules (JSON array).
    pub rules: serde_json::Value,
    /// Whether the policy is active.
    pub is_active: bool,
    /// Description.
    pub description: Option<String>,
    /// User who created the policy.
    pub created_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a notification trigger.
///
/// Notification triggers define automated notification rules
/// based on system events and conditions.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct NotificationTriggerModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Trigger name.
    pub name: String,
    /// Event type that fires the trigger.
    pub event_type: String,
    /// Entity type filter.
    pub entity_type: Option<String>,
    /// Conditions for firing (JSON).
    pub conditions: serde_json::Value,
    /// Actions to take when fired (JSON array).
    pub actions: serde_json::Value,
    /// Whether the trigger is active.
    pub is_active: bool,
    /// Description.
    pub description: Option<String>,
    /// User who created the trigger.
    pub created_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a knowledge pack.
///
/// Knowledge packs store structured content for AI agents and user
/// reference, with vector embeddings for semantic search.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct KnowledgePackModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Pack name.
    pub name: String,
    /// Category.
    pub category: Option<String>,
    /// Content (JSON).
    pub content: serde_json::Value,
    /// Version string.
    pub version: String,
    /// Language code (e.g., "en", "fr").
    pub language: String,
    /// Tags for categorization.
    pub tags: Option<Vec<String>>,
    /// Status (draft, published, archived).
    pub status: String,
    /// User who created the pack.
    pub created_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a learning module.
///
/// Learning modules are educational content units with various
/// content types, difficulty levels, and prerequisite tracking.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct LearningModuleModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Module title.
    pub title: String,
    /// Human-readable module code.
    pub module_code: String,
    /// Description.
    pub description: Option<String>,
    /// Category.
    pub category: Option<String>,
    /// Content type (document, video, interactive, quiz, scorm).
    pub content_type: String,
    /// Content data (JSON).
    pub content: serde_json::Value,
    /// Duration in minutes.
    pub duration_minutes: i32,
    /// Difficulty level (beginner, intermediate, advanced, expert).
    pub difficulty: String,
    /// Status (draft, published, archived).
    pub status: String,
    /// Version string.
    pub version: String,
    /// Prerequisite module IDs.
    pub prerequisites: Option<Vec<Uuid>>,
    /// Tags for categorization.
    pub tags: Option<Vec<String>>,
    /// User who created the module.
    pub created_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a training matrix entry.
///
/// The training matrix maps required skills to roles and employees,
/// tracking gaps and training status.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct TrainingMatrixModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Site reference.
    pub site_id: Option<Uuid>,
    /// Role name.
    pub role: String,
    /// Skill name.
    pub skill: String,
    /// Required proficiency level (1-5).
    pub required_level: i32,
    /// Current proficiency level (0-5).
    pub current_level: i32,
    /// Gap between required and current level.
    pub gap: i32,
    /// Employee reference.
    pub employee_id: Option<Uuid>,
    /// Training program reference.
    pub training_program_id: Option<Uuid>,
    /// Due date for gap closure.
    pub due_date: Option<DateTime<Utc>>,
    /// Status (pending, in_progress, completed, overdue).
    pub status: String,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}
