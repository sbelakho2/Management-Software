"""Development-only endpoints for end-to-end (E2E) automation.

These endpoints are used by Playwright (and similar) to:
- seed minimal, valid domain data
- validate backend + DB persistence through read APIs

They are disabled in production.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from sensei.api.deps import DBSession, get_current_user
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.core.config import settings
from sensei.models.account import Account
from sensei.models.quote import Quote
from sensei.models.rfq import RFQ
from sensei.models.user import User
from sensei.services.core.data_lineage import DataLineageService


def _deny_production() -> None:
    if settings.is_production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


router = APIRouter(dependencies=[Depends(_deny_production)])


class SeedLineageResponse(BaseModel):
    account_id: str
    rfq_id: str
    quote_id: str
    lineage_relationship_type: str


@router.post(
    "/e2e/seed-lineage",
    response_model=APIResponse[SeedLineageResponse],
    status_code=status.HTTP_201_CREATED,
)
async def seed_lineage(
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> APIResponse[SeedLineageResponse]:
    """Seed a minimal Account + RFQ + Quote and connect via Data Lineage.

    Purpose: enable true E2E tests that validate backend+DB persistence and
    cross-module graph retrieval.
    """

    # Generate deterministic-ish identifiers for uniqueness in repeated runs.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    relationship_type = "e2e_seeded"

    account = Account(name=f"E2E Account {stamp}")
    db.add(account)
    await db.flush()

    rfq = RFQ(
        rfq_number=f"E2E-RFQ-{stamp}",
        title="E2E RFQ",
        account_id=account.id,
        status="received",
        priority="medium",
        currency="MAD",
        custom_fields={"e2e_seed": True, "stamp": stamp},
    )
    db.add(rfq)
    await db.flush()

    quote = Quote(
        quote_number=f"E2E-QUOTE-{stamp}",
        title="E2E Quote",
        account_id=account.id,
        rfq_id=rfq.id,
        status="draft",
        currency="MAD",
        custom_fields={"e2e_seed": True, "stamp": stamp},
    )
    db.add(quote)
    await db.flush()

    await DataLineageService().link(
        db,
        source_entity_type="rfq",
        source_entity_id=str(rfq.id),
        relationship_type=relationship_type,
        target_entity_type="quote",
        target_entity_id=str(quote.id),
        created_by_id=getattr(current_user, "id", None),
        metadata={"seed": True, "stamp": stamp},
    )

    await db.commit()

    return build_response(
        data=SeedLineageResponse(
            account_id=str(account.id),
            rfq_id=str(rfq.id),
            quote_id=str(quote.id),
            lineage_relationship_type=relationship_type,
        )
    )
