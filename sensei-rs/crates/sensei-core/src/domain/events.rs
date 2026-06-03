//! Domain event traits and types.
//!
//! Domain events represent state-changing occurrences within the system.
//! They are published to the event bus and can trigger side effects such as
//! notifications, integrations, or state transitions.

use crate::types::{CorrelationId, EventId, Timestamp, new_correlation_id, now};
use serde::{Deserialize, Serialize};
use std::any::Any;
use uuid::Uuid;

/// Core trait for all domain events.
///
/// All domain events must implement this trait, providing metadata about
/// the event such as its unique ID, type name, correlation ID for tracing,
/// and the tenant it belongs to.
pub trait DomainEvent: Send + Sync + std::fmt::Debug {
    /// Returns the unique identifier for this event instance.
    fn event_id(&self) -> EventId;

    /// Returns the type name of this event (e.g., "quality.ncr.created").
    fn event_type(&self) -> &'static str;

    /// Returns the correlation ID for tracing this event across services.
    fn correlation_id(&self) -> CorrelationId;

    /// Returns the tenant ID this event belongs to.
    fn tenant_id(&self) -> Uuid;

    /// Returns the timestamp when this event occurred.
    fn occurred_at(&self) -> Timestamp;

    /// Returns the event payload as a [`serde_json::Value`].
    fn payload(&self) -> Result<serde_json::Value, serde_json::Error>;

    /// Attempt to downcast this event to a concrete type.
    fn as_any(&self) -> &dyn Any;
}

/// Metadata common to all domain events.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventMetadata {
    /// Unique event identifier.
    pub event_id: EventId,
    /// Event type name (dot-notation).
    pub event_type: String,
    /// Correlation ID for distributed tracing.
    pub correlation_id: CorrelationId,
    /// Tenant that originated this event.
    pub tenant_id: Uuid,
    /// When the event occurred.
    pub occurred_at: Timestamp,
    /// Version of the event schema.
    pub version: u32,
}

impl EventMetadata {
    /// Create new [`EventMetadata`] for the given event type and tenant.
    pub fn new(event_type: impl Into<String>, tenant_id: Uuid) -> Self {
        Self {
            event_id: Uuid::new_v4(),
            event_type: event_type.into(),
            correlation_id: new_correlation_id(),
            tenant_id,
            occurred_at: now(),
            version: 1,
        }
    }
}

// ── Concrete Domain Events ─────────────────────────────────────────────

// =========================================================================
// Identity Domain Events
// =========================================================================

/// Event emitted when a user account is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The user's unique identifier.
    pub user_id: Uuid,
    /// The user's email address.
    pub email: String,
    /// The user's display name.
    pub name: String,
}

impl UserCreatedEvent {
    /// Create a new [`UserCreatedEvent`].
    pub fn new(tenant_id: Uuid, user_id: Uuid, email: String, name: String) -> Self {
        Self {
            metadata: EventMetadata::new("identity.user.created", tenant_id),
            user_id,
            email,
            name,
        }
    }
}

impl DomainEvent for UserCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "identity.user.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// Quality Domain Events
// =========================================================================

/// Event emitted when a non-conformance report (NCR) is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NcrCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The NCR's unique identifier.
    pub ncr_id: Uuid,
    /// The NCR number (human-readable).
    pub ncr_number: String,
    /// Title of the NCR.
    pub title: String,
    /// Severity level.
    pub severity: String,
    /// ID of the user who reported it.
    pub reported_by: Uuid,
}

impl NcrCreatedEvent {
    /// Create a new [`NcrCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        ncr_id: Uuid,
        ncr_number: String,
        title: String,
        severity: String,
        reported_by: Uuid,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("quality.ncr.created", tenant_id),
            ncr_id,
            ncr_number,
            title,
            severity,
            reported_by,
        }
    }
}

impl DomainEvent for NcrCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "quality.ncr.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a Corrective/Preventive Action (CAPA) is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CAPACreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The CAPA's unique identifier.
    pub capa_id: Uuid,
    /// Optional NCR ID that triggered this CAPA.
    pub nc_id: Option<Uuid>,
    /// Priority level.
    pub priority: String,
    /// Whether this CAPA was auto-created.
    pub auto_created: bool,
    /// Reason for creation.
    pub creation_reason: String,
}

impl CAPACreatedEvent {
    /// Create a new [`CAPACreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        capa_id: Uuid,
        nc_id: Option<Uuid>,
        priority: String,
        auto_created: bool,
        creation_reason: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("quality.capa.created", tenant_id),
            capa_id,
            nc_id,
            priority,
            auto_created,
            creation_reason,
        }
    }
}

impl DomainEvent for CAPACreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "quality.capa.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a CAPA is closed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CAPAClosedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The CAPA's unique identifier.
    pub capa_id: Uuid,
    /// Outcome of the CAPA closure.
    pub outcome: String,
    /// ID of the user who closed the CAPA.
    pub closed_by: Uuid,
}

impl CAPAClosedEvent {
    /// Create a new [`CAPAClosedEvent`].
    pub fn new(tenant_id: Uuid, capa_id: Uuid, outcome: String, closed_by: Uuid) -> Self {
        Self {
            metadata: EventMetadata::new("quality.capa.closed", tenant_id),
            capa_id,
            outcome,
            closed_by,
        }
    }
}

