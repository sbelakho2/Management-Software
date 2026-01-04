"""
Tests for Qualification models.

Tests:
- Qualification model fields and defaults
- Qualification score calculation methods
- QualificationCriterion model
- QualificationScore model
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.models.qualification import (
    CriterionCategory,
    CriterionType,
    Qualification,
    QualificationCriterion,
    QualificationResult,
    QualificationScore,
    ScoreValue,
)


class TestQualificationModel:
    """Tests for the Qualification model."""

    def test_qualification_required_fields(self):
        """Qualification should require rfq_id."""
        rfq_id = uuid4()
        qual = Qualification(
            rfq_id=rfq_id,
        )
        assert qual.rfq_id == rfq_id

    def test_qualification_default_result_is_pending(self):
        """Qualification result should default to pending."""
        qual = Qualification(
            rfq_id=uuid4(),
            result=QualificationResult.PENDING.value,
        )
        assert qual.result == QualificationResult.PENDING.value

    def test_qualification_default_version_is_1(self):
        """Qualification version should default to 1."""
        qual = Qualification(
            rfq_id=uuid4(),
            version=1,
        )
        assert qual.version == 1

    def test_qualification_default_has_blockers_is_false(self):
        """has_blockers should default to False."""
        qual = Qualification(
            rfq_id=uuid4(),
            has_blockers=False,
        )
        assert qual.has_blockers is False

    def test_qualification_default_pass_threshold(self):
        """pass_threshold should default to 70.00."""
        qual = Qualification(
            rfq_id=uuid4(),
            pass_threshold=Decimal("70.00"),
        )
        assert qual.pass_threshold == Decimal("70.00")

    def test_qualification_default_conditional_threshold(self):
        """conditional_threshold should default to 50.00."""
        qual = Qualification(
            rfq_id=uuid4(),
            conditional_threshold=Decimal("50.00"),
        )
        assert qual.conditional_threshold == Decimal("50.00")

    def test_qualification_total_score_none_by_default(self):
        """total_score should be None by default."""
        qual = Qualification(
            rfq_id=uuid4(),
        )
        assert qual.total_score is None

    def test_qualification_percentage_score_none_by_default(self):
        """percentage_score should be None by default."""
        qual = Qualification(
            rfq_id=uuid4(),
        )
        assert qual.percentage_score is None

    def test_qualification_conditions_field(self):
        """conditions should accept a list."""
        qual = Qualification(
            rfq_id=uuid4(),
            conditions=["Must achieve 80% capacity utilization"],
        )
        assert qual.conditions == ["Must achieve 80% capacity utilization"]

    def test_qualification_category_scores_field(self):
        """category_scores should accept a dict."""
        qual = Qualification(
            rfq_id=uuid4(),
            category_scores={"technical": 85.0, "commercial": 90.0},
        )
        assert qual.category_scores["technical"] == 85.0
        assert qual.category_scores["commercial"] == 90.0


class TestQualificationResultEnum:
    """Tests for QualificationResult enum."""

    def test_all_results_defined(self):
        """All expected qualification results should be defined."""
        assert QualificationResult.PENDING.value == "pending"
        assert QualificationResult.QUALIFIED.value == "qualified"
        assert QualificationResult.CONDITIONALLY_QUALIFIED.value == "conditionally_qualified"
        assert QualificationResult.NOT_QUALIFIED.value == "not_qualified"
        assert QualificationResult.NEEDS_REVIEW.value == "needs_review"


class TestQualificationCriterionModel:
    """Tests for the QualificationCriterion model."""

    def test_criterion_required_fields(self):
        """QualificationCriterion should require name and code."""
        criterion = QualificationCriterion(
            name="Technical Capability",
            code="TECH_CAP",
        )
        assert criterion.name == "Technical Capability"
        assert criterion.code == "TECH_CAP"

    def test_criterion_default_category_is_technical(self):
        """category should default to technical."""
        criterion = QualificationCriterion(
            name="Test",
            code="TEST",
            category=CriterionCategory.TECHNICAL.value,
        )
        assert criterion.category == CriterionCategory.TECHNICAL.value

    def test_criterion_default_max_score(self):
        """max_score should default to 10.00."""
        criterion = QualificationCriterion(
            name="Test",
            code="TEST",
            max_score=Decimal("10.00"),
        )
        assert criterion.max_score == Decimal("10.00")

    def test_criterion_default_weight(self):
        """default_weight should default to 1.00."""
        criterion = QualificationCriterion(
            name="Test",
            code="TEST",
            default_weight=Decimal("1.00"),
        )
        assert criterion.default_weight == Decimal("1.00")

    def test_criterion_is_active_default_true(self):
        """is_active should default to True."""
        criterion = QualificationCriterion(
            name="Test",
            code="TEST",
            is_active=True,
        )
        assert criterion.is_active is True

    def test_criterion_is_blocker_default_false(self):
        """is_blocker should default to False."""
        criterion = QualificationCriterion(
            name="Test",
            code="TEST",
            is_blocker=False,
        )
        assert criterion.is_blocker is False

    def test_criterion_is_required_default_true(self):
        """is_required should default to True."""
        criterion = QualificationCriterion(
            name="Test",
            code="TEST",
            is_required=True,
        )
        assert criterion.is_required is True

    def test_criterion_display_order_default_0(self):
        """display_order should default to 0."""
        criterion = QualificationCriterion(
            name="Test",
            code="TEST",
            display_order=0,
        )
        assert criterion.display_order == 0


class TestCriterionCategoryEnum:
    """Tests for CriterionCategory enum."""

    def test_all_categories_defined(self):
        """All expected criterion categories should be defined."""
        assert CriterionCategory.TECHNICAL.value == "technical"
        assert CriterionCategory.COMMERCIAL.value == "commercial"
        assert CriterionCategory.CAPACITY.value == "capacity"
        assert CriterionCategory.QUALITY.value == "quality"
        assert CriterionCategory.STRATEGIC.value == "strategic"
        assert CriterionCategory.RISK.value == "risk"
        assert CriterionCategory.SUPPLY_CHAIN.value == "supply_chain"


class TestCriterionTypeEnum:
    """Tests for CriterionType enum."""

    def test_all_types_defined(self):
        """All expected criterion types should be defined."""
        assert CriterionType.SCORED.value == "scored"
        assert CriterionType.PASS_FAIL.value == "pass_fail"
        assert CriterionType.INFORMATIONAL.value == "informational"


class TestQualificationScoreModel:
    """Tests for the QualificationScore model."""

    def test_score_required_fields(self):
        """QualificationScore should require qualification_id and criterion_id."""
        qual_id = uuid4()
        crit_id = uuid4()
        score = QualificationScore(
            qualification_id=qual_id,
            criterion_id=crit_id,
        )
        assert score.qualification_id == qual_id
        assert score.criterion_id == crit_id

    def test_score_numeric_score_none_by_default(self):
        """score should be None by default."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
        )
        assert qs.score is None

    def test_score_default_max_score(self):
        """max_score should default to 10.00."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
            max_score=Decimal("10.00"),
        )
        assert qs.max_score == Decimal("10.00")

    def test_score_default_weight(self):
        """weight should default to 1.00."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
            weight=Decimal("1.00"),
        )
        assert qs.weight == Decimal("1.00")

    def test_score_is_blocker_triggered_default_false(self):
        """is_blocker_triggered should default to False."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
            is_blocker_triggered=False,
        )
        assert qs.is_blocker_triggered is False

    def test_score_is_auto_scored_default_false(self):
        """is_auto_scored should default to False."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
            is_auto_scored=False,
        )
        assert qs.is_auto_scored is False

    def test_score_weighted_score_property(self):
        """weighted_score should calculate score * weight."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
            score=Decimal("8.00"),
            weight=Decimal("2.00"),
        )
        assert qs.weighted_score == Decimal("16.00")

    def test_score_weighted_score_none_when_no_score(self):
        """weighted_score should be None when score is None."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
            weight=Decimal("2.00"),
        )
        assert qs.weighted_score is None

    def test_score_percentage_property(self):
        """percentage should calculate (score / max_score) * 100."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
            score=Decimal("7.50"),
            max_score=Decimal("10.00"),
        )
        assert qs.percentage == Decimal("75.00")

    def test_score_percentage_none_when_no_score(self):
        """percentage should be None when score is None."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
            max_score=Decimal("10.00"),
        )
        assert qs.percentage is None

    def test_score_percentage_zero_when_max_score_zero(self):
        """percentage should be 0 when max_score is 0."""
        qs = QualificationScore(
            qualification_id=uuid4(),
            criterion_id=uuid4(),
            score=Decimal("5.00"),
            max_score=Decimal("0.00"),
        )
        assert qs.percentage == Decimal("0")


class TestScoreValueEnum:
    """Tests for ScoreValue enum."""

    def test_all_score_values_defined(self):
        """All expected score values should be defined."""
        assert ScoreValue.GREEN.value == "green"
        assert ScoreValue.YELLOW.value == "yellow"
        assert ScoreValue.RED.value == "red"
        assert ScoreValue.NOT_ASSESSED.value == "not_assessed"
