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
from sensei.models.quoting_helper import (
    WorkPacket,
    PCBSpec,
    RFQPackageVersion,
    RateCard,
    QuoteActual,
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
    ProjectMilestone,
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
from sensei.models.admin import AdminGate, ApprovalWorkflow, Template, LearningCadence, FeatureFlag
from sensei.models.exception import ExceptionRecord
from sensei.models.tps import (
    PDCACycleRecord, 
    KataSessionRecord, 
    MudaDetectionRecord, 
    UserTPSStats,
    TPSAndonEventRecord,
    JidokaResponseRecord,
)
from sensei.models.cognitive_obeya import (
    MetricRecord,
    CausalLinkRecord,
    TrendWarningRecord,
    SiloAlertRecord,
    ResourceRebalanceRecord,
    HeijunkaSuggestionRecord,
)
from sensei.models.strategic import (
    NL2SQLQueryRecord,
    EmployeeRiskAssessmentRecord,
    ScenarioResultRecord,
)
from sensei.models.strategic_v2 import (
    InspectionFeedback,
    TrainingSample,
    AgentAnalysisRecord,
    ConsensusDebateRecord,
    KnowledgeSourceRecord,
    SemanticChunkRecord,
    SiteMaturityRecord,
    LevelUpChecklistRecord,
    UIActionAuditRecord,
    LessonDeliveryRecord,
    StandardWorkEvolutionRecord,
    KnowledgePackRecord,
    KnowledgePackSourceRecord,
)

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
from sensei.models.pii import (
    PIIField,
    DataSubject,
    Consent,
    PIIAccessLog,
    DeletionRequest,
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
    ShiftHandoverNote,
    GlobalPulse,
    HandoverSeverity,
)
from sensei.models.finance import (
    GLAccount,
    OpeningBalance,
    AccountingPeriod,
    JournalEntry,
    JournalLine,
    FXRate,
    CurrencySetting,
    StandardCostRecord,
    WorkOrderCostRollup,
    TaxJurisdiction,
    TaxRate,
    TaxTransaction,
)
from sensei.models.site import Site
from sensei.models.accounts_payable import (
    PurchaseRequisition,
    PRLine,
    PurchaseOrder,
    POLine,
    GoodsReceipt,
    ReceiptLine,
    SupplierInvoice,
    SupplierInvoiceLine,
    PaymentRun,
    Payment,
    PaymentInvoiceLink,
)
from sensei.models.accounts_receivable import (
    CustomerCreditProfile,
    SalesOrder,
    SalesOrderLine,
    CustomerInvoice,
    CustomerInvoiceLine,
    PaymentReceipt,
    PaymentAllocation,
    InvoiceDispute,
)
from sensei.models.maintenance import (
    Asset,
    PMSchedule,
    MaintenanceWorkOrder,
    MaintenanceLaborEntry,
    MaintenancePartUsed,
    SparePart,
    DowntimeEvent,
    FailureRecord,
    ConditionReading,
    LOTOProcedure,
    LOTOEnergySource,
    LOTOLock,
    ToolItem,
    ToolCheckout,
    AssetWarranty,
    WarrantyClaim,
    FieldReturn,
    MaintenanceBudget,
)
from sensei.models.quality_qms import (
    QMSDocument,
    QMSDocumentRevision,
    ExternalDocument,
    SupplierScorecard,
    SCAR,
    QualityAudit,
    AuditFinding,
    Gauge,
    CalibrationEvent,
    CustomerComplaint,
    MSAStudy,
    MSAMeasurement,
    MSAResult,
    ProcessCapabilityStudy,
    ProcessCapabilityMeasurement,
    ProcessCapabilityResult,
    CustomerSurvey,
    CustomerSurveyResponse,
    FirstArticleInspection,
    FAICharacteristic,
    SelfInspection,
    SelfInspectionCheck,
    LabTestMethod,
    LabSample,
    LabTestRun,
    AQLSamplingPlan,
    AQLLotInspection,
    TraceabilityMatrix,
    TraceabilityLink,
    ChangePointStudy,
    ChangePointObservation,
    ChangePointEvent,
    ManagementReview,
    ManagementReviewAction,
)
from sensei.models.mrp import BOMComponent, MRPDemand, MRPSuggestion, MRPRun, MPSPlan, MPSPlanLine
from sensei.models.hr import (
    EmployeeProfile,
    HRChecklist,
    HRJobOpening,
    HRJobApplication,
    HRAppraisal,
    HRLeaveRequest,
)
from sensei.models.inventory import Warehouse, Location, InventoryLevel, StockMove, ValuationLayer
from sensei.models.migration import ImportBatch
from sensei.models.analytics import (
    DailySnapshot,
    DimensionSchema as AnalyticsDimensionSchema,
    FactSchema as AnalyticsFactSchema,
    ExportedRecord as AnalyticsExportedRecord,
)
from sensei.models.business_continuity import (
    QueuedEvent,
    CriticalityRule,
    RTORPOConfig,
    RestoreRehearsal,
)
from sensei.models.ot_network import (
    NetworkZone,
    ZoneViolation,
    EdgeCertificate,
    ZoneType,
    CertificateStatus,
    ZoneViolationSeverity,
)
from sensei.models.segment import (
    Segment,
    SegmentShare,
    SegmentUsage,
    SegmentModule,
    SegmentVisibility,
)

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
    "KnowledgePackRecord",
    "KnowledgePackSourceRecord",
    # Attachment
    "Attachment",
    "AttachmentVersion",
    # Audit
    "AuditLog",
    "DataLineageLink",
    "AdminGate",
    "ApprovalWorkflow",
    "Template",
    "LearningCadence",
    "FeatureFlag",
    "ExceptionRecord",
    "PDCACycleRecord",
    "KataSessionRecord",
    "MudaDetectionRecord",
    "UserTPSStats",
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
    "ShiftHandoverNote",
    "GlobalPulse",
    "HandoverSeverity",
    # Maintenance
    "ConditionReading",
    "MaintenanceRecord",
    # Finance
    "GLAccount",
    "OpeningBalance",
    # Inventory
    "InventoryLevel",
    # Migration
    "ImportBatch",
    # Analytics
    "DailySnapshot",
    "AnalyticsDimensionSchema",
    "AnalyticsFactSchema",
    "AnalyticsExportedRecord",
    # Business Continuity
    "QueuedEvent",
    "CriticalityRule",
    "RTORPOConfig",
    "RestoreRehearsal",
    # OT Network Safety
    "NetworkZone",
    "ZoneViolation",
    "EdgeCertificate",
    "ZoneType",
    "CertificateStatus",
    "ZoneViolationSeverity",
    # Segment Views
    "Segment",
    "SegmentShare",
    "SegmentUsage",
    "SegmentModule",
    "SegmentVisibility",
]
