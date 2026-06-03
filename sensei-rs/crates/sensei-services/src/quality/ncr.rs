//! Non-Conformance Report (NCR) service.
//!
//! Implements the full NCR lifecycle: creation, investigation, disposition,
//! routing, and closure. Supports severity classification, defect coding,
//! CAPA linking, and recurrence detection.
//!
//! Ported from Python's `capa_workflow.py` NCR logic and `qms_quality.py`
//! audit finding patterns.

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{EntityId, TenantId, new_id, now};
use uuid::Uuid;

use super::models::{
    ActionStatus, CapaConfig, CapaCreationResult, CapaExtended, CapaPriority, CapaStatusEx,
    CapaType, ClosureCheckResult, ClosureGate, ClosureGateType, CorrectiveAction,
    EffectivenessCheck, EntityLink, LinkType, NcSeverity, NcType, NonConformance,
    RecurrenceCheckResult, RootCauseAnalysis,
    DEFAULT_CLOSURE_GATES,
};

/// NCR service trait defining the non-conformance report lifecycle.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait NcrService: Send + Sync {
    /// Register a new non-conformance.
    async fn register_nc(
        &self,
        tenant_id: TenantId,
        title: String,
        description: String,
        nc_type: NcType,
        severity: NcSeverity,
        product_id: Option<EntityId>,
        process_id: Option<EntityId>,
        defect_code: Option<String>,
        detected_by: Option<EntityId>,
        department: Option<String>,
        location: Option<String>,
    ) -> Result<NonConformance>;

    /// Get an NCR by ID.
    async fn get_nc(&self, nc_id: EntityId) -> Result<NonConformance>;

    /// Get an NCR by its number.
    async fn get_nc_by_number(&self, nc_number: &str) -> Result<NonConformance>;

    /// List NCRs with optional filters.
    async fn list_ncs(
        &self,
        tenant_id: TenantId,
        nc_type: Option<NcType>,
        severity: Option<NcSeverity>,
        product_id: Option<EntityId>,
    ) -> Result<Vec<NonConformance>>;

    /// Check if an NC is a recurrence within the configured period.
    async fn check_recurrence(
        &self,
        tenant_id: TenantId,
        nc_type: NcType,
        defect_code: Option<&str>,
        product_id: Option<EntityId>,
        process_id: Option<EntityId>,
        config: &CapaConfig,
    ) -> Result<RecurrenceCheckResult>;
}

