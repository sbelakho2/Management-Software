//! NPI Stage-Gate Workflow and Traceability services.
//!
//! - **NPI Stage Gates**: Intake → DFM → Prototype → Pilot → SOP workflow with
//!   artifact tracking, gate reviews, rollback, and health monitoring.
//! - **Traceability**: Traceability matrices and requirement links.
//! - **Certification Gate**: Validates user certifications for quality actions.
//! - **Lab Management**: Lab sample tracking and test method management.

use async_trait::async_trait;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{EntityId, TenantId, Timestamp, new_id, now};
use uuid::Uuid;

use super::models::{
    ArtifactStatus, ArtifactType, CertificationCheckResult, GateDecision, GateReview, LabSample,
    LabTestMethod, LabTestRun, ManagementReview, ManagementReviewAction, NpiArtifact, NpiStage,
    NpiProject, StageRequirements, TraceabilityLink, TraceabilityMatrix, TransitionBlockReason,
    TransitionResult,
};

// ---------------------------------------------------------------------------
// NPI Stage Gates
// ---------------------------------------------------------------------------

/// NPI Stage-Gate service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait NpiStageGateService: Send + Sync {
    /// Create a new NPI project.
    async fn create_project(
        &self,
        _tenant_id: TenantId,
        name: String,
        description: String,
        product_id: Option<Uuid>,
        customer_id: Option<Uuid>,
        project_manager_id: Option<Uuid>,
        target_sop_date: Option<Timestamp>,
        estimated_annual_volume: u64,
        estimated_unit_cost: f64,
        estimated_investment: f64,
        created_by: Uuid,
        priority: u32,
    ) -> Result<NpiProject>;

    /// List NPI projects.
    async fn list_projects(&self, _tenant_id: TenantId) -> Result<Vec<NpiProject>>;

    /// Get an NPI project by ID.
    async fn get_project(&self, id: EntityId) -> Result<NpiProject>;

    /// Update project fields.
    async fn update_project(
        &self,
        id: EntityId,
        name: Option<String>,
        description: Option<String>,
        target_sop_date: Option<Timestamp>,
    ) -> Result<NpiProject>;

    /// Cancel an NPI project.
    async fn cancel_project(&self, id: EntityId) -> Result<NpiProject>;

    /// Get artifacts for a project.
    async fn get_project_artifacts(&self, project_id: EntityId) -> Result<Vec<NpiArtifact>>;

    /// Update artifact status.
    async fn update_artifact_status(
        &self,
        artifact_id: EntityId,
        status: ArtifactStatus,
    ) -> Result<NpiArtifact>;

    /// Add evidence notes to an artifact.
    async fn add_artifact_evidence(
        &self,
        artifact_id: EntityId,
        evidence_notes: String,
    ) -> Result<NpiArtifact>;

    /// Waive an artifact requirement.
    async fn waive_artifact(
        &self,
        artifact_id: EntityId,
        waived_by: Uuid,
        waiver_reason: String,
        waiver_expiration: Option<Timestamp>,
    ) -> Result<NpiArtifact>;

    /// Approve an artifact.
    async fn approve_artifact(
        &self,
        artifact_id: EntityId,
        reviewed_by: Uuid,
        review_notes: String,
    ) -> Result<NpiArtifact>;

    /// Reject an artifact.
    async fn reject_artifact(
        &self,
        artifact_id: EntityId,
        reviewed_by: Uuid,
        review_notes: String,
    ) -> Result<NpiArtifact>;

    /// Check readiness for transitioning to the next stage.
    async fn check_stage_readiness(&self, project_id: EntityId) -> Result<TransitionResult>;

    /// Transition a project to the next stage.
    async fn transition_stage(&self, project_id: EntityId) -> Result<TransitionResult>;

    /// Rollback a project to the previous stage.
    async fn rollback_stage(&self, project_id: EntityId) -> Result<TransitionResult>;

    /// Create a gate review.
    async fn create_gate_review(
        &self,
        project_id: EntityId,
        decision: GateDecision,
        decision_rationale: String,
        conditions: Vec<String>,
        reviewed_by: Uuid,
        review_team: Vec<Uuid>,
        follow_up_date: Option<Timestamp>,
    ) -> Result<GateReview>;

    /// Get gate reviews for a project.
    async fn get_project_gate_reviews(&self, project_id: EntityId) -> Result<Vec<GateReview>>;

    /// Get stage completion percentage for a project.
    async fn get_stage_completion(&self, project_id: EntityId) -> Result<f64>;

    /// Get project summary.
    async fn get_project_summary(&self, project_id: EntityId) -> Result<serde_json::Value>;

    /// Update project health status.
    async fn update_project_health(
        &self,
        project_id: EntityId,
        health_status: String,
        health_notes: String,
    ) -> Result<NpiProject>;
}

// ---------------------------------------------------------------------------
// Traceability Matrix
// ---------------------------------------------------------------------------

