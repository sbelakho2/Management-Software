from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.quality_qms import ManagementReview, ManagementReviewAction


class ManagementReviewService:
    """Service for management review automation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_reviews(self) -> list[ManagementReview]:
        result = await self.db.execute(select(ManagementReview))
        return list(result.scalars().all())

    async def get_review(self, review_id: UUID) -> Optional[ManagementReview]:
        result = await self.db.execute(select(ManagementReview).where(ManagementReview.id == review_id))
        return result.scalar_one_or_none()

    async def create_review(self, **kwargs) -> ManagementReview:
        review = ManagementReview(**kwargs)
        self.db.add(review)
        await self.db.flush()
        return review

    async def add_action(self, **kwargs) -> ManagementReviewAction:
        action = ManagementReviewAction(**kwargs)
        self.db.add(action)
        await self.db.flush()
        return action

    async def list_actions(self, review_id: Optional[UUID] = None) -> list[ManagementReviewAction]:
        stmt = select(ManagementReviewAction)
        if review_id:
            stmt = stmt.where(ManagementReviewAction.review_id == review_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def close_review(self, review: ManagementReview) -> ManagementReview:
        review.status = "closed"
        review.held_at = datetime.now(timezone.utc)
        await self.db.flush()
        return review
