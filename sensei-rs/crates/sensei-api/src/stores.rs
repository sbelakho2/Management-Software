//! Domain entity types and store aliases for route handlers.
//!
//! The domain structs defined here represent the various business entities
//! managed by the API. Each entity type has a corresponding store type alias
//! pointing to [`EntityStore<T>`](crate::db_stores::EntityStore), which
//! transparently switches between in-memory and PostgreSQL-backed storage.
//!
//! When no database is configured, stores operate purely in memory.
//! When `with_db_pool()` is called, each store is replaced with a
//! database-backed instance that persists mutations to the `entity_store`
//! table using a JSONB column approach.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::db_stores::EntityStore;

// ── Pagination ────────────────────────────────────────────────────────────────

/// Query-string parameters accepted by all paginated list endpoints.
///
/// Route handlers should accept `Query<PaginationParams>` and pass them to
/// `PaginatedResponse::new()` for consistent pagination behaviour.
///
/// # Defaults
/// - `page` defaults to `1`
/// - `per_page` defaults to `50`, clamped to `[1, 500]`
#[derive(Debug, Clone, Default, Deserialize)]
pub struct PaginationParams {
    /// Page number (1-based).
    pub page: Option<usize>,
    /// Items per page.
    pub per_page: Option<usize>,
}

impl PaginationParams {
    /// Maximum allowed items per page.
    pub const MAX_PER_PAGE: usize = 500;

    /// Resolve the page number with a default of 1.
    ///
    /// Page `0` (and other out-of-range values) is clamped to `1`; negative
    /// values are impossible because `usize` is unsigned.
    pub fn page(&self) -> usize {
        self.page.unwrap_or(1).max(1)
    }

    /// Resolve the per-page count, clamped to `[1, MAX_PER_PAGE]`.
    pub fn per_page(&self) -> usize {
        self.per_page
            .map(|p| p.clamp(1, Self::MAX_PER_PAGE))
            .unwrap_or(50)
    }

    /// Compute the SQL `OFFSET` value (saturating, so an enormous page
    /// number cannot overflow).
    pub fn offset(&self) -> usize {
        (self.page() - 1).saturating_mul(self.per_page())
    }
}

// ── Kanban ────────────────────────────────────────────────────────────────────

/// A Kanban board containing columns and cards.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct KanbanBoard {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub description: String,
    pub columns: Vec<KanbanColumn>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A column within a Kanban board.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct KanbanColumn {
    pub id: Uuid,
    pub board_id: Uuid,
    pub name: String,
    pub position: i32,
    pub wip_limit: Option<i32>,
    pub cards: Vec<KanbanCard>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A card within a Kanban column.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct KanbanCard {
    pub id: Uuid,
    pub column_id: Uuid,
    pub title: String,
    pub description: String,
    pub priority: String,
    pub assignee_id: Option<Uuid>,
    pub labels: Vec<String>,
    pub position: i32,
    pub due_date: Option<DateTime<Utc>>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    /// Set when the card is moved into a terminal ("done") column.
    #[serde(default)]
    pub completed_at: Option<DateTime<Utc>>,
}

/// Entity store for Kanban boards.
pub type KanbanBoardStore = EntityStore<KanbanBoard>;

// ── Notifications ────────────────────────────────────────────────────────────

/// A user notification.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Notification {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub user_id: Uuid,
    pub title: String,
    pub body: String,
    pub notification_type: String,
    pub reference_type: Option<String>,
    pub reference_id: Option<Uuid>,
    pub is_read: bool,
    pub created_at: DateTime<Utc>,
}

/// Notification preferences for a user.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NotificationPreferences {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub user_id: Uuid,
    pub email_notifications: bool,
    pub push_notifications: bool,
    pub in_app_notifications: bool,
    pub digest_frequency: String,
    pub quiet_hours_start: Option<String>,
    pub quiet_hours_end: Option<String>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for notifications.
pub type NotificationStore = EntityStore<Notification>;

/// Entity store for notification preferences.
pub type NotificationPreferencesStore = EntityStore<NotificationPreferences>;