impl DomainEvent for CAPAClosedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "quality.capa.closed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an inspection is completed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InspectionCompletedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The inspection's unique identifier.
    pub inspection_id: Uuid,
    /// Result of the inspection (pass / fail / conditional).
    pub result: String,
    /// Optional product ID that was inspected.
    pub product_id: Option<Uuid>,
    /// ID of the inspector.
    pub inspector_id: Uuid,
}

impl InspectionCompletedEvent {
    /// Create a new [`InspectionCompletedEvent`].
    pub fn new(
        tenant_id: Uuid,
        inspection_id: Uuid,
        result: String,
        product_id: Option<Uuid>,
        inspector_id: Uuid,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("quality.inspection.completed", tenant_id),
            inspection_id,
            result,
            product_id,
            inspector_id,
        }
    }
}

impl DomainEvent for InspectionCompletedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "quality.inspection.completed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an audit finding is recorded.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditFindingEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The finding's unique identifier.
    pub finding_id: Uuid,
    /// The audit's unique identifier.
    pub audit_id: Uuid,
    /// Severity level of the finding.
    pub severity: String,
    /// Area audited.
    pub area: String,
}

impl AuditFindingEvent {
    /// Create a new [`AuditFindingEvent`].
    pub fn new(
        tenant_id: Uuid,
        finding_id: Uuid,
        audit_id: Uuid,
        severity: String,
        area: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("quality.audit.finding", tenant_id),
            finding_id,
            audit_id,
            severity,
            area,
        }
    }
}

impl DomainEvent for AuditFindingEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "quality.audit.finding"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a supplier is evaluated or scored.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupplierEvaluatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The supplier's unique identifier.
    pub supplier_id: Uuid,
    /// Evaluation score.
    pub score: f64,
    /// Assigned tier.
    pub tier: String,
}

impl SupplierEvaluatedEvent {
    /// Create a new [`SupplierEvaluatedEvent`].
    pub fn new(tenant_id: Uuid, supplier_id: Uuid, score: f64, tier: String) -> Self {
        Self {
            metadata: EventMetadata::new("quality.supplier.evaluated", tenant_id),
            supplier_id,
            score,
            tier,
        }
    }
}

impl DomainEvent for SupplierEvaluatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "quality.supplier.evaluated"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// Production Domain Events
// =========================================================================

/// Event emitted when a work order status changes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkOrderStatusChangedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The work order's unique identifier.
    pub work_order_id: Uuid,
    /// Work order number (human-readable).
    pub wo_number: String,
    /// Previous status.
    pub previous_status: String,
    /// New status.
    pub new_status: String,
    /// ID of the user who made the change.
    pub changed_by: Uuid,
}

impl WorkOrderStatusChangedEvent {
    /// Create a new [`WorkOrderStatusChangedEvent`].
    pub fn new(
        tenant_id: Uuid,
        work_order_id: Uuid,
        wo_number: String,
        previous_status: String,
        new_status: String,
        changed_by: Uuid,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("production.work-order.status-changed", tenant_id),
            work_order_id,
            wo_number,
            previous_status,
            new_status,
            changed_by,
        }
    }
}

impl DomainEvent for WorkOrderStatusChangedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "production.work-order.status-changed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a maintenance work order is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkOrderCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The work order's unique identifier.
    pub work_order_id: Uuid,
    /// The asset's unique identifier.
    pub asset_id: Uuid,
    /// Priority level.
    pub priority: String,
    /// Type of work (corrective / preventive / predictive).
    pub work_type: String,
}

impl WorkOrderCreatedEvent {
    /// Create a new [`WorkOrderCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        work_order_id: Uuid,
        asset_id: Uuid,
        priority: String,
        work_type: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("production.work-order.created", tenant_id),
            work_order_id,
            asset_id,
            priority,
            work_type,
        }
    }
}

impl DomainEvent for WorkOrderCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "production.work-order.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a production order starts on the shop floor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductionOrderStartedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The production order's unique identifier.
    pub order_id: Uuid,
    /// The product's unique identifier.
    pub product_id: Uuid,
    /// Quantity to produce.
    pub quantity: i64,
    /// Production line identifier.
    pub line_id: String,
}

impl ProductionOrderStartedEvent {
    /// Create a new [`ProductionOrderStartedEvent`].
    pub fn new(
        tenant_id: Uuid,
        order_id: Uuid,
        product_id: Uuid,
        quantity: i64,
        line_id: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("production.order.started", tenant_id),
            order_id,
            product_id,
            quantity,
            line_id,
        }
    }
}

impl DomainEvent for ProductionOrderStartedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "production.order.started"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a production order is completed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductionOrderCompletedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The production order's unique identifier.
    pub order_id: Uuid,
    /// The product's unique identifier.
    pub product_id: Uuid,
    /// Quantity successfully produced.
    pub quantity_produced: i64,
    /// Quantity scrapped during production.
    pub scrap_quantity: i64,
}

impl ProductionOrderCompletedEvent {
    /// Create a new [`ProductionOrderCompletedEvent`].
    pub fn new(
        tenant_id: Uuid,
        order_id: Uuid,
        product_id: Uuid,
        quantity_produced: i64,
        scrap_quantity: i64,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("production.order.completed", tenant_id),
            order_id,
            product_id,
            quantity_produced,
            scrap_quantity,
        }
    }
}

impl DomainEvent for ProductionOrderCompletedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "production.order.completed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an MRP explosion run completes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MRPRunCompleted {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The MRP run's unique identifier.
    pub run_id: Uuid,
    /// Number of planned orders generated.
    pub planned_orders: i64,
    /// Number of material shortages found.
    pub shortage_count: i64,
}

