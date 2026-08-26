//! Application state shared across all request handlers.
//!
//! Uses Axum's [`State`](axum::extract::State) extractor to provide
//! shared services to route handlers.

use sensei_auth::jwt::JwtService;
use sensei_auth::oauth2::OAuth2Client;
use sensei_auth::rbac::RbacService;
use sensei_auth::refresh_tokens::RefreshTokenStore;
use sensei_core::config::AppConfig;
use sensei_core::types::{EntityId, TenantId, Timestamp};
use sensei_event_bus::EventBus;
use sensei_services::accounts::{
    AccountsService, DatabaseAccountsService, InMemoryAccountsService,
};
use sensei_services::ai::chatbot::{ChatbotService, InMemoryChatbotService};
use sensei_services::ai::DatabaseChatbotService;
use sensei_services::ai::{AiService, DatabaseAiService, InMemoryAiService};
use sensei_services::contacts::{
    ContactsService, DatabaseContactsService, InMemoryContactsService,
};
use sensei_services::export::excel::ExcelExportService;
use sensei_services::export::pdf::PdfExportService;
use sensei_services::finance::{DatabaseFinanceService, FinanceService, InMemoryFinanceService};
use sensei_services::hr::{DatabaseHrService, HrService, InMemoryHrService};
use sensei_services::maintenance::{
    DatabaseMaintenanceService, InMemoryMaintenanceService, MaintenanceService,
};
use sensei_services::notifications::service::{
    DatabaseNotificationService, InMemoryNotificationService, NotificationService,
};
use sensei_services::notifications::{EmailService, InMemoryEmailService, LettreEmailService};
use sensei_services::ops::search::{InMemorySearchService, SearchService};
use sensei_services::ops::{
    DatabaseOperationsService, InMemoryOperationsService, OperationsService,
};
use sensei_services::production::{
    DatabaseProductionService, InMemoryProductionService, ProductionService,
};
use sensei_services::products::{
    DatabaseProductsService, InMemoryProductsService, ProductsService,
};
use sensei_services::quality::{DatabaseQualityService, InMemoryQualityService, QualityService};
use sensei_services::storage::{
    FileStorageService, InMemoryStorageService, LocalStorageService, S3StorageService,
};
use sensei_services::supply_chain::{
    DatabaseSupplyChainService, InMemorySupplyChainService, SupplyChainService,
};
use sensei_services::tenants::{DatabaseTenantsService, InMemoryTenantsService, TenantsService};
use sensei_services::users::{DatabaseUsersService, UsersService};
use sqlx::PgPool;
use std::sync::Arc;

use dashmap::DashMap;
use uuid::Uuid;

use crate::attachment_repository::AttachmentRepository;
use crate::middleware::audit::AuditLog;
use crate::middleware::rate_limiter::RateLimiter;
use crate::middleware::session::SessionStore;
use crate::middleware::shared_auth_stores::{TokenBlacklist, TokenKind, TokenStore};
use crate::services::{sse::SseManager, ws::WebSocketManager};
use crate::stores;

/// Time-to-live for realtime connection tickets, in seconds.
pub const REALTIME_TICKET_TTL_SECS: u64 = 30;

/// A realtime connection ticket (WebSocket / SSE transport credential).
#[derive(Debug, Clone)]
pub struct RealtimeTicket {
    /// The one-time ticket value.
    pub ticket: Uuid,
    /// The user the ticket authenticates.
    pub user_id: EntityId,
    /// The tenant the user belongs to.
    pub tenant_id: TenantId,
    /// Transport scope: `"ws"` or `"sse"`.
    pub scope: String,
    /// When the ticket stops being valid.
    pub expires_at: Timestamp,
}

/// In-memory ticket record (dev mode, no pool).
#[derive(Debug, Clone)]
struct InMemoryRealtimeTicket {
    user_id: EntityId,
    tenant_id: TenantId,
    scope: String,
    expires_at: Timestamp,
    consumed_at: Option<Timestamp>,
}

/// One-time realtime connection ticket store.
///
/// Backed by the `realtime_tickets` table when a database pool is
/// configured, in-memory otherwise (development mode). Tickets are consumed
/// atomically on first use and are short-lived (see
/// [`REALTIME_TICKET_TTL_SECS`]), so a stolen ticket is usable only within
/// a narrow window and never twice.
#[derive(Clone)]
pub struct RealtimeTicketStore {
    tickets: Arc<DashMap<Uuid, InMemoryRealtimeTicket>>,
    pool: Option<Arc<PgPool>>,
}