// ── Attachments ──────────────────────────────────────────────────────────────

/// A file attachment linked to an entity.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Attachment {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub entity_type: String,
    pub entity_id: Uuid,
    pub file_name: String,
    pub content_type: String,
    pub file_size: i64,
    pub storage_path: String,
    pub uploaded_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// Entity store for attachment metadata.
pub type AttachmentMetaStore = EntityStore<Attachment>;

/// Entity store for raw attachment binary data.
pub type AttachmentDataStore = EntityStore<Vec<u8>>;

// ── Quote Version ────────────────────────────────────────────────────────────

/// A frozen version snapshot of a Quote.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct QuoteVersion {
    pub id: Uuid,
    pub quote_id: Uuid,
    pub tenant_id: Uuid,
    pub version_number: i32,
    pub quote_data: serde_json::Value,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// Entity store for quote versions.
pub type QuoteVersionStore = EntityStore<QuoteVersion>;

// ── Learning Module ──────────────────────────────────────────────────────────

/// A learning module / training course.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LearningModule {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub title: String,
    pub description: String,
    pub category: String,
    pub difficulty: String,
    pub estimated_duration_minutes: Option<i32>,
    pub content_url: Option<String>,
    pub is_published: bool,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for learning modules.
pub type LearningModuleStore = EntityStore<LearningModule>;

// ── Opportunity ──────────────────────────────────────────────────────────────

/// A sales or business opportunity.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Opportunity {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub title: String,
    pub description: String,
    pub customer_id: Uuid,
    pub customer_name: String,
    pub stage: String,
    pub probability: f64,
    pub expected_value: f64,
    pub currency: String,
    pub expected_close_date: Option<DateTime<Utc>>,
    pub assigned_to: Option<Uuid>,
    pub notes: String,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for opportunities.
pub type OpportunityStore = EntityStore<Opportunity>;

// ── Escalation Policy ─────────────────────────────────────────────────────────

/// A rule within an escalation policy.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EscalationRule {
    pub id: Uuid,
    pub priority: i32,
    pub condition: String,
    pub notify_user_ids: Vec<Uuid>,
    pub notify_role: Option<String>,
    pub escalate_after_seconds: i32,
}

/// An escalation policy with one or more rules.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EscalationPolicy {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub description: String,
    pub event_type: String,
    pub is_active: bool,
    pub rules: Vec<EscalationRule>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for escalation policies.
pub type EscalationPolicyStore = EntityStore<EscalationPolicy>;

// ── Training Matrix ───────────────────────────────────────────────────────────

/// A training matrix entry linking a skill to an employee.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TrainingMatrixEntry {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub employee_id: Uuid,
    pub employee_name: String,
    pub skill_name: String,
    pub skill_category: String,
    pub proficiency_level: String,
    pub certification_id: Option<String>,
    pub last_assessed_at: Option<DateTime<Utc>>,
    pub valid_until: Option<DateTime<Utc>>,
    pub notes: String,
    pub assessed_by: Option<Uuid>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for training matrix entries.
pub type TrainingMatrixStore = EntityStore<TrainingMatrixEntry>;

// ── Knowledge Pack ────────────────────────────────────────────────────────────

/// A knowledge pack containing curated content.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct KnowledgePack {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub title: String,
    pub description: String,
    pub category: String,
    pub tags: Vec<String>,
    pub content: String,
    pub source_url: Option<String>,
    pub version: String,
    pub is_published: bool,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for knowledge packs.
pub type KnowledgePackStore = EntityStore<KnowledgePack>;

// ── Smart Ingestion ───────────────────────────────────────────────────────────

/// Status of a document ingestion job.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum IngestionStatus {
    Pending,
    Processing,
    Completed,
    Failed(String),
}

/// An ingestion job tracking document processing.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IngestionJob {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub file_name: String,
    pub content_type: String,
    pub file_size: i64,
    pub status: IngestionStatus,
    pub extracted_text: Option<String>,
    pub extracted_data: Option<serde_json::Value>,
    pub error_message: Option<String>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

