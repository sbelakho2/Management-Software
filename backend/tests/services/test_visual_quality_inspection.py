"""
Tests for Visual Quality Inspection Service.

Tests world-class visual defect detection capabilities:
- Anomaly detection (PatchCore)
- Defect detection (YOLO)
- Quality scoring
- Continuous learning
- Multi-zone inspection
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from sensei.services.visual_quality_inspection import (
    # Enums
    DefectCategory,
    DefectSeverity,
    InspectionDecision,
    ModelType,
    AnomalyMethod,
    ZoneType,
    # Data models
    BoundingBox,
    SegmentationMask,
    InspectionZone,
    DetectedDefect,
    AnomalyMap,
    InspectionResult,
    InspectionBatch,
    InspectionConfig,
    FeedbackRecord,
    # Components
    PatchCoreDetector,
    YOLODefectDetector,
    QualityScoringEngine,
    ContinuousLearningManager,
    VisualQualityInspectionService,
)


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================================================
# BoundingBox Tests
# =============================================================================


class TestBoundingBox:
    """Tests for BoundingBox class."""
    
    def test_x2_y2_properties(self):
        """Test x2 and y2 calculated properties."""
        bbox = BoundingBox(x=100, y=200, width=50, height=75)
        
        assert bbox.x2 == 150
        assert bbox.y2 == 275
    
    def test_center_property(self):
        """Test center calculation."""
        bbox = BoundingBox(x=100, y=100, width=100, height=100)
        
        assert bbox.center == (150, 150)
    
    def test_area_property(self):
        """Test area calculation."""
        bbox = BoundingBox(x=0, y=0, width=100, height=50)
        
        assert bbox.area == 5000
    
    def test_iou_full_overlap(self):
        """Test IoU with identical boxes."""
        bbox1 = BoundingBox(x=0, y=0, width=100, height=100)
        bbox2 = BoundingBox(x=0, y=0, width=100, height=100)
        
        assert bbox1.iou(bbox2) == 1.0
    
    def test_iou_no_overlap(self):
        """Test IoU with non-overlapping boxes."""
        bbox1 = BoundingBox(x=0, y=0, width=100, height=100)
        bbox2 = BoundingBox(x=200, y=200, width=100, height=100)
        
        assert bbox1.iou(bbox2) == 0.0
    
    def test_iou_partial_overlap(self):
        """Test IoU with partial overlap."""
        bbox1 = BoundingBox(x=0, y=0, width=100, height=100)
        bbox2 = BoundingBox(x=50, y=50, width=100, height=100)
        
        iou = bbox1.iou(bbox2)
        assert 0 < iou < 1


# =============================================================================
# SegmentationMask Tests
# =============================================================================


class TestSegmentationMask:
    """Tests for SegmentationMask class."""
    
    def test_area_calculation(self):
        """Test mask area calculation."""
        mask = np.zeros((100, 100))
        mask[20:40, 30:50] = 1  # 20x20 = 400 pixels
        
        seg_mask = SegmentationMask(mask=mask)
        
        assert seg_mask.area == 400
    
    def test_empty_mask_area(self):
        """Test area of empty mask."""
        mask = np.zeros((100, 100))
        
        seg_mask = SegmentationMask(mask=mask)
        
        assert seg_mask.area == 0
    
    def test_probability_mask_threshold(self):
        """Test area with probability mask."""
        mask = np.ones((100, 100)) * 0.3  # All below threshold
        mask[10:20, 10:20] = 0.8  # 10x10 = 100 pixels above threshold
        
        seg_mask = SegmentationMask(mask=mask)
        
        assert seg_mask.area == 100


# =============================================================================
# DetectedDefect Tests
# =============================================================================


class TestDetectedDefect:
    """Tests for DetectedDefect class."""
    
    def test_is_critical_property(self):
        """Test is_critical property."""
        critical_defect = DetectedDefect(
            defect_id="d1",
            category=DefectCategory.MATERIAL,
            severity=DefectSeverity.CRITICAL,
            confidence=0.9,
        )
        
        major_defect = DetectedDefect(
            defect_id="d2",
            category=DefectCategory.SURFACE,
            severity=DefectSeverity.MAJOR,
            confidence=0.8,
        )
        
        minor_defect = DetectedDefect(
            defect_id="d3",
            category=DefectCategory.SURFACE,
            severity=DefectSeverity.MINOR,
            confidence=0.7,
        )
        
        assert critical_defect.is_critical is True
        assert major_defect.is_critical is True
        assert minor_defect.is_critical is False
    
    def test_defect_with_bbox(self):
        """Test defect with bounding box."""
        defect = DetectedDefect(
            defect_id="d1",
            category=DefectCategory.SURFACE,
            severity=DefectSeverity.MINOR,
            confidence=0.85,
            bbox=BoundingBox(x=100, y=100, width=50, height=30),
            defect_type="scratch",
        )
        
        assert defect.bbox is not None
        assert defect.bbox.area == 1500
    
    def test_defect_with_anomaly_score(self):
        """Test defect with anomaly score."""
        defect = DetectedDefect(
            defect_id="d1",
            category=DefectCategory.UNKNOWN,
            severity=DefectSeverity.MINOR,
            confidence=0.7,
            anomaly_score=0.85,
        )
        
        assert defect.anomaly_score == 0.85


# =============================================================================
# AnomalyMap Tests
# =============================================================================


class TestAnomalyMap:
    """Tests for AnomalyMap class."""
    
    def test_get_anomaly_regions_above_threshold(self):
        """Test extraction of anomaly regions."""
        # Create anomaly map with high-score region
        anomaly_map = np.zeros((100, 100))
        anomaly_map[40:60, 40:60] = 0.8  # High anomaly region
        
        amap = AnomalyMap(
            map=anomaly_map,
            threshold=0.5,
            max_score=0.8,
            mean_score=0.1,
        )
        
        regions = amap.get_anomaly_regions()
        
        # Should find at least one region
        assert len(regions) >= 1
    
    def test_get_anomaly_regions_below_threshold(self):
        """Test no regions when below threshold."""
        anomaly_map = np.ones((100, 100)) * 0.3  # All below threshold
        
        amap = AnomalyMap(
            map=anomaly_map,
            threshold=0.5,
            max_score=0.3,
            mean_score=0.3,
        )
        
        regions = amap.get_anomaly_regions()
        
        assert len(regions) == 0


# =============================================================================
# InspectionResult Tests
# =============================================================================


class TestInspectionResult:
    """Tests for InspectionResult class."""
    
    def test_is_pass_property(self):
        """Test is_pass property."""
        pass_result = InspectionResult(
            inspection_id="i1",
            image_id="img1",
            timestamp=datetime.utcnow(),
            decision=InspectionDecision.PASS,
            decision_confidence=0.95,
        )
        
        fail_result = InspectionResult(
            inspection_id="i2",
            image_id="img2",
            timestamp=datetime.utcnow(),
            decision=InspectionDecision.FAIL,
            decision_confidence=0.9,
        )
        
        assert pass_result.is_pass is True
        assert fail_result.is_pass is False
    
    def test_critical_defects_filter(self):
        """Test filtering of critical defects."""
        defects = [
            DetectedDefect("d1", DefectCategory.SURFACE, DefectSeverity.CRITICAL, 0.9),
            DetectedDefect("d2", DefectCategory.SURFACE, DefectSeverity.MINOR, 0.8),
            DetectedDefect("d3", DefectCategory.MATERIAL, DefectSeverity.MAJOR, 0.85),
            DetectedDefect("d4", DefectCategory.SURFACE, DefectSeverity.INFORMATIONAL, 0.7),
        ]
        
        result = InspectionResult(
            inspection_id="i1",
            image_id="img1",
            timestamp=datetime.utcnow(),
            decision=InspectionDecision.FAIL,
            decision_confidence=0.9,
            defects=defects,
        )
        
        critical = result.critical_defects
        
        assert len(critical) == 2  # CRITICAL and MAJOR


# =============================================================================
# InspectionBatch Tests
# =============================================================================


class TestInspectionBatch:
    """Tests for InspectionBatch class."""
    
    def test_pass_rate_calculation(self):
        """Test pass rate calculation."""
        results = [
            InspectionResult("i1", "img1", datetime.utcnow(), InspectionDecision.PASS, 0.9),
            InspectionResult("i2", "img2", datetime.utcnow(), InspectionDecision.PASS, 0.9),
            InspectionResult("i3", "img3", datetime.utcnow(), InspectionDecision.FAIL, 0.9),
            InspectionResult("i4", "img4", datetime.utcnow(), InspectionDecision.PASS, 0.9),
        ]
        
        batch = InspectionBatch(
            batch_id="b1",
            results=results,
            total_inspected=4,
            pass_count=3,
            fail_count=1,
        )
        
        assert batch.pass_rate == 0.75
    
    def test_pass_rate_empty_batch(self):
        """Test pass rate for empty batch."""
        batch = InspectionBatch(
            batch_id="b1",
            results=[],
            total_inspected=0,
            pass_count=0,
            fail_count=0,
        )
        
        assert batch.pass_rate == 1.0
    
    def test_yield_rate_equals_pass_rate(self):
        """Test yield rate equals pass rate."""
        batch = InspectionBatch(
            batch_id="b1",
            results=[],
            total_inspected=10,
            pass_count=8,
            fail_count=2,
        )
        
        assert batch.yield_rate == batch.pass_rate


# =============================================================================
# PatchCoreDetector Tests
# =============================================================================


class TestPatchCoreDetector:
    """Tests for PatchCoreDetector."""
    
    def test_fit_builds_memory_bank(self):
        """Test fitting builds memory bank."""
        detector = PatchCoreDetector()
        
        # Create fake normal images
        normal_images = [np.random.rand(224, 224, 3) for _ in range(10)]
        
        detector.fit(normal_images)
        
        assert detector.memory_bank is not None
        assert len(detector.memory_bank) > 0
    
    def test_predict_returns_score_and_map(self):
        """Test prediction returns anomaly score and map."""
        detector = PatchCoreDetector()
        
        # Fit on normal images
        normal_images = [np.random.rand(224, 224, 3) for _ in range(5)]
        detector.fit(normal_images)
        
        # Predict on test image
        test_image = np.random.rand(224, 224, 3)
        score, anomaly_map = detector.predict(test_image)
        
        assert isinstance(score, float)
        assert isinstance(anomaly_map, AnomalyMap)
        assert anomaly_map.map.shape[0] > 0
    
    def test_predict_without_fit_raises_error(self):
        """Test prediction without fitting raises error."""
        detector = PatchCoreDetector()
        
        test_image = np.random.rand(224, 224, 3)
        
        with pytest.raises(ValueError, match="not fitted"):
            detector.predict(test_image)
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading model."""
        detector = PatchCoreDetector()
        
        normal_images = [np.random.rand(224, 224, 3) for _ in range(5)]
        detector.fit(normal_images)
        
        # Save
        save_path = tmp_path / "patchcore.npz"
        detector.save(save_path)
        
        # Load into new detector
        new_detector = PatchCoreDetector()
        new_detector.load(save_path)
        
        assert new_detector.memory_bank is not None