impl RealtimeTicketStore {
    /// Create a dev-mode (in-memory) ticket store.
    pub fn new() -> Self {
        Self {
            tickets: Arc::new(DashMap::new()),
            pool: None,
        }
    }

    /// Create a ticket store backed by the given pool (or in-memory when
    /// `None`).
    pub fn with_pool(pool: Option<Arc<PgPool>>) -> Self {
        Self {
            tickets: Arc::new(DashMap::new()),
            pool,
        }
    }

    /// Mint a new one-time ticket for the given user/tenant/scope.
    pub async fn create(
        &self,
        user_id: EntityId,
        tenant_id: TenantId,
        scope: &str,
    ) -> Result<RealtimeTicket, String> {
        let expires_at =
            chrono::Utc::now() + chrono::Duration::seconds(REALTIME_TICKET_TTL_SECS as i64);

        match &self.pool {
            Some(pool) => {
                let ticket = Uuid::new_v4();
                sqlx::query(
                    "INSERT INTO realtime_tickets (ticket, user_id, tenant_id, scope, expires_at) \
                     VALUES ($1, $2, $3, $4, $5)",
                )
                .bind(ticket)
                .bind(user_id)
                .bind(tenant_id)
                .bind(scope)
                .bind(expires_at)
                .execute(&**pool)
                .await
                .map_err(|e| format!("Failed to create realtime ticket: {e}"))?;
                Ok(RealtimeTicket {
                    ticket,
                    user_id,
                    tenant_id,
                    scope: scope.to_string(),
                    expires_at,
                })
            }
            None => {
                self.purge_expired_in_memory();
                let ticket = Uuid::new_v4();
                self.tickets.insert(
                    ticket,
                    InMemoryRealtimeTicket {
                        user_id,
                        tenant_id,
                        scope: scope.to_string(),
                        expires_at,
                        consumed_at: None,
                    },
                );
                Ok(RealtimeTicket {
                    ticket,
                    user_id,
                    tenant_id,
                    scope: scope.to_string(),
                    expires_at,
                })
            }
        }
    }

    /// Atomically consume a ticket for the given scope.
    ///
    /// Returns the ticket's `(user_id, tenant_id)` on success, `None` when
    /// the ticket is unknown, already consumed, expired, or scoped to the
    /// other transport. A ticket can be used at most once.
    pub async fn consume(
        &self,
        ticket: Uuid,
        scope: &str,
    ) -> Result<Option<(EntityId, TenantId)>, String> {
        match &self.pool {
            Some(pool) => sqlx::query_as::<_, (Uuid, Uuid)>(
                "UPDATE realtime_tickets \
                     SET consumed_at = NOW() \
                     WHERE ticket = $1 AND scope = $2 \
                       AND consumed_at IS NULL AND expires_at > NOW() \
                     RETURNING user_id, tenant_id",
            )
            .bind(ticket)
            .bind(scope)
            .fetch_optional(&**pool)
            .await
            .map_err(|e| format!("Failed to consume realtime ticket: {e}")),
            None => {
                self.purge_expired_in_memory();
                let Some(mut entry) = self.tickets.get_mut(&ticket) else {
                    return Ok(None);
                };
                let stored = entry.value_mut();
                if stored.scope != scope
                    || stored.consumed_at.is_some()
                    || stored.expires_at <= chrono::Utc::now()
                {
                    return Ok(None);
                }
                stored.consumed_at = Some(chrono::Utc::now());
                Ok(Some((stored.user_id, stored.tenant_id)))
            }
        }
    }

    /// Drop expired / already-consumed in-memory tickets (dev mode).
    fn purge_expired_in_memory(&self) {
        let now = chrono::Utc::now();
        self.tickets
            .retain(|_, t| t.expires_at > now && t.consumed_at.is_none());
    }
}

impl Default for RealtimeTicketStore {
    fn default() -> Self {
        Self::new()
    }
}

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

