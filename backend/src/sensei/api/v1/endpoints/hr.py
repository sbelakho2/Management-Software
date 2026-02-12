"""
HR (Human Resources) API Endpoints.
Aggregates employee data, certifications, and headcount.
"""

from datetime import date, timedelta
from typing import Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from sensei.api import deps
from sensei.api.deps import DBSession, CurrentUser
from sensei.core.config import settings
from sensei.models.user import User, Role
from sensei.models.hr import EmployeeProfile, HRJobOpening, HRLeaveRequest, HRJobApplication, HRAppraisal
from sensei.models.learning import UserLearningProgress, LearningModule
from sensei.models.training import UserSkill, CertificationStatus, Skill
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.services.core.common_thread import get_common_thread_service

import logging

logger = logging.getLogger(__name__)

AllowHRModule = deps.require_role("hr", "supervisor", "gm", "exec")  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[Depends(deps.RoleChecker(["hr", "supervisor", "gm", "exec"]))]
)

class HRStats(BaseModel):
    total_employees: int
    open_positions: int
    pending_time_off: int
    expiring_certifications: int
    new_hires_this_month: int
    turnover_rate: float

class DepartmentHeadcount(BaseModel):
    name: str
    count: int
    percentage: float

class ExpiringCert(BaseModel):
    id: str
    employee: str
    cert: str
    expires: str
    priority: str

@router.get("/stats", response_model=HRStats)
async def get_hr_stats(db: DBSession, current_user: CurrentUser) -> Any:
    from sensei.api import deps
    """Get aggregated HR statistics. Requires authentication."""
    # Aggregated stats from DB
    total_employees = await db.scalar(select(func.count(EmployeeProfile.id)))
    AllowHRModule = deps.require_role("hr", "supervisor", "gm", "exec")  # type: ignore[valid-type]
    open_positions = await db.scalar(select(func.count(HRJobOpening.id)).where(HRJobOpening.status == "open"))
    pending_time_off = await db.scalar(select(func.count(HRLeaveRequest.id)).where(HRLeaveRequest.status == "pending"))
    today = date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

    expiring_certifications = await db.scalar(
        select(func.count(UserSkill.id)).where(
            UserSkill.certification_status == CertificationStatus.CERTIFIED,
            UserSkill.expiration_date.is_not(None),
            UserSkill.expiration_date >= today,
            UserSkill.expiration_date <= today + timedelta(days=30),
        )
    ) or 0

    new_hires_this_month = await db.scalar(
        select(func.count(EmployeeProfile.id)).where(
            EmployeeProfile.hire_date.is_not(None),
            EmployeeProfile.hire_date >= month_start,
            EmployeeProfile.hire_date < next_month,
        )
    ) or 0

    terminated_last_year = await db.scalar(
        select(func.count(EmployeeProfile.id)).where(
            EmployeeProfile.termination_date.is_not(None),
            EmployeeProfile.termination_date >= (today - timedelta(days=365)),
        )
    ) or 0

    turnover_rate = 0.0
    if total_employees:
        turnover_rate = (terminated_last_year / total_employees) * 100

    return HRStats(
        total_employees=total_employees or 0,
        open_positions=open_positions or 0,
        pending_time_off=pending_time_off or 0,
        expiring_certifications=expiring_certifications,
        new_hires_this_month=new_hires_this_month,
        turnover_rate=round(turnover_rate, 2),
    )

@router.get("/headcount", response_model=List[DepartmentHeadcount])
async def get_headcount(db: DBSession, current_user: CurrentUser) -> Any:
    """Get headcount by department. Requires authentication."""
    result = await db.execute(
        select(EmployeeProfile.department, func.count(EmployeeProfile.id))
        .group_by(EmployeeProfile.department)
    )
    counts = result.all()
    total = sum(c[1] for c in counts)
    
    return [
        {"name": c[0] or "Unknown", "count": c[1], "percentage": (c[1] / total * 100) if total > 0 else 0}
        for c in counts
    ]

@router.get("/job-openings", response_model=List[dict])
async def list_job_openings(db: DBSession, current_user: CurrentUser) -> Any:
    """List all job openings. Requires authentication."""
    result = await db.execute(select(HRJobOpening))
    openings = result.scalars().all()
    return [o.to_dict() for o in openings]

@router.get("/applications", response_model=List[dict])
async def list_job_applications(db: DBSession, current_user: CurrentUser) -> Any:
    """List all job applications. Requires authentication."""
    result = await db.execute(select(HRJobApplication))
    apps = result.scalars().all()
    return [a.to_dict() for a in apps]

