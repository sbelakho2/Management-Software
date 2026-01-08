"""
Health Checks and Auto-scaling Service

Provides comprehensive health monitoring, readiness checks, and metrics
for Kubernetes auto-scaling (HPA) integration. Ensures system uptime
and enables automatic scaling based on resource utilization.

Features:
- Liveness probes (is the service running?)
- Readiness probes (is the service ready to accept traffic?)
- Startup probes (has the service finished initialization?)
- Dependency health checks (database, Redis, S3)
- Resource utilization metrics for HPA
- Health check endpoint aggregation
- Auto-scaling recommendations
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil
from sqlalchemy import text
from sqlalchemy.orm import Session


class HealthStatus(str, Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DependencyType(str, Enum):
    """Type of external dependency"""
    DATABASE = "database"
    CACHE = "cache"
    STORAGE = "storage"
    QUEUE = "queue"
    EXTERNAL_API = "external_api"


@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyHealth:
    """Health status of an external dependency"""
    name: str
    dependency_type: DependencyType
    status: HealthStatus
    latency_ms: float
    last_check: datetime
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceMetrics:
    """Current resource utilization metrics"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_available_gb: float
    network_connections: int
    timestamp: datetime


@dataclass
class ScalingRecommendation:
    """Auto-scaling recommendation based on metrics"""
    action: str  # "scale_up", "scale_down", "maintain"
    reason: str
    current_replicas: int
    recommended_replicas: int
    confidence: float
    metrics_snapshot: ResourceMetrics


