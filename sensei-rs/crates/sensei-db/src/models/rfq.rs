//! RFQ (Request for Quote) and quoting models.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database representation of an RFQ line item.
///
/// Line items define the individual products or services being
/// requested within an RFQ, including target pricing.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct RfqLineItemModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent RFQ.
    pub rfq_id: Uuid,
    /// Line number within the RFQ.
    pub line_number: i32,
    /// Part number being quoted.
    pub part_number: Option<String>,
    /// Description of the item.
    pub description: String,
    /// Quantity requested.
    pub quantity: f64,
    /// Unit of measure.
    pub unit_of_measure: String,
    /// Target price per unit.
    pub target_price: Option<f64>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a supplier quote.
///
/// Supplier quotes capture pricing and terms offered by suppliers
/// in response to RFQs.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct SupplierQuoteModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Supplier providing the quote.
    pub supplier_id: Uuid,
    /// RFQ this quote responds to.
    pub rfq_id: Uuid,
    /// Human-readable quote number.
    pub quote_number: String,
    /// Status (submitted, under_review, accepted, rejected, expired).
    pub status: String,
    /// Subtotal before tax.
    pub subtotal: f64,
    /// Tax amount.
    pub tax: f64,
    /// Total including tax.
    pub total: f64,
    /// Currency code.
    pub currency: String,
    /// Delivery lead time in days.
    pub lead_time_days: Option<i32>,
    /// Payment terms.
    pub payment_terms: Option<String>,
    /// Quote validity expiration date.
    pub valid_until: Option<DateTime<Utc>>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a quote version.
///
/// Quote versions track the history of changes to a quote during
/// the negotiation process.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct QuoteVersionModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent quote.
    pub quote_id: Uuid,
    /// Version number (incremented on each revision).
    pub version_number: i32,
    /// Status (draft, submitted, approved, rejected).
    pub status: String,
    /// Subtotal before tax.
    pub subtotal: f64,
    /// Tax amount.
    pub tax: f64,
    /// Total including tax.
    pub total: f64,
    /// Notes for this version.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a quote line item.
///
/// Line items within a quote version, specifying products, quantities,
/// and pricing for each quoted item.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct QuoteLineItemModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Parent quote.
    pub quote_id: Uuid,
    /// Quote version.
    pub version_id: Uuid,
    /// Line number within the version.
    pub line_number: i32,
    /// Product reference.
    pub product_id: Option<Uuid>,
    /// Description of the item.
    pub description: String,
    /// Quantity quoted.
    pub quantity: f64,
    /// Price per unit.
    pub unit_price: f64,
    /// Cost per unit.
    pub unit_cost: f64,
    /// Extended price (quantity * unit_price).
    pub extended_price: f64,
    /// Extended cost (quantity * unit_cost).
    pub extended_cost: f64,
    /// Lead time in days.
    pub lead_time_days: Option<i32>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a supplier qualification.
///
/// Qualifications assess supplier capability against RFQ requirements,
/// scoring technical, quality, delivery, and cost dimensions.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct QualificationModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// RFQ being qualified for.
    pub rfq_id: Uuid,
    /// Supplier being assessed.
    pub supplier_id: Uuid,
    /// Status (pending, in_progress, approved, rejected, expired).
    pub status: String,
    /// Overall weighted score.
    pub overall_score: f64,
    /// Technical capability score.
    pub technical_score: f64,
    /// Quality system score.
    pub quality_score: f64,
    /// Delivery performance score.
    pub delivery_score: f64,
    /// Cost competitiveness score.
    pub cost_score: f64,
    /// Notes.
    pub notes: Option<String>,
    /// Assessor user ID.
    pub assessed_by: Option<Uuid>,
    /// Assessment timestamp.
    pub assessed_at: Option<DateTime<Utc>>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}
