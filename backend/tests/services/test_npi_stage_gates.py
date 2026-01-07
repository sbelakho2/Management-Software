"""
Tests for NPI Stage Gates Service.

Tests cover:
- Project lifecycle management
- Artifact tracking and validation
- Stage transition logic with gating
- Gate review management
- Readiness assessment
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.npi_stage_gates import (
    ArtifactStatus,
    ArtifactType,
    GateDecision,
    NPIArtifact,
    NPIProject,
    NPIStage,
    NPIStageGatesService,
    TransitionBlockReason,
)


@pytest.fixture
def service() -> NPIStageGatesService:
    """Create a fresh service instance."""
    return NPIStageGatesService()


@pytest.fixture
def sample_project(service: NPIStageGatesService) -> NPIProject:
    """Create a sample project."""
    return service.create_project(
        name="Test NPI Project",
        description="A test project for unit testing",
        target_sop_date=datetime.now(timezone.utc) + timedelta(days=180),
    )


class TestProjectManagement:
    """Tests for project CRUD operations."""
    
    def test_create_project(self, service: NPIStageGatesService) -> None:
        """Test creating a new project."""
        project = service.create_project(
            name="New Product Launch",
            description="Launching a new product",
        )
        
        assert project.id is not None
        assert project.name == "New Product Launch"
        assert project.current_stage == NPIStage.INTAKE
        assert project.is_active is True
        assert project.health_status == "green"
    
    def test_create_project_with_all_fields(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test creating a project with all optional fields."""
        customer_id = uuid4()
        rfq_id = uuid4()
        pm_id = uuid4()
        target_date = datetime.now(timezone.utc) + timedelta(days=90)
        
        project = service.create_project(
            name="Full Project",
            description="Complete project details",
            customer_id=customer_id,
            rfq_id=rfq_id,
            project_manager_id=pm_id,
            target_sop_date=target_date,
        )
        
        assert project.customer_id == customer_id
        assert project.rfq_id == rfq_id
        assert project.project_manager_id == pm_id
        assert project.target_sop_date == target_date
    
    def test_create_project_auto_creates_artifacts(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test that creating a project auto-creates all artifacts."""
        project = service.create_project(name="Auto Artifacts Test")
        
        artifacts = service.get_project_artifacts(project.id)
        
        # Should have all artifact types
        assert len(artifacts) == len(ArtifactType)
        
        # All should be not started
        for artifact in artifacts:
            assert artifact.status == ArtifactStatus.NOT_STARTED
            assert artifact.npi_project_id == project.id
    
    def test_get_project(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test retrieving a project."""
        retrieved = service.get_project(sample_project.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_project.id
        assert retrieved.name == sample_project.name
    
    def test_get_nonexistent_project(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test retrieving a non-existent project."""
        result = service.get_project(uuid4())
        assert result is None
    
    def test_list_projects(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test listing projects."""
        service.create_project(name="Project 1")
        service.create_project(name="Project 2")
        service.create_project(name="Project 3")
        
        projects = service.list_projects()
        
        assert len(projects) == 3
    
    def test_list_projects_filter_by_stage(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test filtering projects by stage."""
        service.create_project(name="Intake Project")
        
        intake_projects = service.list_projects(stage=NPIStage.INTAKE)
        dfm_projects = service.list_projects(stage=NPIStage.DFM)
        
        assert len(intake_projects) == 1
        assert len(dfm_projects) == 0
    
    def test_list_projects_filter_by_customer(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test filtering projects by customer."""
        customer_id = uuid4()
        service.create_project(name="Customer Project", customer_id=customer_id)
        service.create_project(name="Other Project")
        
        customer_projects = service.list_projects(customer_id=customer_id)
        
        assert len(customer_projects) == 1
        assert customer_projects[0].name == "Customer Project"
    
    def test_update_project(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test updating project fields."""
        updated = service.update_project(
            sample_project.id,
            name="Updated Name",
            priority=1,
            estimated_annual_volume=10000,
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.priority == 1
        assert updated.estimated_annual_volume == 10000
    
    def test_update_project_nonexistent(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test updating non-existent project."""
        result = service.update_project(uuid4(), name="Test")
        assert result is None
    
    def test_cancel_project(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test cancelling a project."""
        cancelled = service.cancel_project(
            sample_project.id,
            reason="Customer cancelled order",
            cancelled_by=uuid4(),
        )
        
        assert cancelled is not None
        assert cancelled.current_stage == NPIStage.CANCELLED
        assert cancelled.is_active is False
        assert "Customer cancelled order" in cancelled.health_notes


class TestArtifactManagement:
    """Tests for artifact CRUD and status management."""
    
    def test_get_project_artifacts(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test getting all artifacts for a project."""
        artifacts = service.get_project_artifacts(sample_project.id)
        
        assert len(artifacts) > 0
        for artifact in artifacts:
            assert artifact.npi_project_id == sample_project.id
    
    def test_get_artifacts_by_stage(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test filtering artifacts by stage."""
        dfm_artifacts = service.get_project_artifacts(
            sample_project.id,
            stage=NPIStage.DFM,
        )
        
        for artifact in dfm_artifacts:
            assert artifact.required_for_stage == NPIStage.DFM
    
    def test_get_required_artifacts_only(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test filtering for required artifacts only."""
        required = service.get_project_artifacts(
            sample_project.id,
            required_only=True,
        )
        
        for artifact in required:
            assert artifact.is_required is True
    
    def test_update_artifact_status(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test updating artifact status."""
        artifacts = service.get_project_artifacts(sample_project.id)
        artifact = artifacts[0]
        
        updated = service.update_artifact_status(
            artifact.id,
            status=ArtifactStatus.IN_PROGRESS,
            notes="Working on it",
        )
        
        assert updated is not None
        assert updated.status == ArtifactStatus.IN_PROGRESS
    
    def test_add_artifact_evidence(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test adding evidence to an artifact."""
        artifacts = service.get_project_artifacts(sample_project.id)
        artifact = artifacts[0]
        attachment_id = uuid4()
        
        updated = service.add_artifact_evidence(
            artifact.id,
            attachment_ids=[attachment_id],
            evidence_notes="Test evidence",
        )
        
        assert updated is not None
        assert attachment_id in updated.attachment_ids
        assert "Test evidence" in updated.evidence_notes
        # Should auto-transition to in_progress
        assert updated.status == ArtifactStatus.IN_PROGRESS
    
    def test_approve_artifact(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test approving an artifact."""
        artifacts = service.get_project_artifacts(sample_project.id)
        artifact = artifacts[0]
        approver_id = uuid4()
        
        approved = service.approve_artifact(
            artifact.id,
            approved_by=approver_id,
            notes="Looks good",
        )
        
        assert approved is not None
        assert approved.status == ArtifactStatus.APPROVED
        assert approved.reviewed_by == approver_id
        assert approved.reviewed_at is not None
        assert approved.is_complete() is True
    
    def test_reject_artifact(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test rejecting an artifact."""
        artifacts = service.get_project_artifacts(sample_project.id)
        artifact = artifacts[0]
        
        rejected = service.reject_artifact(
            artifact.id,
            rejected_by=uuid4(),
            reason="Missing critical information",
        )
        
        assert rejected is not None
        assert rejected.status == ArtifactStatus.REJECTED
        assert rejected.review_notes == "Missing critical information"
    
    def test_waive_artifact(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test waiving an artifact requirement."""
        artifacts = service.get_project_artifacts(sample_project.id)
        artifact = artifacts[0]
        waiver_id = uuid4()
        expiration = datetime.now(timezone.utc) + timedelta(days=30)
        
        waived = service.waive_artifact(
            artifact.id,
            reason="Customer provided alternative evidence",
            waived_by=waiver_id,
            expiration=expiration,
        )
        
        assert waived is not None
        assert waived.status == ArtifactStatus.WAIVED
        assert waived.waived_by == waiver_id
        assert waived.waiver_expiration == expiration
        assert waived.is_complete() is True
    
    def test_waiver_validity_check(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test waiver validity checking."""
        artifacts = service.get_project_artifacts(sample_project.id)
        artifact = artifacts[0]
        
        # Waive with future expiration
        waived = service.waive_artifact(
            artifact.id,
            reason="Temporary waiver",
            waived_by=uuid4(),
            expiration=datetime.now(timezone.utc) + timedelta(days=30),
        )
        
        assert waived is not None
        assert waived.is_waiver_valid() is True
    
    def test_waiver_expired(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test expired waiver detection."""
        artifacts = service.get_project_artifacts(sample_project.id)
        artifact = artifacts[0]
        
        # Waive with past expiration
        waived = service.waive_artifact(
            artifact.id,
            reason="Expired waiver",
            waived_by=uuid4(),
            expiration=datetime.now(timezone.utc) - timedelta(days=1),
        )
        
        assert waived is not None
        assert waived.is_waiver_valid() is False


class TestStageTransitions:
    """Tests for stage transition logic."""
    
    def test_get_next_stage(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test getting next stage in workflow."""
        assert service.get_next_stage(NPIStage.INTAKE) == NPIStage.DFM
        assert service.get_next_stage(NPIStage.DFM) == NPIStage.PROTOTYPE
        assert service.get_next_stage(NPIStage.PROTOTYPE) == NPIStage.PILOT
        assert service.get_next_stage(NPIStage.PILOT) == NPIStage.SOP
        assert service.get_next_stage(NPIStage.SOP) == NPIStage.COMPLETED
        assert service.get_next_stage(NPIStage.COMPLETED) is None
        assert service.get_next_stage(NPIStage.CANCELLED) is None
    
    def test_get_previous_stage(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test getting previous stage in workflow."""
        assert service.get_previous_stage(NPIStage.INTAKE) is None
        assert service.get_previous_stage(NPIStage.DFM) == NPIStage.INTAKE
        assert service.get_previous_stage(NPIStage.PROTOTYPE) == NPIStage.DFM
        assert service.get_previous_stage(NPIStage.PILOT) == NPIStage.PROTOTYPE
    
    def test_check_stage_readiness_missing_artifacts(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test readiness check with missing artifacts."""
        readiness = service.check_stage_readiness(
            sample_project.id,
            NPIStage.DFM,
        )
        
        assert readiness.success is False
        assert len(readiness.pending_artifacts) > 0
        assert TransitionBlockReason.ARTIFACT_NOT_APPROVED in readiness.blocked_reasons
    
    def test_check_stage_readiness_all_complete(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test readiness check with all artifacts complete."""
        # Approve all required artifacts for DFM
        artifacts = service.get_project_artifacts(
            sample_project.id,
            stage=NPIStage.DFM,
            required_only=True,
        )
        
        for artifact in artifacts:
            service.approve_artifact(artifact.id, approved_by=uuid4())
        
        readiness = service.check_stage_readiness(
            sample_project.id,
            NPIStage.DFM,
        )
        
        assert readiness.success is True
        assert len(readiness.missing_artifacts) == 0
        assert len(readiness.pending_artifacts) == 0
    
    def test_transition_stage_success(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test successful stage transition."""
        # Approve required artifacts for DFM
        artifacts = service.get_project_artifacts(
            sample_project.id,
            stage=NPIStage.DFM,
            required_only=True,
        )
        
        for artifact in artifacts:
            service.approve_artifact(artifact.id, approved_by=uuid4())
        
        result = service.transition_stage(
            sample_project.id,
            NPIStage.DFM,
            transitioned_by=uuid4(),
        )
        
        assert result.success is True
        assert result.to_stage == NPIStage.DFM
        assert result.gate_review_id is not None
        
        # Verify project was updated
        project = service.get_project(sample_project.id)
        assert project is not None
        assert project.current_stage == NPIStage.DFM
    
    def test_transition_stage_blocked(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test blocked stage transition."""
        result = service.transition_stage(
            sample_project.id,
            NPIStage.DFM,
            transitioned_by=uuid4(),
        )
        
        assert result.success is False
        assert len(result.pending_artifacts) > 0
        
        # Project should still be in INTAKE
        project = service.get_project(sample_project.id)
        assert project is not None
        assert project.current_stage == NPIStage.INTAKE
    
    def test_transition_stage_force_without_reason(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test forced transition without reason fails."""
        result = service.transition_stage(
            sample_project.id,
            NPIStage.DFM,
            transitioned_by=uuid4(),
            force=True,
            override_reason="",
        )
        
        assert result.success is False
        assert "Override reason required" in result.message
    
    def test_transition_stage_force_with_reason(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test forced transition with reason succeeds."""
        result = service.transition_stage(
            sample_project.id,
            NPIStage.DFM,
            transitioned_by=uuid4(),
            force=True,
            override_reason="Urgent customer deadline",
        )
        
        assert result.success is True
        
        # Check gate review was recorded
        review = service.get_gate_review(result.gate_review_id)
        assert review is not None
        assert review.decision == GateDecision.CONDITIONAL_GO
    
    def test_transition_invalid_stage_sequence(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test transitioning to non-sequential stage fails."""
        result = service.transition_stage(
            sample_project.id,
            NPIStage.PILOT,  # Skipping DFM and PROTOTYPE
            transitioned_by=uuid4(),
        )
        
        assert result.success is False
        assert "Invalid transition" in result.message
    
    def test_rollback_stage(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test rolling back to previous stage."""
        # First advance to DFM
        artifacts = service.get_project_artifacts(
            sample_project.id,
            stage=NPIStage.DFM,
            required_only=True,
        )
        for artifact in artifacts:
            service.approve_artifact(artifact.id, approved_by=uuid4())
        
        service.transition_stage(
            sample_project.id,
            NPIStage.DFM,
            transitioned_by=uuid4(),
        )
        
        # Now rollback
        result = service.rollback_stage(
            sample_project.id,
            reason="Quality issues found",
            rolled_back_by=uuid4(),
        )
        
        assert result.success is True
        assert result.from_stage == NPIStage.DFM
        assert result.to_stage == NPIStage.INTAKE
        
        project = service.get_project(sample_project.id)
        assert project is not None
        assert project.current_stage == NPIStage.INTAKE
    
    def test_rollback_from_first_stage(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test rollback from first stage fails."""
        result = service.rollback_stage(
            sample_project.id,
            reason="Cannot go further back",
            rolled_back_by=uuid4(),
        )
        
        assert result.success is False
        assert "Cannot roll back from first stage" in result.message


class TestGateReviews:
    """Tests for gate review management."""
    
    def test_create_gate_review(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test creating a gate review."""
        review = service.create_gate_review(
            project_id=sample_project.id,
            from_stage=NPIStage.INTAKE,
            to_stage=NPIStage.DFM,
            decision=GateDecision.GO,
            decision_rationale="All requirements met",
            reviewed_by=uuid4(),
            conditions=["Complete CTQ by next week"],
        )
        
        assert review.id is not None
        assert review.decision == GateDecision.GO
        assert len(review.conditions) == 1
    
    def test_get_gate_review(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test retrieving a gate review."""
        review = service.create_gate_review(
            project_id=sample_project.id,
            from_stage=NPIStage.INTAKE,
            to_stage=NPIStage.DFM,
            decision=GateDecision.HOLD,
            decision_rationale="Waiting for customer approval",
            reviewed_by=uuid4(),
        )
        
        retrieved = service.get_gate_review(review.id)
        
        assert retrieved is not None
        assert retrieved.id == review.id
    
    def test_get_project_gate_reviews(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test getting all gate reviews for a project."""
        # Create multiple reviews
        service.create_gate_review(
            project_id=sample_project.id,
            from_stage=NPIStage.INTAKE,
            to_stage=NPIStage.DFM,
            decision=GateDecision.NO_GO,
            decision_rationale="Missing specs",
            reviewed_by=uuid4(),
        )
        service.create_gate_review(
            project_id=sample_project.id,
            from_stage=NPIStage.INTAKE,
            to_stage=NPIStage.DFM,
            decision=GateDecision.GO,
            decision_rationale="All fixed",
            reviewed_by=uuid4(),
        )
        
        reviews = service.get_project_gate_reviews(sample_project.id)
        
        assert len(reviews) == 2
    
    def test_gate_review_with_action_items(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test gate review with action items."""
        action_items = [
            {"task": "Complete CTQ", "owner": "Engineering", "due": "2026-01-15"},
            {"task": "Get supplier quotes", "owner": "Supply Chain", "due": "2026-01-20"},
        ]
        
        review = service.create_gate_review(
            project_id=sample_project.id,
            from_stage=NPIStage.INTAKE,
            to_stage=NPIStage.DFM,
            decision=GateDecision.CONDITIONAL_GO,
            decision_rationale="Proceed with conditions",
            reviewed_by=uuid4(),
            action_items=action_items,
            follow_up_date=datetime.now(timezone.utc) + timedelta(days=14),
        )
        
        assert len(review.action_items) == 2
        assert review.follow_up_date is not None


class TestReadinessAssessment:
    """Tests for readiness and progress assessment."""
    
    def test_get_stage_completion_percentage_zero(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test completion percentage with no artifacts complete."""
        percentage = service.get_stage_completion_percentage(
            sample_project.id,
            NPIStage.DFM,
        )
        
        assert percentage == Decimal("0")
    
    def test_get_stage_completion_percentage_partial(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test completion percentage with some artifacts complete."""
        # Approve one required artifact for DFM
        artifacts = service.get_project_artifacts(
            sample_project.id,
            stage=NPIStage.DFM,
            required_only=True,
        )
        
        if artifacts:
            service.approve_artifact(artifacts[0].id, approved_by=uuid4())
        
        percentage = service.get_stage_completion_percentage(
            sample_project.id,
            NPIStage.DFM,
        )
        
        assert percentage > Decimal("0")
        assert percentage < Decimal("100")
    
    def test_get_stage_completion_percentage_full(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test completion percentage with all artifacts complete."""
        artifacts = service.get_project_artifacts(
            sample_project.id,
            stage=NPIStage.DFM,
            required_only=True,
        )
        
        for artifact in artifacts:
            service.approve_artifact(artifact.id, approved_by=uuid4())
        
        percentage = service.get_stage_completion_percentage(
            sample_project.id,
            NPIStage.DFM,
        )
        
        assert percentage == Decimal("100")
    
    def test_get_project_summary(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test getting project summary."""
        summary = service.get_project_summary(sample_project.id)
        
        assert summary is not None
        assert summary["current_stage"] == "intake"
        assert summary["total_artifacts"] > 0
        assert summary["health_status"] == "green"
        assert "next_stage_readiness" in summary
    
    def test_get_project_summary_nonexistent(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test getting summary for non-existent project."""
        summary = service.get_project_summary(uuid4())
        assert summary is None
    
    def test_get_blocked_projects(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test getting blocked projects."""
        # Create projects - they start blocked (no artifacts approved)
        service.create_project(name="Blocked 1")
        service.create_project(name="Blocked 2")
        
        blocked = service.get_blocked_projects()
        
        assert len(blocked) == 2
        for project in blocked:
            assert "pending_artifacts" in project
    
    def test_get_blocked_projects_excludes_ready(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test that ready projects are not in blocked list."""
        project = service.create_project(name="Ready Project")
        
        # Approve all required DFM artifacts
        artifacts = service.get_project_artifacts(
            project.id,
            stage=NPIStage.DFM,
            required_only=True,
        )
        for artifact in artifacts:
            service.approve_artifact(artifact.id, approved_by=uuid4())
        
        blocked = service.get_blocked_projects()
        
        # This project should not be blocked
        project_ids = [p["project_id"] for p in blocked]
        assert project.id not in project_ids
    
    def test_get_projects_by_health(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test filtering projects by health status."""
        green = service.create_project(name="Green Project")
        yellow = service.create_project(name="Yellow Project")
        red = service.create_project(name="Red Project")
        
        service.update_project_health(yellow.id, "yellow", "Some concerns")
        service.update_project_health(red.id, "red", "Critical issues")
        
        green_projects = service.get_projects_by_health("green")
        yellow_projects = service.get_projects_by_health("yellow")
        red_projects = service.get_projects_by_health("red")
        
        assert len(green_projects) == 1
        assert len(yellow_projects) == 1
        assert len(red_projects) == 1
    
    def test_update_project_health(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test updating project health status."""
        updated = service.update_project_health(
            sample_project.id,
            "yellow",
            "Behind schedule by 2 weeks",
        )
        
        assert updated is not None
        assert updated.health_status == "yellow"
        assert updated.health_notes == "Behind schedule by 2 weeks"
    
    def test_update_project_health_invalid_status(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test updating with invalid health status."""
        result = service.update_project_health(
            sample_project.id,
            "purple",
            "Invalid color",
        )
        
        assert result is None


class TestCompleteWorkflow:
    """Integration tests for complete NPI workflow."""
    
    def test_full_npi_workflow(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test complete NPI workflow from intake to completed."""
        # Create project
        project = service.create_project(
            name="Full Workflow Test",
            target_sop_date=datetime.now(timezone.utc) + timedelta(days=180),
        )
        
        assert project.current_stage == NPIStage.INTAKE
        
        # Progress through each stage
        stages = [
            NPIStage.DFM,
            NPIStage.PROTOTYPE,
            NPIStage.PILOT,
            NPIStage.SOP,
            NPIStage.COMPLETED,
        ]
        
        for target_stage in stages:
            # Approve required artifacts for target stage
            artifacts = service.get_project_artifacts(
                project.id,
                stage=target_stage,
                required_only=True,
            )
            for artifact in artifacts:
                service.approve_artifact(artifact.id, approved_by=uuid4())
            
            # Transition
            result = service.transition_stage(
                project.id,
                target_stage,
                transitioned_by=uuid4(),
            )
            
            assert result.success is True, f"Failed to transition to {target_stage}"
            
            # Verify
            updated_project = service.get_project(project.id)
            assert updated_project is not None
            assert updated_project.current_stage == target_stage
        
        # Verify final state
        final = service.get_project(project.id)
        assert final is not None
        assert final.current_stage == NPIStage.COMPLETED
        
        # Check gate reviews were created
        reviews = service.get_project_gate_reviews(project.id)
        assert len(reviews) == len(stages)
    
    def test_workflow_with_waiver(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test workflow where artifact is waived."""
        project = service.create_project(name="Waiver Test")
        
        # Get DFM artifacts
        artifacts = service.get_project_artifacts(
            project.id,
            stage=NPIStage.DFM,
            required_only=True,
        )
        
        # Approve some, waive one
        for i, artifact in enumerate(artifacts):
            if i == 0:
                service.waive_artifact(
                    artifact.id,
                    reason="Customer provided alternative",
                    waived_by=uuid4(),
                )
            else:
                service.approve_artifact(artifact.id, approved_by=uuid4())
        
        # Should still be able to transition
        result = service.transition_stage(
            project.id,
            NPIStage.DFM,
            transitioned_by=uuid4(),
        )
        
        assert result.success is True
    
    def test_workflow_with_rollback_and_retry(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test workflow with rollback and subsequent retry."""
        project = service.create_project(name="Rollback Test")
        
        # Advance to DFM
        artifacts = service.get_project_artifacts(
            project.id,
            stage=NPIStage.DFM,
            required_only=True,
        )
        for artifact in artifacts:
            service.approve_artifact(artifact.id, approved_by=uuid4())
        
        service.transition_stage(
            project.id,
            NPIStage.DFM,
            transitioned_by=uuid4(),
        )
        
        # Rollback
        service.rollback_stage(
            project.id,
            reason="Design issue found",
            rolled_back_by=uuid4(),
        )
        
        assert service.get_project(project.id).current_stage == NPIStage.INTAKE
        
        # Advance again
        result = service.transition_stage(
            project.id,
            NPIStage.DFM,
            transitioned_by=uuid4(),
        )
        
        assert result.success is True


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_transition_nonexistent_project(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test transitioning non-existent project."""
        result = service.transition_stage(
            uuid4(),
            NPIStage.DFM,
            transitioned_by=uuid4(),
        )
        
        assert result.success is False
        assert "not found" in result.message.lower()
    
    def test_update_artifact_nonexistent(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test updating non-existent artifact."""
        result = service.update_artifact_status(
            uuid4(),
            ArtifactStatus.APPROVED,
        )
        
        assert result is None
    
    def test_list_inactive_projects(
        self,
        service: NPIStageGatesService,
    ) -> None:
        """Test listing inactive projects."""
        project = service.create_project(name="To Cancel")
        service.cancel_project(project.id, "Test", uuid4())
        
        active = service.list_projects(is_active=True)
        inactive = service.list_projects(is_active=False)
        
        assert project.id not in [p.id for p in active]
        assert project.id in [p.id for p in inactive]
    
    def test_get_artifacts_by_status(
        self,
        service: NPIStageGatesService,
        sample_project: NPIProject,
    ) -> None:
        """Test filtering artifacts by status."""
        artifacts = service.get_project_artifacts(sample_project.id)
        if artifacts:
            service.approve_artifact(artifacts[0].id, approved_by=uuid4())
        
        approved = service.get_project_artifacts(
            sample_project.id,
            status=ArtifactStatus.APPROVED,
        )
        not_started = service.get_project_artifacts(
            sample_project.id,
            status=ArtifactStatus.NOT_STARTED,
        )
        
        assert len(approved) == 1
        assert len(not_started) == len(artifacts) - 1
