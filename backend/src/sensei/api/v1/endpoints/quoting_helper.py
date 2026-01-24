import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api import deps
from sensei.api.deps import CurrentUser, DBSession
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response, build_updated_response
from sensei.api.v1.schemas.quoting_helper import (
    WorkPacketRead,
    WorkPacketUpdate,
    RateCardRead,
    PCBSpecRead,
)
from sensei.services.sales.quoting_helper import get_quoting_helper_service, QuotingHelperService
from sensei.services.ai.quoting_assist import get_quoting_assist_service, QuotingAssistService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/rfqs/{rfq_id}/workpackets/generate",
    response_model=APIResponse[List[WorkPacketRead]],
    status_code=status.HTTP_201_CREATED,
)
async def generate_work_packets(
    rfq_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    service: QuotingHelperService = Depends(get_quoting_helper_service),
    current_user: CurrentUser = Depends(deps.get_current_active_user),
):
    """Generate default work packets for an RFQ."""
    packets = await service.generate_work_packets(rfq_id)
    return build_response(packets)


@router.get(
    "/rfqs/{rfq_id}/workpackets",
    response_model=APIResponse[List[WorkPacketRead]],
)
async def get_work_packets(
    rfq_id: UUID,
    service: QuotingHelperService = Depends(get_quoting_helper_service),
    current_user: CurrentUser = Depends(deps.get_current_active_user),
):
    """Get all work packets for an RFQ."""
    packets = await service.get_work_packets(rfq_id)
    return build_response(packets)


@router.patch(
    "/workpackets/{packet_id}",
    response_model=APIResponse[WorkPacketRead],
)
async def update_work_packet(
    packet_id: UUID,
    packet_in: WorkPacketUpdate,
    service: QuotingHelperService = Depends(get_quoting_helper_service),
    current_user: CurrentUser = Depends(deps.get_current_active_user),
):
    """Update a work packet."""
    packet = await service.update_work_packet(packet_id, packet_in.model_dump(exclude_unset=True))
    return build_updated_response(packet)


@router.post(
    "/rfqs/{rfq_id}/ingest",
    response_model=APIResponse[Dict[str, Any]],
)
async def ingest_rfq(
    rfq_id: UUID,
    files: List[Dict[str, Any]],
    service: QuotingHelperService = Depends(get_quoting_helper_service),
    current_user: CurrentUser = Depends(deps.get_current_active_user),
):
    """Stage 0 - Ingest RFQ package."""
    package_version = await service.ingest_rfq_package(rfq_id, files)
    return build_response({
        "rfq_id": rfq_id,
        "version_number": package_version.version_number,
        "extracted_metadata": package_version.extracted_metadata,
        "triage_risk_score": package_version.extracted_metadata.get("complexity_score"),
    })


@router.post(
    "/quotes/{quote_id}/cost/build",
    response_model=APIResponse[Dict[str, Any]],
)
async def build_quote_cost(
    quote_id: UUID,
    rate_card_id: Optional[UUID] = None,
    service: QuotingHelperService = Depends(get_quoting_helper_service),
    current_user: CurrentUser = Depends(deps.get_current_active_user),
):
    """Stage 3 - Deterministic costing rollup."""
    quote = await service.calculate_cost_estimate(quote_id, rate_card_id)
    return build_response({
        "quote_id": quote.id,
        "total_cost": quote.total_cost,
        "actual_margin": quote.actual_margin,
    })


@router.post(
    "/quotes/{quote_id}/convert-to-npi",
    response_model=APIResponse[Dict[str, Any]],
)
async def convert_to_npi(
    quote_id: UUID,
    service: QuotingHelperService = Depends(get_quoting_helper_service),
    current_user: CurrentUser = Depends(deps.get_current_active_user),
):
    """Stage 6.10 - One-click 'Quote -> NPI Pack'."""
    project = await service.convert_to_npi(quote_id, current_user.id)
    return build_response({
        "project_id": project.id,
        "project_name": project.name,
        "project_slug": project.slug,
    })


@router.get(
    "/ai/clarifications/suggest/{rfq_id}",
    response_model=APIResponse[List[Dict[str, Any]]],
)
async def suggest_clarifications(
    rfq_id: UUID,
    service: QuotingAssistService = Depends(get_quoting_assist_service),
    current_user: CurrentUser = Depends(deps.get_current_active_user),
):
    """AI suggest minimal clarification questions."""
    suggestions = await service.suggest_clarifications(rfq_id)
    return build_response(suggestions)


@router.get(
    "/ai/quote-memory/retrieve/{rfq_id}",
    response_model=APIResponse[List[Dict[str, Any]]],
)
async def retrieve_quote_memory(
    rfq_id: UUID,
    service: QuotingAssistService = Depends(get_quoting_assist_service),
    current_user: CurrentUser = Depends(deps.get_current_active_user),
):
    """AI retrieve similar historical jobs."""
    memory = await service.retrieve_quote_memory(rfq_id)
    return build_response(memory)