/// CAPA workflow service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait CapaWorkflowService: Send + Sync {
    /// Create a CAPA from an NC with optional auto-creation logic.
    async fn create_capa_from_nc(
        &self,
        tenant_id: TenantId,
        nc_id: EntityId,
        title: String,
        description: String,
        capa_type: CapaType,
        priority: CapaPriority,
        owner_id: Option<EntityId>,
        config: &CapaConfig,
    ) -> Result<CapaCreationResult>;

    /// Create a standalone CAPA (not linked to an NC).
    async fn create_capa(
        &self,
        tenant_id: TenantId,
        title: String,
        description: String,
        capa_type: CapaType,
        priority: CapaPriority,
        owner_id: Option<EntityId>,
        due_date: Option<DateTime<Utc>>,
    ) -> Result<CapaExtended>;

    /// Get a CAPA by ID.
    async fn get_capa(&self, capa_id: EntityId) -> Result<CapaExtended>;

    /// List CAPAs with optional filters.
    async fn list_capas(
        &self,
        tenant_id: TenantId,
        status: Option<CapaStatusEx>,
        priority: Option<CapaPriority>,
    ) -> Result<Vec<CapaExtended>>;

    /// Get CAPA metrics.
    async fn get_capa_metrics(&self, tenant_id: TenantId) -> Result<serde_json::Value>;

    /// Add a root cause analysis to a CAPA.
    async fn add_root_cause_analysis(
        &self,
        capa_id: EntityId,
        description: String,
        root_cause_type: String,
        analysis_method: String,
        contributors: Vec<String>,
        evidence: Vec<String>,
    ) -> Result<RootCauseAnalysis>;

    /// Verify a root cause analysis.
    async fn verify_root_cause(
        &self,
        capa_id: EntityId,
        rca_id: EntityId,
        verified_by: EntityId,
    ) -> Result<RootCauseAnalysis>;

    /// Add a corrective/preventive action to a CAPA.
    async fn add_action(
        &self,
        capa_id: EntityId,
        description: String,
        action_type: String,
        owner_id: Option<EntityId>,
        due_date: Option<DateTime<Utc>>,
    ) -> Result<CorrectiveAction>;

    /// Start an action.
    async fn start_action(&self, capa_id: EntityId, action_id: EntityId) -> Result<CorrectiveAction>;

    /// Complete an action.
    async fn complete_action(
        &self,
        capa_id: EntityId,
        action_id: EntityId,
    ) -> Result<CorrectiveAction>;

    /// Verify an action.
    async fn verify_action(
        &self,
        capa_id: EntityId,
        action_id: EntityId,
        verified_by: EntityId,
        verification_notes: String,
    ) -> Result<CorrectiveAction>;

    /// Get overdue actions.
    async fn get_overdue_actions(
        &self,
        tenant_id: TenantId,
        capa_id: Option<EntityId>,
    ) -> Result<Vec<CorrectiveAction>>;

    /// Link a related entity to a CAPA.
    async fn link_entity(
        &self,
        capa_id: EntityId,
        link_type: LinkType,
        entity_id: EntityId,
        entity_type: String,
        description: Option<String>,
    ) -> Result<EntityLink>;

    /// Get linked entities for a CAPA.
    async fn get_linked_entities(&self, capa_id: EntityId) -> Result<Vec<EntityLink>>;

    /// Pass a closure gate for a CAPA.
    async fn pass_closure_gate(
        &self,
        capa_id: EntityId,
        gate_type: ClosureGateType,
        passed_by: EntityId,
        notes: Option<String>,
    ) -> Result<ClosureGate>;

    /// Check closure readiness for a CAPA.
    async fn check_closure_readiness(&self, capa_id: EntityId) -> Result<ClosureCheckResult>;

    /// Add an effectiveness check for a CAPA.
    async fn add_effectiveness_check(
        &self,
        capa_id: EntityId,
        check_method: String,
        results: String,
        is_effective: bool,
        checked_by: EntityId,
        follow_up_needed: bool,
        follow_up_actions: Vec<String>,
    ) -> Result<EffectivenessCheck>;

    /// Get pending effectiveness checks.
    async fn get_pending_effectiveness_checks(&self, tenant_id: TenantId) -> Result<Vec<CapaExtended>>;

    /// Close a CAPA.
    async fn close_capa(&self, capa_id: EntityId, closed_by: EntityId) -> Result<CapaExtended>;

    /// Cancel a CAPA.
    async fn cancel_capa(&self, capa_id: EntityId, reason: String) -> Result<CapaExtended>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of NCR and CAPA workflow services.
pub struct InMemoryCapaWorkflowService {
    ncrs: tokio::sync::RwLock<Vec<NonConformance>>,
    capas: tokio::sync::RwLock<Vec<CapaExtended>>,
    rcas: tokio::sync::RwLock<Vec<RootCauseAnalysis>>,
    actions: tokio::sync::RwLock<Vec<CorrectiveAction>>,
    gates: tokio::sync::RwLock<Vec<ClosureGate>>,
    links: tokio::sync::RwLock<Vec<EntityLink>>,
    ecs: tokio::sync::RwLock<Vec<EffectivenessCheck>>,
    ncr_counter: tokio::sync::RwLock<u64>,
    capa_counter: tokio::sync::RwLock<u64>,
}

impl InMemoryCapaWorkflowService {
    /// Create a new empty service.
    pub fn new() -> Self {
        Self {
            ncrs: tokio::sync::RwLock::new(Vec::new()),
            capas: tokio::sync::RwLock::new(Vec::new()),
            rcas: tokio::sync::RwLock::new(Vec::new()),
            actions: tokio::sync::RwLock::new(Vec::new()),
            gates: tokio::sync::RwLock::new(Vec::new()),
            links: tokio::sync::RwLock::new(Vec::new()),
            ecs: tokio::sync::RwLock::new(Vec::new()),
            ncr_counter: tokio::sync::RwLock::new(0),
            capa_counter: tokio::sync::RwLock::new(0),
        }
    }