/// Entity store for ingestion jobs.
pub type IngestionJobStore = EntityStore<IngestionJob>;

/// Entity store for raw ingestion binary data.
pub type IngestionDataStore = EntityStore<Vec<u8>>;

// ── Work Centers ──────────────────────────────────────────────────────────────

/// A work center (production cell / manufacturing unit).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkCenter {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub work_center_number: String,
    pub name: String,
    pub description: String,
    pub work_center_type: String,
    pub department: Option<String>,
    pub location: Option<String>,
    pub is_active: bool,
    pub capacity_per_shift: i32,
    pub shifts_per_day: i32,
    pub efficiency: f64,
    pub available_hours_per_day: f64,
    pub notes: String,
    pub supervisor_id: Option<Uuid>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for work centers.
pub type WorkCenterStore = EntityStore<WorkCenter>;

// ── Obeya ─────────────────────────────────────────────────────────────────────

/// An Obeya (war room / big room) board for visual management.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ObeyaBoard {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub description: String,
    pub board_type: String,
    pub department: Option<String>,
    pub location: Option<String>,
    pub is_active: bool,
    pub items: Vec<ObeyaItem>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// An item/card on an Obeya board.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ObeyaItem {
    pub id: Uuid,
    pub board_id: Uuid,
    pub title: String,
    pub description: String,
    pub item_type: String,
    pub status: String,
    pub priority: String,
    pub owner_id: Option<Uuid>,
    pub target_date: Option<DateTime<Utc>>,
    pub completed_at: Option<DateTime<Utc>>,
    pub notes: String,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for Obeya boards.
pub type ObeyaBoardStore = EntityStore<ObeyaBoard>;

// ── CTQ (Critical-To-Quality) ─────────────────────────────────────────────────

/// A CTQ (Critical-To-Quality) characteristic.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CtqCharacteristic {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub description: String,
    pub category: String,
    pub specification_limit_lower: Option<f64>,
    pub specification_limit_upper: Option<f64>,
    pub target_value: Option<f64>,
    pub unit: Option<String>,
    pub measurement_method: String,
    pub is_active: bool,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A recorded measurement for a CTQ characteristic.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CtqRecord {
    pub id: Uuid,
    pub characteristic_id: Uuid,
    pub tenant_id: Uuid,
    pub value: f64,
    pub recorded_at: DateTime<Utc>,
    pub recorded_by: Option<Uuid>,
    pub work_order_id: Option<Uuid>,
    pub lot_id: Option<String>,
    pub is_conforming: bool,
    pub notes: Option<String>,
}

/// Entity store for CTQ characteristics.
pub type CtqCharacteristicStore = EntityStore<CtqCharacteristic>;

/// Entity store for CTQ measurement records.
pub type CtqRecordStore = EntityStore<CtqRecord>;

// ── Inventory ─────────────────────────────────────────────────────────────────

