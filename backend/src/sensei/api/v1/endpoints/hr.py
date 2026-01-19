"""
HR (Human Resources) API Endpoints.
Aggregates employee data, certifications, and headcount.
"""

from typing import Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from sensei.api.deps import DBSession, CurrentUser
from sensei.models.user import User, Role
from sensei.models.hr import EmployeeProfile, HRJobOpening, HRLeaveRequest, HRJobApplication, HRAppraisal
from sensei.models.learning import UserLearningProgress, LearningModule
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response

router = APIRouter()

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
async def get_hr_stats(db: DBSession) -> Any:
    # Aggregated stats from DB
    total_employees = await db.scalar(select(func.count(EmployeeProfile.id)))
    open_positions = await db.scalar(select(func.count(HRJobOpening.id)).where(HRJobOpening.status == "open"))
    pending_time_off = await db.scalar(select(func.count(HRLeaveRequest.id)).where(HRLeaveRequest.status == "pending"))
    
    return HRStats(
        total_employees=total_employees or 0,
        open_positions=open_positions or 0,
        pending_time_off=pending_time_off or 0,
        expiring_certifications=5, # Still some mocks until cert service updated
        new_hires_this_month=3,
        turnover_rate=4.2
    )

@router.get("/headcount", response_model=List[DepartmentHeadcount])
async def get_headcount(db: DBSession) -> Any:
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
async def list_job_openings(db: DBSession) -> Any:
    result = await db.execute(select(HRJobOpening))
    openings = result.scalars().all()
    return [o.to_dict() for o in openings]

@router.get("/applications", response_model=List[dict])
async def list_job_applications(db: DBSession) -> Any:
    result = await db.execute(select(HRJobApplication))
    apps = result.scalars().all()
    return [a.to_dict() for a in apps]

@router.get("/appraisals", response_model=List[dict])
async def list_appraisals(db: DBSession) -> Any:
    result = await db.execute(select(HRAppraisal))
    appraisals = result.scalars().all()
    return [a.to_dict() for a in appraisals]

@router.get("/leave-requests", response_model=List[dict])
async def list_leave_requests(db: DBSession) -> Any:
    result = await db.execute(select(HRLeaveRequest))
    requests = result.scalars().all()
    return [r.to_dict() for r in requests]

@router.get("/expiring-certs", response_model=List[ExpiringCert])
async def get_expiring_certs(db: DBSession) -> Any:
    return [
        {"id": "1", "employee": "Tom Brown", "cert": "Forklift Operator", "expires": "5 days", "priority": "high"},
        {"id": "2", "employee": "Lisa Chen", "cert": "First Aid", "expires": "12 days", "priority": "medium"},
        {"id": "3", "employee": "James Lee", "cert": "Crane Operator", "expires": "18 days", "priority": "medium"},
        {"id": "4", "employee": "Emma Davis", "cert": "Safety Training", "expires": "25 days", "priority": "low"},
    ]