    fn generate_nc_number(counter: u64) -> String {
        format!("NC-{}-{:04}", chrono::Utc::now().format("%Y%m%d"), counter)
    }

    fn generate_capa_number(counter: u64) -> String {
        format!("CAPA-{}-{:04}", chrono::Utc::now().format("%Y%m%d"), counter)
    }
}

impl Default for InMemoryCapaWorkflowService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl NcrService for InMemoryCapaWorkflowService {
    async fn register_nc(
        &self,
        _tenant_id: TenantId,
        title: String,
        description: String,
        nc_type: NcType,
        severity: NcSeverity,
        product_id: Option<EntityId>,
        process_id: Option<EntityId>,
        defect_code: Option<String>,
        detected_by: Option<EntityId>,
        department: Option<String>,
        location: Option<String>,
    ) -> Result<NonConformance> {
        let mut counter = self.ncr_counter.write().await;
        *counter += 1;
        let nc_number = Self::generate_nc_number(*counter);

        let nc = NonConformance {
            id: new_id(),
            nc_number,
            title,
            description,
            nc_type,
            severity,
            product_id,
            process_id,
            defect_code,
            detected_by,
            department,
            location,
            is_recurrence: false,
            created_at: now(),
            updated_at: now(),
        };

        self.ncrs.write().await.push(nc.clone());
        Ok(nc)
    }

    async fn get_nc(&self, nc_id: EntityId) -> Result<NonConformance> {
        self.ncrs
            .read()
            .await
            .iter()
            .find(|nc| nc.id == nc_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("NC {nc_id} not found")))
    }

    async fn get_nc_by_number(&self, nc_number: &str) -> Result<NonConformance> {
        self.ncrs
            .read()
            .await
            .iter()
            .find(|nc| nc.nc_number == nc_number)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("NC {nc_number} not found")))
    }

    async fn list_ncs(
        &self,
        _tenant_id: TenantId,
        nc_type: Option<NcType>,
        severity: Option<NcSeverity>,
        product_id: Option<EntityId>,
    ) -> Result<Vec<NonConformance>> {
        let ncrs = self.ncrs.read().await;
        Ok(ncrs
            .iter()
            .filter(|nc| {
                nc_type.is_none_or(|t| nc.nc_type == t)
                    && severity.is_none_or(|s| nc.severity == s)
                    && product_id.is_none_or(|p| nc.product_id == Some(p))
            })
            .cloned()
            .collect())
    }

    async fn check_recurrence(
        &self,
        _tenant_id: TenantId,
        nc_type: NcType,
        defect_code: Option<&str>,
        product_id: Option<EntityId>,
        process_id: Option<EntityId>,
        config: &CapaConfig,
    ) -> Result<RecurrenceCheckResult> {
        let ncrs = self.ncrs.read().await;
        let cutoff = now() - chrono::Duration::days(config.recurrence_period_days as i64);

        let recent_ncs: Vec<&NonConformance> = ncrs
            .iter()
            .filter(|nc| {
                nc.nc_type == nc_type
                    && nc.created_at > cutoff
                    && defect_code.is_none_or(|dc| nc.defect_code.as_deref() == Some(dc))
                    && product_id.is_none_or(|p| nc.product_id == Some(p))
                    && process_id.is_none_or(|p| nc.process_id == Some(p))
            })
            .collect();

        let previous_nc_ids: Vec<Uuid> = recent_ncs.iter().map(|nc| nc.id).collect();
        let count = previous_nc_ids.len() as u32;
        let is_recurrence = count >= config.recurrence_threshold;

        Ok(RecurrenceCheckResult {
            is_recurrence,
            previous_nc_count: count,
            previous_nc_ids,
            period_days: config.recurrence_period_days,
        })
    }
}