/// An inventory item / stock keeping unit.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InventoryItem {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub sku: String,
    pub name: String,
    pub description: String,
    pub category: String,
    pub warehouse_id: Uuid,
    pub quantity_on_hand: f64,
    pub quantity_reserved: f64,
    pub quantity_available: f64,
    pub unit_cost: f64,
    pub total_value: f64,
    pub reorder_point: f64,
    pub reorder_quantity: f64,
    pub is_active: bool,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A stock move (adjustment, transfer, receipt, issue).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StockMove {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub item_id: Uuid,
    pub warehouse_id: Uuid,
    pub move_type: String,
    pub quantity: f64,
    pub reference_type: Option<String>,
    pub reference_id: Option<Uuid>,
    pub notes: String,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// A warehouse / storage location.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Warehouse {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub code: String,
    pub location: String,
    pub is_active: bool,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for inventory items.
pub type InventoryItemStore = EntityStore<InventoryItem>;

/// Entity store for stock moves.
pub type StockMoveStore = EntityStore<StockMove>;

/// Entity store for warehouses.
pub type WarehouseStore = EntityStore<Warehouse>;

// ── MRP (Material Requirements Planning) ──────────────────────────────────────

/// A demand entry for MRP.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DemandEntry {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity: f64,
    pub due_date: DateTime<Utc>,
    pub source_type: String,
    pub source_id: Option<Uuid>,
    pub notes: String,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A planned supply order from MRP.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SupplyOrder {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub product_id: Uuid,
    pub product_name: String,
    pub quantity: f64,
    pub order_date: DateTime<Utc>,
    pub expected_delivery: DateTime<Utc>,
    pub status: String,
    pub notes: String,
    /// ID of the MRP run that generated this supply order.
    #[serde(default)]
    pub run_id: Option<Uuid>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// An MRP run (net requirements calculation execution).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MrpRun {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub run_type: String,
    pub status: String,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub summary: serde_json::Value,
    pub created_by: Uuid,
}

/// Entity store for MRP demand entries.
pub type DemandEntryStore = EntityStore<DemandEntry>;

/// Entity store for MRP supply orders.
pub type SupplyOrderStore = EntityStore<SupplyOrder>;

/// Entity store for MRP runs.
pub type MrpRunStore = EntityStore<MrpRun>;

// ── Tasks ─────────────────────────────────────────────────────────────────────

/// The status of a task within its lifecycle.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum TaskStatus {
    #[default]
    Open,
    InProgress,
    InReview,
    Completed,
    Cancelled,
    Blocked,
}

impl std::fmt::Display for TaskStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TaskStatus::Open => write!(f, "open"),
            TaskStatus::InProgress => write!(f, "in_progress"),
            TaskStatus::InReview => write!(f, "in_review"),
            TaskStatus::Completed => write!(f, "completed"),
            TaskStatus::Cancelled => write!(f, "cancelled"),
            TaskStatus::Blocked => write!(f, "blocked"),
        }
    }
}

/// The priority level of a task.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum TaskPriority {
    Low,
    #[default]
    Medium,
    High,
    Critical,
}

impl std::fmt::Display for TaskPriority {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TaskPriority::Low => write!(f, "low"),
            TaskPriority::Medium => write!(f, "medium"),
            TaskPriority::High => write!(f, "high"),
            TaskPriority::Critical => write!(f, "critical"),
        }
    }
}

/// A task for tracking work items.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Task {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub title: String,
    pub description: String,
    pub status: TaskStatus,
    pub priority: TaskPriority,
    pub assignee_id: Option<Uuid>,
    pub due_date: Option<DateTime<Utc>>,
    pub category: String,
    pub tags: Vec<String>,
    pub estimated_hours: Option<f64>,
    pub actual_hours: Option<f64>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    /// The state machine instance ID, if this task is governed by a state machine.
    pub state_machine_instance_id: Option<Uuid>,
}

/// Entity store for tasks.
pub type TaskStore = EntityStore<Task>;

// ── Audit Logs ────────────────────────────────────────────────────────────────

/// An audit log entry tracking state-changing operations.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AuditLogEntry {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub entity_type: String,
    pub entity_id: Uuid,
    pub action: String,
    pub user_id: Uuid,
    pub changes: Option<serde_json::Value>,
    pub ip_address: Option<String>,
    pub user_agent: Option<String>,
    pub created_at: DateTime<Utc>,
}

/// Entity store for audit log entries.
pub type AuditLogEntryStore = EntityStore<AuditLogEntry>;

// ── Production Cells ──────────────────────────────────────────────────────────

/// A production cell (manufacturing unit).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProductionCell {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub code: String,
    pub description: String,
    pub cell_type: String,
    pub location: Option<String>,
    pub is_active: bool,
    pub capacity_per_shift: i32,
    pub shifts_per_day: i32,
    pub efficiency_target: f64,
    pub supervisor_id: Option<Uuid>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for production cells.
pub type ProductionCellStore = EntityStore<ProductionCell>;

// ── Saved Views ───────────────────────────────────────────────────────────────

/// Visibility level for a saved view.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ViewVisibility {
    /// Only the creator can see this view.
    #[default]
    Private,
    /// All users in the same team can see this view.
    Team,
    /// All users in the same department can see this view.
    Dept,
    /// All users in the tenant can see this view.
    Org,
}