# =============================================================================
# YOLODefectDetector Tests
# =============================================================================


class TestYOLODefectDetector:
    """Tests for YOLODefectDetector."""
    
    def test_detect_returns_detections(self):
        """Test detection returns bounding boxes and classes."""
        detector = YOLODefectDetector()
        
        image = np.random.rand(640, 640, 3)
        detections = detector.detect(image)
        
        assert isinstance(detections, list)
        
        for bbox, class_name, confidence in detections:
            assert isinstance(bbox, BoundingBox)
            assert isinstance(class_name, str)
            assert 0 <= confidence <= 1
    
    def test_detect_with_confidence_threshold(self):
        """Test detection respects confidence threshold."""
        detector = YOLODefectDetector()
        
        image = np.random.rand(640, 640, 3)
        
        # All detections should be above threshold
        threshold = 0.5
        detections = detector.detect(image, confidence_threshold=threshold)
        
        for _, _, confidence in detections:
            assert confidence >= threshold
    
    def test_defect_classes_defined(self):
        """Test that defect classes are defined."""
        assert len(YOLODefectDetector.DEFECT_CLASSES) > 0
        assert "scratch" in YOLODefectDetector.DEFECT_CLASSES
        assert "crack" in YOLODefectDetector.DEFECT_CLASSES


