"""
Tests for ONNX Edge AI Inference Module.

Tests the edge inference module with ONNX Runtime support.
"""

import pytest
import numpy as np


class TestONNXEdgeConfig:
    """Tests for ONNXEdgeConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeConfig
        from pathlib import Path
        
        config = ONNXEdgeConfig(
            model_name="test_model",
            cache_dir=Path("/tmp/test"),
        )
        
        assert config.model_name == "test_model"
        assert config.input_length == 256
        assert config.num_classes == 4
        assert config.quantize_int8 is True
        assert config.warmup_on_init is True
        assert config.batch_size == 32
    
    def test_custom_config(self):
        """Test custom configuration."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeConfig
        from pathlib import Path
        
        config = ONNXEdgeConfig(
            model_name="custom_model",
            cache_dir=Path("/tmp/custom"),
            input_length=512,
            num_classes=8,
            quantize_int8=False,
            warmup_on_init=False,
            batch_size=64,
        )
        
        assert config.input_length == 512
        assert config.num_classes == 8
        assert config.quantize_int8 is False


class TestONNXEdgeInference:
    """Tests for ONNXEdgeInference."""
    
    def test_inference_creation(self):
        """Test inference engine can be created."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        assert inference is not None
    
    def test_is_ready(self):
        """Test is_ready returns boolean."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        assert isinstance(inference.is_ready(), bool)
    
    def test_is_using_onnx(self):
        """Test is_using_onnx returns boolean."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        assert isinstance(inference.is_using_onnx(), bool)
    
    def test_predict_returns_probabilities(self):
        """Test predict returns probability distribution."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        
        # Create test signal
        signal = [0.5] * 256
        probs = inference.predict(signal)
        
        assert isinstance(probs, list)
        assert len(probs) == 4  # 4 classes
        for p in probs:
            assert 0.0 <= p <= 1.0
    
    def test_predict_short_signal(self):
        """Test predict pads short signals."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        
        # Short signal
        signal = [0.1, 0.2, 0.3]
        probs = inference.predict(signal)
        
        assert len(probs) == 4
    
    def test_predict_long_signal(self):
        """Test predict truncates long signals."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        
        # Long signal
        signal = [0.5] * 1000
        probs = inference.predict(signal)
        
        assert len(probs) == 4
    
    def test_classify_returns_tuple(self):
        """Test classify returns (class_idx, confidence, label)."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        
        signal = [0.3] * 256
        class_idx, confidence, label = inference.classify(signal)
        
        assert isinstance(class_idx, int)
        assert 0 <= class_idx < 4
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert label in ["normal", "warning", "critical", "emergency"]
    
    def test_predict_batch(self):
        """Test batch prediction."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        
        signals = [
            [0.1] * 256,
            [0.5] * 256,
            [0.9] * 256,
        ]
        
        all_probs = inference.predict_batch(signals)
        
        assert len(all_probs) == 3
        for probs in all_probs:
            assert len(probs) == 4
    
    def test_predict_batch_empty(self):
        """Test batch prediction with empty input."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        result = inference.predict_batch([])
        
        assert result == []
    
    def test_classify_batch(self):
        """Test batch classification."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        inference = ONNXEdgeInference()
        
        signals = [
            [0.1] * 256,
            [0.5] * 256,
        ]
        
        results = inference.classify_batch(signals)
        
        assert len(results) == 2
        for class_idx, confidence, label in results:
            assert isinstance(class_idx, int)
            assert isinstance(confidence, float)
            assert isinstance(label, str)
    
    def test_class_labels(self):
        """Test class labels are defined correctly."""
        from sensei.services.core.onnx_edge_inference import ONNXEdgeInference
        
        assert ONNXEdgeInference.CLASS_LABELS == [
            "normal", "warning", "critical", "emergency"
        ]


class TestGetONNXEdgeInference:
    """Tests for singleton function."""
    
    def test_returns_inference(self):
        """Test singleton returns inference engine."""
        from sensei.services.core.onnx_edge_inference import get_onnx_edge_inference
        
        inference = get_onnx_edge_inference()
        assert inference is not None
    
    def test_returns_same_instance(self):
        """Test singleton returns same instance."""
        from sensei.services.core.onnx_edge_inference import get_onnx_edge_inference
        
        inf1 = get_onnx_edge_inference()
        inf2 = get_onnx_edge_inference()
        
        assert inf1 is inf2


class TestEdgeAIWithONNX:
    """Integration tests for edge AI with ONNX support."""
    
    def test_predictive_maintenance_engine(self):
        """Test PredictiveMaintenanceEngine uses ONNX or fallback."""
        from sensei.services.core.edge_ai import (
            PredictiveMaintenanceEngine,
            SensorReading,
            AnomalyType,
        )
        from datetime import datetime
        
        engine = PredictiveMaintenanceEngine(use_onnx=True)
        
        reading = SensorReading(
            sensor_id="sensor-001",
            machine_id="machine-001",
            timestamp=datetime.now(),
            values=[0.1 + 0.01 * i for i in range(256)],
            sample_rate=1000,
            reading_type=AnomalyType.VIBRATION,
        )
        
        detection = engine.analyze_reading(reading)
        
        assert detection is not None
        assert detection.machine_id == "machine-001"
        assert 0.0 <= detection.confidence <= 1.0
    
    def test_predictive_maintenance_without_onnx(self):
        """Test PredictiveMaintenanceEngine works without ONNX."""
        from sensei.services.core.edge_ai import (
            PredictiveMaintenanceEngine,
            SensorReading,
            AnomalyType,
        )
        from datetime import datetime
        
        # Force pure-Python mode
        engine = PredictiveMaintenanceEngine(use_onnx=False)
        
        reading = SensorReading(
            sensor_id="sensor-002",
            machine_id="machine-002",
            timestamp=datetime.now(),
            values=[0.5] * 256,
            sample_rate=1000,
            reading_type=AnomalyType.TEMPERATURE,
        )
        
        detection = engine.analyze_reading(reading)
        
        assert detection is not None
        assert detection.machine_id == "machine-002"
