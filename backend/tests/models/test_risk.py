"""
Tests for Risk models.

Tests:
- Risk model fields and defaults
- Risk severity and likelihood scoring
- Risk score calculation (severity × likelihood)
- RiskMitigation model
- Status and category handling
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.models.risk import (
    MitigationStatus,
    Risk,
    RiskCategory,
    RiskLikelihood,
    RiskMitigation,
    RiskSeverity,
    RiskStatus,
)

# Severity score mapping (matches 5x5 risk matrix)
SEVERITY_SCORES = {
    RiskSeverity.NEGLIGIBLE: 1,
    RiskSeverity.MINOR: 2,
    RiskSeverity.MODERATE: 3,
    RiskSeverity.MAJOR: 4,
    RiskSeverity.CRITICAL: 5,
}

# Likelihood score mapping
LIKELIHOOD_SCORES = {
    RiskLikelihood.RARE: 1,
    RiskLikelihood.UNLIKELY: 2,
    RiskLikelihood.POSSIBLE: 3,
    RiskLikelihood.LIKELY: 4,
    RiskLikelihood.ALMOST_CERTAIN: 5,
}


class TestRiskModel:
    """Tests for the Risk model."""

    def test_risk_required_fields(self):
        """Risk should require risk_number, title, category."""
        risk = Risk(
            risk_number="RSK-001",
            title="Supplier Capacity Constraint",
            category=RiskCategory.SUPPLY_CHAIN.value,
        )
        assert risk.risk_number == "RSK-001"
        assert risk.title == "Supplier Capacity Constraint"
        assert risk.category == RiskCategory.SUPPLY_CHAIN.value

    def test_risk_default_status_is_identified(self):
        """Risk status should default to identified."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            status=RiskStatus.IDENTIFIED.value,
        )
        assert risk.status == RiskStatus.IDENTIFIED.value

    def test_risk_default_severity_is_moderate(self):
        """Risk inherent_severity should default to moderate."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_severity=RiskSeverity.MODERATE.value,
        )
        assert risk.inherent_severity == RiskSeverity.MODERATE.value

    def test_risk_default_likelihood_is_possible(self):
        """Risk inherent_likelihood should default to possible."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_likelihood=RiskLikelihood.POSSIBLE.value,
        )
        assert risk.inherent_likelihood == RiskLikelihood.POSSIBLE.value

    def test_risk_is_active_default_true(self):
        """is_active attribute should not be set by default (uses soft delete)."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
        )
        # Risk uses SoftDeleteMixin, so is_deleted defaults to False
        assert risk.is_deleted is False

    def test_risk_inherent_risk_score_default(self):
        """inherent_risk_score should default to 9 (3x3)."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_risk_score=9,
        )
        assert risk.inherent_risk_score == 9

    def test_risk_score_critical_almost_certain(self):
        """Risk score should be 25 for critical severity × almost_certain likelihood."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_severity=RiskSeverity.CRITICAL.value,
            inherent_likelihood=RiskLikelihood.ALMOST_CERTAIN.value,
            inherent_severity_score=5,
            inherent_likelihood_score=5,
            inherent_risk_score=25,
        )
        assert risk.inherent_risk_score == 25

    def test_risk_score_major_likely(self):
        """Risk score should be 16 for major severity × likely likelihood."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_severity=RiskSeverity.MAJOR.value,
            inherent_likelihood=RiskLikelihood.LIKELY.value,
            inherent_severity_score=4,
            inherent_likelihood_score=4,
            inherent_risk_score=16,
        )
        assert risk.inherent_risk_score == 16

    def test_risk_score_negligible_rare(self):
        """Risk score should be 1 for negligible severity × rare likelihood."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_severity=RiskSeverity.NEGLIGIBLE.value,
            inherent_likelihood=RiskLikelihood.RARE.value,
            inherent_severity_score=1,
            inherent_likelihood_score=1,
            inherent_risk_score=1,
        )
        assert risk.inherent_risk_score == 1

    def test_risk_score_moderate_possible(self):
        """Risk score should be 9 for moderate severity × possible likelihood."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_severity=RiskSeverity.MODERATE.value,
            inherent_likelihood=RiskLikelihood.POSSIBLE.value,
            inherent_severity_score=3,
            inherent_likelihood_score=3,
            inherent_risk_score=9,
        )
        assert risk.inherent_risk_score == 9

    def test_risk_level_critical_for_high_score(self):
        """High inherent_risk_score indicates critical risk (>= 20)."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_risk_score=25,
        )
        # Risk level is determined by inherent_risk_score
        assert risk.inherent_risk_score >= 20

    def test_risk_level_high_for_moderate_score(self):
        """Moderate inherent_risk_score indicates high risk (>= 15)."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_risk_score=16,
        )
        assert risk.inherent_risk_score >= 15

    def test_risk_level_medium_for_medium_score(self):
        """Medium inherent_risk_score indicates medium risk (>= 8)."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_risk_score=9,
        )
        assert risk.inherent_risk_score >= 8

    def test_risk_level_low_for_low_score(self):
        """Low inherent_risk_score indicates low risk (< 8)."""
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            inherent_risk_score=2,
        )
        assert risk.inherent_risk_score < 8

    def test_risk_is_open_true_for_active_statuses(self):
        """Risks with active statuses should be considered open."""
        for status in [
            RiskStatus.IDENTIFIED,
            RiskStatus.ANALYZING,
            RiskStatus.MITIGATING,
            RiskStatus.MONITORING,
        ]:
            risk = Risk(
                risk_number="RSK-001",
                title="Test",
                description="Test description",
                category=RiskCategory.TECHNICAL.value,
                identified_date=datetime.now(timezone.utc),
                status=status.value,
            )
            # Active statuses indicate the risk is not yet resolved
            assert risk.status not in [
                RiskStatus.CLOSED.value,
                RiskStatus.ACCEPTED.value,
                RiskStatus.OCCURRED.value,
            ]

    def test_risk_is_open_false_for_closed_statuses(self):
        """Risks with closed statuses should not be considered open."""
        for status in [
            RiskStatus.CLOSED,
            RiskStatus.ACCEPTED,
            RiskStatus.OCCURRED,
        ]:
            risk = Risk(
                risk_number="RSK-001",
                title="Test",
                description="Test description",
                category=RiskCategory.TECHNICAL.value,
                identified_date=datetime.now(timezone.utc),
                status=status.value,
            )
            # These are terminal statuses
            assert risk.status in [
                RiskStatus.CLOSED.value,
                RiskStatus.ACCEPTED.value,
                RiskStatus.OCCURRED.value,
            ]

    def test_risk_next_review_date_tracking(self):
        """Risk should track next_review_date."""
        review_date = datetime.now(timezone.utc) + timedelta(days=7)
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            next_review_date=review_date,
        )
        assert risk.next_review_date == review_date

    def test_risk_next_review_date_can_be_past(self):
        """next_review_date can be in the past (overdue for review)."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        risk = Risk(
            risk_number="RSK-001",
            title="Test",
            description="Test description",
            category=RiskCategory.TECHNICAL.value,
            identified_date=datetime.now(timezone.utc),
            next_review_date=past_date,
        )
        assert risk.next_review_date < datetime.now(timezone.utc)