# =============================================================================
# QualityScoringEngine Tests
# =============================================================================


class TestQualityScoringEngine:
    """Tests for QualityScoringEngine."""
    
    def test_calculate_score_no_defects(self):
        """Test perfect score with no defects."""
        engine = QualityScoringEngine()
        
        score, zone_scores = engine.calculate_score([])
        
        assert score == 100.0
    
    def test_calculate_score_with_critical_defect(self):
        """Test score reduction with critical defect."""
        engine = QualityScoringEngine()
        
        defects = [
            DetectedDefect("d1", DefectCategory.MATERIAL, DefectSeverity.CRITICAL, 1.0)
        ]
        
        score, _ = engine.calculate_score(defects)
        
        # Critical defect should significantly reduce score
        assert score < 10
    
    def test_calculate_score_with_minor_defects(self):
        """Test score reduction with minor defects."""
        engine = QualityScoringEngine()
        
        defects = [
            DetectedDefect("d1", DefectCategory.SURFACE, DefectSeverity.MINOR, 1.0),
            DetectedDefect("d2", DefectCategory.SURFACE, DefectSeverity.MINOR, 1.0),
        ]
        
        score, _ = engine.calculate_score(defects)
        
        # Minor defects should only slightly reduce score
        assert score >= 80
    
    def test_calculate_score_confidence_weighting(self):
        """Test that confidence affects score."""
        engine = QualityScoringEngine()
        
        # Low confidence defect
        low_conf = [
            DetectedDefect("d1", DefectCategory.SURFACE, DefectSeverity.MAJOR, 0.5)
        ]
        
        # High confidence defect
        high_conf = [
            DetectedDefect("d1", DefectCategory.SURFACE, DefectSeverity.MAJOR, 1.0)
        ]
        
        low_score, _ = engine.calculate_score(low_conf)
        high_score, _ = engine.calculate_score(high_conf)
        
        # Lower confidence should result in higher score
        assert low_score > high_score
    
    def test_make_decision_pass(self):
        """Test pass decision with no defects."""
        engine = QualityScoringEngine()
        config = InspectionConfig()
        
        decision, reason = engine.make_decision([], 100.0, config)
        
        assert decision == InspectionDecision.PASS
    
    def test_make_decision_fail_critical(self):
        """Test fail decision with critical defect."""
        engine = QualityScoringEngine()
        config = InspectionConfig(fail_on_critical=True)
        
        defects = [
            DetectedDefect("d1", DefectCategory.MATERIAL, DefectSeverity.CRITICAL, 0.9)
        ]
        
        decision, reason = engine.make_decision(defects, 50.0, config)
        
        assert decision == InspectionDecision.FAIL
        assert "critical" in reason.lower()
    
    def test_make_decision_fail_threshold(self):
        """Test fail decision when below quality threshold."""
        engine = QualityScoringEngine()
        config = InspectionConfig(quality_threshold=80.0)
        
        defects = [
            DetectedDefect("d1", DefectCategory.SURFACE, DefectSeverity.MINOR, 0.8)
        ]
        
        decision, reason = engine.make_decision(defects, 70.0, config)
        
        assert decision == InspectionDecision.FAIL
        assert "threshold" in reason.lower()
    
    def test_make_decision_review_minor(self):
        """Test review decision with minor defects."""
        engine = QualityScoringEngine()
        config = InspectionConfig(
            fail_on_major=False,
            review_on_minor=True,
            max_minor_defects=1,
        )
        
        defects = [
            DetectedDefect("d1", DefectCategory.SURFACE, DefectSeverity.MINOR, 0.8)
        ]
        
        decision, reason = engine.make_decision(defects, 95.0, config)
        
        assert decision == InspectionDecision.REVIEW


