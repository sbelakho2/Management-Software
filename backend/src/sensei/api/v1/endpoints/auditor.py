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

from sensei.api import deps
from sensei.api.deps import DBSession, CurrentUser
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.models.quality_qms import QualityAudit, AuditFinding
from sensei.models.user import User

AllowAuditModule = deps.require_role(
    "auditor",
    "quality",
    "ops",
    "supervisor",
    "engineering",
    "team_lead",
    "operator",
    "gm",
    "exec",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                [
                    "auditor",
                    "quality",
                    "ops",
                    "supervisor",
                    "engineering",
                    "team_lead",
                    "operator",
                    "gm",
                    "exec",
                ]
            )
        )
    ]
)

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
# Helper Functions
# =============================================================================


def _map_audit_status_to_api(db_status: str) -> str:
    return {
        "planned": "scheduled",
        "in_progress": "in_progress",
        "completed": "completed",
        "cancelled": "closed",
    }.get(db_status, db_status)


def _map_audit_status_to_db(api_status: str) -> str:
    return {
        "scheduled": "planned",
        "in_progress": "in_progress",
        "completed": "completed",
        "closed": "completed",
    }.get(api_status, api_status)


def _map_finding_severity_to_api(db_severity: str) -> str:
    return {
        "critical_nc": "critical",
        "major_nc": "major",
        "minor_nc": "minor",
        "observation": "observation",
    }.get(db_severity, db_severity)


def _map_finding_severity_to_db(api_severity: str) -> str:
    return {
        "critical": "critical_nc",
        "major": "major_nc",
        "minor": "minor_nc",
        "observation": "observation",
    }.get(api_severity, api_severity)


def _map_finding_status_to_api(db_status: str) -> str:
    return {
        "open": "open",
        "action_planned": "in_progress",
        "action_implemented": "in_progress",
        "verified_closed": "closed",
        "cancelled": "closed",
    }.get(db_status, db_status)


def _map_finding_status_to_db(api_status: str) -> list[str]:
    # For filtering: one API status may map to multiple DB statuses.
    if api_status == "open":
        return ["open"]
    if api_status == "in_progress":
        return ["action_planned", "action_implemented"]
    if api_status in {"closed", "verified"}:
        return ["verified_closed", "cancelled"]
    return [api_status]


def _compute_days_overdue(due_by: date | None, status: str) -> int:
    if not due_by:
        return 0
    if status in {"verified_closed", "cancelled"}:
        return 0
    days = (date.today() - due_by).days
    return max(0, days)


def _compute_audit_priority(scheduled_for: datetime) -> str:
    # Derived, non-fabricated signal based on schedule proximity.
    days = (scheduled_for.date() - date.today()).days
    if days <= 7:
        return "high"
    if days <= 30:
        return "medium"
    return "low"


async def _audit_findings_count(db: AsyncSession, audit_id: UUID) -> int:
    q = select(func.count(AuditFinding.id)).where(AuditFinding.audit_id == audit_id)
    return int(await db.scalar(q) or 0)


async def _to_audit_response(db: AsyncSession, audit: QualityAudit) -> AuditResponse:
    findings_count = await _audit_findings_count(db, audit.id)
    return AuditResponse(
        id=str(audit.id),
        name=audit.title,
        audit_type=audit.audit_type,
        status=_map_audit_status_to_api(audit.status),
        scheduled_date=audit.scheduled_for.date().isoformat(),
        completed_date=audit.completed_at.date().isoformat() if audit.completed_at else None,
        findings_count=findings_count,
        lead_auditor=None,
        priority=_compute_audit_priority(audit.scheduled_for),
    )


async def _to_finding_response(finding: AuditFinding) -> AuditFindingResponse:
    assigned_to = None
    if finding.assigned_to:
        assigned_to = f"{finding.assigned_to.first_name} {finding.assigned_to.last_name}".strip()
    return AuditFindingResponse(
        id=str(finding.id),
        audit_id=str(finding.audit_id),
        title=finding.title,
        description=finding.description,
        area=finding.requirement_ref or "Uncategorized",
        severity=_map_finding_severity_to_api(finding.severity),
        status=_map_finding_status_to_api(finding.status),
        due_date=finding.due_by.isoformat() if finding.due_by else None,
        days_overdue=_compute_days_overdue(finding.due_by, finding.status),
        assigned_to=assigned_to,
    )


# =============================================================================
# Endpoints - Dashboard Stats
# =============================================================================

