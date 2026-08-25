//! NPI Risk Register and Change Control services.
//!
//! - **NPI Risk Register**: FMEA-based risk identification, mitigation tracking,
//!   heat map visualization, and RPN trending.
//! - **Change Control**: Configuration change request workflow with approval
//!   policies, impact assessment, rollback, and snapshot management.

use async_trait::async_trait;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{EntityId, TenantId, Timestamp, new_id, now};
use uuid::Uuid;

use super::models::{
    ApprovalDecision, ApprovalPolicy, ChangeAuditEntry, ChangeRequest, ChangeRisk, ChangeStatus,
    ChangeType, ConfigSnapshot, ConfigValue, HeatMapCell, ImpactAssessment, NpiMitigationAction,
    NpiMitigationStatus, NpiRisk, NpiRiskCategory, NpiRiskReview, RiskPhase,
    RiskPriority, RiskTemplate,
};

// ---------------------------------------------------------------------------
// NPI Risk Register
// ---------------------------------------------------------------------------

/// NPI Risk Register service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait NpiRiskRegisterService: Send + Sync {
    /// Create a new risk entry.
    async fn create_risk(
        &self,
        _tenant_id: TenantId,
        title: String,
        description: String,
        category: NpiRiskCategory,
        phase: RiskPhase,
        project_id: Option<Uuid>,
        initial_severity: u32,
        initial_occurrence: u32,
        initial_detection: u32,
        target_severity: u32,
        target_occurrence: u32,
        target_detection: u32,
    ) -> Result<NpiRisk>;

    /// Create a risk from a template.
    async fn create_risk_from_template(
        &self,
        _tenant_id: TenantId,
        template_id: EntityId,
        project_id: Option<Uuid>,
        phase: RiskPhase,
    ) -> Result<NpiRisk>;

    /// Get a risk by ID.
    async fn get_risk(&self, id: EntityId) -> Result<NpiRisk>;

    /// Get a risk by its risk number.
    async fn get_risk_by_number(&self, risk_number: String) -> Result<NpiRisk>;

    /// Update risk fields.
    async fn update_risk(
        &self,
        id: EntityId,
        title: Option<String>,
        description: Option<String>,
        category: Option<NpiRiskCategory>,
        phase: Option<RiskPhase>,
    ) -> Result<NpiRisk>;

    /// Update FMEA scores.
    async fn update_scores(
        &self,
        id: EntityId,
        severity: u32,
        occurrence: u32,
        detection: u32,
    ) -> Result<NpiRisk>;

    /// Close a risk.
    async fn close_risk(&self, id: EntityId) -> Result<NpiRisk>;

    /// Mark a risk as having occurred.
    async fn mark_occurred(&self, id: EntityId) -> Result<NpiRisk>;

    /// List risks with optional filtering.
    async fn list_risks(
        &self,
        _tenant_id: TenantId,
        phase: Option<RiskPhase>,
        category: Option<NpiRiskCategory>,
        is_closed: Option<bool>,
    ) -> Result<Vec<NpiRisk>>;

    /// Add a mitigation action to a risk.
    async fn add_mitigation(
        &self,
        risk_id: EntityId,
        description: String,
        owner: String,
        due_date: Option<Timestamp>,
    ) -> Result<NpiMitigationAction>;

    /// Update mitigation status.
    async fn update_mitigation_status(
        &self,
        mitigation_id: EntityId,
        status: NpiMitigationStatus,
        effectiveness: Option<u32>,
    ) -> Result<NpiMitigationAction>;

    /// Verify a mitigation as effective.
    async fn verify_mitigation(
        &self,
        mitigation_id: EntityId,
        effectiveness: u32,
    ) -> Result<NpiMitigationAction>;

    /// Get overdue mitigations.
    async fn get_overdue_mitigations(&self) -> Result<Vec<NpiMitigationAction>>;

    /// Schedule a risk review.
    async fn schedule_review(
        &self,
        risk_id: EntityId,
        phase: RiskPhase,
        reviewed_by: Uuid,
    ) -> Result<NpiRiskReview>;

    /// Complete a risk review.
    async fn complete_review(
        &self,
        risk_id: EntityId,
        review_id: EntityId,
        severity_score: u32,
        occurrence_score: u32,
        detection_score: u32,
        comments: Option<String>,
    ) -> Result<NpiRiskReview>;

    /// Get reviews due.
    async fn get_reviews_due(&self, phase: Option<RiskPhase>) -> Result<Vec<NpiRisk>>;

    /// Get risk templates.
    async fn get_templates(&self) -> Result<Vec<RiskTemplate>>;

    /// Create a risk template.
    async fn create_template(
        &self,
        name: String,
        description: String,
        category: NpiRiskCategory,
        phase: RiskPhase,
        default_severity: u32,
        default_occurrence: u32,
        default_detection: u32,
        suggested_mitigations: Vec<String>,
    ) -> Result<RiskTemplate>;

    /// Get heat map data.
    async fn get_heat_map(&self, phase: Option<RiskPhase>) -> Result<Vec<HeatMapCell>>;

    /// Get risk summary statistics.
    async fn get_risk_summary(&self, _tenant_id: TenantId) -> Result<serde_json::Value>;
}