impl MRPRunCompleted {
    /// Create a new [`MRPRunCompleted`].
    pub fn new(tenant_id: Uuid, run_id: Uuid, planned_orders: i64, shortage_count: i64) -> Self {
        Self {
            metadata: EventMetadata::new("production.mrp.completed", tenant_id),
            run_id,
            planned_orders,
            shortage_count,
        }
    }
}

impl DomainEvent for MRPRunCompleted {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "production.mrp.completed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when equipment downtime is recorded.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DowntimeRecordedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The asset's unique identifier.
    pub asset_id: Uuid,
    /// Duration of downtime in minutes.
    pub duration_minutes: f64,
    /// Cause of the downtime.
    pub cause: String,
    /// Impact description.
    pub impact: String,
}

impl DowntimeRecordedEvent {
    /// Create a new [`DowntimeRecordedEvent`].
    pub fn new(
        tenant_id: Uuid,
        asset_id: Uuid,
        duration_minutes: f64,
        cause: String,
        impact: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("production.downtime.recorded", tenant_id),
            asset_id,
            duration_minutes,
            cause,
            impact,
        }
    }
}

impl DomainEvent for DowntimeRecordedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "production.downtime.recorded"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a preventive maintenance schedule triggers a work order.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PMScheduleTriggeredEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The PM schedule's unique identifier.
    pub schedule_id: Uuid,
    /// The asset's unique identifier.
    pub asset_id: Uuid,
    /// Next due date for maintenance.
    pub next_due: String,
}

impl PMScheduleTriggeredEvent {
    /// Create a new [`PMScheduleTriggeredEvent`].
    pub fn new(
        tenant_id: Uuid,
        schedule_id: Uuid,
        asset_id: Uuid,
        next_due: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("production.pm.triggered", tenant_id),
            schedule_id,
            asset_id,
            next_due,
        }
    }
}

impl DomainEvent for PMScheduleTriggeredEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "production.pm.triggered"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// Finance Domain Events
// =========================================================================

/// Event emitted when a cost roll-up computation finishes for a product.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostRollupCompleted {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The product's unique identifier.
    pub product_id: Uuid,
    /// Computed total cost.
    pub total_cost: f64,
    /// Currency code.
    pub currency: String,
}

impl CostRollupCompleted {
    /// Create a new [`CostRollupCompleted`].
    pub fn new(tenant_id: Uuid, product_id: Uuid, total_cost: f64, currency: String) -> Self {
        Self {
            metadata: EventMetadata::new("finance.cost-rollup.completed", tenant_id),
            product_id,
            total_cost,
            currency,
        }
    }
}

impl DomainEvent for CostRollupCompleted {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "finance.cost-rollup.completed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a journal entry is posted to the ledger.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JournalEntryPosted {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The journal entry's unique identifier.
    pub entry_id: Uuid,
    /// Total debits.
    pub debit_total: f64,
    /// Total credits.
    pub credit_total: f64,
    /// Accounting period.
    pub period: String,
}

impl JournalEntryPosted {
    /// Create a new [`JournalEntryPosted`].
    pub fn new(
        tenant_id: Uuid,
        entry_id: Uuid,
        debit_total: f64,
        credit_total: f64,
        period: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("finance.journal.posted", tenant_id),
            entry_id,
            debit_total,
            credit_total,
            period,
        }
    }
}

impl DomainEvent for JournalEntryPosted {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "finance.journal.posted"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an invoice is created (AP or AR).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvoiceCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The invoice's unique identifier.
    pub invoice_id: Uuid,
    /// Type of invoice (payable / receivable).
    pub invoice_type: String,
    /// Invoice amount.
    pub amount: f64,
    /// Currency code.
    pub currency: String,
    /// Counterparty name or identifier.
    pub counterparty: String,
}

impl InvoiceCreatedEvent {
    /// Create a new [`InvoiceCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        invoice_id: Uuid,
        invoice_type: String,
        amount: f64,
        currency: String,
        counterparty: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("finance.invoice.created", tenant_id),
            invoice_id,
            invoice_type,
            amount,
            currency,
            counterparty,
        }
    }
}

impl DomainEvent for InvoiceCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "finance.invoice.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a payment is processed (AR or AP).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaymentProcessedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The payment's unique identifier.
    pub payment_id: Uuid,
    /// Type of payment (received / issued).
    pub payment_type: String,
    /// Payment amount.
    pub amount: f64,
    /// Currency code.
    pub currency: String,
    /// Counterparty unique identifier.
    pub counterparty_id: Uuid,
}

impl PaymentProcessedEvent {
    /// Create a new [`PaymentProcessedEvent`].
    pub fn new(
        tenant_id: Uuid,
        payment_id: Uuid,
        payment_type: String,
        amount: f64,
        currency: String,
        counterparty_id: Uuid,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("finance.payment.processed", tenant_id),
            payment_id,
            payment_type,
            amount,
            currency,
            counterparty_id,
        }
    }
}

impl DomainEvent for PaymentProcessedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "finance.payment.processed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// HR Domain Events
// =========================================================================

/// Event emitted when an employee completes a training course.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingCompletedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The employee's unique identifier.
    pub employee_id: Uuid,
    /// The training's unique identifier.
    pub training_id: Uuid,
    /// The skill's identifier.
    pub skill_id: String,
    /// Optional test score.
    pub score: Option<f64>,
    /// Whether the employee passed.
    pub passed: bool,
}

