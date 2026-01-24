"""
Auditor API Endpoints.

Provides endpoints for audit management, findings, compliance tracking, and audit reports.
"""

from datetime import datetime, date, timedelta
from typing import Any, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import DBSession, CurrentUser
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response

router = APIRouter()

# =============================================================================
# Schemas
# =============================================================================

class AuditStatsResponse(BaseModel):
    total_audits: int
    completed_this_year: int
    open_findings: int
    critical_findings: int
    upcoming_audits: int
    compliance_score: float


class AuditResponse(BaseModel):
    id: str
    name: str
    audit_type: str  # internal, external, supplier, customer
    status: str  # scheduled, in_progress, completed, closed
    scheduled_date: str
    completed_date: Optional[str]
    findings_count: int
    lead_auditor: Optional[str]
    priority: str


class AuditFindingResponse(BaseModel):
    id: str
    audit_id: str
    title: str
    description: Optional[str]
    area: str
    severity: str  # critical, major, minor, observation
    status: str  # open, in_progress, closed, verified
    due_date: Optional[str]
    days_overdue: int
    assigned_to: Optional[str]


class ComplianceAreaResponse(BaseModel):
    name: str
    score: float
    audits: int
    trend: str


class AuditCreateSchema(BaseModel):
    name: str
    audit_type: str = "internal"
    scheduled_date: date
    priority: str = "medium"
    lead_auditor: Optional[str] = None
    description: Optional[str] = None


class FindingCreateSchema(BaseModel):
    audit_id: str
    title: str
    description: Optional[str] = None
    area: str
    severity: str = "minor"
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None


# =============================================================================
# In-Memory Storage (Replace with DB models in production)
# =============================================================================

# For demo purposes, we maintain in-memory data
# In production, you'd have Audit and AuditFinding models

_audits: dict[str, dict] = {
    "audit-1": {
        "id": "audit-1",
        "name": "ISO 9001 Surveillance",
        "audit_type": "external",
        "status": "scheduled",
        "scheduled_date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
        "completed_date": None,
        "findings_count": 0,
        "lead_auditor": "External Auditor",
        "priority": "high"
    },
    "audit-2": {
        "id": "audit-2",
        "name": "Internal Quality Audit",
        "audit_type": "internal",
        "status": "scheduled",
        "scheduled_date": (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d"),
        "completed_date": None,
        "findings_count": 0,
        "lead_auditor": "Quality Manager",
        "priority": "medium"
    },
    "audit-3": {
        "id": "audit-3",
        "name": "Q4 Process Audit",
        "audit_type": "internal",
        "status": "completed",
        "scheduled_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "completed_date": (datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d"),
        "findings_count": 3,
        "lead_auditor": "Quality Manager",
        "priority": "medium"
    },
}

