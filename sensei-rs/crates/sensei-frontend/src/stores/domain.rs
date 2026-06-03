//! Generic and domain-specific reactive stores.
//!
//! [`DomainStore<T>`] is a generic reactive container for paginated,
//! searchable CRUD lists. Each domain module then defines a typed
//! store wrapping domain-specific operations.

use leptos::prelude::*;

// ---------------------------------------------------------------------------
// Generic DomainStore
// ---------------------------------------------------------------------------

/// A reactive store for a paginated, searchable list of items of type `T`.
///
/// # Type Parameters
/// * `T` — The item type (must be `'static` to live in reactive signals).
#[derive(Debug, Clone)]
pub struct DomainStore<T: 'static> {
    /// The list of items currently loaded.
    pub items: RwSignal<Vec<T>>,
    /// Whether a fetch is in progress.
    pub loading: RwSignal<bool>,
    /// The last error message, if any.
    pub error: RwSignal<Option<String>>,
    /// The current page number (1-based).
    pub current_page: RwSignal<usize>,
    /// The total number of available pages.
    pub total_pages: RwSignal<usize>,
    /// The current search / filter query string.
    pub search_query: RwSignal<String>,
}

impl<T: Send + Sync + 'static> DomainStore<T> {
    /// Create a new, empty `DomainStore`.
    pub fn new() -> Self {
        Self {
            items: RwSignal::new(Vec::new()),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
            current_page: RwSignal::new(1),
            total_pages: RwSignal::new(1),
            search_query: RwSignal::new(String::new()),
        }
    }

    /// Replace the item list (e.g. after a successful fetch).
    pub fn set_items(&self, items: Vec<T>) {
        self.items.set(items);
    }

    /// Set the loading state.
    pub fn set_loading(&self, loading: bool) {
        self.loading.set(loading);
    }

    /// Set or clear the error message.
    pub fn set_error(&self, error: Option<String>) {
        self.error.set(error);
    }

    /// Update pagination state.
    pub fn set_pagination(&self, page: usize, total: usize) {
        self.current_page.set(page);
        self.total_pages.set(total);
    }

    /// Go to a specific page.
    pub fn go_to_page(&self, page: usize) {
        let clamped = page.clamp(1, self.total_pages.get());
        self.current_page.set(clamped);
    }

    /// Go to the next page (if available).
    pub fn next_page(&self) {
        let current = self.current_page.get();
        let total = self.total_pages.get();
        if current < total {
            self.current_page.set(current + 1);
        }
    }

    /// Go to the previous page (if available).
    pub fn prev_page(&self) {
        let current = self.current_page.get();
        if current > 1 {
            self.current_page.set(current - 1);
        }
    }

    /// Update the search query (resets to page 1).
    pub fn set_search(&self, query: &str) {
        self.search_query.set(query.to_string());
        self.current_page.set(1);
    }

    /// Clear all state back to defaults.
    pub fn reset(&self) {
        self.items.set(Vec::new());
        self.loading.set(false);
        self.error.set(None);
        self.current_page.set(1);
        self.total_pages.set(1);
        self.search_query.set(String::new());
    }
}

impl<T: Send + Sync + 'static> Default for DomainStore<T> {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// QualityStore
// ---------------------------------------------------------------------------

/// Reactive store for the Quality domain.
#[derive(Debug, Clone)]
pub struct QualityStore {
    pub ncrs: DomainStore<crate::api::quality::NcrDto>,
    pub capas: DomainStore<crate::api::quality::CapaDto>,
    pub inspections: DomainStore<crate::api::quality::InspectionDto>,
    pub audits: DomainStore<crate::api::quality::AuditDto>,
}

impl QualityStore {
    pub fn new() -> Self {
        Self {
            ncrs: DomainStore::new(),
            capas: DomainStore::new(),
            inspections: DomainStore::new(),
            audits: DomainStore::new(),
        }
    }
}

