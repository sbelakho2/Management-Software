//! Root Leptos application component.
//!
//! Provides global app state, UI store, i18n, responsive context, and
//! defines all application routes.
//!
//! Uses leptos_router 0.7.8 components::*, path!() macro, ParentRoute for nesting.
//!
//! # Route Layout
//!
//! Public routes (`/`, `/login`) render [`LoginPage`] directly — no industrial bezel.
//! All authenticated routes are nested under [`ProtectedShell`] which provides the
//! [`RootLayout`] with rack sidebar, status bar, and corner screws.

use leptos::prelude::*;
use leptos_meta::*;
use leptos_router::components::*;
use leptos_router::path;

use crate::components::layout::ProtectedShell;
use crate::hooks::use_responsive::provide_responsive;
use crate::i18n::provide_i18n;
use crate::pages::{
    dashboard::DashboardPage,
    document_ingestion::DocumentIngestionPage,
    finance::{
        BudgetListPage, CostRollupListPage, FinancePage, InvoiceListPage, JournalEntryListPage,
        PaymentListPage,
    },
    flow_economics::FlowEconomicsPage,
    hr::{
        EmployeeListPage, HrPage, LeaveListPage, ReviewListPage, TimecardListPage, TrainingListPage,
    },
    integration::IntegrationPage,
    learning_metrics::LearningMetricsPage,
    login::LoginPage,
    maintenance::{EquipmentListPage, MaintenancePage, PmScheduleListPage, WorkRequestListPage},
    ops::{A3ListPage, AndonListPage, OpsPage, ProjectListPage, RiskListPage},
    production::{
        BomListPage, MrpPage, ProductionOrderListPage, ProductionPage, WorkOrderListPage,
    },
    quality::{
        AuditListPage, CapaListPage, InspectionListPage, NcrListPage, QualityPage,
        SupplierEvalListPage,
    },
    station::{StationPage, TeamLeadPage},
    supply_chain::{
        InventoryListPage, PurchaseOrderListPage, QuoteListPage, RfqListPage, SalesOrderListPage,
        StockMoveListPage, SupplyChainPage,
    },
    today::TodayPage,
    tps::{LswPage, StandardWorkPage, TierMeetingsPage, TopologyPage, WorkCentersPage},
    tps_flow::{AgentPage, CtqPage, KanbanPage, ObeyaPage, TrainingPage},
};
use crate::state::AppState;
use crate::stores::ui::provide_ui_store;

