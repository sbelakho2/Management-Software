//! Maintenance management models for assets, work orders, spare parts, and downtime.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database representation of an asset.
///
/// Assets are company property tracked in the asset register,
/// including equipment, vehicles, buildings, and tools.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AssetModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Asset name.
    pub name: String,
    /// Human-readable asset number.
    pub asset_number: String,
    /// Description.
    pub description: Option<String>,
    /// Asset type (equipment, vehicle, building, tool, it_equipment, other).
    pub asset_type: String,
    /// Physical location.
    pub location: Option<String>,
    /// Department.
    pub department: Option<String>,
    /// Status (active, in_storage, in_maintenance, disposed, retired).
    pub status: String,
    /// Category.
    pub category: Option<String>,
    /// Manufacturer.
    pub manufacturer: Option<String>,
    /// Model number.
    pub model: Option<String>,
    /// Serial number.
    pub serial_number: Option<String>,
    /// Acquisition date.
    pub acquisition_date: Option<DateTime<Utc>>,
    /// Purchase price.
    pub purchase_price: Option<f64>,
    /// Current book value.
    pub current_value: Option<f64>,
    /// Useful life in months.
    pub useful_life_months: Option<i32>,
    /// Residual/salvage value.
    pub residual_value: Option<f64>,
    /// Linked equipment record.
    pub equipment_id: Option<Uuid>,
    /// Parent asset (for component hierarchy).
    pub parent_id: Option<Uuid>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a maintenance work order.
///
/// Maintenance work orders track corrective, preventive, and predictive
/// maintenance activities for assets and equipment.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct MaintenanceWorkOrderModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Human-readable MWO number.
    pub mwo_number: String,
    /// Asset being maintained.
    pub asset_id: Uuid,
    /// Equipment reference.
    pub equipment_id: Option<Uuid>,
    /// Type (corrective, preventive, predictive, emergency).
    pub r#type: String,
    /// Priority (low, medium, high, emergency).
    pub priority: String,
    /// Status (open, assigned, in_progress, completed, cancelled).
    pub status: String,
    /// Description of the work.
    pub description: String,
    /// Assigned technician.
    pub assigned_to: Option<Uuid>,
    /// Requesting user.
    pub requested_by: Option<Uuid>,
    /// Scheduled start.
    pub scheduled_start: Option<DateTime<Utc>>,
    /// Scheduled end.
    pub scheduled_end: Option<DateTime<Utc>>,
    /// Actual start.
    pub actual_start: Option<DateTime<Utc>>,
    /// Actual end.
    pub actual_end: Option<DateTime<Utc>>,
    /// Downtime hours caused.
    pub downtime_hours: f64,
    /// Root cause analysis.
    pub root_cause: Option<String>,
    /// Resolution description.
    pub resolution: Option<String>,
    /// Parts used (JSON array).
    pub parts_used: serde_json::Value,
    /// Labor hours.
    pub labor_hours: f64,
    /// Total cost.
    pub cost: f64,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a spare part.
///
/// Spare parts inventory for maintenance operations, with
/// reorder tracking and supplier information.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SparePartModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Part number.
    pub part_number: String,
    /// Part name.
    pub name: String,
    /// Description.
    pub description: Option<String>,
    /// Current quantity on hand.
    pub quantity_on_hand: f64,
    /// Quantity reserved for work orders.
    pub quantity_reserved: f64,
    /// Reorder trigger point.
    pub reorder_point: f64,
    /// Quantity to order when reordering.
    pub reorder_quantity: f64,
    /// Cost per unit.
    pub unit_cost: f64,
    /// Unit of measure.
    pub unit_of_measure: String,
    /// Preferred supplier.
    pub supplier_id: Option<Uuid>,
    /// Supplier lead time in days.
    pub lead_time_days: Option<i32>,
    /// Storage location.
    pub location: Option<String>,
    /// Whether the part is active.
    pub is_active: bool,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a downtime event.
///
/// Downtime events track periods when assets or equipment are
/// not available for production.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct DowntimeEventModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Asset affected.
    pub asset_id: Uuid,
    /// Equipment reference.
    pub equipment_id: Option<Uuid>,
    /// Downtime start.
    pub start_time: DateTime<Utc>,
    /// Downtime end (null if ongoing).
    pub end_time: Option<DateTime<Utc>>,
    /// Reason for downtime.
    pub reason: String,
    /// Category (planned, unplanned, changeover, break, meeting, no_demand, other).
    pub category: String,
    /// Duration in minutes.
    pub duration_minutes: f64,
    /// Related maintenance work order.
    pub work_order_id: Option<Uuid>,
    /// User who reported the downtime.
    pub reported_by: Option<Uuid>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a LOTO (Lockout/Tagout) procedure.
///
/// LOTO procedures define safety protocols for equipment maintenance,
/// including authorized workers and step-by-step instructions.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct LotoProcedureModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Asset the procedure applies to.
    pub asset_id: Uuid,
    /// Human-readable procedure number.
    pub procedure_number: String,
    /// Procedure title.
    pub title: String,
    /// Status (draft, active, obsolete).
    pub status: String,
    /// Steps (JSON array of step objects).
    pub steps: serde_json::Value,
    /// Authorized worker user IDs.
    pub authorized_workers: Option<Vec<Uuid>>,
    /// Energy sources description.
    pub energy_sources: Option<String>,
    /// Required PPE.
    pub required_ppe: Option<String>,
    /// Review date.
    pub review_date: Option<DateTime<Utc>>,
    /// Approving user.
    pub approved_by: Option<Uuid>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a tool item.
///
/// Tools managed in the tool crib, including checkout status
/// and calibration tracking.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ToolItemModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Tool name.
    pub name: String,
    /// Part number.
    pub part_number: Option<String>,
    /// Human-readable tool number.
    pub tool_number: String,
    /// Description.
    pub description: Option<String>,
    /// Total quantity.
    pub quantity: i32,
    /// Available quantity.
    pub quantity_available: i32,
    /// Status (available, in_use, calibration, maintenance, retired).
    pub status: String,
    /// Storage location.
    pub location: Option<String>,
    /// Tool type.
    pub tool_type: Option<String>,
    /// Next calibration due date.
    pub calibration_due: Option<DateTime<Utc>>,
    /// Calibration interval in days.
    pub calibration_interval: i32,
    /// Last calibration date.
    pub last_calibration: Option<DateTime<Utc>>,
    /// User who has the tool checked out.
    pub checked_out_to: Option<Uuid>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an asset warranty.
///
/// Warranties track coverage terms for assets, including vendor,
/// coverage period, and contact information.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AssetWarrantyModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Asset covered by the warranty.
    pub asset_id: Uuid,
    /// Warranty vendor.
    pub vendor: String,
    /// Warranty policy number.
    pub warranty_number: Option<String>,
    /// Coverage start date.
    pub start_date: DateTime<Utc>,
    /// Coverage end date.
    pub end_date: DateTime<Utc>,
    /// Warranty terms and conditions.
    pub terms: Option<String>,
    /// Type of coverage.
    pub coverage_type: Option<String>,
    /// Vendor contact information.
    pub contact_info: Option<String>,
    /// Whether the warranty is currently active.
    pub is_active: bool,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}