@router.get("/appraisals", response_model=List[dict])
async def list_appraisals(db: DBSession, current_user: CurrentUser) -> Any:
    """List all performance appraisals. Requires authentication."""
    result = await db.execute(select(HRAppraisal))
    appraisals = result.scalars().all()
    return [a.to_dict() for a in appraisals]

@router.get("/leave-requests", response_model=List[dict])
async def list_leave_requests(db: DBSession, current_user: CurrentUser) -> Any:
    """List all leave requests. Requires authentication."""
    result = await db.execute(select(HRLeaveRequest))
    requests = result.scalars().all()
    return [r.to_dict() for r in requests]

@router.get("/expiring-certs", response_model=List[ExpiringCert])
async def get_expiring_certs(db: DBSession, current_user: CurrentUser) -> Any:
    """Get certifications expiring soon. Requires authentication."""
    today = date.today()
    cutoff = today + timedelta(days=30)

    result = await db.execute(
        select(
            UserSkill.id,
            UserSkill.expiration_date,
            Skill.name,
            User.first_name,
            User.last_name,
            EmployeeProfile.first_name,
            EmployeeProfile.last_name,
        )
        .join(Skill, Skill.id == UserSkill.skill_id)
        .join(User, User.id == UserSkill.user_id)
        .outerjoin(EmployeeProfile, EmployeeProfile.user_id == User.id)
        .where(
            UserSkill.certification_status == CertificationStatus.CERTIFIED,
            UserSkill.expiration_date.is_not(None),
            UserSkill.expiration_date >= today,
            UserSkill.expiration_date <= cutoff,
        )
        .order_by(UserSkill.expiration_date.asc())
        .limit(settings.AUDIT_LOG_QUERY_LIMIT)
    )

    rows = result.all()

    def _priority(days_left: int) -> str:
        if days_left <= 7:
            return "high"
        if days_left <= 14:
            return "medium"
        return "low"

    response: list[ExpiringCert] = []
    for (
        user_skill_id,
        expiration_date,
        skill_name,
        user_first,
        user_last,
        employee_first,
        employee_last,
    ) in rows:
        if expiration_date is None:
            continue
        days_left = (expiration_date - today).days
        display_expires = "today" if days_left == 0 else f"{days_left} days"
        employee_name = (
            f"{employee_first} {employee_last}".strip()
            if employee_first and employee_last
            else f"{user_first} {user_last}".strip()
        )
        response.append(
            ExpiringCert(
                id=str(user_skill_id),
                employee=employee_name or "Unknown",
                cert=skill_name,
                expires=display_expires,
                priority=_priority(max(days_left, 0)),
            )
        )

    return response


# =============================================================================
# Employee Self-Service Endpoints (Enhancement per HR Analysis Report)
# =============================================================================

# Self-service router - any authenticated user can access their own data
self_service_router = APIRouter(prefix="/self-service", tags=["HR Self-Service"])


class SelfServiceProfile(BaseModel):
    """Employee's own profile view."""
    id: str
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    department: str | None
    job_title: str | None
    site_id: str | None
    hire_date: date | None
    status: str


class SelfServiceLeaveBalance(BaseModel):
    """Leave balance summary for self-service."""
    leave_type: str
    available: float
    used: float
    pending: float
    accrued: float


class SelfServiceLeaveRequest(BaseModel):
    """Leave request for submission."""
    leave_type: str
    start_date: date
    end_date: date
    reason: str | None = None


class SelfServiceLeaveResponse(BaseModel):
    """Leave request response."""
    id: str
    leave_type: str
    start_date: date
    end_date: date
    status: str
    reason: str | None
    created_at: str


class SelfServiceCertification(BaseModel):
    """Certification status for self-service."""
    skill_id: str
    skill_name: str
    status: str
    certified_date: date | None
    expiration_date: date | None
    days_until_expiration: int | None


class SelfServiceBenefitEnrollment(BaseModel):
    """Benefit/social security summary for employee."""
    jurisdiction: str
    jurisdiction_name: str
    benefit_type: str  # social_security, medical, family_allowance, pension
    agency_name: str | None
    ss_number: str | None
    registration_date: date | None
    status: str
    details: dict | None


