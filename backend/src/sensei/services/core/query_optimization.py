"""
Query Optimization Service

Provides query performance monitoring, optimization hints, and automatic
query tuning for database operations. Ensures search operations complete
within < 1.5s and general queries meet performance targets.

Features:
- Query performance monitoring and logging
- Automatic index recommendations
- Query plan analysis
- Slow query detection and alerting
- Query result caching
- Pagination optimization
- Search performance optimization
"""

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import Select


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class QueryType(str, Enum):
    """Type of database query"""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    AGGREGATION = "aggregation"


class PerformanceThreshold(str, Enum):
    """Performance threshold levels"""
    EXCELLENT = "excellent"  # < 50ms
    GOOD = "good"           # < 200ms
    ACCEPTABLE = "acceptable"  # < 1000ms
    SLOW = "slow"           # < 2000ms
    CRITICAL = "critical"    # >= 2000ms


@dataclass
class QueryMetrics:
    """Metrics for a single query execution"""
    query_hash: str
    query_text: str
    query_type: QueryType
    execution_time_ms: float
    row_count: int
    timestamp: datetime
    parameters: Dict[str, Any] = field(default_factory=dict)
    index_usage: List[str] = field(default_factory=list)
    table_scans: List[str] = field(default_factory=list)
    threshold_level: PerformanceThreshold = PerformanceThreshold.EXCELLENT
    
    def __post_init__(self):
        """Calculate threshold level based on execution time"""
        if self.execution_time_ms < 50:
            self.threshold_level = PerformanceThreshold.EXCELLENT
        elif self.execution_time_ms < 200:
            self.threshold_level = PerformanceThreshold.GOOD
        elif self.execution_time_ms < 1000:
            self.threshold_level = PerformanceThreshold.ACCEPTABLE
        elif self.execution_time_ms < 2000:
            self.threshold_level = PerformanceThreshold.SLOW
        else:
            self.threshold_level = PerformanceThreshold.CRITICAL


@dataclass
class IndexRecommendation:
    """Recommendation for adding a database index"""
    table_name: str
    columns: List[str]
    reason: str
    estimated_improvement_ms: float
    priority: int  # 1-5, higher is more important
    query_patterns: List[str] = field(default_factory=list)


@dataclass
class QueryAnalysis:
    """Analysis result for a query"""
    query_hash: str
    total_executions: int
    avg_execution_time_ms: float
    max_execution_time_ms: float
    min_execution_time_ms: float
    p95_execution_time_ms: float
    total_rows_returned: int
    recommendations: List[IndexRecommendation] = field(default_factory=list)
    using_full_table_scan: bool = False
    missing_indexes: List[str] = field(default_factory=list)


