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
    
    email: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    site_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manager_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("hr_employees.id"), nullable=True)
    cost_center_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Jurisdiction - determines which social security & benefits regulations apply
    # TN=Tunisia (CNSS), MA=Morocco (CNSS), EG=Egypt (NOSI)
    jurisdiction: Mapped[str] = mapped_column(String(10), default="TN", nullable=False)
    
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


# =============================================================================
# Benefits Administration - North Africa (Tunisia, Morocco, Egypt)
# =============================================================================
# Jurisdiction Codes:
#   TN = Tunisia (CNSS - Caisse Nationale de Sécurité Sociale)
#   MA = Morocco (CNSS - Caisse Nationale de Sécurité Sociale)
#   EG = Egypt (NOSI - National Organization for Social Insurance)
# =============================================================================


class HRJurisdictionConfig(Base, TimestampMixin, AuditMixin):
    """
    Jurisdiction-specific configuration for social security and benefits.
    Stores statutory rates and limits for each country.
    """
    __tablename__ = "hr_jurisdiction_configs"

    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)  # TN, MA, EG
    country_name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)  # TND, MAD, EGP
    
    # Social security agency
    ss_agency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ss_agency_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Employee contribution rates (% of gross)
    employee_pension_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    employee_health_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    employee_unemployment_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0, nullable=False)
    employee_family_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0, nullable=False)
    
    # Employer contribution rates (% of gross)
    employer_pension_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    employer_health_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    employer_work_injury_rate_min: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0, nullable=False)
    employer_work_injury_rate_max: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0, nullable=False)
    employer_family_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0, nullable=False)
    employer_unemployment_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0, nullable=False)
    
    # Contribution caps
    min_monthly_earnings: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    max_monthly_earnings: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Statutory leave entitlements (days)
    annual_leave_days: Mapped[int] = mapped_column(Integer, default=21, nullable=False)
    maternity_leave_days: Mapped[int] = mapped_column(Integer, nullable=False)
    paternity_leave_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sick_leave_max_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Maternity benefit rate (% of salary)
    maternity_benefit_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    
    # Retirement
    retirement_age_male: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    retirement_age_female: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    min_pension_months: Mapped[int] = mapped_column(Integer, nullable=False)  # Minimum months for pension eligibility
    
    # Effective dates
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Additional jurisdiction-specific rules
    rules_json: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class HRSocialSecurityRecord(Base, TimestampMixin, AuditMixin):
    """
    Employee social security registration and contribution tracking.
    """
    __tablename__ = "hr_social_security_records"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)  # TN, MA, EG
    
    # Registration with social security agency
    ss_number: Mapped[str] = mapped_column(String(50), nullable=False)  # CNSS number / NOSI number
    registration_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Employment classification
    employment_type: Mapped[str] = mapped_column(String(50), default="private_sector", nullable=False)
    # private_sector, public_sector, agricultural, self_employed, household, fisherman
    
    # For Tunisia: agricultural vs non-agricultural
    # For Morocco: agricultural vs non-agricultural sector
    sector_type: Mapped[str] = mapped_column(String(50), default="non_agricultural", nullable=False)
    
    # For Egypt: base vs variable earnings tracking
    is_arduous_work: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dangerous_work: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Cumulative contribution tracking
    total_contribution_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_contribution_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    termination_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Voluntary coverage (for expats/foreign workers under bilateral agreements)
    is_voluntary_coverage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bilateral_agreement_country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")

    __table_args__ = (
        UniqueConstraint("employee_id", "jurisdiction", name="uq_hr_ss_records_unique"),
    )


class HRContributionPeriod(Base, TimestampMixin, AuditMixin):
    """
    Quarterly/monthly social security contribution records.
    Tunisia: Quarterly contributions
    Morocco: Monthly contributions  
    Egypt: Monthly contributions
    """
    __tablename__ = "hr_contribution_periods"

    ss_record_id: Mapped[UUID] = mapped_column(ForeignKey("hr_social_security_records.id", ondelete="CASCADE"), nullable=False)
    
    # Period
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # monthly, quarterly
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Earnings for the period
    gross_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    base_earnings: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)  # Egypt: base vs variable
    variable_earnings: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)  # Egypt
    
    # Days worked
    days_worked: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Employee contributions
    employee_pension: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    employee_health: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    employee_unemployment: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    employee_family: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    employee_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Employer contributions
    employer_pension: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    employer_health: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    employer_work_injury: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    employer_family: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    employer_unemployment: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    employer_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Payment tracking
    payment_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    ss_record: Mapped["HRSocialSecurityRecord"] = relationship("HRSocialSecurityRecord")

    __table_args__ = (
        UniqueConstraint("ss_record_id", "period_start", name="uq_hr_contribution_periods_unique"),
    )


