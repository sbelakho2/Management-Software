"""
Tests for ML Module: Condition-Based Maintenance Predictor

Tests the hybrid ML/rule-based system for predicting equipment maintenance needs.
"""

import pytest
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from unittest.mock import patch
import tempfile

from sensei.ml.cbm_predictor import (
    ConditionBasedMaintenancePredictor,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Mock Models
# =============================================================================

class MockEquipment:
    """Mock Equipment model for testing."""
    
    def __init__(
        self,
        equipment_id: str,
        name: str = "Test Equipment",
        installation_date: datetime = None,
        total_operating_hours: float = None,
        total_cycles: int = None,
    ):
        self.id = equipment_id
        self.name = name
        self.installation_date = installation_date or _utcnow() - timedelta(days=365)
        self.total_operating_hours = total_operating_hours or 5000
        self.total_cycles = total_cycles or 100000


class MockMaintenanceRecord:
    """Mock MaintenanceRecord model for testing."""
    
    def __init__(
        self,
        equipment_id: str,
        date: datetime = None,
        maintenance_type: str = "preventive",
        description: str = "Regular maintenance",
    ):
        self.equipment_id = equipment_id
        self.date = date or _utcnow() - timedelta(days=30)
        self.maintenance_type = maintenance_type
        self.description = description


class MockConditionReading:
    """Mock ConditionReading model for testing."""
    
    def __init__(
        self,
        equipment_id: str,
        timestamp: datetime = None,
        temperature: float = None,
        vibration: float = None,
        pressure: float = None,
        current: float = None,
        noise: float = None,
        operating_hours: float = None,
    ):
        self.equipment_id = equipment_id
        self.timestamp = timestamp or _utcnow()
        self.temperature = temperature
        self.vibration = vibration
        self.pressure = pressure
        self.current = current
        self.noise = noise
        self.operating_hours = operating_hours


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def healthy_equipment():
    """Create equipment with normal operating parameters."""
    return MockEquipment(
        equipment_id="EQ-001",
        name="CNC Machine 1",
        installation_date=_utcnow() - timedelta(days=365),
        total_operating_hours=5000,
        total_cycles=100000,
    )


@pytest.fixture
def aging_equipment():
    """Create aging equipment with high hours."""
    return MockEquipment(
        equipment_id="EQ-002",
        name="Old Press Machine",
        installation_date=_utcnow() - timedelta(days=365*5),
        total_operating_hours=50000,
        total_cycles=1000000,
    )


@pytest.fixture
def normal_readings(healthy_equipment):
    """Create normal condition readings."""
    base_time = _utcnow()
    return [
        MockConditionReading(
            equipment_id=healthy_equipment.id,
            timestamp=base_time - timedelta(hours=i),
            temperature=45 + np.random.uniform(-2, 2),
            vibration=3 + np.random.uniform(-0.5, 0.5),
            pressure=100 + np.random.uniform(-5, 5),
            current=10 + np.random.uniform(-1, 1),
            noise=70 + np.random.uniform(-3, 3),
            operating_hours=5000 + i,
        )
        for i in range(10)
    ]


@pytest.fixture
def critical_readings(healthy_equipment):
    """Create readings with critical values."""
    base_time = _utcnow()
    return [
        MockConditionReading(
            equipment_id=healthy_equipment.id,
            timestamp=base_time - timedelta(hours=i),
            temperature=90,  # Critical: > 80
            vibration=15,    # Critical: > 10
            pressure=160,    # Critical: > 150
            current=25,      # Critical: > 20
            noise=90,        # Critical: > 85
            operating_hours=5000 + i,
        )
        for i in range(5)
    ]


@pytest.fixture
def degrading_readings(healthy_equipment):
    """Create readings showing degradation trend."""
    base_time = _utcnow()
    readings = []
    for i in range(10):
        # Trend: temperature and vibration increasing over time
        readings.append(MockConditionReading(
            equipment_id=healthy_equipment.id,
            timestamp=base_time - timedelta(hours=9-i),  # Oldest first
            temperature=45 + (i * 2),  # 45 -> 63
            vibration=3 + (i * 0.5),   # 3 -> 7.5
            pressure=100,
            current=10,
            noise=70,
            operating_hours=5000 + i,
        ))
    return readings


@pytest.fixture
def maintenance_history(healthy_equipment):
    """Create maintenance history."""
    return [
        MockMaintenanceRecord(
            equipment_id=healthy_equipment.id,
            date=_utcnow() - timedelta(days=90),
            maintenance_type="preventive",
        ),
        MockMaintenanceRecord(
            equipment_id=healthy_equipment.id,
            date=_utcnow() - timedelta(days=60),
            maintenance_type="preventive",
        ),
        MockMaintenanceRecord(
            equipment_id=healthy_equipment.id,
            date=_utcnow() - timedelta(days=30),
            maintenance_type="preventive",
        ),
    ]


@pytest.fixture
def temp_model_path():
    """Create temporary directory for model artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Test: Initialization
# =============================================================================

class TestCBMPredictorInit:
    """Test ConditionBasedMaintenancePredictor initialization."""
    
    def test_init_with_default_path(self):
        """Test initialization with default model path."""
        predictor = ConditionBasedMaintenancePredictor()
        assert predictor.failure_classifier is None
        assert predictor.anomaly_detector is None
        assert predictor.scaler is None
    
    def test_init_with_custom_path(self, temp_model_path):
        """Test initialization with custom model path."""
        predictor = ConditionBasedMaintenancePredictor(model_path=temp_model_path)
        assert predictor.model_path == temp_model_path


# =============================================================================
# Test: Critical Threshold Detection
# =============================================================================

class TestCriticalThresholdDetection:
    """Test detection of critical threshold violations."""
    
    def test_detect_critical_temperature(self, healthy_equipment, maintenance_history):
        """Test detection of critical temperature."""
        predictor = ConditionBasedMaintenancePredictor()
        
        critical_reading = MockConditionReading(
            equipment_id=healthy_equipment.id,
            temperature=85,  # > 80 threshold
            vibration=3,
            pressure=100,
        )
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=[critical_reading],
            maintenance_history=maintenance_history,
        )
        
        assert result['risk_level'] == 'critical'
        assert result['failure_probability'] == 1.0
    
    def test_detect_critical_vibration(self, healthy_equipment, maintenance_history):
        """Test detection of critical vibration."""
        predictor = ConditionBasedMaintenancePredictor()
        
        critical_reading = MockConditionReading(
            equipment_id=healthy_equipment.id,
            temperature=50,
            vibration=12,  # > 10 threshold
            pressure=100,
        )
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=[critical_reading],
            maintenance_history=maintenance_history,
        )
        
        assert result['risk_level'] == 'critical'
    
    def test_detect_multiple_critical_issues(self, healthy_equipment, critical_readings, maintenance_history):
        """Test detection of multiple critical issues."""
        predictor = ConditionBasedMaintenancePredictor()
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=critical_readings,
            maintenance_history=maintenance_history,
        )
        
        assert result['risk_level'] == 'critical'
        # Should have multiple recommendations for immediate action
        assert len(result['recommendations']) >= 1
        assert result['estimated_time_to_failure'] == 0


# =============================================================================
# Test: Normal Operation Detection
# =============================================================================

class TestNormalOperationDetection:
    """Test detection of normal operating conditions."""
    
    def test_normal_readings_low_risk(self, healthy_equipment, normal_readings, maintenance_history):
        """Test that normal readings result in low risk."""
        predictor = ConditionBasedMaintenancePredictor()
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=normal_readings,
            maintenance_history=maintenance_history,
        )
        
        # Should not be critical
        assert result['risk_level'] != 'critical'
        assert result['failure_probability'] < 1.0


# =============================================================================
# Test: Empty/Missing Data Handling
# =============================================================================

class TestMissingDataHandling:
    """Test handling of missing or empty data."""
    
    def test_no_readings_returns_unknown(self, healthy_equipment, maintenance_history):
        """Test that no readings returns unknown risk level."""
        predictor = ConditionBasedMaintenancePredictor()
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=[],
            maintenance_history=maintenance_history,
        )
        
        assert result['risk_level'] == 'unknown'
        assert result['failure_probability'] == 0.0
        assert 'No condition data available' in result['reasons']
    
    def test_partial_readings(self, healthy_equipment, maintenance_history):
        """Test handling readings with some None values."""
        predictor = ConditionBasedMaintenancePredictor()
        
        partial_reading = MockConditionReading(
            equipment_id=healthy_equipment.id,
            temperature=50,
            vibration=None,  # Missing
            pressure=None,   # Missing
        )
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=[partial_reading],
            maintenance_history=maintenance_history,
        )
        
        # Should handle gracefully
        assert result is not None
        assert 'risk_level' in result


# =============================================================================
# Test: Result Structure
# =============================================================================

class TestResultStructure:
    """Test prediction result structure."""
    
    def test_result_has_all_fields(self, healthy_equipment, normal_readings, maintenance_history):
        """Test that results have all expected fields."""
        predictor = ConditionBasedMaintenancePredictor()
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=normal_readings,
            maintenance_history=maintenance_history,
        )
        
        assert 'risk_level' in result
        assert 'failure_probability' in result
        assert 'is_anomaly' in result
        assert 'recommendations' in result
        assert 'reasons' in result
    
    def test_risk_level_valid_values(self, healthy_equipment, normal_readings, maintenance_history):
        """Test that risk level is a valid value."""
        predictor = ConditionBasedMaintenancePredictor()
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=normal_readings,
            maintenance_history=maintenance_history,
        )
        
        valid_levels = {'low', 'medium', 'high', 'critical', 'unknown'}
        assert result['risk_level'] in valid_levels
    
    def test_failure_probability_range(self, healthy_equipment, normal_readings, maintenance_history):
        """Test that failure probability is in valid range."""
        predictor = ConditionBasedMaintenancePredictor()
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=normal_readings,
            maintenance_history=maintenance_history,
        )
        
        assert 0 <= result['failure_probability'] <= 1
    
    def test_recommendations_are_actionable(self, healthy_equipment, critical_readings, maintenance_history):
        """Test that recommendations have action info."""
        predictor = ConditionBasedMaintenancePredictor()
        
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=critical_readings,
            maintenance_history=maintenance_history,
        )
        
        for rec in result['recommendations']:
            assert 'action' in rec
            assert 'reason' in rec or 'parameter' in rec


# =============================================================================
# Test: Feature Extraction
# =============================================================================

class TestFeatureExtraction:
    """Test feature extraction for ML models."""
    
    def test_extract_features_returns_array(self, healthy_equipment, normal_readings, maintenance_history):
        """Test that feature extraction returns numpy array."""
        predictor = ConditionBasedMaintenancePredictor()
        
        features = predictor._extract_features(
            equipment=healthy_equipment,
            recent_readings=normal_readings,
            maintenance_history=maintenance_history,
        )
        
        assert isinstance(features, np.ndarray)
        assert features.ndim == 1
    
    def test_extract_features_consistent_size(self, healthy_equipment, normal_readings, maintenance_history):
        """Test that feature vector has consistent size."""
        predictor = ConditionBasedMaintenancePredictor()
        
        # With full readings
        features1 = predictor._extract_features(
            equipment=healthy_equipment,
            recent_readings=normal_readings,
            maintenance_history=maintenance_history,
        )
        
        # With minimal readings
        features2 = predictor._extract_features(
            equipment=healthy_equipment,
            recent_readings=normal_readings[:2],
            maintenance_history=[],
        )
        
        # Should have same dimensionality
        assert features1.shape == features2.shape
    
    def test_extract_features_handles_empty_history(self, healthy_equipment, normal_readings):
        """Test feature extraction with empty maintenance history."""
        predictor = ConditionBasedMaintenancePredictor()
        
        features = predictor._extract_features(
            equipment=healthy_equipment,
            recent_readings=normal_readings,
            maintenance_history=[],
        )
        
        assert features is not None
        assert len(features) > 0


# =============================================================================
# Test: Training
# =============================================================================

class TestCBMTraining:
    """Test CBM predictor training."""
    
    def test_train_with_insufficient_data(self, temp_model_path, healthy_equipment, normal_readings, maintenance_history):
        """Test training with insufficient data."""
        predictor = ConditionBasedMaintenancePredictor(model_path=temp_model_path)
        
        # Just a few records - should warn about insufficient data
        metrics = predictor.train(
            equipment_list=[healthy_equipment],
            maintenance_records=maintenance_history,
            condition_readings=normal_readings,
        )
        
        # Should indicate insufficient data or handle gracefully
        assert 'error' in metrics or 'f1_mean' in metrics


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestCBMEdgeCases:
    """Test edge cases and error handling."""
    
    def test_new_equipment_no_history(self, maintenance_history):
        """Test prediction for new equipment with no history."""
        new_equipment = MockEquipment(
            equipment_id="EQ-NEW",
            installation_date=_utcnow() - timedelta(days=1),
            total_operating_hours=10,
            total_cycles=100,
        )
        
        reading = MockConditionReading(
            equipment_id=new_equipment.id,
            temperature=50,
            vibration=3,
        )
        
        predictor = ConditionBasedMaintenancePredictor()
        result = predictor.predict_maintenance_needs(
            equipment=new_equipment,
            recent_readings=[reading],
            maintenance_history=[],
        )
        
        assert result is not None
        assert 'risk_level' in result
    
    def test_very_old_equipment(self, critical_readings):
        """Test prediction for very old equipment."""
        old_equipment = MockEquipment(
            equipment_id="EQ-OLD",
            installation_date=_utcnow() - timedelta(days=365*20),
            total_operating_hours=200000,
            total_cycles=5000000,
        )
        
        predictor = ConditionBasedMaintenancePredictor()
        result = predictor.predict_maintenance_needs(
            equipment=old_equipment,
            recent_readings=critical_readings[:1],
            maintenance_history=[],
        )
        
        # Critical readings should still trigger critical level
        assert result['risk_level'] == 'critical'
    
    def test_single_reading(self, healthy_equipment, maintenance_history):
        """Test prediction with single reading."""
        single_reading = MockConditionReading(
            equipment_id=healthy_equipment.id,
            temperature=50,
            vibration=3,
            pressure=100,
        )
        
        predictor = ConditionBasedMaintenancePredictor()
        result = predictor.predict_maintenance_needs(
            equipment=healthy_equipment,
            recent_readings=[single_reading],
            maintenance_history=maintenance_history,
        )
        
        assert result is not None
        assert result['risk_level'] != 'unknown'


# =============================================================================
# Test: Threshold Configuration
# =============================================================================

class TestThresholdConfiguration:
    """Test critical threshold configuration."""
    
    def test_thresholds_defined(self):
        """Test that critical thresholds are defined."""
        thresholds = ConditionBasedMaintenancePredictor.CRITICAL_THRESHOLDS
        
        assert 'temperature' in thresholds
        assert 'vibration' in thresholds
        assert 'pressure' in thresholds
        assert 'current' in thresholds
        assert 'noise' in thresholds
    
    def test_thresholds_have_max_and_unit(self):
        """Test that thresholds have max value and unit."""
        thresholds = ConditionBasedMaintenancePredictor.CRITICAL_THRESHOLDS
        
        for param, config in thresholds.items():
            assert 'max' in config
            assert 'unit' in config
            assert isinstance(config['max'], (int, float))
    
    def test_temperature_threshold_value(self):
        """Test temperature threshold is reasonable."""
        thresholds = ConditionBasedMaintenancePredictor.CRITICAL_THRESHOLDS
        
        # Should be around 80°C for equipment
        assert thresholds['temperature']['max'] == 80
        assert thresholds['temperature']['unit'] == '°C'
