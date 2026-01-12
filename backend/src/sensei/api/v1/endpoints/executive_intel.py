"""Executive intelligence endpoints (CEO/Exec).

Development Plan 23.3 persona flow prerequisites:
- NL2SQL query endpoint (deterministic, safe, read-only)

This intentionally implements a *restricted* NL2SQL capability:
- only a small allowlist of supported questions
- executed via SQLAlchemy ORM (no raw SQL)
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

from typing import Any, Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from sensei.api import deps
from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import BadRequestError
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.models.quality import CAPA, CAPAStatus, NCStatus, NonConformance
from sensei.services.ops.ceo_control_plane import CEOControlPlaneService

router = APIRouter()

# Role requirements
AllowExec = deps.require_role("admin", "ceo", "gm", "exec")


class NL2SQLRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class NL2SQLResponse(BaseModel):
    query_id: str
    natural_language: str
    generated_sql: str
    explanation: str
    result: dict


class EmployeeRiskRequest(BaseModel):
    employee_name: str = Field(..., min_length=1, max_length=200)
    department: str = Field(default="", max_length=200)
    tenure_months: int = Field(default=12, ge=0, le=600)
    overtime_hours_weekly: float = Field(default=0, ge=0, le=168)
    skip_rate: float = Field(default=0, ge=0, le=1)
    peer_comparison: float = Field(default=1.0, ge=0, le=10)


class EmployeeRiskResponse(BaseModel):
    employee_name: str
    retention_risk: str
    retention_score: float
    burnout_risk: str
    burnout_score: float
    risk_factors: list[str]
    recommendations: list[str]


def _roles_for_user(user: object) -> set[str]:
    if getattr(user, "is_superuser", False):
        return {"superuser"}
    role_names = []
    if hasattr(user, "get_role_names"):
        try:
            role_names = list(user.get_role_names())  # type: ignore[attr-defined]
        except Exception:
            role_names = []
    return {str(r).lower() for r in role_names}


def _coerce_exec_role(user: object) -> str:
    roles = _roles_for_user(user)
    for candidate in ("ceo", "exec", "admin", "superuser"):
        if candidate in roles:
            return candidate
    # Default to superuser check only; otherwise deny.
    raise BadRequestError("Executive access required")


def _normalize(q: str) -> str:
    return " ".join(q.strip().lower().split())


@router.post("/nl2sql", response_model=APIResponse[NL2SQLResponse])
async def nl2sql_query(
    _: AllowExec,
    payload: NL2SQLRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[NL2SQLResponse]:
    q = _normalize(payload.question)

    # Allowlist of deterministic, read-only executive questions.
    if "non conformance" in q or "nonconformance" in q or " nc " in f" {q} ":
        if "open" in q:
            stmt = select(func.count()).select_from(NonConformance).where(NonConformance.status == NCStatus.OPEN)
            count = (await db.execute(stmt)).scalar() or 0
            resp = NL2SQLResponse(
                query_id="nl2sql:open_non_conformances",
                natural_language=payload.question,
                generated_sql="SELECT COUNT(*) FROM non_conformances WHERE status = 'open';",
                explanation="Counts open non-conformance records.",
                result={"open_non_conformances": int(count)},
            )
            return build_response(data=resp)

    if "capa" in q:
        if "open" in q:
            stmt = select(func.count()).select_from(CAPA).where(CAPA.status == CAPAStatus.OPEN)
            count = (await db.execute(stmt)).scalar() or 0
            resp = NL2SQLResponse(
                query_id="nl2sql:open_capas",
                natural_language=payload.question,
                generated_sql="SELECT COUNT(*) FROM capas WHERE status = 'open';",
                explanation="Counts open CAPA records.",
                result={"open_capas": int(count)},
            )
            return build_response(data=resp)

    raise BadRequestError(
        "Unsupported NL2SQL question (restricted allowlist)",
        details={
            "supported_examples": [
                "How many open non conformances are there?",
                "How many open CAPAs are there?",
            ]
        },
    )


@router.post("/employee-risk/analyze", response_model=APIResponse[EmployeeRiskResponse])
async def analyze_employee_risk(
    _: AllowExec,
    payload: EmployeeRiskRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[EmployeeRiskResponse]:
    """Deterministic employee retention/burnout risk assessment.

    Note: This uses the existing CEO control plane service logic (Section 20.5) to keep
    behavior consistent with the executive risk model.
    """

    _ = db  # DB reserved for future HR/people-data integration.
    role = _coerce_exec_role(current_user)

    svc = CEOControlPlaneService()
    emp_id = svc.register_employee(role, name=payload.employee_name, department=payload.department)
    assessment = svc.assess_retention_risk(
        role,
        employee_id=emp_id,
        tenure_months=payload.tenure_months,
        overtime_hours_weekly=payload.overtime_hours_weekly,
        skip_rate=payload.skip_rate,
        peer_comparison=payload.peer_comparison,
    )

    resp = EmployeeRiskResponse(
        employee_name=assessment.employee_name,
        retention_risk=getattr(assessment.retention_risk, "value", str(assessment.retention_risk)).lower(),
        retention_score=float(assessment.retention_score),
        burnout_risk=getattr(assessment.burnout_risk, "value", str(assessment.burnout_risk)).lower(),
        burnout_score=float(assessment.burnout_score),
        risk_factors=list(assessment.risk_factors),
        recommendations=list(assessment.recommendations),
    )

    return build_response(data=resp)


@router.get("/strategic-report/export")
async def export_strategic_report(
    _: AllowExec,
    db: DBSession,
    current_user: CurrentUser,
) -> Response:
    """Export a minimal strategic report pack as a downloadable JSON file."""

    _ = _coerce_exec_role(current_user)

    open_nc_stmt = select(func.count()).select_from(NonConformance).where(NonConformance.status == NCStatus.OPEN)
    open_capa_stmt = select(func.count()).select_from(CAPA).where(CAPA.status == CAPAStatus.OPEN)
    open_non_conformances = int((await db.execute(open_nc_stmt)).scalar() or 0)
    open_capas = int((await db.execute(open_capa_stmt)).scalar() or 0)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpis": {
            "open_non_conformances": open_non_conformances,
            "open_capas": open_capas,
        },
        "notes": "Restricted export intended for CEO/Exec E2E validation.",
    }

    payload = json.dumps(report, indent=2, sort_keys=True)
    filename = f"strategic-report-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
