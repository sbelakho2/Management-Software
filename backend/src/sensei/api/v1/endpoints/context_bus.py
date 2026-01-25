"""Cross-Module Context Bus API endpoints.

Provides a deterministic "context pack" around an entity, intended as the
input substrate for higher-level AI reasoning (kept out of this endpoint).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from sensei.api.deps import DBSession, OptionalCurrentUser
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.services.core.context_bus import get_context_service

router = APIRouter()


class ContextNodeResponse(BaseModel):
    entity_type: str
    entity_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class ContextEdgeResponse(BaseModel):
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    relationship_type: str


class ContextPackResponse(BaseModel):
    root_entity_type: str
    root_entity_id: str
    nodes: list[ContextNodeResponse]
    edges: list[ContextEdgeResponse]


@router.get("/pack", response_model=APIResponse[ContextPackResponse])
async def get_context_pack(
    db: DBSession,
    entity_type: str = Query(..., min_length=1, max_length=80),
    entity_id: str = Query(..., min_length=1, max_length=120),
    max_depth: int = Query(3, ge=0, le=10),
    current_user: OptionalCurrentUser = None,  # noqa: ARG001
) -> APIResponse[ContextPackResponse]:
    pack = await get_context_service().get_context_pack(
        db,
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        max_depth=max_depth,
    )

    resp = ContextPackResponse(
        root_entity_type=pack.root_entity_type,
        root_entity_id=pack.root_entity_id,
        nodes=[
            ContextNodeResponse(entity_type=n.entity_type, entity_id=n.entity_id, data=n.data)
            for n in pack.nodes
        ],
        edges=[
            ContextEdgeResponse(
                source_entity_type=e["source_entity_type"],
                source_entity_id=e["source_entity_id"],
                target_entity_type=e["target_entity_type"],
                target_entity_id=e["target_entity_id"],
                relationship_type=e["relationship_type"],
            )
            for e in pack.edges
        ],
    )

    return build_response(data=resp)
