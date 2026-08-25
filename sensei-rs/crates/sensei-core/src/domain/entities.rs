//! Core entity definitions for the Sensei ERP system.
//!
//! These represent the foundational domain entities. Each entity has an
//! [`EntityId`](crate::types::EntityId) and timestamp fields for tracking.

use crate::types::{EntityId, TenantId, Timestamp, now, new_id};
use serde::{Deserialize, Serialize};

/// A user account in the system.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    /// Unique identifier.
    pub id: EntityId,
    /// The tenant this user belongs to.
    pub tenant_id: TenantId,
    /// User's email address (used as primary login identifier).
    pub email: String,
    /// User's display name.
    pub name: String,
    /// Bcrypt/Argon2 password hash.
    pub password_hash: String,
    /// Assigned roles for RBAC.
    pub roles: Vec<String>,
    /// Whether this account is active.
    pub is_active: bool,
    /// When the user last logged in.
    pub last_login_at: Option<Timestamp>,
    /// When this record was created.
    pub created_at: Timestamp,
    /// When this record was last updated.
    pub updated_at: Timestamp,
}

impl User {
    /// Create a new [`User`] with the default `"user"` role.
    pub fn new(tenant_id: TenantId, email: String, name: String, password_hash: String) -> Self {
        Self::with_roles(
            tenant_id,
            email,
            name,
            password_hash,
            vec!["user".to_string()],
        )
    }

    /// Create a new [`User`] with explicit roles.
    pub fn with_roles(
        tenant_id: TenantId,
        email: String,
        name: String,
        password_hash: String,
        roles: Vec<String>,
    ) -> Self {
        let now = now();
        Self {
            id: new_id(),
            tenant_id,
            email,
            name,
            password_hash,
            roles,
            is_active: true,
            last_login_at: None,
            created_at: now,
            updated_at: now,
        }
    }
}

/// A tenant/organization in the multi-tenant system.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tenant {
    /// Unique identifier.
    pub id: TenantId,
    /// Organization name.
    pub name: String,
    /// Subdomain slug (used for routing).
    pub slug: String,
    /// Whether this tenant is active.
    pub is_active: bool,
    /// Feature flags for this tenant.
    pub features: Vec<String>,
    /// When this record was created.
    pub created_at: Timestamp,
    /// When this record was last updated.
    pub updated_at: Timestamp,
}

impl Tenant {
    /// Create a new [`Tenant`].
    pub fn new(name: String, slug: String) -> Self {
        let now = now();
        Self {
            id: new_id(),
            name,
            slug,
            is_active: true,
            features: Vec::new(),
            created_at: now,
            updated_at: now,
        }
    }
}

/// A role definition for RBAC.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Role {
    /// Unique identifier.
    pub id: EntityId,
    /// The tenant this role belongs to.
    pub tenant_id: TenantId,
    /// Role name (e.g., "admin", "quality_manager", "operator").
    pub name: String,
    /// Human-readable description.
    pub description: String,
    /// Granted permissions.
    pub permissions: Vec<String>,
    /// When this record was created.
    pub created_at: Timestamp,
    /// When this record was last updated.
    pub updated_at: Timestamp,
}

/// A permission string representing an action on a resource.
///
/// Format: `{resource}:{action}` (e.g., `quality:ncr:create`, `users:read`)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Permission(pub String);

impl Permission {
    /// Parse a permission string into resource and action.
    pub fn parse(&self) -> Option<(&str, &str)> {
        self.0.split_once(':')
    }

    /// Returns the resource part of the permission.
    pub fn resource(&self) -> Option<&str> {
        self.parse().map(|(r, _)| r)
    }

    /// Returns the action part of the permission.
    pub fn action(&self) -> Option<&str> {
        self.parse().map(|(_, a)| a)
    }
}

