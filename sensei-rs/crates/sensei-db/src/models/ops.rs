//! Operations and lean manufacturing models for kanban, obeya, KPIs, tasks, and projects.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database representation of a kanban board.
///
/// Kanban boards provide visual workflow management for teams,
/// organizing work items into columns with WIP limits.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct KanbanBoardModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Board name.
    pub name: String,
    /// Board type (task, production, maintenance, quality, project, custom).
    pub board_type: String,
    /// Status (active, archived).
    pub status: String,
    /// Description.
    pub description: Option<String>,
    /// Board owner.
    pub owner_id: Option<Uuid>,
    /// Whether this is the default board for its type.
    pub is_default: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a kanban column.
///
/// Columns define the workflow stages within a kanban board,
/// with optional WIP (Work In Progress) limits.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct KanbanColumnModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent board.
    pub board_id: Uuid,
    /// Column name.
    pub name: String,
    /// Position within the board.
    pub position: i32,
    /// Work In Progress limit.
    pub wip_limit: Option<i32>,
    /// Column type (backlog, normal, done, blocked).
    pub column_type: String,
    /// Display color (hex).
    pub color: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an obeya board.
///
/// Obeya (big room) boards support visual management for daily
/// standups, project reviews, and SQDCP tracking.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ObeyaBoardModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Board name.
    pub name: String,
    /// Human-readable board number.
    pub board_number: String,
    /// Board type (daily_management, project, strategy, safety, quality, custom).
    pub r#type: String,
    /// Status (active, archived).
    pub status: String,
    /// Description.
    pub description: Option<String>,
    /// Physical location.
    pub location: Option<String>,
    /// Board owner.
    pub owner_id: Option<Uuid>,
    /// Meeting cadence (e.g., "daily", "weekly").
    pub meeting_cadence: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an obeya item.
///
/// Items on obeya boards representing actions, metrics, issues,
/// or decisions organized by SQDCP category.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ObeyaItemModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent board.
    pub board_id: Uuid,
    /// Item type (action, metric, issue, idea, decision, information).
    pub r#type: String,
    /// Status (open, in_progress, completed, closed).
    pub status: String,
    /// SQDCP category (safety, quality, delivery, cost, people).
    pub sqdcp_category: Option<String>,
    /// Item title.
    pub title: String,
    /// Description.
    pub description: Option<String>,
    /// Owner user ID.
    pub owner_id: Option<Uuid>,
    /// Due date.
    pub due_date: Option<DateTime<Utc>>,
    /// Priority (low, medium, high, critical).
    pub priority: Option<String>,
    /// Position on the board.
    pub position: i32,
    /// Additional data (JSON).
    pub data: serde_json::Value,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a standard work document.
///
/// Standard works define the current best practice for performing
/// a task, including step-by-step instructions and time targets.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct StandardWorkModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable document number.
    pub document_number: String,
    /// Document title.
    pub title: String,
    /// Product reference.
    pub product_id: Option<Uuid>,
    /// Work center reference.
    pub work_center_id: Option<Uuid>,
    /// Status (draft, active, under_review, obsolete).
    pub status: String,
    /// Version string.
    pub version: String,
    /// Description.
    pub description: Option<String>,
    /// Steps (JSON array of step objects).
    pub steps: serde_json::Value,
    /// Cycle time in minutes.
    pub cycle_time: Option<f64>,
    /// Takt time in minutes.
    pub takt_time: Option<f64>,
    /// User who created the document.
    pub created_by: Option<Uuid>,
    /// User who approved the document.
    pub approved_by: Option<Uuid>,
    /// Effective date.
    pub effective_date: Option<DateTime<Utc>>,
    /// Next review date.
    pub review_date: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a KPI definition.
///
/// KPI definitions specify measurable performance indicators with
/// targets, thresholds, and measurement frequency.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct KpiDefinitionModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// KPI name.
    pub name: String,
    /// Human-readable KPI code.
    pub kpi_code: String,
    /// Category (safety, quality, delivery, cost, people, operational, financial, environmental, custom).
    pub category: String,
    /// Unit of measurement.
    pub unit: String,
    /// Target value.
    pub target: f64,
    /// Minimum acceptable threshold.
    pub threshold: f64,
    /// Measurement frequency (hourly, daily, weekly, monthly, quarterly, annual).
    pub frequency: String,
    /// Status (active, inactive).
    pub status: String,
    /// Description.
    pub description: Option<String>,
    /// Calculation formula.
    pub formula: Option<String>,
    /// Data source system.
    pub data_source: Option<String>,
    /// KPI owner.
    pub owner_id: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a KPI value.
///
/// KPI values store time-series measurements for tracking
/// performance against targets.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct KpiValueModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// KPI definition.
    pub kpi_id: Uuid,
    /// Measured value.
    pub value: f64,
    /// Target value at time of measurement.
    pub target: Option<f64>,
    /// Measurement timestamp.
    pub timestamp: DateTime<Utc>,
    /// Data source.
    pub source: Option<String>,
    /// Notes.
    pub notes: Option<String>,
    /// User who recorded the value.
    pub recorded_by: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}

/// Database representation of a task.
///
/// Tasks are general-purpose work items that can be linked to any
/// entity in the system, with assignment, priority, and tagging.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct TaskModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable task number.
    pub task_number: String,
    /// Task title.
    pub title: String,
    /// Description.
    pub description: Option<String>,
    /// Status (open, in_progress, completed, cancelled, on_hold).
    pub status: String,
    /// Priority (low, medium, high, critical).
    pub priority: String,
    /// Task type (task, action_item, follow_up, review, approval).
    pub task_type: String,
    /// Assigned user.
    pub assignee_id: Option<Uuid>,
    /// Reporting user.
    pub reporter_id: Option<Uuid>,
    /// Due date.
    pub due_date: Option<DateTime<Utc>>,
    /// Completion timestamp.
    pub completed_at: Option<DateTime<Utc>>,
    /// Related entity type (e.g., "work_order", "ncr", "capa").
    pub related_entity_type: Option<String>,
    /// Related entity ID.
    pub related_entity_id: Option<Uuid>,
    /// Tags for categorization.
    pub tags: Option<Vec<String>>,
    /// Estimated hours.
    pub estimated_hours: Option<f64>,
    /// Actual hours spent.
    pub actual_hours: Option<f64>,
    /// Parent task (for subtasks).
    pub parent_task_id: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}