# =============================================================================
# ContinuousLearningManager Tests
# =============================================================================


class TestContinuousLearningManager:
    """Tests for ContinuousLearningManager."""
    
    def test_record_feedback(self):
        """Test recording feedback."""
        manager = ContinuousLearningManager()
        
        feedback = FeedbackRecord(
            inspection_id="i1",
            timestamp=datetime.utcnow(),
            original_decision=InspectionDecision.PASS,
            corrected_decision=InspectionDecision.FAIL,
            false_negative_boxes=[(BoundingBox(0, 0, 50, 50), "crack")],
        )
        
        manager.record_feedback(feedback)
        
        assert len(manager.feedback_queue) == 1
    
    def test_get_training_recommendations(self):
        """Test getting training recommendations."""
        manager = ContinuousLearningManager()
        
        # Add some feedback
        for i in range(10):
            feedback = FeedbackRecord(
                inspection_id=f"i{i}",
                timestamp=datetime.utcnow(),
                original_decision=InspectionDecision.PASS,
                false_positive_ids=["d1"],
            )
            manager.record_feedback(feedback)
        
        recommendations = manager.get_training_recommendations()
        
        assert recommendations["total_feedback"] == 10
        assert recommendations["false_positives"] == 10
    
    def test_retraining_threshold(self):
        """Test retraining is triggered at threshold."""
        manager = ContinuousLearningManager(feedback_threshold=5)
        
        for i in range(5):
            feedback = FeedbackRecord(
                inspection_id=f"i{i}",
                timestamp=datetime.utcnow(),
                original_decision=InspectionDecision.PASS,
            )
            manager.record_feedback(feedback)
        
        recommendations = manager.get_training_recommendations()
        
        assert recommendations["ready_for_retraining"] is True


