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
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import logging

import psutil
from sqlalchemy import text

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from sensei.core.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
        s3_client: Optional[Any] = None,
        llm_client: Optional[Any] = None,
    ):
        self.db_session_factory = db_session_factory
        self.redis_client = redis_client
        self.s3_client = s3_client
        self.llm_client = llm_client
        
        # Health check configuration
        self.startup_complete = False
        self.startup_time = _utcnow()
        self.max_startup_duration_seconds = settings.HEALTH_LATENCY_OK_MS
        
        # Dependency health tracking
        self.dependency_health: Dict[str, DependencyHealth] = {}
        self.health_check_interval_seconds = settings.HEALTH_LATENCY_WARN_MS
        self.last_full_check: Optional[datetime] = None
        
        # AI model health tracking
        self.ai_model_loaded = False
        self.ai_model_last_check: Optional[datetime] = None
        self.ai_model_load_time_seconds: Optional[float] = None
        
        # Auto-scaling thresholds (configurable via settings)
        self.cpu_scale_up_threshold = settings.HEALTH_CPU_OK_PCT
        self.cpu_scale_down_threshold = settings.HEALTH_CPU_WARN_PCT
        self.memory_scale_up_threshold = settings.HEALTH_MEMORY_OK_PCT
        self.memory_scale_down_threshold = settings.HEALTH_MEMORY_WARN_PCT
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
        elapsed = (_utcnow() - self.startup_time).total_seconds()
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
                        logger.exception("Failed to fetch database connection count")
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
            last_check=_utcnow(),
            error_message=error_msg,
            metadata=metadata
        )
        
        self.dependency_health["database"] = health
        return health
    
    def _check_redis_health_sync(self) -> tuple:
        """Synchronous Redis health check (run in thread)."""
        status = HealthStatus.UNKNOWN
        error_msg = None
        metadata = {}
        if self.redis_client is None:
            raise Exception("Redis client not configured")
        result = self.redis_client.ping()
        if result:
            status = HealthStatus.HEALTHY
            try:
                info = self.redis_client.info()
                metadata["connected_clients"] = info.get("connected_clients", 0)
                metadata["used_memory_mb"] = info.get("used_memory", 0) / 1024 / 1024
            except Exception:
                logger.exception("Failed to fetch Redis metrics")
        else:
            status = HealthStatus.UNHEALTHY
            error_msg = "Redis ping failed"
        return status, error_msg, metadata

    async def check_redis_health(self) -> DependencyHealth:
        """Check Redis connectivity and performance (async)."""
        start_time = time.time()
        status = HealthStatus.UNKNOWN
        error_msg = None
        metadata = {}

        try:
            status, error_msg, metadata = await asyncio.to_thread(
                self._check_redis_health_sync
            )
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
            last_check=_utcnow(),
            error_message=error_msg,
            metadata=metadata
        )

        self.dependency_health["redis"] = health
        return health
    
    def _check_s3_health_sync(self) -> tuple:
        """Synchronous S3 health check (run in thread)."""
        status = HealthStatus.UNKNOWN
        error_msg = None
        metadata = {}
        if self.s3_client is None:
            raise Exception("S3 client not configured")
        buckets = self.s3_client.list_buckets()
        if buckets:
            status = HealthStatus.HEALTHY
            metadata["bucket_count"] = len(buckets.get("Buckets", []))
        else:
            status = HealthStatus.DEGRADED
            error_msg = "S3 accessible but no buckets found"
        return status, error_msg, metadata

    async def check_s3_health(self) -> DependencyHealth:
        """Check S3 storage connectivity (async)."""
        start_time = time.time()
        status = HealthStatus.UNKNOWN
        error_msg = None
        metadata = {}

        try:
            status, error_msg, metadata = await asyncio.to_thread(
                self._check_s3_health_sync
            )
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
            last_check=_utcnow(),
            error_message=error_msg,
            metadata=metadata
        )

        self.dependency_health["s3"] = health
        return health
    
    def check_ai_model_health(self) -> DependencyHealth:
        """
        Check AI/LLM model health and availability.
        
        This performs:
        1. Model file existence check
        2. Model loading capability check (if client provided)
        3. Simple inference test to verify model functionality
        """
        start_time = time.time()
        status = HealthStatus.UNKNOWN
        error_msg = None
        metadata: Dict[str, Any] = {}
        
        try:
            # Import settings to check model path
            from sensei.core.config import settings
            from pathlib import Path
            
            model_path = Path(settings.CHATBOT_MODEL_PATH)
            metadata["model_path"] = str(model_path)
            metadata["model_url"] = settings.CHATBOT_MODEL_URL
            
            # Step 1: Check if model file exists
            if model_path.is_absolute():
                model_exists = model_path.exists()
            else:
                # Try relative to workspace
                workspace_model = Path.cwd() / model_path
                project_root_model = Path(__file__).parent.parent.parent.parent.parent / model_path
                model_exists = workspace_model.exists() or project_root_model.exists()
                if workspace_model.exists():
                    model_path = workspace_model
                elif project_root_model.exists():
                    model_path = project_root_model
            
            metadata["model_exists"] = model_exists
            
            if not model_exists:
                status = HealthStatus.DEGRADED
                error_msg = (
                    f"Model file not found at {model_path}. "
                    f"Download from: {settings.CHATBOT_MODEL_URL}"
                )
                metadata["download_required"] = True
            else:
                # Get model file size
                model_size_mb = model_path.stat().st_size / (1024 * 1024)
                metadata["model_size_mb"] = round(model_size_mb, 2)
                
                # Step 2: Check if LLM client is available and model can be loaded
                if self.llm_client is not None:
                    try:
                        # Check if client is initialized
                        if hasattr(self.llm_client, 'is_initialized'):
                            is_init = self.llm_client.is_initialized()
                            metadata["client_initialized"] = is_init
                        
                        # Check model type
                        if hasattr(self.llm_client, 'model_type'):
                            metadata["model_type"] = str(self.llm_client.model_type)
                        
                        # Step 3: Simple inference test (fast validation)
                        if hasattr(self.llm_client, 'complete'):
                            try:
                                # Use minimal tokens for health check
                                test_result = self.llm_client.complete(
                                    "Hello",
                                    max_tokens=5,
                                    temperature=0.0
                                )
                                if test_result:
                                    status = HealthStatus.HEALTHY
                                    metadata["inference_functional"] = True
                                else:
                                    status = HealthStatus.DEGRADED
                                    metadata["inference_functional"] = False
                                    error_msg = "Inference returned empty result"
                            except Exception as inference_error:
                                status = HealthStatus.DEGRADED
                                metadata["inference_functional"] = False
                                error_msg = f"Inference test failed: {inference_error}"
                        else:
                            # No complete method, just mark as healthy if model exists
                            status = HealthStatus.HEALTHY
                            metadata["inference_functional"] = "not_tested"
                    except Exception as client_error:
                        status = HealthStatus.DEGRADED
                        error_msg = f"LLM client check failed: {client_error}"
                else:
                    # No client provided, but model file exists
                    status = HealthStatus.HEALTHY
                    metadata["llm_client_available"] = False
                    metadata["inference_functional"] = "not_tested"
        
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            error_msg = f"AI model health check failed: {e}"
            logger.exception("AI model health check error")
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Mark as degraded if health check takes too long
        if status == HealthStatus.HEALTHY and latency_ms > 5000:
            status = HealthStatus.DEGRADED
            error_msg = f"AI model health check slow ({latency_ms:.0f}ms)"
        
        health = DependencyHealth(
            name="AI/LLM Model",
            dependency_type=DependencyType.EXTERNAL_API,  # Using EXTERNAL_API type for AI services
            status=status,
            latency_ms=latency_ms,
            last_check=_utcnow(),
            error_message=error_msg,
            metadata=metadata
        )
        
        self.dependency_health["ai_model"] = health
        self.ai_model_last_check = _utcnow()
        
        if status == HealthStatus.HEALTHY:
            self.ai_model_loaded = True
            if self.ai_model_load_time_seconds is None:
                self.ai_model_load_time_seconds = latency_ms / 1000
        
        return health
    
    async def verify_ai_model_at_startup(self) -> bool:
        """
        Verify AI model is available at startup.

        This is a critical startup check that ensures the chatbot model
        is properly configured and accessible. Returns True if model is
        healthy or degraded (can work), False if completely unavailable.

        Call this during application lifespan startup.
        """
        logger.info("Verifying AI model availability at startup...")

        try:
            health = await asyncio.to_thread(self.check_ai_model_health)
            
            if health.status == HealthStatus.HEALTHY:
                logger.info(
                    "AI model healthy",
                    model_path=health.metadata.get("model_path"),
                    model_size_mb=health.metadata.get("model_size_mb"),
                    inference_functional=health.metadata.get("inference_functional"),
                )
                return True
            elif health.status == HealthStatus.DEGRADED:
                logger.warning(
                    "AI model degraded",
                    error=health.error_message,
                    metadata=health.metadata,
                )
                # Still allow startup, but warn
                return True
            else:
                logger.error(
                    "AI model unhealthy - chatbot will not function",
                    error=health.error_message,
                    metadata=health.metadata,
                )
                return False
        except Exception as e:
            logger.exception("Failed to verify AI model at startup")
            return False
    
    async def check_all_dependencies(self) -> List[DependencyHealth]:
        """Check health of all configured dependencies concurrently."""
        tasks = []

        if self.db_session_factory:
            tasks.append(self.check_database_health())

        if self.redis_client:
            tasks.append(self.check_redis_health())

        if self.s3_client:
            tasks.append(self.check_s3_health())

        # AI model check is CPU-bound; wrap in to_thread
        tasks.append(asyncio.to_thread(self.check_ai_model_health))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        clean: List[DependencyHealth] = []
        for r in results:
            if isinstance(r, BaseException):
                logger.exception("Dependency health check failed", exc_info=r)
            else:
                clean.append(r)

        self.last_full_check = _utcnow()
        return clean
    
    def _get_resource_metrics_sync(self) -> ResourceMetrics:
        """Synchronous resource metrics (run in thread)."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network_connections = len(psutil.net_connections())
        return ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            memory_available_mb=memory.available / 1024 / 1024,
            disk_percent=disk.percent,
            disk_used_gb=disk.used / 1024 / 1024 / 1024,
            disk_available_gb=disk.free / 1024 / 1024 / 1024,
            network_connections=network_connections,
            timestamp=_utcnow(),
        )

    async def get_resource_metrics(self) -> ResourceMetrics:
        """Get current resource utilization metrics (async)."""
        return await asyncio.to_thread(self._get_resource_metrics_sync)
    
    async def get_scaling_recommendation(
        self,
        metrics: Optional[ResourceMetrics] = None
    ) -> ScalingRecommendation:
        """
        Generate auto-scaling recommendation based on current metrics
        Used by Kubernetes HPA for intelligent scaling decisions
        """
        if metrics is None:
            metrics = await self.get_resource_metrics()
        
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
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary for monitoring (async)."""
        # Get fresh dependency health if stale
        if (self.last_full_check is None or 
            (_utcnow() - self.last_full_check).total_seconds() > self.health_check_interval_seconds):
            await self.check_all_dependencies()
        
        # Determine overall health
        overall_status = HealthStatus.HEALTHY
        
        for dep in self.dependency_health.values():
            if dep.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            elif dep.status == HealthStatus.DEGRADED:
                overall_status = HealthStatus.DEGRADED
        
        # Get resource metrics
        metrics = await self.get_resource_metrics()
        
        # Get scaling recommendation
        scaling = await self.get_scaling_recommendation(metrics)
        
        return {
            "status": overall_status.value,
            "timestamp": _utcnow().isoformat(),
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