impl Default for QualityStore {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// FinanceStore
// ---------------------------------------------------------------------------

/// Reactive store for the Finance domain.
#[derive(Debug, Clone)]
pub struct FinanceStore {
    pub invoices: DomainStore<crate::api::finance::InvoiceDto>,
    pub payments: DomainStore<crate::api::finance::PaymentDto>,
    pub budgets: DomainStore<crate::api::finance::BudgetDto>,
    pub journal_entries: DomainStore<crate::api::finance::JournalEntryDto>,
}

impl FinanceStore {
    pub fn new() -> Self {
        Self {
            invoices: DomainStore::new(),
            payments: DomainStore::new(),
            budgets: DomainStore::new(),
            journal_entries: DomainStore::new(),
        }
    }
}

impl Default for FinanceStore {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// ProductionStore
// ---------------------------------------------------------------------------

/// Reactive store for the Production domain.
#[derive(Debug, Clone)]
pub struct ProductionStore {
    pub work_orders: DomainStore<crate::api::production::WorkOrderDto>,
    pub production_orders: DomainStore<crate::api::production::ProductionOrderDto>,
    pub bom: DomainStore<crate::api::production::BomItemDto>,
    pub mrp: DomainStore<crate::api::production::MrpRecordDto>,
}

impl ProductionStore {
    pub fn new() -> Self {
        Self {
            work_orders: DomainStore::new(),
            production_orders: DomainStore::new(),
            bom: DomainStore::new(),
            mrp: DomainStore::new(),
        }
    }
}

impl Default for ProductionStore {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// HrStore
// ---------------------------------------------------------------------------

/// Reactive store for the HR domain.
#[derive(Debug, Clone)]
pub struct HrStore {
    pub employees: DomainStore<crate::api::hr::EmployeeDto>,
    pub training: DomainStore<crate::api::hr::TrainingRecordDto>,
    pub leave: DomainStore<crate::api::hr::LeaveRequestDto>,
    pub reviews: DomainStore<crate::api::hr::PerformanceReviewDto>,
    pub timecards: DomainStore<crate::api::hr::TimecardDto>,
}

impl HrStore {
    pub fn new() -> Self {
        Self {
            employees: DomainStore::new(),
            training: DomainStore::new(),
            leave: DomainStore::new(),
            reviews: DomainStore::new(),
            timecards: DomainStore::new(),
        }
    }
}

impl Default for HrStore {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// SupplyChainStore
// ---------------------------------------------------------------------------

/// Reactive store for the Supply Chain domain.
#[derive(Debug, Clone)]
pub struct SupplyChainStore {
    pub rfqs: DomainStore<crate::api::rfq::RfqDto>,
    pub quotes: DomainStore<crate::api::rfq::QuoteDto>,
    pub sales_orders: DomainStore<crate::api::supply_chain::SalesOrderDto>,
    pub purchase_orders: DomainStore<crate::api::supply_chain::PurchaseOrderDto>,
    pub inventory: DomainStore<crate::api::supply_chain::InventoryItemDto>,
}

impl SupplyChainStore {
    pub fn new() -> Self {
        Self {
            rfqs: DomainStore::new(),
            quotes: DomainStore::new(),
            sales_orders: DomainStore::new(),
            purchase_orders: DomainStore::new(),
            inventory: DomainStore::new(),
        }
    }
}

impl Default for SupplyChainStore {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// MaintenanceStore
// ---------------------------------------------------------------------------

/// Reactive store for the Maintenance domain.
#[derive(Debug, Clone)]
pub struct MaintenanceStore {
    pub work_requests: DomainStore<crate::api::maintenance::WorkRequestDto>,
    pub pm_schedules: DomainStore<crate::api::maintenance::PmScheduleDto>,
    pub equipment: DomainStore<crate::api::maintenance::EquipmentDto>,
}

impl MaintenanceStore {
    pub fn new() -> Self {
        Self {
            work_requests: DomainStore::new(),
            pm_schedules: DomainStore::new(),
            equipment: DomainStore::new(),
        }
    }
}

impl Default for MaintenanceStore {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// OpsStore
// ---------------------------------------------------------------------------

/// Reactive store for the Operations / Continuous Improvement domain.
#[derive(Debug, Clone)]
pub struct OpsStore {
    pub andons: DomainStore<crate::api::ops::AndonDto>,
    pub projects: DomainStore<crate::api::ops::ProjectDto>,
    pub a3s: DomainStore<crate::api::ops::A3Dto>,
    pub risks: DomainStore<crate::api::ops::RiskDto>,
}

impl OpsStore {
    pub fn new() -> Self {
        Self {
            andons: DomainStore::new(),
            projects: DomainStore::new(),
            a3s: DomainStore::new(),
            risks: DomainStore::new(),
        }
    }
}

impl Default for OpsStore {
    fn default() -> Self {
        Self::new()
    }
}