class HRFamilyAllowance(Base, TimestampMixin, AuditMixin):
    """
    Family allowance tracking per jurisdiction.
    Tunisia: Allocation familiale - up to 3 children
    Morocco: Allocation familiale - up to 6 children  
    Egypt: Karama/Takaful programs (means-tested)
    """
    __tablename__ = "hr_family_allowances"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Number of eligible dependents
    eligible_children: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_nonworking_spouse: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Tunisia: majoration
    
    # Per-child breakdown
    dependents_json: Mapped[list] = mapped_column(JSONB, default=[], nullable=False)
    # [{name, dob, relationship, in_school, school_type, is_disabled, is_apprentice}]
    
    # Current monthly entitlement (calculated based on jurisdiction rules)
    monthly_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    spouse_supplement: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)  # Tunisia only
    
    # Morocco: nursery school fees
    nursery_fees_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nursery_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Egypt: means-tested programs
    is_means_tested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    means_test_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HRSicknessMaternityBenefit(Base, TimestampMixin, AuditMixin):
    """
    Sickness and maternity benefit claims.
    Tunisia: 66.7% daily wage (sickness), 66.7% for 30 days (maternity)
    Morocco: 66.7% for 52 weeks (sickness), 100% for 14 weeks (maternity)
    Egypt: 75-100% depending on duration (sickness), 100% for 90 days (maternity)
    """
    __tablename__ = "hr_sickness_maternity_benefits"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    
    benefit_type: Mapped[str] = mapped_column(String(20), nullable=False)  # sickness, maternity, paternity
    
    # Claim period
    claim_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    claim_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # For sickness: hospitalization status (affects waiting period and limits)
    is_hospitalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_chronic_disease: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Affects duration limits
    is_work_accident: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # No waiting period
    
    # Waiting period
    waiting_period_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Tunisia: 5 days (sickness), Morocco: 3 days, Egypt: none
    
    # Benefit calculation
    average_daily_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    benefit_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # e.g., 66.7%, 75%, 100%
    daily_benefit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_benefit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # For maternity: extension for complications
    is_extended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extension_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extension_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending, approved, rejected, paid, partially_paid
    
    # Medical certification
    medical_certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    certified_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Payment
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HRPensionEntitlement(Base, TimestampMixin, AuditMixin):
    """
    Pension/retirement benefit calculation and tracking.
    Tunisia: 40% + 0.5% per 3 months over 120 months, max 80%
    Morocco: 50% + 1% per 216 days over 3240 days, max 70%
    Egypt: 2.2% per year (2.5% arduous, 2.8% dangerous), max 80%
    """
    __tablename__ = "hr_pension_entitlements"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    ss_record_id: Mapped[UUID] = mapped_column(ForeignKey("hr_social_security_records.id"), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Eligibility
    pension_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # old_age, early, disability, survivor, partial
    
    # Contribution summary at calculation time
    total_contribution_months: Mapped[int] = mapped_column(Integer, nullable=False)
    total_contribution_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Reference earnings
    reference_period_months: Mapped[int] = mapped_column(Integer, nullable=False)  # e.g., last 120 months
    average_monthly_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # For Egypt: base vs variable
    base_earnings_average: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    variable_earnings_average: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Pension calculation
    base_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # e.g., 40%, 50%
    increment_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)  # e.g., 0.5%, 1%
    increment_periods: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    calculated_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # Total rate
    monthly_pension: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Minimums and maximums
    min_pension_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_pension_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # For early pension: reduction
    is_early_pension: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    early_reduction_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    
    # Supplements
    constant_attendance_supplement: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    # Tunisia: 20% for disability, Egypt: 20%
    
    # Dates
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="calculated", nullable=False)
    # calculated, pending_approval, approved, active, suspended

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")
    ss_record: Mapped["HRSocialSecurityRecord"] = relationship("HRSocialSecurityRecord")