impl TrainingCompletedEvent {
    /// Create a new [`TrainingCompletedEvent`].
    pub fn new(
        tenant_id: Uuid,
        employee_id: Uuid,
        training_id: Uuid,
        skill_id: String,
        score: Option<f64>,
        passed: bool,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("hr.training.completed", tenant_id),
            employee_id,
            training_id,
            skill_id,
            score,
            passed,
        }
    }
}

impl DomainEvent for TrainingCompletedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "hr.training.completed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an employee's certification expires or is about to expire.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CertificationExpiredEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The employee's unique identifier.
    pub employee_id: Uuid,
    /// The certification's unique identifier.
    pub certification_id: Uuid,
    /// Expiration date.
    pub expired_at: String,
    /// Name of the certified skill.
    pub skill_name: String,
}

impl CertificationExpiredEvent {
    /// Create a new [`CertificationExpiredEvent`].
    pub fn new(
        tenant_id: Uuid,
        employee_id: Uuid,
        certification_id: Uuid,
        expired_at: String,
        skill_name: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("hr.certification.expired", tenant_id),
            employee_id,
            certification_id,
            expired_at,
            skill_name,
        }
    }
}

impl DomainEvent for CertificationExpiredEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "hr.certification.expired"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a new employee completes onboarding.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmployeeOnboardedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The employee's unique identifier.
    pub employee_id: Uuid,
    /// Department assigned.
    pub department: String,
    /// Job position.
    pub position: String,
}

impl EmployeeOnboardedEvent {
    /// Create a new [`EmployeeOnboardedEvent`].
    pub fn new(tenant_id: Uuid, employee_id: Uuid, department: String, position: String) -> Self {
        Self {
            metadata: EventMetadata::new("hr.employee.onboarded", tenant_id),
            employee_id,
            department,
            position,
        }
    }
}

impl DomainEvent for EmployeeOnboardedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "hr.employee.onboarded"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a leave request is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LeaveRequestCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The leave request's unique identifier.
    pub leave_request_id: Uuid,
    /// The employee's unique identifier.
    pub employee_id: Uuid,
    /// Type of leave.
    pub leave_type: String,
    /// Start date.
    pub start_date: String,
    /// End date.
    pub end_date: String,
}

impl LeaveRequestCreatedEvent {
    /// Create a new [`LeaveRequestCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        leave_request_id: Uuid,
        employee_id: Uuid,
        leave_type: String,
        start_date: String,
        end_date: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("hr.leave.created", tenant_id),
            leave_request_id,
            employee_id,
            leave_type,
            start_date,
            end_date,
        }
    }
}

impl DomainEvent for LeaveRequestCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "hr.leave.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a leave request is approved.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LeaveRequestApprovedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The leave request's unique identifier.
    pub leave_request_id: Uuid,
    /// The employee's unique identifier.
    pub employee_id: Uuid,
    /// ID of the user who approved.
    pub approved_by_id: Uuid,
}

impl LeaveRequestApprovedEvent {
    /// Create a new [`LeaveRequestApprovedEvent`].
    pub fn new(
        tenant_id: Uuid,
        leave_request_id: Uuid,
        employee_id: Uuid,
        approved_by_id: Uuid,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("hr.leave.approved", tenant_id),
            leave_request_id,
            employee_id,
            approved_by_id,
        }
    }
}

impl DomainEvent for LeaveRequestApprovedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "hr.leave.approved"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a performance review is completed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceReviewCompletedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The performance review's unique identifier.
    pub performance_review_id: Uuid,
    /// The employee's unique identifier.
    pub employee_id: Uuid,
    /// ID of the reviewer.
    pub reviewer_id: Uuid,
    /// Rating given.
    pub rating: String,
}

impl PerformanceReviewCompletedEvent {
    /// Create a new [`PerformanceReviewCompletedEvent`].
    pub fn new(
        tenant_id: Uuid,
        performance_review_id: Uuid,
        employee_id: Uuid,
        reviewer_id: Uuid,
        rating: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("hr.performance.completed", tenant_id),
            performance_review_id,
            employee_id,
            reviewer_id,
            rating,
        }
    }
}

impl DomainEvent for PerformanceReviewCompletedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "hr.performance.completed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a timecard / time clock event is submitted.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimecardSubmittedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The timecard's unique identifier.
    pub timecard_id: Uuid,
    /// The employee's unique identifier.
    pub employee_id: Uuid,
    /// Type of event (clock_in, clock_out, break_start, break_end).
    pub event_type: String,
    /// Timestamp of the event.
    pub event_time: String,
}

impl TimecardSubmittedEvent {
    /// Create a new [`TimecardSubmittedEvent`].
    pub fn new(
        tenant_id: Uuid,
        timecard_id: Uuid,
        employee_id: Uuid,
        event_type: String,
        event_time: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("hr.timecard.submitted", tenant_id),
            timecard_id,
            employee_id,
            event_type,
            event_time,
        }
    }
}

impl DomainEvent for TimecardSubmittedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "hr.timecard.submitted"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// Supply Chain Domain Events
// =========================================================================

/// Event emitted when a Request for Quote (RFQ) is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RFQCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The RFQ's unique identifier.
    pub rfq_id: Uuid,
    /// The RFQ number (human-readable).
    pub rfq_number: String,
    /// The account's unique identifier.
    pub account_id: Uuid,
    /// Priority level.
    pub priority: String,
    /// Source of the RFQ.
    pub source: String,
}