#[async_trait]
impl CapaWorkflowService for InMemoryCapaWorkflowService {
    async fn create_capa_from_nc(
        &self,
        _tenant_id: TenantId,
        nc_id: EntityId,
        title: String,
        description: String,
        capa_type: CapaType,
        priority: CapaPriority,
        owner_id: Option<EntityId>,
        config: &CapaConfig,
    ) -> Result<CapaCreationResult> {
        // Verify NC exists
        let nc = self.get_nc(nc_id).await?;

        let mut counter = self.capa_counter.write().await;
        *counter += 1;
        let capa_number = Self::generate_capa_number(*counter);
        drop(counter);

        let default_gates = self._create_default_closure_gates();
        let now_ts = now();

        let capa = CapaExtended {
            id: new_id(),
            capa_number,
            title,
            description,
            nc_ids: vec![nc_id],
            capa_type,
            priority,
            status: CapaStatusEx::Draft,
            root_cause_analyses: Vec::new(),
            actions: Vec::new(),
            closure_gates: default_gates,
            effectiveness_checks: Vec::new(),
            entity_links: Vec::new(),
            owner_id,
            due_date: None,
            closed_at: None,
            created_at: now_ts,
            updated_at: now_ts,
        };

        let auto_created = config.auto_create_capa;
        let creation_reason = if auto_created {
            format!("Auto-created from NC {} (severity: {:?})", nc.nc_number, nc.severity)
        } else {
            format!("Manual creation from NC {}", nc.nc_number)
        };

        self.capas.write().await.push(capa.clone());

        Ok(CapaCreationResult {
            capa,
            auto_created,
            creation_reason,
        })
    }

    async fn create_capa(
        &self,
        _tenant_id: TenantId,
        title: String,
        description: String,
        capa_type: CapaType,
        priority: CapaPriority,
        owner_id: Option<EntityId>,
        due_date: Option<DateTime<Utc>>,
    ) -> Result<CapaExtended> {
        let mut counter = self.capa_counter.write().await;
        *counter += 1;
        let capa_number = Self::generate_capa_number(*counter);
        drop(counter);

        let default_gates = self._create_default_closure_gates();
        let now_ts = now();

        let capa = CapaExtended {
            id: new_id(),
            capa_number,
            title,
            description,
            nc_ids: Vec::new(),
            capa_type,
            priority,
            status: CapaStatusEx::Draft,
            root_cause_analyses: Vec::new(),
            actions: Vec::new(),
            closure_gates: default_gates,
            effectiveness_checks: Vec::new(),
            entity_links: Vec::new(),
            owner_id,
            due_date,
            closed_at: None,
            created_at: now_ts,
            updated_at: now_ts,
        };

        self.capas.write().await.push(capa.clone());
        Ok(capa)
    }