/// Traceability service trait.
#[async_trait]
pub trait TraceabilityService: Send + Sync {
    /// Create a traceability matrix.
    async fn create_matrix(
        &self,
        _tenant_id: TenantId,
        title: String,
        description: String,
        product_id: Option<Uuid>,
    ) -> Result<TraceabilityMatrix>;

    /// List all traceability matrices.
    async fn list_matrices(&self, _tenant_id: TenantId) -> Result<Vec<TraceabilityMatrix>>;

    /// Add a traceability link.
    async fn add_link(
        &self,
        matrix_id: EntityId,
        source_type: String,
        source_id: Uuid,
        target_type: String,
        target_id: Uuid,
        link_type: String,
    ) -> Result<TraceabilityLink>;

    /// List links for a matrix or globally.
    async fn list_links(
        &self,
        matrix_id: Option<EntityId>,
    ) -> Result<Vec<TraceabilityLink>>;
}

// ---------------------------------------------------------------------------
// Certification Gate
// ---------------------------------------------------------------------------

/// Certification gating service trait.
#[async_trait]
pub trait CertificationGateService: Send + Sync {
    /// Assert that a user can record an inspection (certification check).
    async fn assert_user_can_record_inspection(
        &self,
        user_id: Uuid,
        inspection_type: String,
    ) -> Result<CertificationCheckResult>;
}

// ---------------------------------------------------------------------------
// Lab Management
// ---------------------------------------------------------------------------

/// Lab management service trait.
#[async_trait]
pub trait LabManagementService: Send + Sync {
    /// Create a lab test method.
    async fn create_method(
        &self,
        _tenant_id: TenantId,
        name: String,
        description: String,
        standard: Option<String>,
    ) -> Result<LabTestMethod>;

    /// Create a lab sample.
    async fn create_sample(
        &self,
        _tenant_id: TenantId,
        sample_number: String,
        material: String,
        source: String,
        lot_id: Option<String>,
    ) -> Result<LabSample>;

    /// List lab samples.
    async fn list_samples(&self, _tenant_id: TenantId) -> Result<Vec<LabSample>>;

    /// Get a lab sample.
    async fn get_sample(&self, id: EntityId) -> Result<LabSample>;

    /// Add a test run to a sample.
    async fn add_test_run(
        &self,
        sample_id: EntityId,
        method_id: Uuid,
        result: String,
        measured_value: Option<f64>,
        tested_by: Option<Uuid>,
    ) -> Result<LabTestRun>;
}

// ---------------------------------------------------------------------------
// Management Review
// ---------------------------------------------------------------------------

/// Management review service trait.
#[async_trait]
pub trait ManagementReviewService: Send + Sync {
    /// Create a management review.
    async fn create_review(
        &self,
        _tenant_id: TenantId,
        title: String,
        period_start: Timestamp,
        period_end: Timestamp,
        conducted_by: Uuid,
        notes: String,
    ) -> Result<ManagementReview>;

    /// Add an action item to a review.
    async fn add_action(
        &self,
        review_id: EntityId,
        description: String,
        owner: Uuid,
        due_date: Option<Timestamp>,
    ) -> Result<ManagementReviewAction>;

    /// List actions for a review or all.
    async fn list_actions(
        &self,
        review_id: Option<EntityId>,
    ) -> Result<Vec<ManagementReviewAction>>;

    /// Close a management review.
    async fn close_review(&self, id: EntityId) -> Result<ManagementReview>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// A certification record for the in-memory certification gate.
#[derive(Debug, Clone)]
pub struct UserCertificationEntry {
    /// The inspection type this certification covers.
    pub inspection_type: String,
    /// When the certification was issued.
    pub issued_at: Timestamp,
    /// When the certification expires (None = never expires).
    pub expires_at: Option<Timestamp>,
}

/// Combined in-memory Stage Gates, Traceability, Certification, Lab, and
/// Management Review service.
pub struct InMemoryStageGatesService {
    projects: tokio::sync::RwLock<Vec<NpiProject>>,
    artifacts: tokio::sync::RwLock<Vec<NpiArtifact>>,
    gate_reviews: tokio::sync::RwLock<Vec<GateReview>>,
    matrices: tokio::sync::RwLock<Vec<TraceabilityMatrix>>,
    links: tokio::sync::RwLock<Vec<TraceabilityLink>>,
    lab_methods: tokio::sync::RwLock<Vec<LabTestMethod>>,
    lab_samples: tokio::sync::RwLock<Vec<LabSample>>,
    lab_test_runs: tokio::sync::RwLock<Vec<LabTestRun>>,
    reviews: tokio::sync::RwLock<Vec<ManagementReview>>,
    review_actions: tokio::sync::RwLock<Vec<ManagementReviewAction>>,
    /// User certifications: maps user_id → list of certification entries.
    certifications: tokio::sync::RwLock<std::collections::HashMap<Uuid, Vec<UserCertificationEntry>>>,
}

impl InMemoryStageGatesService {
    pub fn new() -> Self {
        Self {
            projects: tokio::sync::RwLock::new(Vec::new()),
            artifacts: tokio::sync::RwLock::new(Vec::new()),
            gate_reviews: tokio::sync::RwLock::new(Vec::new()),
            matrices: tokio::sync::RwLock::new(Vec::new()),
            links: tokio::sync::RwLock::new(Vec::new()),
            lab_methods: tokio::sync::RwLock::new(Vec::new()),
            lab_samples: tokio::sync::RwLock::new(Vec::new()),
            lab_test_runs: tokio::sync::RwLock::new(Vec::new()),
            reviews: tokio::sync::RwLock::new(Vec::new()),
            review_actions: tokio::sync::RwLock::new(Vec::new()),
            certifications: tokio::sync::RwLock::new(std::collections::HashMap::new()),
        }
    }

