//! Operations / Continuous Improvement domain services.
//!
//! Provides Andon (real-time alert) management, continuous improvement
//! projects, A3 problem-solving reports, risk management, and
//! full-text search across entities, with in-memory storage for
//! development and testing.
//!
//! # Architecture
//!
//! The operations service layer abstracts lean / continuous improvement
//! operations behind a trait, enabling the system to swap in real
//! database-backed implementations while keeping the in-memory
//! implementation for unit tests and demos.

pub mod andon_events;
mod database;
pub mod search;
pub use database::DatabaseOperationsService;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sensei_core::domain::events::{
    A3ClosedEvent, A3CreatedEvent, AndonAcknowledgedEvent, AndonCreatedEvent, AndonResolvedEvent,
    DomainEvent, ProjectCreatedEvent, RiskCreatedEvent, RiskMitigatedEvent,
};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_event_bus::bus::EventBus;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

/// An Andon signal raised on the shop floor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Andon {
    pub id: Uuid,
    pub tenant_id: Uuid,
    /// Explicit operational scope (fifteenth audit): the site the signal
    /// belongs to — never implicitly company-wide.
    #[serde(default)]
    pub site_id: Option<Uuid>,
    pub andon_number: String,
    pub work_center_id: Uuid,
    pub issue_type: String, // quality, safety, maintenance, material, other
    pub severity: String,   // low, medium, high, critical
    pub description: String,
    pub status: String, // active, acknowledged, resolved, closed
    pub raised_by: Uuid,
    pub acknowledged_by: Option<Uuid>,
    pub resolved_by: Option<Uuid>,
    pub resolution: Option<String>,
    pub response_time_seconds: Option<i64>,
    pub resolution_time_seconds: Option<i64>,
    pub created_at: DateTime<Utc>,
    pub acknowledged_at: Option<DateTime<Utc>>,
    pub resolved_at: Option<DateTime<Utc>>,
    /// Restart authorization for critical-safety Andons (hard rule: the
    /// line stays stopped until an authorized restart exists).
    #[serde(default)]
    pub restart_authorized_by: Option<Uuid>,
    #[serde(default)]
    pub restart_authorized_at: Option<DateTime<Utc>>,
    /// When the abnormal condition was OBSERVED (item 47): detection
    /// latency = observed_at - raised_at, measured honestly. The raised_at
    /// is created_at.
    #[serde(default)]
    pub abnormal_condition_observed_at: Option<DateTime<Utc>>,
    /// When customer/process risk was CONTAINED (item 48) — distinct from
    /// resolved_at (root cause fixed).
    #[serde(default)]
    pub contained_at: Option<DateTime<Utc>>,
    #[serde(default)]
    pub contained_by: Option<Uuid>,
    #[serde(default)]
    pub contained_note: Option<String>,
    /// Item 41: escalation to tier review is a REAL state.
    #[serde(default)]
    pub escalated: bool,
    #[serde(default)]
    pub escalated_at: Option<DateTime<Utc>>,
    /// Client command key (seventeenth audit item 11): set when the andon
    /// was raised with an Idempotency-Key — retries replay the original.
    #[serde(default)]
    pub request_key: Option<String>,
}

/// A continuous improvement or kaizen project.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub project_code: String,
    pub name: String,
    pub description: String,
    pub category: String, // kaizen, six_sigma, capital, continuous_improvement
    pub status: String,   // not_started, in_progress, completed, on_hold, cancelled
    pub priority: String, // low, medium, high, critical
    pub owner_id: Uuid,
    pub team_members: Vec<Uuid>,
    pub planned_start: Option<DateTime<Utc>>,
    pub planned_end: Option<DateTime<Utc>>,
    pub actual_start: Option<DateTime<Utc>>,
    pub actual_end: Option<DateTime<Utc>>,
    pub budget: Option<rust_decimal::Decimal>,
    pub savings_realized: Option<rust_decimal::Decimal>,
    pub created_at: DateTime<Utc>,
}

/// An A3 problem-solving report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct A3 {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub a3_number: String,
    pub title: String,
    pub background: String,
    pub current_state: String,
    pub goal: String,
    pub root_cause_analysis: String,
    pub countermeasures: String,
    pub check_plan: String,
    pub follow_up: String,
    pub status: String, // draft, active, implemented, verified, closed
    /// Problem-solving discipline (e.g. standard, safety, quality).
    #[serde(default)]
    pub a3_type: String,
    /// Severity of the problem addressed (e.g. low, medium, high, critical).
    #[serde(default)]
    pub severity: String,
    /// Optimistic-concurrency version (commands require expected_version).
    #[serde(default)]
    pub version: u64,
    /// Structured observed conditions (OBSERVATION, with source evidence).
    #[serde(default)]
    pub observed_conditions: Vec<serde_json::Value>,
    /// Metric baselines (target/actual/trend measurements).
    #[serde(default)]
    pub metric_baselines: Vec<serde_json::Value>,
    /// Evidence references supporting every factual claim in the case.
    #[serde(default)]
    pub evidence_refs: Vec<String>,
    /// Cause hypotheses (never asserted as fact without verification).
    #[serde(default)]
    pub cause_hypotheses: Vec<serde_json::Value>,
    /// Controlled experiments.
    #[serde(default)]
    pub experiments: Vec<serde_json::Value>,
    /// Countermeasure verifications (metric observed after the change).
    #[serde(default)]
    pub verifications: Vec<serde_json::Value>,
    /// Standardization actions (standard work / control plan updates).
    #[serde(default)]
    pub standardizations: Vec<serde_json::Value>,
    /// Organizational learnings.
    #[serde(default)]
    pub learnings: Vec<serde_json::Value>,
    pub owner_id: Uuid,
    pub created_at: DateTime<Utc>,
    pub closed_at: Option<DateTime<Utc>>,
}

