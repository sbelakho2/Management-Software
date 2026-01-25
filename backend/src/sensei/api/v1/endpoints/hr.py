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
from sensei.models.user import User, Role
from sensei.models.hr import EmployeeProfile, HRJobOpening, HRLeaveRequest, HRJobApplication, HRAppraisal
from sensei.models.learning import UserLearningProgress, LearningModule
from sensei.models.training import UserSkill, CertificationStatus, Skill
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response

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
        .limit(50)
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
