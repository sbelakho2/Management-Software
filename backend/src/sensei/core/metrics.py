"""
Prometheus Metrics and SLO Monitoring

Provides:
- Prometheus-compatible metrics endpoint
- Request latency histograms
- Error rate counters
- SLO tracking and alerting
- Custom business metrics

SLOs Tracked:
- P99 latency < 500ms
- Error rate < 1%
- Availability > 99.9%
"""

import time
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import wraps
from threading import Lock
from typing import Callable, Dict, List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse

from sensei.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Metrics Storage
# =============================================================================


@dataclass
class HistogramBucket:
    """A histogram bucket with count and upper bound."""
    upper_bound: float
    count: int = 0


@dataclass  
class MetricValue:
    """A single metric value with labels."""
    name: str
    labels: Dict[str, str]
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsRegistry:
    """
    Thread-safe metrics registry for Prometheus-style metrics.
    
    Supports:
    - Counters (monotonically increasing)
    - Gauges (can go up and down)
    - Histograms (distribution of values)
    """
    
    def __init__(self):
        self._lock = Lock()
        self._counters: Dict[str, Dict[Tuple, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: Dict[str, Dict[Tuple, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: Dict[str, Dict[Tuple, List[float]]] = defaultdict(lambda: defaultdict(list))
        self._histogram_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        
        # Metric metadata
        self._metric_help: Dict[str, str] = {}
        self._metric_type: Dict[str, str] = {}
    
    def _labels_to_key(self, labels: Dict[str, str]) -> Tuple:
        """Convert labels dict to hashable tuple."""
        return tuple(sorted(labels.items()))
    
    def register_metric(self, name: str, metric_type: str, help_text: str):
        """Register metric metadata."""
        self._metric_help[name] = help_text
        self._metric_type[name] = metric_type
    
    def inc_counter(self, name: str, labels: Dict[str, str] = None, value: float = 1.0):
        """Increment a counter metric."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        with self._lock:
            self._counters[name][key] += value
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        with self._lock:
            self._gauges[name][key] = value
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram observation."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        with self._lock:
            self._histograms[name][key].append(value)
            # Keep only last 10k observations per label combo to prevent memory growth
            # At ~8 bytes per float, 10k entries ≈ 80KB per (metric, label) pair
            if len(self._histograms[name][key]) > 10000:
                self._histograms[name][key] = self._histograms[name][key][-5000:]
    
    def get_prometheus_output(self) -> str:
        """Generate Prometheus-compatible text output."""
        lines = []
        
        with self._lock:
            # Counters
            for name, values in self._counters.items():
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                lines.append(f"# TYPE {name} counter")
                for labels_tuple, value in values.items():
                    labels_str = self._format_labels(labels_tuple)
                    lines.append(f"{name}{labels_str} {value}")
            
            # Gauges
            for name, values in self._gauges.items():
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                lines.append(f"# TYPE {name} gauge")
                for labels_tuple, value in values.items():
                    labels_str = self._format_labels(labels_tuple)
                    lines.append(f"{name}{labels_str} {value}")
            
            # Histograms
            for name, values in self._histograms.items():
                if name in self._metric_help:
                    lines.append(f"# HELP {name} {self._metric_help[name]}")
                lines.append(f"# TYPE {name} histogram")
                
                for labels_tuple, observations in values.items():
                    if not observations:
                        continue
                    
                    # Calculate bucket counts
                    sorted_obs = sorted(observations)
                    total_count = len(sorted_obs)
                    total_sum = sum(sorted_obs)
                    
                    for bucket in self._histogram_buckets:
                        count = sum(1 for o in sorted_obs if o <= bucket)
                        bucket_labels = dict(labels_tuple)
                        bucket_labels["le"] = str(bucket)
                        labels_str = self._format_labels(self._labels_to_key(bucket_labels))
                        lines.append(f"{name}_bucket{labels_str} {count}")
                    
                    # +Inf bucket
                    inf_labels = dict(labels_tuple)
                    inf_labels["le"] = "+Inf"
                    labels_str = self._format_labels(self._labels_to_key(inf_labels))
                    lines.append(f"{name}_bucket{labels_str} {total_count}")
                    
                    # Sum and count
                    labels_str = self._format_labels(labels_tuple)
                    lines.append(f"{name}_sum{labels_str} {total_sum}")
                    lines.append(f"{name}_count{labels_str} {total_count}")
        
        return "\n".join(lines)
    
    def _format_labels(self, labels_tuple: Tuple) -> str:
        """Format labels tuple as Prometheus label string."""
        if not labels_tuple:
            return ""
        labels_dict = dict(labels_tuple)
        parts = [f'{k}="{v}"' for k, v in labels_dict.items()]
        return "{" + ",".join(parts) + "}"
    
    def get_percentile(self, name: str, percentile: float, labels: Dict[str, str] = None) -> Optional[float]:
        """Get percentile value from histogram."""
        labels = labels or {}
        key = self._labels_to_key(labels)
        
        with self._lock:
            if name not in self._histograms or key not in self._histograms[name]:
                return None
            
            observations = self._histograms[name][key]
            if not observations:
                return None
            
            sorted_obs = sorted(observations)
            index = int(len(sorted_obs) * percentile / 100)
            return sorted_obs[min(index, len(sorted_obs) - 1)]


# Global metrics registry
metrics_registry = MetricsRegistry()

# Register default metrics
metrics_registry.register_metric(
    "http_requests_total",
    "counter",
    "Total HTTP requests"
)
metrics_registry.register_metric(
    "http_request_duration_seconds",
    "histogram",
    "HTTP request latency in seconds"
)
metrics_registry.register_metric(
    "http_request_errors_total",
    "counter",
    "Total HTTP request errors"
)
metrics_registry.register_metric(
    "active_requests",
    "gauge",
    "Number of active requests"
)


# =============================================================================
# SLO Tracking
# =============================================================================


@dataclass
class SLOStatus:
    """Current SLO compliance status."""
    name: str
    target: float
    current: float
    is_meeting: bool
    error_budget_remaining: float
    window_start: datetime
    window_end: datetime


class SLOTracker:
    """
    Tracks Service Level Objectives (SLOs).
    
    Default SLOs:
    - Latency P99 < 500ms
    - Error rate < 1%
    - Availability > 99.9%
    """
    
    def __init__(
        self,
        latency_p99_ms: float = None,
        error_rate_pct: float = None,
        availability_pct: float = None,
    ):
        self.latency_p99_target_ms = latency_p99_ms or settings.SLO_LATENCY_P99_MS
        self.error_rate_target_pct = error_rate_pct or settings.SLO_ERROR_RATE_PCT
        self.availability_target_pct = availability_pct or settings.SLO_AVAILABILITY_PCT
        
        self._window_duration = timedelta(hours=24)  # 24-hour rolling window
        self._lock = Lock()
        # Use deque with maxlen for automatic O(1) bounded append.
        # Under extreme load this caps memory at ~50 bytes * 100k ≈ 5MB.
        self._max_request_entries = 100000
        self._requests: deque[Tuple[datetime, float, bool]] = deque(
            maxlen=self._max_request_entries
        )
    
    def record_request(self, latency_ms: float, is_error: bool):
        """Record a request for SLO tracking."""
        now = datetime.now(timezone.utc)
        with self._lock:
            # deque(maxlen=N) automatically evicts the oldest entry when full
            self._requests.append((now, latency_ms, is_error))
    
    def _cleanup_old_requests(self, now: datetime):
        """Remove requests outside the rolling window."""
        cutoff = now - self._window_duration
        # popleft is O(1) per entry on deque vs O(n) list rebuild
        while self._requests and self._requests[0][0] <= cutoff:
            self._requests.popleft()
    
    def get_slo_status(self) -> Dict[str, SLOStatus]:
        """Get current SLO compliance status."""
        now = datetime.now(timezone.utc)
        window_start = now - self._window_duration
        
        with self._lock:
            self._cleanup_old_requests(now)
            
            if not self._requests:
                return {}
            
            total = len(self._requests)
            latencies = [r[1] for r in self._requests]
            errors = sum(1 for r in self._requests if r[2])
            
            # Calculate P99 latency
            sorted_latencies = sorted(latencies)
            p99_index = int(len(sorted_latencies) * 0.99)
            p99_latency = sorted_latencies[min(p99_index, len(sorted_latencies) - 1)]
            
            # Calculate error rate
            error_rate = (errors / total) * 100 if total > 0 else 0
            
            # Calculate availability (inverse of error rate)
            availability = 100 - error_rate
            
            return {
                "latency_p99": SLOStatus(
                    name="Latency P99",
                    target=self.latency_p99_target_ms,
                    current=p99_latency,
                    is_meeting=p99_latency <= self.latency_p99_target_ms,
                    error_budget_remaining=max(0, self.latency_p99_target_ms - p99_latency),
                    window_start=window_start,
                    window_end=now,
                ),
                "error_rate": SLOStatus(
                    name="Error Rate",
                    target=self.error_rate_target_pct,
                    current=error_rate,
                    is_meeting=error_rate <= self.error_rate_target_pct,
                    error_budget_remaining=max(0, self.error_rate_target_pct - error_rate),
                    window_start=window_start,
                    window_end=now,
                ),
                "availability": SLOStatus(
                    name="Availability",
                    target=self.availability_target_pct,
                    current=availability,
                    is_meeting=availability >= self.availability_target_pct,
                    error_budget_remaining=max(0, availability - self.availability_target_pct),
                    window_start=window_start,
                    window_end=now,
                ),
            }


# Global SLO tracker
slo_tracker = SLOTracker()


# =============================================================================
# Metrics Middleware
# =============================================================================


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that collects request metrics for Prometheus.
    
    Tracks:
    - Request count by method, path, status
    - Request latency histogram
    - Error counts
    - Active request gauge
    """
    
    def __init__(self, app, path_normalizer: Optional[Callable[[str], str]] = None):
        super().__init__(app)
        self.path_normalizer = path_normalizer or self._default_normalize_path
        self._active_requests = 0
        self._lock = Lock()
    
    @staticmethod
    def _default_normalize_path(path: str) -> str:
        """
        Normalize path for metrics to avoid cardinality explosion.
        
        Replaces UUIDs and numeric IDs with placeholders.
        """
        import re
        
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{uuid}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        return path
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == settings.METRICS_PATH:
            return await call_next(request)
        
        # Track active requests
        with self._lock:
            self._active_requests += 1
            metrics_registry.set_gauge(
                "active_requests",
                self._active_requests
            )
        
        start_time = time.perf_counter()
        status_code = 500
        is_error = True
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            is_error = status_code >= 400
            return response
        except Exception:
            raise
        finally:
            # Calculate latency
            latency = time.perf_counter() - start_time
            latency_ms = latency * 1000
            
            # Normalize path for metrics
            normalized_path = self.path_normalizer(request.url.path)
            
            # Record metrics
            labels = {
                "method": request.method,
                "path": normalized_path,
                "status": str(status_code),
            }
            
            metrics_registry.inc_counter("http_requests_total", labels)
            metrics_registry.observe_histogram(
                "http_request_duration_seconds",
                latency,
                {"method": request.method, "path": normalized_path}
            )
            
            if is_error:
                metrics_registry.inc_counter(
                    "http_request_errors_total",
                    {"method": request.method, "path": normalized_path, "status": str(status_code)}
                )
            
            # Record for SLO tracking
            slo_tracker.record_request(latency_ms, is_error)
            
            # Update active requests
            with self._lock:
                self._active_requests -= 1
                metrics_registry.set_gauge(
                    "active_requests",
                    self._active_requests
                )


# =============================================================================
# Metrics Endpoint
# =============================================================================


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    if not settings.METRICS_ENABLED:
        return PlainTextResponse(
            "Metrics disabled",
            status_code=404
        )
    
    # Generate Prometheus output
    output = metrics_registry.get_prometheus_output()
    
    # Add SLO metrics
    slo_status = slo_tracker.get_slo_status()
    slo_lines = []
    
    for key, status in slo_status.items():
        metric_name = f"slo_{key}"
        slo_lines.append(f"# HELP {metric_name}_target SLO target for {status.name}")
        slo_lines.append(f"# TYPE {metric_name}_target gauge")
        slo_lines.append(f'{metric_name}_target {status.target}')
        
        slo_lines.append(f"# HELP {metric_name}_current Current value for {status.name}")
        slo_lines.append(f"# TYPE {metric_name}_current gauge")
        slo_lines.append(f'{metric_name}_current {status.current}')
        
        slo_lines.append(f"# HELP {metric_name}_meeting Whether SLO is being met")
        slo_lines.append(f"# TYPE {metric_name}_meeting gauge")
        slo_lines.append(f'{metric_name}_meeting {1 if status.is_meeting else 0}')
    
    full_output = output + "\n" + "\n".join(slo_lines)
    
    return PlainTextResponse(
        full_output,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


def get_slo_summary() -> Dict:
    """Get a summary of current SLO status for dashboards."""
    status = slo_tracker.get_slo_status()
    
    return {
        "slos": {
            key: {
                "name": s.name,
                "target": s.target,
                "current": round(s.current, 2),
                "is_meeting": s.is_meeting,
                "error_budget_remaining": round(s.error_budget_remaining, 2),
            }
            for key, s in status.items()
        },
        "overall_healthy": all(s.is_meeting for s in status.values()) if status else True,
    }
