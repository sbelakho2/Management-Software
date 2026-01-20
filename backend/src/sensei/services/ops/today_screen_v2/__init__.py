"""
Today Screen Service - Modularized.

Aggregates data for the Manager GPS "Today" screen, including:
- Top 3 Priorities (forced selection)
- Top Risks (Delivery/Quality/Cash/Reputation)
- Commitments (due quotes, calls, follow-ups)
- Abnormalities (late quotes, stalled RFQs, missing CTQs)
- Micro-Drill recall questions
- LSW Checklist status
- Quick metrics and KPIs
- Shop Floor data (Phase 3)
"""

from sensei.services.ops.today_screen_v2.base import (
    InMemoryRedis,
    UUIDEncoder,
    BaseRedisStore,
)
from sensei.services.ops.today_screen_v2.priorities import PriorityManager
from sensei.services.ops.today_screen_v2.risks import RiskManager
from sensei.services.ops.today_screen_v2.commitments import CommitmentManager
from sensei.services.ops.today_screen_v2.abnormalities import AbnormalityManager
from sensei.services.ops.today_screen_v2.drills import MicroDrillManager
from sensei.services.ops.today_screen_v2.shop_floor import ShopFloorManager
from sensei.services.ops.today_screen_v2.service import (
    AsyncTodayScreenService,
    TodayScreenService,
    get_today_screen_service,
    reset_today_screen_service,
)

# Re-export models for backward compatibility
from sensei.services.ops.today_screen_models import (
    RiskCategory,
    AbnormalityType,
    CommitmentType,
    PriorityLevel,
    LSWChecklistStatus,
    ShopFloorAreaType,
    ShopFloorAlertSeverity,
    Priority,
    Risk,
    Commitment,
    Abnormality,
    MicroDrill,
    LSWChecklistSummary,
    QuickMetric,
    TodayScreenData,
    WorkOrderAtRisk,
    CriticalAndon,
    StationEfficiency,
    CellOEE,
    KanbanAlert,
    ExpiringCertification,
    WIPViolation,
    CAPAVerification,
    ScheduledTraining,
    ShopFloorSummary,
)

__all__ = [
    # Base
    "InMemoryRedis",
    "UUIDEncoder",
    "BaseRedisStore",
    # Managers
    "PriorityManager",
    "RiskManager",
    "CommitmentManager",
    "AbnormalityManager",
    "MicroDrillManager",
    "ShopFloorManager",
    # Service
    "AsyncTodayScreenService",
    "TodayScreenService",
    "get_today_screen_service",
    "reset_today_screen_service",
    # Models (for backward compatibility)
    "RiskCategory",
    "AbnormalityType",
    "CommitmentType",
    "PriorityLevel",
    "LSWChecklistStatus",
    "ShopFloorAreaType",
    "ShopFloorAlertSeverity",
    "Priority",
    "Risk",
    "Commitment",
    "Abnormality",
    "MicroDrill",
    "LSWChecklistSummary",
    "QuickMetric",
    "TodayScreenData",
    "WorkOrderAtRisk",
    "CriticalAndon",
    "StationEfficiency",
    "CellOEE",
    "KanbanAlert",
    "ExpiringCertification",
    "WIPViolation",
    "CAPAVerification",
    "ScheduledTraining",
    "ShopFloorSummary",
]
