//! CRM account, contact, and opportunity models.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Database representation of a CRM account (customer, supplier, partner, etc.).
///
/// Accounts are organizations tracked in the CRM system. They can be customers,
/// suppliers, partners, or prospects. Each account has address, industry, and
/// revenue information for segmentation and reporting.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AccountModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Organization name.
    pub name: String,
    /// Account type (customer, supplier, partner, prospect, other).
    pub account_type: String,
    /// Status (active, inactive, churned, suspended).
    pub status: String,
    /// Tier level (platinum, gold, silver, bronze).
    pub tier: Option<String>,
    /// Industry sector.
    pub industry: Option<String>,
    /// Website URL.
    pub website: Option<String>,
    /// Phone number.
    pub phone: Option<String>,
    /// Email address.
    pub email: Option<String>,
    /// Address line 1.
    pub address_line1: Option<String>,
    /// Address line 2.
    pub address_line2: Option<String>,
    /// City.
    pub city: Option<String>,
    /// State/province.
    pub state: Option<String>,
    /// Postal/ZIP code.
    pub postal_code: Option<String>,
    /// Country.
    pub country: Option<String>,
    /// Annual revenue.
    pub annual_revenue: Option<f64>,
    /// Parent account (for hierarchical organizations).
    pub parent_id: Option<Uuid>,
    /// Notes.
    pub notes: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a CRM contact person.
///
/// Contacts are individual people associated with accounts. They track
/// personal information and communication details.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct ContactModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Legal first name.
    pub first_name: String,
    /// Legal last name.
    pub last_name: String,
    /// Email address.
    pub email: Option<String>,
    /// Phone number.
    pub phone: Option<String>,
    /// Mobile phone number.
    pub mobile: Option<String>,
    /// Job title or position.
    pub job_title: Option<String>,
    /// Associated account.
    pub account_id: Option<Uuid>,
    /// Notes.
    pub notes: Option<String>,
    /// Whether the contact is active.
    pub is_active: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of an account-contact relationship.
///
/// Junction table linking accounts to contacts with role information
/// and primary contact designation.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct AccountContactModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Account foreign key.
    pub account_id: Uuid,
    /// Contact foreign key.
    pub contact_id: Uuid,
    /// Role within the account (e.g., "Decision Maker", "Technical Lead").
    pub role: Option<String>,
    /// Whether this is the primary contact for the account.
    pub is_primary: bool,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}

/// Database representation of a sales opportunity.
///
/// Opportunities track potential sales through a pipeline from prospecting
/// to close, with amount, probability, and expected close date.
#[derive(Debug, Clone, sqlx::FromRow, Serialize, Deserialize)]
pub struct OpportunityModel {
    /// Primary key (UUID).
    pub id: Uuid,
    /// Tenant foreign key.
    pub tenant_id: Uuid,
    /// Opportunity name.
    pub name: String,
    /// Pipeline stage (prospecting, qualification, needs_analysis, etc.).
    pub stage: String,
    /// Estimated deal amount.
    pub amount: f64,
    /// Win probability (0-100).
    pub probability: i32,
    /// Expected close date.
    pub close_date: Option<DateTime<Utc>>,
    /// Associated account.
    pub account_id: Option<Uuid>,
    /// Primary contact.
    pub contact_id: Option<Uuid>,
    /// Sales owner.
    pub owner_id: Option<Uuid>,
    /// Description.
    pub description: Option<String>,
    /// Reason for loss (if closed_lost).
    pub lost_reason: Option<String>,
    /// Record creation timestamp.
    pub created_at: DateTime<Utc>,
    /// Record last update timestamp.
    pub updated_at: DateTime<Utc>,
}