class HealthCheckService:
    """Service for comprehensive health monitoring and auto-scaling support"""
    
    def __init__(
        self,
        db_session_factory: Optional[Callable[[], Session]] = None,
        redis_client: Optional[Any] = None,
        s3_client: Optional[Any] = None
    ):
        self.db_session_factory = db_session_factory
        self.redis_client = redis_client
        self.s3_client = s3_client
        
        # Health check configuration
        self.startup_complete = False
        self.startup_time = datetime.utcnow()
        self.max_startup_duration_seconds = 60
        
        # Dependency health tracking
        self.dependency_health: Dict[str, DependencyHealth] = {}
        self.health_check_interval_seconds = 30
        self.last_full_check: Optional[datetime] = None
        
        # Auto-scaling thresholds
        self.cpu_scale_up_threshold = 70.0
        self.cpu_scale_down_threshold = 30.0
        self.memory_scale_up_threshold = 80.0
        self.memory_scale_down_threshold = 40.0
        self.min_replicas = 2
        self.max_replicas = 10
        self.current_replicas = 2
    
    def mark_startup_complete(self):
        """Mark service startup as complete"""
        self.startup_complete = True
    
    def is_alive(self) -> bool:
        """
        Liveness probe - is the service running?
        Returns False if the service is in an unrecoverable state.
        """
        # Check if process is responsive
        try:
            # Simple liveness check - can we allocate memory and do basic operations?
            test_list = list(range(1000))
            assert len(test_list) == 1000
            return True
        except Exception:
            return False
    
    def is_ready(self) -> bool:
        """
        Readiness probe - is the service ready to accept traffic?
        Returns False if dependencies are unavailable.
        """
        if not self.startup_complete:
            return False
        
        # Check critical dependencies
        critical_deps = [
            dep for dep in self.dependency_health.values()
            if dep.dependency_type in [DependencyType.DATABASE, DependencyType.CACHE]
        ]
        
        for dep in critical_deps:
            if dep.status == HealthStatus.UNHEALTHY:
                return False
        
        return True
    
    def is_started(self) -> bool:
        """
        Startup probe - has the service finished initialization?
        Returns False if still starting up.
        """
        if self.startup_complete:
            return True
        
        # Check if we've exceeded max startup time
        elapsed = (datetime.utcnow() - self.startup_time).total_seconds()
        if elapsed > self.max_startup_duration_seconds:
            # Force complete if taking too long
            self.startup_complete = True
            return True
        
        return False
    
    def check_database_health(self) -> DependencyHealth:
        """Check database connectivity and performance"""
        start_time = time.time()
        status = HealthStatus.UNKNOWN
        error_msg = None
        metadata = {}
        
        try:
            if self.db_session_factory is None:
                raise Exception("Database session factory not configured")
            
            session = self.db_session_factory()
            try:
                # Simple query to check connectivity
                result = session.execute(text("SELECT 1")).scalar()
                
                if result == 1:
                    status = HealthStatus.HEALTHY
                    
                    # Get additional metrics
                    try:
                        # Check connection count
                        conn_result = session.execute(
                            text("SELECT count(*) FROM pg_stat_activity")
                        ).scalar()
                        metadata["active_connections"] = conn_result
                    except Exception:
                        pass
                else:
                    status = HealthStatus.UNHEALTHY
                    error_msg = "Database query returned unexpected result"
            finally:
                session.close()
        
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            error_msg = str(e)
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Determine degraded state based on latency
        if status == HealthStatus.HEALTHY and latency_ms > 100:
            status = HealthStatus.DEGRADED
        
        health = DependencyHealth(
            name="PostgreSQL Database",
            dependency_type=DependencyType.DATABASE,
            status=status,
            latency_ms=latency_ms,
            last_check=datetime.utcnow(),
            error_message=error_msg,
            metadata=metadata
        )
        
        self.dependency_health["database"] = health
        return health
    
    def check_redis_health(self) -> DependencyHealth:
        """Check Redis connectivity and performance"""
        start_time = time.time()
        status = HealthStatus.UNKNOWN
        error_msg = None
        metadata = {}
        
        try:
            if self.redis_client is None:
                raise Exception("Redis client not configured")
            
            # Ping Redis
            result = self.redis_client.ping()
            
            if result:
                status = HealthStatus.HEALTHY
                
                # Get Redis info
                try:
                    info = self.redis_client.info()
                    metadata["connected_clients"] = info.get("connected_clients", 0)
                    metadata["used_memory_mb"] = info.get("used_memory", 0) / 1024 / 1024
                except Exception:
                    pass
            else:
                status = HealthStatus.UNHEALTHY
                error_msg = "Redis ping failed"
        
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            error_msg = str(e)
        
        latency_ms = (time.time() - start_time) * 1000
        
        if status == HealthStatus.HEALTHY and latency_ms > 50:
            status = HealthStatus.DEGRADED
        
        health = DependencyHealth(
            name="Redis Cache",
            dependency_type=DependencyType.CACHE,
            status=status,
            latency_ms=latency_ms,
            last_check=datetime.utcnow(),
            error_message=error_msg,
            metadata=metadata
        )
        
        self.dependency_health["redis"] = health
        return health
    
    def check_s3_health(self) -> DependencyHealth:
        """Check S3 storage connectivity"""
        start_time = time.time()
        status = HealthStatus.UNKNOWN
        error_msg = None
        metadata = {}
        
        try:
            if self.s3_client is None:
                raise Exception("S3 client not configured")
            
            # List buckets as a health check
            buckets = self.s3_client.list_buckets()
            
            if buckets:
                status = HealthStatus.HEALTHY
                metadata["bucket_count"] = len(buckets.get("Buckets", []))
            else:
                status = HealthStatus.DEGRADED
                error_msg = "S3 accessible but no buckets found"
        
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            error_msg = str(e)
        
        latency_ms = (time.time() - start_time) * 1000
        
        if status == HealthStatus.HEALTHY and latency_ms > 200:
            status = HealthStatus.DEGRADED
        
        health = DependencyHealth(
            name="S3 Storage",
            dependency_type=DependencyType.STORAGE,
            status=status,
            latency_ms=latency_ms,
            last_check=datetime.utcnow(),
            error_message=error_msg,
            metadata=metadata
        )
        
        self.dependency_health["s3"] = health
        return health
    
    def check_all_dependencies(self) -> List[DependencyHealth]:
        """Check health of all configured dependencies"""
        results = []
        
        if self.db_session_factory:
            results.append(self.check_database_health())
        
        if self.redis_client:
            results.append(self.check_redis_health())
        
        if self.s3_client:
            results.append(self.check_s3_health())
        
        self.last_full_check = datetime.utcnow()
        return results
    
    def get_resource_metrics(self) -> ResourceMetrics:
        """Get current resource utilization metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / 1024 / 1024
        memory_available_mb = memory.available / 1024 / 1024
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / 1024 / 1024 / 1024
        disk_available_gb = disk.free / 1024 / 1024 / 1024
        
        # Network connections
        network_connections = len(psutil.net_connections())
        
        return ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            disk_percent=disk_percent,
            disk_used_gb=disk_used_gb,
            disk_available_gb=disk_available_gb,
            network_connections=network_connections,
            timestamp=datetime.utcnow()
        )
    
    def get_scaling_recommendation(
        self,
        metrics: Optional[ResourceMetrics] = None
    ) -> ScalingRecommendation:
        """
        Generate auto-scaling recommendation based on current metrics
        Used by Kubernetes HPA for intelligent scaling decisions
        """
        if metrics is None:
            metrics = self.get_resource_metrics()
        
        action = "maintain"
        reason = "Resource utilization within normal range"
        recommended_replicas = self.current_replicas
        confidence = 1.0
        
        # Check CPU threshold
        if metrics.cpu_percent > self.cpu_scale_up_threshold:
            action = "scale_up"
            reason = f"CPU utilization ({metrics.cpu_percent:.1f}%) above threshold ({self.cpu_scale_up_threshold}%)"
            recommended_replicas = min(self.current_replicas + 1, self.max_replicas)
            confidence = min((metrics.cpu_percent - self.cpu_scale_up_threshold) / 30.0, 1.0)
        
        elif metrics.cpu_percent < self.cpu_scale_down_threshold:
            action = "scale_down"
            reason = f"CPU utilization ({metrics.cpu_percent:.1f}%) below threshold ({self.cpu_scale_down_threshold}%)"
            recommended_replicas = max(self.current_replicas - 1, self.min_replicas)
            confidence = min((self.cpu_scale_down_threshold - metrics.cpu_percent) / 20.0, 1.0)
        
        # Check memory threshold (can override CPU decision if more critical)
        if metrics.memory_percent > self.memory_scale_up_threshold:
            action = "scale_up"
            reason = f"Memory utilization ({metrics.memory_percent:.1f}%) above threshold ({self.memory_scale_up_threshold}%)"
            recommended_replicas = min(self.current_replicas + 1, self.max_replicas)
            confidence = min((metrics.memory_percent - self.memory_scale_up_threshold) / 20.0, 1.0)
        
        return ScalingRecommendation(
            action=action,
            reason=reason,
            current_replicas=self.current_replicas,
            recommended_replicas=recommended_replicas,
            confidence=confidence,
            metrics_snapshot=metrics
        )
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary for monitoring"""
        # Get fresh dependency health if stale
        if (self.last_full_check is None or 
            (datetime.utcnow() - self.last_full_check).total_seconds() > self.health_check_interval_seconds):
            self.check_all_dependencies()
        
        # Determine overall health
        overall_status = HealthStatus.HEALTHY
        
        for dep in self.dependency_health.values():
            if dep.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            elif dep.status == HealthStatus.DEGRADED:
                overall_status = HealthStatus.DEGRADED
        
        # Get resource metrics
        metrics = self.get_resource_metrics()
        
        # Get scaling recommendation
        scaling = self.get_scaling_recommendation(metrics)
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "probes": {
                "liveness": self.is_alive(),
                "readiness": self.is_ready(),
                "startup": self.is_started()
            },
            "dependencies": {
                name: {
                    "status": dep.status.value,
                    "latency_ms": dep.latency_ms,
                    "last_check": dep.last_check.isoformat(),
                    "error": dep.error_message,
                    "metadata": dep.metadata
                }
                for name, dep in self.dependency_health.items()
            },
            "resources": {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "memory_used_mb": metrics.memory_used_mb,
                "disk_percent": metrics.disk_percent,
                "network_connections": metrics.network_connections
            },
            "scaling": {
                "action": scaling.action,
                "reason": scaling.reason,
                "current_replicas": scaling.current_replicas,
                "recommended_replicas": scaling.recommended_replicas,
                "confidence": scaling.confidence
            }
        }
