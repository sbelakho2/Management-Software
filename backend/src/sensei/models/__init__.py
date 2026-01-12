"""
Sensei OS Database Models.

All SQLAlchemy ORM models for the application.
"""

from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin, StatusMixin
from sensei.models.user import User, Role, Permission, UserRole, RolePermission
from sensei.models.account import Account, Contact, AccountContact
from sensei.models.opportunity import Opportunity, OpportunityNote
from sensei.models.rfq import RFQ, RFQQuestion, RFQAttachment
from sensei.models.qualification import (
    Qualification,
    QualificationScore,
    QualificationCriterion,
)
from sensei.models.quote import (
    Quote,
    QuoteVersion,
    QuoteLineItem,
    SupplierQuote,
    SupplierQuoteItem,
)
from sensei.models.ctq import CTQ, CTQMeasurement
from sensei.models.risk import Risk, RiskMitigation
from sensei.models.obeya import ObeyaItem, ObeyaComment
from sensei.models.a3 import A3, A3Section
from sensei.models.task import Task, TaskComment, Notification
from sensei.models.project_management import (
    Project,
    ProjectMember,
    Epic,
    UserStory,
    Subtask,
    StoryComment,
    StoryHistory,
    Sprint,
    Issue,
    IssueComment,
    Milestone,
    WikiPage,
    ProjectActivity,
    BoardView,
)
from sensei.models.learning import (
    LearningUnit,
    LearningModule,
    UserLearningProgress,
    LearningAssessment,
)
from sensei.models.attachment import Attachment, AttachmentVersion
from sensei.models.audit_log import AuditLog
from sensei.models.data_lineage import DataLineageLink
from sensei.models.reasoning_trace import ReasoningTrace

# Phase 3: Production & TPS Execution Models
from sensei.models.work_center import (
    WorkCenter,
    WorkCenterStatus,
    Station,
    StationType,
    StationStatus,
)
from sensei.models.product import (
    Product,
    ProductStatus,
    UnitOfMeasure,
    BOMItem,
    Routing,
)
from sensei.models.work_order import (
    WorkOrder,
    WorkOrderStatus,
    WorkOrderPriority,
    HoldReason,
    WorkOrderOperation,
    OperationStatus,
)
from sensei.models.standard_work import (
    StandardWork,
    StandardWorkStatus,
    StandardWorkType,
    StandardWorkVersion,
)
from sensei.models.training import (
    Skill,
    SkillCategory,
    SkillRequirement,
    Training,
    TrainingType,
    TrainingStatus,
    TrainingParticipant,
    EnrollmentStatus,
    AttendanceStatus,
    UserSkill,
    CertificationStatus,
)
from sensei.models.andon import (
    AndonEvent,
    AndonType,
    AndonSeverity,
    AndonStatus,
    EscalationLevel,
    ResponseStatus,
    AndonEscalation,
    AndonRecurrencePattern,
)
from sensei.models.kanban import (
    KanbanBoard,
    BoardType,
    KanbanCard,
    CardType,
    CardStatus,
    CardPriority,
    KanbanCardHistory,
    KanbanMetrics,
)
from sensei.models.quality import (
    NonConformance,
    NCType,
    NCSource,
    NCSeverity,
    NCStatus,
    NCDisposition,
    RootCauseCategory,
    CAPA,
    CAPAType,
    CAPASourceType,
    CAPAStatus,
    CAPAPriority,
    VerificationStatus,
    EffectivenessStatus,
    CAPAAction,
    CAPAActionType,
    CAPAActionStatus,
    InspectionPlan,
    InspectionType,
    InspectionRecord,
    InspectionResult,
)
from sensei.models.production import (
    ProductionCell,
    CellType,
    CellStatus,
    CellPerformance,
    ShiftNumber,
)
from sensei.models.maintenance import ConditionReading, MaintenanceRecord

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "AuditMixin",
    "SoftDeleteMixin",
    "StatusMixin",
    # User & Auth
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    # Account & Contact
    "Account",
    "Contact",
    "AccountContact",
    # Opportunity
    "Opportunity",
    "OpportunityNote",
    # RFQ
    "RFQ",
    "RFQQuestion",
    "RFQAttachment",
    # Qualification
    "Qualification",
    "QualificationScore",
    "QualificationCriterion",
    # Quote
    "Quote",
    "QuoteVersion",
    "QuoteLineItem",
    "SupplierQuote",
    "SupplierQuoteItem",
    # CTQ
    "CTQ",
    "CTQMeasurement",
    # Risk
    "Risk",
    "RiskMitigation",
    # Obeya
    "ObeyaItem",
    "ObeyaComment",
    # A3
    "A3",
    "A3Section",
    # Task & Notification
    "Task",
    "TaskComment",
    "Notification",
    # Learning
    "LearningUnit",
    "LearningModule",
    "UserLearningProgress",
    "LearningAssessment",
    # Attachment
    "Attachment",
    "AttachmentVersion",
    # Audit
    "AuditLog",
    "DataLineageLink",
    # Phase 3: Work Center & Station
    "WorkCenter",
    "WorkCenterStatus",
    "Station",
    "StationType",
    "StationStatus",
    # Phase 3: Product & Routing
    "Product",
    "ProductStatus",
    "UnitOfMeasure",
    "BOMItem",
    "Routing",
    # Phase 3: Work Order
    "WorkOrder",
    "WorkOrderStatus",
    "WorkOrderPriority",
    "HoldReason",
    "WorkOrderOperation",
    "OperationStatus",
    # Phase 3: Standard Work
    "StandardWork",
    "StandardWorkStatus",
    "StandardWorkType",
    "StandardWorkVersion",
    # Phase 3: Training & Skills
    "Skill",
    "SkillCategory",
    "SkillRequirement",
    "Training",
    "TrainingType",
    "TrainingStatus",
    "TrainingParticipant",
    "EnrollmentStatus",
    "AttendanceStatus",
    "UserSkill",
    "CertificationStatus",
    # Phase 3: Andon
    "AndonEvent",
    "AndonType",
    "AndonSeverity",
    "AndonStatus",
    "EscalationLevel",
    "ResponseStatus",
    "AndonEscalation",
    "AndonRecurrencePattern",
    # Phase 3: Kanban
    "KanbanBoard",
    "BoardType",
    "KanbanCard",
    "CardType",
    "CardStatus",
    "CardPriority",
    "KanbanCardHistory",
    "KanbanMetrics",
    # Phase 3: Quality (NC/CAPA)
    "NonConformance",
    "NCType",
    "NCSource",
    "NCSeverity",
    "NCStatus",
    "NCDisposition",
    "RootCauseCategory",
    "CAPA",
    "CAPAType",
    "CAPASourceType",
    "CAPAStatus",
    "CAPAPriority",
    "VerificationStatus",
    "EffectivenessStatus",
    "CAPAAction",
    "CAPAActionType",
    "CAPAActionStatus",
    "InspectionPlan",
    "InspectionType",
    "InspectionRecord",
    "InspectionResult",
    # Phase 3: Production Cell
    "ProductionCell",
    "CellType",
    "CellStatus",
    "CellPerformance",
    "ShiftNumber",
    # Maintenance
    "ConditionReading",
    "MaintenanceRecord",
]