@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(db: DBSession, current_user: CurrentUser) -> Any:
    """Get audit dashboard statistics."""
    now = datetime.now()
    year_start = datetime(now.year, 1, 1)

    total_audits = int(await db.scalar(select(func.count(QualityAudit.id))) or 0)
    completed_this_year = int(
        await db.scalar(
            select(func.count(QualityAudit.id)).where(
                QualityAudit.status == "completed",
                QualityAudit.completed_at.is_not(None),
                QualityAudit.completed_at >= year_start,
            )
        )
        or 0
    )
    open_findings = int(
        await db.scalar(
            select(func.count(AuditFinding.id)).where(
                AuditFinding.status.in_(["open", "action_planned", "action_implemented"])
            )
        )
        or 0
    )
    critical_findings = int(
        await db.scalar(
            select(func.count(AuditFinding.id)).where(
                AuditFinding.severity == "critical_nc",
                AuditFinding.status.not_in(["verified_closed", "cancelled"]),
            )
        )
        or 0
    )
    upcoming_audits = int(
        await db.scalar(
            select(func.count(QualityAudit.id)).where(
                QualityAudit.status == "planned",
                QualityAudit.scheduled_for >= now,
            )
        )
        or 0
    )

    # Derived compliance score from real findings.
    open_critical = critical_findings
    open_major = int(
        await db.scalar(
            select(func.count(AuditFinding.id)).where(
                AuditFinding.severity == "major_nc",
                AuditFinding.status == "open",
            )
        )
        or 0
    )
    compliance_score = max(0.0, min(100.0, float(100 - (open_critical * 10) - (open_major * 5))))
    
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
    # No fabricated default areas: compute from persisted findings.
    rows = (
        await db.execute(
            select(
                func.coalesce(AuditFinding.requirement_ref, "Uncategorized").label("area"),
                func.count(AuditFinding.id).label("findings"),
                func.sum(
                    func.case(
                        (
                            AuditFinding.status.in_(["open", "action_planned", "action_implemented"]),
                            1,
                        ),
                        else_=0,
                    )
                ).label("open_findings"),
                func.count(func.distinct(AuditFinding.audit_id)).label("audits"),
            ).group_by("area")
        )
    ).all()

    result: list[ComplianceAreaResponse] = []
    for area, _findings_count, open_count, audits_count in rows:
        open_count_int = int(open_count or 0)
        score = max(0.0, min(100.0, float(100 - (open_count_int * 2))))
        result.append(
            ComplianceAreaResponse(
                name=str(area),
                score=score,
                audits=int(audits_count or 0),
                trend="stable" if open_count_int == 0 else "down",
            )
        )
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
    q = select(QualityAudit)
    if status:
        q = q.where(QualityAudit.status == _map_audit_status_to_db(status))
    if audit_type:
        q = q.where(QualityAudit.audit_type == audit_type)
    q = q.order_by(QualityAudit.scheduled_for.desc())

    audits = (await db.execute(q)).scalars().all()
    items = [
        (await _to_audit_response(db, a)).model_dump()
        for a in audits
    ]
    return build_response(data={"items": items})


@router.get("/audits/upcoming", response_model=List[AuditResponse])
async def get_upcoming_audits(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(5, ge=1, le=20)
) -> Any:
    """Get upcoming scheduled audits."""
    now = datetime.now()
    q = (
        select(QualityAudit)
        .where(QualityAudit.status == "planned", QualityAudit.scheduled_for >= now)
        .order_by(QualityAudit.scheduled_for.asc())
        .limit(limit)
    )
    audits = (await db.execute(q)).scalars().all()
    return [await _to_audit_response(db, a) for a in audits]


