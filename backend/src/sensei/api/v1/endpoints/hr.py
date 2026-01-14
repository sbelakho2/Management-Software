"""
HR (Human Resources) API Endpoints.
Aggregates employee data, certifications, and headcount.
"""

from typing import Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sensei.api.deps import DBSession, CurrentUser
from sensei.models.user import User, Role
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
    # Aggregated stats
    total_employees = db.query(User).count()
    # Mocking some values for now as they aren't in the schema yet
    return HRStats(
        total_employees=total_employees,
        open_positions=8,
        pending_time_off=12,
        expiring_certifications=5,
        new_hires_this_month=3,
        turnover_rate=4.2
    )

@router.get("/headcount", response_model=List[DepartmentHeadcount])
async def get_headcount(db: DBSession) -> Any:
    # In a real app, you'd group users by department
    return [
        {"name": "Operations", "count": 68, "percentage": 44.0},
        {"name": "Engineering", "count": 32, "percentage": 21.0},
        {"name": "Quality", "count": 18, "percentage": 12.0},
        {"name": "Sales", "count": 22, "percentage": 14.0},
        {"name": "Admin", "count": 16, "percentage": 10.0},
    ]

@router.get("/expiring-certs", response_model=List[ExpiringCert])
async def get_expiring_certs(db: DBSession) -> Any:
    return [
        {"id": "1", "employee": "Tom Brown", "cert": "Forklift Operator", "expires": "5 days", "priority": "high"},
        {"id": "2", "employee": "Lisa Chen", "cert": "First Aid", "expires": "12 days", "priority": "medium"},
        {"id": "3", "employee": "James Lee", "cert": "Crane Operator", "expires": "18 days", "priority": "medium"},
        {"id": "4", "employee": "Emma Davis", "cert": "Safety Training", "expires": "25 days", "priority": "low"},
    ]