impl RFQCreatedEvent {
    /// Create a new [`RFQCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        rfq_id: Uuid,
        rfq_number: String,
        account_id: Uuid,
        priority: String,
        source: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("supply-chain.rfq.created", tenant_id),
            rfq_id,
            rfq_number,
            account_id,
            priority,
            source,
        }
    }
}

impl DomainEvent for RFQCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "supply-chain.rfq.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an RFQ's status changes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RFQStatusChangedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The RFQ's unique identifier.
    pub rfq_id: Uuid,
    /// Previous status.
    pub old_status: String,
    /// New status.
    pub new_status: String,
}

impl RFQStatusChangedEvent {
    /// Create a new [`RFQStatusChangedEvent`].
    pub fn new(
        tenant_id: Uuid,
        rfq_id: Uuid,
        old_status: String,
        new_status: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("supply-chain.rfq.status-changed", tenant_id),
            rfq_id,
            old_status,
            new_status,
        }
    }
}

impl DomainEvent for RFQStatusChangedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "supply-chain.rfq.status-changed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a Quote is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The quote's unique identifier.
    pub quote_id: Uuid,
    /// The quote number (human-readable).
    pub quote_number: String,
    /// The RFQ's unique identifier.
    pub rfq_id: Uuid,
    /// Total amount.
    pub total_amount: f64,
    /// Currency code.
    pub currency: String,
}

impl QuoteCreatedEvent {
    /// Create a new [`QuoteCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        quote_id: Uuid,
        quote_number: String,
        rfq_id: Uuid,
        total_amount: f64,
        currency: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("supply-chain.quote.created", tenant_id),
            quote_id,
            quote_number,
            rfq_id,
            total_amount,
            currency,
        }
    }
}

impl DomainEvent for QuoteCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "supply-chain.quote.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a Quote is approved.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteApprovedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The quote's unique identifier.
    pub quote_id: Uuid,
    /// ID of the user who approved.
    pub approved_by_id: Uuid,
    /// Total amount approved.
    pub total_amount: f64,
}

impl QuoteApprovedEvent {
    /// Create a new [`QuoteApprovedEvent`].
    pub fn new(
        tenant_id: Uuid,
        quote_id: Uuid,
        approved_by_id: Uuid,
        total_amount: f64,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("supply-chain.quote.approved", tenant_id),
            quote_id,
            approved_by_id,
            total_amount,
        }
    }
}

impl DomainEvent for QuoteApprovedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "supply-chain.quote.approved"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a Quote is converted to a Sales Order.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteConvertedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The quote's unique identifier.
    pub quote_id: Uuid,
    /// The sales order's unique identifier.
    pub sales_order_id: Uuid,
}

impl QuoteConvertedEvent {
    /// Create a new [`QuoteConvertedEvent`].
    pub fn new(tenant_id: Uuid, quote_id: Uuid, sales_order_id: Uuid) -> Self {
        Self {
            metadata: EventMetadata::new("supply-chain.quote.converted", tenant_id),
            quote_id,
            sales_order_id,
        }
    }
}

impl DomainEvent for QuoteConvertedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "supply-chain.quote.converted"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a Sales Order is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SalesOrderCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The sales order's unique identifier.
    pub sales_order_id: Uuid,
    /// The sales order number (human-readable).
    pub so_number: String,
    /// The account's unique identifier.
    pub account_id: Uuid,
    /// Total amount.
    pub total_amount: f64,
    /// Currency code.
    pub currency: String,
}

impl SalesOrderCreatedEvent {
    /// Create a new [`SalesOrderCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        sales_order_id: Uuid,
        so_number: String,
        account_id: Uuid,
        total_amount: f64,
        currency: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("supply-chain.sales-order.created", tenant_id),
            sales_order_id,
            so_number,
            account_id,
            total_amount,
            currency,
        }
    }
}

impl DomainEvent for SalesOrderCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "supply-chain.sales-order.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a Purchase Order is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PurchaseOrderCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The purchase order's unique identifier.
    pub purchase_order_id: Uuid,
    /// The purchase order number (human-readable).
    pub po_number: String,
    /// The supplier's unique identifier.
    pub supplier_id: Uuid,
    /// Total amount.
    pub total_amount: f64,
    /// Currency code.
    pub currency: String,
}

impl PurchaseOrderCreatedEvent {
    /// Create a new [`PurchaseOrderCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        purchase_order_id: Uuid,
        po_number: String,
        supplier_id: Uuid,
        total_amount: f64,
        currency: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("supply-chain.purchase-order.created", tenant_id),
            purchase_order_id,
            po_number,
            supplier_id,
            total_amount,
            currency,
        }
    }
}

impl DomainEvent for PurchaseOrderCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "supply-chain.purchase-order.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an inventory stock move is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StockMoveCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The stock move's unique identifier.
    pub stock_move_id: Uuid,
    /// The product's unique identifier.
    pub product_id: Uuid,
    /// Quantity moved.
    pub quantity: f64,
    /// Source location unique identifier.
    pub from_location_id: Uuid,
    /// Destination location unique identifier.
    pub to_location_id: Uuid,
    /// Type of move (receipt, issue, transfer).
    pub move_type: String,
}

impl StockMoveCreatedEvent {
    /// Create a new [`StockMoveCreatedEvent`].
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        tenant_id: Uuid,
        stock_move_id: Uuid,
        product_id: Uuid,
        quantity: f64,
        from_location_id: Uuid,
        to_location_id: Uuid,
        move_type: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("supply-chain.stock-move.created", tenant_id),
            stock_move_id,
            product_id,
            quantity,
            from_location_id,
            to_location_id,
            move_type,
        }
    }
}