@router.get("/audits/{audit_id}", response_model=AuditResponse)
async def get_audit(audit_id: str, db: DBSession, current_user: CurrentUser) -> Any:
    """Get a specific audit."""
    try:
        audit_uuid = UUID(audit_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = await db.get(QualityAudit, audit_uuid)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return await _to_audit_response(db, audit)


@router.post("/audits", response_model=AuditResponse)
async def create_audit(
    audit_in: AuditCreateSchema,
    db: DBSession,
    current_user: CurrentUser
) -> Any:
    """Create a new audit."""
    scheduled_for = datetime.combine(audit_in.scheduled_date, datetime.min.time())
    audit = QualityAudit(
        audit_type=audit_in.audit_type,
        title=audit_in.name,
        scheduled_for=scheduled_for,
        duration_minutes=60,
        scope=audit_in.description,
        status="planned",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    return await _to_audit_response(db, audit)


@router.patch("/audits/{audit_id}/status", response_model=AuditResponse)
async def update_audit_status(
    audit_id: str,
    status: str,
    db: DBSession,
    current_user: CurrentUser
) -> Any:
    """Update audit status."""
    try:
        audit_uuid = UUID(audit_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = await db.get(QualityAudit, audit_uuid)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    valid_statuses = ["scheduled", "in_progress", "completed", "closed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    audit.status = _map_audit_status_to_db(status)
    if audit.status == "completed" and audit.completed_at is None:
        audit.completed_at = datetime.now()
    await db.commit()
    await db.refresh(audit)
    return await _to_audit_response(db, audit)


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
    q = select(AuditFinding).options()
    if audit_id:
        try:
            audit_uuid = UUID(audit_id)
        except Exception:
            return build_response(data={"items": []})
        q = q.where(AuditFinding.audit_id == audit_uuid)
    if status:
        q = q.where(AuditFinding.status.in_(_map_finding_status_to_db(status)))
    if severity:
        q = q.where(AuditFinding.severity == _map_finding_severity_to_db(severity))
    q = q.order_by(AuditFinding.created_at.desc())

    findings = (await db.execute(q)).scalars().all()
    items = [(await _to_finding_response(f)).model_dump() for f in findings]
    return build_response(data={"items": items})


@router.get("/findings/open", response_model=List[AuditFindingResponse])
async def get_open_findings(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=50)
) -> Any:
    """Get open findings prioritized by severity and due date."""
    q = (
        select(AuditFinding)
        .where(AuditFinding.status.in_(["open", "action_planned", "action_implemented"]))
        .order_by(AuditFinding.due_by.asc().nulls_last(), AuditFinding.created_at.desc())
        .limit(limit)
    )
    findings = (await db.execute(q)).scalars().all()
    resp = [await _to_finding_response(f) for f in findings]
    severity_order = {"critical": 0, "major": 1, "minor": 2, "observation": 3}
    resp.sort(key=lambda x: (severity_order.get(x.severity, 4), -x.days_overdue))
    return resp


@router.get("/findings/{finding_id}", response_model=AuditFindingResponse)
async def get_finding(finding_id: str, db: DBSession, current_user: CurrentUser) -> Any:
    """Get a specific finding."""
    try:
        finding_uuid = UUID(finding_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding = await db.get(AuditFinding, finding_uuid)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return await _to_finding_response(finding)


@router.post("/findings", response_model=AuditFindingResponse)
async def create_finding(
    finding_in: FindingCreateSchema,
    db: DBSession,
    current_user: CurrentUser
) -> Any:
    """Create a new audit finding."""
    try:
        audit_uuid = UUID(finding_in.audit_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = await db.get(QualityAudit, audit_uuid)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    finding = AuditFinding(
        audit_id=audit_uuid,
        title=finding_in.title,
        description=finding_in.description or "",
        requirement_ref=finding_in.area,
        severity=_map_finding_severity_to_db(finding_in.severity),
        status="open",
        due_by=finding_in.due_date,
        assigned_to_id=None,
    )
    db.add(finding)
    await db.commit()
    await db.refresh(finding)
    return await _to_finding_response(finding)


@router.patch("/findings/{finding_id}/status", response_model=AuditFindingResponse)
async def update_finding_status(
    finding_id: str,
    status: str,
    db: DBSession,
    current_user: CurrentUser
) -> Any:
    """Update finding status."""
    try:
        finding_uuid = UUID(finding_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding = await db.get(AuditFinding, finding_uuid)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    valid_statuses = ["open", "in_progress", "closed", "verified"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    if status == "open":
        finding.status = "open"
    elif status == "in_progress":
        finding.status = "action_implemented"
    else:
        finding.status = "verified_closed"

    await db.commit()
    await db.refresh(finding)
    return await _to_finding_response(finding)


# =============================================================================
# Endpoints - Reports
# =============================================================================

@router.get("/reports/summary", response_model=dict)
async def get_audit_summary_report(db: DBSession, current_user: CurrentUser) -> Any:
    """Generate audit summary report."""
    stats = await get_audit_stats(db, current_user)
    compliance = await get_compliance_areas(db, current_user)

    total_findings = int(await db.scalar(select(func.count(AuditFinding.id))) or 0)
    closed_findings = int(
        await db.scalar(
            select(func.count(AuditFinding.id)).where(AuditFinding.status.in_(["verified_closed", "cancelled"]))
        )
        or 0
    )
    
    return {
        "generated_at": datetime.now().isoformat(),
        "period": "YTD",
        "summary": stats.model_dump(),
        "compliance_by_area": [c.model_dump() for c in compliance],
        "total_audits_conducted": stats.completed_this_year,
        "average_findings_per_audit": round(total_findings / max(1, stats.completed_this_year), 1),
        "closure_rate": round((closed_findings / max(1, total_findings)) * 100, 1),
    }


@router.get("/reports/findings-trend", response_model=dict)
async def get_findings_trend(db: DBSession, current_user: CurrentUser) -> Any:
    """Get findings trend over time."""
    # Compute a simple 6-month trend from persisted data. Keep SQL portable
    # (SQLite in tests) by aggregating in Python.
    end = date.today().replace(day=1)
    months: list[date] = []
    cursor = end
    for _ in range(6):
        months.append(cursor)
        # step back one month
        prev_month_last_day = cursor - timedelta(days=1)
        cursor = prev_month_last_day.replace(day=1)
    months = list(reversed(months))

    q = select(AuditFinding.created_at, AuditFinding.status)
    findings = (await db.execute(q)).all()
    opened_by_month: dict[str, int] = {m.strftime("%b"): 0 for m in months}
    closed_by_month: dict[str, int] = {m.strftime("%b"): 0 for m in months}

    for created_at, status in findings:
        if not created_at:
            continue
        key = created_at.strftime("%b")
        if key in opened_by_month:
            opened_by_month[key] += 1
            if status in {"verified_closed", "cancelled"}:
                closed_by_month[key] += 1

    data = [
        {"month": m.strftime("%b"), "opened": opened_by_month[m.strftime("%b")], "closed": closed_by_month[m.strftime("%b")]}
        for m in months
    ]
    return {"period": "6 months", "data": data}
