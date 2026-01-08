"""
Tests for Health Checks and Auto-scaling Service

Validates health monitoring, dependency checks, resource metrics,
and auto-scaling recommendations.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from sensei.services.health_checks import (
    DependencyHealth,
    DependencyType,
    HealthCheckService,
    HealthStatus,
    ResourceMetrics,
    ScalingRecommendation,
)


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = Mock()
    result = Mock()
    result.scalar.return_value = 1
    session.execute.return_value = result
    session.close = Mock()
    return session


@pytest.fixture
def mock_db_session_factory(mock_db_session):
    """Create mock database session factory"""
    return lambda: mock_db_session


@pytest.fixture
def mock_redis():
    """Create mock Redis client"""
    redis = Mock()
    redis.ping.return_value = True
    redis.info.return_value = {
        "connected_clients": 5,
        "used_memory": 1024 * 1024 * 50  # 50MB
    }
    return redis


@pytest.fixture
def mock_s3():
    """Create mock S3 client"""
    s3 = Mock()
    s3.list_buckets.return_value = {
        "Buckets": [
            {"Name": "test-bucket-1"},
            {"Name": "test-bucket-2"}
        ]
    }
    return s3


@pytest.fixture
def service():
    """Create health check service without dependencies"""
    return HealthCheckService()


@pytest.fixture
def full_service(mock_db_session_factory, mock_redis, mock_s3):
    """Create health check service with all dependencies"""
    return HealthCheckService(
        db_session_factory=mock_db_session_factory,
        redis_client=mock_redis,
        s3_client=mock_s3
    )


class TestHealthCheckService:
    """Test HealthCheckService"""
    
    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service.startup_complete is False
        assert service.startup_time is not None
        assert service.max_startup_duration_seconds == 60
        assert service.dependency_health == {}
        assert service.current_replicas == 2
        assert service.min_replicas == 2
        assert service.max_replicas == 10
    
    def test_mark_startup_complete(self, service):
        """Test marking startup as complete"""
        assert service.startup_complete is False
        
        service.mark_startup_complete()
        
        assert service.startup_complete is True
    
    def test_is_alive(self, service):
        """Test liveness probe"""
        assert service.is_alive() is True
    
    def test_is_ready_not_started(self, service):
        """Test readiness probe before startup"""
        assert service.is_ready() is False
    
    def test_is_ready_after_startup(self, service):
        """Test readiness probe after startup"""
        service.mark_startup_complete()
        assert service.is_ready() is True
    
    def test_is_ready_with_unhealthy_dependency(self, full_service):
        """Test readiness probe with unhealthy critical dependency"""
        full_service.mark_startup_complete()
        
        # Add unhealthy database dependency
        full_service.dependency_health["database"] = DependencyHealth(
            name="PostgreSQL",
            dependency_type=DependencyType.DATABASE,
            status=HealthStatus.UNHEALTHY,
            latency_ms=1000.0,
            last_check=datetime.utcnow(),
            error_message="Connection failed"
        )
        
        assert full_service.is_ready() is False
    
    def test_is_started_before_complete(self, service):
        """Test startup probe before completion"""
        assert service.is_started() is False
    
    def test_is_started_after_complete(self, service):
        """Test startup probe after completion"""
        service.mark_startup_complete()
        assert service.is_started() is True
    
    def test_is_started_timeout(self, service):
        """Test startup probe timeout"""
        # Simulate startup taking too long
        service.startup_time = datetime.utcnow() - timedelta(seconds=65)
        
        # Should auto-complete after timeout
        assert service.is_started() is True
        assert service.startup_complete is True
    
    def test_check_database_health_success(self, full_service, mock_db_session):
        """Test successful database health check"""
        health = full_service.check_database_health()
        
        assert health.name == "PostgreSQL Database"
        assert health.dependency_type == DependencyType.DATABASE
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms > 0
        assert health.error_message is None
        
        # Verify session was closed
        mock_db_session.close.assert_called_once()
    
    def test_check_database_health_no_factory(self, service):
        """Test database health check without factory"""
        health = service.check_database_health()
        
        assert health.status == HealthStatus.UNHEALTHY
        assert "not configured" in health.error_message
    
    def test_check_database_health_query_failure(self, full_service, mock_db_session):
        """Test database health check with query failure"""
        mock_db_session.execute.side_effect = Exception("Connection timeout")
        
        health = full_service.check_database_health()
        
        assert health.status == HealthStatus.UNHEALTHY
        assert "Connection timeout" in health.error_message
    
    def test_check_database_health_slow_response(self, full_service, mock_db_session):
        """Test database health check with slow response"""
        # Simulate slow query
        def slow_execute(*args, **kwargs):
            time.sleep(0.15)  # 150ms
            result = Mock()
            result.scalar.return_value = 1
            return result
        
        mock_db_session.execute = slow_execute
        
        health = full_service.check_database_health()
        
        # Should be degraded due to high latency
        assert health.status == HealthStatus.DEGRADED
        assert health.latency_ms > 100
    
    def test_check_redis_health_success(self, full_service):
        """Test successful Redis health check"""
        health = full_service.check_redis_health()
        
        assert health.name == "Redis Cache"
        assert health.dependency_type == DependencyType.CACHE
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms > 0
        assert health.error_message is None
        assert "connected_clients" in health.metadata
    
    def test_check_redis_health_no_client(self, service):
        """Test Redis health check without client"""
        health = service.check_redis_health()
        
        assert health.status == HealthStatus.UNHEALTHY
        assert "not configured" in health.error_message
    
    def test_check_redis_health_ping_failure(self, full_service, mock_redis):
        """Test Redis health check with ping failure"""
        mock_redis.ping.side_effect = Exception("Connection refused")
        
        health = full_service.check_redis_health()
        
        assert health.status == HealthStatus.UNHEALTHY
        assert "Connection refused" in health.error_message
    
    def test_check_s3_health_success(self, full_service):
        """Test successful S3 health check"""
        health = full_service.check_s3_health()
        
        assert health.name == "S3 Storage"
        assert health.dependency_type == DependencyType.STORAGE
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms > 0
        assert health.error_message is None
        assert health.metadata["bucket_count"] == 2
    
    def test_check_s3_health_no_client(self, service):
        """Test S3 health check without client"""
        health = service.check_s3_health()
        
        assert health.status == HealthStatus.UNHEALTHY
        assert "not configured" in health.error_message
    
    def test_check_s3_health_failure(self, full_service, mock_s3):
        """Test S3 health check with failure"""
        mock_s3.list_buckets.side_effect = Exception("Access denied")
        
        health = full_service.check_s3_health()
        
        assert health.status == HealthStatus.UNHEALTHY
        assert "Access denied" in health.error_message
    
    def test_check_all_dependencies(self, full_service):
        """Test checking all dependencies"""
        results = full_service.check_all_dependencies()
        
        assert len(results) == 3
        assert full_service.last_full_check is not None
        
        # All should be healthy
        for health in results:
            assert health.status == HealthStatus.HEALTHY
    
    @patch('sensei.services.health_checks.psutil')
    def test_get_resource_metrics(self, mock_psutil, service):
        """Test getting resource metrics"""
        # Mock psutil responses
        mock_psutil.cpu_percent.return_value = 45.5
        
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.used = 1024 * 1024 * 1024 * 4  # 4GB
        mock_memory.available = 1024 * 1024 * 1024 * 4  # 4GB
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.percent = 70.0
        mock_disk.used = 1024 * 1024 * 1024 * 50  # 50GB
        mock_disk.free = 1024 * 1024 * 1024 * 20  # 20GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_psutil.net_connections.return_value = [1, 2, 3, 4, 5]
        
        metrics = service.get_resource_metrics()
        
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_percent == 60.0
        assert metrics.memory_used_mb == 4096.0
        assert metrics.disk_percent == 70.0
        assert metrics.network_connections == 5
        assert metrics.timestamp is not None
    
    def test_get_scaling_recommendation_maintain(self, service):
        """Test scaling recommendation to maintain"""
        metrics = ResourceMetrics(
            cpu_percent=50.0,
            memory_percent=50.0,
            memory_used_mb=2048.0,
            memory_available_mb=2048.0,
            disk_percent=50.0,
            disk_used_gb=25.0,
            disk_available_gb=25.0,
            network_connections=10,
            timestamp=datetime.utcnow()
        )
        
        recommendation = service.get_scaling_recommendation(metrics)
        
        assert recommendation.action == "maintain"
        assert recommendation.current_replicas == 2
        assert recommendation.recommended_replicas == 2
    
    def test_get_scaling_recommendation_scale_up_cpu(self, service):
        """Test scaling recommendation to scale up due to CPU"""
        metrics = ResourceMetrics(
            cpu_percent=85.0,  # Above 70% threshold
            memory_percent=50.0,
            memory_used_mb=2048.0,
            memory_available_mb=2048.0,
            disk_percent=50.0,
            disk_used_gb=25.0,
            disk_available_gb=25.0,
            network_connections=10,
            timestamp=datetime.utcnow()
        )
        
        recommendation = service.get_scaling_recommendation(metrics)
        
        assert recommendation.action == "scale_up"
        assert "CPU" in recommendation.reason
        assert recommendation.recommended_replicas == 3
        assert recommendation.confidence > 0
    
    def test_get_scaling_recommendation_scale_down_cpu(self, service):
        """Test scaling recommendation to scale down due to low CPU"""
        metrics = ResourceMetrics(
            cpu_percent=20.0,  # Below 30% threshold
            memory_percent=50.0,
            memory_used_mb=2048.0,
            memory_available_mb=2048.0,
            disk_percent=50.0,
            disk_used_gb=25.0,
            disk_available_gb=25.0,
            network_connections=10,
            timestamp=datetime.utcnow()
        )
        
        recommendation = service.get_scaling_recommendation(metrics)
        
        assert recommendation.action == "scale_down"
        assert "CPU" in recommendation.reason
        assert recommendation.recommended_replicas == 2  # Min replicas
    
    def test_get_scaling_recommendation_scale_up_memory(self, service):
        """Test scaling recommendation to scale up due to memory"""
        metrics = ResourceMetrics(
            cpu_percent=50.0,
            memory_percent=85.0,  # Above 80% threshold
            memory_used_mb=7000.0,
            memory_available_mb=1000.0,
            disk_percent=50.0,
            disk_used_gb=25.0,
            disk_available_gb=25.0,
            network_connections=10,
            timestamp=datetime.utcnow()
        )
        
        recommendation = service.get_scaling_recommendation(metrics)
        
        assert recommendation.action == "scale_up"
        assert "Memory" in recommendation.reason
        assert recommendation.recommended_replicas == 3
    
    def test_get_scaling_recommendation_max_replicas(self, service):
        """Test scaling recommendation respects max replicas"""
        service.current_replicas = 10  # Already at max
        
        metrics = ResourceMetrics(
            cpu_percent=90.0,
            memory_percent=90.0,
            memory_used_mb=7500.0,
            memory_available_mb=500.0,
            disk_percent=50.0,
            disk_used_gb=25.0,
            disk_available_gb=25.0,
            network_connections=10,
            timestamp=datetime.utcnow()
        )
        
        recommendation = service.get_scaling_recommendation(metrics)
        
        assert recommendation.action == "scale_up"
        assert recommendation.recommended_replicas == 10  # Cannot exceed max
    
    def test_get_health_summary(self, full_service):
        """Test getting comprehensive health summary"""
        full_service.mark_startup_complete()
        
        with patch.object(full_service, 'get_resource_metrics') as mock_metrics:
            mock_metrics.return_value = ResourceMetrics(
                cpu_percent=45.0,
                memory_percent=55.0,
                memory_used_mb=2200.0,
                memory_available_mb=1800.0,
                disk_percent=60.0,
                disk_used_gb=30.0,
                disk_available_gb=20.0,
                network_connections=15,
                timestamp=datetime.utcnow()
            )
            
            summary = full_service.get_health_summary()
        
        assert "status" in summary
        assert "timestamp" in summary
        assert "probes" in summary
        assert "dependencies" in summary
        assert "resources" in summary
        assert "scaling" in summary
        
        # Check probes
        assert summary["probes"]["liveness"] is True
        assert summary["probes"]["readiness"] is True
        assert summary["probes"]["startup"] is True
        
        # Check resources
        assert summary["resources"]["cpu_percent"] == 45.0
        assert summary["resources"]["memory_percent"] == 55.0
        
        # Check scaling
        assert summary["scaling"]["action"] == "maintain"
    
    def test_get_health_summary_with_unhealthy_dependency(self, full_service, mock_redis):
        """Test health summary with unhealthy dependency"""
        full_service.mark_startup_complete()
        
        # Make Redis fail
        mock_redis.ping.side_effect = Exception("Connection refused")
        
        with patch.object(full_service, 'get_resource_metrics') as mock_metrics:
            mock_metrics.return_value = ResourceMetrics(
                cpu_percent=45.0,
                memory_percent=55.0,
                memory_used_mb=2200.0,
                memory_available_mb=1800.0,
                disk_percent=60.0,
                disk_used_gb=30.0,
                disk_available_gb=20.0,
                network_connections=15,
                timestamp=datetime.utcnow()
            )
            
            summary = full_service.get_health_summary()
        
        # Overall status should be unhealthy
        assert summary["status"] == HealthStatus.UNHEALTHY.value
        
        # Redis should be unhealthy in dependencies
        assert summary["dependencies"]["redis"]["status"] == HealthStatus.UNHEALTHY.value


class TestResourceMetrics:
    """Test ResourceMetrics dataclass"""
    
    def test_resource_metrics_creation(self):
        """Test creating resource metrics"""
        metrics = ResourceMetrics(
            cpu_percent=45.5,
            memory_percent=60.0,
            memory_used_mb=2048.0,
            memory_available_mb=2048.0,
            disk_percent=70.0,
            disk_used_gb=50.0,
            disk_available_gb=20.0,
            network_connections=10,
            timestamp=datetime.utcnow()
        )
        
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_percent == 60.0
        assert metrics.disk_percent == 70.0
        assert metrics.network_connections == 10


class TestScalingRecommendation:
    """Test ScalingRecommendation dataclass"""
    
    def test_scaling_recommendation_creation(self):
        """Test creating scaling recommendation"""
        metrics = ResourceMetrics(
            cpu_percent=45.0,
            memory_percent=60.0,
            memory_used_mb=2048.0,
            memory_available_mb=2048.0,
            disk_percent=70.0,
            disk_used_gb=50.0,
            disk_available_gb=20.0,
            network_connections=10,
            timestamp=datetime.utcnow()
        )
        
        recommendation = ScalingRecommendation(
            action="scale_up",
            reason="High CPU usage",
            current_replicas=2,
            recommended_replicas=3,
            confidence=0.8,
            metrics_snapshot=metrics
        )
        
        assert recommendation.action == "scale_up"
        assert recommendation.current_replicas == 2
        assert recommendation.recommended_replicas == 3
        assert recommendation.confidence == 0.8


class TestDependencyHealth:
    """Test DependencyHealth dataclass"""
    
    def test_dependency_health_creation(self):
        """Test creating dependency health"""
        health = DependencyHealth(
            name="PostgreSQL",
            dependency_type=DependencyType.DATABASE,
            status=HealthStatus.HEALTHY,
            latency_ms=25.5,
            last_check=datetime.utcnow(),
            error_message=None,
            metadata={"connections": 10}
        )
        
        assert health.name == "PostgreSQL"
        assert health.dependency_type == DependencyType.DATABASE
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms == 25.5
        assert health.metadata["connections"] == 10
