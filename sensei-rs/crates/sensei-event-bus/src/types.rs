//! Event types and metadata for the event bus.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Envelope wrapping all events published to the bus.
///
/// Contains the serialized payload along with routing and metadata headers.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventEnvelope {
    /// The event type name (e.g., "quality.ncr.created").
    pub event_type: String,
    /// The event payload as raw JSON bytes.
    pub payload: serde_json::Value,
    /// Metadata headers for routing and tracing.
    pub headers: EventHeaders,
}

/// Headers attached to every event for routing, tracing, and filtering.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventHeaders {
    /// Unique event ID for deduplication.
    pub event_id: Uuid,
    /// Correlation ID for distributed tracing.
    pub correlation_id: Uuid,
    /// Tenant that originated the event.
    pub tenant_id: Uuid,
    /// User who triggered the event (if applicable).
    pub user_id: Option<Uuid>,
    /// ISO 8601 timestamp of when the event occurred.
    pub occurred_at: String,
    /// Schema version number.
    pub version: u32,
    /// Content type of the payload (default: "application/json").
    pub content_type: String,
}

impl EventHeaders {
    /// Create new [`EventHeaders`] with the given metadata.
    pub fn new(
        event_id: Uuid,
        correlation_id: Uuid,
        tenant_id: Uuid,
        user_id: Option<Uuid>,
    ) -> Self {
        Self {
            event_id,
            correlation_id,
            tenant_id,
            user_id,
            occurred_at: chrono::Utc::now().to_rfc3339(),
            version: 1,
            content_type: "application/json".to_string(),
        }
    }
}

/// Subject/topic names used for NATS event routing.
///
/// Every constant maps to a real event type defined in
/// `sensei_core::domain::events`. All subjects carry the `sensei.` prefix
/// required by the JetStream stream (`sensei.>`).
pub mod subjects {
    /// Quality domain events.
    pub mod quality {
        pub const NCR_CREATED: &str = "sensei.quality.ncr.created";
        pub const CAPA_CREATED: &str = "sensei.quality.capa.created";
        pub const CAPA_CLOSED: &str = "sensei.quality.capa.closed";
        pub const INSPECTION_COMPLETED: &str = "sensei.quality.inspection.completed";
        pub const AUDIT_FINDING: &str = "sensei.quality.audit.finding";
        pub const SUPPLIER_EVALUATED: &str = "sensei.quality.supplier.evaluated";
    }

    /// Production domain events.
    pub mod production {
        pub const WORK_ORDER_CREATED: &str = "sensei.production.work-order.created";
        pub const WORK_ORDER_STATUS_CHANGED: &str = "sensei.production.work-order.status-changed";
    }

    /// Identity domain events.
    pub mod identity {
        pub const USER_CREATED: &str = "sensei.identity.user.created";
    }

    /// Finance domain events.
    pub mod finance {
        pub const INVOICE_CREATED: &str = "sensei.finance.invoice.created";
        pub const PAYMENT_PROCESSED: &str = "sensei.finance.payment.processed";
    }

    /// Wildcard subscription patterns.
    pub mod patterns {
        /// Subscribe to all events.
        pub const ALL: &str = "sensei.>";

        /// Subscribe to all quality events.
        pub const ALL_QUALITY: &str = "sensei.quality.>";

        /// Subscribe to all production events.
        pub const ALL_PRODUCTION: &str = "sensei.production.>";
    }
}
