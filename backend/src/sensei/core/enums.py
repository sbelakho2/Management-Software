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
    
    # Compatibility aliases (mapping to semantic levels)
    MAJOR = "high"
    MINOR = "low"
    
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


class EntityType(str, Enum):
    """System-wide entity types for linking, metrics, and exceptions."""
    
    # Sales & CRM
    ACCOUNT = "account"
    CONTACT = "contact"
    OPPORTUNITY = "opportunity"
    RFQ = "rfq"
    QUOTE = "quote"
    QUOTE_VERSION = "quote_version"
    QUALIFICATION = "qualification"
    
    # Production
    PRODUCTION = "production"
    WORK_ORDER = "work_order"
    WORK_CENTER = "work_center"
    STATION = "station"
    PRODUCTION_CELL = "production_cell"
    KANBAN_CARD = "kanban_card"
    
    # Quality & Andon
    ANDON = "andon"
    ANDON_EVENT = "andon_event"
    QUALITY = "quality"
    NON_CONFORMANCE = "non_conformance"
    CAPA = "capa"
    INSPECTION_PLAN = "inspection_plan"
    INSPECTION_RECORD = "inspection_record"
    
    # Management & People
    A3 = "a3"
    OBEYA = "obeya"
    OBEYA_ITEM = "obeya_item"
    TASK = "task"
    TRAINING = "training"
    USER_SKILL = "user_skill"
    LSW_ITEM = "lsw_item"
    
    # System
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    AUDIT_LOG = "audit_log"
    BACKUP = "backup"
    ATTACHMENT = "attachment"
    FEATURE_FLAG = "feature_flag"
    APPROVAL = "approval"
    COMPLIANCE = "compliance"


class JidokaAction(str, Enum):
    """Jidoka response actions."""
    
    CONTINUE = "continue"  # Continue operation
    ALERT = "alert"  # Alert operator
    SLOW_DOWN = "slow_down"  # Reduce speed
    STOP = "stop"  # Stop the line
    ESCALATE = "escalate"  # Escalate to supervisor


class MetricCategory(str, Enum):
    """SQDCP metric categories."""
    
    SAFETY = "safety"
    QUALITY = "quality"
    DELIVERY = "delivery"
    COST = "cost"
    PRODUCTIVITY = "productivity"


class DepartmentType(str, Enum):
    """Department types for cross-functional analysis."""
    
    SALES = "sales"
    PRODUCTION = "production"
    QUALITY = "quality"
    LOGISTICS = "logistics"
    ENGINEERING = "engineering"
    MAINTENANCE = "maintenance"


class QuerySecurityLevel(str, Enum):
    """Security levels for NL2SQL queries."""
    
    READ_ONLY = "read_only"
    RESTRICTED = "restricted"
    ELEVATED = "elevated"


class EmployeeRiskType(str, Enum):
    """Types of employee-related risks."""
    
    BURNOUT = "burnout"
    RETENTION = "retention"
    PERFORMANCE_DRIFT = "performance_drift"
    SKILL_GAP = "skill_gap"


class PersonaType(str, Enum):
    """User persona types for overlay."""
    
    GM = "gm"
    OPERATOR = "operator"
    SALES = "sales"
    QUALITY = "quality"
    ENGINEERING = "engineering"


class ExportFormat(str, Enum):
    """Export format options."""
    
    PDF = "pdf"
    CSV = "csv"
    PPTX = "pptx"
    JSON = "json"