// ---------------------------------------------------------------------------
// Change Control
// ---------------------------------------------------------------------------

/// Change Control service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait ChangeControlService: Send + Sync {
    /// Create a change request.
    async fn create_change_request(
        &self,
        _tenant_id: TenantId,
        title: String,
        description: String,
        change_type: ChangeType,
        risk: ChangeRisk,
        config_changes: Vec<ConfigValue>,
        requested_by: Option<Uuid>,
    ) -> Result<ChangeRequest>;

    /// Get a change request by ID.
    async fn get_change_request(&self, id: EntityId) -> Result<ChangeRequest>;

    /// List change requests.
    async fn list_change_requests(&self, _tenant_id: TenantId) -> Result<Vec<ChangeRequest>>;

    /// Update a change request (only if DRAFT).
    async fn update_change_request(
        &self,
        id: EntityId,
        title: Option<String>,
        description: Option<String>,
    ) -> Result<ChangeRequest>;

    /// Cancel a change request.
    async fn cancel_change_request(&self, id: EntityId) -> Result<ChangeRequest>;

    /// Submit for review.
    async fn submit_for_review(&self, id: EntityId) -> Result<ChangeRequest>;

    /// Add impact assessment.
    async fn add_impact_assessment(
        &self,
        change_id: EntityId,
        impact_type: String,
        description: String,
        impact_level: super::models::ChangeImpact,
        affected_areas: Vec<String>,
        mitigation: Option<String>,
    ) -> Result<ImpactAssessment>;

    /// Approve a change request.
    async fn approve_change(
        &self,
        id: EntityId,
        approver_id: Uuid,
        comments: Option<String>,
    ) -> Result<ChangeRequest>;

    /// Reject a change request.
    async fn reject_change(
        &self,
        id: EntityId,
        approver_id: Uuid,
        comments: Option<String>,
    ) -> Result<ChangeRequest>;

    /// Schedule a change for implementation.
    async fn schedule_change(
        &self,
        id: EntityId,
        scheduled_for: Timestamp,
    ) -> Result<ChangeRequest>;

    /// Apply (implement) a change.
    async fn apply_change(&self, id: EntityId) -> Result<ChangeRequest>;

    /// Rollback a change.
    async fn rollback_change(&self, id: EntityId) -> Result<ChangeRequest>;

    /// Create an approval policy.
    async fn create_policy(
        &self,
        change_type: ChangeType,
        required_approvers: u32,
        required_roles: Vec<String>,
        auto_approve_threshold: Option<ChangeRisk>,
        escalation_delay_hours: u32,
    ) -> Result<ApprovalPolicy>;

    /// List approval policies.
    async fn list_policies(&self) -> Result<Vec<ApprovalPolicy>>;

    /// Create a config snapshot.
    async fn create_snapshot(
        &self,
        change_id: EntityId,
        config_data: serde_json::Value,
    ) -> Result<ConfigSnapshot>;

    /// Get snapshots for a change.
    async fn get_snapshots(&self, change_id: EntityId) -> Result<Vec<ConfigSnapshot>>;

    /// Restore a snapshot.
    async fn restore_snapshot(&self, snapshot_id: EntityId) -> Result<ChangeRequest>;

    /// Get audit trail for a change.
    async fn get_audit_trail(&self, change_id: EntityId) -> Result<Vec<ChangeAuditEntry>>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementations
// ---------------------------------------------------------------------------

/// In-memory NPI Risk Register service.
pub struct InMemoryNpiRiskRegisterService {
    risks: tokio::sync::RwLock<Vec<NpiRisk>>,
    templates: tokio::sync::RwLock<Vec<RiskTemplate>>,
    _risk_counter: std::sync::atomic::AtomicU64,
}

impl InMemoryNpiRiskRegisterService {
    pub fn new() -> Self {
        Self {
            risks: tokio::sync::RwLock::new(Vec::new()),
            templates: tokio::sync::RwLock::new(Self::default_templates()),
            _risk_counter: std::sync::atomic::AtomicU64::new(0),
        }
    }