# =============================================================================
# VisualQualityInspectionService Tests
# =============================================================================


class TestVisualQualityInspectionService:
    """Tests for VisualQualityInspectionService."""
    
    def test_inspect_image_returns_result(self):
        """Test image inspection returns result."""
        service = VisualQualityInspectionService()
        
        image = np.random.rand(640, 640, 3)
        result = run_async(service.inspect_image(image))
        
        assert isinstance(result, InspectionResult)
        assert result.inspection_id is not None
        assert result.decision in InspectionDecision
    
    def test_inspect_image_with_custom_config(self):
        """Test inspection with custom configuration."""
        config = InspectionConfig(
            model_type=ModelType.DEFECT_DETECTION,
            detection_confidence=0.7,
            quality_threshold=90.0,
        )
        
        service = VisualQualityInspectionService(config=config)
        
        image = np.random.rand(640, 640, 3)
        result = run_async(service.inspect_image(image))
        
        assert isinstance(result, InspectionResult)
    
    def test_inspect_batch(self):
        """Test batch inspection."""
        service = VisualQualityInspectionService()
        
        images = [
            (np.random.rand(640, 640, 3), f"img_{i}")
            for i in range(3)
        ]
        
        batch = run_async(service.inspect_batch(images))
        
        assert isinstance(batch, InspectionBatch)
        assert len(batch.results) == 3
        assert batch.total_inspected == 3
    
    def test_train_anomaly_detector(self):
        """Test training anomaly detector."""
        service = VisualQualityInspectionService()
        
        normal_images = [np.random.rand(224, 224, 3) for _ in range(10)]
        
        result = service.train_anomaly_detector(normal_images)
        
        assert "num_images" in result
        assert result["num_images"] == 10
        assert "memory_bank_size" in result
    
    def test_record_feedback(self):
        """Test recording operator feedback."""
        service = VisualQualityInspectionService()
        
        service.record_feedback(
            inspection_id="i1",
            corrected_decision=InspectionDecision.FAIL,
            false_positive_ids=["d1"],
            operator_id="op1",
            notes="Missed scratch",
        )
        
        status = service.get_learning_status()
        assert status["total_feedback"] >= 1
    
    def test_inspect_image_logs_processing_time(self):
        """Test that inspection logs processing time."""
        service = VisualQualityInspectionService()
        
        image = np.random.rand(640, 640, 3)
        result = run_async(service.inspect_image(image))
        
        assert result.processing_time_ms > 0
    
    def test_inspect_image_with_zones(self):
        """Test inspection with defined zones."""
        zones = [
            InspectionZone(
                zone_id="z1",
                zone_type=ZoneType.CRITICAL,
                bbox=BoundingBox(0, 0, 320, 320),
                name="Critical Zone",
            ),
            InspectionZone(
                zone_id="z2",
                zone_type=ZoneType.COSMETIC,
                bbox=BoundingBox(320, 0, 320, 320),
                name="Cosmetic Zone",
            ),
        ]
        
        config = InspectionConfig(zones=zones)
        service = VisualQualityInspectionService(config=config)
        
        image = np.random.rand(640, 640, 3)
        result = run_async(service.inspect_image(image))
        
        assert isinstance(result, InspectionResult)


# =============================================================================
# Integration Tests
# =============================================================================