/// Temporary helper to collect PM store references and build search providers.
///
/// Used to avoid the chicken-and-egg problem where stores need to be created
/// before the search service (which references them), but the search service
/// is assigned to the state struct that also owns the stores.
struct PmStores<'a> {
    tasks: &'a crate::stores::TaskStore,
    kanban_boards: &'a crate::stores::KanbanBoardStore,
    obeya_boards: &'a crate::stores::ObeyaBoardStore,
    knowledge_packs: &'a crate::stores::KnowledgePackStore,
    training_courses: &'a crate::stores::TrainingCourseStore,
    work_centers: &'a crate::stores::WorkCenterStore,
    state_machine_instances: &'a crate::stores::StateMachineInstanceStore,
    production_cells: &'a crate::stores::ProductionCellStore,
    standard_work_documents: &'a crate::stores::StandardWorkStore,
    lsw_standards: &'a crate::stores::LswStandardStore,
    kpi_definitions: &'a crate::stores::KpiDefinitionStore,
    notification_triggers: &'a crate::stores::NotificationTriggerStore,
}

impl<'a> PmStores<'a> {
    /// Build [`SearchableEntityProvider`] instances for all PM stores.
    fn build_providers(
        &self,
    ) -> Vec<Arc<dyn sensei_services::ops::search::SearchableEntityProvider>> {
        use crate::search_providers::*;

        vec![
            task_search_provider(self.tasks.clone()),
            kanban_board_search_provider(self.kanban_boards.clone()),
            obeya_board_search_provider(self.obeya_boards.clone()),
            knowledge_pack_search_provider(self.knowledge_packs.clone()),
            training_course_search_provider(self.training_courses.clone()),
            work_center_search_provider(self.work_centers.clone()),
            state_machine_instance_search_provider(self.state_machine_instances.clone()),
            production_cell_search_provider(self.production_cells.clone()),
            standard_work_search_provider(self.standard_work_documents.clone()),
            lsw_standard_search_provider(self.lsw_standards.clone()),
            kpi_definition_search_provider(self.kpi_definitions.clone()),
            notification_trigger_search_provider(self.notification_triggers.clone()),
        ]
    }
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
    ///
    /// Always an [`InMemorySearchService`] (in both in-memory and DB mode):
    /// it searches the shared entity stores and domain services, which
    /// become DB-backed in DB mode, so search stays consistent with the
    /// data the routes serve.
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
    pub token_blacklist: TokenBlacklist,
    /// Password reset tokens.
    pub password_reset_store: TokenStore,
    /// Email verification tokens.
    pub email_verification_store: TokenStore,
    /// Rate limiter for API endpoints.
    pub rate_limiter: RateLimiter,
    /// Audit log for recording state-changing requests.
    pub audit_log: AuditLog,
    /// Session fingerprint store for binding tokens to clients.
    ///
    /// Auth routes register fingerprints here on login/refresh; the session
    /// binding middleware verifies them on every authenticated request.
    pub session_store: SessionStore,
    /// Refresh-token store with rotation and reuse detection.
    ///
    /// Backed by PostgreSQL when a pool is configured, in-memory otherwise.
    pub refresh_token_store: Arc<RefreshTokenStore>,
    /// OAuth2 client (present when `config.auth.oauth2` is configured).
    pub oauth2_client: Option<Arc<OAuth2Client>>,

    // ── Real-time communication managers ─────────────────────────────
    /// WebSocket connection manager for room-based pub/sub.
    pub ws_manager: WebSocketManager,
    /// Server-Sent Events manager for one-way event streaming.
    pub sse_manager: SseManager,
    /// One-time realtime connection tickets (WS/SSE auth).
    pub realtime_tickets: RealtimeTicketStore,

    // ── In-memory stores (temporary; replaced by domain services later) ─
    /// Kanban boards entity store.
    pub kanban_boards: stores::KanbanBoardStore,
    /// Notifications entity store.
    pub notifications: stores::NotificationStore,
    /// Notification preferences entity store.
    pub notification_preferences: stores::NotificationPreferencesStore,
    /// Attachment metadata: typed PostgreSQL repository (the generic
    /// EntityStore cache is no longer the authoritative store for
    /// attachments).
    pub attachment_repo: AttachmentRepository,
    /// Attachment metadata entity store (legacy path, retained during
    /// migration only).
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
        let trusted_proxies = config.security.trusted_proxies.clone();
        let jwt_service = JwtService::new(
            &config.auth.jwt_secret,
            &config.auth.jwt_issuer,
            &config.auth.jwt_audience,
            config.auth.access_token_expiry_minutes,
            config.auth.refresh_token_expiry_days,
        );
        let event_bus: Arc<dyn EventBus> = Arc::new(sensei_event_bus::InMemoryEventBus::new());

