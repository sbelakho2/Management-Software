//! Production and manufacturing models for routings, stations, and work order operations.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database representation of a manufacturing routing step.
///
/// Routings define the sequence of operations required to manufacture
/// a product, including standard times and work center assignments.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct RoutingModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Product being routed.
    pub product_id: Uuid,
    /// Sequence number within the routing.
    pub sequence: i32,
    /// Work center where the operation is performed.
    pub work_center_id: Uuid,
    /// Operation description.
    pub operation: String,
    /// Operation code (short identifier).
    pub operation_code: Option<String>,
    /// Standard cycle time (minutes).
    pub standard_time: f64,
    /// Setup time (minutes).
    pub setup_time: f64,
    /// Move time between operations (minutes).
    pub move_time: f64,
    /// Queue time before operation (minutes).
    pub queue_time: f64,
    /// Description.
    pub description: Option<String>,
    /// Whether this routing step is active.
    pub is_active: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a workstation.
///
/// Stations are individual work positions within a work center
/// where specific manufacturing operations are performed.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct StationModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent work center.
    pub work_center_id: Uuid,
    /// Station name.
    pub name: String,
    /// Station number/code.
    pub station_number: String,
    /// Station type (manual, cnc, robotic, assembly, inspection, packaging).
    pub station_type: String,
    /// Status (active, inactive, maintenance, retired).
    pub status: String,
    /// Description.
    pub description: Option<String>,
    /// Associated equipment.
    pub equipment_id: Option<Uuid>,
    /// Capacity per shift.
    pub capacity: Option<f64>,
    /// Efficiency factor (0.0 - 1.0).
    pub efficiency: Option<f64>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a work order operation.
///
/// Operations track the progress of individual routing steps
/// within a work order, including actual times and operator assignments.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct WorkOrderOperationModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent work order.
    pub work_order_id: Uuid,
    /// Sequence number.
    pub sequence: i32,
    /// Station where the operation is performed.
    pub station_id: Uuid,
    /// Operation description.
    pub operation: String,
    /// Status (pending, in_progress, completed, skipped, on_hold).
    pub status: String,
    /// Standard time (minutes).
    pub standard_time: f64,
    /// Actual time taken (minutes).
    pub actual_time: Option<f64>,
    /// Setup time (minutes).
    pub setup_time: f64,
    /// Actual setup time (minutes).
    pub actual_setup_time: Option<f64>,
    /// Timestamp when operation started.
    pub started_at: Option<DateTime<Utc>>,
    /// Timestamp when operation completed.
    pub completed_at: Option<DateTime<Utc>>,
    /// Operator user ID.
    pub operator_id: Option<Uuid>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a production cell.
///
/// Production cells group work centers into manufacturing cells
/// following lean manufacturing principles.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ProductionCellModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Cell name.
    pub name: String,
    /// Cell number/code.
    pub cell_number: String,
    /// Cell type (manufacturing, assembly, painting, welding, inspection, packaging).
    pub cell_type: String,
    /// Status (active, inactive, reconfiguring).
    pub status: String,
    /// Description.
    pub description: Option<String>,
    /// Physical location.
    pub location: Option<String>,
    /// Supervisor user ID.
    pub supervisor_id: Option<Uuid>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a production cell to work center mapping.
///
/// Junction table linking production cells to their constituent work centers.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ProductionCellWorkCenterModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Production cell.
    pub cell_id: Uuid,
    /// Work center within the cell.
    pub work_center_id: Uuid,
    /// Sequence within the cell flow.
    pub sequence: i32,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
}
