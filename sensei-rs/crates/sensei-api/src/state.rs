//! Application state shared across all request handlers.
//!
//! Uses Axum's [`State`](axum::extract::State) extractor to provide
//! shared services to route handlers.

use sensei_auth::jwt::JwtService;
use sensei_auth::rbac::RbacService;
use sensei_core::config::AppConfig;
use sensei_core::types::{EntityId, Timestamp};
use sensei_event_bus::EventBus;
use sensei_services::accounts::{AccountsService, DatabaseAccountsService, InMemoryAccountsService};
use sensei_services::notifications::{EmailService, InMemoryEmailService, LettreEmailService};
use sensei_services::notifications::service::{
    DatabaseNotificationService, InMemoryNotificationService, NotificationService,
};
use sensei_services::ops::search::{
    DatabaseSearchService, InMemorySearchService, SearchService,
};
use sensei_services::ai::chatbot::{ChatbotService, InMemoryChatbotService};
use sensei_services::ai::DatabaseChatbotService;
use sensei_services::ai::{AiService, DatabaseAiService, InMemoryAiService};
use sensei_services::contacts::{ContactsService, DatabaseContactsService, InMemoryContactsService};
use sensei_services::finance::{DatabaseFinanceService, FinanceService, InMemoryFinanceService};
use sensei_services::hr::{DatabaseHrService, HrService, InMemoryHrService};
use sensei_services::maintenance::{DatabaseMaintenanceService, InMemoryMaintenanceService, MaintenanceService};
use sensei_services::ops::{DatabaseOperationsService, InMemoryOperationsService, OperationsService};
use sensei_services::products::{DatabaseProductsService, InMemoryProductsService, ProductsService};
use sensei_services::production::{DatabaseProductionService, InMemoryProductionService, ProductionService};
use sensei_services::quality::{DatabaseQualityService, InMemoryQualityService, QualityService};
use sensei_services::supply_chain::{DatabaseSupplyChainService, InMemorySupplyChainService, SupplyChainService};
use sensei_services::tenants::{DatabaseTenantsService, InMemoryTenantsService, TenantsService};
use sensei_services::storage::{
    FileStorageService, InMemoryStorageService, LocalStorageService, S3StorageService,
};
use sensei_services::export::excel::ExcelExportService;
use sensei_services::export::pdf::PdfExportService;
use sensei_services::users::{DatabaseUsersService, UsersService};
use sqlx::PgPool;
use std::collections::{HashMap, HashSet};
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::middleware::audit::AuditLog;
use crate::middleware::rate_limiter::RateLimiter;
use crate::services::{sse::SseManager, ws::WebSocketManager};
use crate::stores;

/// A stored password reset token.
#[derive(Debug, Clone)]
pub struct PasswordResetToken {
    /// The user ID this token is for.
    pub user_id: EntityId,
    /// When the token expires.
    pub expires_at: Timestamp,
}

/// A stored email verification token.
#[derive(Debug, Clone)]
pub struct EmailVerificationToken {
    /// The user ID this token is for.
    pub user_id: EntityId,
    /// When the token expires.
    pub expires_at: Timestamp,
}

