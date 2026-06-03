//! # Sensei Domain Services
//!
//! Implementation of domain service logic for all business domains:
//! - Quality (NCR, CAPA, inspections)
//! - Finance (invoices, payments, budgeting)
//! - Production (work orders, scheduling)
//! - Maintenance (equipment, work requests)
//! - HR (employees, training)
//! - Supply Chain (purchasing, inventory)
//! - Operations (continuous improvement)
//! - AI/ML (predictions, anomaly detection)
//! - Accounts (customer/supplier companies)
//! - Contacts (contact persons)
//! - Products (product/service catalog)
//! - Tenants (organization management)

pub mod accounts;
pub mod ai;
pub mod contacts;
pub mod finance;
pub mod hr;
pub mod maintenance;
pub mod ops;
pub mod products;
pub mod production;
pub mod quality;
pub mod supply_chain;
pub mod export;
pub mod notifications;
pub mod storage;
pub mod tenants;
pub mod users;

/// Re-export domain service traits for convenience.
pub use accounts::AccountsService;
pub use contacts::ContactsService;
pub use finance::FinanceService;
pub use hr::HrService;
pub use ops::OperationsService;
pub use products::ProductsService;
pub use production::ProductionService;
pub use quality::QualityService;
pub use tenants::TenantsService;
pub use users::UsersService;
