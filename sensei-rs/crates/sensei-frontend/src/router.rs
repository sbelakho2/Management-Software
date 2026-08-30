//! Application route definitions and configuration.

/// Route constants used throughout the frontend.
pub mod routes {
    // Auth
    pub const LOGIN: &str = "/login";
    pub const DASHBOARD: &str = "/dashboard";

    // Quality
    pub const QUALITY: &str = "/quality";
    pub const QUALITY_NCR: &str = "/quality/ncrs";
    pub const QUALITY_CAPA: &str = "/quality/capa";
    pub const QUALITY_INSPECTIONS: &str = "/quality/inspections";
    pub const QUALITY_AUDITS: &str = "/quality/audits";
    pub const QUALITY_SUPPLIERS: &str = "/quality/suppliers";

    // Production
    pub const PRODUCTION: &str = "/production";
    pub const PRODUCTION_WORK_ORDERS: &str = "/production/work-orders";
    pub const PRODUCTION_ORDERS: &str = "/production/orders";
    pub const PRODUCTION_BOM: &str = "/production/bom";
    pub const PRODUCTION_MRP: &str = "/production/mrp";

    // Maintenance
    pub const MAINTENANCE: &str = "/maintenance";
    pub const MAINTENANCE_WORK_REQUESTS: &str = "/maintenance/work-requests";
    pub const MAINTENANCE_PM_SCHEDULES: &str = "/maintenance/pm-schedules";
    pub const MAINTENANCE_EQUIPMENT: &str = "/maintenance/equipment";

    // Finance
    pub const FINANCE: &str = "/finance";
    pub const FINANCE_INVOICES: &str = "/finance/invoices";
    pub const FINANCE_PAYMENTS: &str = "/finance/payments";
    pub const FINANCE_BUDGETS: &str = "/finance/budgets";
    pub const FINANCE_JOURNAL_ENTRIES: &str = "/finance/journal-entries";
    pub const FINANCE_COST_ROLLUPS: &str = "/finance/cost-rollups";

    // HR
    pub const HR: &str = "/hr";
    pub const HR_EMPLOYEES: &str = "/hr/employees";
    pub const HR_TRAINING: &str = "/hr/training";
    pub const HR_LEAVE: &str = "/hr/leave";
    pub const HR_REVIEWS: &str = "/hr/reviews";
    pub const HR_TIMECARDS: &str = "/hr/timecards";

    // Supply Chain
    pub const SUPPLY_CHAIN: &str = "/supply-chain";
    pub const SC_RFQS: &str = "/supply-chain/rfqs";
    pub const SC_QUOTES: &str = "/supply-chain/quotes";
    pub const SC_SALES_ORDERS: &str = "/supply-chain/sales-orders";
    pub const SC_PURCHASE_ORDERS: &str = "/supply-chain/purchase-orders";
    pub const SC_INVENTORY: &str = "/supply-chain/inventory";
    pub const SC_STOCK_MOVES: &str = "/supply-chain/stock-moves";

    // Operations
    pub const OPS: &str = "/ops";
    pub const OPS_ANDONS: &str = "/ops/andons";
    pub const OPS_PROJECTS: &str = "/ops/projects";
    pub const OPS_A3: &str = "/ops/a3";
    pub const OPS_RISKS: &str = "/ops/risks";

    /// API base path for proxied requests.
    pub const API_BASE: &str = "/api/v1";
}

/// Route groups for middleware and authorization checks.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RouteGroup {
    /// Public routes accessible without authentication.
    Public,
    /// Protected routes requiring a valid JWT.
    Authenticated,
    /// Admin-only routes.
    Admin,
}

/// Return the route group for a given path.
pub fn classify_route(path: &str) -> RouteGroup {
    match path {
        "/"
        | "/login"
        | "/api/v1/auth/login"
        | "/api/v1/auth/refresh"
        | "/health/live"
        | "/health/ready"
        | "/metrics" => RouteGroup::Public,
        // All other routes require authentication
        _ => RouteGroup::Authenticated,
    }
}