/// Shared application state available to all handlers via `State<AppState>`.
#[derive(Clone)]
pub struct AppState {
    /// Application configuration.
    pub config: Arc<AppConfig>,
    /// JWT service for token operations.
    pub jwt_service: Arc<JwtService>,
    /// RBAC service for permission checks.
    pub rbac_service: Arc<RbacService>,
    /// Database connection pool (optional - initialized on demand).
    pub db_pool: Option<Arc<PgPool>>,
    /// Full-text search service across entities.
    pub search_service: Arc<dyn SearchService>,
    /// In-app notification service with persistence.
    pub notification_service: Arc<dyn NotificationService>,
    /// AI/ML prediction and anomaly detection service.
    pub ai_service: Arc<dyn AiService>,
    /// Chatbot service for conversational AI.
    pub chatbot_service: Arc<dyn ChatbotService>,
    /// Finance domain service (invoices, payments, budgets).
    pub finance_service: Arc<dyn FinanceService>,
    /// Human Resources domain service (employees, training, leave).
    pub hr_service: Arc<dyn HrService>,
    /// Maintenance domain service (work requests, PM, equipment).
    pub maintenance_service: Arc<dyn MaintenanceService>,
    /// Operations / Continuous Improvement domain service.
    pub ops_service: Arc<dyn OperationsService>,
    /// Production / Manufacturing domain service.
    pub production_service: Arc<dyn ProductionService>,
    /// Supply Chain domain service (RFQ, orders, inventory).
    pub supply_chain_service: Arc<dyn SupplyChainService>,
    /// Quality domain service (NCR, CAPA, inspections, audits).
    pub quality_service: Arc<dyn QualityService>,
    /// Email service for sending notifications (password reset, verification, etc.).
    pub email_service: Arc<dyn EmailService>,
    /// Event bus for publishing/subscribing to domain events.
    pub event_bus: Arc<dyn EventBus>,
    /// User management service for authentication.
    pub users_service: Arc<dyn UsersService>,
    /// Accounts/Companies management service.
    pub accounts_service: Arc<dyn AccountsService>,
    /// Contacts management service.
    pub contacts_service: Arc<dyn ContactsService>,
    /// Products management service.
    pub products_service: Arc<dyn ProductsService>,
    /// Tenants management service.
    pub tenants_service: Arc<dyn TenantsService>,
    /// File storage service (local filesystem or S3/MinIO).
    pub storage_service: Arc<dyn FileStorageService>,
    /// PDF report generation service.
    pub pdf_service: PdfExportService,
    /// Excel/CSV export service.
    pub excel_service: ExcelExportService,
    /// Blacklisted JWT tokens (for logout).
    pub blacklisted_tokens: Arc<RwLock<HashSet<String>>>,
    /// Password reset tokens.
    pub password_reset_tokens: Arc<RwLock<HashMap<String, PasswordResetToken>>>,
    /// Email verification tokens.
    pub email_verification_tokens: Arc<RwLock<HashMap<String, EmailVerificationToken>>>,
    /// Rate limiter for API endpoints.
    pub rate_limiter: RateLimiter,
    /// Audit log for recording state-changing requests.
    pub audit_log: AuditLog,

    // ── Real-time communication managers ─────────────────────────────

    /// WebSocket connection manager for room-based pub/sub.
    pub ws_manager: WebSocketManager,
    /// Server-Sent Events manager for one-way event streaming.
    pub sse_manager: SseManager,

    // ── In-memory stores (temporary; replaced by domain services later) ─

    /// Kanban boards entity store.
    pub kanban_boards: stores::KanbanBoardStore,
    /// Notifications entity store.
    pub notifications: stores::NotificationStore,
    /// Notification preferences entity store.
    pub notification_preferences: stores::NotificationPreferencesStore,
    /// Attachment metadata entity store.
    pub attachment_meta: stores::AttachmentMetaStore,
    /// Attachment binary data entity store.
    pub attachment_data: stores::AttachmentDataStore,
    /// Quote versions entity store.
    pub quote_versions: stores::QuoteVersionStore,
    /// Learning modules entity store.
    pub learning_modules: stores::LearningModuleStore,
    /// Opportunities entity store.
    pub opportunities: stores::OpportunityStore,
    /// Escalation policies entity store.
    pub escalation_policies: stores::EscalationPolicyStore,
    /// Training matrix entries entity store.
    pub training_matrix: stores::TrainingMatrixStore,
    /// Knowledge packs entity store.
    pub knowledge_packs: stores::KnowledgePackStore,
    /// Ingestion jobs entity store.
    pub ingestion_jobs: stores::IngestionJobStore,
    /// Ingestion binary data entity store.
    pub ingestion_data: stores::IngestionDataStore,
    /// Work centers entity store.
    pub work_centers: stores::WorkCenterStore,
    /// Obeya (visual management) boards entity store.
    pub obeya_boards: stores::ObeyaBoardStore,
    /// CTQ (Critical-To-Quality) characteristics entity store.
    pub ctq_characteristics: stores::CtqCharacteristicStore,
    /// CTQ measurement records entity store.
    pub ctq_records: stores::CtqRecordStore,
    // ── Inventory stores ────────────────────────────────────────────────
    /// Inventory items entity store.
    pub inventory_items: stores::InventoryItemStore,
    /// Stock moves entity store.
    pub stock_moves: stores::StockMoveStore,
    /// Warehouses entity store.
    pub warehouses: stores::WarehouseStore,
    // ── MRP stores ──────────────────────────────────────────────────────
    /// MRP demand entries entity store.
    pub demand_entries: stores::DemandEntryStore,
    /// MRP supply orders entity store.
    pub supply_orders: stores::SupplyOrderStore,
    /// MRP runs entity store.
    pub mrp_runs: stores::MrpRunStore,
    // ── Task store ──────────────────────────────────────────────────────
    /// Tasks entity store.
    pub tasks: stores::TaskStore,
    // ── Audit log store ─────────────────────────────────────────────────
    /// Audit log entries entity store.
    pub audit_log_entries: stores::AuditLogEntryStore,
    // ── Production cell store ───────────────────────────────────────────
    /// Production cells entity store.
    pub production_cells: stores::ProductionCellStore,
    // ── Saved view store ────────────────────────────────────────────────
    /// Saved views entity store.
    pub saved_views: stores::SavedViewStore,
    // ── Quoting Helper stores ───────────────────────────────────────────
    /// Work packets entity store.
    pub work_packets: stores::WorkPacketStore,
    /// Cost builds entity store.
    pub cost_builds: stores::CostBuildStore,
    /// NPI conversions entity store.
    pub npi_conversions: stores::NpiConversionStore,
    // ── KPI stores ──────────────────────────────────────────────────────
    /// KPI definitions entity store.
    pub kpi_definitions: stores::KpiDefinitionStore,
    /// KPI values entity store.
    pub kpi_values: stores::KpiValueStore,
    // ── LSW stores ──────────────────────────────────────────────────────
    /// LSW standards entity store.
    pub lsw_standards: stores::LswStandardStore,
    /// LSW audits entity store.
    pub lsw_audits: stores::LswAuditStore,
    // ── Notification Trigger stores ─────────────────────────────────────
    /// Notification triggers entity store.
    pub notification_triggers: stores::NotificationTriggerStore,
    // ── Standard Work stores ────────────────────────────────────────────
    /// Standard work documents entity store.
    pub standard_work_documents: stores::StandardWorkStore,
    /// Standard work document versions entity store.
    pub standard_work_versions: stores::StandardWorkVersionStore,
    // ── State Machine stores ────────────────────────────────────────────
    /// State machine definitions entity store.
    pub state_machine_definitions: stores::StateMachineDefinitionStore,
    /// State machine instances entity store.
    pub state_machine_instances: stores::StateMachineInstanceStore,
    // ── Training stores ─────────────────────────────────────────────────
    /// Training courses entity store.
    pub training_courses: stores::TrainingCourseStore,
    /// Training enrollments entity store.
    pub training_enrollments: stores::TrainingEnrollmentStore,
}

