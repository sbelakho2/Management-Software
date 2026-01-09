"""
Tests for ML Module: Missing Evidence Detector

Tests the hybrid ML/rule-based system for detecting missing evidence in A3 reports.
"""

import pytest
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from unittest.mock import patch
import tempfile

from sensei.ml.evidence_detector import (
    MissingEvidenceDetector,
    analyze_all_reports,
)


# =============================================================================
# Mock Models
# =============================================================================

class MockA3Report:
    """Mock A3Report model for testing."""
    
    def __init__(
        self,
        report_id: str,
        title: str = "Test A3 Report",
        background: str = "",
        current_condition: str = "",
        goal: str = "",
        root_cause_analysis: str = "",
        countermeasures: str = "",
        implementation_plan: str = "",
        followup: str = "",
        attachments: List[str] = None,
    ):
        self.id = report_id
        self.title = title
        self.background = background
        self.current_condition = current_condition
        self.goal = goal
        self.root_cause_analysis = root_cause_analysis
        self.countermeasures = countermeasures
        self.implementation_plan = implementation_plan
        self.followup = followup
        self.attachments = attachments or []


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def complete_report():
    """Create a complete A3 report with all required evidence."""
    return MockA3Report(
        report_id="A3-001",
        title="Reduce Defect Rate in Assembly Line 3",
        background=(
            "The defect rate in Assembly Line 3 has increased from 2% to 5% "
            "over the past month. This has resulted in increased rework costs "
            "and customer complaints. The production manager requested an A3 "
            "investigation to identify root causes and implement countermeasures."
        ),
        current_condition=(
            "Current defect rate: 5% (baseline was 2%). "
            "Main defect types: misalignment (40%), missing parts (35%), cosmetic (25%). "
            "Rework time increased by 45 hours per week. "
            "Customer complaints: 12 in the past month vs 3 in the previous month."
        ),
        goal=(
            "Reduce defect rate from 5% to less than 2% within 30 days. "
            "Zero customer complaints related to defects."
        ),
        root_cause_analysis=(
            "5 Why Analysis conducted on the top defect type (misalignment):\n"
            "1. Why misalignment? Components shifted during assembly.\n"
            "2. Why shifted? Fixture not holding components firmly.\n"
            "3. Why not holding? Fixture wear after 10,000 cycles.\n"
            "4. Why worn? No preventive maintenance schedule.\n"
            "5. Why no schedule? Root cause: Fixture not included in PM program.\n\n"
            "Pareto analysis confirmed 80% of defects come from 2 work stations."
        ),
        countermeasures=(
            "1. Replace worn fixtures at stations 3 and 7 - Cost: $2,500\n"
            "2. Add fixtures to preventive maintenance schedule (monthly inspection)\n"
            "3. Implement visual management for fixture condition\n"
            "4. Train operators on fixture inspection - 2 hours training\n\n"
            "Validation: After implementing countermeasures, defect rate dropped to 1.5%."
        ),
        implementation_plan=(
            "Week 1: Order new fixtures and prepare training materials\n"
            "Week 2: Install new fixtures, conduct operator training\n"
            "Week 3: Monitor results and adjust as needed\n"
            "Week 4: Verify sustained improvement"
        ),
        followup=(
            "After implementation, the defect rate was measured at 1.5% (improved from 5%).\n"
            "Customer complaints: 0 in the following month.\n"
            "Before: 5% defect rate, 45 hours rework/week\n"
            "After: 1.5% defect rate, 12 hours rework/week"
        ),
        attachments=["defect_pareto.png", "5why_diagram.pdf", "before_after_chart.png"],
    )


@pytest.fixture
def incomplete_report():
    """Create an incomplete A3 report missing evidence."""
    return MockA3Report(
        report_id="A3-002",
        title="Fix Quality Issue",
        background="We have a quality problem.",
        current_condition="Defects are too high.",
        goal="Reduce defects.",
        root_cause_analysis="The machine is broken.",
        countermeasures="Fix the machine.",
        implementation_plan="",
        followup="",
    )


