//! Reactive UI and domain store modules.
//!
//! Provides [`UiStore`](ui::UiStore) for global UI state,
//! [`DomainStore`](domain::DomainStore) for typed CRUD list state,
//! and individual domain-specific stores ported from the TypeScript
//! Zustand stores in [`frontend/src/stores/`](frontend/src/stores/).

pub mod admin;
pub mod analytics;
pub mod auditor;
pub mod command_palette;
pub mod ctq;
pub mod currency;
pub mod customers;
pub mod domain;
pub mod email_drafting;
pub mod exceptions;
pub mod executive;
pub mod finance;
pub mod form_validation;
pub mod it_monitoring;
pub mod kanban;
pub mod obeya;
pub mod pdf_preview;
pub mod pipeline;
pub mod products;
pub mod project_management;
pub mod quick_actions;
pub mod quotes;
pub mod quoting_helper;
pub mod realtime;
pub mod shipping;
pub mod sites;
pub mod sync;
pub mod tasks;
pub mod today;
pub mod training;
pub mod ui;
pub mod warehouse;

// Re-export store structs and key types for convenience
pub use admin::AdminStore;
pub use analytics::AnalyticsStore;
pub use auditor::AuditorStore;
pub use command_palette::CommandPaletteStore;
pub use ctq::CtqStore;
pub use currency::CurrencyStore;
pub use customers::CustomersStore;
pub use domain::*;
pub use email_drafting::EmailDraftingStore;
pub use exceptions::ExceptionsStore;
pub use executive::ExecutiveStore;
pub use finance::FinanceStore;
pub use form_validation::FormValidationStore;
pub use it_monitoring::ItMonitoringStore;
pub use kanban::KanbanStore;
pub use obeya::ObeyaStore;
pub use pdf_preview::PdfPreviewStore;
pub use pipeline::PipelineStore;
pub use products::ProductsStore;
pub use project_management::ProjectManagementStore;
pub use quick_actions::QuickActionsStore;
pub use quotes::QuotesStore;
pub use quoting_helper::QuotingHelperStore;
pub use realtime::RealtimeStore;
pub use shipping::ShippingStore;
pub use sites::SitesStore;
pub use sync::SyncStore;
pub use tasks::TasksStore;
pub use today::TodayStore;
pub use training::TrainingStore;
pub use ui::*;
pub use warehouse::WarehouseStore;
