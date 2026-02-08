"""
Customer Satisfaction Service.

Manages customer satisfaction surveys, Net Promoter Score
(NPS) tracking, complaint correlation analysis, and
customer feedback workflows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.quality_qms import (
    CustomerComplaint,
    CustomerSurvey,
    CustomerSurveyResponse,
)


class CustomerSatisfactionService:
    """Persistent customer satisfaction service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_complaints(self) -> list[CustomerComplaint]:
        result = await self.db.execute(select(CustomerComplaint))
        return list(result.scalars().all())

    async def get_complaint(self, complaint_id: UUID) -> Optional[CustomerComplaint]:
        result = await self.db.execute(
            select(CustomerComplaint).where(CustomerComplaint.id == complaint_id)
        )
        return result.scalar_one_or_none()

    async def create_complaint(self, **kwargs) -> CustomerComplaint:
        complaint = CustomerComplaint(**kwargs)
        self.db.add(complaint)
        await self.db.flush()
        return complaint

    async def update_complaint(self, complaint: CustomerComplaint, **kwargs) -> CustomerComplaint:
        for key, value in kwargs.items():
            setattr(complaint, key, value)
        await self.db.flush()
        return complaint

    async def close_complaint(self, complaint: CustomerComplaint) -> CustomerComplaint:
        complaint.status = "closed"
        complaint.closed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return complaint

    async def list_surveys(self) -> list[CustomerSurvey]:
        result = await self.db.execute(
            select(CustomerSurvey).options(selectinload(CustomerSurvey.responses))
        )
        return list(result.scalars().all())

    async def get_survey(self, survey_id: UUID) -> Optional[CustomerSurvey]:
        result = await self.db.execute(
            select(CustomerSurvey)
            .where(CustomerSurvey.id == survey_id)
            .options(selectinload(CustomerSurvey.responses))
        )
        return result.scalar_one_or_none()

    async def create_survey(self, **kwargs) -> CustomerSurvey:
        survey = CustomerSurvey(**kwargs)
        self.db.add(survey)
        await self.db.flush()
        return survey

    async def add_response(
        self,
        *,
        survey_id: UUID,
        nps_score: int,
        customer_id: Optional[UUID] = None,
        respondent_name: Optional[str] = None,
        respondent_email: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> CustomerSurveyResponse:
        response = CustomerSurveyResponse(
            survey_id=survey_id,
            customer_id=customer_id,
            respondent_name=respondent_name,
            respondent_email=respondent_email,
            nps_score=nps_score,
            comment=comment,
            submitted_at=datetime.now(timezone.utc),
        )
        self.db.add(response)
        await self.db.flush()
        return response

    async def compute_nps_stats(self, survey_id: Optional[UUID] = None) -> dict:
        query = select(CustomerSurveyResponse)
        if survey_id:
            query = query.where(CustomerSurveyResponse.survey_id == survey_id)
        result = await self.db.execute(query)
        responses = list(result.scalars().all())

        total = len(responses)
        if total == 0:
            return {
                "total_responses": 0,
                "promoters": 0,
                "passives": 0,
                "detractors": 0,
                "nps_score": 0,
                "average_score": 0,
            }

        promoters = sum(1 for r in responses if r.nps_score >= 9)
        passives = sum(1 for r in responses if 7 <= r.nps_score <= 8)
        detractors = sum(1 for r in responses if r.nps_score <= 6)

        nps_score = ((promoters - detractors) / total) * 100
        average_score = sum(r.nps_score for r in responses) / total

        return {
            "total_responses": total,
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors,
            "nps_score": round(nps_score, 1),
            "average_score": round(average_score, 2),
        }

    async def complaint_stats(self) -> dict:
        total_query = await self.db.execute(select(func.count(CustomerComplaint.id)))
        total = total_query.scalar_one() or 0

        open_query = await self.db.execute(
            select(func.count(CustomerComplaint.id)).where(CustomerComplaint.status != "closed")
        )
        open_count = open_query.scalar_one() or 0

        closed_query = await self.db.execute(
            select(func.count(CustomerComplaint.id)).where(CustomerComplaint.status == "closed")
        )
        closed_count = closed_query.scalar_one() or 0

        return {
            "total": total,
            "open": open_count,
            "closed": closed_count,
        }