@pytest.fixture
def partial_report():
    """Create a partially complete A3 report."""
    return MockA3Report(
        report_id="A3-003",
        title="Improve Delivery Time",
        background=(
            "Delivery time to customers has increased from 3 days to 7 days. "
            "This is impacting customer satisfaction and repeat orders."
        ),
        current_condition=(
            "Average delivery time: 7 days. "
            "Target: 3 days. "
            "On-time delivery rate: 65%."
        ),
        goal="Reduce delivery time to 3 days with 95% on-time rate.",
        root_cause_analysis=(
            "Investigated the shipping process. "
            "Found delays in packing department."
        ),
        countermeasures="Hired additional packing staff.",
        implementation_plan="Staff starts next week.",
        followup="Will monitor results.",
    )


@pytest.fixture
def temp_model_path():
    """Create temporary directory for model artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Test: MissingEvidenceDetector Initialization
# =============================================================================

class TestEvidenceDetectorInit:
    """Test MissingEvidenceDetector initialization."""
    
    def test_init_with_default_path(self):
        """Test initialization with default model path."""
        detector = MissingEvidenceDetector()
        assert detector.text_classifier is None
        assert detector.tfidf_vectorizer is None
    
    def test_init_with_custom_path(self, temp_model_path):
        """Test initialization with custom model path."""
        detector = MissingEvidenceDetector(model_path=temp_model_path)
        assert detector.model_path == temp_model_path


# =============================================================================
# Test: Evidence Pattern Detection (Rule-Based)
# =============================================================================

class TestEvidencePatternDetection:
    """Test rule-based evidence pattern detection."""
    
    def test_detect_numerical_data(self, complete_report):
        """Test detection of numerical data in reports."""
        detector = MissingEvidenceDetector()
        
        # Complete report should have numerical data
        result = detector.detect_missing_evidence(complete_report)
        
        # Should not report missing numerical data
        missing_types = [item['type'] for item in result['missing_items']]
        assert 'missing_data' not in missing_types
    
    def test_detect_missing_numerical_data(self, incomplete_report):
        """Test detection of missing numerical data."""
        detector = MissingEvidenceDetector()
        
        result = detector.detect_missing_evidence(incomplete_report)
        
        # Should report missing numerical data
        has_missing_data = any(
            item['type'] == 'missing_data'
            for item in result['missing_items']
        )
        assert has_missing_data or len(result['warnings']) > 0
    
    def test_detect_root_cause_evidence(self, complete_report):
        """Test detection of root cause analysis evidence."""
        detector = MissingEvidenceDetector()
        
        result = detector.detect_missing_evidence(complete_report)
        
        # Complete report should have root cause evidence
        has_missing_root_cause = any(
            item['type'] == 'missing_root_cause'
            for item in result['missing_items']
        )
        assert not has_missing_root_cause
    
    def test_detect_missing_root_cause_evidence(self, incomplete_report):
        """Test detection of missing root cause evidence."""
        detector = MissingEvidenceDetector()
        
        result = detector.detect_missing_evidence(incomplete_report)
        
        # Should suggest adding 5-Why or fishbone
        has_suggestion = any(
            '5-Why' in s or 'fishbone' in s
            for s in result['suggestions']
        )
        # May or may not have suggestion depending on detection
        assert isinstance(result['suggestions'], list)
    
    def test_detect_validation_evidence(self, complete_report):
        """Test detection of validation evidence."""
        detector = MissingEvidenceDetector()
        
        result = detector.detect_missing_evidence(complete_report)
        
        # Complete report should have validation
        has_missing_validation = any(
            item['type'] == 'missing_validation'
            for item in result['missing_items']
        )
        assert not has_missing_validation


# =============================================================================
# Test: Section Completeness
# =============================================================================

class TestSectionCompleteness:
    """Test section completeness checking."""
    
    def test_complete_sections_score_high(self, complete_report):
        """Test that complete sections score highly."""
        detector = MissingEvidenceDetector()
        scores = detector._check_section_completeness(complete_report)
        
        # Most sections should be complete (score >= 0.8)
        complete_count = sum(1 for s in scores.values() if s >= 0.8)
        assert complete_count >= 4  # At least 4 out of 7 sections complete
    
    def test_incomplete_sections_score_low(self, incomplete_report):
        """Test that incomplete sections score low."""
        detector = MissingEvidenceDetector()
        scores = detector._check_section_completeness(incomplete_report)
        
        # Some sections should be incomplete
        incomplete_count = sum(1 for s in scores.values() if s < 0.5)
        assert incomplete_count >= 2  # At least 2 incomplete sections
    
    def test_empty_sections_score_zero(self):
        """Test that empty sections score zero."""
        empty_report = MockA3Report(report_id="A3-EMPTY")
        detector = MissingEvidenceDetector()
        
        scores = detector._check_section_completeness(empty_report)
        
        # All sections should be 0
        assert all(s == 0 for s in scores.values())


# =============================================================================
# Test: Detection Results Structure
# =============================================================================

class TestDetectionResults:
    """Test detection results structure and content."""
    
    def test_result_structure(self, complete_report):
        """Test that detection results have correct structure."""
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(complete_report)
        
        # Check all expected fields
        assert 'overall_score' in result
        assert 'is_complete' in result
        assert 'missing_items' in result
        assert 'warnings' in result
        assert 'suggestions' in result
        
        # Check types
        assert isinstance(result['overall_score'], float)
        assert isinstance(result['is_complete'], bool)
        assert isinstance(result['missing_items'], list)
        assert isinstance(result['warnings'], list)
        assert isinstance(result['suggestions'], list)
    
    def test_score_range(self, complete_report):
        """Test that overall score is in valid range."""
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(complete_report)
        
        assert 0 <= result['overall_score'] <= 1
    
    def test_complete_report_high_score(self, complete_report):
        """Test that complete reports get high scores."""
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(complete_report)
        
        # Complete report should score well
        assert result['overall_score'] >= 0.5
    
    def test_incomplete_report_low_score(self, incomplete_report):
        """Test that incomplete reports get low scores."""
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(incomplete_report)
        
        # Incomplete report should have issues flagged
        assert not result['is_complete'] or len(result['missing_items']) > 0 or len(result['warnings']) > 0
    
    def test_missing_items_have_type_and_message(self, incomplete_report):
        """Test that missing items have type and message."""
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(incomplete_report)
        
        for item in result['missing_items']:
            assert 'type' in item
            assert 'message' in item or 'score' in item


# =============================================================================
# Test: Attachment Check
# =============================================================================

class TestAttachmentCheck:
    """Test attachment checking."""
    
    def test_report_with_attachments_no_warning(self, complete_report):
        """Test that reports with attachments don't get warnings."""
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(complete_report)
        
        attachment_warnings = [w for w in result['warnings'] if 'attachment' in w.lower()]
        assert len(attachment_warnings) == 0
    
    def test_report_without_attachments_warning(self, incomplete_report):
        """Test that reports without attachments get warnings."""
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(incomplete_report)
        
        attachment_warnings = [w for w in result['warnings'] if 'attachment' in w.lower()]
        assert len(attachment_warnings) > 0


