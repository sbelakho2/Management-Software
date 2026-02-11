from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import json

from sensei.api.v1.endpoints.executive_intel import analyze_employee_risk, export_strategic_report
from sensei.api.v1.endpoints.executive_intel import EmployeeRiskRequest

import pytest

from sensei.api.exceptions import BadRequestError
from sensei.api.v1.endpoints.executive_intel import NL2SQLRequest, nl2sql_query


def make_db(*, scalar_value: int = 0):
    db = MagicMock()
    result = MagicMock()
    result.scalar = MagicMock(return_value=scalar_value)
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_nl2sql_open_non_conformances_counts() -> None:
    db = make_db(scalar_value=7)
    current_user = type("User", (), {"id": "u-1"})()
    allow_exec = True  # Stub for AllowExec dependency

    resp = await nl2sql_query(allow_exec, NL2SQLRequest(question="How many open non conformances are there?"), db, current_user)
    assert resp.success is True
    assert resp.data.result["open_non_conformances"] == 7


@pytest.mark.asyncio
async def test_nl2sql_rejects_unsupported_question() -> None:
    db = make_db(scalar_value=0)
    current_user = type("User", (), {"id": "u-1"})()
    allow_exec = True  # Stub for AllowExec dependency

    with pytest.raises(BadRequestError):
        await nl2sql_query(allow_exec, NL2SQLRequest(question="Show me all customers"), db, current_user)


class _StubUser:
    def __init__(self, *, is_superuser: bool = True):
        self.is_superuser = is_superuser


@pytest.mark.asyncio
async def test_employee_risk_analysis_returns_assessment():
    db = MagicMock()
    user = _StubUser(is_superuser=True)
    allow_exec = True  # Stub for AllowExec dependency

    payload = EmployeeRiskRequest(
        employee_name="Alice Example",
        department="Operations",
        tenure_months=3,
        overtime_hours_weekly=20,
        skip_rate=0.25,
        peer_comparison=1.4,
    )

    resp = await analyze_employee_risk(_=allow_exec, payload=payload, db=db, current_user=user)
    assert resp.success is True
    assert resp.data is not None
    assert resp.data.employee_name == "Alice Example"
    assert resp.data.retention_risk in {"low", "medium", "high", "critical"}
    assert resp.data.burnout_risk in {"low", "medium", "high", "critical"}
    assert isinstance(resp.data.risk_factors, list)


@pytest.mark.asyncio
async def test_strategic_report_export_downloads_json():
    db = MagicMock()
    user = _StubUser(is_superuser=True)
    allow_exec = True  # Stub for AllowExec dependency

    # The endpoint executes 22 DB queries via asyncio.gather.
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    db.execute = AsyncMock(return_value=mock_result)

    resp = await export_strategic_report(_=allow_exec, db=db, current_user=user)
    assert resp.media_type == "application/json"
    assert "attachment" in resp.headers.get("Content-Disposition", "")

    payload = json.loads(resp.body.decode("utf-8"))
    assert payload["quality"]["open_non_conformances"] == 0
    assert payload["quality"]["open_capas"] == 0