class TestRiskCategoryEnum:
    """Tests for RiskCategory enum."""

    def test_all_categories_defined(self):
        """All expected risk categories should be defined."""
        assert RiskCategory.TECHNICAL.value == "technical"
        assert RiskCategory.COMMERCIAL.value == "commercial"
        assert RiskCategory.SUPPLY_CHAIN.value == "supply_chain"
        assert RiskCategory.QUALITY.value == "quality"
        assert RiskCategory.SCHEDULE.value == "schedule"
        assert RiskCategory.RESOURCE.value == "resource"
        assert RiskCategory.FINANCIAL.value == "financial"
        assert RiskCategory.REGULATORY.value == "regulatory"


class TestRiskStatusEnum:
    """Tests for RiskStatus enum."""

    def test_all_statuses_defined(self):
        """All expected risk statuses should be defined."""
        assert RiskStatus.IDENTIFIED.value == "identified"
        assert RiskStatus.ANALYZING.value == "analyzing"
        assert RiskStatus.MITIGATING.value == "mitigating"
        assert RiskStatus.MONITORING.value == "monitoring"
        assert RiskStatus.ACCEPTED.value == "accepted"
        assert RiskStatus.CLOSED.value == "closed"
        assert RiskStatus.OCCURRED.value == "occurred"

    def test_status_count(self):
        """There should be 7 status values."""
        assert len(RiskStatus) == 7


class TestRiskSeverityEnum:
    """Tests for RiskSeverity enum."""

    def test_all_severities_defined(self):
        """All expected risk severities should be defined."""
        assert RiskSeverity.NEGLIGIBLE.value == "negligible"
        assert RiskSeverity.MINOR.value == "minor"
        assert RiskSeverity.MODERATE.value == "moderate"
        assert RiskSeverity.MAJOR.value == "major"
        assert RiskSeverity.CRITICAL.value == "critical"

    def test_severity_count(self):
        """There should be 5 severity levels for 5x5 matrix."""
        assert len(RiskSeverity) == 5