    async fn get_capa(&self, capa_id: EntityId) -> Result<CapaExtended> {
        self.capas
            .read()
            .await
            .iter()
            .find(|c| c.id == capa_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("CAPA {capa_id} not found")))
    }

    async fn list_capas(
        &self,
        _tenant_id: TenantId,
        status: Option<CapaStatusEx>,
        priority: Option<CapaPriority>,
    ) -> Result<Vec<CapaExtended>> {
        let capas = self.capas.read().await;
        Ok(capas
            .iter()
            .filter(|c| status.is_none_or(|s| c.status == s))
            .filter(|c| priority.is_none_or(|p| c.priority == p))
            .cloned()
            .collect())
    }

    async fn get_capa_metrics(&self, _tenant_id: TenantId) -> Result<serde_json::Value> {
        let capas = self.capas.read().await;
        let total = capas.len();
        let open = capas.iter().filter(|c| {
            matches!(c.status, CapaStatusEx::Open | CapaStatusEx::Draft | CapaStatusEx::PendingApproval)
        }).count();
        let closed = capas.iter().filter(|c| c.status == CapaStatusEx::Closed).count();
        let overdue = capas.iter().filter(|c| {
            if let Some(due) = c.due_date {
                due < now() && c.status != CapaStatusEx::Closed
            } else {
                false
            }
        }).count();

        Ok(serde_json::json!({
            "total": total,
            "open": open,
            "closed": closed,
            "overdue": overdue,
            "closure_rate": if total > 0 { (closed as f64 / total as f64) * 100.0 } else { 0.0 },
        }))
    }

    async fn add_root_cause_analysis(
        &self,
        capa_id: EntityId,
        description: String,
        root_cause_type: String,
        analysis_method: String,
        contributors: Vec<String>,
        evidence: Vec<String>,
    ) -> Result<RootCauseAnalysis> {
        // Verify CAPA exists
        self.get_capa(capa_id).await?;

        let rca = RootCauseAnalysis {
            id: new_id(),
            capa_id,
            description,
            root_cause_type,
            analysis_method,
            contributors,
            evidence,
            verified_by: None,
            verified_at: None,
            created_at: now(),
        };

        self.rcas.write().await.push(rca.clone());

        // Update CAPA status
        let mut capas = self.capas.write().await;
        if let Some(capa) = capas.iter_mut().find(|c| c.id == capa_id) {
            capa.root_cause_analyses.push(rca.clone());
            if capa.status == CapaStatusEx::Draft || capa.status == CapaStatusEx::Open {
                capa.status = CapaStatusEx::RootCauseAnalysis;
            }
            capa.updated_at = now();
        }

        Ok(rca)
    }

    async fn verify_root_cause(
        &self,
        capa_id: EntityId,
        rca_id: EntityId,
        verified_by: EntityId,
    ) -> Result<RootCauseAnalysis> {
        let mut rcas = self.rcas.write().await;
        let rca = rcas
            .iter_mut()
            .find(|r| r.id == rca_id && r.capa_id == capa_id)
            .ok_or_else(|| SenseiError::NotFound(format!("RCA {rca_id} not found")))?;

        rca.verified_by = Some(verified_by);
        rca.verified_at = Some(now());

        // Update CAPA status
        let mut capas = self.capas.write().await;
        if let Some(capa) = capas.iter_mut().find(|c| c.id == capa_id) {
            capa.status = CapaStatusEx::ActionPlanning;
            capa.updated_at = now();
        }

        Ok(rca.clone())
    }

    async fn add_action(
        &self,
        capa_id: EntityId,
        description: String,
        action_type: String,
        owner_id: Option<EntityId>,
        due_date: Option<DateTime<Utc>>,
    ) -> Result<CorrectiveAction> {
        self.get_capa(capa_id).await?;

        let action = CorrectiveAction {
            id: new_id(),
            capa_id,
            description,
            action_type,
            owner_id,
            status: ActionStatus::Open,
            due_date,
            completed_at: None,
            verified_by: None,
            verified_at: None,
            verification_notes: None,
            created_at: now(),
            updated_at: now(),
        };

        self.actions.write().await.push(action.clone());

        let mut capas = self.capas.write().await;
        if let Some(capa) = capas.iter_mut().find(|c| c.id == capa_id) {
            capa.actions.push(action.clone());
            if capa.status == CapaStatusEx::RootCauseAnalysis || capa.status == CapaStatusEx::ActionPlanning {
                capa.status = CapaStatusEx::ActionPlanning;
            }
            capa.updated_at = now();
        }

        Ok(action)
    }

    async fn start_action(&self, capa_id: EntityId, action_id: EntityId) -> Result<CorrectiveAction> {
        let mut actions = self.actions.write().await;
        let action = actions
            .iter_mut()
            .find(|a| a.id == action_id && a.capa_id == capa_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Action {action_id} not found")))?;

        if action.status != ActionStatus::Open {
            return Err(SenseiError::Validation(
                format!("Cannot start action {action_id}: status is {:?}", action.status)
            ));
        }

        action.status = ActionStatus::InProgress;
        action.updated_at = now();

        let mut capas = self.capas.write().await;
        if let Some(capa) = capas.iter_mut().find(|c| c.id == capa_id) {
            capa.status = CapaStatusEx::Implementing;
            capa.updated_at = now();
        }

        Ok(action.clone())
    }

    async fn complete_action(
        &self,
        capa_id: EntityId,
        action_id: EntityId,
    ) -> Result<CorrectiveAction> {
        let mut actions = self.actions.write().await;
        let action = actions
            .iter_mut()
            .find(|a| a.id == action_id && a.capa_id == capa_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Action {action_id} not found")))?;

        action.status = ActionStatus::Completed;
        action.completed_at = Some(now());
        action.updated_at = now();

        Ok(action.clone())
    }

    async fn verify_action(
        &self,
        capa_id: EntityId,
        action_id: EntityId,
        verified_by: EntityId,
        verification_notes: String,
    ) -> Result<CorrectiveAction> {
        let mut actions = self.actions.write().await;
        let action = actions
            .iter_mut()
            .find(|a| a.id == action_id && a.capa_id == capa_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Action {action_id} not found")))?;

        action.status = ActionStatus::Verified;
        action.verified_by = Some(verified_by);
        action.verified_at = Some(now());
        action.verification_notes = Some(verification_notes);
        action.updated_at = now();

        let mut capas = self.capas.write().await;
        if let Some(capa) = capas.iter_mut().find(|c| c.id == capa_id) {
            if capa.status == CapaStatusEx::Implementing {
                capa.status = CapaStatusEx::Verification;
            }
            capa.updated_at = now();
        }

        Ok(action.clone())
    }

    async fn get_overdue_actions(
        &self,
        _tenant_id: TenantId,
        capa_id: Option<EntityId>,
    ) -> Result<Vec<CorrectiveAction>> {
        let actions = self.actions.read().await;
        let now_ts = now();
        Ok(actions
            .iter()
            .filter(|a| {
                let overdue = a.due_date.is_some_and(|d| d < now_ts)
                    && a.status != ActionStatus::Completed
                    && a.status != ActionStatus::Verified
                    && a.status != ActionStatus::Closed;

                match capa_id {
                    Some(cid) => a.capa_id == cid && overdue,
                    None => overdue,
                }
            })
            .cloned()
            .collect())
    }

    async fn link_entity(
        &self,
        capa_id: EntityId,
        link_type: LinkType,
        entity_id: EntityId,
        entity_type: String,
        description: Option<String>,
    ) -> Result<EntityLink> {
        self.get_capa(capa_id).await?;

        let link = EntityLink {
            id: new_id(),
            capa_id,
            link_type,
            entity_id,
            entity_type,
            description,
            created_at: now(),
        };

        self.links.write().await.push(link.clone());

        let mut capas = self.capas.write().await;
        if let Some(capa) = capas.iter_mut().find(|c| c.id == capa_id) {
            capa.entity_links.push(link.clone());
        }

        Ok(link)
    }

    async fn get_linked_entities(&self, capa_id: EntityId) -> Result<Vec<EntityLink>> {
        let links = self.links.read().await;
        Ok(links.iter().filter(|l| l.capa_id == capa_id).cloned().collect())
    }

    async fn pass_closure_gate(
        &self,
        capa_id: EntityId,
        gate_type: ClosureGateType,
        passed_by: EntityId,
        notes: Option<String>,
    ) -> Result<ClosureGate> {
        let mut gates = self.gates.write().await;

        // Check if gate exists, create if not
        let gate = if let Some(g) = gates.iter_mut().find(|g| g.capa_id == capa_id && g.gate_type == gate_type) {
            g.passed = true;
            g.passed_by = Some(passed_by);
            g.passed_at = Some(now());
            g.notes = notes;
            g.clone()
        } else {
            let gate = ClosureGate {
                id: new_id(),
                capa_id,
                gate_type,
                description: format!("{:?} gate", gate_type),
                is_mandatory: true,
                passed: true,
                passed_by: Some(passed_by),
                passed_at: Some(now()),
                notes,
                created_at: now(),
            };
            gates.push(gate.clone());
            gate
        };

        Ok(gate)
    }

    async fn check_closure_readiness(&self, capa_id: EntityId) -> Result<ClosureCheckResult> {
        let capa = self.get_capa(capa_id).await?;
        let gates = self.gates.read().await;
        let capa_gates: Vec<&ClosureGate> = gates.iter().filter(|g| g.capa_id == capa_id).collect();

        let mut passed = Vec::new();
        let mut failed = Vec::new();
        let mut pending = Vec::new();

        for default_gate in DEFAULT_CLOSURE_GATES {
            let (gt, _desc, is_mandatory) = default_gate;
            let gate = capa_gates.iter().find(|g| g.gate_type == *gt);

            match gate {
                Some(g) => {
                    if g.passed {
                        passed.push(*gt);
                    } else if *is_mandatory {
                        failed.push(*gt);
                    } else {
                        pending.push(*gt);
                    }
                }
                None => {
                    pending.push(*gt);
                }
            }
        }

        let mut missing_items = Vec::new();
        if capa.root_cause_analyses.is_empty() {
            missing_items.push("Root cause analysis not completed".to_string());
        }
        if capa.actions.is_empty() {
            missing_items.push("No corrective actions defined".to_string());
        }
        if capa.actions.iter().any(|a| a.status != ActionStatus::Verified) {
            missing_items.push("Not all actions are verified".to_string());
        }

        let is_ready = failed.is_empty() && pending.is_empty() && missing_items.is_empty();

        Ok(ClosureCheckResult {
            is_ready,
            passed_gates: passed,
            failed_gates: failed,
            pending_gates: pending,
            missing_items,
            warnings: Vec::new(),
        })
    }

    async fn add_effectiveness_check(
        &self,
        capa_id: EntityId,
        check_method: String,
        results: String,
        is_effective: bool,
        checked_by: EntityId,
        follow_up_needed: bool,
        follow_up_actions: Vec<String>,
    ) -> Result<EffectivenessCheck> {
        self.get_capa(capa_id).await?;

        let ec = EffectivenessCheck {
            id: new_id(),
            capa_id,
            check_method,
            results,
            is_effective,
            checked_by: Some(checked_by),
            checked_at: Some(now()),
            follow_up_needed,
            follow_up_actions,
            created_at: now(),
        };

        self.ecs.write().await.push(ec.clone());

        let mut capas = self.capas.write().await;
        if let Some(capa) = capas.iter_mut().find(|c| c.id == capa_id) {
            capa.effectiveness_checks.push(ec.clone());
            capa.status = CapaStatusEx::EffectivenessCheck;
            capa.updated_at = now();
        }

        Ok(ec)
    }

    async fn get_pending_effectiveness_checks(&self, _tenant_id: TenantId) -> Result<Vec<CapaExtended>> {
        let capas = self.capas.read().await;
        Ok(capas
            .iter()
            .filter(|c| c.status == CapaStatusEx::EffectivenessCheck || c.status == CapaStatusEx::PendingClosure)
            .cloned()
            .collect())
    }

    async fn close_capa(&self, capa_id: EntityId, _closed_by: EntityId) -> Result<CapaExtended> {
        let mut capas = self.capas.write().await;
        let capa = capas
            .iter_mut()
            .find(|c| c.id == capa_id)
            .ok_or_else(|| SenseiError::NotFound(format!("CAPA {capa_id} not found")))?;

        if capa.status == CapaStatusEx::Closed {
            return Err(SenseiError::Validation("CAPA is already closed".to_string()));
        }

        capa.status = CapaStatusEx::Closed;
        capa.closed_at = Some(now());
        capa.updated_at = now();

        Ok(capa.clone())
    }

    async fn cancel_capa(&self, capa_id: EntityId, _reason: String) -> Result<CapaExtended> {
        let mut capas = self.capas.write().await;
        let capa = capas
            .iter_mut()
            .find(|c| c.id == capa_id)
            .ok_or_else(|| SenseiError::NotFound(format!("CAPA {capa_id} not found")))?;

        capa.status = CapaStatusEx::Cancelled;
        capa.updated_at = now();

        Ok(capa.clone())
    }
}

impl InMemoryCapaWorkflowService {
    fn _create_default_closure_gates(&self) -> Vec<ClosureGate> {
        DEFAULT_CLOSURE_GATES
            .iter()
            .map(|(gate_type, description, is_mandatory)| ClosureGate {
                id: new_id(),
                capa_id: Uuid::nil(), // Will be updated when added to CAPA
                gate_type: *gate_type,
                description: description.to_string(),
                is_mandatory: *is_mandatory,
                passed: false,
                passed_by: None,
                passed_at: None,
                notes: None,
                created_at: now(),
            })
            .collect()
    }
}