class HRWorkInjuryRecord(Base, TimestampMixin, AuditMixin):
    """
    Work injury and occupational disease records.
    Tunisia: 66.7% temporary, permanent pension varies by disability %
    Morocco: 66.7% temporary, employer-liability through private carriers
    Egypt: 100% temporary, 80% permanent (total disability)
    """
    __tablename__ = "hr_work_injury_records"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Incident details
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    incident_type: Mapped[str] = mapped_column(String(30), nullable=False)  # work_injury, occupational_disease, commuting
    incident_description: Mapped[str] = mapped_column(Text, nullable=False)
    incident_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Tunisia: must report within 48 hours
    reported_date: Mapped[date] = mapped_column(Date, nullable=False)
    reported_within_deadline: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Disability assessment
    disability_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # temporary, permanent, none
    disability_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100%
    assessment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Temporary disability
    temp_disability_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    temp_disability_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    temp_disability_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=66.7, nullable=False)
    
    # Permanent disability pension (if applicable)
    perm_disability_pension: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    requires_constant_attendance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    constant_attendance_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Medical benefits
    medical_benefits_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="reported", nullable=False)
    # reported, investigating, approved, rejected, closed
    
    # Morocco: private carrier reference
    insurance_carrier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    insurance_claim_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HRUnemploymentBenefit(Base, TimestampMixin, AuditMixin):
    """
    Unemployment benefit tracking.
    Tunisia: 100% up to min wage for 12 months
    Morocco: 70% up to min wage for 6 months
    Egypt: 60% for 16-28 weeks
    """
    __tablename__ = "hr_unemployment_benefits"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Eligibility
    separation_date: Mapped[date] = mapped_column(Date, nullable=False)
    separation_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    # involuntary, economic_layoff, technological_layoff
    
    # Contribution history at separation
    contribution_months: Mapped[int] = mapped_column(Integer, nullable=False)
    contribution_months_recent: Mapped[int] = mapped_column(Integer, nullable=False)  # Last 12/36 months
    
    # Benefit calculation
    average_monthly_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    benefit_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # e.g., 60%, 70%, 100%
    monthly_benefit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Duration
    max_benefit_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    benefit_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    benefit_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    waiting_period_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    
    # Requirements
    is_registered_employment_office: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_actively_seeking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    
    # Additional benefits during unemployment
    family_allowance_continues: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    medical_benefits_continue: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HRDeathSurvivorBenefit(Base, TimestampMixin, AuditMixin):
    """
    Death grant and survivor pension tracking.
    Tunisia: Death benefit 12x monthly + survivor pension 50-100%
    Morocco: Death grant 10-12k MAD + survivor pension 50%
    Egypt: Death grant 3 months + survivor pension 80%
    """
    __tablename__ = "hr_death_survivor_benefits"

    deceased_employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id"), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Death details
    date_of_death: Mapped[date] = mapped_column(Date, nullable=False)
    cause_category: Mapped[str] = mapped_column(String(30), nullable=False)  # natural, work_injury, accident
    
    # Death grant (lump sum)
    death_grant_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    funeral_grant_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Survivor pension entitlement
    survivor_pension_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Beneficiaries
    beneficiaries_json: Mapped[list] = mapped_column(JSONB, default=[], nullable=False)
    # [{name, relationship, dob, share_percent, monthly_amount, is_eligible, eligibility_end_date}]
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    approved_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    deceased_employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HRMedicalCoverage(Base, TimestampMixin, AuditMixin):
    """
    Medical/health coverage enrollment and tracking.
    Tunisia: CNAM - Régime de Base d'Assurance-Maladie
    Morocco: AMO - Assurance Maladie Obligatoire
    Egypt: Health Insurance Organization
    """
    __tablename__ = "hr_medical_coverages"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Coverage details
    coverage_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # TN: regime_base, assistance_medicale_gratuite
    # MA: amo, ramed (social assistance)
    # EG: health_insurance_organization
    
    # Registration
    medical_card_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    registration_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Tunisia: coverage option choice
    coverage_option: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # public_facilities, private_coordinated, reimbursement
    
    # Covered dependents
    spouse_covered: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    children_covered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parents_covered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Tunisia
    
    dependents_json: Mapped[list] = mapped_column(JSONB, default=[], nullable=False)
    
    # For Morocco RAMED (means-tested)
    is_means_tested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    annual_contribution: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    termination_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")

    __table_args__ = (
        UniqueConstraint("employee_id", "jurisdiction", "coverage_type", name="uq_hr_medical_coverage_unique"),
    )


# =============================================================================
# Mobile Time Clock with Geofencing (Enhancement per HR Analysis Report)
# =============================================================================