impl DomainEvent for StockMoveCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "supply-chain.stock-move.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when goods are received into inventory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GoodsReceiptCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The goods receipt's unique identifier.
    pub goods_receipt_id: Uuid,
    /// The purchase order's unique identifier.
    pub purchase_order_id: Uuid,
    /// Quantity received.
    pub quantity: f64,
}

impl GoodsReceiptCreatedEvent {
    /// Create a new [`GoodsReceiptCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        goods_receipt_id: Uuid,
        purchase_order_id: Uuid,
        quantity: f64,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("supply-chain.goods-receipt.created", tenant_id),
            goods_receipt_id,
            purchase_order_id,
            quantity,
        }
    }
}

impl DomainEvent for GoodsReceiptCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "supply-chain.goods-receipt.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// Operations Domain Events
// =========================================================================

/// Event emitted when an Andon signal is triggered.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AndonCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The Andon event's unique identifier.
    pub andon_event_id: Uuid,
    /// Type of Andon (safety, quality, production, maintenance).
    pub andon_type: String,
    /// Optional work order ID.
    pub work_order_id: Option<Uuid>,
    /// Optional station ID.
    pub station_id: Option<Uuid>,
    /// Severity level.
    pub severity: String,
}

impl AndonCreatedEvent {
    /// Create a new [`AndonCreatedEvent`].
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        tenant_id: Uuid,
        andon_event_id: Uuid,
        andon_type: String,
        work_order_id: Option<Uuid>,
        station_id: Option<Uuid>,
        severity: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.andon.created", tenant_id),
            andon_event_id,
            andon_type,
            work_order_id,
            station_id,
            severity,
        }
    }
}

impl DomainEvent for AndonCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.andon.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an Andon signal is acknowledged.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AndonAcknowledgedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The Andon event's unique identifier.
    pub andon_event_id: Uuid,
    /// ID of the user who acknowledged.
    pub acknowledged_by_id: Uuid,
}

impl AndonAcknowledgedEvent {
    /// Create a new [`AndonAcknowledgedEvent`].
    pub fn new(tenant_id: Uuid, andon_event_id: Uuid, acknowledged_by_id: Uuid) -> Self {
        Self {
            metadata: EventMetadata::new("operations.andon.acknowledged", tenant_id),
            andon_event_id,
            acknowledged_by_id,
        }
    }
}

impl DomainEvent for AndonAcknowledgedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.andon.acknowledged"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an Andon signal is resolved.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AndonResolvedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The Andon event's unique identifier.
    pub andon_event_id: Uuid,
    /// ID of the user who resolved.
    pub resolved_by_id: Uuid,
    /// Description of the resolution.
    pub resolution: String,
    /// Downtime in minutes.
    pub downtime_minutes: f64,
}

impl AndonResolvedEvent {
    /// Create a new [`AndonResolvedEvent`].
    pub fn new(
        tenant_id: Uuid,
        andon_event_id: Uuid,
        resolved_by_id: Uuid,
        resolution: String,
        downtime_minutes: f64,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.andon.resolved", tenant_id),
            andon_event_id,
            resolved_by_id,
            resolution,
            downtime_minutes,
        }
    }
}

impl DomainEvent for AndonResolvedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.andon.resolved"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a Kanban card is moved between columns.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanCardMovedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The card's unique identifier.
    pub card_id: Uuid,
    /// The board's unique identifier.
    pub board_id: Uuid,
    /// Source column name.
    pub from_column: String,
    /// Destination column name.
    pub to_column: String,
}

impl KanbanCardMovedEvent {
    /// Create a new [`KanbanCardMovedEvent`].
    pub fn new(
        tenant_id: Uuid,
        card_id: Uuid,
        board_id: Uuid,
        from_column: String,
        to_column: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.kanban.moved", tenant_id),
            card_id,
            board_id,
            from_column,
            to_column,
        }
    }
}

impl DomainEvent for KanbanCardMovedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.kanban.moved"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a project is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The project's unique identifier.
    pub project_id: Uuid,
    /// The project name.
    pub project_name: String,
    /// The project type.
    pub project_type: String,
}

impl ProjectCreatedEvent {
    /// Create a new [`ProjectCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        project_id: Uuid,
        project_name: String,
        project_type: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.project.created", tenant_id),
            project_id,
            project_name,
            project_type,
        }
    }
}

impl DomainEvent for ProjectCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.project.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a sprint is completed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SprintCompletedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The sprint's unique identifier.
    pub sprint_id: Uuid,
    /// The project's unique identifier.
    pub project_id: Uuid,
    /// Number of stories completed.
    pub stories_completed: i64,
    /// Velocity achieved.
    pub velocity: f64,
}

impl SprintCompletedEvent {
    /// Create a new [`SprintCompletedEvent`].
    pub fn new(
        tenant_id: Uuid,
        sprint_id: Uuid,
        project_id: Uuid,
        stories_completed: i64,
        velocity: f64,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.sprint.completed", tenant_id),
            sprint_id,
            project_id,
            stories_completed,
            velocity,
        }
    }
}

impl DomainEvent for SprintCompletedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.sprint.completed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a project issue is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IssueCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The issue's unique identifier.
    pub issue_id: Uuid,
    /// The project's unique identifier.
    pub project_id: Uuid,
    /// Type of issue.
    pub issue_type: String,
    /// Severity level.
    pub severity: String,
}