class TestVisualQualityInspectionIntegration:
    """Integration tests for visual quality inspection."""
    
    def test_full_inspection_pipeline(self):
        """Test complete inspection pipeline."""
        config = InspectionConfig(
            model_type=ModelType.DEFECT_DETECTION,
            anomaly_threshold=0.5,
            detection_confidence=0.5,
            quality_threshold=80.0,
        )
        
        service = VisualQualityInspectionService(config=config)
        
        # Train on normal images
        normal_images = [np.random.rand(224, 224, 3) for _ in range(5)]
        service.train_anomaly_detector(normal_images)
        
        # Inspect test images
        test_images = [
            (np.random.rand(640, 640, 3), f"test_{i}")
            for i in range(5)
        ]
        
        batch = run_async(service.inspect_batch(test_images))
        
        assert batch.total_inspected == 5
        assert batch.pass_count + batch.fail_count + batch.review_count == 5
    
    def test_feedback_loop_integration(self):
        """Test continuous learning feedback loop."""
        service = VisualQualityInspectionService()
        
        # Perform inspections
        for i in range(5):
            image = np.random.rand(640, 640, 3)
            result = run_async(service.inspect_image(image, f"img_{i}"))
            
            # Record feedback (simulate operator review)
            service.record_feedback(
                inspection_id=result.inspection_id,
                corrected_decision=None,  # Agree with decision
                operator_id="op1",
            )
        
        status = service.get_learning_status()
        
        assert status["total_feedback"] >= 5


# =============================================================================
# Edge Cases
# =============================================================================


class TestVisualQualityInspectionEdgeCases:
    """Edge case tests for visual quality inspection."""
    
    def test_inspect_grayscale_image(self):
        """Test inspection of grayscale image."""
        service = VisualQualityInspectionService()
        
        # Grayscale image (2D)
        image = np.random.rand(640, 640)
        
        # Should handle gracefully (may need to convert to 3-channel)
        result = run_async(service.inspect_image(image))
        
        assert isinstance(result, InspectionResult)
    
    def test_inspect_small_image(self):
        """Test inspection of very small image."""
        service = VisualQualityInspectionService()
        
        image = np.random.rand(32, 32, 3)
        result = run_async(service.inspect_image(image))
        
        assert isinstance(result, InspectionResult)
    
    def test_inspect_large_image(self):
        """Test inspection of large image."""
        service = VisualQualityInspectionService()
        
        image = np.random.rand(2048, 2048, 3)
        result = run_async(service.inspect_image(image))
        
        assert isinstance(result, InspectionResult)
    
    def test_quality_scoring_edge_cases(self):
        """Test quality scoring with edge case inputs."""
        engine = QualityScoringEngine()
        
        # All critical defects
        all_critical = [
            DetectedDefect(f"d{i}", DefectCategory.MATERIAL, DefectSeverity.CRITICAL, 1.0)
            for i in range(10)
        ]
        
        score, _ = engine.calculate_score(all_critical)
        
        # Score should be clamped to 0
        assert score >= 0
    
    def test_empty_batch_inspection(self):
        """Test batch inspection with no images."""
        service = VisualQualityInspectionService()
        
        batch = run_async(service.inspect_batch([]))
        
        assert batch.total_inspected == 0
        assert batch.pass_rate == 1.0


# =============================================================================
# Performance Tests
# =============================================================================


class TestVisualQualityInspectionPerformance:
    """Performance tests for visual quality inspection."""
    
    def test_inspection_latency(self):
        """Test that inspection completes in reasonable time."""
        service = VisualQualityInspectionService()
        
        image = np.random.rand(640, 640, 3)
        result = run_async(service.inspect_image(image))
        
        # Simulated inspection should be fast
        assert result.processing_time_ms < 1000
    
    def test_batch_inspection_throughput(self):
        """Test batch inspection throughput."""
        service = VisualQualityInspectionService()
        
        images = [(np.random.rand(640, 640, 3), f"img_{i}") for i in range(10)]
        
        import time
        start = time.time()
        batch = run_async(service.inspect_batch(images))
        elapsed = (time.time() - start) * 1000
        
        # Should process all images
        assert batch.total_inspected == 10
        
        # Average time per image should be reasonable
        avg_time = elapsed / 10
        assert avg_time < 500  # Less than 500ms per image