        // Initialize email service — use SMTP if credentials are provided,
        // otherwise fall back to in-memory for development/testing.
        let email_service: Arc<dyn EmailService> = if !config.email.smtp_username.is_empty() {
            Arc::new(LettreEmailService::new(&config.email))
        } else {
            Arc::new(InMemoryEmailService::new())
        };

        // Initialize file storage service based on configuration. An unknown
        // backend is a configuration error (fail fast); an S3 initialization
        // failure is fatal in production (silently switching to in-memory
        // storage would lose uploaded files), and a development-only
        // degradation otherwise.
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
                        if config.environment.is_prod() {
                            panic!(
                                "Failed to initialize S3 storage: {e} — object storage is \
                                 required in production (the in-memory storage service is \
                                 development-only and loses files on restart)"
                            );
                        }
                        tracing::warn!(
                            error = %e,
                            "Failed to initialize S3 storage, using in-memory storage (development mode only)"
                        );
                        Arc::new(InMemoryStorageService::new()) as Arc<dyn FileStorageService>
                    }
                }
            }
            "local" => Arc::new(LocalStorageService::new(&config.storage.local_path))
                as Arc<dyn FileStorageService>,
            other => {
                panic!(
                    "Unknown storage backend '{other}' — valid backends are 's3' and 'local'. \
                     Check the STORAGE_BACKEND configuration."
                );
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

        // ── Refresh-token store (in-memory until a DB pool is attached) ──
        // `new(None)` spawns the expired-token cleanup task itself.
        let refresh_token_store = Arc::new(RefreshTokenStore::new(None));

        // ── OAuth2 client (optional) ─────────────────────────────────────
        let oauth2_client = match config.auth.oauth2.as_ref() {
            Some(provider_config) => match OAuth2Client::from_config(provider_config) {
                Ok(client) => Some(Arc::new(client)),
                Err(e) => {
                    tracing::warn!(
                        error = %e,
                        provider = %provider_config.provider,
                        "Failed to build OAuth2 client; OAuth2 login disabled"
                    );
                    None
                }
            },
            None => None,
        };

        // ── Create in-memory entity stores (referenced by both the search service and routes) ──
        let kanban_boards = stores::new_store!("kanban_board");
        let notifications = stores::new_store!("notification");
        let notification_preferences = stores::new_store!("notification_preferences");
        let attachment_meta = stores::new_store!("attachment");
        let attachment_data = stores::new_store!("attachment_data");
        let quote_versions = stores::new_store!("quote_version");
        let learning_modules = stores::new_store!("learning_module");
        let opportunities = stores::new_store!("opportunity");
        let escalation_policies = stores::new_store!("escalation_policy");
        let training_matrix = stores::new_store!("training_matrix_entry");
        let knowledge_packs = stores::new_store!("knowledge_pack");
        let ingestion_jobs = stores::new_store!("ingestion_job");
        let ingestion_data = stores::new_store!("ingestion_data");
        let work_centers = stores::new_store!("work_center");
        let obeya_boards = stores::new_store!("obeya_board");
        let ctq_characteristics = stores::new_store!("ctq_characteristic");
        let ctq_records = stores::new_store!("ctq_record");
        let inventory_items = stores::new_store!("inventory_item");
        let stock_moves = stores::new_store!("stock_move");
        let warehouses = stores::new_store!("warehouse");
        let demand_entries = stores::new_store!("demand_entry");
        let supply_orders = stores::new_store!("supply_order");
        let mrp_runs = stores::new_store!("mrp_run");
        let tasks = stores::new_store!("task");
        let audit_log_entries = stores::new_store!("audit_log_entry");
        let production_cells = stores::new_store!("production_cell");
        let saved_views = stores::new_store!("saved_view");
        let work_packets = stores::new_store!("work_packet");
        let cost_builds = stores::new_store!("cost_build");
        let npi_conversions = stores::new_store!("npi_conversion");
        let kpi_definitions = stores::new_store!("kpi_definition");
        let kpi_values = stores::new_store!("kpi_value");
        let lsw_standards = stores::new_store!("lsw_standard");
        let lsw_audits = stores::new_store!("lsw_audit");
        let notification_triggers = stores::new_store!("notification_trigger");
        let standard_work_documents = stores::new_store!("standard_work_document");
        let standard_work_versions = stores::new_store!("standard_work_version");
        let state_machine_definitions = stores::new_store!("state_machine_definition");
        let state_machine_instances = stores::new_store!("state_machine_instance");
        let training_courses = stores::new_store!("training_course");
        let training_enrollments = stores::new_store!("training_enrollment");

        // Build a temporary AppState-like struct to pass to the macro.
        // We use a temporary block to create a scope for the references.
        let pm_stores = PmStores {
            tasks: &tasks,
            kanban_boards: &kanban_boards,
            obeya_boards: &obeya_boards,
            knowledge_packs: &knowledge_packs,
            training_courses: &training_courses,
            work_centers: &work_centers,
            state_machine_instances: &state_machine_instances,
            production_cells: &production_cells,
            standard_work_documents: &standard_work_documents,
            lsw_standards: &lsw_standards,
            kpi_definitions: &kpi_definitions,
            notification_triggers: &notification_triggers,
        };

        let entity_providers = pm_stores.build_providers();

        let search_service: Arc<dyn SearchService> = Arc::new(
            InMemorySearchService::new(
                accounts_service.clone(),
                contacts_service.clone(),
                products_service.clone(),
                users_service.clone(),
            )
            .with_entity_providers(entity_providers),
        ) as Arc<dyn SearchService>;

        Self {
            config: Arc::new(config),
            jwt_service: Arc::new(jwt_service),
            rbac_service: Arc::new(RbacService::new()),
            email_service,
            db_pool: None,
            search_service,
            notification_service: Arc::new(InMemoryNotificationService::new())
                as Arc<dyn NotificationService>,
            ai_service: Arc::new(InMemoryAiService::new(None)) as Arc<dyn AiService>,
            chatbot_service: Arc::new(InMemoryChatbotService::new(
                sensei_services::ai::chatbot::ChatbotConfig::default(),
            )) as Arc<dyn ChatbotService>,
            finance_service: Arc::new(InMemoryFinanceService::new(Some(event_bus.clone())))
                as Arc<dyn FinanceService>,
            hr_service: Arc::new(InMemoryHrService::new(Some(event_bus.clone())))
                as Arc<dyn HrService>,
            maintenance_service: Arc::new(InMemoryMaintenanceService::new(Some(event_bus.clone())))
                as Arc<dyn MaintenanceService>,
            ops_service: Arc::new(InMemoryOperationsService::new(Some(event_bus.clone())))
                as Arc<dyn OperationsService>,
            production_service: Arc::new(InMemoryProductionService::new(Some(event_bus.clone())))
                as Arc<dyn ProductionService>,
            supply_chain_service: Arc::new(InMemorySupplyChainService::new(Some(event_bus.clone())))
                as Arc<dyn SupplyChainService>,
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
            token_blacklist: TokenBlacklist::new(None),
            password_reset_store: TokenStore::new(TokenKind::PasswordReset, None),
            email_verification_store: TokenStore::new(TokenKind::EmailVerification, None),
            rate_limiter: RateLimiter::with_trusted_proxies(100, 60, trusted_proxies), // 100 requests per 60s; XFF only from trusted proxies

            audit_log: AuditLog::new(10_000), // Keep last 10 000 entries
            session_store: SessionStore::new(86_400), // 24 hour fingerprint TTL
            refresh_token_store,
            oauth2_client,
            // ── Real-time communication managers ──────────────────────
            ws_manager: WebSocketManager::new(),
            sse_manager: SseManager::new(),
            realtime_tickets: RealtimeTicketStore::new(),
            // ── Entity stores (in-memory by default, DB-backed when pool is configured) ──
            kanban_boards,
            notifications,
            notification_preferences,
            attachment_repo: AttachmentRepository::new(None),
            attachment_meta,
            attachment_data,
            quote_versions,
            learning_modules,
            opportunities,
            escalation_policies,
            training_matrix,
            knowledge_packs,
            ingestion_jobs,
            ingestion_data,
            work_centers,
            obeya_boards,
            ctq_characteristics,
            ctq_records,
            inventory_items,
            stock_moves,
            warehouses,
            demand_entries,
            supply_orders,
            mrp_runs,
            tasks,
            audit_log_entries,
            production_cells,
            saved_views,
            work_packets,
            cost_builds,
            npi_conversions,
            kpi_definitions,
            kpi_values,
            lsw_standards,
            lsw_audits,
            notification_triggers,
            standard_work_documents,
            standard_work_versions,
            state_machine_definitions,
            state_machine_instances,
            training_courses,
            training_enrollments,
        }
    }

    /// Attach a database pool to the application state.
    ///
    /// When a pool is provided, this method swaps in-memory service implementations
    /// for database-backed implementations that use the given connection pool.
    /// Entity stores are also replaced with database-backed instances that persist
    /// mutations to the `entity_store` table.
    /// The email service is preserved as-is (no DB needed).
    ///
    /// The search service is swapped for the SQL-backed
    /// [`DatabaseSearchService`]: the [`InMemorySearchService`] captured
    /// `Arc`s to the *original* in-memory account/contact/product/user
    /// services at construction, so swapping the state fields alone would
    /// leave DB-mode search pointing at stale in-memory instances.
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
        self.hr_service = Arc::new(DatabaseHrService::new(p.clone())) as Arc<dyn HrService>;
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
        // ── Search unification ──────────────────────────────────────────
        // The InMemorySearchService is kept in BOTH modes: it searches the
        // shared entity stores and the domain services above (which become
        // DB-backed in this mode), so search results stay consistent with
        // the data the routes serve. No DatabaseSearchService swap here.
        self.notification_service =
            Arc::new(DatabaseNotificationService::new(p.clone())) as Arc<dyn NotificationService>;
        self.users_service =
            Arc::new(DatabaseUsersService::new(p.clone())) as Arc<dyn UsersService>;
        // Create the AI service first so it can be shared with the chatbot.
        let db_ai_service = Arc::new(DatabaseAiService::new(p.clone())) as Arc<dyn AiService>;
        self.ai_service = db_ai_service.clone();

        // Wire the chatbot with the AI service for context-aware responses.
        self.chatbot_service = Arc::new(DatabaseChatbotService::with_ai_service(
            p.clone(),
            sensei_services::ai::chatbot::ChatbotConfig::default(),
            db_ai_service,
        )) as Arc<dyn ChatbotService>;

        // ── Swap entity stores with database-backed instances ───────────
        use crate::db_stores::EntityStore;
        self.kanban_boards = EntityStore::with_pool("kanban_board", p.clone());
        self.notifications = EntityStore::with_pool("notification", p.clone());
        self.notification_preferences =
            EntityStore::with_pool("notification_preferences", p.clone());
        self.attachment_meta = EntityStore::with_pool("attachment", p.clone());
        self.attachment_repo = self.attachment_repo.attach_pool(p.clone());
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
        self.state_machine_definitions =
            EntityStore::with_pool("state_machine_definition", p.clone());
        self.state_machine_instances = EntityStore::with_pool("state_machine_instance", p.clone());
        self.training_courses = EntityStore::with_pool("training_course", p.clone());
        self.training_enrollments = EntityStore::with_pool("training_enrollment", p.clone());

        // Refresh tokens persist to the database when a pool is available.
        self.refresh_token_store = Arc::new(RefreshTokenStore::new(Some(p.clone())));

        // Realtime tickets persist to the database when a pool is available.
        self.realtime_tickets = RealtimeTicketStore::with_pool(Some(Arc::new(p.clone())));

        // Session fingerprints are shared across replicas (multi-replica
        // logout/session enforcement).
        self.session_store = self.session_store.attach_pool(p.clone());

        // Rate limiting becomes a SHARED sliding-window counter (one
        // effective limit across all replicas).
        self.rate_limiter = self.rate_limiter.with_shared_pool(p.clone());

        // Access-token revocation + one-time tokens become shared tables.
        self.token_blacklist = TokenBlacklist::new(Some(p.clone()));
        self.password_reset_store = TokenStore::new(TokenKind::PasswordReset, Some(p.clone()));
        self.email_verification_store =
            TokenStore::new(TokenKind::EmailVerification, Some(p.clone()));

        // Durable audit logging: writes go to PostgreSQL instead of the
        // dev-mode ring buffer.
        self.audit_log = self.audit_log.with_pool(Arc::new(p.clone()));

        // ── Search: swap to the SQL-backed implementation ───────────────
        // The in-memory search service captured Arcs to the ORIGINAL
        // in-memory account/contact/product/user services at construction;
        // swapping the state fields alone would leave DB-mode search
        // pointing at stale in-memory instances. Construct the DB search
        // AFTER the production repositories are in place.
        self.search_service = Arc::new(crate::db_search_service::DatabaseSearchService::new(
            p.clone(),
        )) as Arc<dyn sensei_services::ops::search::SearchService>;

        self.db_pool = Some(pool);
        self
    }

    /// Replace the event bus with a custom implementation.
    ///
    /// The WebSocket manager is re-attached so cross-replica fanout uses
    /// the new bus.
    pub fn with_event_bus(mut self, event_bus: Arc<dyn EventBus>) -> Self {
        self.ws_manager.set_event_bus(event_bus.clone());
        self.event_bus = event_bus;
        self
    }

    /// Subscribe every DB-backed entity store to cross-replica cache
    /// invalidation: a write committed by ANY replica evicts the affected
    /// rows from this replica's cache immediately (core NATS pub/sub).
    pub fn attach_entity_store_buses(&self, bus: Arc<dyn EventBus>) {
        macro_rules! attach {
            ($($field:ident),* $(,)?) => {
                $( self.$field.attach_bus(bus.clone()); )*
            };
        }
        attach!(
            kanban_boards,
            notifications,
            notification_preferences,
            attachment_meta,
            attachment_data,
            quote_versions,
            learning_modules,
            opportunities,
            escalation_policies,
            training_matrix,
            knowledge_packs,
            ingestion_jobs,
            ingestion_data,
            work_centers,
            obeya_boards,
            ctq_characteristics,
            ctq_records,
            inventory_items,
            stock_moves,
            warehouses,
            demand_entries,
            supply_orders,
            mrp_runs,
            tasks,
            audit_log_entries,
            production_cells,
            saved_views,
            work_packets,
            cost_builds,
            npi_conversions,
            kpi_definitions,
            kpi_values,
            lsw_standards,
            lsw_audits,
            notification_triggers,
            standard_work_documents,
            standard_work_versions,
            state_machine_definitions,
            state_machine_instances,
            training_courses,
            training_enrollments,
        );
    }
}

