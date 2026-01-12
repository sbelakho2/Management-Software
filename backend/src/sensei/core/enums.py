"""
Sensei OS Core Enums

Centralized enum definitions to ensure system-wide consistency
and reduce duplication across models, services, and APIs.
"""

from enum import Enum


class Severity(str, Enum):
    """Unified severity levels for alerts, exceptions, and andons."""
    
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"          # Urgent action required
    MEDIUM = "medium"      # Standard attention
    LOW = "low"            # Minor issue
    INFO = "info"          # Informational only
    
    # Color-coded aliases for Andon compatibility
    RED = "critical"
    YELLOW = "high"
    BLUE = "low"


class WorkflowStatus(str, Enum):
    """Standardized workflow statuses for entities (Tasks, Exceptions, etc.)."""
    
    OPEN = "open"
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"
    BLOCKED = "blocked"


class MetricStatus(str, Enum):
    """Status for KPI and Obeya metrics (SQDCP)."""
    
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    
    # Granular KPI statuses
    ON_TARGET = "green"
    WITHIN_TOLERANCE = "yellow"
    OFF_TARGET = "red"
    CRITICAL = "critical"
    
    NO_DATA = "no_data"


class ComparisonOperator(str, Enum):
    """Operators for filters and conditions."""
    
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    IS_NULL = "is_null"