impl std::fmt::Display for ViewVisibility {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ViewVisibility::Private => write!(f, "private"),
            ViewVisibility::Team => write!(f, "team"),
            ViewVisibility::Dept => write!(f, "dept"),
            ViewVisibility::Org => write!(f, "org"),
        }
    }
}

/// Sort direction for a sort column.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum SortDirection {
    /// Ascending order (A-Z, 0-9).
    #[default]
    Asc,
    /// Descending order (Z-A, 9-0).
    Desc,
}

/// A single sort column configuration.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SortConfig {
    /// The field name to sort by.
    pub field: String,
    /// The sort direction.
    #[serde(default)]
    pub direction: SortDirection,
}

/// A user-saved view configuration.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SavedView {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub user_id: Uuid,
    pub name: String,
    pub entity_type: String,
    pub filters: serde_json::Value,
    /// Compound sort configuration (replaces the old sort_by/sort_order).
    #[serde(default)]
    pub sort_config: Vec<SortConfig>,
    pub columns: Vec<String>,
    pub is_default: bool,
    /// Visibility level for RBAC-based sharing.
    #[serde(default)]
    pub visibility: ViewVisibility,
    /// Explicit list of user IDs this view is shared with.
    #[serde(default)]
    pub shared_with: Vec<Uuid>,
    /// Number of times the view has been opened.
    #[serde(default)]
    pub view_count: u64,
    /// Timestamp of the last time the view was opened.
    #[serde(default)]
    pub last_used_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for saved views.
pub type SavedViewStore = EntityStore<SavedView>;

// ── Helper to create empty stores ─────────────────────────────────────────────

macro_rules! new_store {
    ($entity_type:expr) => {
        $crate::db_stores::EntityStore::new($entity_type)
    };
}

// ── Quoting Helper ──────────────────────────────────────────────────────────

/// A work packet for an RFQ, representing a discipline's work assignment.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkPacket {
    pub id: Uuid,
    pub rfq_id: Uuid,
    pub tenant_id: Uuid,
    pub line_items: Vec<Uuid>,
    pub template_id: Option<Uuid>,
    pub status: String,
    pub workpackets: Vec<WorkPacketOperation>,
    pub notes: Option<String>,
    pub estimated_hours: Option<f64>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// An operation within a work packet.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkPacketOperation {
    pub operation: String,
    pub estimated_hours: f64,
}

/// Entity store for work packets.
pub type WorkPacketStore = EntityStore<WorkPacket>;

/// A cost build for a quote, capturing rolled-up cost calculations.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CostBuild {
    pub id: Uuid,
    pub quote_id: Uuid,
    pub tenant_id: Uuid,
    pub material_costs: serde_json::Value,
    pub labor_costs: serde_json::Value,
    pub overhead_percentage: f64,
    pub margin_percentage: f64,
    pub total_cost: f64,
    pub selling_price: f64,
    pub margin: f64,
    pub breakdown: serde_json::Value,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// Entity store for cost builds.
pub type CostBuildStore = EntityStore<CostBuild>;

/// An NPI (New Product Introduction) conversion record.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NpiConversion {
    pub id: Uuid,
    pub npi_project_id: Uuid,
    pub quote_id: Uuid,
    pub tenant_id: Uuid,
    pub status: String,
    pub converted_at: DateTime<Utc>,
    pub created_by: Uuid,
}

/// Entity store for NPI conversions.
pub type NpiConversionStore = EntityStore<NpiConversion>;

// ── Helper to create empty stores (needed by new types above) ────────────────

pub(crate) use new_store;

// ── KPI (Key Performance Indicators) ─────────────────────────────────────────

/// Category of a KPI.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum KpiCategory {
    Quality,
    Production,
    Maintenance,
    Inventory,
    Safety,
    Cost,
    Delivery,
    People,
}

/// Direction indicating whether higher/lower/target values are better.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum KpiDirection {
    HigherIsBetter,
    LowerIsBetter,
    TargetIsBetter,
}

