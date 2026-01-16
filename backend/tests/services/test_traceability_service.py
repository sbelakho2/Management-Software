from __future__ import annotations

import pytest

from sensei.services.quality.traceability_service import TraceabilityService


@pytest.mark.asyncio
async def test_traceability_flow(async_session):
    svc = TraceabilityService(async_session)

    matrix = await svc.create_matrix(
        name="WO-TRACE-1001",
        status="active",
        lot_number="LOT-2026-1001",
    )

    link = await svc.add_link(
        matrix_id=matrix.id,
        link_type="inspection",
        reference_id="INS-0001",
        reference_table="quality_inspections",
        notes="Incoming inspection",
    )

    assert link.matrix_id == matrix.id
    assert link.link_type == "inspection"
