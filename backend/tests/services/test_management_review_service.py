from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sensei.services.quality.management_review_service import ManagementReviewService


@pytest.mark.asyncio
async def test_management_review_flow(async_session):
    svc = ManagementReviewService(async_session)
    review = await svc.create_review(
        title="Q1 Management Review",
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
        scheduled_for=datetime(2026, 4, 5, tzinfo=timezone.utc),
        status="scheduled",
    )

    action = await svc.add_action(
        review_id=review.id,
        title="Improve supplier audit cadence",
        status="open",
    )

    assert action.review_id == review.id

    await svc.close_review(review)
    assert review.status == "closed"
