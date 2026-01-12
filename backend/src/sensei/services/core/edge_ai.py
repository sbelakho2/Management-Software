"""
Edge AI & IoT Infrastructure.

Implements:
- Predictive Maintenance Edge (1D-CNN for machine health anomalies)
- Edge-to-Core Sync (protobuf-based sync with priority queuing)
"""

from __future__ import annotations

import struct
import hashlib
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from collections import deque
import math


# =============================================================================
# ENUMS
# =============================================================================


class AnomalyType(str, Enum):
    """Types of machine anomalies."""
    VIBRATION = "vibration"
    SOUND = "sound"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    CURRENT = "current"
    MIXED = "mixed"


class SeverityLevel(str, Enum):
    """Anomaly severity levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SyncPriority(str, Enum):
    """Sync priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BATCH = "batch"


class MessageType(str, Enum):
    """Edge message types."""
    ANOMALY_ALERT = "anomaly_alert"
    HEALTH_STATUS = "health_status"
    SENSOR_DATA = "sensor_data"
    CONFIG_UPDATE = "config_update"
    HEARTBEAT = "heartbeat"


class ConnectionState(str, Enum):
    """Connection state."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SensorReading:
    """A sensor reading from edge device."""
    sensor_id: str
    machine_id: str
    timestamp: datetime
    values: list[float]
    sample_rate: int  # Hz
    reading_type: AnomalyType


@dataclass
class AnomalyDetection:
    """An anomaly detection result."""
    detection_id: str
    machine_id: str
    anomaly_type: AnomalyType
    severity: SeverityLevel
    confidence: float
    detected_at: datetime
    feature_values: dict[str, float]
    raw_data_hash: str
    recommended_action: str


@dataclass
class MachineHealthStatus:
    """Machine health status."""
    machine_id: str
    overall_health: float  # 0-100
    component_health: dict[str, float]
    last_anomaly: datetime | None
    anomaly_count_24h: int
    maintenance_due: datetime | None
    status: SeverityLevel


@dataclass
class EdgeMessage:
    """A message for edge-to-core sync."""
    message_id: str
    message_type: MessageType
    priority: SyncPriority
    payload: bytes
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class SyncResult:
    """Result of sync operation."""
    messages_sent: int
    messages_failed: int
    bytes_transferred: int
    sync_duration_ms: float
    connection_state: ConnectionState


@dataclass
class CNNModelConfig:
    """Configuration for 1D-CNN model."""
    input_length: int
    num_filters: list[int]
    kernel_sizes: list[int]
    pool_sizes: list[int]
    dense_units: list[int]
    num_classes: int
    threshold: float


# =============================================================================
# 1D-CNN IMPLEMENTATION FOR EDGE INFERENCE
# =============================================================================


class Conv1DLayer:
    """
    1D Convolutional layer for edge inference.
    Implements a simple convolution without heavy frameworks.
    """
    
    def __init__(
        self,
        num_filters: int,
        kernel_size: int,
        weights: list[list[list[float]]] | None = None,
        biases: list[float] | None = None,
    ):
        self.num_filters = num_filters
        self.kernel_size = kernel_size
        
        # Initialize or use provided weights
        if weights is not None:
            self.weights = weights
        else:
            # Random initialization (in production, would load trained weights)
            self.weights = [
                [[0.1 * (i + j + k) for k in range(kernel_size)]
                 for j in range(1)]  # Single input channel
                for i in range(num_filters)
            ]
        
        self.biases = biases if biases else [0.0] * num_filters
    
    def forward(self, input_data: list[float]) -> list[list[float]]:
        """Apply 1D convolution."""
        input_len = len(input_data)
        output_len = input_len - self.kernel_size + 1
        
        if output_len <= 0:
            return [[0.0] for _ in range(self.num_filters)]
        
        outputs = []
        for f in range(self.num_filters):
            weights = self.weights[f][0]
            bias = self.biases[f]
            # Use dot product via zip/sum for better Python performance
            filter_output = [
                max(0.0, sum(weights[k] * input_data[i + k] for k in range(self.kernel_size)) + bias)
                for i in range(output_len)
            ]
            outputs.append(filter_output)
        
        return outputs


class MaxPool1DLayer:
    """
    Max pooling layer for 1D signals.
    """
    
    def __init__(self, pool_size: int = 2):
        self.pool_size = pool_size
    
    def forward(self, inputs: list[list[float]]) -> list[list[float]]:
        """Apply max pooling."""
        outputs = []
        for channel in inputs:
            if not channel:
                outputs.append([0.0])
                continue
            pooled = [
                max(channel[i:i + self.pool_size]) 
                for i in range(0, len(channel) - self.pool_size + 1, self.pool_size)
            ]
            outputs.append(pooled if pooled else [0.0])
        return outputs


class DenseLayer:
    """
    Dense (fully connected) layer.
    """
    
    def __init__(
        self,
        input_size: int,
        output_size: int,
        weights: list[list[float]] | None = None,
        biases: list[float] | None = None,
        activation: str = "relu",
    ):
        self.input_size = input_size
        self.output_size = output_size
        self.activation = activation
        
        if weights is not None:
            self.weights = weights
        else:
            # Simple initialization
            self.weights = [
                [0.01 * (i + j) for j in range(input_size)]
                for i in range(output_size)
            ]
        
        self.biases = biases if biases else [0.0] * output_size
    
    def forward(self, inputs: list[float]) -> list[float]:
        """Apply dense layer."""
        outputs = []
        input_len = len(inputs)
        for i in range(self.output_size):
            weights = self.weights[i]
            weighted_sum = sum(
                inputs[j] * weights[j] 
                for j in range(min(input_len, self.input_size))
            ) + self.biases[i]
            
            # Apply activation
            if self.activation == "relu":
                outputs.append(max(0.0, weighted_sum))
            elif self.activation == "softmax":
                outputs.append(weighted_sum)  # Will apply softmax later
            else:
                outputs.append(weighted_sum)
        
        # Apply softmax if needed
        if self.activation == "softmax" and outputs:
            max_val = max(outputs)
            exp_outputs = [math.exp(x - max_val) for x in outputs]
            sum_exp = sum(exp_outputs)
            outputs = [x / sum_exp if sum_exp > 0 else 0.0 for x in exp_outputs]
        
        return outputs


class EdgeCNN1D:
    """
    1D Convolutional Neural Network for edge inference.
    Optimized for embedded/edge deployment.
    """
    
    def __init__(self, config: CNNModelConfig):
        self.config = config
        self.layers: list[Any] = []
        self._build_model()
    
    def _build_model(self) -> None:
        """Build the CNN architecture."""
        # Convolutional layers
        for i, (num_filters, kernel_size) in enumerate(
            zip(self.config.num_filters, self.config.kernel_sizes)
        ):
            self.layers.append(Conv1DLayer(num_filters, kernel_size))
            if i < len(self.config.pool_sizes):
                self.layers.append(MaxPool1DLayer(self.config.pool_sizes[i]))
        
        # Flatten size estimation
        flatten_size = self._estimate_flatten_size()
        
        # Dense layers
        prev_size = flatten_size
        for i, units in enumerate(self.config.dense_units):
            activation = "relu" if i < len(self.config.dense_units) - 1 else "linear"
            self.layers.append(DenseLayer(prev_size, units, activation=activation))
            prev_size = units
        
        # Output layer
        self.layers.append(DenseLayer(
            prev_size,
            self.config.num_classes,
            activation="softmax",
        ))
    
    def _estimate_flatten_size(self) -> int:
        """Estimate flattened size after conv layers."""
        size = self.config.input_length
        for i, kernel_size in enumerate(self.config.kernel_sizes):
            size = size - kernel_size + 1
            if i < len(self.config.pool_sizes):
                size = size // self.config.pool_sizes[i]
        
        total_filters = self.config.num_filters[-1] if self.config.num_filters else 1
        return max(size * total_filters, 1)
    
    def predict(self, signal: list[float]) -> list[float]:
        """Run inference on a signal."""
        # Pad or truncate to expected input length
        if len(signal) < self.config.input_length:
            signal = signal + [0.0] * (self.config.input_length - len(signal))
        elif len(signal) > self.config.input_length:
            signal = signal[:self.config.input_length]
        
        x: Any = signal
        
        for layer in self.layers:
            if isinstance(layer, Conv1DLayer):
                x = layer.forward(x if isinstance(x, list) and not isinstance(x[0], list) else x[0] if isinstance(x, list) else x)
            elif isinstance(layer, MaxPool1DLayer):
                x = layer.forward(x)
            elif isinstance(layer, DenseLayer):
                # Flatten if needed
                if isinstance(x, list) and x and isinstance(x[0], list):
                    x = [val for channel in x for val in channel]
                x = layer.forward(x)
        
        return x if isinstance(x, list) else [x]
    
    def classify(self, signal: list[float]) -> tuple[int, float]:
        """Classify signal and return class index and confidence."""
        probs = self.predict(signal)
        if not probs:
            return 0, 0.0
        
        max_idx = 0
        max_prob = probs[0]
        for i, p in enumerate(probs):
            if p > max_prob:
                max_prob = p
                max_idx = i
        
        return max_idx, max_prob


class PredictiveMaintenanceEngine:
    """
    Predictive maintenance engine using 1D-CNN for anomaly detection.
    
    Uses ONNX Runtime for high-performance CPU inference when available,
    with automatic fallback to pure-Python implementation.
    """
    
    CLASS_LABELS = ["normal", "warning", "critical", "emergency"]
    
    def __init__(
        self,
        input_length: int = 256,
        threshold: float = 0.7,
        use_onnx: bool = True,
    ):
        self.threshold = threshold
        self.input_length = input_length
        self._use_onnx = use_onnx
        self._onnx_model = None
        
        # Build default CNN config
        self.config = CNNModelConfig(
            input_length=input_length,
            num_filters=[16, 32],
            kernel_sizes=[5, 3],
            pool_sizes=[2, 2],
            dense_units=[64, 32],
            num_classes=4,  # normal, warning, critical, emergency
            threshold=threshold,
        )
        
        # Always create pure-Python model as fallback (and for backwards compatibility)
        self.model = EdgeCNN1D(self.config)
        
        # Try ONNX for faster inference
        if use_onnx:
            self._init_onnx_model()
        
        self.anomaly_history: list[AnomalyDetection] = []
        self.machine_health: dict[str, MachineHealthStatus] = {}
    
    def _init_onnx_model(self) -> None:
        """Initialize ONNX model if available."""
        try:
            from sensei.services.core.onnx_edge_inference import (
                ONNXEdgeConfig,
                ONNXEdgeInference,
            )
            from pathlib import Path
            import os
            
            cache_dir = Path(os.getenv("SENSEI_ONNX_CACHE_DIR", ".cache/sensei/onnx"))
            config = ONNXEdgeConfig(
                model_name="edge_anomaly_detector",
                cache_dir=cache_dir,
                input_length=self.input_length,
                num_classes=4,
                quantize_int8=True,
                warmup_on_init=True,
            )
            
            self._onnx_model = ONNXEdgeInference(config)
            if self._onnx_model.is_ready():
                import logging
                logging.getLogger(__name__).info(
                    f"Using ONNX inference (onnx={self._onnx_model.is_using_onnx()})"
                )
            else:
                self._onnx_model = None
                
        except ImportError:
            self._onnx_model = None
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"ONNX init failed: {e}")
            self._onnx_model = None
    
    def _classify(self, signal: list[float]) -> tuple[int, float]:
        """Classify signal using ONNX or pure-Python model."""
        if self._onnx_model is not None:
            class_idx, confidence, _ = self._onnx_model.classify(signal)
            return class_idx, confidence
        elif self.model is not None:
            return self.model.classify(signal)
        else:
            # Fallback: return normal with low confidence
            return 0, 0.25
    
    def _extract_features(self, reading: SensorReading) -> dict[str, float]:
        """Extract features from sensor reading."""
        values = reading.values
        if not values:
            return {}
        
        # Statistical features
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        max_val = max(values)
        min_val = min(values)
        
        # RMS (Root Mean Square)
        rms = (sum(x ** 2 for x in values) / len(values)) ** 0.5
        
        # Peak-to-peak
        peak_to_peak = max_val - min_val
        
        # Crest factor
        crest_factor = max_val / rms if rms > 0 else 0
        
        return {
            "mean": mean_val,
            "std_dev": std_dev,
            "max": max_val,
            "min": min_val,
            "rms": rms,
            "peak_to_peak": peak_to_peak,
            "crest_factor": crest_factor,
        }
    
    def analyze_reading(self, reading: SensorReading) -> AnomalyDetection:
        """Analyze a sensor reading for anomalies."""
        # Extract features
        features = self._extract_features(reading)
        
        # Run CNN inference (uses ONNX or pure-Python)
        class_idx, confidence = self._classify(reading.values)
        
        # Map to severity
        severity = SeverityLevel(self.CLASS_LABELS[class_idx])
        
        # Generate detection ID
        detection_id = hashlib.md5(
            f"{reading.machine_id}:{reading.timestamp.isoformat()}".encode()
        ).hexdigest()[:12]
        
        # Determine recommended action
        if severity == SeverityLevel.EMERGENCY:
            action = "Immediate shutdown required. Dispatch maintenance team."
        elif severity == SeverityLevel.CRITICAL:
            action = "Schedule maintenance within 24 hours."
        elif severity == SeverityLevel.WARNING:
            action = "Monitor closely. Plan preventive maintenance."
        else:
            action = "Continue normal operation."
        
        # Create detection result
        detection = AnomalyDetection(
            detection_id=detection_id,
            machine_id=reading.machine_id,
            anomaly_type=reading.reading_type,
            severity=severity,
            confidence=confidence,
            detected_at=reading.timestamp,
            feature_values=features,
            raw_data_hash=hashlib.md5(str(reading.values).encode()).hexdigest()[:16],
            recommended_action=action,
        )
        
        # Update history
        self.anomaly_history.append(detection)
        if len(self.anomaly_history) > 1000:
            self.anomaly_history = self.anomaly_history[-500:]
        
        # Update machine health
        self._update_machine_health(detection)
        
        return detection
    
    def _update_machine_health(self, detection: AnomalyDetection) -> None:
        """Update machine health status."""
        machine_id = detection.machine_id
        
        # Count anomalies in last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        recent_anomalies = [
            a for a in self.anomaly_history
            if a.machine_id == machine_id and a.detected_at >= cutoff
            and a.severity != SeverityLevel.NORMAL
        ]
        
        # Calculate health score
        if detection.severity == SeverityLevel.EMERGENCY:
            health_score = 20.0
        elif detection.severity == SeverityLevel.CRITICAL:
            health_score = 50.0
        elif detection.severity == SeverityLevel.WARNING:
            health_score = 75.0
        else:
            health_score = 95.0
        
        # Adjust based on recent anomaly count
        health_score -= len(recent_anomalies) * 2
        health_score = max(0.0, min(100.0, health_score))
        
        self.machine_health[machine_id] = MachineHealthStatus(
            machine_id=machine_id,
            overall_health=health_score,
            component_health={detection.anomaly_type.value: health_score},
            last_anomaly=detection.detected_at if detection.severity != SeverityLevel.NORMAL else None,
            anomaly_count_24h=len(recent_anomalies),
            maintenance_due=datetime.now() + timedelta(days=7) if health_score < 70 else None,
            status=detection.severity,
        )
    
    def get_machine_health(self, machine_id: str) -> MachineHealthStatus | None:
        """Get health status for a machine."""
        return self.machine_health.get(machine_id)
    
    def get_recent_anomalies(
        self,
        machine_id: str | None = None,
        hours: int = 24,
    ) -> list[AnomalyDetection]:
        """Get recent anomalies."""
        cutoff = datetime.now() - timedelta(hours=hours)
        anomalies = [a for a in self.anomaly_history if a.detected_at >= cutoff]
        
        if machine_id:
            anomalies = [a for a in anomalies if a.machine_id == machine_id]
        
        return anomalies


# =============================================================================
# EDGE-TO-CORE SYNC
# =============================================================================


class ProtobufLikeEncoder:
    """
    Simple protobuf-like binary encoder for edge messages.
    """
    
    @staticmethod
    def encode_varint(value: int) -> bytes:
        """Encode an integer as a varint."""
        result = []
        while value > 0x7f:
            result.append((value & 0x7f) | 0x80)
            value >>= 7
        result.append(value)
        return bytes(result)
    
    @staticmethod
    def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
        """Decode a varint, return value and bytes consumed."""
        result = 0
        shift = 0
        consumed = 0
        for i in range(offset, len(data)):
            byte = data[i]
            result |= (byte & 0x7f) << shift
            consumed += 1
            if not (byte & 0x80):
                break
            shift += 7
        return result, consumed
    
    @staticmethod
    def encode_string(s: str) -> bytes:
        """Encode a string with length prefix."""
        encoded = s.encode("utf-8")
        return ProtobufLikeEncoder.encode_varint(len(encoded)) + encoded
    
    @staticmethod
    def encode_message(msg: EdgeMessage) -> bytes:
        """Encode an EdgeMessage to bytes."""
        parts = []
        
        # Field 1: message_id (string)
        parts.append(b"\x0a")  # field 1, wire type 2
        parts.append(ProtobufLikeEncoder.encode_string(msg.message_id))
        
        # Field 2: message_type (enum as int)
        parts.append(b"\x10")  # field 2, wire type 0
        type_map = {t: i for i, t in enumerate(MessageType)}
        parts.append(ProtobufLikeEncoder.encode_varint(type_map.get(msg.message_type, 0)))
        
        # Field 3: priority (enum as int)
        parts.append(b"\x18")  # field 3, wire type 0
        priority_map = {p: i for i, p in enumerate(SyncPriority)}
        parts.append(ProtobufLikeEncoder.encode_varint(priority_map.get(msg.priority, 2)))
        
        # Field 4: payload (bytes)
        parts.append(b"\x22")  # field 4, wire type 2
        parts.append(ProtobufLikeEncoder.encode_varint(len(msg.payload)))
        parts.append(msg.payload)
        
        # Field 5: timestamp (int64)
        parts.append(b"\x28")  # field 5, wire type 0
        timestamp_ms = int(msg.created_at.timestamp() * 1000)
        parts.append(ProtobufLikeEncoder.encode_varint(timestamp_ms))
        
        return b"".join(parts)
    
    @staticmethod
    def compress(data: bytes) -> bytes:
        """Compress data using zlib."""
        return zlib.compress(data, level=6)
    
    @staticmethod
    def decompress(data: bytes) -> bytes:
        """Decompress zlib data."""
        return zlib.decompress(data)


class PriorityMessageQueue:
    """
    Priority queue for edge messages with critical alert prioritization.
    """
    
    PRIORITY_VALUES = {
        SyncPriority.CRITICAL: 0,
        SyncPriority.HIGH: 1,
        SyncPriority.NORMAL: 2,
        SyncPriority.LOW: 3,
        SyncPriority.BATCH: 4,
    }
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queues: dict[SyncPriority, deque[EdgeMessage]] = {
            priority: deque() for priority in SyncPriority
        }
        self._total_count = 0
    
    def enqueue(self, message: EdgeMessage) -> bool:
        """Add message to queue."""
        if self._total_count >= self.max_size:
            # Drop lowest priority message
            for priority in reversed(SyncPriority):
                if self._queues[priority]:
                    self._queues[priority].popleft()
                    self._total_count -= 1
                    break
            else:
                return False
        
        self._queues[message.priority].append(message)
        self._total_count += 1
        return True
    
    def dequeue(self) -> EdgeMessage | None:
        """Get highest priority message."""
        for priority in SyncPriority:
            if self._queues[priority]:
                self._total_count -= 1
                return self._queues[priority].popleft()
        return None
    
    def peek(self) -> EdgeMessage | None:
        """Peek at highest priority message without removing."""
        for priority in SyncPriority:
            if self._queues[priority]:
                return self._queues[priority][0]
        return None
    
    def size(self) -> int:
        """Get total queue size."""
        return self._total_count
    
    def size_by_priority(self, priority: SyncPriority) -> int:
        """Get queue size for a specific priority."""
        return len(self._queues[priority])
    
    def clear(self) -> int:
        """Clear all messages, return count cleared."""
        count = self._total_count
        for queue in self._queues.values():
            queue.clear()
        self._total_count = 0
        return count


class EdgeToCoreSyncManager:
    """
    Manages edge-to-core synchronization.
    """
    
    def __init__(
        self,
        device_id: str,
        core_endpoint: str = "https://core.sensei.local",
        batch_size: int = 50,
        retry_delay_sec: float = 5.0,
    ):
        self.device_id = device_id
        self.core_endpoint = core_endpoint
        self.batch_size = batch_size
        self.retry_delay_sec = retry_delay_sec
        
        self.message_queue = PriorityMessageQueue()
        self.encoder = ProtobufLikeEncoder()
        self.connection_state = ConnectionState.DISCONNECTED
        self.last_sync: datetime | None = None
        self.sync_stats = {
            "total_sent": 0,
            "total_failed": 0,
            "bytes_sent": 0,
        }

    def connect(self) -> bool:
        """Establish a connection to core (simulated)."""
        self.connection_state = ConnectionState.CONNECTED
        return True

    def disconnect(self) -> None:
        """Disconnect from core."""
        self.connection_state = ConnectionState.DISCONNECTED
    
    def queue_anomaly_alert(self, detection: AnomalyDetection) -> str:
        """Queue an anomaly alert for sync."""
        # Determine priority based on severity
        if detection.severity == SeverityLevel.EMERGENCY:
            priority = SyncPriority.CRITICAL
        elif detection.severity == SeverityLevel.CRITICAL:
            priority = SyncPriority.HIGH
        elif detection.severity == SeverityLevel.WARNING:
            priority = SyncPriority.NORMAL
        else:
            priority = SyncPriority.BATCH
        
        # Create payload
        payload = {
            "detection_id": detection.detection_id,
            "machine_id": detection.machine_id,
            "anomaly_type": detection.anomaly_type.value,
            "severity": detection.severity.value,
            "confidence": detection.confidence,
            "features": detection.feature_values,
            "action": detection.recommended_action,
        }
        
        message = EdgeMessage(
            message_id=f"alert_{detection.detection_id}",
            message_type=MessageType.ANOMALY_ALERT,
            priority=priority,
            payload=str(payload).encode(),
            created_at=detection.detected_at,
        )
        
        self.message_queue.enqueue(message)
        return message.message_id
    
    def queue_health_status(self, status: MachineHealthStatus) -> str:
        """Queue health status for sync."""
        payload = {
            "machine_id": status.machine_id,
            "health": status.overall_health,
            "components": status.component_health,
            "anomaly_count": status.anomaly_count_24h,
            "status": status.status.value,
        }
        
        message = EdgeMessage(
            message_id=f"health_{status.machine_id}_{int(time.time())}",
            message_type=MessageType.HEALTH_STATUS,
            priority=SyncPriority.NORMAL,
            payload=str(payload).encode(),
            created_at=datetime.now(),
        )
        
        self.message_queue.enqueue(message)
        return message.message_id
    
    def queue_sensor_data(
        self,
        reading: SensorReading,
        priority: SyncPriority = SyncPriority.BATCH,
    ) -> str:
        """Queue sensor data for sync."""
        payload = {
            "sensor_id": reading.sensor_id,
            "machine_id": reading.machine_id,
            "sample_rate": reading.sample_rate,
            "type": reading.reading_type.value,
            "data_hash": hashlib.md5(str(reading.values).encode()).hexdigest()[:16],
        }
        
        message = EdgeMessage(
            message_id=f"sensor_{reading.sensor_id}_{int(time.time())}",
            message_type=MessageType.SENSOR_DATA,
            priority=priority,
            payload=str(payload).encode(),
            created_at=reading.timestamp,
        )
        
        self.message_queue.enqueue(message)
        return message.message_id
    
    def _simulate_send(self, encoded_data: bytes) -> bool:
        """Simulate sending data (in production, would use actual network)."""
        # Simulate network latency and potential failures
        if self.connection_state in (ConnectionState.ERROR, ConnectionState.DISCONNECTED):
            return False
        
        # Success
        return True
    
    def sync_batch(self) -> SyncResult:
        """Sync a batch of messages to core."""
        start_time = time.time()
        sent = 0
        failed = 0
        bytes_transferred = 0
        
        for _ in range(self.batch_size):
            message = self.message_queue.dequeue()
            if not message:
                break
            
            # Encode and compress
            encoded = self.encoder.encode_message(message)
            compressed = self.encoder.compress(encoded)
            
            # Attempt send
            if self._simulate_send(compressed):
                sent += 1
                bytes_transferred += len(compressed)
            else:
                failed += 1
                # Retry logic
                if message.retry_count < message.max_retries:
                    message.retry_count += 1
                    self.message_queue.enqueue(message)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Update stats
        self.sync_stats["total_sent"] += sent
        self.sync_stats["total_failed"] += failed
        self.sync_stats["bytes_sent"] += bytes_transferred
        self.last_sync = datetime.now()
        
        return SyncResult(
            messages_sent=sent,
            messages_failed=failed,
            bytes_transferred=bytes_transferred,
            sync_duration_ms=duration_ms,
            connection_state=self.connection_state,
        )
    
    def sync_critical_only(self) -> SyncResult:
        """Immediately sync only critical messages."""
        start_time = time.time()
        sent = 0
        failed = 0
        bytes_transferred = 0
        
        # Process only critical queue
        while self.message_queue.size_by_priority(SyncPriority.CRITICAL) > 0:
            message = self.message_queue.dequeue()
            if not message or message.priority != SyncPriority.CRITICAL:
                if message:
                    self.message_queue.enqueue(message)
                break
            
            encoded = self.encoder.encode_message(message)
            compressed = self.encoder.compress(encoded)
            
            if self._simulate_send(compressed):
                sent += 1
                bytes_transferred += len(compressed)
            else:
                failed += 1
        
        duration_ms = (time.time() - start_time) * 1000
        self.sync_stats["total_sent"] += sent
        self.sync_stats["total_failed"] += failed
        
        return SyncResult(
            messages_sent=sent,
            messages_failed=failed,
            bytes_transferred=bytes_transferred,
            sync_duration_ms=duration_ms,
            connection_state=self.connection_state,
        )

    def get_queue_status(self) -> dict[str, int]:
        """Get current queue status."""
        return {
            "total": self.message_queue.size(),
            "critical": self.message_queue.size_by_priority(SyncPriority.CRITICAL),
            "high": self.message_queue.size_by_priority(SyncPriority.HIGH),
            "normal": self.message_queue.size_by_priority(SyncPriority.NORMAL),
            "low": self.message_queue.size_by_priority(SyncPriority.LOW),
            "batch": self.message_queue.size_by_priority(SyncPriority.BATCH),
        }


# =============================================================================
# ORCHESTRATION LAYER (USED BY API)
# =============================================================================


class EdgeOrchestrator:
    """High-level orchestrator combining inference + edge-to-core sync.

    This is intentionally lightweight: it provides the stable surface that the
    API layer depends on, while delegating to the underlying engine/manager.
    """

    def __init__(
        self,
        machine_id: str,
        *,
        input_length: int = 256,
        threshold: float = 0.7,
        core_endpoint: str = "https://core.sensei.local",
    ):
        self.machine_id = machine_id
        self.engine = PredictiveMaintenanceEngine(input_length=input_length, threshold=threshold)
        self.sync_manager = EdgeToCoreSyncManager(device_id=machine_id, core_endpoint=core_endpoint)

    def run_inference(self, reading: SensorReading) -> AnomalyDetection | None:
        """Run inference and optionally queue messages for sync."""
        detection = self.engine.analyze_reading(reading)

        # Always queue raw sensor metadata as batch.
        self.sync_manager.queue_sensor_data(reading, priority=SyncPriority.BATCH)

        # Queue anomaly alerts for anything non-normal.
        if detection.severity != SeverityLevel.NORMAL:
            self.sync_manager.queue_anomaly_alert(detection)

        # Keep core up-to-date with health status when available.
        health = self.engine.get_machine_health(reading.machine_id)
        if health:
            self.sync_manager.queue_health_status(health)

        # Respect the model threshold: callers treat None as "no detection".
        if detection.confidence < self.engine.threshold:
            return None

        return detection

    def get_machine_health(self, machine_id: str) -> MachineHealthStatus | None:
        return self.engine.get_machine_health(machine_id)

    def get_recent_anomalies(
        self, *, machine_id: str | None = None, hours: int = 24
    ) -> list[AnomalyDetection]:
        return self.engine.get_recent_anomalies(machine_id=machine_id, hours=hours)

    def sync_batch(self) -> SyncResult:
        return self.sync_manager.sync_batch()
    
    def connect(self) -> bool:
        """Establish connection to core."""
        return self.sync_manager.connect()
    
    def disconnect(self) -> None:
        """Disconnect from core."""
        self.sync_manager.disconnect()
    
    def get_queue_status(self) -> dict[str, int]:
        """Get current queue status."""
        return self.sync_manager.get_queue_status()


# =============================================================================
# SINGLETON & FACTORY FUNCTIONS
# =============================================================================


_edge_orchestrator: EdgeOrchestrator | None = None


def get_edge_orchestrator(machine_id: str = "default_machine") -> EdgeOrchestrator:
    """Get the Edge Orchestrator singleton."""
    global _edge_orchestrator
    if _edge_orchestrator is None:
        _edge_orchestrator = EdgeOrchestrator(machine_id=machine_id)
    return _edge_orchestrator


def create_predictive_maintenance_engine(
    input_length: int = 256,
    threshold: float = 0.7,
) -> PredictiveMaintenanceEngine:
    """Create a predictive maintenance engine."""
    return PredictiveMaintenanceEngine(
        input_length=input_length,
        threshold=threshold,
    )


def create_edge_sync_manager(
    device_id: str,
    core_endpoint: str = "https://core.sensei.local",
) -> EdgeToCoreSyncManager:
    """Create an edge-to-core sync manager."""
    return EdgeToCoreSyncManager(
        device_id=device_id,
        core_endpoint=core_endpoint,
    )


def create_cnn_model(config: CNNModelConfig) -> EdgeCNN1D:
    """Create a 1D CNN model."""
    return EdgeCNN1D(config)


def create_priority_queue(max_size: int = 1000) -> PriorityMessageQueue:
    """Create a priority message queue."""
    return PriorityMessageQueue(max_size=max_size)