impl AppState {
    /// Create a new [`AppState`] with the given configuration.
    ///
    /// The event bus is initialized as [`InMemoryEventBus`] by default.
    /// Use [`AppState::with_nats_event_bus`] to attempt a NATS connection,
    /// or call [`AppState::with_event_bus`] to provide a custom implementation.
    pub fn new(config: AppConfig, users_service: Arc<dyn UsersService>) -> Self {
        let jwt_service = JwtService::new(
            &config.auth.jwt_secret,
            &config.auth.jwt_issuer,
            &config.auth.jwt_audience,
            config.auth.access_token_expiry_minutes,
            config.auth.refresh_token_expiry_days,
        );
        let event_bus: Arc<dyn EventBus> =
            Arc::new(sensei_event_bus::InMemoryEventBus::new());

        // Initialize email service — use SMTP if credentials are provided,
        // otherwise fall back to in-memory for development/testing.
        let email_service: Arc<dyn EmailService> = if !config.email.smtp_username.is_empty() {
            Arc::new(LettreEmailService::new(&config.email))
        } else {
            Arc::new(InMemoryEmailService::new())
        };

        // Initialize file storage service based on configuration.
        let storage_service: Arc<dyn FileStorageService> = match config.storage.backend.as_str() {
            "s3" => {
                match S3StorageService::new(
                    &config.storage.s3_bucket,
                    &config.storage.s3_region,
                    config.storage.s3_endpoint.as_deref(),
                    &config.storage.s3_access_key,
                    &config.storage.s3_secret_key,
                ) {
                    Ok(svc) => Arc::new(svc) as Arc<dyn FileStorageService>,
                    Err(e) => {
                        tracing::warn!(
                            error = %e,
                            "Failed to initialize S3 storage, falling back to in-memory"
                        );
                        Arc::new(InMemoryStorageService::new()) as Arc<dyn FileStorageService>
                    }
                }
            }
            "local" => {
                Arc::new(LocalStorageService::new(&config.storage.local_path))
                    as Arc<dyn FileStorageService>
            }
            _ => {
                tracing::warn!(
                    backend = %config.storage.backend,
                    "Unknown storage backend, falling back to in-memory"
                );
                Arc::new(InMemoryStorageService::new()) as Arc<dyn FileStorageService>
            }
        };

        // Create shared in-memory service instances (used by both the struct fields
        // and the InMemorySearchService so search sees the same data as routes).
        let accounts_service: Arc<dyn AccountsService> =
            Arc::new(InMemoryAccountsService::new()) as Arc<dyn AccountsService>;
        let contacts_service: Arc<dyn ContactsService> =
            Arc::new(InMemoryContactsService::new()) as Arc<dyn ContactsService>;
        let products_service: Arc<dyn ProductsService> =
            Arc::new(InMemoryProductsService::new()) as Arc<dyn ProductsService>;

        let search_service: Arc<dyn SearchService> =
            Arc::new(InMemorySearchService::new(
                accounts_service.clone(),
                contacts_service.clone(),
                products_service.clone(),
                users_service.clone(),
            )) as Arc<dyn SearchService>;

        Self {
            config: Arc::new(config),
            jwt_service: Arc::new(jwt_service),
            rbac_service: Arc::new(RbacService::new()),
            email_service,
            db_pool: None,
            search_service,
            notification_service: Arc::new(InMemoryNotificationService::new()) as Arc<dyn NotificationService>,
            ai_service: Arc::new(InMemoryAiService::new(None)) as Arc<dyn AiService>,
            chatbot_service: Arc::new(InMemoryChatbotService::new(
                sensei_services::ai::chatbot::ChatbotConfig::default(),
            )) as Arc<dyn ChatbotService>,
            finance_service: Arc::new(InMemoryFinanceService::new(Some(event_bus.clone()))) as Arc<dyn FinanceService>,
            hr_service: Arc::new(InMemoryHrService::new(Some(event_bus.clone()))) as Arc<dyn HrService>,
            maintenance_service: Arc::new(InMemoryMaintenanceService::new(Some(event_bus.clone()))) as Arc<dyn MaintenanceService>,
            ops_service: Arc::new(InMemoryOperationsService::new(Some(event_bus.clone()))) as Arc<dyn OperationsService>,
            production_service: Arc::new(InMemoryProductionService::new(Some(event_bus.clone()))) as Arc<dyn ProductionService>,
            supply_chain_service: Arc::new(InMemorySupplyChainService::new(Some(event_bus.clone()))) as Arc<dyn SupplyChainService>,
            quality_service: Arc::new(InMemoryQualityService::new(Some(event_bus.clone()))),
            event_bus,
            users_service,
            accounts_service,
            contacts_service,
            products_service,
            storage_service,
            pdf_service: PdfExportService::new(),
            excel_service: ExcelExportService::new(),
            tenants_service: Arc::new(InMemoryTenantsService::new()) as Arc<dyn TenantsService>,
            blacklisted_tokens: Arc::new(RwLock::new(HashSet::new())),
            password_reset_tokens: Arc::new(RwLock::new(HashMap::new())),
            email_verification_tokens: Arc::new(RwLock::new(HashMap::new())),
            rate_limiter: RateLimiter::new(100, 60), // 100 requests per 60 seconds
            audit_log: AuditLog::new(10_000),        // Keep last 10 000 entries
            // ── Real-time communication managers ──────────────────────
            ws_manager: WebSocketManager::new(),
            sse_manager: SseManager::new(),
            // ── Entity stores (in-memory by default, DB-backed when pool is configured) ──
            kanban_boards: stores::new_store!("kanban_board"),
            notifications: stores::new_store!("notification"),
            notification_preferences: stores::new_store!("notification_preferences"),
            attachment_meta: stores::new_store!("attachment"),
            attachment_data: stores::new_store!("attachment_data"),
            quote_versions: stores::new_store!("quote_version"),
            learning_modules: stores::new_store!("learning_module"),
            opportunities: stores::new_store!("opportunity"),
            escalation_policies: stores::new_store!("escalation_policy"),
            training_matrix: stores::new_store!("training_matrix_entry"),
            knowledge_packs: stores::new_store!("knowledge_pack"),
            ingestion_jobs: stores::new_store!("ingestion_job"),
            ingestion_data: stores::new_store!("ingestion_data"),
            work_centers: stores::new_store!("work_center"),
            obeya_boards: stores::new_store!("obeya_board"),
            ctq_characteristics: stores::new_store!("ctq_characteristic"),
            ctq_records: stores::new_store!("ctq_record"),
            inventory_items: stores::new_store!("inventory_item"),
            stock_moves: stores::new_store!("stock_move"),
            warehouses: stores::new_store!("warehouse"),
            demand_entries: stores::new_store!("demand_entry"),
            supply_orders: stores::new_store!("supply_order"),
            mrp_runs: stores::new_store!("mrp_run"),
            tasks: stores::new_store!("task"),
            audit_log_entries: stores::new_store!("audit_log_entry"),
            production_cells: stores::new_store!("production_cell"),
            saved_views: stores::new_store!("saved_view"),
            work_packets: stores::new_store!("work_packet"),
            cost_builds: stores::new_store!("cost_build"),
            npi_conversions: stores::new_store!("npi_conversion"),
            kpi_definitions: stores::new_store!("kpi_definition"),
            kpi_values: stores::new_store!("kpi_value"),
            lsw_standards: stores::new_store!("lsw_standard"),
            lsw_audits: stores::new_store!("lsw_audit"),
            notification_triggers: stores::new_store!("notification_trigger"),
            standard_work_documents: stores::new_store!("standard_work_document"),
            standard_work_versions: stores::new_store!("standard_work_version"),
            state_machine_definitions: stores::new_store!("state_machine_definition"),
            state_machine_instances: stores::new_store!("state_machine_instance"),
            training_courses: stores::new_store!("training_course"),
            training_enrollments: stores::new_store!("training_enrollment"),
        }
    }