/// A Key Performance Indicator definition.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct KpiDefinition {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub category: KpiCategory,
    pub unit: String,
    pub target: Option<f64>,
    pub lower_limit: Option<f64>,
    pub upper_limit: Option<f64>,
    pub direction: KpiDirection,
    pub formula: Option<String>,
    pub owner_role: Option<String>,
    pub is_active: bool,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A recorded value for a KPI at a point in time.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct KpiValue {
    pub id: Uuid,
    pub kpi_id: Uuid,
    pub tenant_id: Uuid,
    pub value: f64,
    pub recorded_at: DateTime<Utc>,
    pub note: Option<String>,
    pub recorded_by: Uuid,
}

/// Entity store for KPI definitions.
pub type KpiDefinitionStore = EntityStore<KpiDefinition>;

/// Entity store for KPI values.
pub type KpiValueStore = EntityStore<KpiValue>;

// ── LSW (Layer Standard Work) ────────────────────────────────────────────────

/// Frequency of an LSW standard.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum LswFrequency {
    Hourly,
    Daily,
    Weekly,
    Monthly,
}

/// A checklist item within an LSW standard.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LswChecklistItem {
    pub id: Uuid,
    pub description: String,
    pub expected_value: Option<String>,
    pub is_critical: bool,
}

/// An LSW standard (layer standard work definition).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LswStandard {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub title: String,
    pub area: String,
    pub layer: u8,
    pub frequency: LswFrequency,
    pub checklist_items: Vec<LswChecklistItem>,
    pub is_active: bool,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Result of a single checklist item during an audit.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LswAuditResult {
    pub item_id: Uuid,
    pub passed: bool,
    pub observed_value: Option<String>,
    pub notes: Option<String>,
}

/// An LSW audit (checklist execution).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LswAudit {
    pub id: Uuid,
    pub standard_id: Uuid,
    pub tenant_id: Uuid,
    pub auditor_id: Uuid,
    pub area: String,
    pub layer: u8,
    pub results: Vec<LswAuditResult>,
    pub compliance_rate: f64,
    pub notes: Option<String>,
    pub audited_at: DateTime<Utc>,
}

/// Entity store for LSW standards.
pub type LswStandardStore = EntityStore<LswStandard>;

/// Entity store for LSW audits.
pub type LswAuditStore = EntityStore<LswAudit>;

// ── Notification Triggers ────────────────────────────────────────────────────

/// A notification channel.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum NotificationChannel {
    InApp,
    Email,
    SMS,
    Webhook,
}

/// Action to take when a notification trigger fires.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NotificationAction {
    pub template: Option<String>,
    pub payload: Option<serde_json::Value>,
}

/// An event-driven notification trigger rule.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NotificationTrigger {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub event_type: String,
    pub condition: serde_json::Value,
    pub action: NotificationAction,
    pub channels: Vec<NotificationChannel>,
    pub cooldown_minutes: Option<i32>,
    pub is_active: bool,
    /// Roles whose users receive the notification when this trigger fires.
    #[serde(default)]
    pub target_roles: Vec<String>,
    pub last_triggered_at: Option<DateTime<Utc>>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Entity store for notification triggers.
pub type NotificationTriggerStore = EntityStore<NotificationTrigger>;

// ── Standard Work ────────────────────────────────────────────────────────────

/// Status of a standard work document.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum SwStatus {
    Draft,
    Published,
    Archived,
}

/// A single work step in a standard work document.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WorkStep {
    pub id: Uuid,
    pub step_number: i32,
    pub description: String,
    pub key_points: Vec<String>,
    pub safety_warning: Option<String>,
    pub duration_seconds: Option<i32>,
    pub photo_id: Option<Uuid>,
}

/// A quality check within a standard work document.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct QualityCheck {
    pub id: Uuid,
    pub description: String,
    pub standard: String,
    pub method: String,
    pub frequency: String,
}