/// Represents a quality non-conformance report (NCR).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NonConformanceReport {
    /// Unique identifier.
    pub id: EntityId,
    /// The tenant this NCR belongs to.
    pub tenant_id: TenantId,
    /// NCR number (human-readable).
    pub ncr_number: String,
    /// Title/summary of the non-conformance.
    pub title: String,
    /// Detailed description.
    pub description: String,
    /// Severity level.
    pub severity: NcrSeverity,
    /// Current status.
    pub status: NcrStatus,
    /// ID of the assigned corrective action.
    pub capa_id: Option<EntityId>,
    /// ID of the user who reported this.
    pub reported_by: EntityId,
    /// When this record was created.
    pub created_at: Timestamp,
    /// When this record was last updated.
    pub updated_at: Timestamp,
}

/// Severity levels for non-conformance reports.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NcrSeverity {
    /// Minor issue, no product impact.
    Minor,
    /// Significant issue requiring corrective action.
    Major,
    /// Critical issue with safety or regulatory implications.
    Critical,
}

/// Status values for non-conformance reports.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NcrStatus {
    /// Report has been opened.
    Open,
    /// Investigation is in progress.
    UnderInvestigation,
    /// Corrective action has been defined.
    ActionDefined,
    /// Corrective action is in progress.
    InProgress,
    /// Corrective action has been completed and verified.
    Closed,
    /// Report has been rejected as invalid.
    Rejected,
}

/// A corrective and preventive action (CAPA).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Capa {
    /// Unique identifier.
    pub id: EntityId,
    /// The tenant this CAPA belongs to.
    pub tenant_id: TenantId,
    /// CAPA number (human-readable).
    pub capa_number: String,
    /// Title of the corrective action.
    pub title: String,
    /// Root cause analysis text.
    pub root_cause: Option<String>,
    /// Description of the action plan.
    pub action_plan: String,
    /// Current status.
    pub status: CapaStatus,
    /// ID of the user who owns this CAPA.
    pub owner_id: EntityId,
    /// When this record was created.
    pub created_at: Timestamp,
    /// When this record was last updated.
    pub updated_at: Timestamp,
    /// Deadline for completion.
    pub due_date: Option<Timestamp>,
}

/// Status values for CAPAs.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CapaStatus {
    /// CAPA has been opened.
    Open,
    /// Root cause analysis in progress.
    AnalysisInProgress,
    /// Action plan defined and approved.
    Approved,
    /// Implementation in progress.
    ImplementationInProgress,
    /// Effectiveness verification in progress.
    VerificationInProgress,
    /// CAPA has been closed.
    Closed,
}

/// A work order in the production/manufacturing domain.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkOrder {
    /// Unique identifier.
    pub id: EntityId,
    /// The tenant this work order belongs to.
    pub tenant_id: TenantId,
    /// Work order number (human-readable).
    pub wo_number: String,
    /// Product/part being produced.
    pub product_id: EntityId,
    /// Quantity to produce.
    pub quantity: i64,
    /// Current status.
    pub status: WorkOrderStatus,
    /// Assigned work center.
    pub work_center_id: Option<EntityId>,
    /// Scheduled start date.
    pub scheduled_start: Option<Timestamp>,
    /// Scheduled end date.
    pub scheduled_end: Option<Timestamp>,
    /// When this record was created.
    pub created_at: Timestamp,
    /// When this record was last updated.
    pub updated_at: Timestamp,
}

/// Status values for work orders.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum WorkOrderStatus {
    /// Work order has been created.
    Created,
    /// Work order has been released to production.
    Released,
    /// Work is in progress.
    InProgress,
    /// Work has been completed.
    Completed,
    /// Work has been cancelled.
    Cancelled,
    /// Work order is on hold.
    OnHold,
}

/// A customer account or company in the system.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Account {
    /// Unique identifier.
    pub id: EntityId,
    /// The tenant this account belongs to.
    pub tenant_id: TenantId,
    /// Account/company name.
    pub name: String,
    /// Tax identification number.
    pub tax_id: Option<String>,
    /// Primary contact email.
    pub email: Option<String>,
    /// Primary phone number.
    pub phone: Option<String>,
    /// Street address.
    pub address_line1: Option<String>,
    /// Additional address info.
    pub address_line2: Option<String>,
    /// City.
    pub city: Option<String>,
    /// State/province.
    pub state: Option<String>,
    /// Postal/ZIP code.
    pub postal_code: Option<String>,
    /// Country.
    pub country: Option<String>,
    /// Account type (e.g., "customer", "supplier", "both").
    pub account_type: String,
    /// Whether this account is active.
    pub is_active: bool,
    /// Free-form notes.
    pub notes: Option<String>,
    /// When this record was created.
    pub created_at: Timestamp,
    /// When this record was last updated.
    pub updated_at: Timestamp,
}