_findings: dict[str, dict] = {
    "finding-1": {
        "id": "finding-1",
        "audit_id": "audit-3",
        "title": "Document control procedure gap",
        "description": "Document revision process not consistently followed",
        "area": "Quality",
        "severity": "major",
        "status": "open",
        "due_date": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
        "days_overdue": 0,
        "assigned_to": "Quality Lead"
    },
    "finding-2": {
        "id": "finding-2",
        "audit_id": "audit-3",
        "title": "Training records incomplete",
        "description": "Some employee training records missing signatures",
        "area": "HR",
        "severity": "minor",
        "status": "in_progress",
        "due_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
        "days_overdue": 0,
        "assigned_to": "HR Manager"
    },
    "finding-3": {
        "id": "finding-3",
        "audit_id": "audit-3",
        "title": "Calibration schedule not followed",
        "description": "Two measuring devices overdue for calibration",
        "area": "Production",
        "severity": "major",
        "status": "open",
        "due_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        "days_overdue": 5,
        "assigned_to": "Maintenance Lead"
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def calculate_compliance_score() -> float:
    """Calculate overall compliance score based on findings."""
    total_findings = len(_findings)
    if total_findings == 0:
        return 100.0
    
    open_critical = sum(1 for f in _findings.values() if f["status"] == "open" and f["severity"] == "critical")
    open_major = sum(1 for f in _findings.values() if f["status"] == "open" and f["severity"] == "major")
    
    # Simple scoring: 100 - (critical * 10) - (major * 5)
    score = 100 - (open_critical * 10) - (open_major * 5)
    return max(0, min(100, score))


# =============================================================================
# Endpoints - Dashboard Stats
# =============================================================================

@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(db: DBSession, current_user: CurrentUser) -> Any:
    """Get audit dashboard statistics."""
    total_audits = len(_audits)
    completed_this_year = sum(1 for a in _audits.values() if a["status"] in ["completed", "closed"])
    open_findings = sum(1 for f in _findings.values() if f["status"] in ["open", "in_progress"])
    critical_findings = sum(1 for f in _findings.values() if f["severity"] == "critical" and f["status"] != "closed")
    upcoming_audits = sum(1 for a in _audits.values() if a["status"] == "scheduled")
    compliance_score = calculate_compliance_score()
    
    return AuditStatsResponse(
        total_audits=total_audits,
        completed_this_year=completed_this_year,
        open_findings=open_findings,
        critical_findings=critical_findings,
        upcoming_audits=upcoming_audits,
        compliance_score=compliance_score
    )


@router.get("/compliance-areas", response_model=List[ComplianceAreaResponse])
async def get_compliance_areas(db: DBSession, current_user: CurrentUser) -> Any:
    """Get compliance scores by area."""
    # Aggregate findings by area
    areas: dict[str, dict[str, Any]] = {}
    for f in _findings.values():
        area = f["area"]
        if area not in areas:
            areas[area] = {"findings": 0, "open": 0, "audits": set()}
        areas[area]["findings"] += 1
        if f["status"] in ["open", "in_progress"]:
            areas[area]["open"] += 1
        areas[area]["audits"].add(f["audit_id"])
    
    result = []
    default_areas = [
        ("Quality Management", 96),
        ("Safety & Environment", 92),
        ("Document Control", 88),
        ("Training & Competency", 95),
        ("Supplier Management", 91),
    ]
    
    for area_name, default_score in default_areas:
        area_data: dict[str, Any] = areas.get(area_name, {"findings": 0, "open": 0, "audits": set()})
        # Adjust score based on open findings
        score = default_score - (area_data["open"] * 2)
        result.append(ComplianceAreaResponse(
            name=area_name,
            score=max(0, min(100, score)),
            audits=len(area_data["audits"]) or 1,
            trend="stable" if area_data["open"] == 0 else "down"
        ))
    
    return result


# =============================================================================
# Endpoints - Audits CRUD
# =============================================================================

@router.get("/audits", response_model=APIResponse[dict])
async def get_audits(
    db: DBSession,
    current_user: CurrentUser,
    status: Optional[str] = None,
    audit_type: Optional[str] = None
) -> Any:
    """Get all audits with optional filters."""
    audits = list(_audits.values())
    
    if status:
        audits = [a for a in audits if a["status"] == status]
    if audit_type:
        audits = [a for a in audits if a["audit_type"] == audit_type]
    
    return build_response(data={"items": audits})


@router.get("/audits/upcoming", response_model=List[AuditResponse])
async def get_upcoming_audits(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(5, ge=1, le=20)
) -> Any:
    """Get upcoming scheduled audits."""
    upcoming = [
        AuditResponse(**a) for a in _audits.values()
        if a["status"] == "scheduled"
    ]
    upcoming.sort(key=lambda x: x.scheduled_date)
    return upcoming[:limit]


@router.get("/audits/{audit_id}", response_model=AuditResponse)
async def get_audit(audit_id: str, db: DBSession, current_user: CurrentUser) -> Any:
    """Get a specific audit."""
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    return AuditResponse(**_audits[audit_id])


@router.post("/audits", response_model=AuditResponse)
async def create_audit(
    audit_in: AuditCreateSchema,
    db: DBSession,
    current_user: CurrentUser
) -> Any:
    """Create a new audit."""
    audit_id = f"audit-{uuid4().hex[:8]}"
    audit = {
        "id": audit_id,
        "name": audit_in.name,
        "audit_type": audit_in.audit_type,
        "status": "scheduled",
        "scheduled_date": audit_in.scheduled_date.isoformat(),
        "completed_date": None,
        "findings_count": 0,
        "lead_auditor": audit_in.lead_auditor,
        "priority": audit_in.priority
    }
    _audits[audit_id] = audit
    return AuditResponse(**audit)


@router.patch("/audits/{audit_id}/status", response_model=AuditResponse)
async def update_audit_status(
    audit_id: str,
    status: str,
    db: DBSession,
    current_user: CurrentUser
) -> Any:
    """Update audit status."""
    if audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    valid_statuses = ["scheduled", "in_progress", "completed", "closed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    _audits[audit_id]["status"] = status
    if status in ["completed", "closed"]:
        _audits[audit_id]["completed_date"] = datetime.now().strftime("%Y-%m-%d")
    
    return AuditResponse(**_audits[audit_id])


# =============================================================================
# Endpoints - Findings CRUD
# =============================================================================

@router.get("/findings", response_model=APIResponse[dict])
async def get_findings(
    db: DBSession,
    current_user: CurrentUser,
    audit_id: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None
) -> Any:
    """Get all findings with optional filters."""
    findings = list(_findings.values())
    
    if audit_id:
        findings = [f for f in findings if f["audit_id"] == audit_id]
    if status:
        findings = [f for f in findings if f["status"] == status]
    if severity:
        findings = [f for f in findings if f["severity"] == severity]
    
    return build_response(data={"items": findings})


@router.get("/findings/open", response_model=List[AuditFindingResponse])
async def get_open_findings(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=50)
) -> Any:
    """Get open findings prioritized by severity and due date."""
    open_findings = [
        AuditFindingResponse(**f) for f in _findings.values()
        if f["status"] in ["open", "in_progress"]
    ]
    # Sort by severity (critical first) then by days overdue
    severity_order = {"critical": 0, "major": 1, "minor": 2, "observation": 3}
    open_findings.sort(key=lambda x: (severity_order.get(x.severity, 4), -x.days_overdue))
    return open_findings[:limit]


@router.get("/findings/{finding_id}", response_model=AuditFindingResponse)
async def get_finding(finding_id: str, db: DBSession, current_user: CurrentUser) -> Any:
    """Get a specific finding."""
    if finding_id not in _findings:
        raise HTTPException(status_code=404, detail="Finding not found")
    return AuditFindingResponse(**_findings[finding_id])


@router.post("/findings", response_model=AuditFindingResponse)
async def create_finding(
    finding_in: FindingCreateSchema,
    db: DBSession,
    current_user: CurrentUser
) -> Any:
    """Create a new audit finding."""
    if finding_in.audit_id not in _audits:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    finding_id = f"finding-{uuid4().hex[:8]}"
    finding = {
        "id": finding_id,
        "audit_id": finding_in.audit_id,
        "title": finding_in.title,
        "description": finding_in.description,
        "area": finding_in.area,
        "severity": finding_in.severity,
        "status": "open",
        "due_date": finding_in.due_date.isoformat() if finding_in.due_date else None,
        "days_overdue": 0,
        "assigned_to": finding_in.assigned_to
    }
    _findings[finding_id] = finding
    _audits[finding_in.audit_id]["findings_count"] += 1
    
    return AuditFindingResponse(**finding)


@router.patch("/findings/{finding_id}/status", response_model=AuditFindingResponse)
async def update_finding_status(
    finding_id: str,
    status: str,
    db: DBSession,
    current_user: CurrentUser
) -> Any:
    """Update finding status."""
    if finding_id not in _findings:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    valid_statuses = ["open", "in_progress", "closed", "verified"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    _findings[finding_id]["status"] = status
    return AuditFindingResponse(**_findings[finding_id])


# =============================================================================
# Endpoints - Reports
# =============================================================================

@router.get("/reports/summary", response_model=dict)
async def get_audit_summary_report(db: DBSession, current_user: CurrentUser) -> Any:
    """Generate audit summary report."""
    stats = await get_audit_stats(db, current_user)
    compliance = await get_compliance_areas(db, current_user)
    
    return {
        "generated_at": datetime.now().isoformat(),
        "period": "YTD",
        "summary": stats.model_dump(),
        "compliance_by_area": [c.model_dump() for c in compliance],
        "total_audits_conducted": stats.completed_this_year,
        "average_findings_per_audit": round(len(_findings) / max(1, stats.completed_this_year), 1),
        "closure_rate": round(
            (len([f for f in _findings.values() if f["status"] == "closed"]) / max(1, len(_findings))) * 100, 1
        )
    }


@router.get("/reports/findings-trend", response_model=dict)
async def get_findings_trend(db: DBSession, current_user: CurrentUser) -> Any:
    """Get findings trend over time."""
    # In production, this would query historical data
    return {
        "period": "6 months",
        "data": [
            {"month": "Aug", "opened": 5, "closed": 4},
            {"month": "Sep", "opened": 3, "closed": 5},
            {"month": "Oct", "opened": 4, "closed": 3},
            {"month": "Nov", "opened": 2, "closed": 4},
            {"month": "Dec", "opened": 3, "closed": 2},
            {"month": "Jan", "opened": 1, "closed": 2},
        ]
    }