    /// Register a certification for a user.
    pub async fn register_user_certification(
        &self,
        user_id: Uuid,
        entry: UserCertificationEntry,
    ) {
        self.certifications
            .write()
            .await
            .entry(user_id)
            .or_default()
            .push(entry);
    }

    /// Define required and optional artifacts for each NPI stage.
    fn stage_requirements(&self) -> Vec<StageRequirements> {
        vec![
            StageRequirements {
                stage: NpiStage::Intake,
                required_artifacts: vec![
                    ArtifactType::CustomerRequirements,
                    ArtifactType::InitialSpecs,
                    ArtifactType::VolumeForecast,
                    ArtifactType::TargetPricing,
                ],
                optional_artifacts: vec![ArtifactType::CtqDefinition],
                required_approvers: vec!["Project Manager".into()],
                minimum_approval_count: 1,
            },
            StageRequirements {
                stage: NpiStage::Dfm,
                required_artifacts: vec![
                    ArtifactType::CtqDefinition,
                    ArtifactType::DfmReview,
                    ArtifactType::ToolingPlan,
                    ArtifactType::ProcessCapabilityStudy,
                ],
                optional_artifacts: vec![ArtifactType::SupplierQuotes],
                required_approvers: vec![
                    "Project Manager".into(),
                    "Engineering Manager".into(),
                ],
                minimum_approval_count: 2,
            },
            StageRequirements {
                stage: NpiStage::Prototype,
                required_artifacts: vec![
                    ArtifactType::PrototypeBuild,
                    ArtifactType::PrototypeTestResults,
                    ArtifactType::DesignValidation,
                ],
                optional_artifacts: vec![ArtifactType::SupplierQuotes],
                required_approvers: vec![
                    "Project Manager".into(),
                    "Quality Manager".into(),
                ],
                minimum_approval_count: 2,
            },
            StageRequirements {
                stage: NpiStage::Pilot,
                required_artifacts: vec![
                    ArtifactType::PilotBuild,
                    ArtifactType::ProcessValidation,
                    ArtifactType::SupplierReadiness,
                    ArtifactType::PpapSubmission,
                    ArtifactType::OperatorTraining,
                ],
                optional_artifacts: vec![ArtifactType::ControlPlan],
                required_approvers: vec![
                    "Project Manager".into(),
                    "Quality Manager".into(),
                    "Production Manager".into(),
                ],
                minimum_approval_count: 3,
            },
            StageRequirements {
                stage: NpiStage::Sop,
                required_artifacts: vec![
                    ArtifactType::ProductionApproval,
                    ArtifactType::StandardWorkApproved,
                    ArtifactType::ControlPlan,
                    ArtifactType::CustomerApproval,
                ],
                optional_artifacts: Vec::new(),
                required_approvers: vec![
                    "Project Manager".into(),
                    "Quality Manager".into(),
                    "Production Manager".into(),
                    "Customer Representative".into(),
                ],
                minimum_approval_count: 4,
            },
        ]
    }

    /// Create default artifacts for each stage of a new project.
    async fn _create_default_artifacts(&self, project_id: Uuid, stages: &[NpiStage]) {
        let mut artifacts = self.artifacts.write().await;
        let requirements = self.stage_requirements();

        for req in &requirements {
            if stages.contains(&req.stage) {
                for &at in &req.required_artifacts {
                    artifacts.push(NpiArtifact {
                        id: new_id(),
                        npi_project_id: project_id,
                        artifact_type: at,
                        name: format!("{:?}", at),
                        description: String::new(),
                        status: ArtifactStatus::NotStarted,
                        is_required: true,
                        required_for_stage: req.stage,
                        attachment_ids: Vec::new(),
                        evidence_notes: String::new(),
                        reviewed_by: None,
                        reviewed_at: None,
                        review_notes: String::new(),
                        waived_by: None,
                        waived_at: None,
                        waiver_reason: String::new(),
                        waiver_expiration: None,
                        created_at: now(),
                        updated_at: now(),
                        created_by: Uuid::default(),
                    });
                }
                for &at in &req.optional_artifacts {
                    artifacts.push(NpiArtifact {
                        id: new_id(),
                        npi_project_id: project_id,
                        artifact_type: at,
                        name: format!("{:?} (Optional)", at),
                        description: String::new(),
                        status: ArtifactStatus::NotStarted,
                        is_required: false,
                        required_for_stage: req.stage,
                        attachment_ids: Vec::new(),
                        evidence_notes: String::new(),
                        reviewed_by: None,
                        reviewed_at: None,
                        review_notes: String::new(),
                        waived_by: None,
                        waived_at: None,
                        waiver_reason: String::new(),
                        waiver_expiration: None,
                        created_at: now(),
                        updated_at: now(),
                        created_by: Uuid::default(),
                    });
                }
            }
        }
    }

