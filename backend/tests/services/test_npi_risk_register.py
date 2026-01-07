"""
Tests for NPI Risk Register Service.

Tests cover:
- Risk creation and management
- FMEA-style scoring (Severity, Occurrence, Detection)
- Mitigation action tracking
- Risk review scheduling
- Templates
- Analytics and reporting
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.npi_risk_register import (
    HeatMapCell,
    MitigationAction,
    MitigationStatus,
    NPIRisk,
    NPIRiskCategory,
    NPIRiskRegisterService,
    ReviewStatus,
    RiskPhase,
    RiskPriority,
    RiskReview,
    RiskTemplate,
)


@pytest.fixture
def service() -> NPIRiskRegisterService:
    """Create a fresh service instance."""
    return NPIRiskRegisterService()


@pytest.fixture
def sample_risk(service: NPIRiskRegisterService) -> NPIRisk:
    """Create a sample risk."""
    return service.create_risk(
        title="Tight tolerance on critical dimension",
        description="Dimension X requires ±0.05mm which may be beyond process capability",
        category=NPIRiskCategory.TOLERANCE_CAPABILITY,
        npi_project_id=uuid4(),
        phase=RiskPhase.DFM,
        severity=7,
        occurrence=5,
        detection=6,
    )


@pytest.fixture
def project_id() -> uuid4:
    """Create a consistent project ID for tests."""
    return uuid4()


class TestRiskCreation:
    """Tests for risk creation."""
    
    def test_create_basic_risk(self, service: NPIRiskRegisterService) -> None:
        """Test creating a basic risk."""
        risk = service.create_risk(
            title="Test Risk",
            description="A test risk description",
            category=NPIRiskCategory.DESIGN_COMPLEXITY,
        )
        
        assert risk.id is not None
        assert risk.risk_number.startswith("NPI-R-")
        assert risk.title == "Test Risk"
        assert risk.category == NPIRiskCategory.DESIGN_COMPLEXITY
        assert risk.status == "open"
    
    def test_create_risk_with_all_fields(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test creating a risk with all fields."""
        project_id = uuid4()
        product_id = uuid4()
        owner_id = uuid4()
        target_date = datetime.now(timezone.utc) + timedelta(days=30)
        
        risk = service.create_risk(
            title="Complete Risk",
            description="Full description",
            category=NPIRiskCategory.SUPPLIER_QUALITY,
            npi_project_id=project_id,
            phase=RiskPhase.PILOT,
            product_id=product_id,
            part_number="ABC-123",
            severity=8,
            occurrence=4,
            detection=5,
            failure_mode="Incoming material fails spec",
            potential_effects=["Production delay", "Rework"],
            potential_causes=["Supplier process variation"],
            current_controls=["Incoming inspection"],
            owner_id=owner_id,
            target_resolution_date=target_date,
            potential_cost_impact=Decimal("50000"),
            potential_schedule_impact_days=14,
            tags=["supplier", "urgent"],
        )
        
        assert risk.npi_project_id == project_id
        assert risk.phase == RiskPhase.PILOT
        assert risk.part_number == "ABC-123"
        assert risk.severity == 8
        assert risk.rpn == 8 * 4 * 5  # 160
        assert len(risk.potential_effects) == 2
        assert risk.owner_id == owner_id
    
    def test_risk_score_boundaries(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test that scores are bounded to 1-10."""
        risk = service.create_risk(
            title="Boundary Test",
            description="Testing score boundaries",
            category=NPIRiskCategory.OTHER,
            severity=15,  # Should be capped to 10
            occurrence=0,  # Should be raised to 1
            detection=5,
        )
        
        assert risk.severity == 10
        assert risk.occurrence == 1
        assert risk.detection == 5
    
    def test_risk_priority_calculation(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test priority calculation from RPN."""
        # Critical: RPN > 200 or severity >= 9
        critical_risk = service.create_risk(
            title="Critical",
            description="High severity",
            category=NPIRiskCategory.OTHER,
            severity=9,
            occurrence=3,
            detection=3,
        )
        assert critical_risk.priority == RiskPriority.CRITICAL
        
        # High: RPN 100-200
        high_risk = service.create_risk(
            title="High",
            description="High RPN",
            category=NPIRiskCategory.OTHER,
            severity=5,
            occurrence=5,
            detection=5,  # RPN = 125
        )
        assert high_risk.priority == RiskPriority.HIGH
        
        # Medium: RPN 50-100
        medium_risk = service.create_risk(
            title="Medium",
            description="Medium RPN",
            category=NPIRiskCategory.OTHER,
            severity=4,
            occurrence=4,
            detection=4,  # RPN = 64
        )
        assert medium_risk.priority == RiskPriority.MEDIUM
        
        # Low: RPN < 50
        low_risk = service.create_risk(
            title="Low",
            description="Low RPN",
            category=NPIRiskCategory.OTHER,
            severity=2,
            occurrence=2,
            detection=2,  # RPN = 8
        )
        assert low_risk.priority == RiskPriority.LOW
    
    def test_create_risk_from_template(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test creating a risk from a template."""
        templates = service.get_templates()
        template = templates[0]
        
        risk = service.create_risk_from_template(
            template_id=template.id,
            title="Risk from Template",
            npi_project_id=uuid4(),
        )
        
        assert risk is not None
        assert risk.category == template.category
        assert risk.severity == template.default_severity
        assert len(risk.potential_effects) == len(template.potential_effects_template)
    
    def test_create_risk_from_nonexistent_template(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test creating risk from non-existent template."""
        result = service.create_risk_from_template(
            template_id=uuid4(),
            title="Should Fail",
        )
        assert result is None


class TestRiskRetrieval:
    """Tests for risk retrieval."""
    
    def test_get_risk_by_id(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test retrieving a risk by ID."""
        retrieved = service.get_risk(sample_risk.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_risk.id
        assert retrieved.title == sample_risk.title
    
    def test_get_risk_by_number(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test retrieving a risk by number."""
        retrieved = service.get_risk_by_number(sample_risk.risk_number)
        
        assert retrieved is not None
        assert retrieved.id == sample_risk.id
    
    def test_get_nonexistent_risk(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test retrieving non-existent risk."""
        result = service.get_risk(uuid4())
        assert result is None
    
    def test_list_risks(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test listing risks."""
        service.create_risk(
            title="Risk 1",
            description="First",
            category=NPIRiskCategory.DESIGN_COMPLEXITY,
        )
        service.create_risk(
            title="Risk 2",
            description="Second",
            category=NPIRiskCategory.SUPPLIER_QUALITY,
        )
        
        risks = service.list_risks()
        
        assert len(risks) == 2
    
    def test_list_risks_by_project(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test filtering risks by project."""
        project_id = uuid4()
        
        service.create_risk(
            title="Project Risk",
            description="In project",
            category=NPIRiskCategory.OTHER,
            npi_project_id=project_id,
        )
        service.create_risk(
            title="Other Risk",
            description="No project",
            category=NPIRiskCategory.OTHER,
        )
        
        project_risks = service.list_risks(npi_project_id=project_id)
        
        assert len(project_risks) == 1
        assert project_risks[0].title == "Project Risk"
    
    def test_list_risks_by_priority(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test filtering risks by priority."""
        service.create_risk(
            title="Critical Risk",
            description="High severity",
            category=NPIRiskCategory.OTHER,
            severity=10,
            occurrence=5,
            detection=5,
        )
        service.create_risk(
            title="Low Risk",
            description="Low scores",
            category=NPIRiskCategory.OTHER,
            severity=2,
            occurrence=2,
            detection=2,
        )
        
        critical = service.list_risks(priority=RiskPriority.CRITICAL)
        
        assert len(critical) == 1
        assert critical[0].title == "Critical Risk"
    
    def test_list_risks_excludes_closed(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test that closed risks are excluded by default."""
        risk = service.create_risk(
            title="To Close",
            description="Will be closed",
            category=NPIRiskCategory.OTHER,
        )
        service.close_risk(risk.id, uuid4(), "Issue resolved")
        
        open_risks = service.list_risks()
        all_risks = service.list_risks(include_closed=True)
        
        assert len(open_risks) == 0
        assert len(all_risks) == 1


class TestRiskUpdates:
    """Tests for risk updates."""
    
    def test_update_risk_fields(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test updating risk fields."""
        updated = service.update_risk(
            sample_risk.id,
            title="Updated Title",
            status="mitigating",
        )
        
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.status == "mitigating"
    
    def test_update_risk_scores(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test updating risk scores creates review record."""
        original_rpn = sample_risk.rpn
        
        updated = service.update_risk_scores(
            sample_risk.id,
            severity=4,
            occurrence=3,
            detection=4,
            updated_by=uuid4(),
            notes="Mitigations effective",
        )
        
        assert updated is not None
        assert updated.severity == 4
        assert updated.rpn == 4 * 3 * 4  # 48
        assert updated.rpn < original_rpn
        
        # Should have created a review record
        assert len(updated.reviews) == 1
        review = updated.reviews[0]
        assert review.previous_rpn == original_rpn
        assert review.updated_rpn == 48
    
    def test_close_risk(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test closing a risk."""
        closed = service.close_risk(
            sample_risk.id,
            closed_by=uuid4(),
            reason="Issue fully resolved",
        )
        
        assert closed is not None
        assert closed.status == "closed"
        assert closed.resolved_date is not None
        assert "fully resolved" in closed.notes
    
    def test_mark_risk_occurred(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test marking a risk as occurred."""
        occurred = service.mark_risk_occurred(
            sample_risk.id,
            actual_impact="Production delayed by 2 weeks",
            actual_cost=Decimal("25000"),
            lessons_learned="Earlier supplier audits needed",
        )
        
        assert occurred is not None
        assert occurred.status == "occurred"
        assert "Production delayed" in occurred.notes
        assert "Earlier supplier audits" in occurred.notes


class TestMitigationActions:
    """Tests for mitigation action management."""
    
    def test_add_mitigation(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test adding a mitigation action."""
        due_date = datetime.now(timezone.utc) + timedelta(days=14)
        
        mitigation = service.add_mitigation(
            sample_risk.id,
            description="Request tolerance review with customer",
            action_type="mitigate",
            owner_id=uuid4(),
            due_date=due_date,
            expected_severity_reduction=2,
        )
        
        assert mitigation is not None
        assert mitigation.description == "Request tolerance review with customer"
        assert mitigation.status == MitigationStatus.PLANNED
        
        # Risk should update to mitigating
        risk = service.get_risk(sample_risk.id)
        assert risk.status == "mitigating"
        assert len(risk.mitigations) == 1
    
    def test_update_mitigation_progress(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test updating mitigation progress."""
        mitigation = service.add_mitigation(
            sample_risk.id,
            description="Implement fix",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        
        updated = service.update_mitigation_status(
            sample_risk.id,
            mitigation.id,
            status=MitigationStatus.IN_PROGRESS,
            progress_percentage=50,
            progress_notes="Halfway done",
        )
        
        assert updated is not None
        assert updated.status == MitigationStatus.IN_PROGRESS
        assert updated.progress_percentage == 50
    
    def test_complete_mitigation(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test completing a mitigation."""
        user_id = uuid4()
        mitigation = service.add_mitigation(
            sample_risk.id,
            description="Complete this",
        )
        
        completed = service.update_mitigation_status(
            sample_risk.id,
            mitigation.id,
            status=MitigationStatus.IMPLEMENTED,
            completed_by=user_id,
        )
        
        assert completed is not None
        assert completed.status == MitigationStatus.IMPLEMENTED
        assert completed.completed_at is not None
        assert completed.completed_by == user_id
        assert completed.progress_percentage == 100
    
    def test_verify_mitigation(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test verifying mitigation effectiveness."""
        verifier_id = uuid4()
        mitigation = service.add_mitigation(
            sample_risk.id,
            description="Verify this",
        )
        
        verified = service.verify_mitigation(
            sample_risk.id,
            mitigation.id,
            verified_by=verifier_id,
            effectiveness_rating=4,
            effectiveness_notes="Mostly effective",
        )
        
        assert verified is not None
        assert verified.status == MitigationStatus.VERIFIED
        assert verified.effectiveness_rating == 4
        assert verified.effectiveness_notes == "Mostly effective"
    
    def test_get_overdue_mitigations(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test getting overdue mitigations."""
        risk = service.create_risk(
            title="Risk with overdue",
            description="Has overdue mitigation",
            category=NPIRiskCategory.OTHER,
        )
        
        past_due = datetime.now(timezone.utc) - timedelta(days=5)
        service.add_mitigation(
            risk.id,
            description="Overdue action",
            due_date=past_due,
        )
        
        overdue = service.get_overdue_mitigations()
        
        assert len(overdue) == 1
        assert overdue[0]["days_overdue"] == 5


class TestRiskReviews:
    """Tests for risk review scheduling."""
    
    def test_schedule_review(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test scheduling a risk review."""
        review_date = datetime.now(timezone.utc) + timedelta(days=7)
        reviewer_id = uuid4()
        
        review = service.schedule_review(
            sample_risk.id,
            scheduled_date=review_date,
            reviewer_id=reviewer_id,
        )
        
        assert review is not None
        assert review.scheduled_date == review_date
        assert review.status == ReviewStatus.PENDING
        
        risk = service.get_risk(sample_risk.id)
        assert risk.next_review_date == review_date
    
    def test_complete_review(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test completing a risk review."""
        review = service.schedule_review(
            sample_risk.id,
            scheduled_date=datetime.now(timezone.utc),
        )
        
        completed = service.complete_review(
            sample_risk.id,
            review.id,
            reviewer_id=uuid4(),
            updated_severity=5,
            updated_occurrence=4,
            notes="Mitigations reducing risk",
        )
        
        assert completed is not None
        assert completed.status == ReviewStatus.COMPLETED
        assert completed.updated_severity == 5
        
        risk = service.get_risk(sample_risk.id)
        assert risk.severity == 5
        assert risk.last_review_date is not None
    
    def test_complete_review_closes_risk(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test that review can close a risk."""
        review = service.schedule_review(
            sample_risk.id,
            scheduled_date=datetime.now(timezone.utc),
        )
        
        completed = service.complete_review(
            sample_risk.id,
            review.id,
            reviewer_id=uuid4(),
            risk_closed=True,
            notes="Risk no longer applicable",
        )
        
        assert completed is not None
        
        risk = service.get_risk(sample_risk.id)
        assert risk.status == "closed"
    
    def test_get_reviews_due(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test getting reviews due soon."""
        # Create risk with imminent review
        risk = service.create_risk(
            title="Review Due Soon",
            description="Has review coming up",
            category=NPIRiskCategory.OTHER,
        )
        
        # Set review date to tomorrow
        service.update_risk(
            risk.id,
            next_review_date=datetime.now(timezone.utc) + timedelta(days=1),
        )
        
        due = service.get_reviews_due(days_ahead=7)
        
        assert len(due) >= 1
        assert any(r["risk_id"] == risk.id for r in due)
    
    def test_risk_is_review_due(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test checking if review is due."""
        # Set review to past
        service.update_risk(
            sample_risk.id,
            next_review_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        
        risk = service.get_risk(sample_risk.id)
        assert risk.is_review_due() is True


class TestTemplates:
    """Tests for risk templates."""
    
    def test_get_all_templates(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test getting all templates."""
        templates = service.get_templates()
        
        assert len(templates) >= 5  # Default templates
    
    def test_get_templates_by_category(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test filtering templates by category."""
        supplier_templates = service.get_templates(
            category=NPIRiskCategory.SINGLE_SOURCE,
        )
        
        assert len(supplier_templates) >= 1
        assert all(
            t.category == NPIRiskCategory.SINGLE_SOURCE
            for t in supplier_templates
        )
    
    def test_get_templates_by_phase(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test filtering templates by phase."""
        dfm_templates = service.get_templates(phase=RiskPhase.DFM)
        
        assert len(dfm_templates) >= 1
        assert all(
            t.phase in (RiskPhase.DFM, RiskPhase.ALL_PHASES)
            for t in dfm_templates
        )
    
    def test_get_template_by_id(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test getting template by ID."""
        templates = service.get_templates()
        template_id = templates[0].id
        
        template = service.get_template(template_id)
        
        assert template is not None
        assert template.id == template_id
    
    def test_create_custom_template(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test creating a custom template."""
        template = service.create_template(
            name="Custom Risk Template",
            description="A custom template",
            category=NPIRiskCategory.OTHER,
            phase=RiskPhase.PROTOTYPE,
            default_severity=6,
            default_occurrence=4,
            default_detection=5,
            failure_mode_template="Custom failure mode",
            potential_effects_template=["Effect 1", "Effect 2"],
            recommended_controls=["Control 1"],
            recommended_mitigations=["Mitigation 1"],
        )
        
        assert template.id is not None
        assert template.name == "Custom Risk Template"
        assert template.default_severity == 6


class TestAnalytics:
    """Tests for analytics and reporting."""
    
    def test_get_heat_map(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test generating risk heat map."""
        # Create some risks
        service.create_risk(
            title="Risk 1",
            description="Sev 8, Occ 6",
            category=NPIRiskCategory.OTHER,
            severity=8,
            occurrence=6,
            detection=5,
        )
        service.create_risk(
            title="Risk 2",
            description="Sev 8, Occ 6",
            category=NPIRiskCategory.OTHER,
            severity=8,
            occurrence=6,
            detection=3,
        )
        
        heat_map = service.get_heat_map()
        
        assert len(heat_map) >= 1
        
        # Should have cell with 2 risks at (8, 6)
        cell = next(
            (c for c in heat_map if c.severity == 8 and c.occurrence == 6),
            None,
        )
        assert cell is not None
        assert cell.count == 2
    
    def test_get_risk_summary(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test getting risk summary."""
        project_id = uuid4()
        
        service.create_risk(
            title="Critical",
            description="High severity",
            category=NPIRiskCategory.SUPPLIER_QUALITY,
            npi_project_id=project_id,
            severity=10,
            occurrence=5,
            detection=5,
        )
        service.create_risk(
            title="Low",
            description="Low severity",
            category=NPIRiskCategory.DESIGN_COMPLEXITY,
            npi_project_id=project_id,
            severity=2,
            occurrence=2,
            detection=2,
        )
        
        summary = service.get_risk_summary(npi_project_id=project_id)
        
        assert summary["total_open"] == 2
        assert summary["by_priority"]["critical"] == 1
        assert summary["by_priority"]["low"] == 1
        assert summary["by_category"]["supplier_quality"] == 1
        assert summary["average_rpn"] > 0
    
    def test_get_project_risk_report(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test generating project risk report."""
        project_id = uuid4()
        
        risk1 = service.create_risk(
            title="Open Risk",
            description="Still open",
            category=NPIRiskCategory.PROCESS_CAPABILITY,
            npi_project_id=project_id,
            severity=7,
            occurrence=5,
            detection=4,
        )
        
        risk2 = service.create_risk(
            title="Closed Risk",
            description="Already resolved",
            category=NPIRiskCategory.TOOLING_DESIGN,
            npi_project_id=project_id,
        )
        service.close_risk(risk2.id, uuid4(), "Resolved")
        
        report = service.get_project_risk_report(project_id)
        
        assert report["project_id"] == project_id
        assert report["total_risks"] == 2
        assert report["open_risks"] == 1
        assert report["closed_risks"] == 1
        assert len(report["top_risks"]) == 1
        assert "heat_map" in report
    
    def test_get_rpn_trend(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test getting RPN trend over time."""
        # Create a risk with higher initial scores
        risk = service.create_risk(
            title="Risk for trend",
            description="Track RPN trend",
            category=NPIRiskCategory.OTHER,
            severity=8,
            occurrence=7,
            detection=6,  # Initial RPN = 336
        )
        
        # Update scores to create trend - lowering values
        service.update_risk_scores(
            risk.id,
            severity=6,
            occurrence=5,
            detection=5,  # RPN = 150
            updated_by=uuid4(),
        )
        
        service.update_risk_scores(
            risk.id,
            severity=4,
            occurrence=3,
            detection=3,  # RPN = 36
            updated_by=uuid4(),
        )
        
        trend = service.get_rpn_trend(risk.id)
        
        assert len(trend) == 3  # Initial + 2 updates
        # Should be decreasing
        assert trend[0]["rpn"] > trend[-1]["rpn"]
    
    def test_empty_summary(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test summary with no risks."""
        summary = service.get_risk_summary(npi_project_id=uuid4())
        
        assert summary["total_open"] == 0
        assert summary["average_rpn"] == 0


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_update_nonexistent_risk(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test updating non-existent risk."""
        result = service.update_risk(uuid4(), title="Should Fail")
        assert result is None
    
    def test_add_mitigation_to_nonexistent_risk(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test adding mitigation to non-existent risk."""
        result = service.add_mitigation(
            uuid4(),
            description="Should fail",
        )
        assert result is None
    
    def test_update_nonexistent_mitigation(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test updating non-existent mitigation."""
        result = service.update_mitigation_status(
            sample_risk.id,
            uuid4(),
            MitigationStatus.IMPLEMENTED,
        )
        assert result is None
    
    def test_heat_map_cell_level(self) -> None:
        """Test heat map cell level calculation."""
        critical = HeatMapCell(severity=10, occurrence=8)
        assert critical.level == "critical"
        
        high = HeatMapCell(severity=5, occurrence=6)
        assert high.level == "high"
        
        medium = HeatMapCell(severity=3, occurrence=4)
        assert medium.level == "medium"
        
        low = HeatMapCell(severity=2, occurrence=2)
        assert low.level == "low"
    
    def test_risk_open_mitigations(
        self,
        service: NPIRiskRegisterService,
        sample_risk: NPIRisk,
    ) -> None:
        """Test getting open mitigations from risk."""
        # Add various mitigations
        m1 = service.add_mitigation(sample_risk.id, "Planned")
        m2 = service.add_mitigation(sample_risk.id, "In Progress")
        m3 = service.add_mitigation(sample_risk.id, "Done")
        
        service.update_mitigation_status(
            sample_risk.id,
            m2.id,
            MitigationStatus.IN_PROGRESS,
        )
        service.update_mitigation_status(
            sample_risk.id,
            m3.id,
            MitigationStatus.VERIFIED,
        )
        
        risk = service.get_risk(sample_risk.id)
        open_mitigations = risk.get_open_mitigations()
        
        assert len(open_mitigations) == 2  # Planned and In Progress


class TestCompleteWorkflow:
    """Integration tests for complete workflows."""
    
    def test_complete_risk_lifecycle(
        self,
        service: NPIRiskRegisterService,
    ) -> None:
        """Test complete risk lifecycle from creation to closure."""
        project_id = uuid4()
        owner_id = uuid4()
        
        # 1. Create risk from template
        templates = service.get_templates(
            category=NPIRiskCategory.TOLERANCE_CAPABILITY,
        )
        template = templates[0]
        
        risk = service.create_risk_from_template(
            template_id=template.id,
            title="Critical Dimension Risk",
            npi_project_id=project_id,
            owner_id=owner_id,
        )
        
        assert risk.status == "open"
        original_rpn = risk.rpn
        
        # 2. Add mitigations
        m1 = service.add_mitigation(
            risk.id,
            description="Request tolerance review",
            expected_severity_reduction=2,
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        
        m2 = service.add_mitigation(
            risk.id,
            description="Upgrade measurement equipment",
            expected_detection_improvement=3,
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
        )
        
        assert service.get_risk(risk.id).status == "mitigating"
        
        # 3. Complete mitigations
        service.update_mitigation_status(
            risk.id,
            m1.id,
            MitigationStatus.IMPLEMENTED,
            completed_by=owner_id,
        )
        
        service.verify_mitigation(
            risk.id,
            m1.id,
            verified_by=uuid4(),
            effectiveness_rating=5,
        )
        
        service.update_mitigation_status(
            risk.id,
            m2.id,
            MitigationStatus.IMPLEMENTED,
            completed_by=owner_id,
        )
        
        # 4. Update risk scores after mitigation
        updated = service.update_risk_scores(
            risk.id,
            severity=5,  # Reduced
            occurrence=3,  # Reduced
            detection=3,  # Improved
            updated_by=owner_id,
            notes="Mitigations effective",
        )
        
        assert updated.rpn < original_rpn
        
        # 5. Close risk
        closed = service.close_risk(
            risk.id,
            closed_by=owner_id,
            reason="Risk successfully mitigated",
        )
        
        assert closed.status == "closed"
        assert closed.resolved_date is not None
        
        # 6. Verify trend shows improvement
        trend = service.get_rpn_trend(risk.id)
        assert len(trend) >= 2
        assert trend[0]["rpn"] > trend[-1]["rpn"]
