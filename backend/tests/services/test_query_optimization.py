"""
Tests for Query Optimization Service

Validates query performance monitoring, optimization recommendations,
caching, and pagination optimization.
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from sensei.services.core.query_optimization import (
    IndexRecommendation,
    PerformanceThreshold,
    QueryAnalysis,
    QueryMetrics,
    QueryOptimizationService,
    QueryType,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing"""
    return create_engine("sqlite:///:memory:", echo=False)


@pytest.fixture
def service(engine):
    """Create query optimization service"""
    return QueryOptimizationService(engine, enable_monitoring=False)


@pytest.fixture
def service_with_monitoring(engine):
    """Create query optimization service with monitoring enabled"""
    return QueryOptimizationService(engine, enable_monitoring=True)


class TestQueryMetrics:
    """Test QueryMetrics dataclass"""
    
    def test_metrics_creation(self):
        """Test creating query metrics"""
        metrics = QueryMetrics(
            query_hash="abc123",
            query_text="SELECT * FROM users",
            query_type=QueryType.SELECT,
            execution_time_ms=150.5,
            row_count=10,
            timestamp=_utcnow()
        )
        
        assert metrics.query_hash == "abc123"
        assert metrics.query_type == QueryType.SELECT
        assert metrics.execution_time_ms == 150.5
        assert metrics.row_count == 10
        assert metrics.threshold_level == PerformanceThreshold.GOOD
    
    def test_threshold_calculation_excellent(self):
        """Test threshold calculation for excellent performance"""
        metrics = QueryMetrics(
            query_hash="test",
            query_text="SELECT 1",
            query_type=QueryType.SELECT,
            execution_time_ms=30.0,
            row_count=1,
            timestamp=_utcnow()
        )
        assert metrics.threshold_level == PerformanceThreshold.EXCELLENT
    
    def test_threshold_calculation_good(self):
        """Test threshold calculation for good performance"""
        metrics = QueryMetrics(
            query_hash="test",
            query_text="SELECT 1",
            query_type=QueryType.SELECT,
            execution_time_ms=150.0,
            row_count=1,
            timestamp=_utcnow()
        )
        assert metrics.threshold_level == PerformanceThreshold.GOOD
    
    def test_threshold_calculation_acceptable(self):
        """Test threshold calculation for acceptable performance"""
        metrics = QueryMetrics(
            query_hash="test",
            query_text="SELECT 1",
            query_type=QueryType.SELECT,
            execution_time_ms=800.0,
            row_count=1,
            timestamp=_utcnow()
        )
        assert metrics.threshold_level == PerformanceThreshold.ACCEPTABLE
    
    def test_threshold_calculation_slow(self):
        """Test threshold calculation for slow performance"""
        metrics = QueryMetrics(
            query_hash="test",
            query_text="SELECT 1",
            query_type=QueryType.SELECT,
            execution_time_ms=1500.0,
            row_count=1,
            timestamp=_utcnow()
        )
        assert metrics.threshold_level == PerformanceThreshold.SLOW
    
    def test_threshold_calculation_critical(self):
        """Test threshold calculation for critical performance"""
        metrics = QueryMetrics(
            query_hash="test",
            query_text="SELECT 1",
            query_type=QueryType.SELECT,
            execution_time_ms=2500.0,
            row_count=1,
            timestamp=_utcnow()
        )
        assert metrics.threshold_level == PerformanceThreshold.CRITICAL