    /// Get artifacts for a specific stage of a project.
    fn _get_artifacts_for_stage(
        artifacts: &[NpiArtifact],
        project_id: Uuid,
        stage: NpiStage,
    ) -> Vec<&NpiArtifact> {
        artifacts
            .iter()
            .filter(|a| a.npi_project_id == project_id && a.required_for_stage == stage)
            .collect()
    }

    /// Get the next stage in the workflow.
    fn _next_stage(current: NpiStage) -> Option<NpiStage> {
        match current {
            NpiStage::Intake => Some(NpiStage::Dfm),
            NpiStage::Dfm => Some(NpiStage::Prototype),
            NpiStage::Prototype => Some(NpiStage::Pilot),
            NpiStage::Pilot => Some(NpiStage::Sop),
            NpiStage::Sop => Some(NpiStage::Completed),
            _ => None,
        }
    }

    /// Get the previous stage.
    fn _previous_stage(current: NpiStage) -> Option<NpiStage> {
        match current {
            NpiStage::Dfm => Some(NpiStage::Intake),
            NpiStage::Prototype => Some(NpiStage::Dfm),
            NpiStage::Pilot => Some(NpiStage::Prototype),
            NpiStage::Sop => Some(NpiStage::Pilot),
            NpiStage::Completed => Some(NpiStage::Sop),
            _ => None,
        }
    }
}

impl Default for InMemoryStageGatesService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl NpiStageGateService for InMemoryStageGatesService {
    async fn create_project(
        &self,
        _tenant_id: TenantId,
        name: String,
        description: String,
        product_id: Option<Uuid>,
        customer_id: Option<Uuid>,
        project_manager_id: Option<Uuid>,
        target_sop_date: Option<Timestamp>,
        estimated_annual_volume: u64,
        estimated_unit_cost: f64,
        estimated_investment: f64,
        created_by: Uuid,
        priority: u32,
    ) -> Result<NpiProject> {
        let id = new_id();
        let project = NpiProject {
            id,
            name,
            description,
            product_id,
            customer_id,
            rfq_id: None,
            quote_id: None,
            current_stage: NpiStage::Intake,
            stage_entered_at: now(),
            target_sop_date,
            actual_sop_date: None,
            project_manager_id,
            engineering_lead_id: None,
            quality_lead_id: None,
            manufacturing_lead_id: None,
            estimated_annual_volume,
            estimated_unit_cost,
            estimated_investment,
            is_active: true,
            priority,
            health_status: "On Track".into(),
            health_notes: String::new(),
            created_at: now(),
            updated_at: now(),
            created_by,
        };

        self.projects.write().await.push(project.clone());

        // Create default artifacts for all stages
        self._create_default_artifacts(
            id,
            &[
                NpiStage::Intake,
                NpiStage::Dfm,
                NpiStage::Prototype,
                NpiStage::Pilot,
                NpiStage::Sop,
            ],
        )
        .await;

        Ok(project)
    }

    async fn list_projects(&self, _tenant_id: TenantId) -> Result<Vec<NpiProject>> {
        let projects = self.projects.read().await;
        Ok(projects.clone())
    }

    async fn get_project(&self, id: EntityId) -> Result<NpiProject> {
        self.projects
            .read()
            .await
            .iter()
            .find(|p| p.id == id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))
    }