class HRTimeClockEvent(Base, TimestampMixin, AuditMixin):
    """
    Time clock events with geolocation for mobile clock-in/out.
    """
    __tablename__ = "hr_time_clock_events"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # clock_in, clock_out, break_start, break_end
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Geolocation (for mobile time clock)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7), nullable=True)
    accuracy_meters: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Geofence validation
    geofence_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("hr_geofences.id"), nullable=True)
    is_within_geofence: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    distance_from_geofence_meters: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Device info
    device_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ios, android, web, terminal
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Station/work center (for terminal scans)
    station_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    work_center_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Verification
    verification_method: Mapped[str] = mapped_column(String(50), default="none", nullable=False)  # none, pin, biometric, photo, supervisor
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Anomaly detection
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anomaly_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")
    geofence: Mapped[Optional["HRGeofence"]] = relationship("HRGeofence")


class HRGeofence(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Geofence definition for location-based time clock validation.
    """
    __tablename__ = "hr_geofences"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Center point
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    
    # Radius in meters
    radius_meters: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Polygon definition (alternative to circle - for complex shapes)
    polygon_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # Array of [lat, lng] coordinates
    
    # Settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_clock_outside: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Allow with warning
    require_photo_outside: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Require photo if outside
    
    # Address (for display)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    time_events: Mapped[list["HRTimeClockEvent"]] = relationship("HRTimeClockEvent", back_populates="geofence")


# =============================================================================
# Extended HR Models for erpStarz Legacy Data Migration
# =============================================================================
# These models handle additional employee data from the erpStarz Symfony/PHP
# legacy system at /home/aaron/IdeaProjects/erpStarz/src/Entity/


class HREmployeeContract(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Employment contract tracking.
    Maps to erpStarz: employee_contract table
    """
    __tablename__ = "hr_employee_contracts"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    # Contract details
    contract_number: Mapped[str] = mapped_column(String(100), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CDI, CDD, interim, apprentice
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    ends_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # Null for CDI (permanent)
    
    # Employment terms
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    weekly_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    trial_period_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trial_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    # active, expired, terminated, renewed
    
    # Renewal tracking
    renewed_from_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("hr_employee_contracts.id"), nullable=True)
    
    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")
    renewed_from: Mapped[Optional["HREmployeeContract"]] = relationship("HREmployeeContract", remote_side="HREmployeeContract.id")


class HREmployeeBankAccount(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Employee bank account for salary payments.
    Maps to erpStarz: employee_bank_acc table
    """
    __tablename__ = "hr_employee_bank_accounts"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rib: Mapped[str] = mapped_column(String(24), nullable=False)  # Tunisian RIB (20-24 chars)
    
    # IBAN for international transfers
    iban: Mapped[Optional[str]] = mapped_column(String(34), nullable=True)
    bic_swift: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    
    # Account details
    account_holder_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    branch_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")

    __table_args__ = (
        UniqueConstraint("employee_id", "rib", name="uq_hr_employee_bank_rib"),
    )


class HREmployeeSalary(Base, TimestampMixin, AuditMixin):
    """
    Monthly salary/payroll record.
    Maps to erpStarz: employee_salary table
    """
    __tablename__ = "hr_employee_salaries"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    # Pay period
    payroll_month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    payroll_year: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Earnings
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    overtime_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    bonuses: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    allowances: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    gross_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Deductions
    cnss_employee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)  # Employee SS contribution
    income_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    advances_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Employer contributions (not deducted from employee)
    cnss_employer: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    
    # Payment status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending, validated, paid
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")

    __table_args__ = (
        UniqueConstraint("employee_id", "payroll_year", "payroll_month", name="uq_hr_salary_period"),
    )


class HREmployeeAbsence(Base, TimestampMixin, AuditMixin):
    """
    Absence tracking (unplanned absences, tardiness).
    Maps to erpStarz: employee_absence table
    """
    __tablename__ = "hr_employee_absences"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    absence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # unexcused, excused, late, early_departure, unauthorized_leave
    
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_excused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Duration
    hours_missed: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    
    # Disciplinary impact
    status: Mapped[str] = mapped_column(String(20), default="recorded", nullable=False)
    # recorded, reviewed, excused, disciplinary_action
    
    reviewed_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HREmployeeSuspension(Base, TimestampMixin, AuditMixin):
    """
    Employment suspension tracking.
    Maps to erpStarz: employee_suspension table
    """
    __tablename__ = "hr_employee_suspensions"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    suspension_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # disciplinary, administrative, medical, pending_investigation
    
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    # active, ended, converted_to_termination
    
    # Linked HR Case (if disciplinary)
    hr_case_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("hr_cases.id"), nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HREmployeeAdvance(Base, TimestampMixin, AuditMixin):
    """
    Salary advance/loan tracking.
    Maps to erpStarz: employee_advance table
    """
    __tablename__ = "hr_employee_advances"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    request_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Approval
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending, approved, rejected, disbursed, repaid
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Repayment
    installments: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # Number of salary deductions
    monthly_deduction: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    remaining_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    disbursed_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HREmployeeDiploma(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Employee education/diploma records.
    Maps to erpStarz: employee_diploma table
    """
    __tablename__ = "hr_employee_diplomas"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Diploma name
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # baccalaureate, license, master, doctorate, professional_cert, trade_cert
    
    institution: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    obtained_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Document storage
    document_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HREmployeeAddress(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Employee addresses (home, mailing, emergency).
    Maps to erpStarz: employee_address table
    """
    __tablename__ = "hr_employee_addresses"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    address_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # home, mailing, emergency_contact
    
    street_address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state_province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(50), default="Tunisia", nullable=False)
    
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HREmployeePermission(Base, TimestampMixin, AuditMixin):
    """
    Short-term permission/authorization to leave work.
    Maps to erpStarz: employee_permission table
    """
    __tablename__ = "hr_employee_permissions"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hours_count: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    
    permission_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # medical_appointment, administrative, personal, family_emergency
    
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Approval
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending, approved, rejected
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HREmployeeDocument(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Employee document storage.
    Maps to erpStarz: employee_files table
    """
    __tablename__ = "hr_employee_documents"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # contract, id_card, diploma, medical_cert, training_cert, other
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Metadata
    uploaded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Access control
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HREmployeeHistory(Base, TimestampMixin, AuditMixin):
    """
    Employment history (position changes, promotions, transfers).
    Maps to erpStarz: employee_history table
    """
    __tablename__ = "hr_employee_histories"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # hire, promotion, transfer, demotion, salary_change, department_change, title_change
    
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Before/after values
    previous_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Details
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Authorization
    authorized_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HREmployeeNote(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    General notes about an employee.
    Maps to erpStarz: employee_note table
    """
    __tablename__ = "hr_employee_notes"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    note_type: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    # general, performance, disciplinary, medical, personal
    
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Visibility
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visible_to_employee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")


class HRPublicHoliday(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Public holiday calendar for jurisdictions.
    Maps to erpStarz: employee_public_holiday table (enhanced for multi-jurisdiction)
    """
    __tablename__ = "hr_public_holidays"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Jurisdiction-specific (TN, MA, EG)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # Holiday type
    holiday_type: Mapped[str] = mapped_column(String(50), default="national", nullable=False)
    # national, religious, regional, company
    
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_working_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Some holidays require work
    
    # Optional: company-specific
    site_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("jurisdiction", "holiday_date", "name", name="uq_hr_public_holiday"),
    )


class HRLeaveBalance(Base, TimestampMixin, AuditMixin):
    """
    Leave balance tracking per employee per leave type.
    Complements HRLeaveRequest for leave accrual management.
    """
    __tablename__ = "hr_leave_balances"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    leave_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # vacation, sick, personal, maternity, paternity, unpaid, etc.
    
    # Annual cycle
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Balance tracking
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    accrued: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    used: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    pending: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)  # Pending approval
    carried_over: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, nullable=False)  # From previous year
    
    # Calculated current balance
    @property
    def available(self) -> Decimal:
        return self.initial_balance + self.accrued + self.carried_over - self.used - self.pending

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")

    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type", "year", name="uq_hr_leave_balance"),
    )


class HRCase(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    HR Case management for disciplinary, grievance, investigation.
    Referenced by HREmployeeSuspension.
    """
    __tablename__ = "hr_cases"

    employee_id: Mapped[UUID] = mapped_column(ForeignKey("hr_employees.id", ondelete="CASCADE"), nullable=False)
    
    case_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    case_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # disciplinary, grievance, harassment, discrimination, investigation, performance
    
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Case handling
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    # open, investigating, pending_hearing, resolved, closed, appealed
    
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    # low, normal, high, critical
    
    assigned_to_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    opened_date: Mapped[date] = mapped_column(Date, nullable=False)
    closed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Outcome
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # no_action, verbal_warning, written_warning, suspension, termination, resolved
    
    # Confidentiality
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee: Mapped["EmployeeProfile"] = relationship("EmployeeProfile")
    suspensions: Mapped[list["HREmployeeSuspension"]] = relationship("HREmployeeSuspension", back_populates="hr_case", foreign_keys="HREmployeeSuspension.hr_case_id")


# Update HREmployeeSuspension relationship
HREmployeeSuspension.hr_case = relationship("HRCase", back_populates="suspensions", foreign_keys=[HREmployeeSuspension.hr_case_id])