    fn _next_risk_number(&self) -> String {
        let n = self
            ._risk_counter
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        format!("RISK-{}-{:04}", chrono::Utc::now().format("%Y%m%d"), n)
    }

    fn default_templates() -> Vec<RiskTemplate> {
        vec![
            RiskTemplate {
                id: new_id(),
                name: "Design Complexity Risk".into(),
                description: "Risk related to product design complexity and new technology".into(),
                category: NpiRiskCategory::DesignComplexity,
                phase: RiskPhase::Intake,
                default_severity: 5,
                default_occurrence: 4,
                default_detection: 4,
                suggested_mitigations: vec![
                    "Conduct DFM review early".into(),
                    "Engage supplier for design input".into(),
                ],
            },
            RiskTemplate {
                id: new_id(),
                name: "Supplier Capability Risk".into(),
                description: "Risk that supplier cannot meet quality or delivery requirements".into(),
                category: NpiRiskCategory::SupplierCapability,
                phase: RiskPhase::Dfm,
                default_severity: 7,
                default_occurrence: 3,
                default_detection: 5,
                suggested_mitigations: vec![
                    "Conduct supplier audit".into(),
                    "Request PPAP submission".into(),
                ],
            },
            RiskTemplate {
                id: new_id(),
                name: "Schedule Risk".into(),
                description: "Risk of missing key project milestones".into(),
                category: NpiRiskCategory::ScheduleRisk,
                phase: RiskPhase::Intake,
                default_severity: 6,
                default_occurrence: 4,
                default_detection: 3,
                suggested_mitigations: vec![
                    "Create detailed project plan with buffer".into(),
                    "Weekly status reviews".into(),
                ],
            },
        ]
    }
}

impl Default for InMemoryNpiRiskRegisterService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl NpiRiskRegisterService for InMemoryNpiRiskRegisterService {
    async fn create_risk(
        &self,
        _tenant_id: TenantId,
        title: String,
        description: String,
        category: NpiRiskCategory,
        phase: RiskPhase,
        project_id: Option<Uuid>,
        initial_severity: u32,
        initial_occurrence: u32,
        initial_detection: u32,
        target_severity: u32,
        target_occurrence: u32,
        target_detection: u32,
    ) -> Result<NpiRisk> {
        let risk = NpiRisk {
            id: new_id(),
            risk_number: self._next_risk_number(),
            title,
            description,
            category,
            phase,
            project_id,
            initial_severity,
            initial_occurrence,
            initial_detection,
            current_severity: initial_severity,
            current_occurrence: initial_occurrence,
            current_detection: initial_detection,
            target_severity,
            target_occurrence,
            target_detection,
            is_closed: false,
            has_occurred: false,
            occurred_at: None,
            mitigations: Vec::new(),
            reviews: Vec::new(),
            created_at: now(),
            updated_at: now(),
        };
        self.risks.write().await.push(risk.clone());
        Ok(risk)
    }

    async fn create_risk_from_template(
        &self,
        _tenant_id: TenantId,
        template_id: EntityId,
        project_id: Option<Uuid>,
        phase: RiskPhase,
    ) -> Result<NpiRisk> {
        let templates = self.templates.read().await;
        let tpl = templates
            .iter()
            .find(|t| t.id == template_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Template {template_id} not found")))?;

        let risk = NpiRisk {
            id: new_id(),
            risk_number: self._next_risk_number(),
            title: tpl.name.clone(),
            description: tpl.description.clone(),
            category: tpl.category,
            phase,
            project_id,
            initial_severity: tpl.default_severity,
            initial_occurrence: tpl.default_occurrence,
            initial_detection: tpl.default_detection,
            current_severity: tpl.default_severity,
            current_occurrence: tpl.default_occurrence,
            current_detection: tpl.default_detection,
            target_severity: tpl.default_severity.saturating_sub(2),
            target_occurrence: tpl.default_occurrence.saturating_sub(1),
            target_detection: tpl.default_detection.saturating_sub(1),
            is_closed: false,
            has_occurred: false,
            occurred_at: None,
            mitigations: Vec::new(),
            reviews: Vec::new(),
            created_at: now(),
            updated_at: now(),
        };
        self.risks.write().await.push(risk.clone());
        Ok(risk)
    }

    async fn get_risk(&self, id: EntityId) -> Result<NpiRisk> {
        self.risks
            .read()
            .await
            .iter()
            .find(|r| r.id == id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))
    }