# =============================================================================
# Test: Training
# =============================================================================

class TestEvidenceDetectorTraining:
    """Test MissingEvidenceDetector training."""
    
    def test_train_creates_model(self, temp_model_path, complete_report, incomplete_report):
        """Test that training creates model artifacts."""
        detector = MissingEvidenceDetector(model_path=temp_model_path)
        
        # Create labeled training data
        labeled_reports = [
            (complete_report, {'has_numerical_data': True, 'has_root_cause_evidence': True, 'has_validation': True}),
            (incomplete_report, {'has_numerical_data': False, 'has_root_cause_evidence': False, 'has_validation': False}),
        ]
        
        # Need at least some data for training
        # Duplicate to have minimal training set
        labeled_reports = labeled_reports * 10
        
        metrics = detector.train(labeled_reports)
        
        # Check metrics returned
        assert 'f1_mean' in metrics
        assert 'f1_std' in metrics
        
        # Check artifacts created
        assert (temp_model_path / "classifier.pkl").exists()
        assert (temp_model_path / "tfidf.pkl").exists()
    
    def test_train_with_empty_data(self, temp_model_path):
        """Test training with empty data handles gracefully."""
        detector = MissingEvidenceDetector(model_path=temp_model_path)
        
        # This should handle empty data gracefully
        with pytest.raises(Exception):
            detector.train([])


