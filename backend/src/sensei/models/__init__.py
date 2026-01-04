"""
Sensei OS Database Models.

All SQLAlchemy ORM models for the application.
"""

from sensei.models.base import Base, TimestampMixin, AuditMixin
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
from sensei.models.learning import (
    LearningUnit,
    LearningModule,
    UserLearningProgress,
    LearningAssessment,
)
from sensei.models.attachment import Attachment, AttachmentVersion
from sensei.models.audit_log import AuditLog

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "AuditMixin",
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
]
