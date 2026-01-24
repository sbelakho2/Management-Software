"""Common Thread genealogy endpoints.

Exposes deterministic trace retrieval across modules by combining:
- data lineage graph
- reasoning IDs attached to entities

Also supports explicit binding of entities across the RFQ->Quote->WO->NC->Shipment chain.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import get_current_user, get_db
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.models.user import User
from sensei.services.core.common_thread import get_common_thread_service

router = APIRouter()

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class CommonThreadNodeResponse(BaseModel):
    entity_type: str
    entity_id: str
    reasoning_ids: list[str] = Field(default_factory=list)


class CommonThreadEdgeResponse(BaseModel):
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    relationship_type: str


class CommonThreadTraceResponse(BaseModel):
    root_entity_type: str
    root_entity_id: str
    nodes: list[CommonThreadNodeResponse]
    edges: list[CommonThreadEdgeResponse]


class CommonThreadBindRequest(BaseModel):
    rfq_id: str | None = None
    quote_id: str | None = None
    work_order_id: str | None = None
    non_conformance_id: str | None = None
    shipment_id: str | None = None
    invoice_id: str | None = None

    source: str | None = Field(default="api")


@router.get("/trace", response_model=APIResponse[CommonThreadTraceResponse])
async def get_common_thread_trace(
    db: DBSession,
    entity_type: str = Query(..., min_length=1, max_length=80),
    entity_id: str = Query(..., min_length=1, max_length=120),
    max_depth: int = Query(3, ge=0, le=10),
    current_user: CurrentUser | None = None,  # noqa: ARG001
) -> APIResponse[CommonThreadTraceResponse]:
    trace = await get_common_thread_service().get_trace(
        db,
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        max_depth=max_depth,
    )

    resp = CommonThreadTraceResponse(
        root_entity_type=trace.root_entity_type,
        root_entity_id=trace.root_entity_id,
        nodes=[
            CommonThreadNodeResponse(
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                reasoning_ids=n.reasoning_ids,
            )
            for n in trace.nodes
        ],
        edges=[
            CommonThreadEdgeResponse(
                source_entity_type=e.source_entity_type,
                source_entity_id=e.source_entity_id,
                target_entity_type=e.target_entity_type,
                target_entity_id=e.target_entity_id,
                relationship_type=e.relationship_type,
            )
            for e in trace.edges
        ],
    )

    return build_response(data=resp)


@router.post("/bind", response_model=APIResponse[dict])
async def bind_common_thread(
    req: CommonThreadBindRequest,
    db: DBSession,
    current_user: CurrentUser | None = None,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[dict]:
    await get_common_thread_service().bind(
        db,
        rfq_id=req.rfq_id,
        quote_id=req.quote_id,
        work_order_id=req.work_order_id,
        non_conformance_id=req.non_conformance_id,
        shipment_id=req.shipment_id,
        invoice_id=req.invoice_id,
        created_by_id=getattr(current_user, "id", None),
        reasoning_id=x_reasoning_id,
        source=req.source,
    )
    await db.commit()
    return build_response(data={"bound": True})