impl IssueCreatedEvent {
    /// Create a new [`IssueCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        issue_id: Uuid,
        project_id: Uuid,
        issue_type: String,
        severity: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.issue.created", tenant_id),
            issue_id,
            project_id,
            issue_type,
            severity,
        }
    }
}

impl DomainEvent for IssueCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.issue.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an A3 problem-solving report is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A3CreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The A3's unique identifier.
    pub a3_id: Uuid,
    /// Type of A3 report.
    pub a3_type: String,
    /// Title of the A3.
    pub title: String,
    /// Priority level.
    pub priority: String,
}

impl A3CreatedEvent {
    /// Create a new [`A3CreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        a3_id: Uuid,
        a3_type: String,
        title: String,
        priority: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.a3.created", tenant_id),
            a3_id,
            a3_type,
            title,
            priority,
        }
    }
}

impl DomainEvent for A3CreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.a3.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an A3 report is closed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A3ClosedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The A3's unique identifier.
    pub a3_id: Uuid,
    /// Outcome (effective, ineffective, inconclusive).
    pub outcome: String,
}

impl A3ClosedEvent {
    /// Create a new [`A3ClosedEvent`].
    pub fn new(tenant_id: Uuid, a3_id: Uuid, outcome: String) -> Self {
        Self {
            metadata: EventMetadata::new("operations.a3.closed", tenant_id),
            a3_id,
            outcome,
        }
    }
}

impl DomainEvent for A3ClosedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.a3.closed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a risk is identified and recorded.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The risk's unique identifier.
    pub risk_id: Uuid,
    /// Risk category.
    pub risk_category: String,
    /// Severity level.
    pub severity: String,
    /// Likelihood.
    pub likelihood: String,
    /// Type of entity the risk is associated with.
    pub entity_type: String,
    /// ID of the entity the risk is associated with.
    pub entity_id: Uuid,
}

impl RiskCreatedEvent {
    /// Create a new [`RiskCreatedEvent`].
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        tenant_id: Uuid,
        risk_id: Uuid,
        risk_category: String,
        severity: String,
        likelihood: String,
        entity_type: String,
        entity_id: Uuid,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.risk.created", tenant_id),
            risk_id,
            risk_category,
            severity,
            likelihood,
            entity_type,
            entity_id,
        }
    }
}

impl DomainEvent for RiskCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.risk.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a risk mitigation is completed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskMitigatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The risk's unique identifier.
    pub risk_id: Uuid,
    /// The mitigation's unique identifier.
    pub mitigation_id: Uuid,
    /// Effectiveness of the mitigation.
    pub effectiveness: String,
}

impl RiskMitigatedEvent {
    /// Create a new [`RiskMitigatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        risk_id: Uuid,
        mitigation_id: Uuid,
        effectiveness: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.risk.mitigated", tenant_id),
            risk_id,
            mitigation_id,
            effectiveness,
        }
    }
}

impl DomainEvent for RiskMitigatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.risk.mitigated"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// AI/ML Domain Events
// =========================================================================

/// Event emitted when the AI anomaly detector finds a potential anomaly.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyDetectedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// Type of entity where anomaly was detected.
    pub entity_type: String,
    /// ID of the entity.
    pub entity_id: Uuid,
    /// Type of anomaly.
    pub anomaly_type: String,
    /// Confidence score of the detection.
    pub confidence: f64,
    /// Description of the anomaly.
    pub description: String,
}

impl AnomalyDetectedEvent {
    /// Create a new [`AnomalyDetectedEvent`].
    pub fn new(
        tenant_id: Uuid,
        entity_type: String,
        entity_id: Uuid,
        anomaly_type: String,
        confidence: f64,
        description: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("ai.anomaly.detected", tenant_id),
            entity_type,
            entity_id,
            anomaly_type,
            confidence,
            description,
        }
    }
}

impl DomainEvent for AnomalyDetectedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "ai.anomaly.detected"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an ML model is retrained.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelRetrainedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// Name of the model.
    pub model_name: String,
    /// Version string.
    pub version: String,
    /// Accuracy achieved.
    pub accuracy: f64,
    /// Size of the training dataset.
    pub dataset_size: i64,
}

impl ModelRetrainedEvent {
    /// Create a new [`ModelRetrainedEvent`].
    pub fn new(
        tenant_id: Uuid,
        model_name: String,
        version: String,
        accuracy: f64,
        dataset_size: i64,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("ai.model.retrained", tenant_id),
            model_name,
            version,
            accuracy,
            dataset_size,
        }
    }
}

impl DomainEvent for ModelRetrainedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "ai.model.retrained"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// CRM / Opportunity Domain Events
// =========================================================================

/// Event emitted when a CRM opportunity changes pipeline stage.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpportunityStageChangedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The opportunity's unique identifier.
    pub opportunity_id: Uuid,
    /// Previous pipeline stage.
    pub old_stage: String,
    /// New pipeline stage.
    pub new_stage: String,
    /// Opportunity amount.
    pub amount: f64,
}

impl OpportunityStageChangedEvent {
    /// Create a new [`OpportunityStageChangedEvent`].
    pub fn new(
        tenant_id: Uuid,
        opportunity_id: Uuid,
        old_stage: String,
        new_stage: String,
        amount: f64,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("crm.opportunity.stage-changed", tenant_id),
            opportunity_id,
            old_stage,
            new_stage,
            amount,
        }
    }
}