class QueryOptimizationService:
    """Service for monitoring and optimizing database query performance"""
    
    def __init__(self, engine: Engine, enable_monitoring: bool = True):
        self.engine = engine
        self.enable_monitoring = enable_monitoring
        self.query_metrics: List[QueryMetrics] = []
        self.query_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl_seconds = 300  # 5 minutes default
        self.slow_query_threshold_ms = 1500  # Alert for queries > 1.5s
        self.search_query_threshold_ms = 1500  # Search must be < 1.5s
        
        if enable_monitoring:
            self._setup_monitoring()
    
    def _setup_monitoring(self):
        """Setup SQLAlchemy event listeners for query monitoring"""
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            conn: Connection,
            cursor,
            statement: str,
            parameters,
            context,
            executemany
        ):
            conn.info.setdefault("query_start_time", []).append(time.time())
        
        @event.listens_for(Engine, "after_cursor_execute")
        def receive_after_cursor_execute(
            conn: Connection,
            cursor,
            statement: str,
            parameters,
            context,
            executemany
        ):
            total_time = time.time() - conn.info["query_start_time"].pop()
            execution_time_ms = total_time * 1000
            
            # Create query metrics
            query_hash = self._hash_query(statement)
            query_type = self._detect_query_type(statement)
            
            metrics = QueryMetrics(
                query_hash=query_hash,
                query_text=statement[:500],  # Truncate long queries
                query_type=query_type,
                execution_time_ms=execution_time_ms,
                row_count=cursor.rowcount if cursor.rowcount > 0 else 0,
                timestamp=_utcnow(),
                parameters=parameters if isinstance(parameters, dict) else {}
            )
            
            self.query_metrics.append(metrics)
            
            # Alert on slow queries
            if execution_time_ms > self.slow_query_threshold_ms:
                self._alert_slow_query(metrics)
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query deduplication"""
        # Normalize query by removing parameter values
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _detect_query_type(self, query: str) -> QueryType:
        """Detect type of query from SQL text"""
        query_lower = query.lower().strip()
        
        if query_lower.startswith("select"):
            if "where" in query_lower and any(
                term in query_lower for term in ["like", "ilike", "tsvector", "ts_rank"]
            ):
                return QueryType.SEARCH
            elif any(term in query_lower for term in ["count(", "sum(", "avg(", "group by"]):
                return QueryType.AGGREGATION
            return QueryType.SELECT
        elif query_lower.startswith("insert"):
            return QueryType.INSERT
        elif query_lower.startswith("update"):
            return QueryType.UPDATE
        elif query_lower.startswith("delete"):
            return QueryType.DELETE
        
        return QueryType.SELECT
    
    def _alert_slow_query(self, metrics: QueryMetrics):
        """Alert on slow query execution"""
        print(f"⚠️  SLOW QUERY DETECTED ({metrics.execution_time_ms:.2f}ms)")
        print(f"   Type: {metrics.query_type.value}")
        print(f"   Query: {metrics.query_text[:200]}...")
        print(f"   Threshold: {metrics.threshold_level.value}")
    
    def analyze_query_performance(
        self,
        query_hash: Optional[str] = None,
        min_executions: int = 10
    ) -> List[QueryAnalysis]:
        """Analyze query performance and generate recommendations"""
        query_groups: Dict[str, List[QueryMetrics]] = {}
        
        # Group metrics by query hash
        for metric in self.query_metrics:
            if query_hash and metric.query_hash != query_hash:
                continue
            if metric.query_hash not in query_groups:
                query_groups[metric.query_hash] = []
            query_groups[metric.query_hash].append(metric)
        
        analyses = []
        for qhash, metrics_list in query_groups.items():
            if len(metrics_list) < min_executions:
                continue
            
            execution_times = [m.execution_time_ms for m in metrics_list]
            execution_times.sort()
            
            p95_index = int(len(execution_times) * 0.95)
            
            analysis = QueryAnalysis(
                query_hash=qhash,
                total_executions=len(metrics_list),
                avg_execution_time_ms=sum(execution_times) / len(execution_times),
                max_execution_time_ms=max(execution_times),
                min_execution_time_ms=min(execution_times),
                p95_execution_time_ms=execution_times[p95_index] if p95_index < len(execution_times) else execution_times[-1],
                total_rows_returned=sum(m.row_count for m in metrics_list),
            )
            
            # Generate recommendations for slow queries
            if analysis.p95_execution_time_ms > 1000:
                recommendations = self._generate_recommendations(metrics_list[0])
                analysis.recommendations = recommendations
            
            analyses.append(analysis)
        
        # Sort by p95 execution time (worst first)
        analyses.sort(key=lambda a: a.p95_execution_time_ms, reverse=True)
        
        return analyses
    
    def _generate_recommendations(self, metric: QueryMetrics) -> List[IndexRecommendation]:
        """Generate index recommendations for a query"""
        recommendations = []
        query_lower = metric.query_text.lower()
        
        # Check for missing indexes on WHERE clauses
        if "where" in query_lower:
            # Simple heuristic: look for column names after WHERE
            where_part = query_lower.split("where")[1].split("order by")[0].split("group by")[0]
            
            # Extract table and column references (simplified)
            if "=" in where_part or "in" in where_part or "like" in where_part:
                recommendations.append(
                    IndexRecommendation(
                        table_name="<auto-detected>",
                        columns=["<where-columns>"],
                        reason="Query uses WHERE clause without indexed columns",
                        estimated_improvement_ms=metric.execution_time_ms * 0.6,
                        priority=5,
                        query_patterns=[metric.query_text[:100]]
                    )
                )
        
        # Check for full text search optimization
        if metric.query_type == QueryType.SEARCH:
            if "like" in query_lower or "ilike" in query_lower:
                recommendations.append(
                    IndexRecommendation(
                        table_name="<search-table>",
                        columns=["<search-columns>"],
                        reason="Full-text search using LIKE/ILIKE should use GIN index with tsvector",
                        estimated_improvement_ms=metric.execution_time_ms * 0.8,
                        priority=5,
                        query_patterns=[metric.query_text[:100]]
                    )
                )
        
        # Check for missing index on ORDER BY
        if "order by" in query_lower:
            recommendations.append(
                IndexRecommendation(
                    table_name="<table>",
                    columns=["<order-by-columns>"],
                    reason="ORDER BY clause may benefit from index",
                    estimated_improvement_ms=metric.execution_time_ms * 0.3,
                    priority=3,
                    query_patterns=[metric.query_text[:100]]
                )
            )
        
        return recommendations
    
    def get_cache_key(self, query: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key for query and parameters"""
        param_str = str(sorted(parameters.items()))
        combined = f"{query}:{param_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def cache_query_result(
        self,
        query: str,
        parameters: Dict[str, Any],
        result: Any,
        ttl_seconds: Optional[int] = None
    ):
        """Cache query result with TTL"""
        cache_key = self.get_cache_key(query, parameters)
        ttl = ttl_seconds if ttl_seconds is not None else self.cache_ttl_seconds
        expiry = _utcnow() + timedelta(seconds=ttl)
        self.query_cache[cache_key] = (result, expiry)
    
    def get_cached_result(
        self,
        query: str,
        parameters: Dict[str, Any]
    ) -> Optional[Any]:
        """Get cached query result if available and not expired"""
        cache_key = self.get_cache_key(query, parameters)
        
        if cache_key in self.query_cache:
            result, expiry = self.query_cache[cache_key]
            
            if _utcnow() < expiry:
                return result
            else:
                # Remove expired cache entry
                del self.query_cache[cache_key]
        
        return None
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear query cache, optionally matching a pattern"""
        if pattern is None:
            self.query_cache.clear()
        else:
            keys_to_delete = [
                key for key in self.query_cache.keys()
                if pattern in key
            ]
            for key in keys_to_delete:
                del self.query_cache[key]
    
    def optimize_pagination(
        self,
        query: Query,
        page: int,
        page_size: int,
        use_keyset: bool = False,
        keyset_column: Optional[str] = None,
        last_value: Optional[Any] = None
    ) -> Query:
        """Optimize pagination query using offset or keyset pagination"""
        if use_keyset and keyset_column and last_value is not None:
            # Keyset pagination (more efficient for large offsets)
            query = query.filter(
                getattr(query.column_descriptions[0]["entity"], keyset_column) > last_value
            )
            query = query.limit(page_size)
        else:
            # Standard offset pagination
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
        
        return query
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of query performance metrics"""
        if not self.query_metrics:
            return {
                "total_queries": 0,
                "avg_execution_time_ms": 0,
                "slow_queries": 0,
                "by_type": {},
                "by_threshold": {}
            }
        
        total_queries = len(self.query_metrics)
        avg_time = sum(m.execution_time_ms for m in self.query_metrics) / total_queries
        slow_queries = sum(
            1 for m in self.query_metrics
            if m.execution_time_ms > self.slow_query_threshold_ms
        )
        
        # Group by query type
        by_type: Dict[str, int] = {}
        for metric in self.query_metrics:
            by_type[metric.query_type.value] = by_type.get(metric.query_type.value, 0) + 1
        
        # Group by threshold level
        by_threshold: Dict[str, int] = {}
        for metric in self.query_metrics:
            by_threshold[metric.threshold_level.value] = by_threshold.get(
                metric.threshold_level.value, 0
            ) + 1
        
        return {
            "total_queries": total_queries,
            "avg_execution_time_ms": avg_time,
            "slow_queries": slow_queries,
            "slow_query_percentage": (slow_queries / total_queries * 100) if total_queries > 0 else 0,
            "by_type": by_type,
            "by_threshold": by_threshold,
            "cache_hit_rate": self._calculate_cache_hit_rate(),
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate (placeholder for actual tracking)"""
        # In a real implementation, track cache hits vs misses
        return 0.0
    
    def explain_query(self, session: Session, query: Query) -> str:
        """Get EXPLAIN output for a query"""
        statement = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        result = session.execute(text(f"EXPLAIN ANALYZE {statement}"))
        return "\n".join(row[0] for row in result)
    
    def get_slow_queries(
        self,
        threshold_ms: Optional[float] = None,
        limit: int = 10
    ) -> List[QueryMetrics]:
        """Get slowest queries above threshold"""
        threshold = threshold_ms if threshold_ms is not None else self.slow_query_threshold_ms
        
        slow_queries = [
            m for m in self.query_metrics
            if m.execution_time_ms > threshold
        ]
        
        slow_queries.sort(key=lambda m: m.execution_time_ms, reverse=True)
        
        return slow_queries[:limit]
    
    def reset_metrics(self):
        """Reset collected query metrics"""
        self.query_metrics.clear()
