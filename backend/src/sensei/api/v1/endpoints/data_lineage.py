"""Data Lineage API endpoints.

Exposes a deterministic lineage graph view around an entity.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import get_current_user, get_db
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.models.user import User
from sensei.services.core.data_lineage import get_data_lineage_service

router = APIRouter()

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class LineageNodeResponse(BaseModel):
    entity_type: str
    entity_id: str


class LineageEdgeResponse(BaseModel):
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    relationship_type: str


class LineageGraphResponse(BaseModel):
    root_entity_type: str
    root_entity_id: str
    nodes: list[LineageNodeResponse]
    edges: list[LineageEdgeResponse]


@router.get("/graph", response_model=APIResponse[LineageGraphResponse])
async def get_lineage_graph(
    db: DBSession,
    entity_type: str = Query(..., min_length=1, max_length=80),
    entity_id: str = Query(..., min_length=1, max_length=120),
    max_depth: int = Query(3, ge=0, le=10),
    current_user: CurrentUser | None = None,  # noqa: ARG001
) -> APIResponse[LineageGraphResponse]:
    graph = await get_data_lineage_service().get_graph(
        db,
        root_entity_type=entity_type,
        root_entity_id=entity_id,
        max_depth=max_depth,
    )

    resp = LineageGraphResponse(
        root_entity_type=entity_type,
        root_entity_id=str(entity_id),
        nodes=[LineageNodeResponse(entity_type=n.entity_type, entity_id=n.entity_id) for n in graph.nodes],
        edges=[
            LineageEdgeResponse(
                source_entity_type=e.source.entity_type,
                source_entity_id=e.source.entity_id,
                target_entity_type=e.target.entity_type,
                target_entity_id=e.target.entity_id,
                relationship_type=e.relationship_type,
            )
            for e in graph.edges
        ],
    )

    return build_response(data=resp)