class SelfServiceSocialSecuritySummary(BaseModel):
    """Complete social security summary per jurisdiction."""
    jurisdiction: str
    country_name: str
    currency: str
    ss_number: str | None
    employment_type: str | None
    total_contribution_months: int
    # Current contribution rates
    employee_pension_rate: float
    employee_health_rate: float
    employer_pension_rate: float
    employer_health_rate: float
    # Medical coverage
    medical_coverage_type: str | None
    medical_card_number: str | None
    dependents_covered: int
    # Family allowance
    family_allowance_amount: float | None
    eligible_children: int
    # Leave entitlements
    annual_leave_days: int
    maternity_leave_days: int
    paternity_leave_days: int
    # Retirement
    retirement_age: int
    pension_eligibility_months: int


class SelfServiceTimeEntry(BaseModel):
    """Time clock entry for self-service."""
    event_type: str
    latitude: float | None = None
    longitude: float | None = None
    device_type: str | None = None


@self_service_router.get("/profile", response_model=SelfServiceProfile)
async def get_my_profile(db: DBSession, current_user: CurrentUser) -> Any:
    """Get current user's employee profile."""
    result = await db.execute(
        select(EmployeeProfile).where(EmployeeProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Return user data if no employee profile exists
        return SelfServiceProfile(
            id=str(current_user.id),
            first_name=current_user.first_name or "",
            last_name=current_user.last_name or "",
            email=current_user.email,
            phone=None,
            department=None,
            job_title=None,
            site_id=None,
            hire_date=None,
            status="active",
        )
    
    return SelfServiceProfile(
        id=str(profile.id),
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email,
        phone=profile.phone,
        department=profile.department,
        job_title=profile.job_title,
        site_id=profile.site_id,
        hire_date=profile.hire_date,
        status=profile.status,
    )


@self_service_router.get("/leave-requests", response_model=List[SelfServiceLeaveResponse])
async def get_my_leave_requests(db: DBSession, current_user: CurrentUser) -> Any:
    """Get current user's leave requests."""
    # Find employee profile
    profile_result = await db.execute(
        select(EmployeeProfile).where(EmployeeProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        return []
    
    result = await db.execute(
        select(HRLeaveRequest)
        .where(HRLeaveRequest.employee_id == profile.id)
        .order_by(HRLeaveRequest.created_at.desc())
        .limit(settings.AUDIT_LOG_QUERY_LIMIT)
    )
    requests = result.scalars().all()
    
    return [
        SelfServiceLeaveResponse(
            id=str(r.id),
            leave_type=r.leave_type,
            start_date=r.start_date,
            end_date=r.end_date,
            status=r.status,
            reason=r.reason,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in requests
    ]


@self_service_router.post("/leave-requests", response_model=SelfServiceLeaveResponse)
async def submit_leave_request(
    request: SelfServiceLeaveRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Submit a new leave request."""
    from datetime import datetime, timezone as tz
    
    # Find employee profile
    profile_result = await db.execute(
        select(EmployeeProfile).where(EmployeeProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Validate dates
    if request.end_date < request.start_date:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    # Create leave request
    leave_request = HRLeaveRequest(
        employee_id=profile.id,
        leave_type=request.leave_type,
        start_date=request.start_date,
        end_date=request.end_date,
        status="pending",
        reason=request.reason,
    )
    db.add(leave_request)
    await db.flush()
    await db.refresh(leave_request)

    # Wire into common thread lineage
    try:
        await get_common_thread_service().bind_hr(
            db,
            employee_id=profile.id,
            leave_request_id=leave_request.id,
            created_by_id=getattr(current_user, "id", None),
            source="hr_self_service_leave_request",
        )
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        logger.exception("Failed to capture leave request lineage")
    
    return SelfServiceLeaveResponse(
        id=str(leave_request.id),
        leave_type=leave_request.leave_type,
        start_date=leave_request.start_date,
        end_date=leave_request.end_date,
        status=leave_request.status,
        reason=leave_request.reason,
        created_at=leave_request.created_at.isoformat() if leave_request.created_at else "",
    )


@self_service_router.get("/certifications", response_model=List[SelfServiceCertification])
async def get_my_certifications(db: DBSession, current_user: CurrentUser) -> Any:
    """Get current user's certifications and their status."""
    today = date.today()
    
    result = await db.execute(
        select(UserSkill, Skill)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.user_id == current_user.id)
        .order_by(UserSkill.expiration_date.asc().nullslast())
    )
    rows = result.all()
    
    certs = []
    for user_skill, skill in rows:
        days_until = None
        if user_skill.expiration_date:
            days_until = (user_skill.expiration_date - today).days
        
        certs.append(
            SelfServiceCertification(
                skill_id=str(skill.id),
                skill_name=skill.name,
                status=user_skill.certification_status.value if user_skill.certification_status else "unknown",
                certified_date=user_skill.certified_date,
                expiration_date=user_skill.expiration_date,
                days_until_expiration=days_until,
            )
        )
    
    return certs


@self_service_router.get("/benefits", response_model=List[SelfServiceBenefitEnrollment])
async def get_my_benefits(db: DBSession, current_user: CurrentUser) -> Any:
    """Get current user's social security and benefit enrollments based on jurisdiction."""
    from sensei.models.hr import (
        HRSocialSecurityRecord, HRMedicalCoverage, HRFamilyAllowance,
        HRJurisdictionConfig
    )
    
    # Find employee profile
    profile_result = await db.execute(
        select(EmployeeProfile).where(EmployeeProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        return []
    
    benefits = []
    jurisdiction = profile.jurisdiction
    
    # Get jurisdiction config
    jurisdiction_names = {"TN": "Tunisia", "MA": "Morocco", "EG": "Egypt"}
    jurisdiction_agencies = {
        "TN": "CNSS - Caisse Nationale de Sécurité Sociale",
        "MA": "CNSS - Caisse Nationale de Sécurité Sociale", 
        "EG": "NOSI - National Organization for Social Insurance"
    }
    
    # Get social security record
    ss_result = await db.execute(
        select(HRSocialSecurityRecord).where(
            HRSocialSecurityRecord.employee_id == profile.id,
            HRSocialSecurityRecord.is_active == True,
        )
    )
    ss_record = ss_result.scalar_one_or_none()
    
    if ss_record:
        benefits.append(SelfServiceBenefitEnrollment(
            jurisdiction=jurisdiction,
            jurisdiction_name=jurisdiction_names.get(jurisdiction, "Unknown"),
            benefit_type="social_security",
            agency_name=jurisdiction_agencies.get(jurisdiction),
            ss_number=ss_record.ss_number,
            registration_date=ss_record.registration_date,
            status="active" if ss_record.is_active else "inactive",
            details={
                "employment_type": ss_record.employment_type,
                "sector_type": ss_record.sector_type,
                "total_contribution_months": ss_record.total_contribution_months,
                "total_contribution_days": ss_record.total_contribution_days,
            }
        ))
    
    # Get medical coverage
    med_result = await db.execute(
        select(HRMedicalCoverage).where(
            HRMedicalCoverage.employee_id == profile.id,
            HRMedicalCoverage.is_active == True,
        )
    )
    med_coverage = med_result.scalar_one_or_none()
    
    if med_coverage:
        benefits.append(SelfServiceBenefitEnrollment(
            jurisdiction=jurisdiction,
            jurisdiction_name=jurisdiction_names.get(jurisdiction, "Unknown"),
            benefit_type="medical",
            agency_name=jurisdiction_agencies.get(jurisdiction),
            ss_number=med_coverage.medical_card_number,
            registration_date=med_coverage.registration_date,
            status="active" if med_coverage.is_active else "inactive",
            details={
                "coverage_type": med_coverage.coverage_type,
                "coverage_option": med_coverage.coverage_option,
                "spouse_covered": med_coverage.spouse_covered,
                "children_covered": med_coverage.children_covered,
                "parents_covered": med_coverage.parents_covered,
            }
        ))
    
    # Get family allowance
    fam_result = await db.execute(
        select(HRFamilyAllowance).where(
            HRFamilyAllowance.employee_id == profile.id,
            HRFamilyAllowance.is_active == True,
        )
    )
    fam_allowance = fam_result.scalar_one_or_none()
    
    if fam_allowance:
        benefits.append(SelfServiceBenefitEnrollment(
            jurisdiction=jurisdiction,
            jurisdiction_name=jurisdiction_names.get(jurisdiction, "Unknown"),
            benefit_type="family_allowance",
            agency_name=jurisdiction_agencies.get(jurisdiction),
            ss_number=None,
            registration_date=fam_allowance.effective_date,
            status="active" if fam_allowance.is_active else "inactive",
            details={
                "eligible_children": fam_allowance.eligible_children,
                "monthly_allowance": float(fam_allowance.monthly_allowance),
                "has_nonworking_spouse": fam_allowance.has_nonworking_spouse,
                "spouse_supplement": float(fam_allowance.spouse_supplement),
                "nursery_allowance": float(fam_allowance.nursery_allowance),
            }
        ))
    
    return benefits


@self_service_router.get("/social-security-summary", response_model=SelfServiceSocialSecuritySummary)
async def get_my_social_security_summary(db: DBSession, current_user: CurrentUser) -> Any:
    """Get comprehensive social security summary based on employee jurisdiction."""
    from sensei.models.hr import (
        HRSocialSecurityRecord, HRMedicalCoverage, HRFamilyAllowance,
        HRJurisdictionConfig
    )
    
    # Find employee profile
    profile_result = await db.execute(
        select(EmployeeProfile).where(EmployeeProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    jurisdiction = profile.jurisdiction
    
    # Get jurisdiction config (or use defaults)
    config_result = await db.execute(
        select(HRJurisdictionConfig).where(
            HRJurisdictionConfig.jurisdiction == jurisdiction,
            HRJurisdictionConfig.is_active == True,
        )
    )
    config = config_result.scalar_one_or_none()
    
    # Default rates by jurisdiction (based on SSA research)
    default_configs = {
        "TN": {  # Tunisia
            "country_name": "Tunisia",
            "currency": "TND",
            "employee_pension_rate": 4.74,
            "employee_health_rate": 3.17,
            "employer_pension_rate": 7.76,
            "employer_health_rate": 5.08,
            "annual_leave_days": 21,
            "maternity_leave_days": 30,
            "paternity_leave_days": 1,
            "retirement_age": 60,
            "pension_eligibility_months": 120,
        },
        "MA": {  # Morocco
            "country_name": "Morocco",
            "currency": "MAD",
            "employee_pension_rate": 3.96,
            "employee_health_rate": 2.26,
            "employer_pension_rate": 7.93,
            "employer_health_rate": 4.11,
            "annual_leave_days": 18,
            "maternity_leave_days": 98,  # 14 weeks
            "paternity_leave_days": 3,
            "retirement_age": 60,
            "pension_eligibility_months": 108,  # 3240 days
        },
        "EG": {  # Egypt
            "country_name": "Egypt",
            "currency": "EGP",
            "employee_pension_rate": 10.0,
            "employee_health_rate": 1.0,
            "employer_pension_rate": 15.0,
            "employer_health_rate": 4.0,
            "annual_leave_days": 21,
            "maternity_leave_days": 90,
            "paternity_leave_days": 0,
            "retirement_age": 60,
            "pension_eligibility_months": 120,
        },
    }
    
    jur_config = default_configs.get(jurisdiction, default_configs["TN"])
    
    # Get social security record
    ss_result = await db.execute(
        select(HRSocialSecurityRecord).where(
            HRSocialSecurityRecord.employee_id == profile.id,
            HRSocialSecurityRecord.is_active == True,
        )
    )
    ss_record = ss_result.scalar_one_or_none()
    
    # Get medical coverage
    med_result = await db.execute(
        select(HRMedicalCoverage).where(
            HRMedicalCoverage.employee_id == profile.id,
            HRMedicalCoverage.is_active == True,
        )
    )
    med_coverage = med_result.scalar_one_or_none()
    
    # Get family allowance
    fam_result = await db.execute(
        select(HRFamilyAllowance).where(
            HRFamilyAllowance.employee_id == profile.id,
            HRFamilyAllowance.is_active == True,
        )
    )
    fam_allowance = fam_result.scalar_one_or_none()
    
    return SelfServiceSocialSecuritySummary(
        jurisdiction=jurisdiction,
        country_name=jur_config["country_name"],
        currency=jur_config["currency"],
        ss_number=ss_record.ss_number if ss_record else None,
        employment_type=ss_record.employment_type if ss_record else None,
        total_contribution_months=ss_record.total_contribution_months if ss_record else 0,
        employee_pension_rate=float(config.employee_pension_rate) if config else jur_config["employee_pension_rate"],
        employee_health_rate=float(config.employee_health_rate) if config else jur_config["employee_health_rate"],
        employer_pension_rate=float(config.employer_pension_rate) if config else jur_config["employer_pension_rate"],
        employer_health_rate=float(config.employer_health_rate) if config else jur_config["employer_health_rate"],
        medical_coverage_type=med_coverage.coverage_type if med_coverage else None,
        medical_card_number=med_coverage.medical_card_number if med_coverage else None,
        dependents_covered=med_coverage.children_covered + (1 if med_coverage and med_coverage.spouse_covered else 0) if med_coverage else 0,
        family_allowance_amount=float(fam_allowance.monthly_allowance) if fam_allowance else None,
        eligible_children=fam_allowance.eligible_children if fam_allowance else 0,
        annual_leave_days=config.annual_leave_days if config else jur_config["annual_leave_days"],
        maternity_leave_days=config.maternity_leave_days if config else jur_config["maternity_leave_days"],
        paternity_leave_days=config.paternity_leave_days if config else jur_config["paternity_leave_days"],
        retirement_age=config.retirement_age_male if config else jur_config["retirement_age"],
        pension_eligibility_months=config.min_pension_months if config else jur_config["pension_eligibility_months"],
    )


@self_service_router.post("/time-clock")
async def clock_in_out(
    entry: SelfServiceTimeEntry,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Record a time clock event (clock in/out, break start/end)."""
    from datetime import datetime, timezone as tz
    from sensei.models.hr import HRTimeClockEvent, HRGeofence
    from decimal import Decimal
    
    # Find employee profile
    profile_result = await db.execute(
        select(EmployeeProfile).where(EmployeeProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Validate event type
    valid_types = ["clock_in", "clock_out", "break_start", "break_end"]
    if entry.event_type not in valid_types:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid event type. Must be one of: {valid_types}")
    
    # Check geofence if location provided
    is_within_geofence = None
    geofence_id = None
    distance_from_geofence = None
    
    if entry.latitude is not None and entry.longitude is not None:
        # Find active geofences for the employee's site
        geofence_result = await db.execute(
            select(HRGeofence).where(
                HRGeofence.is_active == True,
                HRGeofence.site_id == profile.site_id,
            )
        )
        geofences = geofence_result.scalars().all()
        
        # Simple distance calculation (Haversine would be better for production)
        import math
        
        for gf in geofences:
            # Calculate approximate distance in meters
            lat_diff = float(entry.latitude) - float(gf.latitude)
            lng_diff = float(entry.longitude) - float(gf.longitude)
            # Approximate meters (1 degree ≈ 111km at equator)
            distance = math.sqrt(lat_diff**2 + lng_diff**2) * 111000
            
            if distance <= float(gf.radius_meters):
                is_within_geofence = True
                geofence_id = gf.id
                distance_from_geofence = Decimal(str(distance))
                break
            elif geofence_id is None:
                is_within_geofence = False
                geofence_id = gf.id
                distance_from_geofence = Decimal(str(distance))
    
    # Create time clock event
    event = HRTimeClockEvent(
        employee_id=profile.id,
        event_type=entry.event_type,
        event_time=datetime.now(tz.utc),
        latitude=Decimal(str(entry.latitude)) if entry.latitude else None,
        longitude=Decimal(str(entry.longitude)) if entry.longitude else None,
        geofence_id=geofence_id,
        is_within_geofence=is_within_geofence,
        distance_from_geofence_meters=distance_from_geofence,
        device_type=entry.device_type,
        verification_method="none",
        is_anomaly=is_within_geofence is False,  # Flag as anomaly if outside geofence
        anomaly_reason="Outside geofence" if is_within_geofence is False else None,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    # Wire into common thread lineage
    try:
        await get_common_thread_service().bind_hr(
            db,
            employee_id=profile.id,
            timecard_id=event.id,
            created_by_id=getattr(current_user, "id", None),
            source="hr_self_service_time_clock",
        )
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        logger.exception("Failed to capture time clock lineage")
    
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "event_time": event.event_time.isoformat(),
        "is_within_geofence": is_within_geofence,
        "distance_from_geofence_meters": float(distance_from_geofence) if distance_from_geofence else None,
        "is_anomaly": event.is_anomaly,
    }


@self_service_router.get("/time-clock/today")
async def get_today_time_entries(db: DBSession, current_user: CurrentUser) -> Any:
    """Get today's time clock entries for the current user."""
    from datetime import datetime, timezone as tz
    from sensei.models.hr import HRTimeClockEvent
    
    # Find employee profile
    profile_result = await db.execute(
        select(EmployeeProfile).where(EmployeeProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        return []
    
    today_start = datetime.now(tz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(
        select(HRTimeClockEvent)
        .where(
            HRTimeClockEvent.employee_id == profile.id,
            HRTimeClockEvent.event_time >= today_start,
        )
        .order_by(HRTimeClockEvent.event_time.asc())
    )
    events = result.scalars().all()
    
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "event_time": e.event_time.isoformat(),
            "is_within_geofence": e.is_within_geofence,
            "is_anomaly": e.is_anomaly,
        }
        for e in events
    ]