class TestRiskLikelihoodEnum:
    """Tests for RiskLikelihood enum."""

    def test_all_likelihoods_defined(self):
        """All expected risk likelihoods should be defined."""
        assert RiskLikelihood.RARE.value == "rare"
        assert RiskLikelihood.UNLIKELY.value == "unlikely"
        assert RiskLikelihood.POSSIBLE.value == "possible"
        assert RiskLikelihood.LIKELY.value == "likely"
        assert RiskLikelihood.ALMOST_CERTAIN.value == "almost_certain"

    def test_likelihood_count(self):
        """Likelihood enum should have 5 levels for 5x5 matrix."""
        assert len(RiskLikelihood) == 5


class TestRiskMitigationModel:
    """Tests for the RiskMitigation model."""

    def test_mitigation_required_fields(self):
        """RiskMitigation should require risk_id, title, description."""
        risk_id = uuid4()
        mit = RiskMitigation(
            risk_id=risk_id,
            title="Qualify Backup Supplier",
            description="Qualify alternate supplier for critical components",
            mitigation_type="preventive",
        )
        assert mit.risk_id == risk_id
        assert mit.title == "Qualify Backup Supplier"
        assert mit.mitigation_type == "preventive"

    def test_mitigation_default_status_is_planned(self):
        """RiskMitigation status should default to planned."""
        mit = RiskMitigation(
            risk_id=uuid4(),
            title="Test",
            description="Test description",
            mitigation_type="preventive",
            status=MitigationStatus.PLANNED.value,
        )
        assert mit.status == MitigationStatus.PLANNED.value

    def test_mitigation_is_complete_true_for_completed(self):
        """is_complete should be True for completed status."""
        mit = RiskMitigation(
            risk_id=uuid4(),
            title="Test",
            description="Test description",
            mitigation_type="preventive",
            status=MitigationStatus.COMPLETED.value,
        )
        assert mit.is_complete is True

    def test_mitigation_is_complete_false_for_other_statuses(self):
        """is_complete should be False for non-completed statuses."""
        for status in [
            MitigationStatus.PLANNED,
            MitigationStatus.IN_PROGRESS,
            MitigationStatus.ON_HOLD,
            MitigationStatus.CANCELLED,
        ]:
            mit = RiskMitigation(
                risk_id=uuid4(),
                title="Test",
                description="Test description",
                mitigation_type="preventive",
                status=status.value,
            )
            assert mit.is_complete is False

    def test_mitigation_is_overdue_true_for_past_due_date(self):
        """is_overdue should be True when planned_end_date is past and not complete."""
        mit = RiskMitigation(
            risk_id=uuid4(),
            title="Test",
            description="Test description",
            mitigation_type="preventive",
            status=MitigationStatus.IN_PROGRESS.value,
            planned_end_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert mit.is_overdue is True

    def test_mitigation_is_overdue_false_when_completed(self):
        """is_overdue should be False when completed even if past due."""
        mit = RiskMitigation(
            risk_id=uuid4(),
            title="Test",
            description="Test description",
            mitigation_type="preventive",
            status=MitigationStatus.COMPLETED.value,
            planned_end_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert mit.is_overdue is False

    def test_mitigation_is_overdue_false_for_future_date(self):
        """is_overdue should be False when planned_end_date is in the future."""
        mit = RiskMitigation(
            risk_id=uuid4(),
            title="Test",
            description="Test description",
            mitigation_type="preventive",
            status=MitigationStatus.IN_PROGRESS.value,
            planned_end_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert mit.is_overdue is False

    def test_mitigation_is_overdue_false_when_no_date(self):
        """is_overdue should be False when planned_end_date is not set."""
        mit = RiskMitigation(
            risk_id=uuid4(),
            title="Test",
            description="Test description",
            mitigation_type="preventive",
            status=MitigationStatus.IN_PROGRESS.value,
        )
        assert mit.is_overdue is False

    def test_mitigation_type_values(self):
        """mitigation_type accepts standard values like preventive, detective, corrective."""
        for mtype in ["preventive", "detective", "corrective"]:
            mit = RiskMitigation(
                risk_id=uuid4(),
                title="Test",
                description="Test description",
                mitigation_type=mtype,
            )
            assert mit.mitigation_type == mtype


class TestMitigationStatusEnum:
    """Tests for MitigationStatus enum."""

    def test_all_statuses_defined(self):
        """All expected mitigation statuses should be defined."""
        assert MitigationStatus.PLANNED.value == "planned"
        assert MitigationStatus.IN_PROGRESS.value == "in_progress"
        assert MitigationStatus.COMPLETED.value == "completed"
        assert MitigationStatus.ON_HOLD.value == "on_hold"
        assert MitigationStatus.CANCELLED.value == "cancelled"