class TestQueryOptimizationService:
    """Test QueryOptimizationService"""
    
    def test_service_initialization(self, engine):
        """Test service initialization"""
        service = QueryOptimizationService(engine, enable_monitoring=False)
        
        assert service.engine == engine
        assert service.enable_monitoring is False
        assert service.query_metrics == []
        assert service.query_cache == {}
        assert service.cache_ttl_seconds == 300
        assert service.slow_query_threshold_ms == 1500
        assert service.search_query_threshold_ms == 1500
    
    def test_hash_query(self, service):
        """Test query hashing"""
        query1 = "SELECT * FROM users WHERE id = 1"
        query2 = "SELECT * FROM users WHERE id = 2"
        query3 = "SELECT * FROM users WHERE id = 1"
        
        hash1 = service._hash_query(query1)
        hash2 = service._hash_query(query2)
        hash3 = service._hash_query(query3)
        
        assert isinstance(hash1, str)
        assert len(hash1) == 16
        # Different parameters produce different hashes (includes values)
        assert hash1 != hash2
        # Identical queries produce same hash
        assert hash1 == hash3
    
    def test_detect_query_type_select(self, service):
        """Test detecting SELECT query type"""
        query_type = service._detect_query_type("SELECT * FROM users")
        assert query_type == QueryType.SELECT
    
    def test_detect_query_type_search(self, service):
        """Test detecting SEARCH query type"""
        query = "SELECT * FROM users WHERE name LIKE '%test%'"
        query_type = service._detect_query_type(query)
        assert query_type == QueryType.SEARCH
    
    def test_detect_query_type_aggregation(self, service):
        """Test detecting AGGREGATION query type"""
        query = "SELECT COUNT(*) FROM users GROUP BY role"
        query_type = service._detect_query_type(query)
        assert query_type == QueryType.AGGREGATION
    
    def test_detect_query_type_insert(self, service):
        """Test detecting INSERT query type"""
        query = "INSERT INTO users (name) VALUES ('test')"
        query_type = service._detect_query_type(query)
        assert query_type == QueryType.INSERT
    
    def test_detect_query_type_update(self, service):
        """Test detecting UPDATE query type"""
        query = "UPDATE users SET name = 'test' WHERE id = 1"
        query_type = service._detect_query_type(query)
        assert query_type == QueryType.UPDATE
    
    def test_detect_query_type_delete(self, service):
        """Test detecting DELETE query type"""
        query = "DELETE FROM users WHERE id = 1"
        query_type = service._detect_query_type(query)
        assert query_type == QueryType.DELETE
    
    def test_get_cache_key(self, service):
        """Test cache key generation"""
        query = "SELECT * FROM users WHERE id = ?"
        params1 = {"id": 1}
        params2 = {"id": 2}
        params3 = {"id": 1}
        
        key1 = service.get_cache_key(query, params1)
        key2 = service.get_cache_key(query, params2)
        key3 = service.get_cache_key(query, params3)
        
        assert key1 != key2  # Different parameters
        assert key1 == key3  # Same parameters
    
    def test_cache_query_result(self, service):
        """Test caching query results"""
        query = "SELECT * FROM users"
        params = {}
        result = [{"id": 1, "name": "Test"}]
        
        service.cache_query_result(query, params, result, ttl_seconds=60)
        
        cached = service.get_cached_result(query, params)
        assert cached == result
    
    def test_cache_expiry(self, service):
        """Test cache expiry"""
        query = "SELECT * FROM users"
        params = {}
        result = [{"id": 1}]
        
        # Cache with very short TTL
        service.cache_query_result(query, params, result, ttl_seconds=0)
        
        # Should be expired immediately
        time.sleep(0.01)
        cached = service.get_cached_result(query, params)
        assert cached is None
    
    def test_clear_cache_all(self, service):
        """Test clearing all cache"""
        service.cache_query_result("SELECT 1", {}, [1])
        service.cache_query_result("SELECT 2", {}, [2])
        
        assert len(service.query_cache) == 2
        
        service.clear_cache()
        assert len(service.query_cache) == 0
    
    def test_clear_cache_pattern(self, service):
        """Test clearing cache with pattern"""
        key1 = service.get_cache_key("SELECT * FROM users", {})
        key2 = service.get_cache_key("SELECT * FROM accounts", {})
        
        service.query_cache[key1] = ([1], _utcnow() + timedelta(hours=1))
        service.query_cache[key2] = ([2], _utcnow() + timedelta(hours=1))
        
        # This is a simple test - in practice, pattern matching would be more sophisticated
        service.clear_cache(pattern=key1)
        
        assert key1 not in service.query_cache
        assert key2 in service.query_cache
    
    def test_analyze_query_performance_no_data(self, service):
        """Test query analysis with no data"""
        analyses = service.analyze_query_performance()
        assert analyses == []
    
    def test_analyze_query_performance_insufficient_data(self, service):
        """Test query analysis with insufficient data"""
        # Add only 5 metrics (below min_executions=10)
        for i in range(5):
            service.query_metrics.append(
                QueryMetrics(
                    query_hash="test123",
                    query_text="SELECT * FROM users",
                    query_type=QueryType.SELECT,
                    execution_time_ms=100.0,
                    row_count=10,
                    timestamp=_utcnow()
                )
            )
        
        analyses = service.analyze_query_performance(min_executions=10)
        assert analyses == []
    
    def test_analyze_query_performance_with_data(self, service):
        """Test query analysis with sufficient data"""
        query_hash = "test123"
        execution_times = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500,
                          550, 600, 650, 700, 750]
        
        for exec_time in execution_times:
            service.query_metrics.append(
                QueryMetrics(
                    query_hash=query_hash,
                    query_text="SELECT * FROM users WHERE id = ?",
                    query_type=QueryType.SELECT,
                    execution_time_ms=exec_time,
                    row_count=1,
                    timestamp=_utcnow()
                )
            )
        
        analyses = service.analyze_query_performance(min_executions=10)
        
        assert len(analyses) == 1
        analysis = analyses[0]
        
        assert analysis.query_hash == query_hash
        assert analysis.total_executions == 15
        assert analysis.min_execution_time_ms == 50
        assert analysis.max_execution_time_ms == 750
        assert 300 < analysis.avg_execution_time_ms < 500
        assert analysis.p95_execution_time_ms > 600
    
    def test_generate_recommendations_where_clause(self, service):
        """Test generating recommendations for WHERE clause"""
        metric = QueryMetrics(
            query_hash="test",
            query_text="SELECT * FROM users WHERE email = 'test@example.com'",
            query_type=QueryType.SELECT,
            execution_time_ms=1200.0,
            row_count=1,
            timestamp=_utcnow()
        )
        
        recommendations = service._generate_recommendations(metric)
        
        assert len(recommendations) > 0
        assert any("WHERE clause" in rec.reason for rec in recommendations)
    
    def test_generate_recommendations_search(self, service):
        """Test generating recommendations for search queries"""
        metric = QueryMetrics(
            query_hash="test",
            query_text="SELECT * FROM users WHERE name LIKE '%test%'",
            query_type=QueryType.SEARCH,
            execution_time_ms=1800.0,
            row_count=50,
            timestamp=_utcnow()
        )
        
        recommendations = service._generate_recommendations(metric)
        
        assert len(recommendations) > 0
        assert any("GIN index" in rec.reason or "tsvector" in rec.reason for rec in recommendations)
    
    def test_generate_recommendations_order_by(self, service):
        """Test generating recommendations for ORDER BY"""
        metric = QueryMetrics(
            query_hash="test",
            query_text="SELECT * FROM users ORDER BY created_at DESC",
            query_type=QueryType.SELECT,
            execution_time_ms=1100.0,
            row_count=1000,
            timestamp=_utcnow()
        )
        
        recommendations = service._generate_recommendations(metric)
        
        assert len(recommendations) > 0
        assert any("ORDER BY" in rec.reason for rec in recommendations)
    
    def test_get_slow_queries_no_data(self, service):
        """Test getting slow queries with no data"""
        slow_queries = service.get_slow_queries()
        assert slow_queries == []
    
    def test_get_slow_queries_with_data(self, service):
        """Test getting slow queries"""
        # Add mix of slow and fast queries
        for i, exec_time in enumerate([100, 200, 1600, 1700, 1800, 300, 2000]):
            service.query_metrics.append(
                QueryMetrics(
                    query_hash=f"query{i}",
                    query_text=f"SELECT {i}",
                    query_type=QueryType.SELECT,
                    execution_time_ms=exec_time,
                    row_count=1,
                    timestamp=_utcnow()
                )
            )
        
        slow_queries = service.get_slow_queries(threshold_ms=1500, limit=3)
        
        assert len(slow_queries) == 3
        assert slow_queries[0].execution_time_ms == 2000  # Slowest first
        assert slow_queries[1].execution_time_ms == 1800
        assert slow_queries[2].execution_time_ms == 1700
    
    def test_get_performance_summary_no_data(self, service):
        """Test performance summary with no data"""
        summary = service.get_performance_summary()
        
        assert summary["total_queries"] == 0
        assert summary["avg_execution_time_ms"] == 0
        assert summary["slow_queries"] == 0
        assert summary["by_type"] == {}
        assert summary["by_threshold"] == {}
    
    def test_get_performance_summary_with_data(self, service):
        """Test performance summary with data"""
        # Add various queries
        service.query_metrics.extend([
            QueryMetrics(
                query_hash="q1",
                query_text="SELECT 1",
                query_type=QueryType.SELECT,
                execution_time_ms=50,
                row_count=1,
                timestamp=_utcnow()
            ),
            QueryMetrics(
                query_hash="q2",
                query_text="SELECT 2",
                query_type=QueryType.SELECT,
                execution_time_ms=150,
                row_count=1,
                timestamp=_utcnow()
            ),
            QueryMetrics(
                query_hash="q3",
                query_text="INSERT INTO test",
                query_type=QueryType.INSERT,
                execution_time_ms=1600,  # Slow query
                row_count=1,
                timestamp=_utcnow()
            ),
            QueryMetrics(
                query_hash="q4",
                query_text="SELECT 3",
                query_type=QueryType.SEARCH,
                execution_time_ms=800,
                row_count=10,
                timestamp=_utcnow()
            ),
        ])
        
        summary = service.get_performance_summary()
        
        assert summary["total_queries"] == 4
        assert 0 < summary["avg_execution_time_ms"] < 1000
        assert summary["slow_queries"] == 1  # Only one > 1500ms
        assert summary["slow_query_percentage"] == 25.0
        assert summary["by_type"]["select"] == 2
        assert summary["by_type"]["insert"] == 1
        assert summary["by_type"]["search"] == 1
        # Check that thresholds are present (actual values depend on execution times)
        assert len(summary["by_threshold"]) > 0
    
    def test_reset_metrics(self, service):
        """Test resetting metrics"""
        service.query_metrics.extend([
            QueryMetrics(
                query_hash="q1",
                query_text="SELECT 1",
                query_type=QueryType.SELECT,
                execution_time_ms=100,
                row_count=1,
                timestamp=_utcnow()
            )
        ])
        
        assert len(service.query_metrics) == 1
        
        service.reset_metrics()
        assert len(service.query_metrics) == 0


class TestIndexRecommendation:
    """Test IndexRecommendation dataclass"""
    
    def test_recommendation_creation(self):
        """Test creating index recommendation"""
        rec = IndexRecommendation(
            table_name="users",
            columns=["email"],
            reason="Frequent WHERE clause on email",
            estimated_improvement_ms=500.0,
            priority=5,
            query_patterns=["SELECT * FROM users WHERE email = ?"]
        )
        
        assert rec.table_name == "users"
        assert rec.columns == ["email"]
        assert rec.priority == 5
        assert len(rec.query_patterns) == 1


class TestQueryAnalysis:
    """Test QueryAnalysis dataclass"""
    
    def test_analysis_creation(self):
        """Test creating query analysis"""
        analysis = QueryAnalysis(
            query_hash="abc123",
            total_executions=100,
            avg_execution_time_ms=250.0,
            max_execution_time_ms=800.0,
            min_execution_time_ms=50.0,
            p95_execution_time_ms=600.0,
            total_rows_returned=1000,
            using_full_table_scan=True,
            missing_indexes=["users.email"]
        )
        
        assert analysis.query_hash == "abc123"
        assert analysis.total_executions == 100
        assert analysis.using_full_table_scan is True
        assert "users.email" in analysis.missing_indexes