/// A standard work document.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StandardWorkDocument {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub title: String,
    pub document_number: String,
    pub area: String,
    pub process: String,
    pub current_version: i32,
    pub status: SwStatus,
    pub steps: Vec<WorkStep>,
    pub required_skills: Vec<String>,
    pub cycle_time_seconds: Option<i32>,
    pub takt_time_seconds: Option<i32>,
    pub quality_checks: Vec<QualityCheck>,
    pub safety_notes: Vec<String>,
    pub tools_required: Vec<String>,
    pub materials_required: Vec<String>,
    pub attachments: Vec<Uuid>,
    pub approved_by: Option<Uuid>,
    pub approved_at: Option<DateTime<Utc>>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A frozen version of a standard work document.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StandardWorkVersion {
    pub id: Uuid,
    pub document_id: Uuid,
    pub tenant_id: Uuid,
    pub version_number: i32,
    pub snapshot: serde_json::Value,
    pub change_notes: Option<String>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
}

/// Entity store for standard work documents.
pub type StandardWorkStore = EntityStore<StandardWorkDocument>;

/// Entity store for standard work versions.
pub type StandardWorkVersionStore = EntityStore<StandardWorkVersion>;

// ── State Machines ───────────────────────────────────────────────────────────

/// A state definition within a state machine.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StateDefinition {
    pub name: String,
    pub label: String,
    pub is_terminal: bool,
    pub allowed_roles: Vec<String>,
}

/// A transition definition between states.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TransitionDefinition {
    pub from_state: String,
    pub to_state: String,
    pub event: String,
    pub conditions: Option<serde_json::Value>,
    pub on_transition: Option<serde_json::Value>,
}

/// A state machine definition.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StateMachineDefinition {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub entity_type: String,
    pub states: Vec<StateDefinition>,
    pub transitions: Vec<TransitionDefinition>,
    pub initial_state: String,
    pub is_active: bool,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A running instance of a state machine.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StateMachineInstance {
    pub id: Uuid,
    pub definition_id: Uuid,
    pub tenant_id: Uuid,
    pub entity_id: Uuid,
    pub current_state: String,
    pub state_history: Vec<StateTransitionRecord>,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A record of a state transition.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StateTransitionRecord {
    pub from_state: String,
    pub to_state: String,
    pub event: String,
    pub triggered_by: Uuid,
    pub triggered_at: DateTime<Utc>,
    pub metadata: Option<serde_json::Value>,
}

/// Entity store for state machine definitions.
pub type StateMachineDefinitionStore = EntityStore<StateMachineDefinition>;

/// Entity store for state machine instances.
pub type StateMachineInstanceStore = EntityStore<StateMachineInstance>;

// ── Training (General Training Courses) ───────────────────────────────────────

/// Category of a training course.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TrainingCategory {
    Safety,
    Quality,
    Technical,
    Leadership,
    Compliance,
    Onboarding,
}

/// Enrollment status for a training course.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum TrainingEnrollmentStatus {
    Enrolled,
    InProgress,
    Completed,
    Passed,
    Failed,
    Expired,
}

/// A general training course.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TrainingCourse {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub title: String,
    pub description: Option<String>,
    pub category: TrainingCategory,
    pub duration_minutes: i32,
    pub required_for_roles: Vec<String>,
    pub prerequisites: Vec<Uuid>,
    pub content_url: Option<String>,
    pub passing_score: Option<f64>,
    pub is_mandatory: bool,
    pub is_active: bool,
    pub created_by: Uuid,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// A user's enrollment in a training course.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TrainingEnrollment {
    pub id: Uuid,
    pub course_id: Uuid,
    pub tenant_id: Uuid,
    pub user_id: Uuid,
    pub status: TrainingEnrollmentStatus,
    pub score: Option<f64>,
    pub completed_at: Option<DateTime<Utc>>,
    pub deadline: Option<DateTime<Utc>>,
    pub enrolled_by: Uuid,
    pub enrolled_at: DateTime<Utc>,
}

/// Entity store for training courses.
pub type TrainingCourseStore = EntityStore<TrainingCourse>;

/// Entity store for training enrollments.
pub type TrainingEnrollmentStore = EntityStore<TrainingEnrollment>;