impl Account {
    /// Create a new [`Account`].
    pub fn new(tenant_id: TenantId, name: String, account_type: String) -> Self {
        let now = now();
        Self {
            id: new_id(),
            tenant_id,
            name,
            tax_id: None,
            email: None,
            phone: None,
            address_line1: None,
            address_line2: None,
            city: None,
            state: None,
            postal_code: None,
            country: None,
            account_type,
            is_active: true,
            notes: None,
            created_at: now,
            updated_at: now,
        }
    }
}

/// A contact person linked to an account.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Contact {
    /// Unique identifier.
    pub id: EntityId,
    /// The tenant this contact belongs to.
    pub tenant_id: TenantId,
    /// The account this contact belongs to.
    pub account_id: Option<EntityId>,
    /// Contact's first name.
    pub first_name: String,
    /// Contact's last name.
    pub last_name: String,
    /// Contact's email address.
    pub email: String,
    /// Contact's phone number.
    pub phone: Option<String>,
    /// Job title.
    pub job_title: Option<String>,
    /// Department.
    pub department: Option<String>,
    /// Whether this contact is the primary contact for their account.
    pub is_primary: bool,
    /// Whether this contact is active.
    pub is_active: bool,
    /// Free-form notes.
    pub notes: Option<String>,
    /// When this record was created.
    pub created_at: Timestamp,
    /// When this record was last updated.
    pub updated_at: Timestamp,
}

impl Contact {
    /// Create a new [`Contact`].
    pub fn new(tenant_id: TenantId, first_name: String, last_name: String, email: String) -> Self {
        let now = now();
        Self {
            id: new_id(),
            tenant_id,
            account_id: None,
            first_name,
            last_name,
            email,
            phone: None,
            job_title: None,
            department: None,
            is_primary: false,
            is_active: true,
            notes: None,
            created_at: now,
            updated_at: now,
        }
    }
}

/// A product or service offered by the organization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Product {
    /// Unique identifier.
    pub id: EntityId,
    /// The tenant this product belongs to.
    pub tenant_id: TenantId,
    /// Product SKU/code.
    pub sku: String,
    /// Product name.
    pub name: String,
    /// Product description.
    pub description: Option<String>,
    /// Product category.
    pub category: Option<String>,
    /// Product type (e.g., "finished_good", "raw_material", "service", "subassembly").
    pub product_type: String,
    /// Unit of measure (e.g., "pcs", "kg", "m", "l").
    pub unit_of_measure: String,
    /// Standard cost.
    pub standard_cost: Option<f64>,
    /// Selling price.
    pub selling_price: Option<f64>,
    /// Minimum stock level.
    pub min_stock_level: Option<f64>,
    /// Maximum stock level.
    pub max_stock_level: Option<f64>,
    /// Current stock quantity.
    pub current_stock: f64,
    /// Whether this product is active.
    pub is_active: bool,
    /// Free-form notes.
    pub notes: Option<String>,
    /// When this record was created.
    pub created_at: Timestamp,
    /// When this record was last updated.
    pub updated_at: Timestamp,
}

impl Product {
    /// Create a new [`Product`].
    pub fn new(
        tenant_id: TenantId,
        sku: String,
        name: String,
        product_type: String,
        unit_of_measure: String,
    ) -> Self {
        let now = now();
        Self {
            id: new_id(),
            tenant_id,
            sku,
            name,
            description: None,
            category: None,
            product_type,
            unit_of_measure,
            standard_cost: None,
            selling_price: None,
            min_stock_level: None,
            max_stock_level: None,
            current_stock: 0.0,
            is_active: true,
            notes: None,
            created_at: now,
            updated_at: now,
        }
    }
}