/// Convenience function to create an event bus backed by NATS JetStream
/// when a NATS URL is configured.
///
/// The [`NatsEventBus`] is constructed via [`NatsEventBus::from_config`] so
/// the stream name and reconnection limits come from the configuration.
///
/// NATS is the production event backbone: in a production environment a
/// missing or unreachable broker is a fatal configuration error, never a
/// silent degradation to the in-memory bus (which is not durable and does
/// not survive restarts). In development the in-memory bus is the explicit
/// choice when `NATS_URL` is empty.
///
/// This is called from [`main`](crate::main) after loading the configuration.
pub async fn create_event_bus(
    config: &sensei_core::config::EventBusConfig,
    environment: &sensei_core::config::Environment,
) -> Arc<dyn EventBus> {
    use sensei_event_bus::NatsEventBus;

    if config.url.is_empty() {
        if environment.is_prod() {
            panic!("NATS_URL is not configured — NATS JetStream is required in production (the in-memory event bus is development-only and non-durable)");
        }
        tracing::info!("NATS URL not configured, using in-memory event bus (development mode)");
        return Arc::new(sensei_event_bus::InMemoryEventBus::new());
    }

    let bus = NatsEventBus::from_config(config);
    match bus.connect(&config.url).await {
        Ok(()) => {
            tracing::info!(url = %config.url, "Connected to NATS JetStream event bus");
            Arc::new(bus) as Arc<dyn EventBus>
        }
        Err(e) => {
            if environment.is_prod() {
                panic!(
                    "Failed to connect to NATS JetStream at {url}: {e} — the event bus is \
                     required in production (the in-memory bus is development-only and \
                     non-durable)",
                    url = config.url
                );
            }
            tracing::warn!(
                error = %e,
                url = %config.url,
                "Failed to connect to NATS, using in-memory event bus (development mode only)"
            );
            Arc::new(sensei_event_bus::InMemoryEventBus::new()) as Arc<dyn EventBus>
        }
    }
}