impl DomainEvent for OpportunityStageChangedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "crm.opportunity.stage-changed"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a job application is received.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApplicationReceivedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The application's unique identifier.
    pub application_id: Uuid,
    /// The job posting's unique identifier.
    pub job_posting_id: Uuid,
    /// Candidate's email address.
    pub candidate_email: String,
}

impl ApplicationReceivedEvent {
    /// Create a new [`ApplicationReceivedEvent`].
    pub fn new(
        tenant_id: Uuid,
        application_id: Uuid,
        job_posting_id: Uuid,
        candidate_email: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("crm.application.received", tenant_id),
            application_id,
            job_posting_id,
            candidate_email,
        }
    }
}

impl DomainEvent for ApplicationReceivedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "crm.application.received"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// Kanban Domain Events
// =========================================================================

/// Event emitted when a Kanban card is created.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanCardCreatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The card's unique identifier.
    pub card_id: Uuid,
    /// The board's unique identifier.
    pub board_id: Uuid,
    /// The column's unique identifier.
    pub column_id: Uuid,
    /// The card title.
    pub title: String,
    /// The user who created the card.
    pub created_by: Uuid,
}

impl KanbanCardCreatedEvent {
    /// Create a new [`KanbanCardCreatedEvent`].
    pub fn new(
        tenant_id: Uuid,
        card_id: Uuid,
        board_id: Uuid,
        column_id: Uuid,
        title: String,
        created_by: Uuid,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.kanban.created", tenant_id),
            card_id,
            board_id,
            column_id,
            title,
            created_by,
        }
    }
}

impl DomainEvent for KanbanCardCreatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.kanban.created"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when a Kanban card is deleted.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanCardDeletedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The card's unique identifier.
    pub card_id: Uuid,
    /// The board's unique identifier.
    pub board_id: Uuid,
    /// The column's unique identifier.
    pub column_id: Uuid,
    /// The card title at time of deletion.
    pub title: String,
}

impl KanbanCardDeletedEvent {
    /// Create a new [`KanbanCardDeletedEvent`].
    pub fn new(
        tenant_id: Uuid,
        card_id: Uuid,
        board_id: Uuid,
        column_id: Uuid,
        title: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.kanban.deleted", tenant_id),
            card_id,
            board_id,
            column_id,
            title,
        }
    }
}

impl DomainEvent for KanbanCardDeletedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.kanban.deleted"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

// =========================================================================
// Obeya Domain Events
// =========================================================================

/// Event emitted when an item is added to an Obeya board.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObeyaItemAddedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The item's unique identifier.
    pub item_id: Uuid,
    /// The board's unique identifier.
    pub board_id: Uuid,
    /// The item title.
    pub title: String,
    /// The item type.
    pub item_type: String,
    /// The user who added the item.
    pub added_by: Uuid,
}

impl ObeyaItemAddedEvent {
    /// Create a new [`ObeyaItemAddedEvent`].
    pub fn new(
        tenant_id: Uuid,
        item_id: Uuid,
        board_id: Uuid,
        title: String,
        item_type: String,
        added_by: Uuid,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.obeya.item-added", tenant_id),
            item_id,
            board_id,
            title,
            item_type,
            added_by,
        }
    }
}

impl DomainEvent for ObeyaItemAddedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.obeya.item-added"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an Obeya board item is updated.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObeyaItemUpdatedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The item's unique identifier.
    pub item_id: Uuid,
    /// The board's unique identifier.
    pub board_id: Uuid,
    /// The item title.
    pub title: String,
    /// Previous status.
    pub old_status: String,
    /// New status.
    pub new_status: String,
    /// The user who updated the item.
    pub updated_by: Uuid,
}

impl ObeyaItemUpdatedEvent {
    /// Create a new [`ObeyaItemUpdatedEvent`].
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        tenant_id: Uuid,
        item_id: Uuid,
        board_id: Uuid,
        title: String,
        old_status: String,
        new_status: String,
        updated_by: Uuid,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.obeya.item-updated", tenant_id),
            item_id,
            board_id,
            title,
            old_status,
            new_status,
            updated_by,
        }
    }
}

impl DomainEvent for ObeyaItemUpdatedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.obeya.item-updated"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

/// Event emitted when an Obeya board item is deleted.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObeyaItemDeletedEvent {
    /// Event metadata.
    pub metadata: EventMetadata,
    /// The item's unique identifier.
    pub item_id: Uuid,
    /// The board's unique identifier.
    pub board_id: Uuid,
    /// The item title at time of deletion.
    pub title: String,
}

impl ObeyaItemDeletedEvent {
    /// Create a new [`ObeyaItemDeletedEvent`].
    pub fn new(
        tenant_id: Uuid,
        item_id: Uuid,
        board_id: Uuid,
        title: String,
    ) -> Self {
        Self {
            metadata: EventMetadata::new("operations.obeya.item-deleted", tenant_id),
            item_id,
            board_id,
            title,
        }
    }
}

impl DomainEvent for ObeyaItemDeletedEvent {
    fn event_id(&self) -> EventId {
        self.metadata.event_id
    }

    fn event_type(&self) -> &'static str {
        "operations.obeya.item-deleted"
    }

    fn correlation_id(&self) -> CorrelationId {
        self.metadata.correlation_id
    }

    fn tenant_id(&self) -> Uuid {
        self.metadata.tenant_id
    }

    fn occurred_at(&self) -> Timestamp {
        self.metadata.occurred_at
    }

    fn payload(&self) -> Result<serde_json::Value, serde_json::Error> {
        serde_json::to_value(self)
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}