    /// Attach a database pool to the application state.
    ///
    /// When a pool is provided, this method swaps in-memory service implementations
    /// for database-backed implementations that use the given connection pool.
    /// Entity stores are also replaced with database-backed instances that persist
    /// mutations to the `entity_store` table.
    /// The email service is preserved as-is (no DB needed).
    pub fn with_db_pool(mut self, pool: Arc<PgPool>) -> Self {
        let p = (*pool).clone();

        // ── Swap domain services ────────────────────────────────────────
        self.accounts_service =
            Arc::new(DatabaseAccountsService::new(p.clone())) as Arc<dyn AccountsService>;
        self.contacts_service =
            Arc::new(DatabaseContactsService::new(p.clone())) as Arc<dyn ContactsService>;
        self.products_service =
            Arc::new(DatabaseProductsService::new(p.clone())) as Arc<dyn ProductsService>;
        self.tenants_service =
            Arc::new(DatabaseTenantsService::new(p.clone())) as Arc<dyn TenantsService>;
        self.finance_service =
            Arc::new(DatabaseFinanceService::new(p.clone())) as Arc<dyn FinanceService>;
        self.hr_service =
            Arc::new(DatabaseHrService::new(p.clone())) as Arc<dyn HrService>;
        self.maintenance_service =
            Arc::new(DatabaseMaintenanceService::new(p.clone())) as Arc<dyn MaintenanceService>;
        self.ops_service =
            Arc::new(DatabaseOperationsService::new(p.clone())) as Arc<dyn OperationsService>;
        self.production_service =
            Arc::new(DatabaseProductionService::new(p.clone())) as Arc<dyn ProductionService>;
        self.supply_chain_service =
            Arc::new(DatabaseSupplyChainService::new(p.clone())) as Arc<dyn SupplyChainService>;
        self.quality_service =
            Arc::new(DatabaseQualityService::new(p.clone())) as Arc<dyn QualityService>;
        self.search_service =
            Arc::new(DatabaseSearchService::new(p.clone())) as Arc<dyn SearchService>;
        self.notification_service =
            Arc::new(DatabaseNotificationService::new(p.clone())) as Arc<dyn NotificationService>;
        self.users_service =
            Arc::new(DatabaseUsersService::new(p.clone())) as Arc<dyn UsersService>;
        // Create the AI service first so it can be shared with the chatbot.
        let db_ai_service = Arc::new(DatabaseAiService::new(p.clone())) as Arc<dyn AiService>;
        self.ai_service = db_ai_service.clone();

        // Wire the chatbot with the AI service for context-aware responses.
        self.chatbot_service =
            Arc::new(DatabaseChatbotService::with_ai_service(
                p.clone(),
                sensei_services::ai::chatbot::ChatbotConfig::default(),
                db_ai_service,
            )) as Arc<dyn ChatbotService>;

        // ── Swap entity stores with database-backed instances ───────────
        use crate::db_stores::EntityStore;
        self.kanban_boards = EntityStore::with_pool("kanban_board", p.clone());
        self.notifications = EntityStore::with_pool("notification", p.clone());
        self.notification_preferences = EntityStore::with_pool("notification_preferences", p.clone());
        self.attachment_meta = EntityStore::with_pool("attachment", p.clone());
        self.attachment_data = EntityStore::with_pool("attachment_data", p.clone());
        self.quote_versions = EntityStore::with_pool("quote_version", p.clone());
        self.learning_modules = EntityStore::with_pool("learning_module", p.clone());
        self.opportunities = EntityStore::with_pool("opportunity", p.clone());
        self.escalation_policies = EntityStore::with_pool("escalation_policy", p.clone());
        self.training_matrix = EntityStore::with_pool("training_matrix_entry", p.clone());
        self.knowledge_packs = EntityStore::with_pool("knowledge_pack", p.clone());
        self.ingestion_jobs = EntityStore::with_pool("ingestion_job", p.clone());
        self.ingestion_data = EntityStore::with_pool("ingestion_data", p.clone());
        self.work_centers = EntityStore::with_pool("work_center", p.clone());
        self.obeya_boards = EntityStore::with_pool("obeya_board", p.clone());
        self.ctq_characteristics = EntityStore::with_pool("ctq_characteristic", p.clone());
        self.ctq_records = EntityStore::with_pool("ctq_record", p.clone());
        self.inventory_items = EntityStore::with_pool("inventory_item", p.clone());
        self.stock_moves = EntityStore::with_pool("stock_move", p.clone());
        self.warehouses = EntityStore::with_pool("warehouse", p.clone());
        self.demand_entries = EntityStore::with_pool("demand_entry", p.clone());
        self.supply_orders = EntityStore::with_pool("supply_order", p.clone());
        self.mrp_runs = EntityStore::with_pool("mrp_run", p.clone());
        self.tasks = EntityStore::with_pool("task", p.clone());
        self.audit_log_entries = EntityStore::with_pool("audit_log_entry", p.clone());
        self.production_cells = EntityStore::with_pool("production_cell", p.clone());
        self.saved_views = EntityStore::with_pool("saved_view", p.clone());
        self.work_packets = EntityStore::with_pool("work_packet", p.clone());
        self.cost_builds = EntityStore::with_pool("cost_build", p.clone());
        self.npi_conversions = EntityStore::with_pool("npi_conversion", p.clone());
        self.kpi_definitions = EntityStore::with_pool("kpi_definition", p.clone());
        self.kpi_values = EntityStore::with_pool("kpi_value", p.clone());
        self.lsw_standards = EntityStore::with_pool("lsw_standard", p.clone());
        self.lsw_audits = EntityStore::with_pool("lsw_audit", p.clone());
        self.notification_triggers = EntityStore::with_pool("notification_trigger", p.clone());
        self.standard_work_documents = EntityStore::with_pool("standard_work_document", p.clone());
        self.standard_work_versions = EntityStore::with_pool("standard_work_version", p.clone());
        self.state_machine_definitions = EntityStore::with_pool("state_machine_definition", p.clone());
        self.state_machine_instances = EntityStore::with_pool("state_machine_instance", p.clone());
        self.training_courses = EntityStore::with_pool("training_course", p.clone());
        self.training_enrollments = EntityStore::with_pool("training_enrollment", p);

        self.db_pool = Some(pool);
        self
    }