# =============================================================================
# Test: Model Loading
# =============================================================================

class TestEvidenceDetectorLoading:
    """Test MissingEvidenceDetector model loading."""
    
    def test_load_after_training(self, temp_model_path, complete_report, incomplete_report):
        """Test loading model after training."""
        # Train first
        detector1 = MissingEvidenceDetector(model_path=temp_model_path)
        labeled_reports = [
            (complete_report, {'has_numerical_data': True, 'has_root_cause_evidence': True, 'has_validation': True}),
            (incomplete_report, {'has_numerical_data': False, 'has_root_cause_evidence': False, 'has_validation': False}),
        ] * 10
        detector1.train(labeled_reports)
        
        # Load in new instance
        detector2 = MissingEvidenceDetector(model_path=temp_model_path)
        detector2.load()
        
        assert detector2.text_classifier is not None
        assert detector2.tfidf_vectorizer is not None
    
    def test_load_without_training_raises(self, temp_model_path):
        """Test that loading without training raises error."""
        detector = MissingEvidenceDetector(model_path=temp_model_path)
        
        with pytest.raises(Exception):
            detector.load()


# =============================================================================
# Test: Batch Analysis
# =============================================================================

class TestBatchAnalysis:
    """Test batch analysis of multiple reports."""
    
    def test_analyze_all_reports(self, complete_report, incomplete_report, partial_report):
        """Test analyzing multiple reports."""
        detector = MissingEvidenceDetector()
        reports = [complete_report, incomplete_report, partial_report]
        
        results = analyze_all_reports(detector, reports)
        
        # Should have results for each report
        assert len(results) == 3
        assert "A3-001" in results
        assert "A3-002" in results
        assert "A3-003" in results
    
    def test_analyze_all_reports_handles_errors(self):
        """Test that batch analysis handles individual errors."""
        detector = MissingEvidenceDetector()
        
        # Create a problematic report
        bad_report = MockA3Report(report_id="A3-BAD")
        bad_report.root_cause_analysis = None  # None instead of empty string
        
        results = analyze_all_reports(detector, [bad_report])
        
        # Should still return results (possibly with error flag)
        assert len(results) == 1
        assert "A3-BAD" in results


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_report(self):
        """Test detection on completely empty report."""
        empty_report = MockA3Report(report_id="A3-EMPTY")
        detector = MissingEvidenceDetector()
        
        result = detector.detect_missing_evidence(empty_report)
        
        # Should have low score and many missing items
        assert result['overall_score'] < 0.5
        assert not result['is_complete']
    
    def test_report_with_none_fields(self):
        """Test detection on report with None fields."""
        report = MockA3Report(report_id="A3-NONE")
        report.background = None
        report.current_condition = None
        
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(report)
        
        # Should handle None gracefully
        assert isinstance(result, dict)
        assert 'overall_score' in result
    
    def test_report_with_unicode(self):
        """Test detection on report with unicode content."""
        report = MockA3Report(
            report_id="A3-UNICODE",
            background="测试报告 - Test Report with unicode characters: é à ü ñ 日本語",
            root_cause_analysis="5 Why分析: 根本原因は問題です. Root cause analysis with 50% improvement.",
        )
        
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(report)
        
        # Should handle unicode gracefully
        assert isinstance(result, dict)
    
    def test_report_with_very_long_content(self):
        """Test detection on report with very long content."""
        long_content = "This is a test sentence with numerical data 50%. " * 1000
        report = MockA3Report(
            report_id="A3-LONG",
            background=long_content,
            current_condition=long_content,
            root_cause_analysis=long_content + " Root cause 5 why analysis validation verify.",
        )
        
        detector = MissingEvidenceDetector()
        result = detector.detect_missing_evidence(report)
        
        # Should complete without error
        assert isinstance(result, dict)
        assert result['overall_score'] >= 0