    async fn get_risk_by_number(&self, risk_number: String) -> Result<NpiRisk> {
        self.risks
            .read()
            .await
            .iter()
            .find(|r| r.risk_number == risk_number)
            .cloned()
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Risk {risk_number} not found"))
            })
    }

    async fn update_risk(
        &self,
        id: EntityId,
        title: Option<String>,
        description: Option<String>,
        category: Option<NpiRiskCategory>,
        phase: Option<RiskPhase>,
    ) -> Result<NpiRisk> {
        let mut risks = self.risks.write().await;
        let risk = risks
            .iter_mut()
            .find(|r| r.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;
        if let Some(t) = title {
            risk.title = t;
        }
        if let Some(d) = description {
            risk.description = d;
        }
        if let Some(c) = category {
            risk.category = c;
        }
        if let Some(p) = phase {
            risk.phase = p;
        }
        risk.updated_at = now();
        Ok(risk.clone())
    }

    async fn update_scores(
        &self,
        id: EntityId,
        severity: u32,
        occurrence: u32,
        detection: u32,
    ) -> Result<NpiRisk> {
        let mut risks = self.risks.write().await;
        let risk = risks
            .iter_mut()
            .find(|r| r.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;
        risk.current_severity = severity.clamp(1, 10);
        risk.current_occurrence = occurrence.clamp(1, 10);
        risk.current_detection = detection.clamp(1, 10);
        risk.updated_at = now();
        Ok(risk.clone())
    }

    async fn close_risk(&self, id: EntityId) -> Result<NpiRisk> {
        let mut risks = self.risks.write().await;
        let risk = risks
            .iter_mut()
            .find(|r| r.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;
        risk.is_closed = true;
        risk.updated_at = now();
        Ok(risk.clone())
    }

    async fn mark_occurred(&self, id: EntityId) -> Result<NpiRisk> {
        let mut risks = self.risks.write().await;
        let risk = risks
            .iter_mut()
            .find(|r| r.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;
        risk.has_occurred = true;
        risk.occurred_at = Some(now());
        risk.updated_at = now();
        Ok(risk.clone())
    }

    async fn list_risks(
        &self,
        _tenant_id: TenantId,
        phase: Option<RiskPhase>,
        category: Option<NpiRiskCategory>,
        is_closed: Option<bool>,
    ) -> Result<Vec<NpiRisk>> {
        let risks = self.risks.read().await;
        Ok(risks
            .iter()
            .filter(|r| {
                if let Some(p) = &phase {
                    &r.phase == p
                } else {
                    true
                }
            })
            .filter(|r| {
                if let Some(c) = &category {
                    &r.category == c
                } else {
                    true
                }
            })
            .filter(|r| {
                if let Some(closed) = is_closed {
                    r.is_closed == closed
                } else {
                    true
                }
            })
            .cloned()
            .collect())
    }

    async fn add_mitigation(
        &self,
        risk_id: EntityId,
        description: String,
        owner: String,
        due_date: Option<Timestamp>,
    ) -> Result<NpiMitigationAction> {
        let mut risks = self.risks.write().await;
        let risk = risks
            .iter_mut()
            .find(|r| r.id == risk_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {risk_id} not found")))?;

        let action = NpiMitigationAction {
            id: new_id(),
            risk_id,
            description,
            owner,
            status: NpiMitigationStatus::Identified,
            due_date,
            completed_at: None,
            effectiveness: None,
            notes: None,
            created_at: now(),
            updated_at: now(),
        };
        risk.mitigations.push(action.clone());
        risk.updated_at = now();
        Ok(action)
    }

    async fn update_mitigation_status(
        &self,
        mitigation_id: EntityId,
        status: NpiMitigationStatus,
        effectiveness: Option<u32>,
    ) -> Result<NpiMitigationAction> {
        let mut risks = self.risks.write().await;
        for risk in risks.iter_mut() {
            if let Some(mit) = risk
                .mitigations
                .iter_mut()
                .find(|m| m.id == mitigation_id)
            {
                mit.status = status;
                mit.effectiveness = effectiveness;
                mit.updated_at = now();
                if matches!(status, NpiMitigationStatus::Completed | NpiMitigationStatus::Verified) {
                    mit.completed_at = Some(now());
                }
                return Ok(mit.clone());
            }
        }
        Err(SenseiError::NotFound(format!(
            "Mitigation {mitigation_id} not found"
        )))
    }

    async fn verify_mitigation(
        &self,
        mitigation_id: EntityId,
        effectiveness: u32,
    ) -> Result<NpiMitigationAction> {
        self.update_mitigation_status(mitigation_id, NpiMitigationStatus::Verified, Some(effectiveness))
            .await
    }

    async fn get_overdue_mitigations(&self) -> Result<Vec<NpiMitigationAction>> {
        let risks = self.risks.read().await;
        let now = now();
        let mut overdue = Vec::new();
        for risk in risks.iter() {
            for mit in &risk.mitigations {
                if matches!(
                    mit.status,
                    NpiMitigationStatus::Identified | NpiMitigationStatus::InProgress
                ) {
                    if let Some(due) = mit.due_date {
                        if due < now {
                            overdue.push(mit.clone());
                        }
                    }
                }
            }
        }
        Ok(overdue)
    }

    async fn schedule_review(
        &self,
        risk_id: EntityId,
        phase: RiskPhase,
        reviewed_by: Uuid,
    ) -> Result<NpiRiskReview> {
        let mut risks = self.risks.write().await;
        let risk = risks
            .iter_mut()
            .find(|r| r.id == risk_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {risk_id} not found")))?;

        // Create a placeholder review (to be completed later)
        let review = NpiRiskReview {
            id: new_id(),
            risk_id,
            phase,
            reviewed_by,
            reviewed_at: now(),
            severity_score: risk.current_severity,
            occurrence_score: risk.current_occurrence,
            detection_score: risk.current_detection,
            rpn: risk.current_rpn(),
            comments: None,
            created_at: now(),
        };
        risk.reviews.push(review.clone());
        risk.updated_at = now();
        Ok(review)
    }

    async fn complete_review(
        &self,
        risk_id: EntityId,
        review_id: EntityId,
        severity_score: u32,
        occurrence_score: u32,
        detection_score: u32,
        comments: Option<String>,
    ) -> Result<NpiRiskReview> {
        let mut risks = self.risks.write().await;
        let risk = risks
            .iter_mut()
            .find(|r| r.id == risk_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Risk {risk_id} not found")))?;

        let review = risk
            .reviews
            .iter_mut()
            .find(|r| r.id == review_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Review {review_id} not found")))?;

        review.severity_score = severity_score;
        review.occurrence_score = occurrence_score;
        review.detection_score = detection_score;
        review.rpn = severity_score * occurrence_score * detection_score;
        review.comments = comments;
        review.reviewed_at = now();

        // Update current scores to match review
        risk.current_severity = severity_score;
        risk.current_occurrence = occurrence_score;
        risk.current_detection = detection_score;
        risk.updated_at = now();

        Ok(review.clone())
    }

    async fn get_reviews_due(&self, phase: Option<RiskPhase>) -> Result<Vec<NpiRisk>> {
        let risks = self.risks.read().await;
        Ok(risks
            .iter()
            .filter(|r| !r.is_closed)
            .filter(|r| {
                if let Some(p) = &phase {
                    &r.phase == p
                } else {
                    true
                }
            })
            .cloned()
            .collect())
    }

    async fn get_templates(&self) -> Result<Vec<RiskTemplate>> {
        let templates = self.templates.read().await;
        Ok(templates.clone())
    }

    async fn create_template(
        &self,
        name: String,
        description: String,
        category: NpiRiskCategory,
        phase: RiskPhase,
        default_severity: u32,
        default_occurrence: u32,
        default_detection: u32,
        suggested_mitigations: Vec<String>,
    ) -> Result<RiskTemplate> {
        let template = RiskTemplate {
            id: new_id(),
            name,
            description,
            category,
            phase,
            default_severity,
            default_occurrence,
            default_detection,
            suggested_mitigations,
        };
        self.templates.write().await.push(template.clone());
        Ok(template)
    }

    async fn get_heat_map(&self, phase: Option<RiskPhase>) -> Result<Vec<HeatMapCell>> {
        let risks = self.risks.read().await;
        let mut cell_map: std::collections::HashMap<(u32, u32), HeatMapCell> =
            std::collections::HashMap::new();

        for risk in risks
            .iter()
            .filter(|r| !r.is_closed)
            .filter(|r| {
                if let Some(p) = &phase {
                    &r.phase == p
                } else {
                    true
                }
            }) {
            let key = (risk.current_severity, risk.current_occurrence);
            let entry = cell_map.entry(key).or_insert(HeatMapCell {
                severity: risk.current_severity,
                occurrence: risk.current_occurrence,
                count: 0,
                rpn: 0,
                risk_ids: Vec::new(),
            });
            entry.count += 1;
            entry.rpn = risk.current_rpn().max(entry.rpn);
            entry.risk_ids.push(risk.id);
        }

        let mut cells: Vec<HeatMapCell> = cell_map.into_values().collect();
        cells.sort_by_key(|b| std::cmp::Reverse(b.rpn));
        Ok(cells)
    }

    async fn get_risk_summary(&self, _tenant_id: TenantId) -> Result<serde_json::Value> {
        let risks = self.risks.read().await;
        let total = risks.len();
        let closed = risks.iter().filter(|r| r.is_closed).count();
        let occurred = risks.iter().filter(|r| r.has_occurred).count();
        let critical: Vec<&NpiRisk> = risks
            .iter()
            .filter(|r| !r.is_closed && r.priority() == RiskPriority::Critical)
            .collect();
        let high: Vec<&NpiRisk> = risks
            .iter()
            .filter(|r| !r.is_closed && r.priority() == RiskPriority::High)
            .collect();

        Ok(serde_json::json!({
            "total_risks": total,
            "closed": closed,
            "occurred": occurred,
            "open_count": total - closed,
            "critical_count": critical.len(),
            "high_count": high.len(),
            "average_rpn": if total > 0 {
                risks.iter().map(|r| r.current_rpn()).sum::<u32>() as f64 / total as f64
            } else {
                0.0
            },
        }))
    }
}

// ---------------------------------------------------------------------------
// In-Memory Change Control
// ---------------------------------------------------------------------------

/// In-memory Change Control service.
pub struct InMemoryChangeControlService {
    changes: tokio::sync::RwLock<Vec<ChangeRequest>>,
    policies: tokio::sync::RwLock<Vec<ApprovalPolicy>>,
    snapshots: tokio::sync::RwLock<Vec<ConfigSnapshot>>,
    _change_counter: std::sync::atomic::AtomicU64,
}

impl InMemoryChangeControlService {
    pub fn new() -> Self {
        Self {
            changes: tokio::sync::RwLock::new(Vec::new()),
            policies: tokio::sync::RwLock::new(Self::default_policies()),
            snapshots: tokio::sync::RwLock::new(Vec::new()),
            _change_counter: std::sync::atomic::AtomicU64::new(0),
        }
    }

    fn _next_change_number(&self) -> String {
        let n = self
            ._change_counter
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst);
        format!("CR-{}-{:04}", chrono::Utc::now().format("%Y%m%d"), n)
    }

    fn default_policies() -> Vec<ApprovalPolicy> {
        vec![
            ApprovalPolicy {
                id: new_id(),
                change_type: ChangeType::Workflow,
                required_approvers: 2,
                required_roles: vec!["Quality Manager".into(), "Production Manager".into()],
                auto_approve_threshold: Some(ChangeRisk::Low),
                escalation_delay_hours: 48,
            },
            ApprovalPolicy {
                id: new_id(),
                change_type: ChangeType::Parameter,
                required_approvers: 3,
                required_roles: vec![
                    "Quality Manager".into(),
                    "Engineering Manager".into(),
                    "Customer Representative".into(),
                ],
                auto_approve_threshold: None,
                escalation_delay_hours: 24,
            },
            ApprovalPolicy {
                id: new_id(),
                change_type: ChangeType::Integration,
                required_approvers: 2,
                required_roles: vec!["Purchasing Manager".into(), "Quality Manager".into()],
                auto_approve_threshold: Some(ChangeRisk::Medium),
                escalation_delay_hours: 72,
            },
            ApprovalPolicy {
                id: new_id(),
                change_type: ChangeType::Configuration,
                required_approvers: 4,
                required_roles: vec![
                    "Engineering Manager".into(),
                    "Quality Manager".into(),
                    "Production Manager".into(),
                    "Customer Representative".into(),
                ],
                auto_approve_threshold: None,
                escalation_delay_hours: 24,
            },
        ]
    }

    fn _add_audit_entry(
        audit_trail: &mut Vec<ChangeAuditEntry>,
        change_request_id: Uuid,
        action: String,
        details: String,
        performed_by: Option<Uuid>,
    ) {
        audit_trail.push(ChangeAuditEntry {
            id: new_id(),
            change_request_id,
            action,
            details,
            performed_by,
            performed_at: now(),
        });
    }
}

impl Default for InMemoryChangeControlService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ChangeControlService for InMemoryChangeControlService {
    async fn create_change_request(
        &self,
        _tenant_id: TenantId,
        title: String,
        description: String,
        change_type: ChangeType,
        risk: ChangeRisk,
        config_changes: Vec<ConfigValue>,
        requested_by: Option<Uuid>,
    ) -> Result<ChangeRequest> {
        let id = new_id();
        let entry = ChangeAuditEntry {
            id: new_id(),
            change_request_id: id,
            action: "created".into(),
            details: format!("Change request created: {title}"),
            performed_by: requested_by,
            performed_at: now(),
        };

        let change = ChangeRequest {
            id,
            change_number: self._next_change_number(),
            title,
            description,
            change_type,
            status: ChangeStatus::Draft,
            risk,
            config_changes,
            approvals: Vec::new(),
            impact_assessments: Vec::new(),
            audit_trail: vec![entry],
            requested_by,
            scheduled_for: None,
            applied_at: None,
            rolled_back_at: None,
            created_at: now(),
            updated_at: now(),
        };
        self.changes.write().await.push(change.clone());
        Ok(change)
    }

    async fn get_change_request(&self, id: EntityId) -> Result<ChangeRequest> {
        self.changes
            .read()
            .await
            .iter()
            .find(|c| c.id == id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {id} not found")))
    }

    async fn list_change_requests(
        &self,
        _tenant_id: TenantId,
    ) -> Result<Vec<ChangeRequest>> {
        let changes = self.changes.read().await;
        Ok(changes.clone())
    }

    async fn update_change_request(
        &self,
        id: EntityId,
        title: Option<String>,
        description: Option<String>,
    ) -> Result<ChangeRequest> {
        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {id} not found")))?;

        if change.status != ChangeStatus::Draft {
            return Err(SenseiError::Validation(
                "Can only update draft change requests".into(),
            ));
        }
        if let Some(t) = title {
            change.title = t;
        }
        if let Some(d) = description {
            change.description = d;
        }
        change.updated_at = now();
        Ok(change.clone())
    }

    async fn cancel_change_request(&self, id: EntityId) -> Result<ChangeRequest> {
        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {id} not found")))?;

        change.status = ChangeStatus::Cancelled;
        change.updated_at = now();
        Self::_add_audit_entry(
            &mut change.audit_trail,
            id,
            "cancelled".into(),
            "Change request cancelled".into(),
            None,
        );
        Ok(change.clone())
    }

    async fn submit_for_review(&self, id: EntityId) -> Result<ChangeRequest> {
        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {id} not found")))?;

        if change.status != ChangeStatus::Draft {
            return Err(SenseiError::Validation(
                "Only draft changes can be submitted for review".into(),
            ));
        }
        change.status = ChangeStatus::PendingReview;
        change.updated_at = now();
        Self::_add_audit_entry(
            &mut change.audit_trail,
            id,
            "submitted_for_review".into(),
            "Submitted for review".into(),
            None,
        );
        Ok(change.clone())
    }

    async fn add_impact_assessment(
        &self,
        change_id: EntityId,
        impact_type: String,
        description: String,
        impact_level: super::models::ChangeImpact,
        affected_areas: Vec<String>,
        mitigation: Option<String>,
    ) -> Result<ImpactAssessment> {
        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == change_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {change_id} not found")))?;

        let assessment = ImpactAssessment {
            id: new_id(),
            change_request_id: change_id,
            impact_type,
            description,
            impact_level,
            affected_areas,
            mitigation,
        };
        change.impact_assessments.push(assessment.clone());
        change.updated_at = now();
        Ok(assessment)
    }

    async fn approve_change(
        &self,
        id: EntityId,
        approver_id: Uuid,
        comments: Option<String>,
    ) -> Result<ChangeRequest> {
        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {id} not found")))?;

        if change.status != ChangeStatus::PendingReview {
            return Err(SenseiError::Validation(
                "Change is not pending review".into(),
            ));
        }

        let approval = super::models::ChangeApproval {
            id: new_id(),
            change_request_id: id,
            approver_id,
            decision: ApprovalDecision::Approved,
            comments,
            decided_at: now(),
        };
        change.approvals.push(approval);

        // Check if enough approvals collected
        let policies = self.policies.read().await;
        let policy = policies.iter().find(|p| p.change_type == change.change_type);
        let required = policy.map(|p| p.required_approvers).unwrap_or(1);

        if change.approvals.len() as u32 >= required {
            change.status = ChangeStatus::Approved;
        }
        change.updated_at = now();
        Self::_add_audit_entry(
            &mut change.audit_trail,
            id,
            "approved".into(),
            format!("Approved by {approver_id}"),
            Some(approver_id),
        );
        Ok(change.clone())
    }

    async fn reject_change(
        &self,
        id: EntityId,
        approver_id: Uuid,
        comments: Option<String>,
    ) -> Result<ChangeRequest> {
        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {id} not found")))?;

        if change.status != ChangeStatus::PendingReview {
            return Err(SenseiError::Validation(
                "Change is not pending review".into(),
            ));
        }

        let approval = super::models::ChangeApproval {
            id: new_id(),
            change_request_id: id,
            approver_id,
            decision: ApprovalDecision::Rejected,
            comments,
            decided_at: now(),
        };
        change.approvals.push(approval);
        change.status = ChangeStatus::Rejected;
        change.updated_at = now();
        Self::_add_audit_entry(
            &mut change.audit_trail,
            id,
            "rejected".into(),
            format!("Rejected by {approver_id}"),
            Some(approver_id),
        );
        Ok(change.clone())
    }

    async fn schedule_change(
        &self,
        id: EntityId,
        scheduled_for: Timestamp,
    ) -> Result<ChangeRequest> {
        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {id} not found")))?;

        if change.status != ChangeStatus::Approved {
            return Err(SenseiError::Validation(
                "Only approved changes can be scheduled".into(),
            ));
        }
        change.status = ChangeStatus::Scheduled;
        change.scheduled_for = Some(scheduled_for);
        change.updated_at = now();
        Self::_add_audit_entry(
            &mut change.audit_trail,
            id,
            "scheduled".into(),
            format!("Scheduled for {}", scheduled_for),
            None,
        );
        Ok(change.clone())
    }

    async fn apply_change(&self, id: EntityId) -> Result<ChangeRequest> {
        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {id} not found")))?;

        if change.status != ChangeStatus::Scheduled && change.status != ChangeStatus::Approved {
            return Err(SenseiError::Validation(
                "Change must be approved or scheduled to apply".into(),
            ));
        }
        change.status = ChangeStatus::Completed;
        change.applied_at = Some(now());
        change.updated_at = now();
        Self::_add_audit_entry(
            &mut change.audit_trail,
            id,
            "applied".into(),
            "Change implemented".into(),
            None,
        );
        Ok(change.clone())
    }

    async fn rollback_change(&self, id: EntityId) -> Result<ChangeRequest> {
        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {id} not found")))?;

        if change.status != ChangeStatus::Completed {
            return Err(SenseiError::Validation(
                "Only implemented changes can be rolled back".into(),
            ));
        }
        change.status = ChangeStatus::RolledBack;
        change.rolled_back_at = Some(now());
        change.updated_at = now();
        Self::_add_audit_entry(
            &mut change.audit_trail,
            id,
            "rolled_back".into(),
            "Change rolled back".into(),
            None,
        );
        Ok(change.clone())
    }

    async fn create_policy(
        &self,
        change_type: ChangeType,
        required_approvers: u32,
        required_roles: Vec<String>,
        auto_approve_threshold: Option<ChangeRisk>,
        escalation_delay_hours: u32,
    ) -> Result<ApprovalPolicy> {
        let policy = ApprovalPolicy {
            id: new_id(),
            change_type,
            required_approvers,
            required_roles,
            auto_approve_threshold,
            escalation_delay_hours,
        };
        self.policies.write().await.push(policy.clone());
        Ok(policy)
    }

    async fn list_policies(&self) -> Result<Vec<ApprovalPolicy>> {
        let policies = self.policies.read().await;
        Ok(policies.clone())
    }

    async fn create_snapshot(
        &self,
        change_id: EntityId,
        config_data: serde_json::Value,
    ) -> Result<ConfigSnapshot> {
        let snapshot = ConfigSnapshot {
            id: new_id(),
            change_request_id: change_id,
            config_data,
            created_at: now(),
        };
        self.snapshots.write().await.push(snapshot.clone());
        Ok(snapshot)
    }

    async fn get_snapshots(&self, change_id: EntityId) -> Result<Vec<ConfigSnapshot>> {
        let snapshots = self.snapshots.read().await;
        Ok(snapshots
            .iter()
            .filter(|s| s.change_request_id == change_id)
            .cloned()
            .collect())
    }

    async fn restore_snapshot(&self, snapshot_id: EntityId) -> Result<ChangeRequest> {
        let snapshots = self.snapshots.read().await;
        let snapshot = snapshots
            .iter()
            .find(|s| s.id == snapshot_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Snapshot {snapshot_id} not found")))?;

        let mut changes = self.changes.write().await;
        let change = changes
            .iter_mut()
            .find(|c| c.id == snapshot.change_request_id)
            .ok_or_else(|| {
                SenseiError::NotFound(format!(
                    "Change request {} not found",
                    snapshot.change_request_id
                ))
            })?;

        change.status = ChangeStatus::RolledBack;
        change.rolled_back_at = Some(now());
        change.updated_at = now();
        Self::_add_audit_entry(
            &mut change.audit_trail,
            snapshot.change_request_id,
            "snapshot_restored".into(),
            format!("Restored snapshot {snapshot_id}"),
            None,
        );
        Ok(change.clone())
    }

    async fn get_audit_trail(&self, change_id: EntityId) -> Result<Vec<ChangeAuditEntry>> {
        let changes = self.changes.read().await;
        let change = changes
            .iter()
            .find(|c| c.id == change_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Change request {change_id} not found")))?;
        Ok(change.audit_trail.clone())
    }
}