    /// Replace the event bus with a custom implementation.
    pub fn with_event_bus(mut self, event_bus: Arc<dyn EventBus>) -> Self {
        self.event_bus = event_bus;
        self
    }
}

/// Convenience function to create an event bus backed by NATS JetStream
/// when a NATS URL is configured, falling back to [`InMemoryEventBus`].
///
/// This is called from [`main`](crate::main) after loading the configuration.
pub async fn create_event_bus(config: &sensei_core::config::EventBusConfig) -> Arc<dyn EventBus> {
    use sensei_event_bus::NatsEventBus;

    if config.url.is_empty() {
        tracing::info!("NATS URL not configured, using in-memory event bus");
        return Arc::new(sensei_event_bus::InMemoryEventBus::new());
    }

    let bus = NatsEventBus::new("sensei");
    match bus.connect(&config.url).await {
        Ok(()) => {
            tracing::info!(url = %config.url, "Connected to NATS JetStream event bus");
            Arc::new(bus) as Arc<dyn EventBus>
        }
        Err(e) => {
            tracing::warn!(
                error = %e,
                url = %config.url,
                "Failed to connect to NATS, falling back to in-memory event bus"
            );
            Arc::new(sensei_event_bus::InMemoryEventBus::new()) as Arc<dyn EventBus>
        }
    }
}