/// Root application component.
#[component]
pub fn App() -> impl IntoView {
    provide_meta_context();

    // Provide shared app state (auth tokens, API client, etc.)
    let app_state = AppState::new();
    provide_context(app_state.clone());

    // Resolve the initial auth state (Loading -> Anonymous, or a refresh
    // attempt when tokens survived an SSR handoff).
    leptos::task::spawn_local({
        let state = app_state.clone();
        async move {
            state.resolve_initial_auth().await;
        }
    });

    // Provide reactive UI store.
    let _ui_store = provide_ui_store();

    // Provide i18n context.
    let i18n = provide_i18n();
    let dir = i18n.direction;

    // Provide responsive breakpoint info.
    let _responsive = provide_responsive();

    // Item 60: the PWA/offline machinery was never INITIALIZED — the
    // service worker registration, connectivity listeners and the offline
    // queue now start with the application.
    let _pwa_state = crate::pwa::init_pwa();
    let sync_store = crate::stores::sync::SyncStore::new();
    provide_context(sync_store.clone());
    leptos::task::spawn_local(async move {
        let _ = crate::pwa::init_sync_service(sync_store).await;
    });

    // Item 63: realtime push — when a session exists, connect the WebSocket
    // and join the tenant room so Andon/production events arrive without
    // any refresh.
    let realtime_store = crate::stores::realtime::RealtimeStore::new();
    provide_context(realtime_store.clone());
    leptos::task::spawn_local({
        let state = app_state.clone();
        let realtime_store = realtime_store.clone();
        async move {
            let Some(tokens) = state.tokens.get_untracked() else {
                return;
            };
            let Some(user) = state.user.get_untracked() else {
                return;
            };
            realtime_store.connect(
                &state.api_base.get_untracked(),
                &user.tenant_id,
                &tokens.access_token,
            );
        }
    });
    let _ = realtime_store;

    view! {
        <Html attr:lang=move || i18n.locale.get() attr:dir=move || dir.get() />

        <Title text="Sensei ERP" />

        <Meta charset="UTF-8" />
        <Meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <Meta name="description" content="Sensei ERP - Manufacturing Management System" />

        <Stylesheet href="/pkg/sensei-frontend.css" />
        <Stylesheet href="/styles/rams.css" />

        <Router>
            <Routes fallback=|| view! {
                <div class="not-found">
                    <h1>"404 - Page Not Found"</h1>
                    <a href="/dashboard">"Back to Dashboard"</a>
                </div>
            }>
                // ═══════════════════════════════════════════════
                // PUBLIC ROUTES — no industrial bezel / sidebar
                // ═══════════════════════════════════════════════
                <Route path=path!("/") view=LoginPage />
                <Route path=path!("/login") view=LoginPage />

                // ═══════════════════════════════════════════════
                // AUTHENTICATED ROUTES — wrapped in Rams layout
                // ═══════════════════════════════════════════════
                // ProtectedShell provides the RootLayout (bezel, status bar,
                // rack sidebar, corner screws) via <Outlet/>.
                <ParentRoute path=path!("/") view=ProtectedShell>
                    // Today is the primary home (item 30/67): the landing
                    // route redirects here, not to the count dashboard.
                    <Route path=path!("/") view=TodayPage />
                    <Route path=path!("today") view=TodayPage />
                    <Route path=path!("/dashboard") view=DashboardPage />

                    // TPS work surfaces (item 64): the flows live beside
                    // the work — not inside an "Ops" module.
                    <Route path=path!("/tps/lsw") view=LswPage />
                    <Route path=path!("/tps/standard-work") view=StandardWorkPage />
                    <Route path=path!("/tps/tier-meetings") view=TierMeetingsPage />
                    <Route path=path!("/tps/topology") view=TopologyPage />
                    <Route path=path!("/tps/work-centers") view=WorkCentersPage />
                    <Route path=path!("/tps/kanban") view=KanbanPage />
                    <Route path=path!("/tps/training") view=TrainingPage />
                    <Route path=path!("/tps/ctq") view=CtqPage />
                    <Route path=path!("/tps/obeya") view=ObeyaPage />
                    <Route path=path!("/agent") view=AgentPage />
                    <Route path=path!("/station") view=StationPage />
                    <Route path=path!("/team-lead") view=TeamLeadPage />
                    <Route path=path!("/tps/learning") view=LearningMetricsPage />
                    <Route path=path!("/tps/flow-economics") view=FlowEconomicsPage />
                    <Route path=path!("/integration") view=IntegrationPage />
                    <Route path=path!("/documents/ingestion") view=DocumentIngestionPage />

                    // Quality Management
                    <ParentRoute path=path!("/quality") view=QualityPage>
                        <Route path=path!("/") view=NcrListPage />
                        <Route path=path!("ncr") view=NcrListPage />
                        <Route path=path!("capa") view=CapaListPage />
                        <Route path=path!("inspections") view=InspectionListPage />
                        <Route path=path!("audits") view=AuditListPage />
                        <Route path=path!("suppliers") view=SupplierEvalListPage />
                    </ParentRoute>

                    // Production Management
                    <ParentRoute path=path!("/production") view=ProductionPage>
                        <Route path=path!("/") view=WorkOrderListPage />
                        <Route path=path!("work-orders") view=WorkOrderListPage />
                        <Route path=path!("orders") view=ProductionOrderListPage />
                        <Route path=path!("bom") view=BomListPage />
                        <Route path=path!("mrp") view=MrpPage />
                    </ParentRoute>

                    // Maintenance Management
                    <ParentRoute path=path!("/maintenance") view=MaintenancePage>
                        <Route path=path!("/") view=WorkRequestListPage />
                        <Route path=path!("work-requests") view=WorkRequestListPage />
                        <Route path=path!("pm-schedules") view=PmScheduleListPage />
                        <Route path=path!("equipment") view=EquipmentListPage />
                    </ParentRoute>

                    // Finance Management
                    <ParentRoute path=path!("/finance") view=FinancePage>
                        <Route path=path!("/") view=InvoiceListPage />
                        <Route path=path!("invoices") view=InvoiceListPage />
                        <Route path=path!("payments") view=PaymentListPage />
                        <Route path=path!("budgets") view=BudgetListPage />
                        <Route path=path!("journal-entries") view=JournalEntryListPage />
                        <Route path=path!("cost-rollups") view=CostRollupListPage />
                    </ParentRoute>

                    // Human Resources
                    <ParentRoute path=path!("/hr") view=HrPage>
                        <Route path=path!("/") view=EmployeeListPage />
                        <Route path=path!("employees") view=EmployeeListPage />
                        <Route path=path!("training") view=TrainingListPage />
                        <Route path=path!("leave") view=LeaveListPage />
                        <Route path=path!("reviews") view=ReviewListPage />
                        <Route path=path!("timecards") view=TimecardListPage />
                    </ParentRoute>

                    // Supply Chain
                    <ParentRoute path=path!("/supply-chain") view=SupplyChainPage>
                        <Route path=path!("/") view=RfqListPage />
                        <Route path=path!("rfqs") view=RfqListPage />
                        <Route path=path!("quotes") view=QuoteListPage />
                        <Route path=path!("sales-orders") view=SalesOrderListPage />
                        <Route path=path!("purchase-orders") view=PurchaseOrderListPage />
                        <Route path=path!("inventory") view=InventoryListPage />
                        <Route path=path!("stock-moves") view=StockMoveListPage />
                    </ParentRoute>

                    // Operations / Continuous Improvement
                    <ParentRoute path=path!("/ops") view=OpsPage>
                        <Route path=path!("/") view=AndonListPage />
                        <Route path=path!("andons") view=AndonListPage />
                        <Route path=path!("projects") view=ProjectListPage />
                        <Route path=path!("a3") view=A3ListPage />
                        <Route path=path!("risks") view=RiskListPage />
                    </ParentRoute>
                </ParentRoute>
            </Routes>
        </Router>
    }
}