/// A risk identified and tracked in the system.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Risk {
    pub id: Uuid,
    pub tenant_id: Uuid,
    pub risk_number: String,
    pub title: String,
    pub description: String,
    pub category: String, // strategic, operational, financial, compliance, safety, quality
    pub likelihood: String, // rare, unlikely, possible, likely, almost_certain
    pub impact: String,   // insignificant, minor, moderate, major, catastrophic
    pub risk_score: i32,  // likelihood × impact (1-25)
    pub mitigation: String,
    pub contingency: String,
    pub status: String, // identified, assessed, mitigated, monitored, closed
    pub owner_id: Uuid,
    pub created_at: DateTime<Utc>,
    pub mitigated_at: Option<DateTime<Utc>>,
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Operations service trait covering Andon, projects, A3 reports, and risks.
#[async_trait]
pub trait OperationsService: Send + Sync {
    // ── Andon ───────────────────────────────────────────────────────────
    /// Raise a new Andon signal.
    async fn raise_andon(&self, tenant_id: Uuid, andon: Andon) -> Result<Andon>;

    /// Request-level idempotent raise (seventeenth audit item 11): the
    /// client's command key is generated once per raise; a retry after a
    /// dropped connection REPLAYS the original andon instead of creating
    /// a duplicate. `request_key = None` keeps the plain behavior.
    async fn raise_andon_idempotent(
        &self,
        tenant_id: Uuid,
        andon: Andon,
        request_key: Option<String>,
    ) -> Result<Andon>;
    /// Acknowledge an Andon signal.
    async fn acknowledge_andon(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        acknowledged_by: Uuid,
    ) -> Result<Andon>;
    /// Escalate an Andon to tier review (item 41): a real state
    /// transition through the same command path.
    async fn escalate_andon(&self, tenant_id: Uuid, id: Uuid, escalated_by: Uuid) -> Result<Andon>;
    /// Resolve an Andon signal with a resolution description.
    async fn resolve_andon(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        resolved_by: Uuid,
        resolution: &str,
    ) -> Result<Andon>;
    /// Get an Andon signal by ID.
    async fn get_andon(&self, tenant_id: Uuid, id: Uuid) -> Result<Andon>;
    /// Authorize the restart of a line after a critical-safety Andon (hard
    /// rule: resolution requires this authorization).
    async fn authorize_restart(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        authorized_by: Uuid,
    ) -> Result<Andon>;
    /// List Andon signals with optional status and work center filters, with pagination.
    async fn list_andons(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        work_center_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Andon>>;

    /// Scope-intersected listing (seventeenth audit item 4): `scope_site`
    /// is the caller's authorized site — when set, ONLY that site's
    /// andons are returned. The unscoped variant must never be exposed
    /// for ordinary callers.
    async fn list_andons_scoped(
        &self,
        tenant_id: Uuid,
        scope_site: Option<Uuid>,
        status: Option<&str>,
        work_center_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Andon>>;

    // ── Projects ────────────────────────────────────────────────────────
    /// Create a new improvement project.
    async fn create_project(&self, tenant_id: Uuid, project: Project) -> Result<Project>;
    /// Get a project by ID.
    async fn get_project(&self, tenant_id: Uuid, id: Uuid) -> Result<Project>;
    /// List projects with optional status and category filters, with pagination.
    async fn list_projects(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        category: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Project>>;
    /// Complete a project and record realized savings.
    async fn complete_project(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        savings_realized: f64,
    ) -> Result<Project>;

    // ── A3 ──────────────────────────────────────────────────────────────
    /// Create a new A3 report.
    async fn create_a3(&self, tenant_id: Uuid, a3: A3) -> Result<A3>;
    /// Get an A3 report by ID.
    async fn get_a3(&self, tenant_id: Uuid, id: Uuid) -> Result<A3>;
    /// List A3 reports with optional status filter, with pagination.
    async fn list_a3s(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<A3>>;
    /// Close an A3 report.
    async fn close_a3(&self, tenant_id: Uuid, id: Uuid) -> Result<A3>;

    // ── Risk ────────────────────────────────────────────────────────────
    /// Create a new risk record.
    async fn create_risk(&self, tenant_id: Uuid, risk: Risk) -> Result<Risk>;
    /// Get a risk by ID.
    async fn get_risk(&self, tenant_id: Uuid, id: Uuid) -> Result<Risk>;
    /// List risks with optional status and category filters, with pagination.
    async fn list_risks(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        category: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Risk>>;
    /// Mitigate a risk (move to mitigated status).
    async fn mitigate_risk(&self, tenant_id: Uuid, id: Uuid) -> Result<Risk>;
    /// Update an Andon signal.
    async fn update_andon(&self, tenant_id: Uuid, id: Uuid, andon: Andon) -> Result<Andon>;
    /// Delete an Andon signal.
    async fn void_andon(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        actor_id: Uuid,
        reason: &str,
    ) -> Result<Andon>;
    /// Update a project.
    async fn update_project(&self, tenant_id: Uuid, id: Uuid, project: Project) -> Result<Project>;
    /// Delete a project.
    async fn delete_project(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Update an A3 report.
    async fn update_a3(&self, tenant_id: Uuid, id: Uuid, a3: A3) -> Result<A3>;
    /// Delete an A3 report.
    async fn delete_a3(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
    /// Update a risk.
    async fn update_risk(&self, tenant_id: Uuid, id: Uuid, risk: Risk) -> Result<Risk>;
    /// Delete a risk.
    async fn delete_risk(&self, tenant_id: Uuid, id: Uuid) -> Result<()>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of the [`OperationsService`] trait.
///
/// Stores Andon signals, projects, A3 reports, and risks in memory using
/// `HashMap`s. Suitable for development, testing, and demo environments.
pub struct InMemoryOperationsService {
    andons: RwLock<HashMap<Uuid, Andon>>,
    projects: RwLock<HashMap<Uuid, Project>>,
    a3s: RwLock<HashMap<Uuid, A3>>,
    risks: RwLock<HashMap<Uuid, Risk>>,
    andon_counter: RwLock<u64>,
    project_counter: RwLock<u64>,
    a3_counter: RwLock<u64>,
    risk_counter: RwLock<u64>,
    event_bus: Option<Arc<dyn EventBus>>,
}

impl InMemoryOperationsService {
    /// Create a new empty [`InMemoryOperationsService`].
    pub fn new(event_bus: Option<Arc<dyn EventBus>>) -> Self {
        Self {
            andons: RwLock::new(HashMap::new()),
            projects: RwLock::new(HashMap::new()),
            a3s: RwLock::new(HashMap::new()),
            risks: RwLock::new(HashMap::new()),
            andon_counter: RwLock::new(0),
            project_counter: RwLock::new(0),
            a3_counter: RwLock::new(0),
            risk_counter: RwLock::new(0),
            event_bus,
        }
    }

    async fn publish_event(&self, event: impl DomainEvent + 'static) {
        if let Some(ref bus) = self.event_bus {
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!("Failed to publish event {}: {}", event.event_type(), e);
            }
        }
    }

    fn generate_andon_number(counter: u64) -> String {
        format!("AND-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_project_code(counter: u64) -> String {
        format!("PRJ-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_a3_number(counter: u64) -> String {
        format!("A3-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_risk_number(counter: u64) -> String {
        format!("RSK-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    /// Compute a numeric score for a likelihood string.
    fn likelihood_score(likelihood: &str) -> i32 {
        match likelihood {
            "rare" => 1,
            "unlikely" => 2,
            "possible" => 3,
            "likely" => 4,
            "almost_certain" => 5,
            _ => 3,
        }
    }

    /// Compute a numeric score for an impact string.
    fn impact_score(impact: &str) -> i32 {
        match impact {
            "insignificant" => 1,
            "minor" => 2,
            "moderate" => 3,
            "major" => 4,
            "catastrophic" => 5,
            _ => 3,
        }
    }
}

impl Default for InMemoryOperationsService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl OperationsService for InMemoryOperationsService {
    // ── Andon ───────────────────────────────────────────────────────────

    async fn raise_andon(&self, tenant_id: Uuid, mut andon: Andon) -> Result<Andon> {
        let mut counter = self.andon_counter.write().await;
        *counter += 1;
        let andon_number = Self::generate_andon_number(*counter);
        drop(counter);

        andon.id = Uuid::new_v4();
        andon.tenant_id = tenant_id;
        andon.andon_number = andon_number;
        andon.status = "active".to_string();
        andon.created_at = Utc::now();

        let id = andon.id;
        let issue_type = andon.issue_type.clone();
        let work_center_id = andon.work_center_id;
        let severity = andon.severity.clone();
        self.andons.write().await.insert(id, andon.clone());
        self.publish_event(AndonCreatedEvent::new(
            tenant_id,
            id,
            issue_type,
            None,
            Some(work_center_id),
            severity,
        ))
        .await;
        Ok(andon)
    }

    async fn raise_andon_idempotent(
        &self,
        tenant_id: Uuid,
        andon: Andon,
        request_key: Option<String>,
    ) -> Result<Andon> {
        let Some(key) = request_key else {
            return self.raise_andon(tenant_id, andon).await;
        };
        // Replay: the same command key returns the ORIGINAL andon.
        {
            let store = self.andons.read().await;
            if let Some(existing) = store.values().find(|a| {
                a.tenant_id == tenant_id && a.request_key.as_deref() == Some(key.as_str())
            }) {
                return Ok(existing.clone());
            }
        }
        let mut raised = self.raise_andon(tenant_id, andon).await?;
        // Stamp the key atomically with the create (best-effort in-memory).
        {
            let mut store = self.andons.write().await;
            if let Some(row) = store.get_mut(&raised.id) {
                row.request_key = Some(key.clone());
            }
        }
        raised.request_key = Some(key);
        Ok(raised)
    }

    async fn acknowledge_andon(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        acknowledged_by: Uuid,
    ) -> Result<Andon> {
        let mut store = self.andons.write().await;
        let andon = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))?;

        if andon.status != "active" {
            return Err(SenseiError::Validation(format!(
                "Cannot acknowledge an Andon with status: {}",
                andon.status
            )));
        }

        let now = Utc::now();
        andon.status = "acknowledged".to_string();
        andon.acknowledged_by = Some(acknowledged_by);
        andon.acknowledged_at = Some(now);

        // Compute response time in seconds (from created_at to acknowledged_at)
        let response = now.signed_duration_since(andon.created_at);
        andon.response_time_seconds = Some(response.num_seconds());

        let result = andon.clone();
        drop(store);
        self.publish_event(AndonAcknowledgedEvent::new(tenant_id, id, acknowledged_by))
            .await;
        Ok(result)
    }

    async fn escalate_andon(&self, tenant_id: Uuid, id: Uuid, escalated_by: Uuid) -> Result<Andon> {
        let mut store = self.andons.write().await;
        let andon = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))?;
        if andon.status == "resolved" || andon.status == "voided" {
            return Err(SenseiError::Validation(format!(
                "Cannot escalate a closed Andon (status: {})",
                andon.status
            )));
        }
        let now = Utc::now();
        andon.escalated = true;
        andon.escalated_at = Some(now);
        if andon.status == "active" {
            andon.status = "acknowledged".to_string();
            andon.acknowledged_by = Some(escalated_by);
            andon.acknowledged_at = Some(now);
        }
        let result = andon.clone();
        drop(store);
        self.publish_event(AndonAcknowledgedEvent::new(tenant_id, id, escalated_by))
            .await;
        Ok(result)
    }

    async fn resolve_andon(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        resolved_by: Uuid,
        resolution: &str,
    ) -> Result<Andon> {
        let mut store = self.andons.write().await;
        let andon = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))?;

        if andon.status == "resolved" || andon.status == "closed" {
            return Err(SenseiError::Validation(format!(
                "Cannot resolve an Andon with status: {}",
                andon.status
            )));
        }

        let now = Utc::now();
        andon.status = "resolved".to_string();
        andon.resolved_by = Some(resolved_by);
        andon.resolution = Some(resolution.to_string());
        andon.resolved_at = Some(now);

        // Compute resolution time in seconds (from created_at to resolved_at)
        let resolution_time = now.signed_duration_since(andon.created_at);
        andon.resolution_time_seconds = Some(resolution_time.num_seconds());

        // If it wasn't explicitly acknowledged, compute response time too
        if andon.response_time_seconds.is_none() {
            andon.response_time_seconds = Some(resolution_time.num_seconds());
        }

        let result = andon.clone();
        let resolution_str = result.resolution.clone().unwrap_or_default();
        let downtime_minutes = result.resolution_time_seconds.unwrap_or(0) as f64 / 60.0;
        drop(store);
        self.publish_event(AndonResolvedEvent::new(
            tenant_id,
            id,
            resolved_by,
            resolution_str,
            downtime_minutes,
        ))
        .await;
        Ok(result)
    }

    async fn get_andon(&self, _tenant_id: Uuid, id: Uuid) -> Result<Andon> {
        let store = self.andons.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))
    }

    async fn list_andons(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        work_center_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Andon>> {
        let store = self.andons.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|a| {
                a.tenant_id == tenant_id
                    && status.is_none_or(|s| a.status == s)
                    && work_center_id.is_none_or(|wc| a.work_center_id == wc)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn list_andons_scoped(
        &self,
        tenant_id: Uuid,
        scope_site: Option<Uuid>,
        status: Option<&str>,
        work_center_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Andon>> {
        let store = self.andons.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|a| {
                a.tenant_id == tenant_id
                    && scope_site.is_none_or(|site| a.site_id == Some(site))
                    && status.is_none_or(|s| a.status == s)
                    && work_center_id.is_none_or(|wc| a.work_center_id == wc)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    // ── Projects ────────────────────────────────────────────────────────

    async fn create_project(&self, tenant_id: Uuid, mut project: Project) -> Result<Project> {
        let mut counter = self.project_counter.write().await;
        *counter += 1;
        let project_code = Self::generate_project_code(*counter);
        drop(counter);

        project.id = Uuid::new_v4();
        project.tenant_id = tenant_id;
        project.project_code = project_code;
        project.status = "not_started".to_string();
        project.created_at = Utc::now();

        let id = project.id;
        let project_name = project.name.clone();
        let project_category = project.category.clone();
        self.projects.write().await.insert(id, project.clone());
        self.publish_event(ProjectCreatedEvent::new(
            tenant_id,
            id,
            project_name,
            project_category,
        ))
        .await;
        Ok(project)
    }

    async fn get_project(&self, _tenant_id: Uuid, id: Uuid) -> Result<Project> {
        let store = self.projects.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))
    }

    async fn list_projects(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        category: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Project>> {
        let store = self.projects.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|p| {
                p.tenant_id == tenant_id
                    && status.is_none_or(|s| p.status == s)
                    && category.is_none_or(|c| p.category == c)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn complete_project(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        savings_realized: f64,
    ) -> Result<Project> {
        let mut store = self.projects.write().await;
        let project = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))?;

        if project.status == "completed" {
            return Err(SenseiError::Validation(
                "Project is already completed".to_string(),
            ));
        }

        project.status = "completed".to_string();
        project.savings_realized = Some(
            rust_decimal::Decimal::from_f64_retain(savings_realized)
                .unwrap_or(rust_decimal::Decimal::ZERO),
        );
        project.actual_end = Some(Utc::now());

        if project.actual_start.is_none() {
            project.actual_start = Some(Utc::now());
        }

        Ok(project.clone())
    }

    // ── A3 ──────────────────────────────────────────────────────────────

    async fn create_a3(&self, tenant_id: Uuid, mut a3: A3) -> Result<A3> {
        let mut counter = self.a3_counter.write().await;
        *counter += 1;
        let a3_number = Self::generate_a3_number(*counter);
        drop(counter);

        a3.id = Uuid::new_v4();
        a3.tenant_id = tenant_id;
        a3.a3_number = a3_number;
        a3.status = "draft".to_string();
        a3.created_at = Utc::now();

        let id = a3.id;
        let title = a3.title.clone();
        self.a3s.write().await.insert(id, a3.clone());
        self.publish_event(A3CreatedEvent::new(
            tenant_id,
            id,
            "problem_solving".to_string(),
            title,
            "medium".to_string(),
        ))
        .await;
        Ok(a3)
    }

    async fn get_a3(&self, _tenant_id: Uuid, id: Uuid) -> Result<A3> {
        let store = self.a3s.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("A3 {id} not found")))
    }

    async fn list_a3s(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<A3>> {
        let store = self.a3s.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|a| a.tenant_id == tenant_id && status.is_none_or(|s| a.status == s))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn close_a3(&self, tenant_id: Uuid, id: Uuid) -> Result<A3> {
        let mut store = self.a3s.write().await;
        let a3 = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("A3 {id} not found")))?;

        if a3.status == "closed" {
            return Err(SenseiError::Validation(
                "A3 report is already closed".to_string(),
            ));
        }

        // Evidence gate: countermeasures + a verification plan must be
        // recorded before closure (an A3 does not close by clicking).
        if a3.countermeasures.trim().is_empty() {
            return Err(SenseiError::Validation(
                "A3 cannot be closed: no countermeasures recorded".to_string(),
            ));
        }
        if a3.check_plan.trim().is_empty() || a3.follow_up.trim().is_empty() {
            return Err(SenseiError::Validation(
                "A3 cannot be closed: the verification plan (check_plan/follow_up) is empty"
                    .to_string(),
            ));
        }

        if a3.verifications.is_empty() {
            return Err(SenseiError::Validation(
                "A3 cannot be closed: no verification evidence recorded (verifications is empty)"
                    .to_string(),
            ));
        }
        a3.status = "closed".to_string();
        a3.closed_at = Some(Utc::now());
        a3.version += 1;
        let result = a3.clone();
        // The outcome reflects the A3's actual state before closure: reports
        // closed from `implemented`/`verified` carry that outcome, anything
        // else is inconclusive.
        let outcome = match result.status.as_str() {
            "implemented" | "verified" => result.status.clone(),
            _ => "inconclusive".to_string(),
        };
        drop(store);
        self.publish_event(A3ClosedEvent::new(tenant_id, id, outcome))
            .await;
        Ok(result)
    }

    // ── Risk ────────────────────────────────────────────────────────────

    async fn create_risk(&self, tenant_id: Uuid, mut risk: Risk) -> Result<Risk> {
        let mut counter = self.risk_counter.write().await;
        *counter += 1;
        let risk_number = Self::generate_risk_number(*counter);
        drop(counter);

        // Compute risk score from likelihood × impact
        let likelihood_score = Self::likelihood_score(&risk.likelihood);
        let impact_score = Self::impact_score(&risk.impact);
        let risk_score = likelihood_score * impact_score;

        // Preserve a caller-supplied id; only generate one when absent.
        if risk.id.is_nil() {
            risk.id = Uuid::new_v4();
        }
        risk.tenant_id = tenant_id;
        risk.risk_number = risk_number;
        risk.risk_score = risk_score;
        risk.status = "identified".to_string();
        risk.created_at = Utc::now();

        let id = risk.id;
        let category = risk.category.clone();
        let severity = risk.impact.clone();
        let likelihood = risk.likelihood.clone();
        self.risks.write().await.insert(id, risk.clone());
        self.publish_event(RiskCreatedEvent::new(
            tenant_id,
            id,
            category,
            severity,
            likelihood,
            "risk".to_string(),
            Uuid::nil(),
        ))
        .await;
        Ok(risk)
    }

    async fn get_risk(&self, _tenant_id: Uuid, id: Uuid) -> Result<Risk> {
        let store = self.risks.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))
    }

    async fn list_risks(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        category: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Risk>> {
        let store = self.risks.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|r| {
                r.tenant_id == tenant_id
                    && status.is_none_or(|s| r.status == s)
                    && category.is_none_or(|c| r.category == c)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn mitigate_risk(&self, tenant_id: Uuid, id: Uuid) -> Result<Risk> {
        let mut store = self.risks.write().await;
        let risk = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;

        if risk.status == "mitigated" || risk.status == "closed" {
            return Err(SenseiError::Validation(format!(
                "Cannot mitigate a risk with status: {}",
                risk.status
            )));
        }

        risk.status = "mitigated".to_string();
        risk.mitigated_at = Some(Utc::now());
        let result = risk.clone();
        // The mitigation is identified by a stable id derived from the risk,
        // and its effectiveness reflects whether an actual mitigation action
        // is defined (an empty mitigation plan cannot be "effective").
        let mitigation_id = Uuid::new_v5(
            &Uuid::NAMESPACE_OID,
            format!("{tenant_id}:{id}:mitigation").as_bytes(),
        );
        let effectiveness = if result.mitigation.trim().is_empty() {
            "inconclusive".to_string()
        } else {
            "effective".to_string()
        };
        drop(store);
        self.publish_event(RiskMitigatedEvent::new(
            tenant_id,
            id,
            mitigation_id,
            effectiveness,
        ))
        .await;
        Ok(result)
    }
    // ── New: Update / Delete ─────────────────────────────────────────────

    async fn update_andon(&self, _tenant_id: Uuid, id: Uuid, andon: Andon) -> Result<Andon> {
        let mut store = self.andons.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))?;
        existing.issue_type = andon.issue_type;
        existing.severity = andon.severity;
        existing.description = andon.description;
        existing.status = andon.status;
        existing.resolution = andon.resolution;
        // Preserve: id, tenant_id, andon_number, work_center_id, raised_by,
        //           acknowledged_by, resolved_by, response_time_seconds,
        //           resolution_time_seconds, created_at, acknowledged_at, resolved_at
        Ok(existing.clone())
    }

    async fn authorize_restart(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        authorized_by: Uuid,
    ) -> Result<Andon> {
        let mut store = self.andons.write().await;
        let andon = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))?;
        andon.restart_authorized_by = Some(authorized_by);
        andon.restart_authorized_at = Some(Utc::now());
        Ok(andon.clone())
    }

    async fn void_andon(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        actor_id: Uuid,
        reason: &str,
    ) -> Result<Andon> {
        let mut store = self.andons.write().await;
        let andon = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))?;
        andon.status = "voided".to_string();
        andon.resolved_by = Some(actor_id);
        andon.resolution = Some(format!("VOIDED: {reason}"));
        Ok(andon.clone())
    }

    async fn update_project(
        &self,
        _tenant_id: Uuid,
        id: Uuid,
        project: Project,
    ) -> Result<Project> {
        let mut store = self.projects.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))?;
        existing.name = project.name;
        existing.description = project.description;
        existing.category = project.category;
        existing.status = project.status;
        existing.priority = project.priority;
        existing.owner_id = project.owner_id;
        existing.team_members = project.team_members;
        existing.planned_start = project.planned_start;
        existing.planned_end = project.planned_end;
        existing.actual_start = project.actual_start;
        existing.actual_end = project.actual_end;
        existing.budget = project.budget;
        // Preserve: id, tenant_id, project_code, savings_realized, created_at
        Ok(existing.clone())
    }

    async fn delete_project(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.projects.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))?;
        Ok(())
    }

    async fn update_a3(&self, _tenant_id: Uuid, id: Uuid, a3: A3) -> Result<A3> {
        let mut store = self.a3s.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("A3 {id} not found")))?;
        // Optimistic concurrency mirrors the DB CAS.
        if existing.version != a3.version {
            return Err(SenseiError::Conflict(format!(
                "VERSION_CONFLICT: A3 {id} was modified concurrently (expected version {})",
                a3.version
            )));
        }
        existing.title = a3.title;
        existing.background = a3.background;
        existing.current_state = a3.current_state;
        existing.goal = a3.goal;
        existing.root_cause_analysis = a3.root_cause_analysis;
        existing.countermeasures = a3.countermeasures;
        existing.check_plan = a3.check_plan;
        existing.follow_up = a3.follow_up;
        existing.status = a3.status;
        existing.owner_id = a3.owner_id;
        // Evidence model is part of the update.
        existing.observed_conditions = a3.observed_conditions;
        existing.metric_baselines = a3.metric_baselines;
        existing.evidence_refs = a3.evidence_refs;
        existing.cause_hypotheses = a3.cause_hypotheses;
        existing.experiments = a3.experiments;
        existing.verifications = a3.verifications;
        existing.standardizations = a3.standardizations;
        existing.learnings = a3.learnings;
        existing.version += 1;
        // Preserve: id, tenant_id, a3_number, created_at, closed_at
        Ok(existing.clone())
    }

    async fn delete_a3(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        // A3 learning history is never physically erased: abandoned draft
        // cases are voided and retained.
        let mut store = self.a3s.write().await;
        let a3 = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("A3 {id} not found")))?;
        if a3.status != "draft" {
            return Err(SenseiError::Validation(
                "Only draft A3 cases can be voided; published/closed history is retained"
                    .to_string(),
            ));
        }
        a3.status = "voided".to_string();
        Ok(())
    }

    async fn update_risk(&self, _tenant_id: Uuid, id: Uuid, risk: Risk) -> Result<Risk> {
        let mut store = self.risks.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;
        existing.title = risk.title;
        existing.description = risk.description;
        existing.category = risk.category;
        existing.likelihood = risk.likelihood;
        existing.impact = risk.impact;
        existing.risk_score = risk.risk_score;
        existing.mitigation = risk.mitigation;
        existing.contingency = risk.contingency;
        existing.status = risk.status;
        existing.owner_id = risk.owner_id;
        // Preserve: id, tenant_id, risk_number, created_at, mitigated_at
        Ok(existing.clone())
    }

    async fn delete_risk(&self, _tenant_id: Uuid, id: Uuid) -> Result<()> {
        let mut store = self.risks.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_andon_lifecycle() {
        let service = InMemoryOperationsService::default();
        let tenant_id = Uuid::new_v4();
        let work_center_id = Uuid::new_v4();
        let user_id = Uuid::new_v4();

        let andon = Andon {
            id: Uuid::nil(),
            tenant_id,
            site_id: None,
            andon_number: String::new(),
            work_center_id,
            issue_type: "quality".to_string(),
            severity: "high".to_string(),
            description: "Temperature out of spec on press #3".to_string(),
            status: String::new(),
            raised_by: user_id,
            acknowledged_by: None,
            resolved_by: None,
            resolution: None,
            response_time_seconds: None,
            resolution_time_seconds: None,
            created_at: Utc::now(),
            acknowledged_at: None,
            resolved_at: None,
            restart_authorized_by: None,
            restart_authorized_at: None,
            abnormal_condition_observed_at: None,
            contained_at: None,
            contained_by: None,
            contained_note: None,
            escalated: false,
            escalated_at: None,
            request_key: None,
        };

        let raised = service
            .raise_andon(tenant_id, andon)
            .await
            .expect("should raise andon");
        assert!(raised.andon_number.starts_with("AND-"));
        assert_eq!(raised.status, "active");

        let ack = service
            .acknowledge_andon(tenant_id, raised.id, user_id)
            .await
            .unwrap();
        assert_eq!(ack.status, "acknowledged");
        assert!(ack.response_time_seconds.is_some());

        let resolved = service
            .resolve_andon(
                tenant_id,
                raised.id,
                user_id,
                "Rebooted controller, temperature normalised",
            )
            .await
            .unwrap();
        assert_eq!(resolved.status, "resolved");
        assert!(resolved.resolution_time_seconds.is_some());
        assert_eq!(
            resolved.resolution.as_deref(),
            Some("Rebooted controller, temperature normalised")
        );
    }

    #[tokio::test]
    async fn test_project_lifecycle() {
        let service = InMemoryOperationsService::default();
        let tenant_id = Uuid::new_v4();
        let owner_id = Uuid::new_v4();

        let project = Project {
            id: Uuid::nil(),
            tenant_id,
            project_code: String::new(),
            name: "Reduce scrap by 15%".to_string(),
            description: "Kaizen project targeting press scrap reduction".to_string(),
            category: "kaizen".to_string(),
            status: String::new(),
            priority: "high".to_string(),
            owner_id,
            team_members: vec![owner_id],
            planned_start: Some(Utc::now()),
            planned_end: Some(Utc::now() + chrono::Duration::days(90)),
            actual_start: None,
            actual_end: None,
            budget: Some(rust_decimal::Decimal::from(5000u32)),
            savings_realized: None,
            created_at: Utc::now(),
        };

        let created = service
            .create_project(tenant_id, project)
            .await
            .expect("should create project");
        assert!(created.project_code.starts_with("PRJ-"));
        assert_eq!(created.status, "not_started");

        let completed = service
            .complete_project(tenant_id, created.id, 15000.0)
            .await
            .unwrap();
        assert_eq!(completed.status, "completed");
        assert_eq!(
            completed.savings_realized,
            Some(rust_decimal::Decimal::from(15000u32))
        );
    }

    #[tokio::test]
    async fn test_a3_lifecycle() {
        let service = InMemoryOperationsService::default();
        let tenant_id = Uuid::new_v4();
        let owner_id = Uuid::new_v4();

        let a3 = A3 {
            id: Uuid::nil(),
            tenant_id,
            a3_number: String::new(),
            title: "Reduce changeover time".to_string(),
            background: "Current changeover takes 45 minutes".to_string(),
            version: 0,
            current_state: "SMED analysis shows 60% internal setup".to_string(),
            goal: "Reduce to under 15 minutes".to_string(),
            root_cause_analysis: "Lack of standard work".to_string(),
            countermeasures: "Implement SMED".to_string(),
            check_plan: "Track changeover times weekly".to_string(),
            follow_up: "Standardise and repeat".to_string(),
            status: String::new(),
            a3_type: "standard".to_string(),
            severity: "medium".to_string(),
            owner_id,
            created_at: Utc::now(),
            closed_at: None,
            observed_conditions: vec![],
            metric_baselines: vec![],
            evidence_refs: vec![],
            cause_hypotheses: vec![],
            experiments: vec![],
            verifications: vec![],
            standardizations: vec![],
            learnings: vec![],
        };

        let created = service
            .create_a3(tenant_id, a3)
            .await
            .expect("should create A3");
        assert!(created.a3_number.starts_with("A3-"));
        assert_eq!(created.status, "draft");

        let mut with_evidence = service.get_a3(tenant_id, created.id).await.unwrap();
        with_evidence.verifications =
            vec![serde_json::json!({"metric": "defect_rate", "after": 1.8})];
        let _ = service
            .update_a3(tenant_id, created.id, with_evidence)
            .await
            .unwrap();
        let closed = service.close_a3(tenant_id, created.id).await.unwrap();
        assert_eq!(closed.status, "closed");
        assert!(closed.closed_at.is_some());
    }

    #[tokio::test]
    async fn test_risk_creation_and_mitigation() {
        let service = InMemoryOperationsService::default();
        let tenant_id = Uuid::new_v4();
        let owner_id = Uuid::new_v4();

        let risk = Risk {
            id: Uuid::nil(),
            tenant_id,
            risk_number: String::new(),
            title: "Single supplier for critical component".to_string(),
            description: "Only one supplier qualified for custom bearing".to_string(),
            category: "operational".to_string(),
            likelihood: "likely".to_string(),
            impact: "major".to_string(),
            risk_score: 0,
            mitigation: "Qualify second supplier by Q3".to_string(),
            contingency: "Increase safety stock to 8 weeks".to_string(),
            status: String::new(),
            owner_id,
            created_at: Utc::now(),
            mitigated_at: None,
        };

        let created = service
            .create_risk(tenant_id, risk)
            .await
            .expect("should create risk");
        assert!(created.risk_number.starts_with("RSK-"));
        // likely(4) × major(4) = 16
        assert_eq!(created.risk_score, 16);
        assert_eq!(created.status, "identified");

        let mitigated = service.mitigate_risk(tenant_id, created.id).await.unwrap();
        assert_eq!(mitigated.status, "mitigated");
        assert!(mitigated.mitigated_at.is_some());
    }

    #[tokio::test]
    async fn test_list_andons_with_filters() {
        let service = InMemoryOperationsService::default();
        let tenant_id = Uuid::new_v4();
        let wc1 = Uuid::new_v4();
        let wc2 = Uuid::new_v4();
        let user_id = Uuid::new_v4();

        let a1 = Andon {
            id: Uuid::nil(),
            tenant_id,
            site_id: None,
            andon_number: String::new(),
            work_center_id: wc1,
            issue_type: "quality".to_string(),
            severity: "high".to_string(),
            description: "Issue 1".to_string(),
            status: String::new(),
            raised_by: user_id,
            acknowledged_by: None,
            resolved_by: None,
            resolution: None,
            response_time_seconds: None,
            resolution_time_seconds: None,
            created_at: Utc::now(),
            acknowledged_at: None,
            resolved_at: None,
            restart_authorized_by: None,
            restart_authorized_at: None,
            abnormal_condition_observed_at: None,
            contained_at: None,
            contained_by: None,
            contained_note: None,
            escalated: false,
            escalated_at: None,
            request_key: None,
        };
        let a2 = Andon {
            id: Uuid::nil(),
            tenant_id,
            site_id: None,
            andon_number: String::new(),
            work_center_id: wc2,
            issue_type: "safety".to_string(),
            severity: "critical".to_string(),
            description: "Issue 2".to_string(),
            status: String::new(),
            raised_by: user_id,
            acknowledged_by: None,
            resolved_by: None,
            resolution: None,
            response_time_seconds: None,
            resolution_time_seconds: None,
            created_at: Utc::now(),
            acknowledged_at: None,
            resolved_at: None,
            restart_authorized_by: None,
            restart_authorized_at: None,
            abnormal_condition_observed_at: None,
            contained_at: None,
            contained_by: None,
            contained_note: None,
            escalated: false,
            escalated_at: None,
            request_key: None,
        };

        service.raise_andon(tenant_id, a1).await.unwrap();
        service.raise_andon(tenant_id, a2).await.unwrap();

        let all = service
            .list_andons(tenant_id, None, None, None, None)
            .await
            .unwrap();
        assert_eq!(all.data.len(), 2);

        let wc1_andons = service
            .list_andons(tenant_id, None, Some(wc1), None, None)
            .await
            .unwrap();
        assert_eq!(wc1_andons.data.len(), 1);
        assert_eq!(wc1_andons.data[0].work_center_id, wc1);
    }
}
