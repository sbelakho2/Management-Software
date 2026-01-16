from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    Boolean,
    UniqueConstraint,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from sensei.models.user import User

class EmployeeProfile(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Central hub for employee data.
    """
    __tablename__ = "hr_employees"

    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    site_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manager_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("hr_employees.id"), nullable=True)
    cost_center_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, onboarding, offboarding, terminated
    
    hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    termination_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    manager: Mapped[Optional["EmployeeProfile"]] = relationship("EmployeeProfile", remote_side="EmployeeProfile.id")
    checklists: Mapped[list["HRChecklist"]] = relationship("HRChecklist", back_populates="employee")
    appraisals: Mapped[list["HRAppraisal"]] = relationship("HRAppraisal", back_populates="employee")


class HRChecklist(Base, TimestampMixin, AuditMixin):
    """
    Onboarding/Offboarding checklists.
    """
    __tablename__ = "hr_checklists"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    checklist_type: Mapped[str] = mapped_column(String(20), nullable=False) # onboarding, offboarding
    status: Mapped[str] = mapped_column(String(20), default="not_started", nullable=False) # not_started, in_progress, completed
    
    items_json: Mapped[list] = mapped_column(JSONB, default=[], nullable=False)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile", back_populates="checklists")


class HRJobOpening(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Job opening for recruitment.
    """
    __tablename__ = "hr_job_openings"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False) # open, filled, cancelled
    
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hiring_manager_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    hiring_manager: Mapped["User"] = relationship("User", foreign_keys=[hiring_manager_id])
    applications: Mapped[list["HRJobApplication"]] = relationship("HRJobApplication", back_populates="job_opening")


class HRJobApplication(Base, TimestampMixin, AuditMixin):
    """
    Job application record.
    """
    __tablename__ = "hr_job_applications"

    job_opening_id: Mapped[UUID] = mapped_column(ForeignKey("hr_job_openings.id"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    resume_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="received", nullable=False) # received, screening, interview, offer, hired, rejected
    
    job_opening: Mapped["HRJobOpening"] = relationship("HRJobOpening", back_populates="applications")


class HRAppraisal(Base, TimestampMixin, AuditMixin):
    """
    Performance appraisal record.
    """
    __tablename__ = "hr_appraisals"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id"), nullable=False)
    appraiser_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False) # draft, submitted, completed
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile", back_populates="appraisals")
    appraiser: Mapped["User"] = relationship("User", foreign_keys=[appraiser_id])


class HRLeaveRequest(Base, TimestampMixin, AuditMixin):
    """
    Leave/Time-off request.
    """
    __tablename__ = "hr_leave_requests"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id"), nullable=False)
    leave_type: Mapped[str] = mapped_column(String(50), nullable=False) # vacation, sick, personal, etc.
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False) # pending, approved, rejected
    
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