    async fn update_project(
        &self,
        id: EntityId,
        name: Option<String>,
        description: Option<String>,
        target_sop_date: Option<Timestamp>,
    ) -> Result<NpiProject> {
        let mut projects = self.projects.write().await;
        let project = projects
            .iter_mut()
            .find(|p| p.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))?;
        if let Some(n) = name {
            project.name = n;
        }
        if let Some(d) = description {
            project.description = d;
        }
        if let Some(t) = target_sop_date {
            project.target_sop_date = Some(t);
        }
        project.updated_at = now();
        Ok(project.clone())
    }

    async fn cancel_project(&self, id: EntityId) -> Result<NpiProject> {
        let mut projects = self.projects.write().await;
        let project = projects
            .iter_mut()
            .find(|p| p.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))?;
        project.current_stage = NpiStage::Cancelled;
        project.is_active = false;
        project.updated_at = now();
        Ok(project.clone())
    }

    async fn get_project_artifacts(
        &self,
        project_id: EntityId,
    ) -> Result<Vec<NpiArtifact>> {
        let artifacts = self.artifacts.read().await;
        Ok(artifacts
            .iter()
            .filter(|a| a.npi_project_id == project_id)
            .cloned()
            .collect())
    }

    async fn update_artifact_status(
        &self,
        artifact_id: EntityId,
        status: ArtifactStatus,
    ) -> Result<NpiArtifact> {
        let mut artifacts = self.artifacts.write().await;
        let artifact = artifacts
            .iter_mut()
            .find(|a| a.id == artifact_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Artifact {artifact_id} not found")))?;
        artifact.status = status;
        artifact.updated_at = now();
        Ok(artifact.clone())
    }

    async fn add_artifact_evidence(
        &self,
        artifact_id: EntityId,
        evidence_notes: String,
    ) -> Result<NpiArtifact> {
        let mut artifacts = self.artifacts.write().await;
        let artifact = artifacts
            .iter_mut()
            .find(|a| a.id == artifact_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Artifact {artifact_id} not found")))?;
        artifact.evidence_notes = evidence_notes;
        if artifact.status == ArtifactStatus::NotStarted {
            artifact.status = ArtifactStatus::InProgress;
        }
        artifact.updated_at = now();
        Ok(artifact.clone())
    }

    async fn waive_artifact(
        &self,
        artifact_id: EntityId,
        waived_by: Uuid,
        waiver_reason: String,
        waiver_expiration: Option<Timestamp>,
    ) -> Result<NpiArtifact> {
        let mut artifacts = self.artifacts.write().await;
        let artifact = artifacts
            .iter_mut()
            .find(|a| a.id == artifact_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Artifact {artifact_id} not found")))?;
        artifact.status = ArtifactStatus::Waived;
        artifact.waived_by = Some(waived_by);
        artifact.waiver_reason = waiver_reason;
        artifact.waiver_expiration = waiver_expiration;
        artifact.waived_at = Some(now());
        artifact.updated_at = now();
        Ok(artifact.clone())
    }

    async fn approve_artifact(
        &self,
        artifact_id: EntityId,
        reviewed_by: Uuid,
        review_notes: String,
    ) -> Result<NpiArtifact> {
        let mut artifacts = self.artifacts.write().await;
        let artifact = artifacts
            .iter_mut()
            .find(|a| a.id == artifact_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Artifact {artifact_id} not found")))?;
        artifact.status = ArtifactStatus::Approved;
        artifact.reviewed_by = Some(reviewed_by);
        artifact.review_notes = review_notes;
        artifact.reviewed_at = Some(now());
        artifact.updated_at = now();
        Ok(artifact.clone())
    }

    async fn reject_artifact(
        &self,
        artifact_id: EntityId,
        reviewed_by: Uuid,
        review_notes: String,
    ) -> Result<NpiArtifact> {
        let mut artifacts = self.artifacts.write().await;
        let artifact = artifacts
            .iter_mut()
            .find(|a| a.id == artifact_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Artifact {artifact_id} not found")))?;
        artifact.status = ArtifactStatus::Rejected;
        artifact.reviewed_by = Some(reviewed_by);
        artifact.review_notes = review_notes;
        artifact.reviewed_at = Some(now());
        artifact.updated_at = now();
        Ok(artifact.clone())
    }

    async fn check_stage_readiness(&self, project_id: EntityId) -> Result<TransitionResult> {
        let projects = self.projects.read().await;
        let project = projects
            .iter()
            .find(|p| p.id == project_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {project_id} not found")))?;

        if project.current_stage == NpiStage::Cancelled || project.current_stage == NpiStage::Completed {
            return Ok(TransitionResult {
                success: false,
                from_stage: project.current_stage,
                to_stage: project.current_stage,
                blocked_reasons: vec![TransitionBlockReason::FailedGateReview],
                missing_artifacts: Vec::new(),
                pending_artifacts: Vec::new(),
                message: "Project is already completed or cancelled".into(),
                gate_review_id: None,
            });
        }

        let next = Self::_next_stage(project.current_stage)
            .ok_or_else(|| SenseiError::Validation("No next stage available".into()))?;

        let artifacts = self.artifacts.read().await;
        let stage_artifacts = Self::_get_artifacts_for_stage(
            &artifacts,
            project_id,
            project.current_stage,
        );

        let mut blocked_reasons = Vec::new();
        let mut missing_artifacts = Vec::new();
        let mut pending_artifacts = Vec::new();

        for artifact in &stage_artifacts {
            if artifact.is_required {
                match artifact.status {
                    ArtifactStatus::NotStarted => {
                        blocked_reasons.push(TransitionBlockReason::MissingRequiredArtifact);
                        missing_artifacts.push(artifact.artifact_type);
                    }
                    ArtifactStatus::InProgress | ArtifactStatus::PendingReview => {
                        blocked_reasons.push(TransitionBlockReason::PendingApproval);
                        pending_artifacts.push(artifact.artifact_type);
                    }
                    ArtifactStatus::Rejected => {
                        blocked_reasons.push(TransitionBlockReason::ArtifactNotApproved);
                        pending_artifacts.push(artifact.artifact_type);
                    }
                    ArtifactStatus::Approved | ArtifactStatus::Waived => {
                        // OK - artifact is complete
                    }
                }
            }
        }

        let success = blocked_reasons.is_empty();
        let message = if success {
            format!(
                "All requirements met for transition from {:?} to {:?}",
                project.current_stage, next
            )
        } else {
            format!(
                "Cannot transition from {:?} to {:?}: {} blockers",
                project.current_stage,
                next,
                blocked_reasons.len()
            )
        };

        Ok(TransitionResult {
            success,
            from_stage: project.current_stage,
            to_stage: next,
            blocked_reasons,
            missing_artifacts,
            pending_artifacts,
            message,
            gate_review_id: None,
        })
    }

    async fn transition_stage(&self, project_id: EntityId) -> Result<TransitionResult> {
        let readiness = self.check_stage_readiness(project_id).await?;
        if !readiness.success {
            return Ok(readiness);
        }

        let mut projects = self.projects.write().await;
        let project = projects
            .iter_mut()
            .find(|p| p.id == project_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {project_id} not found")))?;

        let next = Self::_next_stage(project.current_stage)
            .ok_or_else(|| SenseiError::Validation("No next stage available".into()))?;

        let from = project.current_stage;
        project.current_stage = next;
        project.stage_entered_at = now();
        project.updated_at = now();

        if next == NpiStage::Completed {
            project.actual_sop_date = Some(now());
        }

        Ok(TransitionResult {
            success: true,
            from_stage: from,
            to_stage: next,
            blocked_reasons: Vec::new(),
            missing_artifacts: Vec::new(),
            pending_artifacts: Vec::new(),
            message: format!("Successfully transitioned from {:?} to {:?}", from, next),
            gate_review_id: None,
        })
    }

    async fn rollback_stage(&self, project_id: EntityId) -> Result<TransitionResult> {
        let mut projects = self.projects.write().await;
        let project = projects
            .iter_mut()
            .find(|p| p.id == project_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {project_id} not found")))?;

        if project.current_stage == NpiStage::Intake || project.current_stage == NpiStage::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot rollback from Intake or Cancelled stage".into(),
            ));
        }

        let prev = Self::_previous_stage(project.current_stage)
            .ok_or_else(|| SenseiError::Validation("No previous stage available".into()))?;

        let from = project.current_stage;
        project.current_stage = prev;
        project.stage_entered_at = now();
        project.updated_at = now();

        Ok(TransitionResult {
            success: true,
            from_stage: from,
            to_stage: prev,
            blocked_reasons: Vec::new(),
            missing_artifacts: Vec::new(),
            pending_artifacts: Vec::new(),
            message: format!("Rolled back from {:?} to {:?}", from, prev),
            gate_review_id: None,
        })
    }

    async fn create_gate_review(
        &self,
        project_id: EntityId,
        decision: GateDecision,
        decision_rationale: String,
        conditions: Vec<String>,
        reviewed_by: Uuid,
        review_team: Vec<Uuid>,
        follow_up_date: Option<Timestamp>,
    ) -> Result<GateReview> {
        let projects = self.projects.read().await;
        let project = projects
            .iter()
            .find(|p| p.id == project_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {project_id} not found")))?;

        let next = Self::_next_stage(project.current_stage).unwrap_or(NpiStage::Completed);

        let review = GateReview {
            id: new_id(),
            npi_project_id: project_id,
            from_stage: project.current_stage,
            to_stage: next,
            decision,
            decision_rationale,
            conditions,
            reviewed_by,
            review_team,
            scheduled_at: None,
            conducted_at: now(),
            action_items: Vec::new(),
            follow_up_date,
            created_at: now(),
        };
        self.gate_reviews.write().await.push(review.clone());
        Ok(review)
    }

    async fn get_project_gate_reviews(
        &self,
        project_id: EntityId,
    ) -> Result<Vec<GateReview>> {
        let reviews = self.gate_reviews.read().await;
        Ok(reviews
            .iter()
            .filter(|r| r.npi_project_id == project_id)
            .cloned()
            .collect())
    }

    async fn get_stage_completion(&self, project_id: EntityId) -> Result<f64> {
        let projects = self.projects.read().await;
        let project = projects
            .iter()
            .find(|p| p.id == project_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {project_id} not found")))?;

        let artifacts = self.artifacts.read().await;
        let stage_artifacts = Self::_get_artifacts_for_stage(
            &artifacts,
            project_id,
            project.current_stage,
        );

        if stage_artifacts.is_empty() {
            return Ok(100.0);
        }

        let total = stage_artifacts.len() as f64;
        let completed = stage_artifacts
            .iter()
            .filter(|a| a.is_required && a.is_complete())
            .count() as f64;

        Ok((completed / total) * 100.0)
    }

    async fn get_project_summary(&self, project_id: EntityId) -> Result<serde_json::Value> {
        let projects = self.projects.read().await;
        let project = projects
            .iter()
            .find(|p| p.id == project_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {project_id} not found")))?;

        let artifacts = self.artifacts.read().await;
        let project_artifacts: Vec<&NpiArtifact> = artifacts
            .iter()
            .filter(|a| a.npi_project_id == project_id)
            .collect();

        let total_artifacts = project_artifacts.len();
        let completed = project_artifacts
            .iter()
            .filter(|a| a.is_complete())
            .count();
        let approved = project_artifacts
            .iter()
            .filter(|a| a.status == ArtifactStatus::Approved)
            .count();
        let waived = project_artifacts
            .iter()
            .filter(|a| a.status == ArtifactStatus::Waived)
            .count();
        let rejected = project_artifacts
            .iter()
            .filter(|a| a.status == ArtifactStatus::Rejected)
            .count();
        let in_progress = project_artifacts
            .iter()
            .filter(|a| a.status == ArtifactStatus::InProgress)
            .count();

        Ok(serde_json::json!({
            "project_id": project.id,
            "name": project.name,
            "current_stage": format!("{:?}", project.current_stage),
            "is_active": project.is_active,
            "health_status": project.health_status,
            "total_artifacts": total_artifacts,
            "completed": completed,
            "approved": approved,
            "waived": waived,
            "rejected": rejected,
            "in_progress": in_progress,
            "completion_percent": if total_artifacts > 0 {
                (completed as f64 / total_artifacts as f64) * 100.0
            } else {
                0.0
            },
        }))
    }

    async fn update_project_health(
        &self,
        project_id: EntityId,
        health_status: String,
        health_notes: String,
    ) -> Result<NpiProject> {
        let mut projects = self.projects.write().await;
        let project = projects
            .iter_mut()
            .find(|p| p.id == project_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Project {project_id} not found")))?;
        project.health_status = health_status;
        project.health_notes = health_notes;
        project.updated_at = now();
        Ok(project.clone())
    }
}

#[async_trait]
impl TraceabilityService for InMemoryStageGatesService {
    async fn create_matrix(
        &self,
        _tenant_id: TenantId,
        name: String,
        description: String,
        product_id: Option<Uuid>,
    ) -> Result<TraceabilityMatrix> {
        let matrix = TraceabilityMatrix {
            id: new_id(),
            name,
            description,
            product_id,
            created_at: now(),
        };
        self.matrices.write().await.push(matrix.clone());
        Ok(matrix)
    }

    async fn list_matrices(&self, _tenant_id: TenantId) -> Result<Vec<TraceabilityMatrix>> {
        let matrices = self.matrices.read().await;
        Ok(matrices.clone())
    }

    async fn add_link(
        &self,
        matrix_id: EntityId,
        source_type: String,
        source_id: Uuid,
        target_type: String,
        target_id: Uuid,
        relationship: String,
    ) -> Result<TraceabilityLink> {
        let link = TraceabilityLink {
            id: new_id(),
            matrix_id,
            source_type,
            source_id,
            target_type,
            target_id,
            relationship,
            created_at: now(),
        };
        self.links.write().await.push(link.clone());
        Ok(link)
    }

    async fn list_links(
        &self,
        matrix_id: Option<EntityId>,
    ) -> Result<Vec<TraceabilityLink>> {
        let links = self.links.read().await;
        Ok(match matrix_id {
            Some(mid) => links
                .iter()
                .filter(|l| l.matrix_id == mid)
                .cloned()
                .collect(),
            None => links.clone(),
        })
    }
}

#[async_trait]
impl CertificationGateService for InMemoryStageGatesService {
    async fn assert_user_can_record_inspection(
        &self,
        user_id: Uuid,
        inspection_type: String,
    ) -> Result<CertificationCheckResult> {
        let certs = self.certifications.read().await;
        let user_certs = match certs.get(&user_id) {
            Some(c) => c,
            None => {
                return Ok(CertificationCheckResult {
                    is_allowed: false,
                    required_skill_ids: Vec::new(),
                    missing_skill_ids: Vec::new(),
                    message: Some(format!(
                        "User {user_id} has no certifications on file. \
                         Register a certification for inspection type '{inspection_type}' \
                         before recording inspections."
                    )),
                });
            }
        };

        // Filter certs matching the requested inspection type
        let matching: Vec<&UserCertificationEntry> = user_certs
            .iter()
            .filter(|c| c.inspection_type == inspection_type)
            .collect();

        if matching.is_empty() {
            return Ok(CertificationCheckResult {
                is_allowed: false,
                required_skill_ids: Vec::new(),
                missing_skill_ids: Vec::new(),
                message: Some(format!(
                    "User {user_id} has no certification for inspection type '{inspection_type}'. \
                     Required certification is missing."
                )),
            });
        }

        let now = chrono::Utc::now();
        let valid: Vec<&&UserCertificationEntry> = matching
            .iter()
            .filter(|c| c.expires_at.is_none_or(|exp| exp > now))
            .collect();

        if valid.is_empty() {
            return Ok(CertificationCheckResult {
                is_allowed: false,
                required_skill_ids: Vec::new(),
                missing_skill_ids: Vec::new(),
                message: Some(format!(
                    "User {user_id} has an expired certification for inspection type '{inspection_type}'. \
                     Renew the certification to record inspections."
                )),
            });
        }

        Ok(CertificationCheckResult {
            is_allowed: true,
            required_skill_ids: Vec::new(),
            missing_skill_ids: Vec::new(),
            message: None,
        })
    }
}

#[async_trait]
impl LabManagementService for InMemoryStageGatesService {
    async fn create_method(
        &self,
        _tenant_id: TenantId,
        name: String,
        description: String,
        standard: Option<String>,
    ) -> Result<LabTestMethod> {
        let method = LabTestMethod {
            id: new_id(),
            method_number: format!("M-{}", now().timestamp()),
            name,
            description,
            standard,
            created_at: now(),
        };
        self.lab_methods.write().await.push(method.clone());
        Ok(method)
    }

    async fn create_sample(
        &self,
        _tenant_id: TenantId,
        sample_number: String,
        material: String,
        source: String,
        lot_id: Option<String>,
    ) -> Result<LabSample> {
        let sample = LabSample {
            id: new_id(),
            sample_number,
            product_id: None,
            lot_id,
            sample_type: format!("{material}/{source}"),
            status: "active".to_string(),
            created_at: now(),
        };
        self.lab_samples.write().await.push(sample.clone());
        Ok(sample)
    }

    async fn list_samples(&self, _tenant_id: TenantId) -> Result<Vec<LabSample>> {
        let samples = self.lab_samples.read().await;
        Ok(samples.clone())
    }

    async fn get_sample(&self, id: EntityId) -> Result<LabSample> {
        self.lab_samples
            .read()
            .await
            .iter()
            .find(|s| s.id == id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Lab sample {id} not found")))
    }

    async fn add_test_run(
        &self,
        sample_id: EntityId,
        method_id: Uuid,
        result: String,
        value: Option<f64>,
        technician_id: Option<Uuid>,
    ) -> Result<LabTestRun> {
        // Verify the sample exists before recording the run.
        {
            let samples = self.lab_samples.read().await;
            if !samples.iter().any(|s| s.id == sample_id) {
                return Err(SenseiError::NotFound(format!(
                    "Lab sample {sample_id} not found"
                )));
            }
        }
        // Verify the method exists.
        {
            let methods = self.lab_methods.read().await;
            if !methods.iter().any(|m| m.id == method_id) {
                return Err(SenseiError::NotFound(format!(
                    "Lab test method {method_id} not found"
                )));
            }
        }

        let test_run = LabTestRun {
            id: new_id(),
            sample_id,
            method_id,
            result,
            value,
            unit: None,
            technician_id,
            tested_at: now(),
            created_at: now(),
        };
        self.lab_test_runs.write().await.push(test_run.clone());
        Ok(test_run)
    }
}

#[async_trait]
impl ManagementReviewService for InMemoryStageGatesService {
    async fn create_review(
        &self,
        _tenant_id: TenantId,
        title: String,
        period_start: Timestamp,
        period_end: Timestamp,
        _conducted_by: Uuid,
        notes: String,
    ) -> Result<ManagementReview> {
        let review = ManagementReview {
            id: new_id(),
            title,
            period_start,
            period_end,
            status: "open".to_string(),
            notes,
            actions: Vec::new(),
            created_at: now(),
        };
        self.reviews.write().await.push(review.clone());
        Ok(review)
    }

    async fn add_action(
        &self,
        review_id: EntityId,
        description: String,
        owner: Uuid,
        due_date: Option<Timestamp>,
    ) -> Result<ManagementReviewAction> {
        let action = ManagementReviewAction {
            id: new_id(),
            review_id,
            description,
            owner_id: Some(owner),
            due_date,
            status: "open".to_string(),
            created_at: now(),
        };
        self.review_actions.write().await.push(action.clone());
        Ok(action)
    }

    async fn list_actions(
        &self,
        review_id: Option<EntityId>,
    ) -> Result<Vec<ManagementReviewAction>> {
        let actions = self.review_actions.read().await;
        Ok(match review_id {
            Some(rid) => actions
                .iter()
                .filter(|a| a.review_id == rid)
                .cloned()
                .collect(),
            None => actions.clone(),
        })
    }

    async fn close_review(&self, id: EntityId) -> Result<ManagementReview> {
        let mut reviews = self.reviews.write().await;
        let review = reviews
            .iter_mut()
            .find(|r| r.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Management review {id} not found")))?;
        review.status = "closed".to_string();
        Ok(review.clone())
    }
}
