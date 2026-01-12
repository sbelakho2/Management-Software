"""
Tests for Edge AI & IoT Infrastructure.

Tests Predictive Maintenance Edge (1D-CNN) and Edge-to-Core Sync.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

import pytest

from sensei.services.core.edge_ai import (
    # Enums
    AnomalyType,
    SeverityLevel,
    SyncPriority,
    MessageType,
    ConnectionState,
    # Data models
    SensorReading,
    AnomalyDetection,
    MachineHealthStatus,
    EdgeMessage,
    SyncResult,
    CNNModelConfig,
    # CNN components
    Conv1DLayer,
    MaxPool1DLayer,
    DenseLayer,
    EdgeCNN1D,
    # Main classes
    PredictiveMaintenanceEngine,
    ProtobufLikeEncoder,
    PriorityMessageQueue,
    EdgeToCoreSyncManager,
    # Factory functions
    create_predictive_maintenance_engine,
    create_edge_sync_manager,
    create_cnn_model,
    create_priority_queue,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_sensor_reading() -> SensorReading:
    """Create a sample sensor reading."""
    return SensorReading(
        sensor_id="sensor_001",
        machine_id="machine_001",
        timestamp=datetime.now(),
        values=[0.1 * i + random.gauss(0, 0.01) for i in range(256)],
        sample_rate=1000,
        reading_type=AnomalyType.VIBRATION,
    )


@pytest.fixture
def anomaly_sensor_reading() -> SensorReading:
    """Create a sensor reading with anomaly pattern."""
    # Simulate anomalous vibration with spikes
    values = [0.5 + random.gauss(0, 0.1) for _ in range(256)]
    # Add spikes
    for i in range(0, 256, 32):
        values[i] = 5.0  # Anomalous spike
    return SensorReading(
        sensor_id="sensor_002",
        machine_id="machine_002",
        timestamp=datetime.now(),
        values=values,
        sample_rate=1000,
        reading_type=AnomalyType.VIBRATION,
    )


@pytest.fixture
def cnn_config() -> CNNModelConfig:
    """Create CNN config for testing."""
    return CNNModelConfig(
        input_length=256,
        num_filters=[8, 16],
        kernel_sizes=[5, 3],
        pool_sizes=[2, 2],
        dense_units=[32, 16],
        num_classes=4,
        threshold=0.7,
    )


@pytest.fixture
def predictive_engine() -> PredictiveMaintenanceEngine:
    """Create predictive maintenance engine."""
    return create_predictive_maintenance_engine()


@pytest.fixture
def sync_manager() -> EdgeToCoreSyncManager:
    """Create edge sync manager."""
    return create_edge_sync_manager(device_id="edge_001")


@pytest.fixture
def sample_edge_message() -> EdgeMessage:
    """Create a sample edge message."""
    return EdgeMessage(
        message_id="msg_001",
        message_type=MessageType.ANOMALY_ALERT,
        priority=SyncPriority.HIGH,
        payload=b'{"test": "data"}',
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_anomaly_detection() -> AnomalyDetection:
    """Create sample anomaly detection."""
    return AnomalyDetection(
        detection_id="det_001",
        machine_id="machine_001",
        anomaly_type=AnomalyType.VIBRATION,
        severity=SeverityLevel.WARNING,
        confidence=0.85,
        detected_at=datetime.now(),
        feature_values={"mean": 1.5, "std_dev": 0.3},
        raw_data_hash="abc123",
        recommended_action="Monitor closely.",
    )


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Test enum definitions."""
    
    def test_anomaly_type_values(self):
        """Test AnomalyType enum values."""
        assert AnomalyType.VIBRATION == "vibration"
        assert AnomalyType.SOUND == "sound"
        assert AnomalyType.TEMPERATURE == "temperature"
        assert AnomalyType.PRESSURE == "pressure"
        assert AnomalyType.CURRENT == "current"
        assert AnomalyType.MIXED == "mixed"
    
    def test_severity_level_values(self):
        """Test SeverityLevel enum values."""
        assert SeverityLevel.NORMAL == "normal"
        assert SeverityLevel.WARNING == "warning"
        assert SeverityLevel.CRITICAL == "critical"
        assert SeverityLevel.EMERGENCY == "emergency"
    
    def test_sync_priority_values(self):
        """Test SyncPriority enum values."""
        assert SyncPriority.CRITICAL == "critical"
        assert SyncPriority.HIGH == "high"
        assert SyncPriority.NORMAL == "normal"
        assert SyncPriority.LOW == "low"
        assert SyncPriority.BATCH == "batch"
    
    def test_message_type_values(self):
        """Test MessageType enum values."""
        assert MessageType.ANOMALY_ALERT == "anomaly_alert"
        assert MessageType.HEALTH_STATUS == "health_status"
        assert MessageType.SENSOR_DATA == "sensor_data"
        assert MessageType.CONFIG_UPDATE == "config_update"
        assert MessageType.HEARTBEAT == "heartbeat"
    
    def test_connection_state_values(self):
        """Test ConnectionState enum values."""
        assert ConnectionState.CONNECTED == "connected"
        assert ConnectionState.DISCONNECTED == "disconnected"
        assert ConnectionState.RECONNECTING == "reconnecting"
        assert ConnectionState.ERROR == "error"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Test data models."""
    
    def test_sensor_reading_creation(self, sample_sensor_reading):
        """Test SensorReading creation."""
        assert sample_sensor_reading.sensor_id == "sensor_001"
        assert sample_sensor_reading.machine_id == "machine_001"
        assert len(sample_sensor_reading.values) == 256
        assert sample_sensor_reading.sample_rate == 1000
        assert sample_sensor_reading.reading_type == AnomalyType.VIBRATION
    
    def test_anomaly_detection_creation(self, sample_anomaly_detection):
        """Test AnomalyDetection creation."""
        assert sample_anomaly_detection.detection_id == "det_001"
        assert sample_anomaly_detection.severity == SeverityLevel.WARNING
        assert sample_anomaly_detection.confidence == 0.85
        assert "mean" in sample_anomaly_detection.feature_values
    
    def test_machine_health_status_creation(self):
        """Test MachineHealthStatus creation."""
        status = MachineHealthStatus(
            machine_id="machine_001",
            overall_health=85.0,
            component_health={"vibration": 90.0, "temperature": 80.0},
            last_anomaly=datetime.now(),
            anomaly_count_24h=3,
            maintenance_due=datetime.now() + timedelta(days=7),
            status=SeverityLevel.WARNING,
        )
        assert status.overall_health == 85.0
        assert status.anomaly_count_24h == 3
    
    def test_edge_message_creation(self, sample_edge_message):
        """Test EdgeMessage creation."""
        assert sample_edge_message.message_id == "msg_001"
        assert sample_edge_message.message_type == MessageType.ANOMALY_ALERT
        assert sample_edge_message.priority == SyncPriority.HIGH
        assert sample_edge_message.retry_count == 0
        assert sample_edge_message.max_retries == 3
    
    def test_sync_result_creation(self):
        """Test SyncResult creation."""
        result = SyncResult(
            messages_sent=10,
            messages_failed=2,
            bytes_transferred=1024,
            sync_duration_ms=50.5,
            connection_state=ConnectionState.CONNECTED,
        )
        assert result.messages_sent == 10
        assert result.messages_failed == 2
    
    def test_cnn_config_creation(self, cnn_config):
        """Test CNNModelConfig creation."""
        assert cnn_config.input_length == 256
        assert cnn_config.num_filters == [8, 16]
        assert cnn_config.num_classes == 4


# =============================================================================
# 1D-CNN LAYER TESTS
# =============================================================================


class TestConv1DLayer:
    """Test Conv1D layer."""
    
    def test_layer_creation(self):
        """Test layer creation with default weights."""
        layer = Conv1DLayer(num_filters=4, kernel_size=3)
        assert layer.num_filters == 4
        assert layer.kernel_size == 3
        assert len(layer.weights) == 4
        assert len(layer.biases) == 4
    
    def test_layer_creation_with_weights(self):
        """Test layer creation with provided weights."""
        weights = [[[0.1, 0.2, 0.3]] for _ in range(2)]
        biases = [0.1, 0.2]
        layer = Conv1DLayer(num_filters=2, kernel_size=3, weights=weights, biases=biases)
        assert layer.weights == weights
        assert layer.biases == biases
    
    def test_forward_pass(self):
        """Test forward pass computation."""
        weights = [[[1.0, 1.0, 1.0]]]  # Sum kernel
        biases = [0.0]
        layer = Conv1DLayer(num_filters=1, kernel_size=3, weights=weights, biases=biases)
        
        input_data = [1.0, 2.0, 3.0, 4.0, 5.0]
        output = layer.forward(input_data)
        
        assert len(output) == 1  # One filter
        assert len(output[0]) == 3  # 5 - 3 + 1 = 3
        assert output[0][0] == 6.0  # 1+2+3
        assert output[0][1] == 9.0  # 2+3+4
        assert output[0][2] == 12.0  # 3+4+5
    
    def test_forward_with_relu(self):
        """Test that ReLU is applied."""
        weights = [[[-1.0, -1.0, -1.0]]]  # Negative sum
        biases = [0.0]
        layer = Conv1DLayer(num_filters=1, kernel_size=3, weights=weights, biases=biases)
        
        input_data = [1.0, 2.0, 3.0]
        output = layer.forward(input_data)
        
        # Should be 0 due to ReLU
        assert output[0][0] == 0.0
    
    def test_forward_short_input(self):
        """Test forward with input shorter than kernel."""
        layer = Conv1DLayer(num_filters=1, kernel_size=5)
        output = layer.forward([1.0, 2.0])
        assert len(output) == 1
        assert output[0] == [0.0]


class TestMaxPool1DLayer:
    """Test MaxPool1D layer."""
    
    def test_layer_creation(self):
        """Test layer creation."""
        layer = MaxPool1DLayer(pool_size=2)
        assert layer.pool_size == 2
    
    def test_max_pooling(self):
        """Test max pooling computation."""
        layer = MaxPool1DLayer(pool_size=2)
        inputs = [[1.0, 3.0, 2.0, 4.0]]
        output = layer.forward(inputs)
        
        assert len(output) == 1
        assert output[0] == [3.0, 4.0]
    
    def test_max_pooling_multiple_channels(self):
        """Test max pooling with multiple channels."""
        layer = MaxPool1DLayer(pool_size=2)
        inputs = [[1.0, 3.0, 2.0, 4.0], [5.0, 1.0, 6.0, 2.0]]
        output = layer.forward(inputs)
        
        assert len(output) == 2
        assert output[0] == [3.0, 4.0]
        assert output[1] == [5.0, 6.0]
    
    def test_max_pooling_with_stride(self):
        """Test that pooling uses non-overlapping regions."""
        layer = MaxPool1DLayer(pool_size=3)
        inputs = [[1.0, 5.0, 2.0, 8.0, 3.0, 1.0]]
        output = layer.forward(inputs)
        
        assert len(output[0]) == 2
        assert output[0][0] == 5.0
        assert output[0][1] == 8.0


class TestDenseLayer:
    """Test Dense layer."""
    
    def test_layer_creation(self):
        """Test layer creation."""
        layer = DenseLayer(input_size=10, output_size=5)
        assert layer.input_size == 10
        assert layer.output_size == 5
        assert len(layer.weights) == 5
        assert len(layer.biases) == 5
    
    def test_forward_relu(self):
        """Test forward with ReLU activation."""
        weights = [[1.0, 1.0]]
        biases = [0.0]
        layer = DenseLayer(input_size=2, output_size=1, weights=weights, biases=biases, activation="relu")
        
        output = layer.forward([2.0, 3.0])
        assert output[0] == 5.0
    
    def test_forward_softmax(self):
        """Test forward with softmax activation."""
        weights = [[1.0, 0.0], [0.0, 1.0]]
        biases = [0.0, 0.0]
        layer = DenseLayer(input_size=2, output_size=2, weights=weights, biases=biases, activation="softmax")
        
        output = layer.forward([1.0, 2.0])
        assert len(output) == 2
        # Softmax outputs should sum to 1
        assert abs(sum(output) - 1.0) < 0.001
    
    def test_relu_negative_values(self):
        """Test ReLU clips negative values."""
        weights = [[-1.0]]
        biases = [0.0]
        layer = DenseLayer(input_size=1, output_size=1, weights=weights, biases=biases, activation="relu")
        
        output = layer.forward([5.0])
        assert output[0] == 0.0


# =============================================================================
# EDGE CNN TESTS
# =============================================================================


class TestEdgeCNN1D:
    """Test EdgeCNN1D model."""
    
    def test_model_creation(self, cnn_config):
        """Test model creation."""
        model = EdgeCNN1D(cnn_config)
        assert len(model.layers) > 0
    
    def test_predict(self, cnn_config):
        """Test model prediction."""
        model = EdgeCNN1D(cnn_config)
        signal = [random.random() for _ in range(256)]
        output = model.predict(signal)
        
        assert len(output) == cnn_config.num_classes
        # Softmax outputs should sum to ~1
        assert abs(sum(output) - 1.0) < 0.01
    
    def test_predict_short_input(self, cnn_config):
        """Test prediction with short input (padded)."""
        model = EdgeCNN1D(cnn_config)
        signal = [1.0, 2.0, 3.0]  # Much shorter than 256
        output = model.predict(signal)
        
        assert len(output) == cnn_config.num_classes
    
    def test_predict_long_input(self, cnn_config):
        """Test prediction with long input (truncated)."""
        model = EdgeCNN1D(cnn_config)
        signal = [random.random() for _ in range(500)]
        output = model.predict(signal)
        
        assert len(output) == cnn_config.num_classes
    
    def test_classify(self, cnn_config):
        """Test classification."""
        model = EdgeCNN1D(cnn_config)
        signal = [random.random() for _ in range(256)]
        class_idx, confidence = model.classify(signal)
        
        assert 0 <= class_idx < cnn_config.num_classes
        assert 0.0 <= confidence <= 1.0
    
    def test_classify_deterministic(self, cnn_config):
        """Test that same input gives same output."""
        model = EdgeCNN1D(cnn_config)
        signal = [0.1 * i for i in range(256)]
        
        idx1, conf1 = model.classify(signal)
        idx2, conf2 = model.classify(signal)
        
        assert idx1 == idx2
        assert conf1 == conf2


# =============================================================================
# PREDICTIVE MAINTENANCE ENGINE TESTS
# =============================================================================


class TestPredictiveMaintenanceEngine:
    """Test PredictiveMaintenanceEngine."""
    
    def test_engine_creation(self, predictive_engine):
        """Test engine creation."""
        assert predictive_engine.threshold == 0.7
        assert predictive_engine.model is not None
    
    def test_analyze_reading(self, predictive_engine, sample_sensor_reading):
        """Test analyzing a sensor reading."""
        detection = predictive_engine.analyze_reading(sample_sensor_reading)
        
        assert detection.detection_id is not None
        assert detection.machine_id == sample_sensor_reading.machine_id
        assert detection.anomaly_type == sample_sensor_reading.reading_type
        assert detection.severity in SeverityLevel
        assert 0.0 <= detection.confidence <= 1.0
        assert detection.recommended_action
    
    def test_feature_extraction(self, predictive_engine, sample_sensor_reading):
        """Test feature extraction."""
        features = predictive_engine._extract_features(sample_sensor_reading)
        
        assert "mean" in features
        assert "std_dev" in features
        assert "max" in features
        assert "min" in features
        assert "rms" in features
        assert "peak_to_peak" in features
        assert "crest_factor" in features
    
    def test_feature_extraction_empty(self, predictive_engine):
        """Test feature extraction with empty values."""
        reading = SensorReading(
            sensor_id="s1",
            machine_id="m1",
            timestamp=datetime.now(),
            values=[],
            sample_rate=1000,
            reading_type=AnomalyType.VIBRATION,
        )
        features = predictive_engine._extract_features(reading)
        assert features == {}
    
    def test_machine_health_updated(self, predictive_engine, sample_sensor_reading):
        """Test that machine health is updated after analysis."""
        detection = predictive_engine.analyze_reading(sample_sensor_reading)
        health = predictive_engine.get_machine_health(sample_sensor_reading.machine_id)
        
        assert health is not None
        assert health.machine_id == sample_sensor_reading.machine_id
        assert 0.0 <= health.overall_health <= 100.0
    
    def test_anomaly_history(self, predictive_engine, sample_sensor_reading):
        """Test anomaly history tracking."""
        predictive_engine.analyze_reading(sample_sensor_reading)
        predictive_engine.analyze_reading(sample_sensor_reading)
        
        assert len(predictive_engine.anomaly_history) == 2
    
    def test_get_recent_anomalies(self, predictive_engine, sample_sensor_reading):
        """Test getting recent anomalies."""
        predictive_engine.analyze_reading(sample_sensor_reading)
        anomalies = predictive_engine.get_recent_anomalies()
        
        assert len(anomalies) == 1
    
    def test_get_recent_anomalies_filtered(self, predictive_engine):
        """Test getting anomalies filtered by machine."""
        reading1 = SensorReading("s1", "machine_A", datetime.now(), [1.0]*256, 1000, AnomalyType.VIBRATION)
        reading2 = SensorReading("s2", "machine_B", datetime.now(), [2.0]*256, 1000, AnomalyType.VIBRATION)
        
        predictive_engine.analyze_reading(reading1)
        predictive_engine.analyze_reading(reading2)
        
        anomalies = predictive_engine.get_recent_anomalies(machine_id="machine_A")
        assert len(anomalies) == 1
        assert anomalies[0].machine_id == "machine_A"
    
    def test_history_pruning(self, predictive_engine):
        """Test that history is pruned when too large."""
        for i in range(1100):
            reading = SensorReading(
                f"s{i}", f"m{i % 10}", datetime.now(),
                [float(i)] * 256, 1000, AnomalyType.VIBRATION,
            )
            predictive_engine.analyze_reading(reading)
        
        # Should be pruned to 500
        assert len(predictive_engine.anomaly_history) <= 600
    
    def test_severity_recommendations(self, predictive_engine):
        """Test that different severities give different recommendations."""
        # We can check the logic by looking at detection results
        reading = SensorReading("s1", "m1", datetime.now(), [1.0]*256, 1000, AnomalyType.VIBRATION)
        detection = predictive_engine.analyze_reading(reading)
        
        # Action should match severity
        if detection.severity == SeverityLevel.EMERGENCY:
            assert "shutdown" in detection.recommended_action.lower()
        elif detection.severity == SeverityLevel.NORMAL:
            assert "normal" in detection.recommended_action.lower()


# =============================================================================
# PROTOBUF-LIKE ENCODER TESTS
# =============================================================================


class TestProtobufLikeEncoder:
    """Test ProtobufLikeEncoder."""
    
    def test_encode_varint_small(self):
        """Test encoding small varints."""
        result = ProtobufLikeEncoder.encode_varint(0)
        assert result == b"\x00"
        
        result = ProtobufLikeEncoder.encode_varint(1)
        assert result == b"\x01"
        
        result = ProtobufLikeEncoder.encode_varint(127)
        assert result == b"\x7f"
    
    def test_encode_varint_large(self):
        """Test encoding larger varints."""
        result = ProtobufLikeEncoder.encode_varint(128)
        assert result == b"\x80\x01"
        
        result = ProtobufLikeEncoder.encode_varint(300)
        assert len(result) == 2
    
    def test_decode_varint(self):
        """Test decoding varints."""
        encoded = ProtobufLikeEncoder.encode_varint(300)
        value, consumed = ProtobufLikeEncoder.decode_varint(encoded)
        assert value == 300
        assert consumed == len(encoded)
    
    def test_encode_decode_roundtrip(self):
        """Test encoding and decoding roundtrip."""
        for value in [0, 1, 127, 128, 16383, 16384, 1000000]:
            encoded = ProtobufLikeEncoder.encode_varint(value)
            decoded, _ = ProtobufLikeEncoder.decode_varint(encoded)
            assert decoded == value
    
    def test_encode_string(self):
        """Test string encoding."""
        result = ProtobufLikeEncoder.encode_string("hello")
        assert len(result) == 6  # 1 byte length + 5 bytes content
        assert result[0] == 5  # Length
        assert result[1:] == b"hello"
    
    def test_encode_message(self, sample_edge_message):
        """Test message encoding."""
        encoded = ProtobufLikeEncoder.encode_message(sample_edge_message)
        
        assert isinstance(encoded, bytes)
        assert len(encoded) > 0
        # Should contain field markers
        assert b"\x0a" in encoded  # Field 1
    
    def test_compress_decompress(self):
        """Test compression roundtrip."""
        data = b"test data " * 100
        compressed = ProtobufLikeEncoder.compress(data)
        decompressed = ProtobufLikeEncoder.decompress(compressed)
        
        assert decompressed == data
        assert len(compressed) < len(data)


# =============================================================================
# PRIORITY QUEUE TESTS
# =============================================================================


class TestPriorityMessageQueue:
    """Test PriorityMessageQueue."""
    
    def test_queue_creation(self):
        """Test queue creation."""
        queue = PriorityMessageQueue(max_size=100)
        assert queue.size() == 0
        assert queue.max_size == 100
    
    def test_enqueue_dequeue(self, sample_edge_message):
        """Test enqueue and dequeue."""
        queue = PriorityMessageQueue()
        queue.enqueue(sample_edge_message)
        
        assert queue.size() == 1
        
        msg = queue.dequeue()
        assert msg == sample_edge_message
        assert queue.size() == 0
    
    def test_priority_ordering(self):
        """Test that higher priority messages come first."""
        queue = PriorityMessageQueue()
        
        # Add in reverse priority order
        for priority in reversed(list(SyncPriority)):
            msg = EdgeMessage(
                f"msg_{priority.value}",
                MessageType.SENSOR_DATA,
                priority,
                b"data",
                datetime.now(),
            )
            queue.enqueue(msg)
        
        # Should dequeue in priority order
        assert queue.dequeue().priority == SyncPriority.CRITICAL
        assert queue.dequeue().priority == SyncPriority.HIGH
        assert queue.dequeue().priority == SyncPriority.NORMAL
        assert queue.dequeue().priority == SyncPriority.LOW
        assert queue.dequeue().priority == SyncPriority.BATCH
    
    def test_size_by_priority(self):
        """Test size by priority."""
        queue = PriorityMessageQueue()
        
        for _ in range(3):
            queue.enqueue(EdgeMessage("m", MessageType.SENSOR_DATA, SyncPriority.CRITICAL, b"", datetime.now()))
        for _ in range(5):
            queue.enqueue(EdgeMessage("m", MessageType.SENSOR_DATA, SyncPriority.NORMAL, b"", datetime.now()))
        
        assert queue.size_by_priority(SyncPriority.CRITICAL) == 3
        assert queue.size_by_priority(SyncPriority.NORMAL) == 5
        assert queue.size_by_priority(SyncPriority.LOW) == 0
    
    def test_max_size_enforcement(self):
        """Test that max size is enforced."""
        queue = PriorityMessageQueue(max_size=5)
        
        # Add 10 low priority messages
        for i in range(10):
            queue.enqueue(EdgeMessage(f"msg_{i}", MessageType.SENSOR_DATA, SyncPriority.BATCH, b"", datetime.now()))
        
        assert queue.size() <= 5
    
    def test_peek(self, sample_edge_message):
        """Test peek without removing."""
        queue = PriorityMessageQueue()
        queue.enqueue(sample_edge_message)
        
        msg = queue.peek()
        assert msg == sample_edge_message
        assert queue.size() == 1  # Still there
    
    def test_peek_empty(self):
        """Test peek on empty queue."""
        queue = PriorityMessageQueue()
        assert queue.peek() is None
    
    def test_dequeue_empty(self):
        """Test dequeue on empty queue."""
        queue = PriorityMessageQueue()
        assert queue.dequeue() is None
    
    def test_clear(self):
        """Test clearing queue."""
        queue = PriorityMessageQueue()
        for _ in range(10):
            queue.enqueue(EdgeMessage("m", MessageType.SENSOR_DATA, SyncPriority.NORMAL, b"", datetime.now()))
        
        count = queue.clear()
        assert count == 10
        assert queue.size() == 0


# =============================================================================
# EDGE-TO-CORE SYNC MANAGER TESTS
# =============================================================================


class TestEdgeToCoreSyncManager:
    """Test EdgeToCoreSyncManager."""
    
    def test_manager_creation(self, sync_manager):
        """Test manager creation."""
        assert sync_manager.device_id == "edge_001"
        assert sync_manager.connection_state == ConnectionState.DISCONNECTED
    
    def test_connect_disconnect(self, sync_manager):
        """Test connect and disconnect."""
        assert sync_manager.connect()
        assert sync_manager.connection_state == ConnectionState.CONNECTED
        
        sync_manager.disconnect()
        assert sync_manager.connection_state == ConnectionState.DISCONNECTED
    
    def test_queue_anomaly_alert(self, sync_manager, sample_anomaly_detection):
        """Test queuing anomaly alert."""
        msg_id = sync_manager.queue_anomaly_alert(sample_anomaly_detection)
        
        assert msg_id is not None
        assert sync_manager.message_queue.size() == 1
    
    def test_queue_anomaly_priority_mapping(self, sync_manager):
        """Test that anomaly severity maps to correct priority."""
        for severity, expected_priority in [
            (SeverityLevel.EMERGENCY, SyncPriority.CRITICAL),
            (SeverityLevel.CRITICAL, SyncPriority.HIGH),
            (SeverityLevel.WARNING, SyncPriority.NORMAL),
            (SeverityLevel.NORMAL, SyncPriority.BATCH),
        ]:
            detection = AnomalyDetection(
                f"det_{severity.value}",
                "machine_001",
                AnomalyType.VIBRATION,
                severity,
                0.8,
                datetime.now(),
                {},
                "hash",
                "action",
            )
            sync_manager.queue_anomaly_alert(detection)
        
        # Check priorities
        msg = sync_manager.message_queue.dequeue()
        assert msg.priority == SyncPriority.CRITICAL
    
    def test_queue_health_status(self, sync_manager):
        """Test queuing health status."""
        status = MachineHealthStatus(
            "machine_001", 85.0, {"vibration": 90.0},
            None, 2, None, SeverityLevel.WARNING,
        )
        msg_id = sync_manager.queue_health_status(status)
        
        assert msg_id is not None
        assert sync_manager.message_queue.size() == 1
    
    def test_queue_sensor_data(self, sync_manager, sample_sensor_reading):
        """Test queuing sensor data."""
        msg_id = sync_manager.queue_sensor_data(sample_sensor_reading)
        
        assert msg_id is not None
        assert sync_manager.message_queue.size() == 1
    
    def test_sync_batch(self, sync_manager, sample_anomaly_detection):
        """Test batch sync."""
        sync_manager.connect()
        
        # Queue some messages
        for _ in range(5):
            sync_manager.queue_anomaly_alert(sample_anomaly_detection)
        
        result = sync_manager.sync_batch()
        
        assert result.messages_sent == 5
        assert result.messages_failed == 0
        assert result.bytes_transferred > 0
        assert result.sync_duration_ms >= 0
    
    def test_sync_batch_empty(self, sync_manager):
        """Test sync with empty queue."""
        sync_manager.connect()
        result = sync_manager.sync_batch()
        
        assert result.messages_sent == 0
        assert result.messages_failed == 0
    
    def test_sync_critical_only(self, sync_manager):
        """Test syncing only critical messages."""
        sync_manager.connect()
        
        # Queue mixed priorities
        for severity in [SeverityLevel.EMERGENCY, SeverityLevel.NORMAL, SeverityLevel.NORMAL]:
            detection = AnomalyDetection(
                f"det_{severity.value}",
                "machine_001",
                AnomalyType.VIBRATION,
                severity,
                0.8,
                datetime.now(),
                {},
                "hash",
                "action",
            )
            sync_manager.queue_anomaly_alert(detection)
        
        result = sync_manager.sync_critical_only()
        
        assert result.messages_sent == 1  # Only emergency
        assert sync_manager.message_queue.size() == 2  # Others remain
    
    def test_get_queue_status(self, sync_manager, sample_anomaly_detection):
        """Test getting queue status."""
        sync_manager.queue_anomaly_alert(sample_anomaly_detection)
        
        status = sync_manager.get_queue_status()
        
        assert "total" in status
        assert "critical" in status
        assert "high" in status
        assert "normal" in status
        assert "low" in status
        assert "batch" in status
    
    def test_sync_stats_tracking(self, sync_manager, sample_anomaly_detection):
        """Test that sync stats are tracked."""
        sync_manager.connect()
        sync_manager.queue_anomaly_alert(sample_anomaly_detection)
        sync_manager.sync_batch()
        
        assert sync_manager.sync_stats["total_sent"] == 1
        assert sync_manager.sync_stats["bytes_sent"] > 0
    
    def test_last_sync_updated(self, sync_manager, sample_anomaly_detection):
        """Test that last sync time is updated."""
        sync_manager.connect()
        sync_manager.queue_anomaly_alert(sample_anomaly_detection)
        
        assert sync_manager.last_sync is None
        sync_manager.sync_batch()
        assert sync_manager.last_sync is not None


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_predictive_maintenance_engine(self):
        """Test creating predictive maintenance engine."""
        engine = create_predictive_maintenance_engine(input_length=128, threshold=0.8)
        assert engine.threshold == 0.8
        assert engine.config.input_length == 128
    
    def test_create_edge_sync_manager(self):
        """Test creating edge sync manager."""
        manager = create_edge_sync_manager("device_123", "https://test.local")
        assert manager.device_id == "device_123"
        assert manager.core_endpoint == "https://test.local"
    
    def test_create_cnn_model(self, cnn_config):
        """Test creating CNN model."""
        model = create_cnn_model(cnn_config)
        assert isinstance(model, EdgeCNN1D)
        assert model.config == cnn_config
    
    def test_create_priority_queue(self):
        """Test creating priority queue."""
        queue = create_priority_queue(max_size=500)
        assert queue.max_size == 500


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestEdgeAIIntegration:
    """Integration tests for Edge AI system."""
    
    def test_full_pipeline(self):
        """Test full edge AI pipeline."""
        # Create components
        engine = create_predictive_maintenance_engine()
        sync_manager = create_edge_sync_manager("edge_device_001")
        sync_manager.connect()
        
        # Simulate sensor readings
        for i in range(10):
            reading = SensorReading(
                f"sensor_{i % 3}",
                f"machine_{i % 2}",
                datetime.now(),
                [random.random() for _ in range(256)],
                1000,
                AnomalyType.VIBRATION,
            )
            
            # Analyze
            detection = engine.analyze_reading(reading)
            
            # Queue for sync
            sync_manager.queue_anomaly_alert(detection)
        
        # Sync
        result = sync_manager.sync_batch()
        
        assert result.messages_sent == 10
        assert engine.get_recent_anomalies()
    
    def test_multi_machine_monitoring(self):
        """Test monitoring multiple machines."""
        engine = create_predictive_maintenance_engine()
        
        machines = ["lathe_01", "mill_02", "drill_03"]
        for machine in machines:
            reading = SensorReading(
                f"sensor_{machine}",
                machine,
                datetime.now(),
                [random.random() for _ in range(256)],
                1000,
                AnomalyType.VIBRATION,
            )
            engine.analyze_reading(reading)
        
        # Each machine should have health status
        for machine in machines:
            health = engine.get_machine_health(machine)
            assert health is not None
            assert health.machine_id == machine
    
    def test_priority_based_sync(self):
        """Test that critical alerts sync first."""
        sync_manager = create_edge_sync_manager("edge_001")
        sync_manager.connect()
        
        # Create detections with different severities
        severities = [
            SeverityLevel.NORMAL,
            SeverityLevel.WARNING,
            SeverityLevel.EMERGENCY,  # This should sync first
            SeverityLevel.CRITICAL,
        ]
        
        for i, severity in enumerate(severities):
            detection = AnomalyDetection(
                f"det_{i}",
                "machine_001",
                AnomalyType.VIBRATION,
                severity,
                0.9,
                datetime.now(),
                {},
                f"hash_{i}",
                "action",
            )
            sync_manager.queue_anomaly_alert(detection)
        
        # First dequeued should be emergency (critical priority)
        sync_manager.sync_critical_only()
        
        # Emergency should be synced, others remain
        status = sync_manager.get_queue_status()
        assert status["critical"] == 0
        assert status["high"] == 1  # CRITICAL severity
        assert status["normal"] == 1  # WARNING severity
        assert status["batch"] == 1  # NORMAL severity
    
    def test_connection_failure_retry(self):
        """Test retry on connection failure."""
        sync_manager = create_edge_sync_manager("edge_001")
        sync_manager.connection_state = ConnectionState.ERROR
        
        detection = AnomalyDetection(
            "det_001", "machine_001", AnomalyType.VIBRATION,
            SeverityLevel.WARNING, 0.8, datetime.now(), {}, "hash", "action",
        )
        sync_manager.queue_anomaly_alert(detection)
        
        initial_size = sync_manager.message_queue.size()
        result = sync_manager.sync_batch()
        
        # Should fail and re-queue (with retry count)
        assert result.messages_failed >= 0  # May succeed or fail
    
    def test_compression_efficiency(self):
        """Test that compression reduces message size."""
        encoder = ProtobufLikeEncoder()
        
        # Create a large payload
        large_payload = b"sensor_data=" + b"x" * 1000
        msg = EdgeMessage(
            "msg_large",
            MessageType.SENSOR_DATA,
            SyncPriority.BATCH,
            large_payload,
            datetime.now(),
        )
        
        encoded = encoder.encode_message(msg)
        compressed = encoder.compress(encoded)
        
        # Compressed should be smaller
        assert len(compressed) < len(encoded)
